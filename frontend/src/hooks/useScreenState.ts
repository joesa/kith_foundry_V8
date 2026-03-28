import { useState, useCallback } from "react";

export function useScreenState<S extends string>(initialState: S) {
    const [state, setState] = useState<S>(initialState);
    const [error, setError] = useState<string | null>(null);

    const transition = useCallback((next: S) => {
        setError(null);
        setState(next);
    }, []);

    const fail = useCallback((message: string) => {
        setError(message);
        setState("error" as S);
    }, []);

    const reset = useCallback(() => {
        setError(null);
        setState(initialState);
    }, [initialState]);

    return { state, error, transition, fail, reset } as const;
}
