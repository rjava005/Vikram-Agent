import type { Source } from "@vikram/contracts";
import { sourceSchema } from "@vikram/contracts";
import { z } from "zod";

export const ipcChannels = {
	chooseAndImportSource: "vikram:v1:sources:choose-and-import",
	requestMicrophonePermission: "vikram:v1:microphone:request-permission",
} as const;

export const projectIdSchema = z.string().uuid();

export const sourceImportResultSchema = z.discriminatedUnion("status", [
	z.object({ status: z.literal("cancelled") }),
	z.object({ status: z.literal("imported"), source: sourceSchema }),
]);

export const microphonePermissionSchema = z.object({
	granted: z.boolean(),
});

export const apiConnectionSchema = z.object({
	baseUrl: z.url().refine((value) => {
		const url = new URL(value);
		return (
			url.protocol === "http:" &&
			(url.hostname === "127.0.0.1" || url.hostname === "localhost") &&
			!url.username &&
			!url.password
		);
	}, "The API must use loopback HTTP."),
	token: z.string().min(43).max(256),
});

export type SourceImportResult =
	| { status: "cancelled" }
	| { status: "imported"; source: Source };

export interface VikramDesktopBridge {
	readonly version: "v1";
	readonly connection: z.infer<typeof apiConnectionSchema>;
	readonly sources: {
		chooseAndImport(projectId: string): Promise<SourceImportResult>;
	};
	readonly microphone: {
		requestPermission(): Promise<{ granted: boolean }>;
	};
}
