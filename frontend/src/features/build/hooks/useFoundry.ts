import { useState, useEffect, useRef, useCallback } from "react";
import type { TreeNode } from "../../../components/workspace/FileExplorer";
import { getWsUrl } from "../../../lib/runtimeConfig";
import { useAuth } from "../../../contexts/AuthContext";

const DEFAULT_APP_TSX = `// Your app will appear here after generation
import './App.css'

function App() {
    return (
        <main style={{ padding: '24px', fontFamily: 'system-ui, sans-serif' }}>
            <h1>Preview Ready</h1>
            <p>Describe the product requirements and generate the app.</p>
        </main>
    )
}

export default App
`;

export function useFoundry(projectId?: string) {
    const { getAccessToken, loading: authLoading } = useAuth();

    // Capture the token string into stable state — avoids WS reconnect loop.
    // getAccessToken is async (Nhost session/token).
    const [wsToken, setWsToken] = useState<string | null>(null);
    useEffect(() => {
        if (authLoading) return;
        let cancelled = false;
        getAccessToken().then(t => {
            if (!cancelled) setWsToken(prev => (prev !== t ? t : prev));
        });
        return () => { cancelled = true; };
    }, [authLoading, getAccessToken]);
    const [status, setStatus] = useState<string>("idle");
    const [wsConnected, setWsConnected] = useState(false);
    const reconnectTimer = useRef<number | null>(null);
    const reconnectAttempts = useRef(0);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const previewUrlRef = useRef<string | null>(null);
    const [iframeSrc, setIframeSrc] = useState<string | null>(null);
    const dnsRetryTimer = useRef<number | null>(null);
    const probeGen = useRef(0); // incremented on each new probe chain to cancel stale ones
    const [hasExistingFiles, setHasExistingFiles] = useState<boolean | null>(null); // null = unknown yet
    const [files, setFiles] = useState<Record<string, string>>({
        "src/App.tsx": DEFAULT_APP_TSX
    });
    const [fileTree, setFileTree] = useState<TreeNode[]>([
        {
            name: "src", path: "src", type: "dir", children: [
                { name: "App.tsx", path: "src/App.tsx", type: "file" },
                { name: "App.css", path: "src/App.css", type: "file" },
                { name: "main.tsx", path: "src/main.tsx", type: "file" }
            ]
        }
    ]);

    // Streaming state
    const [streamingFile, setStreamingFile] = useState<string | null>(null);
    const [isStreaming, setIsStreaming] = useState(false);
    const streamBuffer = useRef<string>("");
    const flushTimer = useRef<number | null>(null);
    const streamingFileRef = useRef<string | null>(null);

    const [messages, setMessages] = useState<{ role: string, content: string }[]>([]);
    const ws = useRef<WebSocket | null>(null);
    const pendingCommandRef = useRef<{ prompt: string; model: string; images: string[] } | null>(null);

    // Conversation streaming state
    const [assistantStreaming, setAssistantStreaming] = useState(false);
    const [streamingAssistantMessage, setStreamingAssistantMessage] = useState("");
    const assistantMessageRef = useRef("");

    // Build pipeline state (orchestration stages, patches, sandbox logs, security scans)
    const [buildStage, setBuildStage] = useState<{ stage: string; status: string } | null>(null);
    const [patchProposals, setPatchProposals] = useState<Array<{ file: string; diff: string; status: string }>>([]);
    const [sandboxLogs, setSandboxLogs] = useState<Array<{ ts: number; level: string; message: string }>>([]);
    const [securityScan, setSecurityScan] = useState<{ status: string; violations: Array<{ category: string; detail: string }> } | null>(null);
    const [sandboxFailed, setSandboxFailed] = useState(false);

    // Auto-fix: debounced error collection from preview iframe
    const pendingErrors = useRef<Array<{ source: string, message: string, stack?: string }>>([]);
    const errorFlushTimer = useRef<number | null>(null);

    const sendPreviewErrors = useCallback(() => {
        if (pendingErrors.current.length === 0) return;
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
                type: "preview_error",
                errors: pendingErrors.current,
            }));
        }
        pendingErrors.current = [];
    }, []);

    useEffect(() => {
        // Wait until auth is resolved and we have a token
        if (authLoading || !wsToken) return;

        let destroyed = false;

        // handleIframeError lives outside connect() so the cleanup can remove the listener
        const queuePreviewError = (source: string, message: string, stack?: string) => {
            if (!message) return;
            pendingErrors.current.push({
                source,
                message,
                stack,
            });
            if (errorFlushTimer.current) clearTimeout(errorFlushTimer.current);
            errorFlushTimer.current = window.setTimeout(sendPreviewErrors, 500);
        };

        const isLikelyFromPreview = (text: string) => {
            const preview = previewUrlRef.current;
            const lower = text.toLowerCase();
            if (preview) {
                try {
                    const host = new URL(preview).host.toLowerCase();
                    if (host && lower.includes(host)) return true;
                } catch {
                    // ignore malformed URL edge cases
                }
            }
            // Fallback patterns that usually come from sandbox runtime stack traces
            return /(landingpage\.tsx|app\.tsx|src\/components\/|uncaught referenceerror|uncaught syntaxerror|vite\/deps\/lucide-react)/i.test(text);
        };

        const handleIframeError = (event: MessageEvent) => {
            if (event.data?.type === "preview-error" && event.data?.message) {
                queuePreviewError(
                    event.data.source || "browser",
                    event.data.message,
                    event.data.stack
                );
            }
        };

        // Cross-origin previews cannot always be script-injected.
        // Capture top-level error/rejection events as a fallback and
        // forward likely preview-runtime failures to backend auto-fix.
        const handleWindowError = (event: ErrorEvent) => {
            const parts = [
                event.message || "",
                event.filename || "",
                String(event.lineno || ""),
                String(event.colno || ""),
                event.error?.stack || "",
            ].filter(Boolean);
            const combined = parts.join(" ");
            if (!isLikelyFromPreview(combined)) return;
            queuePreviewError(
                "runtime",
                event.message || "Runtime error in preview",
                event.error?.stack || `${event.filename || ""}:${event.lineno || 0}:${event.colno || 0}`
            );
        };

        const handleWindowRejection = (event: PromiseRejectionEvent) => {
            const reason = event.reason;
            const msg = reason?.message || String(reason || "Unhandled promise rejection");
            const stack = reason?.stack || "";
            const combined = `${msg} ${stack}`;
            if (!isLikelyFromPreview(combined)) return;
            queuePreviewError("promise", msg, stack);
        };

        window.addEventListener("message", handleIframeError);
        window.addEventListener("error", handleWindowError);
        window.addEventListener("unhandledrejection", handleWindowRejection);

        const connect = () => {
            if (destroyed) return;

            // Build WS URL with auth token and project ID
            let wsUrl = getWsUrl("/ws/chat");
            const params: string[] = [];
            if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);
            params.push(`token=${encodeURIComponent(wsToken)}`);
            wsUrl += `?${params.join("&")}`;

            const socket = new WebSocket(wsUrl);
            ws.current = socket;

            socket.onopen = () => {
                if (destroyed) { socket.close(); return; }
                console.log("Connected to Kith Foundry backend");
                reconnectAttempts.current = 0;
                setWsConnected(true);
                setStatus("idle");

                // Flush one queued command if send was attempted during reconnect.
                const pending = pendingCommandRef.current;
                if (pending) {
                    socket.send(JSON.stringify(pending));
                    pendingCommandRef.current = null;
                    setStatus("analyzing");
                    setMessages(prev => [...prev, { role: "system", content: "Reconnected. Resuming generation..." }]);
                }

                // Clear stale sandbox URL — new sandbox_ready will set the fresh one.
                // This prevents the iframe from showing a 404 from the previous session's sandbox.
                probeGen.current++; // invalidate any in-flight probe chains
                if (dnsRetryTimer.current) { clearTimeout(dnsRetryTimer.current); dnsRetryTimer.current = null; }
                setIframeSrc(null);
                previewUrlRef.current = null;
                setPreviewUrl(null);
            };

            socket.onerror = () => {
                if (destroyed) return;
                setMessages(prev => [...prev, { role: "system", content: "Connection hiccup detected. Reconnecting..." }]);
                setStatus("reconnecting");
            };

            socket.onclose = (e) => {
                if (destroyed) return;
                setWsConnected(false);
                // Don't reconnect on auth failure (4401) or not found (4404)
                    if (e.code === 4401) {
                        getAccessToken().then((freshToken) => {
                            if (freshToken && freshToken !== wsToken) {
                                setWsToken(freshToken);
                            }
                        });
                        return;
                    }
                    if (e.code === 4404) return;
                const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 15000);
                reconnectAttempts.current += 1;
                console.log(`WS closed (${e.code}), reconnecting in ${delay}ms...`);
                setStatus("reconnecting");
                reconnectTimer.current = window.setTimeout(connect, delay);
            };

            socket.onmessage = (event) => {
            let data: any;
            try {
                data = JSON.parse(event.data);
            } catch {
                setMessages(prev => [...prev, { role: "system", content: "Received an invalid server message. Please retry." }]);
                setStatus("idle");
                return;
            }

            if (data.type === "status") {
                setStatus(data.status);
                if (data.message) {
                    setMessages(prev => [...prev, { role: "system", content: data.message }]);
                }
            } else if (data.type === "sandbox_failed") {
                setSandboxFailed(true);
                // Unblock the auto-build gate — hasExistingFiles must be set so
                // the editor is usable even without a live sandbox.
                setHasExistingFiles(prev => prev ?? false);
                if (data.message) {
                    setMessages(prev => [...prev, { role: "system", content: data.message }]);
                }
            } else if (data.type === "sandbox_ready") {
                setSandboxFailed(false);
                setStatus("idle"); // build gate passed — clear verifying_build
                const pUrl: string | null = (data.previewUrl && data.previewUrl !== "null" && data.previewUrl !== "") ? data.previewUrl : null;
                if (pUrl) {
                    setPreviewUrl(pUrl);
                    previewUrlRef.current = pUrl;
                }
                if (typeof data.fileCount === "number") {
                    setHasExistingFiles(data.fileCount > 0);
                }
                setMessages(prev => [...prev, { role: "system", content: "Sandbox is ready and connected." }]);
                // Backend already polled health — load preview
                if (pUrl) {
                    setIframeSrc(`${pUrl}?ts=${Date.now()}`);
                    // DNS may not have propagated yet for brand-new sandboxes.
                    // Use a generation counter so stale probe chains from old URLs self-cancel
                    // when a new sandbox_ready arrives (avoids cascading retries from multiple messages).
                    probeGen.current++;
                    if (dnsRetryTimer.current) clearTimeout(dnsRetryTimer.current);
                    const myGen = probeGen.current;
                    const probe = (attempt: number) => {
                        if (probeGen.current !== myGen) return; // cancelled by newer sandbox_ready or reconnect
                        fetch(pUrl, { mode: "no-cors", cache: "no-store" })
                            .then(() => {
                                if (probeGen.current !== myGen) return;
                                // Host is reachable — reload iframe to get clean non-stale version
                                setIframeSrc(`${pUrl}?ts=${Date.now()}`);
                            })
                            .catch(() => {
                                if (probeGen.current !== myGen) return;
                                // DNS not yet resolved or connection failed — retry up to 6 times (~30s)
                                if (attempt < 6) {
                                    dnsRetryTimer.current = window.setTimeout(() => probe(attempt + 1), 5000);
                                }
                            });
                    };
                    dnsRetryTimer.current = window.setTimeout(() => probe(0), 3000);
                }
            } else if (data.type === "file_tree") {
                // Received the sandbox file tree
                console.log("File tree received:", data.tree);
                setFileTree(data.tree);
            } else if (data.type === "agent_status") {
                if (data.data?.message) {
                    setMessages(prev => [...prev, { role: "system", content: data.data.message }]);
                }
            } else if (data.type === "message_history") {
                if (Array.isArray(data.messages)) {
                    setMessages(data.messages);
                }
            } else if (data.type === "file_stream_start") {
                if (!data.file || data.file === "unknown") return;
                console.log(`Streaming file: ${data.file}`);
                setIsStreaming(true);
                setStreamingFile(data.file);
                streamingFileRef.current = data.file;
                streamBuffer.current = "";
                setStatus("streaming");
                // Open the file tab and clear its content for streaming
                setFiles(prev => ({
                    ...prev,
                    [data.file]: ""
                }));
                // Only add to tree, don't spam messages
                setFileTree(prev => addFileToTree(prev, data.file));
            } else if (data.type === "code_token") {
                // Accumulate code characters and flush to state periodically
                streamBuffer.current += data.token;
                // Throttled flush: update React state every 50ms
                if (!flushTimer.current) {
                    flushTimer.current = window.setTimeout(() => {
                        const buffered = streamBuffer.current;
                        const currentFile = streamingFileRef.current;
                        if (currentFile) {
                            setFiles(prev => ({
                                ...prev,
                                [currentFile]: buffered
                            }));
                        }
                        flushTimer.current = null;
                    }, 50);
                }
            } else if (data.type === "file_stream_end") {
                if (!data.file || data.file === "unknown") return;
                console.log(`File stream complete: ${data.file}`);
                // Clear any pending flush
                if (flushTimer.current) {
                    clearTimeout(flushTimer.current);
                    flushTimer.current = null;
                }
                streamBuffer.current = "";
                setFiles(prev => ({
                    ...prev,
                    [data.file]: data.content
                }));
                setMessages(prev => [...prev, { role: "system", content: `✓ Generated ${data.file}` }]);
            } else if (data.type === "stream_end") {
                // All files done streaming — backend is now running the Vite gate
                console.log("Stream ended");
                setIsStreaming(false);
                setStreamingFile(null);
                streamBuffer.current = "";
                setStatus("verifying_build");
            } else if (data.type === "file_written") {
                if (!data.file || data.file === "unknown") return;
                console.log(`File written: ${data.file}`);
                setFiles(prev => ({
                    ...prev,
                    [data.file]: data.content
                }));
                setFileTree(prev => addFileToTree(prev, data.file));
                setMessages(prev => [...prev, { role: "system", content: `✓ Wrote ${data.file}` }]);
            } else if (data.type === "reload_preview") {
                // Backend already confirmed sandbox is healthy — load immediately
                const url = previewUrlRef.current;
                if (!url) return;
                setIframeSrc(`${url}?ts=${Date.now()}`);
                setMessages(m => [...m, { role: "system", content: "\u2713 Preview reloaded" }]);
            } else if (data.type === "edit_success") {
                console.log(`Successfully patched: ${data.file}`);
                setFiles(prev => {
                    const currentContent = prev[data.file] || "";
                    if (!data.search_block) return prev;
                    return {
                        ...prev,
                        [data.file]: currentContent.replace(data.search_block, data.replace_block)
                    };
                });
            } else if (data.type === "auto_fix_status") {
                if (data.status === "fixing") {
                    setStatus("fixing");
                } else if (data.status === "fixed" && data.message) {
                    setMessages(prev => [...prev, { role: "system", content: data.message }]);
                    setStatus("idle");
                } else if (data.status === "skipped" || data.status === "failed") {
                    setStatus("idle");
                }
                // "skipped" and "failed" are silent
            } else if (data.type === "chat_token") {
                if (!assistantStreaming) setAssistantStreaming(true);
                assistantMessageRef.current += data.token;
                setStreamingAssistantMessage(assistantMessageRef.current);
            } else if (data.type === "chat_complete") {
                setAssistantStreaming(false);
                assistantMessageRef.current = "";
                setStreamingAssistantMessage("");
                if (data.message) {
                    setMessages(prev => [...prev, { role: "assistant", content: data.message }]);
                }
            } else if (data.type === "build_stage") {
                setBuildStage({ stage: data.stage, status: data.status });
                if (data.stage && data.status) {
                    setMessages(prev => [...prev, { role: "system", content: `Build: ${data.stage} — ${data.status}` }]);
                }
            } else if (data.type === "patch_proposal") {
                setPatchProposals(prev => [...prev, { file: data.file, diff: data.diff, status: data.status || "pending" }]);
            } else if (data.type === "sandbox_log") {
                setSandboxLogs(prev => {
                    const next = [...prev, { ts: data.ts || Date.now(), level: data.level || "info", message: data.message }];
                    return next.slice(-200);
                });
            } else if (data.type === "security_scan") {
                setSecurityScan({ status: data.status, violations: data.violations || [] });
                if (data.violations?.length) {
                    setMessages(prev => [...prev, { role: "system", content: `Security scan: ${data.violations.length} issue(s) found` }]);
                }
            } else if (data.type === "error") {
                if (data.message === "Authentication failed") {
                    // Token may have expired — force refresh and reconnect
                    console.warn("[useFoundry] Auth failed, refreshing token...");
                    getAccessToken().then(freshToken => {
                        if (freshToken && freshToken !== wsToken) {
                            setWsToken(freshToken);
                        }
                    });
                }
                setMessages(prev => [...prev, { role: "system", content: `Error: ${data.message}` }]);
                setStatus("idle");
                setIsStreaming(false);
                setStreamingFile(null);
                setAssistantStreaming(false);
                assistantMessageRef.current = "";
                setStreamingAssistantMessage("");
            }
            }; // end socket.onmessage
        }; // end connect()

        connect();

        return () => {
            destroyed = true;
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            setWsConnected(false);
            window.removeEventListener("message", handleIframeError);
            window.removeEventListener("error", handleWindowError);
            window.removeEventListener("unhandledrejection", handleWindowRejection);
            if (errorFlushTimer.current) clearTimeout(errorFlushTimer.current);
            if (ws.current) ws.current.close();
        };
    }, [projectId, authLoading, wsToken]);

    const sendCommand = useCallback((prompt: string, model: string = "", images: string[] = []) => {
        setMessages(prev => [...prev, { role: "user", content: prompt || `[${images.length} image(s) attached]` }]);
        const payload = { prompt, model, images };
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify(payload));
        } else {
            pendingCommandRef.current = payload;
            setStatus("reconnecting");
            setMessages(prev => [...prev, { role: "system", content: "Connection is recovering. Your request is queued and will send automatically." }]);
            console.error("WebSocket not connected; queued command for resend");
        }
    }, []);

    return {
        wsConnected,
        status,
        previewUrl,
        iframeSrc,
        setIframeSrc,
        hasExistingFiles,
        files,
        setFiles,
        fileTree,
        messages,
        sendCommand,
        streamingFile,
        isStreaming,
        assistantStreaming,
        streamingAssistantMessage,
        buildStage,
        patchProposals,
        sandboxLogs,
        securityScan,
        sandboxFailed,
    };
}

/**
 * Utility: Add a file path to the tree if it doesn't already exist.
 * e.g. "src/components/Header.tsx" -> creates the src/components dir node and Header.tsx file node
 */
function addFileToTree(tree: TreeNode[], filePath: string): TreeNode[] {
    const parts = filePath.split("/");
    const newTree = [...tree];

    function ensurePath(nodes: TreeNode[], pathParts: string[], currentPath: string): TreeNode[] {
        if (pathParts.length === 0) return nodes;

        const [current, ...rest] = pathParts;
        const fullPath = currentPath ? `${currentPath}/${current}` : current;
        const isFile = rest.length === 0;

        let existing = nodes.find(n => n.name === current);

        if (!existing) {
            if (isFile) {
                nodes.push({ name: current, path: fullPath, type: "file" });
            } else {
                const dirNode: TreeNode = { name: current, path: fullPath, type: "dir", children: [] };
                nodes.push(dirNode);
                ensurePath(dirNode.children!, rest, fullPath);
            }
        } else if (!isFile && existing.type === "dir") {
            existing.children = ensurePath(existing.children || [], rest, fullPath);
        }

        return nodes;
    }

    ensurePath(newTree, parts, "");
    return newTree;
}
