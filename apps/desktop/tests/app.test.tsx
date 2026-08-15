import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	cleanup,
	fireEvent,
	render,
	screen,
	waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockApi = vi.hoisted(() => ({
	health: vi.fn(),
	listProjects: vi.fn(),
	createProject: vi.fn(),
	workspace: vi.fn(),
	ask: vi.fn(),
	feedback: vi.fn(),
	taskFromAnswer: vi.fn(),
	startFocus: vi.fn(),
	transitionFocus: vi.fn(),
	updateAiPolicy: vi.fn(),
}));

const MockApiError = vi.hoisted(
	() =>
		class ApiError extends Error {
			constructor(
				message: string,
				readonly status?: number,
				readonly code = "unknown",
				readonly retryable = false,
			) {
				super(message);
				this.name = "ApiError";
			}
		},
);

vi.mock("../src/renderer/api", () => ({
	api: mockApi,
	ApiError: MockApiError,
}));

import App from "../src/renderer/App";

const projectId = "123e4567-e89b-42d3-a456-426614174000";
const answerId = "123e4567-e89b-42d3-a456-426614174001";
const sourceId = "123e4567-e89b-42d3-a456-426614174002";
const evidenceId = "123e4567-e89b-42d3-a456-426614174003";
const citationId = "123e4567-e89b-42d3-a456-426614174004";
const timestamp = "2026-08-07T00:00:00Z";

const localPolicy = {
	project_id: projectId,
	mode: "local",
	zdr_attested: false,
	revision: 0,
	updated_at: timestamp,
};

const remotePolicy = {
	project_id: projectId,
	mode: "nebius",
	zdr_attested: true,
	revision: 1,
	updated_at: timestamp,
};

const localWorkspace = {
	project: {
		id: projectId,
		name: "Motor controller",
		created_at: timestamp,
	},
	ai_policy: localPolicy,
	sources: [
		{
			id: sourceId,
			project_id: projectId,
			version_id: "123e4567-e89b-42d3-a456-426614174005",
			name: "control.md",
			kind: "markdown",
			status: "ready",
			evidence_count: 1,
			created_at: timestamp,
		},
	],
	tasks: [],
	active_focus: null,
};

const localAnswer = {
	id: answerId,
	project_id: projectId,
	question: "What is phase margin?",
	text: "The source states: Phase margin measures distance from instability.",
	grounding: "grounded",
	claims: [
		{
			id: "claim-1",
			text: "Phase margin measures distance from instability.",
			evidence_ids: [evidenceId],
		},
	],
	citations: [
		{
			id: citationId,
			evidence_id: evidenceId,
			source_id: sourceId,
			source_version_id: "123e4567-e89b-42d3-a456-426614174005",
			source_name: "control.md",
			locator: {
				kind: "markdown_section",
				heading: "Stability",
				line_start: 1,
				line_end: 2,
			},
			excerpt: "Phase margin measures distance from instability.",
			supported_claim_ids: ["claim-1"],
		},
	],
	provider_id: "fake-extractive-model-v1",
	prompt_version: "grounded-answer-v1",
	provenance: {
		provider_mode: "fake",
		verification: "local_deterministic",
		model_id: "fake-extractive-model-v1",
		embedding_model_id: "fake-hash-embedding-v1",
		retrieval_strategy: "fake-hybrid-retrieval-v1",
		verifier_model_id: null,
		verifier_prompt_version: null,
		candidate_count: 1,
		selected_evidence_count: 1,
		generation_latency_ms: null,
		verification_latency_ms: null,
	},
	created_at: timestamp,
};

function renderApp() {
	const client = new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});
	return render(
		<QueryClientProvider client={client}>
			<App />
		</QueryClientProvider>,
	);
}

function useRemoteWorkspace() {
	mockApi.health.mockResolvedValue({
		status: "ok",
		api_version: "v1",
		provider_mode: "nebius",
		persistence: "sqlite",
		ai_runtime: {
			provider_mode: "nebius",
			remote_configured: true,
			generation_model: "server-selected-generation-model",
			embedding_model: "server-selected-embedding-model",
		},
	});
	mockApi.workspace.mockResolvedValue({
		...localWorkspace,
		ai_policy: remotePolicy,
	});
}

function askQuestion() {
	const input = screen.getByLabelText("Ask about the selected project");
	fireEvent.change(input, { target: { value: "What is phase margin?" } });
	fireEvent.click(screen.getByRole("button", { name: "Ask" }));
}

describe("reviewable vertical slice UI", () => {
	afterEach(cleanup);

	beforeEach(() => {
		Object.values(mockApi).forEach((mock) => {
			mock.mockReset();
		});
		mockApi.health.mockResolvedValue({
			status: "ok",
			api_version: "v1",
			provider_mode: "fake",
			persistence: "sqlite",
			ai_runtime: {
				provider_mode: "fake",
				remote_configured: false,
				generation_model: "fake-extractive-model-v1",
				embedding_model: "fake-hash-embedding-v1",
			},
		});
		mockApi.listProjects.mockResolvedValue([localWorkspace.project]);
		mockApi.workspace.mockResolvedValue(localWorkspace);
		mockApi.ask.mockResolvedValue(localAnswer);
		mockApi.feedback.mockResolvedValue({
			id: "123e4567-e89b-42d3-a456-426614174006",
			answer_id: answerId,
			status: "understood",
			created_at: timestamp,
			updated_at: timestamp,
		});
		mockApi.taskFromAnswer.mockResolvedValue({
			id: "123e4567-e89b-42d3-a456-426614174007",
			project_id: projectId,
			source_answer_id: answerId,
			title: "Review phase margin",
			status: "todo",
			created_at: timestamp,
			completed_at: null,
		});
		Object.defineProperty(window, "vikramDesktop", {
			configurable: true,
			value: {
				v1: {
					version: "v1",
					sources: { chooseAndImport: vi.fn() },
					microphone: { requestPermission: vi.fn() },
				},
			},
		});
	});

	it("keeps the complete deterministic local answer flow available", async () => {
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		expect(screen.getAllByText("Local deterministic").length).toBeGreaterThan(
			0,
		);
		askQuestion();

		expect(
			await screen.findByText(/The source states: Phase margin/),
		).toBeTruthy();
		expect(screen.getByText("Stability · lines 1–2")).toBeTruthy();
		expect(screen.queryByText("Remote verified")).toBeNull();
		expect(mockApi.ask).toHaveBeenCalledWith(
			projectId,
			"What is phase margin?",
			expect.objectContaining({ aborted: false }),
		);
		fireEvent.click(screen.getByLabelText("Understood"));
		await waitFor(() =>
			expect(mockApi.feedback).toHaveBeenCalledWith(answerId, "understood"),
		);
		fireEvent.click(
			screen.getByRole("button", { name: "Turn answer into a task" }),
		);
		await waitFor(() =>
			expect(mockApi.taskFromAnswer).toHaveBeenCalledWith(answerId),
		);
	});

	it("blocks remote opt-in until the user explicitly attests ZDR", async () => {
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		fireEvent.click(
			screen.getByRole("button", { name: /Local deterministic/ }),
		);

		expect(
			screen.getByText(/bounded source evidence units.*semantic embedding/i),
		).toBeTruthy();
		expect(
			screen.getByText(/at most four selected source excerpts/i),
		).toBeTruthy();
		fireEvent.click(
			screen.getByRole("button", { name: "Enable Nebius remote AI" }),
		);

		expect((await screen.findByRole("alert")).textContent).toMatch(
			/must attest that Zero Data Retention is enabled/i,
		);
		expect(mockApi.updateAiPolicy).not.toHaveBeenCalled();
		fireEvent.keyDown(document, { key: "Escape" });
		expect(screen.queryByRole("dialog")).toBeNull();
	});

	it("explains unavailable remote configuration without requesting credentials", async () => {
		mockApi.updateAiPolicy.mockRejectedValue(
			new MockApiError(
				"Remote AI is not configured",
				409,
				"provider_not_configured",
			),
		);
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		fireEvent.click(
			screen.getByRole("button", { name: /Local deterministic/ }),
		);
		fireEvent.click(
			screen.getByRole("checkbox", { name: /Zero Data Retention/ }),
		);
		fireEvent.click(
			screen.getByRole("button", { name: "Enable Nebius remote AI" }),
		);

		expect((await screen.findByRole("alert")).textContent).toMatch(
			/not configured in the local API.*workspace administrator.*try again/i,
		);
		expect(screen.getByRole("dialog")).toBeTruthy();
		expect(
			screen.queryByText(/API key|provider URL|choose a model/i),
		).toBeNull();
	});

	it("opts a project into remote AI and revokes it with policy revisions", async () => {
		mockApi.health.mockResolvedValue({
			status: "ok",
			api_version: "v1",
			provider_mode: "nebius",
			persistence: "sqlite",
			ai_runtime: {
				provider_mode: "nebius",
				remote_configured: true,
				generation_model: "server-selected-generation-model",
				embedding_model: "server-selected-embedding-model",
			},
		});
		mockApi.updateAiPolicy
			.mockResolvedValueOnce(remotePolicy)
			.mockResolvedValueOnce({
				...localPolicy,
				revision: 2,
			});
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });

		fireEvent.click(
			screen.getByRole("button", { name: /Local deterministic/ }),
		);
		fireEvent.click(
			screen.getByRole("checkbox", { name: /Zero Data Retention/ }),
		);
		fireEvent.click(
			screen.getByRole("button", { name: "Enable Nebius remote AI" }),
		);

		await waitFor(() =>
			expect(mockApi.updateAiPolicy).toHaveBeenCalledWith(
				projectId,
				"nebius",
				true,
				0,
			),
		);
		expect(
			await screen.findByText("Nebius remote · ZDR attested"),
		).toBeTruthy();

		fireEvent.click(screen.getByRole("button", { name: /Nebius remote/ }));
		fireEvent.click(screen.getByRole("button", { name: "Use local AI" }));

		await waitFor(() =>
			expect(mockApi.updateAiPolicy).toHaveBeenLastCalledWith(
				projectId,
				"local",
				false,
				1,
			),
		);
		await waitFor(() =>
			expect(screen.getAllByText("Local deterministic").length).toBeGreaterThan(
				0,
			),
		);
	});

	it("turns a classified provider outage into an actionable remote error", async () => {
		useRemoteWorkspace();
		mockApi.ask.mockRejectedValue(
			new MockApiError(
				"Upstream unavailable",
				503,
				"provider_unavailable",
				true,
			),
		);
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		askQuestion();

		expect((await screen.findByRole("alert")).textContent).toMatch(
			/Nebius is temporarily unavailable. No answer was saved; try again/i,
		);
	});

	it("shows remote answer stages and cancels the in-flight request", async () => {
		useRemoteWorkspace();
		let requestSignal: AbortSignal | undefined;
		mockApi.ask.mockImplementation(
			(_project: string, _question: string, signal: AbortSignal) => {
				requestSignal = signal;
				return new Promise((_resolve, reject) => {
					signal.addEventListener(
						"abort",
						() =>
							reject(
								new MockApiError("Cancelled", undefined, "request_cancelled"),
							),
						{ once: true },
					);
				});
			},
		);
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		askQuestion();

		expect(await screen.findByText("Remote answer in progress")).toBeTruthy();
		expect(
			screen.getByText(
				"Local retrieval → remote generation → remote verification",
			),
		).toBeTruthy();
		fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

		await waitFor(() => expect(requestSignal?.aborted).toBe(true));
		expect(
			await screen.findByText("Answer request cancelled. No answer was saved."),
		).toBeTruthy();
	});

	it("labels only verified remote answers with the remote verification badge", async () => {
		useRemoteWorkspace();
		mockApi.ask.mockResolvedValue({
			...localAnswer,
			provider_id: "server-selected-generation-model",
			provenance: {
				...localAnswer.provenance,
				provider_mode: "nebius",
				verification: "remote_verified",
				verifier_model_id: "server-selected-verifier-model",
				verifier_prompt_version: "grounding-verifier-v1",
			},
		});
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		askQuestion();

		expect(await screen.findByText("Remote verified")).toBeTruthy();
		expect(screen.getByText("Grounded in your source")).toBeTruthy();
		expect(screen.queryByText("server-selected-generation-model")).toBeNull();
	});
});
