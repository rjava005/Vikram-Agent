export function browserWindowOptions(
	preloadPath: string,
	isPackaged: boolean,
): Electron.BrowserWindowConstructorOptions {
	return {
		width: 1480,
		height: 920,
		minWidth: 1040,
		minHeight: 720,
		backgroundColor: "#070a12",
		show: false,
		webPreferences: {
			preload: preloadPath,
			nodeIntegration: false,
			contextIsolation: true,
			sandbox: true,
			webSecurity: true,
			allowRunningInsecureContent: false,
			devTools: !isPackaged,
		},
	};
}
