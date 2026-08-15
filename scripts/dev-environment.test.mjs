import assert from "node:assert/strict";
import test from "node:test";
import { createDevChildEnvironments } from "./dev-environment.mjs";

test("provider secrets reach only the API child environment", () => {
	const parentEnvironment = {
		PATH: "/tools/bin",
		HOME: "/home/vikram",
		TMPDIR: "/tmp/vikram",
		COREPACK_HOME: "/cache/corepack",
		NPM_CONFIG_CACHE: "/cache/npm",
		LANG: "en_US.UTF-8",
		LC_MESSAGES: "en_US.UTF-8",
		DISPLAY: ":0",
		NEBIUS_API_KEY: "nebius-secret",
		VIKRAM_NEBIUS_GENERATION_MODEL: "provider-model",
		OPENAI_API_KEY: "unrelated-provider-secret",
		VIKRAM_PROVIDER_MODE: "nebius",
		VIKRAM_API_TOKEN: "parent-token-must-not-win",
		VIKRAM_API_BASE_URL: "http://malicious.invalid:9999",
		VIKRAM_DATA_DIR: "/private/project-data",
	};
	const originalEnvironment = { ...parentEnvironment };
	const result = createDevChildEnvironments(parentEnvironment, {
		apiToken: "generated-capability-token",
		apiBaseUrl: "http://127.0.0.1:8742",
		host: "127.0.0.1",
		port: "8742",
	});

	assert.equal(result.apiEnvironment.NEBIUS_API_KEY, "nebius-secret");
	assert.equal(result.apiEnvironment.VIKRAM_PROVIDER_MODE, "nebius");
	assert.equal(
		result.apiEnvironment.VIKRAM_NEBIUS_GENERATION_MODEL,
		"provider-model",
	);
	assert.equal(
		result.apiEnvironment.VIKRAM_API_TOKEN,
		"generated-capability-token",
	);
	assert.equal(result.apiEnvironment.VIKRAM_HOST, "127.0.0.1");
	assert.equal(result.apiEnvironment.VIKRAM_PORT, "8742");

	assert.deepEqual(result.desktopEnvironment, {
		PATH: "/tools/bin",
		HOME: "/home/vikram",
		TMPDIR: "/tmp/vikram",
		COREPACK_HOME: "/cache/corepack",
		NPM_CONFIG_CACHE: "/cache/npm",
		LANG: "en_US.UTF-8",
		LC_MESSAGES: "en_US.UTF-8",
		DISPLAY: ":0",
		VIKRAM_API_TOKEN: "generated-capability-token",
		VIKRAM_API_BASE_URL: "http://127.0.0.1:8742",
	});
	assert.equal("NEBIUS_API_KEY" in result.desktopEnvironment, false);
	assert.equal(
		"VIKRAM_NEBIUS_GENERATION_MODEL" in result.desktopEnvironment,
		false,
	);
	assert.equal("OPENAI_API_KEY" in result.desktopEnvironment, false);
	assert.equal("VIKRAM_PROVIDER_MODE" in result.desktopEnvironment, false);
	assert.equal("VIKRAM_DATA_DIR" in result.desktopEnvironment, false);
	assert.deepEqual(parentEnvironment, originalEnvironment);
});

test("desktop allowlist retains Windows execution and cache variables", () => {
	const { desktopEnvironment } = createDevChildEnvironments(
		{
			Path: "C:\\Tools",
			ComSpec: "C:\\Windows\\System32\\cmd.exe",
			SystemRoot: "C:\\Windows",
			PATHEXT: ".COM;.EXE;.BAT;.CMD",
			USERPROFILE: "C:\\Users\\Vikram",
			LOCALAPPDATA: "C:\\Users\\Vikram\\AppData\\Local",
			TEMP: "C:\\Temp",
			PNPM_HOME: "C:\\pnpm",
			SECRET_ACCESS_TOKEN: "do-not-forward",
		},
		{
			apiToken: "generated-capability-token",
			apiBaseUrl: "http://localhost:9000",
			host: "127.0.0.1",
			port: "9000",
		},
	);

	assert.equal(desktopEnvironment.Path, "C:\\Tools");
	assert.equal(
		desktopEnvironment.ComSpec,
		"C:\\Windows\\System32\\cmd.exe",
	);
	assert.equal(desktopEnvironment.SystemRoot, "C:\\Windows");
	assert.equal(desktopEnvironment.PNPM_HOME, "C:\\pnpm");
	assert.equal("SECRET_ACCESS_TOKEN" in desktopEnvironment, false);
	assert.deepEqual(
		Object.keys(desktopEnvironment).filter((key) => key.startsWith("VIKRAM_")),
		["VIKRAM_API_TOKEN", "VIKRAM_API_BASE_URL"],
	);
});
