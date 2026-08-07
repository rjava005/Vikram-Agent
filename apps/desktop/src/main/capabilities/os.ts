import { dialog, type BrowserWindow, systemPreferences } from "electron";
import { readFile, stat } from "node:fs/promises";
import { basename, extname } from "node:path";

export type SelectedSource =
	| { status: "cancelled" }
	| {
			status: "selected";
			displayName: string;
			mediaType: "application/pdf" | "text/markdown";
			bytes: Uint8Array;
	  };

export interface OsCapabilities {
	chooseEngineeringSource(owner: BrowserWindow): Promise<SelectedSource>;
	requestMicrophoneAccess(): Promise<boolean>;
}

export class ElectronOsCapabilities implements OsCapabilities {
	static readonly maxBytes = 10 * 1024 * 1024;

	async chooseEngineeringSource(owner: BrowserWindow): Promise<SelectedSource> {
		const selection = await dialog.showOpenDialog(owner, {
			title: "Import an engineering source",
			buttonLabel: "Import source",
			properties: ["openFile"],
			filters: [{ name: "Engineering sources", extensions: ["pdf", "md"] }],
		});
		const selectedPath = selection.filePaths[0];
		if (selection.canceled || !selectedPath) {
			return { status: "cancelled" };
		}
		const extension = extname(selectedPath).toLowerCase();
		if (extension !== ".pdf" && extension !== ".md") {
			throw new Error("Only PDF and Markdown sources are supported.");
		}
		const metadata = await stat(selectedPath);
		if (!metadata.isFile() || metadata.size > ElectronOsCapabilities.maxBytes) {
			throw new Error(
				"The selected source must be a file no larger than 10 MB.",
			);
		}
		const bytes = await readFile(selectedPath);
		if (
			extension === ".pdf" &&
			!bytes.subarray(0, 5).equals(Buffer.from("%PDF-"))
		) {
			throw new Error("The selected file is not a valid PDF.");
		}
		if (extension === ".md") {
			new TextDecoder("utf-8", { fatal: true }).decode(bytes);
		}
		return {
			status: "selected",
			displayName: basename(selectedPath),
			mediaType: extension === ".pdf" ? "application/pdf" : "text/markdown",
			bytes,
		};
	}

	async requestMicrophoneAccess(): Promise<boolean> {
		if (process.platform === "darwin") {
			return systemPreferences.askForMediaAccess("microphone");
		}
		return true;
	}
}
