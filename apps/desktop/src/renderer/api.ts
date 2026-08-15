import {
	type AiMode,
	type AiPolicy,
	type Answer,
	aiPolicySchema,
	answerSchema,
	type FeedbackStatus,
	type FocusSession,
	feedbackSchema,
	focusSchema,
	healthSchema,
	type Project,
	problemSchema,
	projectSchema,
	type Task,
	taskSchema,
	type Workspace,
	workspaceSchema,
} from "@vikram/contracts";
import { z } from "zod";

export class ApiError extends Error {
	constructor(
		message: string,
		readonly status?: number,
		readonly code = "unknown",
		readonly retryable = false,
	) {
		super(message);
		this.name = "ApiError";
	}
}

async function request<T>(
	path: string,
	schema: z.ZodType<T>,
	init?: RequestInit,
	timeoutMs = 8_000,
): Promise<T> {
	const controller = new AbortController();
	const callerSignal = init?.signal;
	let timedOut = false;
	const abortFromCaller = () => controller.abort();
	if (callerSignal?.aborted) {
		controller.abort();
	} else {
		callerSignal?.addEventListener("abort", abortFromCaller, { once: true });
	}
	const timeout = setTimeout(() => {
		timedOut = true;
		controller.abort();
	}, timeoutMs);
	try {
		const connection = window.vikramDesktop.v1.connection;
		const response = await fetch(`${connection.baseUrl}${path}`, {
			...init,
			headers: {
				"X-Vikram-Token": connection.token,
				...(init?.body ? { "Content-Type": "application/json" } : {}),
				...init?.headers,
			},
			signal: controller.signal,
		});
		const payload: unknown = await response.json();
		if (!response.ok) {
			const problem = problemSchema.safeParse(payload);
			throw new ApiError(
				problem.success
					? problem.data.detail
					: "The local service rejected the request.",
				response.status,
				problem.success ? problem.data.code : "invalid_problem",
				problem.success ? problem.data.retryable : false,
			);
		}
		return schema.parse(payload);
	} catch (error) {
		if (error instanceof ApiError) {
			throw error;
		}
		if (controller.signal.aborted) {
			if (callerSignal?.aborted && !timedOut) {
				throw new ApiError(
					"The answer request was cancelled.",
					undefined,
					"request_cancelled",
				);
			}
			throw new ApiError(
				"The local service timed out.",
				undefined,
				"request_timeout",
				true,
			);
		}
		throw new ApiError(
			"Vikram's local service is offline or returned invalid data.",
		);
	} finally {
		clearTimeout(timeout);
		callerSignal?.removeEventListener("abort", abortFromCaller);
	}
}

export const api = {
	health: () => request("/health", healthSchema),
	listProjects: (): Promise<Project[]> =>
		request("/api/v1/projects", z.array(projectSchema)),
	createProject: (name: string): Promise<Project> =>
		request("/api/v1/projects", projectSchema, {
			method: "POST",
			body: JSON.stringify({ name }),
		}),
	workspace: (projectId: string): Promise<Workspace> =>
		request(
			`/api/v1/projects/${encodeURIComponent(projectId)}`,
			workspaceSchema,
		),
	updateAiPolicy: (
		projectId: string,
		mode: AiMode,
		zdrAttested: boolean,
		expectedRevision: number,
	): Promise<AiPolicy> =>
		request(
			`/api/v1/projects/${encodeURIComponent(projectId)}/ai-policy`,
			aiPolicySchema,
			{
				method: "PUT",
				body: JSON.stringify({
					mode,
					zdr_attested: zdrAttested,
					expected_revision: expectedRevision,
				}),
			},
		),
	ask: (
		projectId: string,
		question: string,
		signal?: AbortSignal,
	): Promise<Answer> =>
		request(
			`/api/v1/projects/${encodeURIComponent(projectId)}/answers`,
			answerSchema,
			{
				method: "POST",
				body: JSON.stringify({ question }),
				signal,
			},
			60_000,
		),
	feedback: (answerId: string, status: FeedbackStatus) =>
		request(
			`/api/v1/answers/${encodeURIComponent(answerId)}/feedback`,
			feedbackSchema,
			{
				method: "PUT",
				body: JSON.stringify({ status }),
			},
		),
	taskFromAnswer: (answerId: string): Promise<Task> =>
		request(
			`/api/v1/answers/${encodeURIComponent(answerId)}/tasks`,
			taskSchema,
			{
				method: "POST",
				body: JSON.stringify({}),
			},
		),
	startFocus: (taskId: string): Promise<FocusSession> =>
		request(
			`/api/v1/tasks/${encodeURIComponent(taskId)}/focus-sessions`,
			focusSchema,
			{
				method: "POST",
				body: JSON.stringify({ duration_minutes: 25 }),
			},
		),
	transitionFocus: (
		focusId: string,
		transition: "pause" | "resume" | "complete",
		expectedRevision: number,
	): Promise<FocusSession> =>
		request(
			`/api/v1/focus-sessions/${encodeURIComponent(focusId)}/transitions`,
			focusSchema,
			{
				method: "POST",
				body: JSON.stringify({
					transition,
					expected_revision: expectedRevision,
				}),
			},
		),
};
