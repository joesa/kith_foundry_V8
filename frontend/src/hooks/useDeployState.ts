import { useScreenState } from "./useScreenState";

export type DeployScreenState = "idle" | "connecting_git" | "committing" | "deploying" | "deployed" | "failed";

export function useDeployState() {
    return useScreenState<DeployScreenState>("idle");
}
