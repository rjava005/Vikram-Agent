import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
	Answer,
	Citation,
	FeedbackStatus,
	FocusSession,
	Project,
	Task,
	Workspace,
} from "@vikram/contracts";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, api } from "./api";
import { type RecordingState, useWorkspaceStore } from "./store";

export function locatorLabel(citation: Citation): string {
	return citation.locator.kind === "pdf_page"
		? `Page ${citation.locator.page}`
		: `${citation.locator.heading} · lines ${citation.locator.line_start}–${citation.locator.line_end}`;
}

function ProjectRail(props: {
	projects: Project[];
	selectedId: string | null;
	onSelect: (id: string) => void;
	onCreate: () => void;
}) {
	return (
		<aside className="project-rail panel" aria-label="Project navigation">
			<button
				className="new-project-button"
				type="button"
				onClick={props.onCreate}
			>
				<span aria-hidden="true">＋</span>
				<span>New project</span>
			</button>
			<div className="rail-heading">
				<span>Projects</span>
				<span className="count-badge">{props.projects.length}</span>
			</div>
			<nav aria-label="Engineering projects">
				{props.projects.length === 0 ? (
					<p className="muted empty-copy">
						Your active engineering work will live here.
					</p>
				) : (
					<ul className="project-list">
						{props.projects.map((project) => (
							<li key={project.id}>
								<button
									type="button"
									className={
										project.id === props.selectedId
											? "project-item selected"
											: "project-item"
									}
									onClick={() => props.onSelect(project.id)}
									aria-current={
										project.id === props.selectedId ? "page" : undefined
									}
								>
									<span className="project-orbit" aria-hidden="true" />
									<span>{project.name}</span>
								</button>
							</li>
						))}
					</ul>
				)}
			</nav>
			<div className="rail-footer muted">
				<span className="privacy-dot" aria-hidden="true" /> Project storage
				local
			</div>
		</aside>
	);
}

function CitationCard({ citation }: { citation: Citation }) {
	return (
		<details className="citation-card">
			<summary>
				<span className="citation-number" aria-hidden="true">
					↗
				</span>
				<span>
					<strong>{citation.source_name}</strong>
					<small>{locatorLabel(citation)}</small>
				</span>
			</summary>
			<p>“{citation.excerpt}”</p>
			<small className="muted">
				Evidence {citation.evidence_id.slice(0, 8)}
			</small>
		</details>
	);
}

function AnswerPanel(props: {
	answer: Answer;
	feedback: FeedbackStatus | null;
	feedbackPending: boolean;
	taskPending: boolean;
	onFeedback: (value: FeedbackStatus) => void;
	onCreateTask: () => void;
}) {
	return (
		<section className="answer-panel" aria-labelledby="answer-title">
			<div className="answer-status-row">
				<div className="answer-kicker">
					<span className="grounded-mark" aria-hidden="true">
						✓
					</span>
					<span>
						{props.answer.grounding === "grounded"
							? "Grounded in your source"
							: "Evidence is insufficient"}
					</span>
				</div>
				{props.answer.provenance.verification === "remote_verified" && (
					<span className="verified-badge">Remote verified</span>
				)}
			</div>
			<h2 id="answer-title">Vikram’s answer</h2>
			<p className="answer-text">{props.answer.text}</p>
			<section className="citation-grid" aria-label="Answer citations">
				{props.answer.citations.map((citation) => (
					<CitationCard key={citation.id} citation={citation} />
				))}
			</section>
			<fieldset className="feedback-fieldset" disabled={props.feedbackPending}>
				<legend>How did this explanation land?</legend>
				{(["understood", "unclear", "review_later"] as const).map((value) => (
					<label
						key={value}
						className={
							props.feedback === value
								? "feedback-chip active"
								: "feedback-chip"
						}
					>
						<input
							type="radio"
							name="learning-feedback"
							value={value}
							checked={props.feedback === value}
							onChange={() => props.onFeedback(value)}
						/>
						{value === "review_later"
							? "Review later"
							: value[0]?.toUpperCase() + value.slice(1)}
					</label>
				))}
			</fieldset>
			<button
				className="secondary-button task-action"
				type="button"
				onClick={props.onCreateTask}
				disabled={props.taskPending}
			>
				{props.taskPending ? "Creating task…" : "Turn answer into a task"}
			</button>
		</section>
	);
}

function EngineeringWorkspace(props: {
	workspace?: Workspace;
	loading: boolean;
	remoteConfigured: boolean;
	answer: Answer | null;
	feedback: FeedbackStatus | null;
	feedbackPending: boolean;
	taskPending: boolean;
	importPending: boolean;
	onImport: () => void;
	onConfigureAi: () => void;
	onFeedback: (value: FeedbackStatus) => void;
	onCreateTask: () => void;
}) {
	if (props.loading) {
		return (
			<main
				id="workspace"
				className="engineering-workspace panel loading-state"
				aria-busy="true"
			>
				Loading project evidence…
			</main>
		);
	}
	if (!props.workspace) {
		return (
			<main
				id="workspace"
				className="engineering-workspace panel welcome-state"
			>
				<span className="eyebrow">Engineering workspace</span>
				<h1>Build understanding into momentum.</h1>
				<p>
					Create a project to import source evidence, ask a grounded question,
					and plan the next focused action.
				</p>
			</main>
		);
	}
	return (
		<main id="workspace" className="engineering-workspace panel">
			<header className="workspace-header">
				<div>
					<span className="eyebrow">Active project</span>
					<h1>{props.workspace.project.name}</h1>
				</div>
				<div className="workspace-actions">
					<button
						className="ai-policy-button"
						type="button"
						onClick={props.onConfigureAi}
						aria-haspopup="dialog"
					>
						<span>
							{props.workspace.ai_policy.mode === "nebius"
								? "Nebius remote"
								: "Local deterministic"}
						</span>
						<small>
							{props.workspace.ai_policy.mode === "nebius"
								? "ZDR attested"
								: props.remoteConfigured
									? "Remote available"
									: "Remote unavailable"}
						</small>
					</button>
					<button
						className="secondary-button"
						type="button"
						onClick={props.onImport}
						disabled={props.importPending}
					>
						{props.importPending ? "Importing…" : "＋ Import source"}
					</button>
				</div>
			</header>
			<section className="source-strip" aria-label="Imported project sources">
				{props.workspace.sources.length === 0 ? (
					<span className="muted">
						No evidence imported yet. Choose one PDF or Markdown source.
					</span>
				) : (
					props.workspace.sources.map((source) => (
						<span className="source-pill" key={source.id}>
							<span aria-hidden="true">
								{source.kind === "pdf" ? "PDF" : "MD"}
							</span>
							{source.name}
							<small>
								{source.evidence_count} evidence{" "}
								{source.evidence_count === 1 ? "unit" : "units"}
							</small>
						</span>
					))
				)}
			</section>
			{props.answer ? (
				<AnswerPanel
					answer={props.answer}
					feedback={props.feedback}
					feedbackPending={props.feedbackPending}
					taskPending={props.taskPending}
					onFeedback={props.onFeedback}
					onCreateTask={props.onCreateTask}
				/>
			) : (
				<section
					className="canvas-placeholder"
					aria-label="Future structured engineering workspace"
				>
					<div className="canvas-grid" aria-hidden="true" />
					<div className="project-node primary-node">
						<small>Current system</small>
						<strong>{props.workspace.project.name}</strong>
						<span>
							{props.workspace.sources.length} source{" "}
							{props.workspace.sources.length === 1
								? "connected"
								: "connections"}
						</span>
					</div>
					<div className="project-node ghost-node node-one">
						<span aria-hidden="true">◇</span> Requirements
					</div>
					<div className="project-node ghost-node node-two">
						<span aria-hidden="true">◇</span> Evidence
					</div>
					<p className="canvas-caption">
						Structured diagrams and a whiteboard will grow here after the
						evidence loop is proven.
					</p>
				</section>
			)}
		</main>
	);
}

function useRemainingTime(focus: FocusSession | null): number {
	const [now, setNow] = useState(() => Date.now());
	const [snapshotAt, setSnapshotAt] = useState(() => Date.now());
	const focusSnapshotKey = `${focus?.id ?? "none"}:${focus?.revision ?? 0}`;
	useEffect(() => {
		if (!focusSnapshotKey) return;
		setSnapshotAt(Date.now());
		setNow(Date.now());
	}, [focusSnapshotKey]);
	useEffect(() => {
		if (focus?.status !== "active") return;
		const timer = window.setInterval(() => setNow(Date.now()), 1_000);
		return () => window.clearInterval(timer);
	}, [focus?.status]);
	if (!focus) return 0;
	const liveSeconds =
		focus.status === "active" ? Math.floor((now - snapshotAt) / 1_000) : 0;
	return Math.max(0, focus.remaining_seconds - liveSeconds);
}

function formatDuration(totalSeconds: number): string {
	const minutes = Math.floor(totalSeconds / 60)
		.toString()
		.padStart(2, "0");
	const seconds = (totalSeconds % 60).toString().padStart(2, "0");
	return `${minutes}:${seconds}`;
}

function TodayRail(props: {
	workspace?: Workspace;
	focusPending: boolean;
	onStart: (taskId: string) => void;
	onTransition: (transition: "pause" | "resume" | "complete") => void;
}) {
	const focus = props.workspace?.active_focus ?? null;
	const remaining = useRemainingTime(focus);
	const focusTask = props.workspace?.tasks.find(
		(task) => task.id === focus?.task_id,
	);
	return (
		<aside className="today-rail panel" aria-label="Today's tasks and focus">
			<header className="today-header">
				<div>
					<span className="eyebrow">Today</span>
					<h2>Next actions</h2>
				</div>
				<span className="today-date">
					{new Intl.DateTimeFormat(undefined, {
						month: "short",
						day: "numeric",
					}).format(new Date())}
				</span>
			</header>
			<section
				className={focus ? "focus-card active" : "focus-card"}
				aria-label="Active focus session"
			>
				<div className="focus-status">
					<span aria-hidden="true" /> {focus ? focus.status : "Ready to focus"}
				</div>
				<div
					className="focus-time"
					role="timer"
					aria-label={`${remaining} seconds remaining`}
				>
					{focus ? formatDuration(remaining) : "25:00"}
				</div>
				<p>
					{focusTask?.title ??
						"Choose a task below to begin a calm focus block."}
				</p>
				{focus && (
					<div className="focus-controls">
						<button
							type="button"
							onClick={() =>
								props.onTransition(
									focus.status === "active" ? "pause" : "resume",
								)
							}
							disabled={props.focusPending}
						>
							{focus.status === "active" ? "Pause" : "Resume"}
						</button>
						<button
							type="button"
							onClick={() => props.onTransition("complete")}
							disabled={props.focusPending}
						>
							Complete
						</button>
					</div>
				)}
			</section>
			<div className="task-list-heading">
				<h3>Tasks</h3>
				<span>{props.workspace?.tasks.length ?? 0}</span>
			</div>
			<ul className="task-list">
				{(props.workspace?.tasks ?? []).map((task: Task) => (
					<li key={task.id} className={`task-row ${task.status}`}>
						<span
							className="task-status-icon"
							role="img"
							aria-label={task.status}
						>
							{task.status === "completed" ? "✓" : "○"}
						</span>
						<span className="task-title">
							{task.title}
							<small>{task.status.replace("_", " ")}</small>
						</span>
						{task.status !== "completed" && !focus && (
							<button
								type="button"
								onClick={() => props.onStart(task.id)}
								disabled={props.focusPending}
							>
								Focus
							</button>
						)}
					</li>
				))}
			</ul>
			{(props.workspace?.tasks.length ?? 0) === 0 && (
				<p className="muted empty-copy">
					Grounded answers can become today’s next task.
				</p>
			)}
		</aside>
	);
}

const recordingLabels: Record<RecordingState, string> = {
	idle: "Microphone idle",
	requesting: "Requesting microphone permission",
	recording: "Recording — press stop when finished",
	processing: "Processing voice locally",
	denied: "Microphone permission denied",
	error: "Microphone unavailable",
};

function AssistantDock(props: {
	disabled: boolean;
	pending: boolean;
	isRemote: boolean;
	onAsk: (question: string) => void;
	onCancel: () => void;
}) {
	const [question, setQuestion] = useState("");
	const recordingState = useWorkspaceStore((state) => state.recordingState);
	const setRecordingState = useWorkspaceStore(
		(state) => state.setRecordingState,
	);
	const streamRef = useRef<MediaStream | null>(null);

	const stopRecording = () => {
		for (const track of streamRef.current?.getTracks() ?? []) track.stop();
		streamRef.current = null;
		setRecordingState("processing");
		window.setTimeout(() => setRecordingState("idle"), 500);
	};

	const startRecording = async () => {
		if (recordingState === "recording") {
			stopRecording();
			return;
		}
		setRecordingState("requesting");
		try {
			const permission =
				await window.vikramDesktop.v1.microphone.requestPermission();
			if (!permission.granted) {
				setRecordingState("denied");
				return;
			}
			streamRef.current = await navigator.mediaDevices.getUserMedia({
				audio: true,
				video: false,
			});
			setRecordingState("recording");
		} catch {
			setRecordingState("error");
		}
	};

	useEffect(
		() => () => {
			for (const track of streamRef.current?.getTracks() ?? []) track.stop();
		},
		[],
	);

	const submit = (event: FormEvent) => {
		event.preventDefault();
		const value = question.trim();
		if (!value || props.disabled) return;
		props.onAsk(value);
		setQuestion("");
	};

	return (
		<section className="assistant-dock panel" aria-label="Vikram assistant">
			<div className={`mic-status ${recordingState}`} aria-live="polite">
				<span className="mic-pulse" aria-hidden="true" />
				<span>
					<strong>Vikram</strong>
					<small>{recordingLabels[recordingState]}</small>
				</span>
			</div>
			<div className="assistant-composer">
				<form onSubmit={submit} className="assistant-form">
					<label className="sr-only" htmlFor="assistant-question">
						Ask about the selected project
					</label>
					<input
						id="assistant-question"
						value={question}
						onChange={(event) => setQuestion(event.target.value)}
						placeholder={
							props.disabled
								? "Create a project and import evidence first"
								: "Ask a question about your source…"
						}
						disabled={props.disabled || props.pending}
					/>
					{props.pending ? (
						<button
							className="cancel-answer-button"
							type="button"
							onClick={props.onCancel}
						>
							Cancel
						</button>
					) : (
						<button
							className="ask-button"
							type="submit"
							disabled={props.disabled || !question.trim()}
						>
							Ask
						</button>
					)}
				</form>
				{props.pending && (
					<div className="answer-activity" role="status" aria-live="polite">
						<strong>
							{props.isRemote
								? "Remote answer in progress"
								: "Local answer in progress"}
						</strong>
						<small>
							{props.isRemote
								? "Local retrieval → remote generation → remote verification"
								: "Retrieving and checking local evidence"}
						</small>
					</div>
				)}
			</div>
			<button
				className={
					recordingState === "recording" ? "mic-button recording" : "mic-button"
				}
				type="button"
				aria-label={
					recordingState === "recording"
						? "Stop recording"
						: "Start push-to-talk recording"
				}
				onClick={startRecording}
				disabled={
					recordingState === "requesting" || recordingState === "processing"
				}
			>
				{recordingState === "recording" ? "■" : "●"}
			</button>
		</section>
	);
}

function CreateProjectDialog(props: {
	pending: boolean;
	onClose: () => void;
	onCreate: (name: string) => void;
}) {
	const [name, setName] = useState("");
	return (
		<div className="dialog-backdrop">
			<section
				className="dialog-card"
				role="dialog"
				aria-modal="true"
				aria-labelledby="create-title"
			>
				<span className="eyebrow">Start with intent</span>
				<h2 id="create-title">Create an engineering project</h2>
				<p>
					A project scopes source evidence, answers, tasks, and focus sessions.
				</p>
				<form
					onSubmit={(event) => {
						event.preventDefault();
						if (name.trim()) props.onCreate(name.trim());
					}}
				>
					<label htmlFor="project-name">Project name</label>
					<input
						id="project-name"
						maxLength={120}
						value={name}
						onChange={(event) => setName(event.target.value)}
						placeholder="e.g. Motor controller prototype"
					/>
					<div className="dialog-actions">
						<button
							type="button"
							className="secondary-button"
							onClick={props.onClose}
						>
							Cancel
						</button>
						<button
							type="submit"
							className="primary-button"
							disabled={!name.trim() || props.pending}
						>
							{props.pending ? "Creating…" : "Create project"}
						</button>
					</div>
				</form>
			</section>
		</div>
	);
}

function userFacingError(error: unknown): string {
	if (!(error instanceof ApiError)) {
		return error instanceof Error
			? error.message
			: "Something went wrong. Try the action again.";
	}
	const classifiedMessages: Record<string, string> = {
		provider_not_configured:
			"Nebius remote AI is not configured in the local API. Ask the workspace administrator to configure it, then try again.",
		zdr_attestation_required:
			"Confirm that Zero Data Retention is enabled before turning on remote AI.",
		provider_authentication:
			"Nebius authentication failed. Check the local API configuration before retrying.",
		provider_rate_limit:
			"Nebius is rate-limiting requests. No answer was saved; wait a moment, then try again.",
		provider_timeout:
			"Nebius did not respond in time. No answer was saved; try again.",
		provider_unavailable:
			"Nebius is temporarily unavailable. No answer was saved; try again.",
		provider_invalid_output:
			"Nebius returned an answer Vikram could not safely read. No answer was saved; try again.",
		grounding_verification:
			"Vikram could not verify the remote answer against your sources, so it was not saved. Try a more specific question.",
		remote_index_limit:
			"This project has too much evidence for the current remote limit. Keep remote AI off or use a smaller project.",
		conflict:
			"The project AI setting changed elsewhere. Close this dialog, review the current setting, and try again.",
		request_timeout:
			"The local answer request timed out. No answer was saved; try again.",
	};
	return classifiedMessages[error.code] ?? error.message;
}

function RemoteAiDialog(props: {
	projectName: string;
	mode: Workspace["ai_policy"]["mode"];
	remoteConfigured: boolean;
	pending: boolean;
	error: string | null;
	onClose: () => void;
	onEnable: () => void;
	onRevoke: () => void;
}) {
	const [attested, setAttested] = useState(false);
	const [attestationError, setAttestationError] = useState<string | null>(null);
	const firstButtonRef = useRef<HTMLButtonElement | null>(null);
	const dialogRef = useRef<HTMLElement | null>(null);
	const onCloseRef = useRef(props.onClose);
	const pendingRef = useRef(props.pending);

	useEffect(() => {
		onCloseRef.current = props.onClose;
		pendingRef.current = props.pending;
	}, [props.onClose, props.pending]);

	useEffect(() => {
		const previousFocus =
			document.activeElement instanceof HTMLElement
				? document.activeElement
				: null;
		firstButtonRef.current?.focus();
		const closeOnEscape = (event: KeyboardEvent) => {
			if (event.key === "Escape" && !pendingRef.current) {
				onCloseRef.current();
			}
			if (event.key !== "Tab") return;
			const focusable = Array.from(
				dialogRef.current?.querySelectorAll<HTMLElement>(
					"button:not([disabled]), input:not([disabled])",
				) ?? [],
			);
			const first = focusable[0];
			const last = focusable.at(-1);
			if (!first || !last) return;
			if (event.shiftKey && document.activeElement === first) {
				event.preventDefault();
				last.focus();
			} else if (!event.shiftKey && document.activeElement === last) {
				event.preventDefault();
				first.focus();
			}
		};
		document.addEventListener("keydown", closeOnEscape);
		return () => {
			document.removeEventListener("keydown", closeOnEscape);
			previousFocus?.focus();
		};
	}, []);

	const enable = () => {
		if (!attested) {
			setAttestationError(
				"You must attest that Zero Data Retention is enabled before continuing.",
			);
			return;
		}
		setAttestationError(null);
		props.onEnable();
	};

	return (
		<div className="dialog-backdrop">
			<section
				ref={dialogRef}
				className="dialog-card ai-policy-dialog"
				role="dialog"
				aria-modal="true"
				aria-labelledby="ai-policy-title"
				aria-describedby="ai-policy-disclosure"
			>
				<span className="eyebrow">Project AI boundary</span>
				<h2 id="ai-policy-title">AI processing for {props.projectName}</h2>
				<p id="ai-policy-disclosure">
					Local deterministic AI keeps processing on this device. If you enable
					Nebius remote AI, Vikram sends bounded source evidence units to Nebius
					for semantic embedding. For each question, it sends the question text
					and at most four selected source excerpts for generation and
					verification.
				</p>
				{props.mode === "local" ? (
					<>
						<div className="runtime-summary" role="status">
							<strong>Remote runtime</strong>
							<span>
								{props.remoteConfigured ? "Available" : "Not configured"}
							</span>
						</div>
						<label className="attestation-control">
							<input
								type="checkbox"
								checked={attested}
								onChange={(event) => {
									setAttested(event.target.checked);
									if (event.target.checked) setAttestationError(null);
								}}
							/>
							<span>
								I attest that Zero Data Retention (ZDR) is enabled for my Nebius
								account.
							</span>
						</label>
						{attestationError && (
							<p className="inline-error" role="alert">
								{attestationError}
							</p>
						)}
					</>
				) : (
					<div className="runtime-summary remote-active" role="status">
						<strong>Nebius remote is enabled</strong>
						<span>ZDR attested for this project</span>
					</div>
				)}
				{props.error && (
					<p className="inline-error" role="alert">
						{props.error}
					</p>
				)}
				{props.mode === "nebius" && (
					<p className="revocation-copy">
						Returning to local AI preserves your sources and answers. Future
						questions stay on this device.
					</p>
				)}
				<div className="dialog-actions">
					<button
						ref={firstButtonRef}
						type="button"
						className="secondary-button"
						onClick={props.onClose}
						disabled={props.pending}
					>
						Cancel
					</button>
					{props.mode === "local" ? (
						<button
							type="button"
							className="primary-button"
							onClick={enable}
							disabled={props.pending}
						>
							{props.pending ? "Enabling…" : "Enable Nebius remote AI"}
						</button>
					) : (
						<button
							type="button"
							className="primary-button revoke-button"
							onClick={props.onRevoke}
							disabled={props.pending}
						>
							{props.pending ? "Returning to local…" : "Use local AI"}
						</button>
					)}
				</div>
			</section>
		</div>
	);
}

export default function App() {
	const queryClient = useQueryClient();
	const [showCreate, setShowCreate] = useState(false);
	const [showAiPolicy, setShowAiPolicy] = useState(false);
	const [answer, setAnswer] = useState<Answer | null>(null);
	const [feedback, setFeedback] = useState<FeedbackStatus | null>(null);
	const [notice, setNotice] = useState<string | null>(null);
	const askControllerRef = useRef<AbortController | null>(null);
	const selectedProjectId = useWorkspaceStore(
		(state) => state.selectedProjectId,
	);
	const setSelectedProjectId = useWorkspaceStore(
		(state) => state.setSelectedProjectId,
	);

	const health = useQuery({
		queryKey: ["health"],
		queryFn: api.health,
		retry: false,
		refetchInterval: 15_000,
	});
	const projects = useQuery({
		queryKey: ["projects"],
		queryFn: api.listProjects,
		retry: false,
	});
	const workspace = useQuery({
		queryKey: ["workspace", selectedProjectId],
		queryFn: () => api.workspace(selectedProjectId ?? ""),
		enabled: Boolean(selectedProjectId),
		retry: false,
	});

	useEffect(() => {
		if (!selectedProjectId && projects.data?.[0])
			setSelectedProjectId(projects.data[0].id);
	}, [projects.data, selectedProjectId, setSelectedProjectId]);
	useEffect(
		() => () => {
			askControllerRef.current?.abort();
		},
		[],
	);

	const refreshWorkspace = () =>
		queryClient.invalidateQueries({
			queryKey: ["workspace", selectedProjectId],
		});
	const createProject = useMutation({
		mutationFn: api.createProject,
		onSuccess: async (project) => {
			setSelectedProjectId(project.id);
			setShowCreate(false);
			setAnswer(null);
			await queryClient.invalidateQueries({ queryKey: ["projects"] });
		},
	});
	const importSource = useMutation({
		mutationFn: async () =>
			window.vikramDesktop.v1.sources.chooseAndImport(selectedProjectId ?? ""),
		onSuccess: async (result) => {
			if (result.status === "imported") {
				setNotice(
					`${result.source.name} is ready with ${result.source.evidence_count} evidence units.`,
				);
				await refreshWorkspace();
			}
		},
	});
	const aiPolicyMutation = useMutation({
		mutationFn: (input: {
			projectId: string;
			mode: "local" | "nebius";
			zdrAttested: boolean;
			expectedRevision: number;
		}) =>
			api.updateAiPolicy(
				input.projectId,
				input.mode,
				input.zdrAttested,
				input.expectedRevision,
			),
		onSuccess: (policy) => {
			queryClient.setQueryData<Workspace>(
				["workspace", policy.project_id],
				(current) => (current ? { ...current, ai_policy: policy } : current),
			);
			setShowAiPolicy(false);
			setNotice(
				policy.mode === "nebius"
					? "Nebius remote AI is enabled for this project."
					: "This project now uses local deterministic AI.",
			);
		},
	});
	const ask = useMutation({
		mutationFn: (input: {
			projectId: string;
			question: string;
			signal: AbortSignal;
		}) => api.ask(input.projectId, input.question, input.signal),
		onSuccess: (result) => {
			setAnswer(result);
			setFeedback(null);
		},
		onError: (error) => {
			if (error instanceof ApiError && error.code === "request_cancelled") {
				setNotice("Answer request cancelled. No answer was saved.");
			}
		},
		onSettled: () => {
			askControllerRef.current = null;
		},
	});
	const feedbackMutation = useMutation({
		mutationFn: (value: FeedbackStatus) =>
			api.feedback(answer?.id ?? "", value),
		onSuccess: (result) => setFeedback(result.status),
	});
	const taskMutation = useMutation({
		mutationFn: () => api.taskFromAnswer(answer?.id ?? ""),
		onSuccess: async () => {
			setNotice("Answer added to Today as a task.");
			await refreshWorkspace();
		},
	});
	const focusMutation = useMutation({
		mutationFn: api.startFocus,
		onSuccess: refreshWorkspace,
	});
	const transitionMutation = useMutation({
		mutationFn: (transition: "pause" | "resume" | "complete") => {
			const focus = workspace.data?.active_focus;
			if (!focus) throw new Error("No focus session is active.");
			return api.transitionFocus(focus.id, transition, focus.revision);
		},
		onSuccess: refreshWorkspace,
	});

	const askError =
		ask.error instanceof ApiError && ask.error.code === "request_cancelled"
			? null
			: ask.error;
	const visibleError =
		createProject.error ??
		importSource.error ??
		askError ??
		feedbackMutation.error ??
		taskMutation.error ??
		focusMutation.error ??
		transitionMutation.error ??
		workspace.error;
	const remoteActive = workspace.data?.ai_policy.mode === "nebius";
	const runtimeLabel = health.isError
		? "Local API offline"
		: health.isPending
			? "Checking AI runtime…"
			: remoteActive
				? "Nebius remote · ZDR attested"
				: "Local deterministic";

	const changeAiPolicy = (mode: "local" | "nebius", zdrAttested: boolean) => {
		const policy = workspace.data?.ai_policy;
		if (!policy) return;
		if (mode === "local") askControllerRef.current?.abort();
		aiPolicyMutation.mutate({
			projectId: policy.project_id,
			mode,
			zdrAttested,
			expectedRevision: policy.revision,
		});
	};

	const askQuestion = (question: string) => {
		if (!selectedProjectId) return;
		const controller = new AbortController();
		askControllerRef.current = controller;
		setNotice(null);
		ask.mutate({
			projectId: selectedProjectId,
			question,
			signal: controller.signal,
		});
	};

	return (
		<div className="app-shell">
			<a className="skip-link" href="#workspace">
				Skip to engineering workspace
			</a>
			<header className="top-bar">
				<div className="brand-lockup">
					<span className="brand-mark" aria-hidden="true">
						V
					</span>
					<span>
						<strong>Vikram</strong>
						<small>Engineering workspace</small>
					</span>
				</div>
				<div className="top-project">
					{workspace.data?.project.name ?? "No project selected"}
				</div>
				<div className="system-state" aria-live="polite">
					<span
						className={health.isError ? "status-dot offline" : "status-dot"}
						aria-hidden="true"
					/>
					{runtimeLabel}
					<span className="privacy-label">
						{remoteActive
							? "Remote embeddings + bounded answer excerpts"
							: "Private on this device"}
					</span>
				</div>
			</header>
			<div className="workspace-grid">
				<ProjectRail
					projects={projects.data ?? []}
					selectedId={selectedProjectId}
					onSelect={(id) => {
						askControllerRef.current?.abort();
						setSelectedProjectId(id);
						setAnswer(null);
						setFeedback(null);
						setShowAiPolicy(false);
					}}
					onCreate={() => setShowCreate(true)}
				/>
				<EngineeringWorkspace
					workspace={workspace.data}
					loading={workspace.isLoading}
					remoteConfigured={health.data?.ai_runtime.remote_configured ?? false}
					answer={answer}
					feedback={feedback}
					feedbackPending={feedbackMutation.isPending}
					taskPending={taskMutation.isPending}
					importPending={importSource.isPending}
					onImport={() => importSource.mutate()}
					onConfigureAi={() => {
						aiPolicyMutation.reset();
						setShowAiPolicy(true);
					}}
					onFeedback={(value) => feedbackMutation.mutate(value)}
					onCreateTask={() => taskMutation.mutate()}
				/>
				<TodayRail
					workspace={workspace.data}
					focusPending={focusMutation.isPending || transitionMutation.isPending}
					onStart={(id) => focusMutation.mutate(id)}
					onTransition={(value) => transitionMutation.mutate(value)}
				/>
				<AssistantDock
					disabled={
						!selectedProjectId || (workspace.data?.sources.length ?? 0) === 0
					}
					pending={ask.isPending}
					isRemote={remoteActive}
					onAsk={askQuestion}
					onCancel={() => askControllerRef.current?.abort()}
				/>
			</div>
			{(notice || visibleError) && (
				<div
					className={visibleError ? "toast error" : "toast"}
					role={visibleError ? "alert" : "status"}
				>
					{visibleError ? userFacingError(visibleError) : notice}
					<button
						type="button"
						aria-label="Dismiss notification"
						onClick={() => {
							setNotice(null);
							ask.reset();
							createProject.reset();
							importSource.reset();
							feedbackMutation.reset();
							taskMutation.reset();
							focusMutation.reset();
							transitionMutation.reset();
						}}
					>
						×
					</button>
				</div>
			)}
			{showCreate && (
				<CreateProjectDialog
					pending={createProject.isPending}
					onClose={() => setShowCreate(false)}
					onCreate={(name) => createProject.mutate(name)}
				/>
			)}
			{showAiPolicy && workspace.data && (
				<RemoteAiDialog
					projectName={workspace.data.project.name}
					mode={workspace.data.ai_policy.mode}
					remoteConfigured={health.data?.ai_runtime.remote_configured ?? false}
					pending={aiPolicyMutation.isPending}
					error={
						aiPolicyMutation.error
							? userFacingError(aiPolicyMutation.error)
							: null
					}
					onClose={() => {
						aiPolicyMutation.reset();
						setShowAiPolicy(false);
					}}
					onEnable={() => changeAiPolicy("nebius", true)}
					onRevoke={() => changeAiPolicy("local", false)}
				/>
			)}
		</div>
	);
}
