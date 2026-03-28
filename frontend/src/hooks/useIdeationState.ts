import { useScreenState } from "./useScreenState";

export type PromptState = "idle" | "typing" | "submitting" | "submitted" | "error";
export type CuratedIdeaState = "loading" | "loaded" | "accepted" | "saved" | "rejected" | "error";
export type QuestionnaireState = "loading_questions" | "answering" | "submitting" | "submitted" | "error";
export type Top5State = "loading" | "loaded" | "selecting" | "saving" | "selected" | "error";
export type SavedIdeasState = "loading" | "loaded" | "empty" | "launching" | "archiving" | "error";

export function usePromptState() {
    return useScreenState<PromptState>("idle");
}

export function useCuratedIdeaState() {
    return useScreenState<CuratedIdeaState>("loading");
}

export function useQuestionnaireState() {
    return useScreenState<QuestionnaireState>("loading_questions");
}

export function useTop5State() {
    return useScreenState<Top5State>("loading");
}

export function useSavedIdeasState() {
    return useScreenState<SavedIdeasState>("loading");
}
