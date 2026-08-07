import {
	type Answer,
	answerSchema,
	type FeedbackStatus,
	feedbackSchema,
	type FocusSession,
	focusSchema,
	healthSchema,
	type Project,
	projectSchema,
	problemSchema,
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
	) {
		super(message);
		this.name = "ApiError";
	}
}

async function request<T>(
	path: string,
	schema: z.ZodType<T>,
	init?: RequestInit,
): Promise<T> {
	const controller = new AbortController();
	const timeout = setTimeout(() => controller.abort(), 8_000);
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
			);
		}
		return schema.parse(payload);
	} catch (error) {
		if (error instanceof ApiError) {
			throw error;
		}
		if (error instanceof DOMException && error.name === "AbortError") {
			throw new ApiError("The local service timed out.");
		}
		throw new ApiError(
			"Vikram's local service is offline or returned invalid data.",
		);
	} finally {
		clearTimeout(timeout);
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
	ask: (projectId: string, question: string): Promise<Answer> =>
		request(
			`/api/v1/projects/${encodeURIComponent(projectId)}/answers`,
			answerSchema,
			{
				method: "POST",
				body: JSON.stringify({ question }),
			},
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
