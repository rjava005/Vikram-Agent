import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

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

vi.mock("../src/renderer/api", () => ({ api: mockApi }));

import App from "../src/renderer/App";

const projectId = "123e4567-e89b-42d3-a456-426614174000";
const answerId = "123e4567-e89b-42d3-a456-426614174001";
const sourceId = "123e4567-e89b-42d3-a456-426614174002";
const evidenceId = "123e4567-e89b-42d3-a456-426614174003";
const citationId = "123e4567-e89b-42d3-a456-426614174004";

function renderApp() {
	const client = new QueryClient({
		defaultOptions: { queries: { retry: false } },
	});
	return render(
		<QueryClientProvider client={client}>
			<App />
		</QueryClientProvider>,
	);
}

describe("reviewable vertical slice UI", () => {
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
		mockApi.listProjects.mockResolvedValue([
			{
				id: projectId,
				name: "Motor controller",
				created_at: "2026-08-07T00:00:00Z",
			},
		]);
		mockApi.workspace.mockResolvedValue({
			project: {
				id: projectId,
				name: "Motor controller",
				created_at: "2026-08-07T00:00:00Z",
			},
			ai_policy: {
				project_id: projectId,
				mode: "local",
				zdr_attested: false,
				revision: 0,
				updated_at: "2026-08-07T00:00:00Z",
			},
			sources: [
				{
					id: sourceId,
					project_id: projectId,
					version_id: "123e4567-e89b-42d3-a456-426614174005",
					name: "control.md",
					kind: "markdown",
					status: "ready",
					evidence_count: 1,
					created_at: "2026-08-07T00:00:00Z",
				},
			],
			tasks: [],
			active_focus: null,
		});
		mockApi.ask.mockResolvedValue({
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
			created_at: "2026-08-07T00:00:00Z",
		});
		mockApi.feedback.mockResolvedValue({
			id: "123e4567-e89b-42d3-a456-426614174006",
			answer_id: answerId,
			status: "understood",
			created_at: "2026-08-07T00:00:00Z",
			updated_at: "2026-08-07T00:00:00Z",
		});
		mockApi.taskFromAnswer.mockResolvedValue({
			id: "123e4567-e89b-42d3-a456-426614174007",
			project_id: projectId,
			source_answer_id: answerId,
			title: "Review phase margin",
			status: "todo",
			created_at: "2026-08-07T00:00:00Z",
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

	it("asks, renders a structured citation, records feedback, and creates a task", async () => {
		renderApp();
		await screen.findByRole("heading", { name: "Motor controller" });
		const input = screen.getByLabelText("Ask about the selected project");
		fireEvent.change(input, { target: { value: "What is phase margin?" } });
		fireEvent.click(screen.getByRole("button", { name: "Ask" }));

		expect(
			await screen.findByText(/The source states: Phase margin/),
		).toBeTruthy();
		expect(screen.getByText("Stability · lines 1–2")).toBeTruthy();
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
});
