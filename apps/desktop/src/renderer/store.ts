import { create } from "zustand";

export type RecordingState =
	| "idle"
	| "requesting"
	| "recording"
	| "processing"
	| "denied"
	| "error";

interface WorkspaceStore {
	selectedProjectId: string | null;
	recordingState: RecordingState;
	setSelectedProjectId: (id: string) => void;
	setRecordingState: (state: RecordingState) => void;
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
	selectedProjectId: null,
	recordingState: "idle",
	setSelectedProjectId: (selectedProjectId) => set({ selectedProjectId }),
	setRecordingState: (recordingState) => set({ recordingState }),
}));
