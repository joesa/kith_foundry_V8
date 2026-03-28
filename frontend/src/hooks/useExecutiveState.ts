import { useScreenState } from "./useScreenState";

export type ExecutiveState = "loading" | "running" | "loaded" | "error";

export function useExecutiveState() {
    return useScreenState<ExecutiveState>("loading");
}
