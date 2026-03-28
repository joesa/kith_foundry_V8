import { useScreenState } from "./useScreenState";

export type CapabilityState = "idle" | "editing" | "submitting" | "needs_secrets" | "complete" | "error";

export function useCapabilityState() {
    return useScreenState<CapabilityState>("idle");
}
