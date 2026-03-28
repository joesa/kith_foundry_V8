import { useScreenState } from "./useScreenState";

export type SecretsState = "idle" | "collecting" | "submitting" | "stored" | "revoking" | "error";

export function useSecretsState() {
    return useScreenState<SecretsState>("idle");
}
