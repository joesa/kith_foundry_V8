import { useScreenState } from "./useScreenState";

export type BuildState = "idle" | "queued" | "planning" | "generating_code" | "building" | "repairing" | "ready_for_preview" | "failed";
export type EditorChatState = "idle" | "sending" | "processing" | "patch_ready" | "applying" | "rebuilding" | "completed" | "error";

export function useBuildState() {
    return useScreenState<BuildState>("idle");
}

export function useEditorChatState() {
    return useScreenState<EditorChatState>("idle");
}
