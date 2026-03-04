import { useState, useEffect, useRef, useCallback } from "react";
import type { TreeNode } from "../components/FileExplorer";
import { getWsUrl } from "../lib/runtimeConfig";
import { useAuth } from "../contexts/AuthContext";

const DEFAULT_APP_TSX = `// Your app will appear here after generation
import './App.css'

function App() {
  return (
    <div className="kith-container">
      <h1>Kith Foundry</h1>
      <p>Describe what you want to build...</p>
    </div>
  )
}

export default App
`;

export function useFoundry(projectId?: string) {
    const { getAccessToken, loading: authLoading } = useAuth();

    // Capture the token string into stable state — avoids WS reconnect loop.
    // getAccessToken is now async (fetches fresh session from Supabase).
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
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const previewUrlRef = useRef<string | null>(null);
    const [iframeSrc, setIframeSrc] = useState<string | null>(null);
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

    useEffect(() => {
        // Wait until auth is resolved and we have a token
        if (authLoading || !wsToken) return;

        // Build WS URL with auth token and project ID
        let wsUrl = getWsUrl("/ws/chat");
        const params: string[] = [];
        if (projectId) params.push(`project_id=${encodeURIComponent(projectId)}`);
        params.push(`token=${encodeURIComponent(wsToken)}`);
        wsUrl += `?${params.join("&")}`;

        ws.current = new WebSocket(wsUrl);

        ws.current.onopen = () => {
            console.log("Connected to Kith Foundry backend");
            setWsConnected(true);
        };

        ws.current.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === "status") {
                setStatus(data.status);
                if (data.message) {
                    setMessages(prev => [...prev, { role: "system", content: data.message }]);
                }
            } else if (data.type === "sandbox_ready") {
                setPreviewUrl(data.previewUrl);
                previewUrlRef.current = data.previewUrl;
                if (typeof data.fileCount === "number") {
                    setHasExistingFiles(data.fileCount > 0);
                }
                setMessages(prev => [...prev, { role: "system", content: "Sandbox is ready and connected." }]);
                // Backend already polled health — load preview
                setIframeSrc(`${data.previewUrl}?ts=${Date.now()}`);
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
                // A new file is being streamed by the LLM
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
                // File streaming complete — set final verified content
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
                // All files done streaming
                console.log("Stream ended");
                setIsStreaming(false);
                setStreamingFile(null);
                streamBuffer.current = "";
            } else if (data.type === "file_written") {
                // A file was written to the sandbox — update local state
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
                setIsStreaming(false);
                setStreamingFile(null);
            }
        };

        return () => {
            setWsConnected(false);
            if (ws.current) ws.current.close();
        };
    }, [projectId, authLoading, wsToken]);

    const sendCommand = useCallback((prompt: string, model: string = "", images: string[] = []) => {
        setMessages(prev => [...prev, { role: "user", content: prompt || `[${images.length} image(s) attached]` }]);
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({ prompt, model, images }));
        } else {
            console.error("WebSocket not connected");
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
        fileTree,
        messages,
        sendCommand,
        streamingFile,
        isStreaming
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
