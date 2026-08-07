import { type Source, sourceSchema } from "@vikram/contracts";

const allowedApiHosts = new Set(["127.0.0.1", "localhost"]);

export function validatedApiBase(value: string): string {
	const url = new URL(value);
	if (
		url.protocol !== "http:" ||
		!allowedApiHosts.has(url.hostname) ||
		url.username ||
		url.password
	) {
		throw new Error("The API must be a loopback HTTP origin.");
	}
	return url.origin;
}

export function validatedApiToken(value: string | undefined): string {
	if (!value || value.length < 43 || value.length > 256) {
		throw new Error(
			"VIKRAM_API_TOKEN must be a high-entropy local capability.",
		);
	}
	return value;
}

export async function uploadSource(input: {
	apiBase: string;
	apiToken: string;
	projectId: string;
	displayName: string;
	mediaType: "application/pdf" | "text/markdown";
	bytes: Uint8Array;
	timeoutMs?: number;
}): Promise<Source> {
	const form = new FormData();
	const uploadBuffer = new ArrayBuffer(input.bytes.byteLength);
	new Uint8Array(uploadBuffer).set(input.bytes);
	form.append(
		"file",
		new Blob([uploadBuffer], { type: input.mediaType }),
		input.displayName,
	);
	form.append("display_name", input.displayName);
	const controller = new AbortController();
	const timeout = setTimeout(
		() => controller.abort(),
		input.timeoutMs ?? 10_000,
	);
	try {
		const response = await fetch(
			`${validatedApiBase(input.apiBase)}/api/v1/projects/${encodeURIComponent(input.projectId)}/sources`,
			{
				method: "POST",
				body: form,
				headers: { "X-Vikram-Token": input.apiToken },
				signal: controller.signal,
			},
		);
		const payload: unknown = await response.json();
		if (!response.ok) {
			throw new Error("The local API rejected the selected source.");
		}
		return sourceSchema.parse(payload);
	} finally {
		clearTimeout(timeout);
	}
}
