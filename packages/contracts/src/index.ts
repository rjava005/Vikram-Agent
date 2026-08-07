import { z } from "zod";

export const apiVersion = "v1" as const;

export const projectSchema = z.object({
	id: z.string().uuid(),
	name: z.string().min(1).max(120),
	created_at: z.string().datetime(),
});

export const sourceSchema = z.object({
	id: z.string().uuid(),
	project_id: z.string().uuid(),
	version_id: z.string().uuid(),
	name: z.string().min(1),
	kind: z.enum(["pdf", "markdown"]),
	status: z.enum(["ready", "failed"]),
	evidence_count: z.number().int().nonnegative(),
	created_at: z.string().datetime(),
});

export const pdfLocatorSchema = z.object({
	kind: z.literal("pdf_page"),
	page: z.number().int().positive(),
});

export const markdownLocatorSchema = z.object({
	kind: z.literal("markdown_section"),
	heading: z.string(),
	line_start: z.number().int().positive(),
	line_end: z.number().int().positive(),
});

export const evidenceLocatorSchema = z.discriminatedUnion("kind", [
	pdfLocatorSchema,
	markdownLocatorSchema,
]);

export const citationSchema = z.object({
	id: z.string().uuid(),
	evidence_id: z.string().uuid(),
	source_id: z.string().uuid(),
	source_version_id: z.string().uuid(),
	source_name: z.string(),
	locator: evidenceLocatorSchema,
	excerpt: z.string(),
	supported_claim_ids: z.array(z.string()),
});

export const answerSchema = z.object({
	id: z.string().uuid(),
	project_id: z.string().uuid(),
	question: z.string(),
	text: z.string(),
	grounding: z.enum(["grounded", "insufficient_evidence"]),
	claims: z.array(
		z.object({
			id: z.string(),
			text: z.string(),
			evidence_ids: z.array(z.string().uuid()),
		}),
	),
	citations: z.array(citationSchema),
	provider_id: z.string(),
	prompt_version: z.string(),
	created_at: z.string().datetime(),
});

export const feedbackStatusSchema = z.enum([
	"understood",
	"unclear",
	"review_later",
]);

export const feedbackSchema = z.object({
	id: z.string().uuid(),
	answer_id: z.string().uuid(),
	status: feedbackStatusSchema,
	created_at: z.string().datetime(),
	updated_at: z.string().datetime(),
});

export const taskSchema = z.object({
	id: z.string().uuid(),
	project_id: z.string().uuid(),
	source_answer_id: z.string().uuid().nullable(),
	title: z.string(),
	status: z.enum(["todo", "in_progress", "completed"]),
	created_at: z.string().datetime(),
	completed_at: z.string().datetime().nullable(),
});

export const focusSchema = z.object({
	id: z.string().uuid(),
	task_id: z.string().uuid(),
	status: z.enum(["active", "paused", "completed"]),
	duration_seconds: z.number().int().positive(),
	elapsed_active_seconds: z.number().int().nonnegative(),
	remaining_seconds: z.number().int().nonnegative(),
	current_segment_started_at: z.string().datetime().nullable(),
	revision: z.number().int().nonnegative(),
	created_at: z.string().datetime(),
	completed_at: z.string().datetime().nullable(),
});

export const workspaceSchema = z.object({
	project: projectSchema,
	sources: z.array(sourceSchema),
	tasks: z.array(taskSchema),
	active_focus: focusSchema.nullable(),
});

export const healthSchema = z.object({
	status: z.literal("ok"),
	api_version: z.literal("v1"),
	provider_mode: z.string(),
	persistence: z.literal("sqlite"),
});

export const problemSchema = z.object({
	type: z.string(),
	title: z.string(),
	status: z.number().int(),
	detail: z.string(),
});

export type Project = z.infer<typeof projectSchema>;
export type Source = z.infer<typeof sourceSchema>;
export type Citation = z.infer<typeof citationSchema>;
export type Answer = z.infer<typeof answerSchema>;
export type FeedbackStatus = z.infer<typeof feedbackStatusSchema>;
export type Task = z.infer<typeof taskSchema>;
export type FocusSession = z.infer<typeof focusSchema>;
export type Workspace = z.infer<typeof workspaceSchema>;
export type Health = z.infer<typeof healthSchema>;
