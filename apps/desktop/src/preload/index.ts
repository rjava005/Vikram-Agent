import { contextBridge, ipcRenderer } from "electron";
import {
	apiConnectionSchema,
	ipcChannels,
	microphonePermissionSchema,
	projectIdSchema,
	sourceImportResultSchema,
	type VikramDesktopBridge,
} from "../shared/ipc";

export type Invoke = (
	channel: string,
	...args: readonly unknown[]
) => Promise<unknown>;

export function createBridge(
	invoke: Invoke,
	connection: unknown,
): VikramDesktopBridge {
	return Object.freeze({
		version: "v1" as const,
		connection: Object.freeze(apiConnectionSchema.parse(connection)),
		sources: Object.freeze({
			chooseAndImport: async (projectId: string) => {
				const validProjectId = projectIdSchema.parse(projectId);
				return sourceImportResultSchema.parse(
					await invoke(ipcChannels.chooseAndImportSource, validProjectId),
				);
			},
		}),
		microphone: Object.freeze({
			requestPermission: async () =>
				microphonePermissionSchema.parse(
					await invoke(ipcChannels.requestMicrophonePermission),
				),
		}),
	});
}

export function createDesktopApi(
	invoke: Invoke,
	connection: unknown,
): {
	readonly v1: VikramDesktopBridge;
} {
	return Object.freeze({ v1: createBridge(invoke, connection) });
}

contextBridge.exposeInMainWorld(
	"vikramDesktop",
	createDesktopApi((channel, ...args) => ipcRenderer.invoke(channel, ...args), {
		baseUrl: process.env.VIKRAM_API_BASE_URL ?? "http://127.0.0.1:8742",
		token: process.env.VIKRAM_API_TOKEN,
	}),
);
