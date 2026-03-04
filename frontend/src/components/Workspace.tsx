import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { Send, Loader2, RefreshCw, FolderTree, Code2, UserCircle, ArrowLeft, LayoutGrid, ExternalLink, ImagePlus, X } from "lucide-react";
import { useFoundry } from "../hooks/useFoundry";
import { ModelSelector } from "./ModelSelector";
import { FileExplorer } from "./FileExplorer";
import { WelcomeScreen } from "./WelcomeScreen";
import { useAuth } from "../contexts/AuthContext";
import { getApiBaseUrl } from "../lib/runtimeConfig";

function LiveCodeBox({ filename, content }: { filename: string; content: string }) {
    const codeRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (codeRef.current) {
            codeRef.current.scrollTop = codeRef.current.scrollHeight;
        }
    }, [content]);

    // Show last 18 lines so the box stays compact but feels alive
    const lines = content.split("\n");
    const visibleLines = lines.slice(-18).join("\n");

    return (
        <div className="rounded-lg border border-indigo-800/50 bg-[#0d1117] overflow-hidden text-xs font-mono shadow-lg shadow-indigo-950/40">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900 border-b border-zinc-800">
                <Loader2 className="w-3 h-3 animate-spin text-indigo-400 shrink-0" />
                <span className="text-indigo-300 truncate flex-1">{filename}</span>
                <span className="text-zinc-600 text-[10px] shrink-0">{lines.length} lines</span>
            </div>
            <div
                ref={codeRef}
                className="p-2.5 h-32 overflow-hidden"
                style={{ maskImage: "linear-gradient(to bottom, transparent 0%, black 25%)" }}
            >
                <pre className="whitespace-pre-wrap break-all text-zinc-400 leading-relaxed">{visibleLines}</pre>
            </div>
        </div>
    );
}

function getLanguage(filename: string): string {
    const ext = filename.split(".").pop() || "";
    const map: Record<string, string> = {
        tsx: "typescript", ts: "typescript",
        jsx: "javascript", js: "javascript",
        css: "css", json: "json", html: "html",
        md: "markdown", svg: "xml"
    };
    return map[ext] || "plaintext";
}

export default function Workspace() {
    const { projectId } = useParams<{ projectId: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();
    const { wsConnected, status, previewUrl, iframeSrc, setIframeSrc, hasExistingFiles, files, fileTree, messages, sendCommand, isStreaming, streamingFile } = useFoundry(projectId);
    const [input, setInput] = useState("");
    const [attachedImages, setAttachedImages] = useState<{ name: string; dataUrl: string }[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [activeFile, setActiveFile] = useState("src/App.tsx");
    const [openTabs, setOpenTabs] = useState<string[]>(["src/App.tsx"]);
    const [selectedModel, setSelectedModel] = useState("");
    const [showExplorer, setShowExplorer] = useState(false);
    const [showEditor, setShowEditor] = useState(false);
    const [hasGenerated, setHasGenerated] = useState(false);
    const [chatWidth, setChatWidth] = useState(340);
    const [explorerWidth, setExplorerWidth] = useState(220);
    const [previewWidth, setPreviewWidth] = useState(420);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const editorRef = useRef<any>(null);
    const bootstrapSentRef = useRef(false);
    const isDragging = useRef<string | null>(null);
    const startX = useRef(0);
    const startWidth = useRef(0);

    // Drag resize handler
    const onMouseDown = useCallback((e: React.MouseEvent, pane: string) => {
        e.preventDefault();
        isDragging.current = pane;
        startX.current = e.clientX;
        if (pane === "chat") startWidth.current = chatWidth;
        else if (pane === "explorer") startWidth.current = explorerWidth;
        else if (pane === "preview") startWidth.current = previewWidth;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        // Block pointer events on iframes during drag
        document.querySelectorAll("iframe").forEach(f => (f.style.pointerEvents = "none"));
    }, [chatWidth, explorerWidth, previewWidth]);

    useEffect(() => {
        const onMouseMove = (e: MouseEvent) => {
            if (!isDragging.current) return;
            const delta = e.clientX - startX.current;
            if (isDragging.current === "chat") {
                setChatWidth(Math.max(240, Math.min(600, startWidth.current + delta)));
            } else if (isDragging.current === "explorer") {
                setExplorerWidth(Math.max(140, Math.min(400, startWidth.current + delta)));
            } else if (isDragging.current === "preview") {
                // Preview resizes from left edge, so dragging left = wider
                setPreviewWidth(Math.max(280, Math.min(900, startWidth.current - delta)));
            }
        };
        const onMouseUp = () => {
            if (isDragging.current) {
                isDragging.current = null;
                document.body.style.cursor = "";
                document.body.style.userSelect = "";
                document.querySelectorAll("iframe").forEach(f => (f.style.pointerEvents = ""));
            }
        };
        window.addEventListener("mousemove", onMouseMove);
        window.addEventListener("mouseup", onMouseUp);
        return () => {
            window.removeEventListener("mousemove", onMouseMove);
            window.removeEventListener("mouseup", onMouseUp);
        };
    }, []);

    // Auto-scroll chat
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // Auto-open files as they are written
    useEffect(() => {
        const fileNames = Object.keys(files);
        setOpenTabs(prev => {
            const newTabs = [...prev];
            for (const f of fileNames) {
                if (!newTabs.includes(f)) {
                    newTabs.push(f);
                }
            }
            return newTabs;
        });
    }, [files]);

    // Auto-switch to file being written & auto-show panes on first generation
    useEffect(() => {
        if (streamingFile && streamingFile !== "generating" && streamingFile !== "Generating...") {
            setActiveFile(streamingFile);
            if (!hasGenerated) {
                setHasGenerated(true);
                setShowExplorer(true);
                setShowEditor(true);
            }
        }
    }, [streamingFile, hasGenerated]);

    // When returning to an existing project, reveal panes without regenerating
    useEffect(() => {
        if (hasExistingFiles && !hasGenerated) {
            setHasGenerated(true);
            setShowExplorer(true);
            setShowEditor(true);
        }
    }, [hasExistingFiles, hasGenerated]);

    // Auto-scroll editor to bottom during streaming
    useEffect(() => {
        if (isStreaming && editorRef.current) {
            const editor = editorRef.current;
            const model = editor.getModel();
            if (model) {
                const lastLine = model.getLineCount();
                editor.revealLine(lastLine, 1); // 1 = immediate scroll
            }
        }
    }, [isStreaming, files[activeFile]]);

    const handleImageAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(e.target.files || []);
        const remaining = 20 - attachedImages.length;
        const toProcess = files.slice(0, remaining);
        toProcess.forEach(file => {
            const reader = new FileReader();
            reader.onload = () => {
                setAttachedImages(prev => [
                    ...prev,
                    { name: file.name, dataUrl: reader.result as string }
                ]);
            };
            reader.readAsDataURL(file);
        });
        // Reset so same file can be re-attached if removed
        e.target.value = "";
    };

    const handlePaste = (e: React.ClipboardEvent) => {
        const items = Array.from(e.clipboardData.items);
        const imageItems = items.filter(item => item.type === "image/png" || item.type.startsWith("image/"));
        if (imageItems.length === 0) return;
        e.preventDefault();
        const remaining = 20 - attachedImages.length;
        imageItems.slice(0, remaining).forEach((item, idx) => {
            const blob = item.getAsFile();
            if (!blob) return;
            const reader = new FileReader();
            reader.onload = () => {
                setAttachedImages(prev => [
                    ...prev,
                    { name: `pasted-image-${Date.now()}-${idx}.png`, dataUrl: reader.result as string }
                ]);
            };
            reader.readAsDataURL(blob);
        });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() && attachedImages.length === 0) return;
        sendCommand(input, selectedModel, attachedImages.map(i => i.dataUrl));
        setInput("");
        setAttachedImages([]);
    };

    const handleFileSelect = (path: string) => {
        setActiveFile(path);
        if (!openTabs.includes(path)) {
            setOpenTabs(prev => [...prev, path]);
        }
    };

    const handleCloseTab = (path: string, e: React.MouseEvent) => {
        e.stopPropagation();
        setOpenTabs(prev => {
            const next = prev.filter(t => t !== path);
            if (activeFile === path && next.length > 0) {
                setActiveFile(next[next.length - 1]);
            }
            return next;
        });
    };

    useEffect(() => {
        const shouldAutoBuild = searchParams.get("autobuild") === "1";
        // hasExistingFiles is null until sandbox_ready arrives — wait for it
        if (!shouldAutoBuild || !projectId || !wsConnected || bootstrapSentRef.current || hasExistingFiles === null) return;
        // Don't re-generate if the project already has persisted files
        if (hasExistingFiles) {
            // Strip the autobuild param so refreshes don't re-check unnecessarily
            const next = new URLSearchParams(searchParams);
            next.delete("autobuild");
            navigate({ search: next.toString() }, { replace: true });
            return;
        }

        const run = async () => {
            try {
                const token = await getAccessToken();
                const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/bootstrap-prompt`, {
                    method: "POST",
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!resp.ok) return;
                const data = await resp.json();
                if (data?.prompt) {
                    bootstrapSentRef.current = true;
                    // Remove autobuild param from URL so page refresh won't regenerate
                    const next = new URLSearchParams(searchParams);
                    next.delete("autobuild");
                    navigate({ search: next.toString() }, { replace: true });
                    sendCommand(data.prompt, selectedModel);
                }
            } catch {
                // Fail silently; manual prompt still works
            }
        };

        run();
    }, [projectId, wsConnected, hasExistingFiles, getAccessToken, sendCommand, searchParams, selectedModel, navigate]);

    useEffect(() => {
        // On each project visit/revisit, default back to chat + preview layout.
        setShowExplorer(false);
        setShowEditor(false);
        setHasGenerated(false);
    }, [projectId]);

    return (
        <>
            <div className="flex h-screen bg-[#0E0E11] text-zinc-100 overflow-hidden font-sans">

                {/* PANE 1: Chat UI */}
                <div style={{ width: chatWidth }} className="flex flex-col border-r border-zinc-800 bg-[#12121A] shrink-0">
                    <div className="p-4 border-b border-zinc-800 flex flex-col gap-3">
                        <div className="flex items-center justify-between">
                            <h1 className="font-bold text-lg bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Kith Foundry</h1>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => projectId && navigate(`/project/${projectId}`)}
                                    disabled={!projectId}
                                    className="p-1.5 rounded-md transition-colors cursor-pointer text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 disabled:opacity-50"
                                    title="Back to project"
                                >
                                    <ArrowLeft className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => navigate("/")}
                                    className="p-1.5 rounded-md transition-colors cursor-pointer text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                                    title="All projects"
                                >
                                    <LayoutGrid className="w-3.5 h-3.5" />
                                </button>
                                <div className="w-px h-4 bg-zinc-700 mx-1" />
                                <Link
                                    to="/profile"
                                    className="p-1.5 rounded-md transition-colors cursor-pointer text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                                    title="Profile & settings"
                                >
                                    <UserCircle className="w-3.5 h-3.5" />
                                </Link>
                                {hasGenerated && (
                                    <>
                                        <button
                                            onClick={() => setShowExplorer(v => !v)}
                                            className={`p-1.5 rounded-md transition-colors cursor-pointer ${showExplorer ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-500 hover:text-zinc-300'}`}
                                            title={showExplorer ? "Hide explorer" : "Show explorer"}
                                        >
                                            <FolderTree className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                            onClick={() => setShowEditor(v => !v)}
                                            className={`p-1.5 rounded-md transition-colors cursor-pointer ${showEditor ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-500 hover:text-zinc-300'}`}
                                            title={showEditor ? "Hide editor" : "Show editor"}
                                        >
                                            <Code2 className="w-3.5 h-3.5" />
                                        </button>
                                        <div className="w-px h-4 bg-zinc-700 mx-1" />
                                    </>
                                )}
                                <div className={`w-2 h-2 rounded-full ${status === 'idle' ? 'bg-green-500' : 'bg-amber-500 animate-pulse'}`}></div>
                                <span className="text-xs text-zinc-400">{status === 'idle' ? 'idle' : status.replace(/_/g, ' ')}</span>
                            </div>
                        </div>
                        <ModelSelector
                            selectedModel={selectedModel}
                            onChange={setSelectedModel}
                        />
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {messages.length === 0 ? (
                            <div className="text-center text-zinc-500 mt-10">
                                <p>What are we building today?</p>
                            </div>
                        ) : (
                            messages.map((msg, i) => (
                                <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                    <div className={`px-3 py-2 rounded-lg max-w-[90%] text-sm ${msg.role === 'user'
                                        ? 'bg-indigo-600 text-white rounded-br-none'
                                        : msg.content.startsWith('✓')
                                            ? 'bg-green-900/30 text-green-300 border border-green-800/40 rounded-bl-none'
                                            : msg.content.startsWith('Error')
                                                ? 'bg-red-900/30 text-red-300 border border-red-800/40 rounded-bl-none'
                                                : 'bg-zinc-800/80 text-zinc-300 rounded-bl-none'
                                        }`}>
                                        {msg.content}
                                    </div>
                                </div>
                            ))
                        )}
                        {isStreaming && streamingFile ? (
                            <LiveCodeBox
                                filename={streamingFile}
                                content={files[streamingFile] || ""}
                            />
                        ) : status !== 'idle' && (
                            <div className="flex items-center gap-2 text-zinc-500 text-sm p-2">
                                <Loader2 className="w-4 h-4 animate-spin" />
                                <span>
                                    {status === "booting_sandbox"
                                        ? "Booting sandbox..."
                                        : status === "applying_edits"
                                            ? "Writing files..."
                                            : status === "analyzing"
                                                ? "Analyzing request using " + (typeof selectedModel === "string" && selectedModel ? selectedModel : "AI") + "..."
                                                : status === "reading"
                                                    ? "Reading current project files..."
                                                    : status === "generating"
                                                        ? "Generating code..."
                                                        : "Working..."}
                                </span>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="p-4 border-t border-zinc-800 space-y-2">
                        {attachedImages.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                {attachedImages.map((img, i) => (
                                    <div key={i} className="relative group w-12 h-12 rounded-md overflow-hidden border border-zinc-700 shrink-0">
                                        <img src={img.dataUrl} alt={img.name} className="w-full h-full object-cover" />
                                        <button
                                            type="button"
                                            onClick={() => setAttachedImages(prev => prev.filter((_, idx) => idx !== i))}
                                            className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity"
                                        >
                                            <X className="w-3.5 h-3.5 text-white" />
                                        </button>
                                    </div>
                                ))}
                                {attachedImages.length < 20 && (
                                    <button
                                        type="button"
                                        onClick={() => fileInputRef.current?.click()}
                                        className="w-12 h-12 rounded-md border border-dashed border-zinc-700 flex items-center justify-center text-zinc-600 hover:text-zinc-400 hover:border-zinc-500 transition-colors shrink-0"
                                    >
                                        <ImagePlus className="w-4 h-4" />
                                    </button>
                                )}
                            </div>
                        )}
                        <form onSubmit={handleSubmit} className="relative">
                            <input
                                type="text"
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onPaste={handlePaste}
                                placeholder="Describe your feature..."
                                className="w-full bg-[#1A1A24] border border-zinc-700 rounded-lg pl-4 pr-20 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-zinc-600"
                            />
                            <div className="absolute right-2 top-2 flex items-center gap-1">
                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={attachedImages.length >= 20}
                                    className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-700 disabled:opacity-50 transition-colors"
                                    title={`Attach PNG images (${attachedImages.length}/20)`}
                                >
                                    <ImagePlus className="w-4 h-4" />
                                </button>
                                <button
                                    type="submit"
                                    disabled={!input.trim() && attachedImages.length === 0}
                                    className="p-1.5 rounded-md text-zinc-400 hover:text-white hover:bg-zinc-700 disabled:opacity-50 transition-colors"
                                >
                                    <Send className="w-4 h-4" />
                                </button>
                            </div>
                        </form>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/png"
                            multiple
                            className="hidden"
                            onChange={handleImageAttach}
                        />
                    </div>
                </div>

                {/* Resize Handle: Chat ↔ Explorer/Editor */}
                <div
                    onMouseDown={(e) => onMouseDown(e, "chat")}
                    className="w-1 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-500/60 bg-transparent transition-colors shrink-0 relative group"
                >
                    <div className="absolute inset-y-0 -left-1 -right-1" />
                </div>

                {/* PANE 2: File Explorer */}
                {showExplorer && (
                    <>
                        <div style={{ width: explorerWidth }} className="border-r border-zinc-800 shrink-0">
                            <FileExplorer
                                tree={fileTree}
                                activeFile={activeFile}
                                onFileSelect={handleFileSelect}
                                streamingFile={streamingFile}
                            />
                        </div>
                        {/* Resize Handle: Explorer ↔ Editor */}
                        <div
                            onMouseDown={(e) => onMouseDown(e, "explorer")}
                            className="w-1 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-500/60 bg-transparent transition-colors shrink-0 relative"
                        >
                            <div className="absolute inset-y-0 -left-1 -right-1" />
                        </div>
                    </>
                )}

                {/* PANE 3: Editor */}
                {showEditor && (
                    <div className="flex-1 flex flex-col min-w-0 bg-[#0A0A0F]">
                        {/* Tabs */}
                        <div className="flex px-1 bg-[#12121A] border-b border-zinc-800 overflow-x-auto scrollbar-none">
                            {openTabs.map((filename) => (
                                <button
                                    key={filename}
                                    onClick={() => setActiveFile(filename)}
                                    className={`flex items-center gap-1.5 px-3 py-2 text-xs font-mono border-t-[2px] whitespace-nowrap shrink-0 group ${activeFile === filename
                                        ? 'border-indigo-500 text-indigo-300 bg-[#0A0A0F]'
                                        : 'border-transparent text-zinc-500 hover:text-zinc-300 hover:bg-[#1A1A24]'
                                        }`}
                                >
                                    {filename.split("/").pop()}
                                    {isStreaming && streamingFile === filename && (
                                        <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                                    )}
                                    <span
                                        onClick={(e) => handleCloseTab(filename, e)}
                                        className="ml-1 opacity-0 group-hover:opacity-100 hover:text-red-400 text-zinc-600 transition-opacity"
                                    >
                                        ×
                                    </span>
                                </button>
                            ))}
                        </div>

                        {/* Monaco Editor */}
                        <div className="flex-1 relative">
                            <Editor
                                height="100%"
                                language={getLanguage(activeFile)}
                                theme="vs-dark"
                                path={activeFile}
                                value={files[activeFile] || "// File not loaded yet"}
                                onMount={(editor) => { editorRef.current = editor; }}
                                options={{
                                    minimap: { enabled: false },
                                    fontSize: 13,
                                    fontFamily: "'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace",
                                    fontLigatures: true,
                                    padding: { top: 12 },
                                    scrollBeyondLastLine: false,
                                    wordWrap: 'on',
                                    lineNumbers: 'on',
                                    renderLineHighlight: 'gutter',
                                    bracketPairColorization: { enabled: true },
                                    guides: { bracketPairs: true, indentation: true },
                                    smoothScrolling: true,
                                    cursorSmoothCaretAnimation: "on",
                                    readOnly: isStreaming && streamingFile === activeFile,
                                }}
                            />
                        </div>
                    </div>
                )}

                {/* Resize Handle: Editor ↔ Preview */}
                <div
                    onMouseDown={(e) => onMouseDown(e, "preview")}
                    className="w-1 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-500/60 bg-transparent transition-colors shrink-0 relative"
                >
                    <div className="absolute inset-y-0 -left-1 -right-1" />
                </div>

                {/* PANE 4: Live Preview */}
                <div style={{ width: (!showExplorer && !showEditor) ? undefined : previewWidth, flex: (!showExplorer && !showEditor) ? 1 : undefined }} className="flex flex-col border-l border-zinc-800 bg-[#0c0c14] shrink-0">
                    <div className="h-10 bg-[#12121A] border-b border-zinc-800 flex items-center px-3 gap-2 z-10">
                        <div className="flex gap-1.5">
                            <div className="w-2.5 h-2.5 rounded-full bg-red-400/80"></div>
                            <div className="w-2.5 h-2.5 rounded-full bg-amber-400/80"></div>
                            <div className="w-2.5 h-2.5 rounded-full bg-green-400/80"></div>
                        </div>
                        <div className="flex-1 bg-[#1A1A24] rounded h-6 px-2 flex items-center text-[11px] text-zinc-500 border border-zinc-700/50 font-mono overflow-hidden whitespace-nowrap">
                            {iframeSrc || "preview"}
                        </div>
                        {previewUrl && (
                            <>
                                <button
                                    onClick={() => setIframeSrc(`${previewUrl}?ts=${Date.now()}`)}
                                    className="p-1 hover:bg-zinc-700 rounded text-zinc-400"
                                    title="Refresh preview"
                                >
                                    <RefreshCw className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => window.open(previewUrl, "_blank", "noopener,noreferrer")}
                                    className="p-1 hover:bg-zinc-700 rounded text-zinc-400"
                                    title="Open in new tab"
                                >
                                    <ExternalLink className="w-3.5 h-3.5" />
                                </button>
                            </>
                        )}
                    </div>

                    <div className="flex-1 relative overflow-hidden">
                        {!iframeSrc ? (
                            <WelcomeScreen />
                        ) : (
                            <iframe
                                src={iframeSrc}
                                className="w-full h-full border-none bg-white"
                                title="Live Preview"
                            />
                        )}
                    </div>
                </div>

            </div>

        </>
    );
}
