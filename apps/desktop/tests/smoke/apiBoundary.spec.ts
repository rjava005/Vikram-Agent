import { _electron as electron, expect, test } from "@playwright/test";
import { type ChildProcess, spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { mkdtempSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { uploadSource } from "../../src/main/api";

let apiBase = "";
let apiToken = "";
let apiProcess: ChildProcess | null = null;
let apiExitCode: number | null = null;
let smokeDataDir = "";

async function reservePort(): Promise<number> {
	const server = createServer();
	await new Promise<void>((resolve, reject) => {
		server.once("error", reject);
		server.listen(0, "127.0.0.1", resolve);
	});
	const address = server.address();
	if (!address || typeof address === "string") {
		server.close();
		throw new Error("Could not reserve a loopback port.");
	}
	await new Promise<void>((resolve, reject) =>
		server.close((error) => (error ? reject(error) : resolve())),
	);
	return address.port;
}

test.beforeAll(async () => {
	const port = await reservePort();
	apiBase = `http://127.0.0.1:${port}`;
	apiToken = randomBytes(32).toString("base64url");
	smokeDataDir = mkdtempSync(join(tmpdir(), "vikram-smoke-"));
	const python =
		process.platform === "win32"
			? "../../services/api/.venv/Scripts/python.exe"
			: "../../services/api/.venv/bin/python";
	apiProcess = spawn(
		python,
		[
			"-m",
			"uvicorn",
			"vikram_api.main:app",
			"--host",
			"127.0.0.1",
			"--port",
			String(port),
		],
		{
			cwd: process.cwd(),
			env: {
				...process.env,
				VIKRAM_API_TOKEN: apiToken,
				VIKRAM_DATA_DIR: smokeDataDir,
			},
			stdio: "ignore",
			windowsHide: true,
		},
	);
	apiProcess.once("exit", (code) => {
		apiExitCode = code ?? 1;
	});
	const deadline = Date.now() + 20_000;
	while (Date.now() < deadline) {
		if (apiExitCode !== null) {
			throw new Error(`The smoke API exited early with code ${apiExitCode}.`);
		}
		try {
			const response = await fetch(`${apiBase}/health`);
			if (response.ok) return;
		} catch {
			// The owned API process is still starting.
		}
		await new Promise((resolve) => setTimeout(resolve, 150));
	}
	throw new Error(
		"The owned local API did not become ready for the boundary smoke test.",
	);
});

test.afterAll(async () => {
	if (apiProcess && apiExitCode === null) {
		const closed = new Promise<void>((resolve) =>
			apiProcess?.once("close", () => resolve()),
		);
		apiProcess.kill();
		await Promise.race([
			closed,
			new Promise<void>((resolve) => setTimeout(resolve, 2_000)),
		]);
	}
	if (smokeDataDir) {
		rmSync(smokeDataDir, {
			recursive: true,
			force: true,
			maxRetries: 10,
			retryDelay: 200,
		});
	}
});

async function jsonRequest(
	path: string,
	body: object,
): Promise<Record<string, unknown>> {
	const response = await fetch(`${apiBase}${path}`, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			"X-Vikram-Token": apiToken,
		},
		body: JSON.stringify(body),
	});
	expect(response.ok).toBe(true);
	return (await response.json()) as Record<string, unknown>;
}

test("secure desktop performs the grounded review flow across the real API boundary", async () => {
	const electronApp = await electron.launch({
		args: [process.cwd()],
		cwd: process.cwd(),
		timeout: 8_000,
		env: {
			...process.env,
			VIKRAM_API_BASE_URL: apiBase,
			VIKRAM_API_TOKEN: apiToken,
			VIKRAM_DISABLE_HARDWARE_ACCELERATION: "1",
			VIKRAM_ELECTRON_DATA_DIR: join(smokeDataDir, "electron"),
		},
	});
	try {
		const page = await electronApp.firstWindow({ timeout: 8_000 });
		await expect(page).toHaveTitle("Vikram Engineering Workspace");
		const runtimeBoundary = await page.evaluate(() => ({
			requireType: typeof (window as unknown as { require?: unknown }).require,
			processType: typeof (window as unknown as { process?: unknown }).process,
			bridgeKeys: Object.keys(window.vikramDesktop),
			capabilityKeys: Object.keys(window.vikramDesktop.v1),
		}));
		expect(runtimeBoundary).toEqual({
			requireType: "undefined",
			processType: "undefined",
			bridgeKeys: ["v1"],
			capabilityKeys: ["version", "connection", "sources", "microphone"],
		});

		const projectName = `Boundary smoke ${Date.now()}`;
		await page.getByRole("button", { name: "New project" }).click();
		await page.getByLabel("Project name").fill(projectName);
		await page.getByRole("button", { name: "Create project" }).click();
		await expect(
			page.getByRole("heading", { name: projectName }),
		).toBeVisible();

		const projectsResponse = await fetch(`${apiBase}/api/v1/projects`, {
			headers: { "X-Vikram-Token": apiToken },
		});
		expect(projectsResponse.ok).toBe(true);
		const projects = (await projectsResponse.json()) as Array<{
			id: string;
			name: string;
		}>;
		const projectId = projects.find(
			(project) => project.name === projectName,
		)?.id;
		expect(projectId).toBeTruthy();

		const source = await uploadSource({
			apiBase,
			apiToken,
			projectId: String(projectId),
			displayName: "smoke.md",
			mediaType: "text/markdown",
			bytes: new TextEncoder().encode(
				"# Grounding\nA current-limiting resistor protects an LED from excessive current.",
			),
		});
		expect(source.name).toBe("smoke.md");
		await page.reload();
		await expect(
			page.getByRole("heading", { name: projectName }),
		).toBeVisible();
		await expect(
			page.getByLabel("Ask about the selected project"),
		).toBeEnabled();

		const answer = await jsonRequest(`/api/v1/projects/${projectId}/answers`, {
			question: "What protects an LED from excessive current?",
		});
		expect(answer.grounding).toBe("grounded");
		expect(answer.citations).toEqual(
			expect.arrayContaining([
				expect.objectContaining({
					source_id: source.id,
					locator: expect.objectContaining({
						kind: "markdown_section",
						heading: "Grounding",
					}),
				}),
			]),
		);

		await page
			.getByLabel("Ask about the selected project")
			.fill("What protects an LED from excessive current?");
		await page.getByRole("button", { name: "Ask" }).click();
		await expect(page.getByText(/The source states:/)).toBeVisible();
		await expect(page.getByText("Grounding · lines 1–2")).toBeVisible();
		await page.getByLabel("Understood").click();
		await page.getByRole("button", { name: "Turn answer into a task" }).click();
		await expect(
			page.getByText("Review: What protects an LED from excessive current?"),
		).toBeVisible();
		await page.getByRole("button", { name: "Focus" }).click();
		await expect(page.getByRole("button", { name: "Pause" })).toBeVisible();
		await page.getByRole("button", { name: "Pause" }).click();
		await expect(page.getByRole("button", { name: "Resume" })).toBeVisible();
		await page.getByRole("button", { name: "Resume" }).click();
		await page.getByRole("button", { name: "Complete" }).click();
		await expect(page.getByRole("button", { name: "Complete" })).toHaveCount(0);
	} finally {
		const electronProcess = electronApp.process();
		await Promise.race([
			electronApp.close(),
			new Promise<void>((resolve) => setTimeout(resolve, 2_000)),
		]);
		if (electronProcess.exitCode === null) electronProcess.kill();
	}
});
