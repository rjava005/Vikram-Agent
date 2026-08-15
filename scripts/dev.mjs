import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { createDevChildEnvironments } from "./dev-environment.mjs";

const port = process.env.VIKRAM_PORT ?? "8742";
if (!/^\d+$/.test(port) || Number(port) < 1024 || Number(port) > 65535) {
	throw new Error("VIKRAM_PORT must be an unprivileged TCP port.");
}

const apiBase = process.env.VIKRAM_API_BASE_URL ?? `http://127.0.0.1:${port}`;
const parsedBase = new URL(apiBase);
if (
	parsedBase.protocol !== "http:" ||
	!new Set(["127.0.0.1", "localhost"]).has(parsedBase.hostname) ||
	parsedBase.port !== port
) {
	throw new Error("VIKRAM_API_BASE_URL must match the configured loopback port.");
}

const { apiEnvironment, desktopEnvironment } = createDevChildEnvironments(
	process.env,
	{
		apiToken: randomBytes(32).toString("base64url"),
		apiBaseUrl: parsedBase.origin,
		host: "127.0.0.1",
		port,
	},
);
const desktopCommand =
	process.platform === "win32"
		? (process.env.ComSpec ?? "C:\\Windows\\System32\\cmd.exe")
		: "corepack";
const desktopArguments =
	process.platform === "win32"
		? ["/d", "/s", "/c", "corepack pnpm --filter @vikram/desktop dev"]
		: ["pnpm", "--filter", "@vikram/desktop", "dev"];
const processes = [
	spawn(
		"uv",
		[
			"run",
			"--project",
			"services/api",
			"uvicorn",
			"vikram_api.main:app",
			"--host",
			"127.0.0.1",
			"--port",
			port,
		],
		{ env: apiEnvironment, stdio: "inherit", windowsHide: true },
	),
	spawn(desktopCommand, desktopArguments, {
		env: desktopEnvironment,
		stdio: "inherit",
		windowsHide: true,
	}),
];

let stopping = false;
function stop(exitCode = 0) {
	if (stopping) return;
	stopping = true;
	for (const child of processes) child.kill();
	process.exitCode = exitCode;
}

for (const child of processes) {
	child.on("error", (error) => {
		console.error(error.message);
		stop(1);
	});
	child.on("exit", (code) => {
		if (!stopping) stop(code ?? 1);
	});
}
process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));
