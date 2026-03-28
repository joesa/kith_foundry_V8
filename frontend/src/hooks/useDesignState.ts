import { useScreenState } from "./useScreenState";

export type DesignState = "loading" | "loaded" | "refining" | "regenerating" | "error";

export function useDesignState() {
    return useScreenState<DesignState>("loading");
}
