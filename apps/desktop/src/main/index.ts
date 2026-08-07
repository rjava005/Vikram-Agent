import { app, BrowserWindow, session } from "electron";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { validatedApiBase, validatedApiToken } from "./api";
import { ElectronOsCapabilities } from "./capabilities/os";
import { registerIpcHandlers } from "./ipc";
import {
	installPermissionPolicy,
	installWindowSecurity,
	isTrustedRendererUrl,
} from "./security";
import { browserWindowOptions } from "./windowOptions";

let mainWindow: BrowserWindow | null = null;
let removeIpcHandlers: (() => void) | null = null;
let microphoneGrantExpiresAt = 0;

const userDataOverride = process.env.VIKRAM_ELECTRON_DATA_DIR;
if (userDataOverride) app.setPath("userData", resolve(userDataOverride));
if (process.env.VIKRAM_DISABLE_HARDWARE_ACCELERATION === "1") {
	app.disableHardwareAcceleration();
	app.commandLine.appendSwitch("disable-gpu");
	app.commandLine.appendSwitch("disable-gpu-compositing");
}

async function createWindow(rendererUrl: string): Promise<void> {
	mainWindow = new BrowserWindow(
		browserWindowOptions(
			join(__dirname, "../preload/index.js"),
			app.isPackaged,
		),
	);
	installWindowSecurity(mainWindow);
	mainWindow.once("ready-to-show", () => mainWindow?.show());
	mainWindow.on("closed", () => {
		mainWindow = null;
	});

	await mainWindow.loadURL(rendererUrl);
}

app.whenReady().then(async () => {
	const apiBase = validatedApiBase(
		process.env.VIKRAM_API_BASE_URL ?? "http://127.0.0.1:8742",
	);
	const apiToken = validatedApiToken(process.env.VIKRAM_API_TOKEN);
	const packagedRendererPath = join(__dirname, "../renderer/index.html");
	const packagedRendererUrl = pathToFileURL(packagedRendererPath).href;
	const rendererUrl = process.env.ELECTRON_RENDERER_URL ?? packagedRendererUrl;
	if (!isTrustedRendererUrl(rendererUrl, packagedRendererUrl)) {
		throw new Error(
			"ELECTRON_RENDERER_URL is not an allowlisted renderer origin.",
		);
	}
	installPermissionPolicy(
		session.defaultSession,
		() => mainWindow,
		() => rendererUrl,
		() => Date.now() < microphoneGrantExpiresAt,
	);
	removeIpcHandlers = registerIpcHandlers({
		getWindow: () => mainWindow,
		trustedRendererUrl: rendererUrl,
		os: new ElectronOsCapabilities(),
		apiBase,
		apiToken,
		allowMicrophoneForFiveSeconds: () => {
			microphoneGrantExpiresAt = Date.now() + 5_000;
		},
	});
	await createWindow(rendererUrl);
	app.on("activate", async () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			await createWindow(rendererUrl);
		}
	});
});

app.on("window-all-closed", () => {
	if (process.platform !== "darwin") {
		app.quit();
	}
});

app.on("before-quit", () => removeIpcHandlers?.());
