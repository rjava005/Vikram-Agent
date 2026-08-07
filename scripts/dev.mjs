import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";

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

const environment = {
	...process.env,
	VIKRAM_API_TOKEN: randomBytes(32).toString("base64url"),
	VIKRAM_API_BASE_URL: parsedBase.origin,
	VIKRAM_HOST: "127.0.0.1",
	VIKRAM_PORT: port,
};
const corepack = process.platform === "win32" ? "corepack.cmd" : "corepack";
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
		{ env: environment, stdio: "inherit", windowsHide: true },
	),
	spawn(corepack, ["pnpm", "--filter", "@vikram/desktop", "dev"], {
		env: environment,
		shell: process.platform === "win32",
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
