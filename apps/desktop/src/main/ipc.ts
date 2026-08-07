import { type BrowserWindow, ipcMain } from "electron";
import {
	microphonePermissionSchema,
	ipcChannels,
	projectIdSchema,
} from "../shared/ipc";
import { uploadSource } from "./api";
import type { OsCapabilities } from "./capabilities/os";
import { assertTrustedSender } from "./security";

export function registerIpcHandlers(input: {
	getWindow: () => BrowserWindow | null;
	trustedRendererUrl: string;
	os: OsCapabilities;
	apiBase: string;
	apiToken: string;
	allowMicrophoneForFiveSeconds: () => void;
}): () => void {
	ipcMain.handle(
		ipcChannels.chooseAndImportSource,
		async (event, rawProjectId: unknown) => {
			const window = input.getWindow();
			if (!window) {
				throw new Error("The desktop window is not available.");
			}
			assertTrustedSender(event, window, input.trustedRendererUrl);
			const projectId = projectIdSchema.parse(rawProjectId);
			const selection = await input.os.chooseEngineeringSource(window);
			if (selection.status === "cancelled") {
				return { status: "cancelled" } as const;
			}
			const source = await uploadSource({
				apiBase: input.apiBase,
				apiToken: input.apiToken,
				projectId,
				displayName: selection.displayName,
				mediaType: selection.mediaType,
				bytes: selection.bytes,
			});
			return { status: "imported", source } as const;
		},
	);

	ipcMain.handle(ipcChannels.requestMicrophonePermission, async (event) => {
		const window = input.getWindow();
		if (!window) {
			throw new Error("The desktop window is not available.");
		}
		assertTrustedSender(event, window, input.trustedRendererUrl);
		const granted = await input.os.requestMicrophoneAccess();
		if (granted) {
			input.allowMicrophoneForFiveSeconds();
		}
		return microphonePermissionSchema.parse({ granted });
	});

	return () => {
		ipcMain.removeHandler(ipcChannels.chooseAndImportSource);
		ipcMain.removeHandler(ipcChannels.requestMicrophonePermission);
	};
}
