import type { BrowserWindow, IpcMainInvokeEvent, Session } from "electron";

export function isTrustedRendererUrl(
	value: string,
	trustedFileUrl?: string,
): boolean {
	try {
		const url = new URL(value);
		if (url.protocol === "file:") {
			return (
				trustedFileUrl !== undefined &&
				url.href === new URL(trustedFileUrl).href
			);
		}
		return (
			url.protocol === "http:" &&
			(url.hostname === "localhost" || url.hostname === "127.0.0.1") &&
			url.port === "5173"
		);
	} catch {
		return false;
	}
}

export function assertTrustedSender(
	event: IpcMainInvokeEvent,
	window: BrowserWindow,
	trustedRendererUrl: string,
): void {
	const currentUrl = window.webContents.getURL();
	const senderFrame = event.senderFrame;
	if (
		event.sender.id !== window.webContents.id ||
		!senderFrame ||
		senderFrame.url !== currentUrl ||
		!isTrustedRendererUrl(currentUrl, trustedRendererUrl)
	) {
		throw new Error("Rejected an untrusted desktop capability request.");
	}
}

export function installWindowSecurity(window: BrowserWindow): void {
	window.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
	window.webContents.on("will-navigate", (event, navigationUrl) => {
		if (navigationUrl !== window.webContents.getURL()) {
			event.preventDefault();
		}
	});
	window.webContents.on("will-attach-webview", (event) =>
		event.preventDefault(),
	);
}

export function installPermissionPolicy(
	electronSession: Session,
	getWindow: () => BrowserWindow | null,
	getTrustedRendererUrl: () => string,
	mayUseMicrophone: () => boolean,
): void {
	electronSession.setPermissionCheckHandler(
		(webContents, permission, requestingOrigin, details) => {
			const window = getWindow();
			return (
				Boolean(window) &&
				webContents !== null &&
				webContents.id === window?.webContents.id &&
				permission === "media" &&
				details.mediaType === "audio" &&
				mayUseMicrophone() &&
				isTrustedRendererUrl(requestingOrigin, getTrustedRendererUrl()) &&
				isTrustedRendererUrl(webContents.getURL(), getTrustedRendererUrl())
			);
		},
	);
	electronSession.setPermissionRequestHandler(
		(webContents, permission, callback, details) => {
			const window = getWindow();
			const mediaTypes =
				("mediaTypes" in details ? details.mediaTypes : []) ?? [];
			const isAudioOnly =
				mediaTypes.length > 0 && mediaTypes.every((type) => type === "audio");
			const allowed =
				Boolean(window) &&
				webContents.id === window?.webContents.id &&
				permission === "media" &&
				isAudioOnly &&
				mayUseMicrophone() &&
				isTrustedRendererUrl(webContents.getURL(), getTrustedRendererUrl());
			callback(allowed);
		},
	);
}
