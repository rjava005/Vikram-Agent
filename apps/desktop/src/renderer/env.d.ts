/// <reference types="vite/client" />

import type { VikramDesktopBridge } from "../shared/ipc";

declare global {
	interface Window {
		readonly vikramDesktop: { readonly v1: VikramDesktopBridge };
	}
}
