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
import { api } from "./api";
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
				<span className="privacy-dot" aria-hidden="true" /> Local workspace
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
	answer: Answer | null;
	feedback: FeedbackStatus | null;
	feedbackPending: boolean;
	taskPending: boolean;
	importPending: boolean;
	onImport: () => void;
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
				<button
					className="secondary-button"
					type="button"
					onClick={props.onImport}
					disabled={props.importPending}
				>
					{props.importPending ? "Importing…" : "＋ Import source"}
				</button>
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
	onAsk: (question: string) => void;
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
				<button
					className="ask-button"
					type="submit"
					disabled={props.disabled || props.pending || !question.trim()}
				>
					{props.pending ? "Thinking…" : "Ask"}
				</button>
			</form>
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

export default function App() {
	const queryClient = useQueryClient();
	const [showCreate, setShowCreate] = useState(false);
	const [answer, setAnswer] = useState<Answer | null>(null);
	const [feedback, setFeedback] = useState<FeedbackStatus | null>(null);
	const [notice, setNotice] = useState<string | null>(null);
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
	const ask = useMutation({
		mutationFn: (question: string) =>
			api.ask(selectedProjectId ?? "", question),
		onSuccess: (result) => {
			setAnswer(result);
			setFeedback(null);
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

	const visibleError =
		createProject.error ??
		importSource.error ??
		ask.error ??
		feedbackMutation.error ??
		taskMutation.error ??
		focusMutation.error ??
		transitionMutation.error ??
		workspace.error;

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
					{health.isError ? "Local API offline" : "Local · fake providers"}
					<span className="privacy-label">Private on this device</span>
				</div>
			</header>
			<div className="workspace-grid">
				<ProjectRail
					projects={projects.data ?? []}
					selectedId={selectedProjectId}
					onSelect={(id) => {
						setSelectedProjectId(id);
						setAnswer(null);
						setFeedback(null);
					}}
					onCreate={() => setShowCreate(true)}
				/>
				<EngineeringWorkspace
					workspace={workspace.data}
					loading={workspace.isLoading}
					answer={answer}
					feedback={feedback}
					feedbackPending={feedbackMutation.isPending}
					taskPending={taskMutation.isPending}
					importPending={importSource.isPending}
					onImport={() => importSource.mutate()}
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
					onAsk={(question) => ask.mutate(question)}
				/>
			</div>
			{(notice || visibleError) && (
				<div
					className={visibleError ? "toast error" : "toast"}
					role={visibleError ? "alert" : "status"}
				>
					{visibleError instanceof Error ? visibleError.message : notice}
					<button
						type="button"
						aria-label="Dismiss notification"
						onClick={() => setNotice(null)}
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
		</div>
	);
}
