import { describe, expect, it } from "vitest";
import { validatedApiBase, validatedApiToken } from "../src/main/api";
import { isTrustedRendererUrl } from "../src/main/security";
import { browserWindowOptions } from "../src/main/windowOptions";

describe("desktop security boundary", () => {
	it("keeps the renderer sandboxed and isolated", () => {
		const options = browserWindowOptions("C:/app/preload.js", true);
		expect(options.webPreferences).toMatchObject({
			nodeIntegration: false,
			contextIsolation: true,
			sandbox: true,
			webSecurity: true,
			allowRunningInsecureContent: false,
			devTools: false,
		});
	});

	it("rejects external renderer and API origins", () => {
		expect(isTrustedRendererUrl("https://example.com")).toBe(false);
		expect(isTrustedRendererUrl("http://localhost:5173/")).toBe(true);
		expect(isTrustedRendererUrl("file:///tmp/attacker.html")).toBe(false);
		expect(
			isTrustedRendererUrl(
				"file:///C:/vikram/out/renderer/index.html",
				"file:///C:/vikram/out/renderer/index.html",
			),
		).toBe(true);
		expect(() => validatedApiBase("https://api.example.com")).toThrow(
			/loopback/i,
		);
		expect(validatedApiBase("http://127.0.0.1:8742")).toBe(
			"http://127.0.0.1:8742",
		);
		expect(() => validatedApiToken("short")).toThrow(/high-entropy/i);
		expect(
			validatedApiToken("test-local-capability-token-000000000000000000"),
		).toHaveLength(46);
	});
});
