import { beforeEach, describe, expect, it, vi } from "vitest";

const electronMock = vi.hoisted(() => ({
	exposeInMainWorld: vi.fn(),
	invoke: vi.fn(),
}));

vi.mock("electron", () => ({
	contextBridge: { exposeInMainWorld: electronMock.exposeInMainWorld },
	ipcRenderer: { invoke: electronMock.invoke },
}));

import { createDesktopApi } from "../src/preload";
import { ipcChannels } from "../src/shared/ipc";

const connection = {
	baseUrl: "http://127.0.0.1:8742",
	token: "test-local-capability-token-000000000000000000",
};

describe("typed preload bridge", () => {
	beforeEach(() => electronMock.invoke.mockReset());

	it("exposes only the declared v1 source and microphone capabilities", () => {
		const desktop = createDesktopApi(vi.fn(), connection);
		expect(Object.keys(desktop)).toEqual(["v1"]);
		expect(Object.keys(desktop.v1)).toEqual([
			"version",
			"connection",
			"sources",
			"microphone",
		]);
		expect(Object.keys(desktop.v1.sources)).toEqual(["chooseAndImport"]);
		expect(Object.keys(desktop.v1.microphone)).toEqual(["requestPermission"]);
		expect("invoke" in desktop.v1).toBe(false);
		expect("filesystem" in desktop.v1).toBe(false);
		expect("shell" in desktop.v1).toBe(false);
		expect(Object.isFrozen(desktop.v1)).toBe(true);
	});

	it("validates project IDs before invoking main", async () => {
		const invoke = vi.fn().mockResolvedValue({ status: "cancelled" });
		const desktop = createDesktopApi(invoke, connection);
		await expect(
			desktop.v1.sources.chooseAndImport("not-a-project-id"),
		).rejects.toThrow();
		expect(invoke).not.toHaveBeenCalled();

		await expect(
			desktop.v1.sources.chooseAndImport(
				"123e4567-e89b-42d3-a456-426614174000",
			),
		).resolves.toEqual({ status: "cancelled" });
		expect(invoke).toHaveBeenCalledWith(
			ipcChannels.chooseAndImportSource,
			"123e4567-e89b-42d3-a456-426614174000",
		);
	});
});
