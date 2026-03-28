import { useEffect, useCallback, useRef } from "react";
import { getApiBaseUrl } from "../lib/runtimeConfig";
import { useAuth } from "../contexts/AuthContext";

/**
 * Debounced auto-save hook for manual Monaco Editor changes.
 * Sends changed files to POST /api/v1/projects/{project_id}/save
 * after the user stops typing for `delayMs` (default 1500ms).
 * @param onSaved Callback when save succeeds; use to trigger preview reload.
 */
export function useAutoSave(
    projectId: string | undefined,
    files: Record<string, string>,
    delayMs: number = 1500,
    options?: { onSaved?: () => void },
) {
    const { getAccessToken } = useAuth();
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const lastSavedRef = useRef<Record<string, string>>({});
    const isSavingRef = useRef(false);
    const onSavedRef = useRef(options?.onSaved);
    onSavedRef.current = options?.onSaved;

    // Compute diff: only send files whose content actually changed
    const getDirtyFiles = useCallback((): Record<string, string> => {
        const dirty: Record<string, string> = {};
        for (const [path, content] of Object.entries(files)) {
            if (lastSavedRef.current[path] !== content) {
                dirty[path] = content;
            }
        }
        return dirty;
    }, [files]);

    const saveNow = useCallback(async () => {
        if (!projectId || isSavingRef.current) return;

        const dirty = getDirtyFiles();
        if (Object.keys(dirty).length === 0) return;

        isSavingRef.current = true;
        try {
            const token = await getAccessToken();
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/save`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                    },
                    body: JSON.stringify({ files: dirty }),
                },
            );
            if (resp.ok) {
                // Mark those files as saved
                for (const [path, content] of Object.entries(dirty)) {
                    lastSavedRef.current[path] = content;
                }
                onSavedRef.current?.();
            }
        } catch (err) {
            console.warn("[useAutoSave] save failed:", err);
        } finally {
            isSavingRef.current = false;
        }
    }, [projectId, getDirtyFiles, getAccessToken]);

    // Debounce: restart timer on every files change
    useEffect(() => {
        if (!projectId) return;

        if (timerRef.current) clearTimeout(timerRef.current);
        timerRef.current = setTimeout(() => {
            saveNow();
        }, delayMs);

        return () => {
            if (timerRef.current) clearTimeout(timerRef.current);
        };
    }, [files, projectId, delayMs, saveNow]);

    // Seed lastSavedRef when files first arrive (from restore)
    // so we don't immediately re-save restored files.
    const seededRef = useRef(false);
    useEffect(() => {
        if (!seededRef.current && Object.keys(files).length > 0) {
            lastSavedRef.current = { ...files };
            seededRef.current = true;
        }
    }, [files]);

    return { saveNow };
}
