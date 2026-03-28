import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams, useSearchParams, Link } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { Send, Loader2, RefreshCw, FolderTree, Code2, UserCircle, ArrowLeft, LayoutGrid, ExternalLink, ImagePlus, X, ChevronDown, ChevronRight, MessageSquare, PanelLeftClose, LogOut, CreditCard, Cpu, Settings, Shield, Terminal, GitBranch } from "lucide-react";
import { useFoundry } from "./hooks/useFoundry";
import { useAutoSave } from "./hooks/useAutoSave";
import { ModelSelector } from "../../components/workspace/ModelSelector";
import { FileExplorer } from "../../components/workspace/FileExplorer";
import { WelcomeScreen } from "../../components/workspace/WelcomeScreen";
import { EditorToolbar, DEFAULT_SETTINGS, type EditorSettings } from "../../components/workspace/EditorToolbar";
import { registerThemes } from "../../components/workspace/EditorThemes";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";

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
            <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--forge-surface)] border-b border-[var(--forge-border)]">
                <Loader2 className="w-3 h-3 animate-spin text-indigo-400 shrink-0" />
                <span className="text-indigo-300 truncate flex-1">{filename}</span>
                <span className="text-zinc-600 text-[10px] shrink-0">{lines.length} lines</span>
            </div>
            <div
                ref={codeRef}
                className="p-2.5 h-32 overflow-hidden"
                style={{ maskImage: "linear-gradient(to bottom, transparent 0%, black 25%)" }}
            >
                <pre className="whitespace-pre-wrap break-all text-[var(--forge-text-secondary)] leading-relaxed">{visibleLines}</pre>
            </div>
        </div>
    );
}

function getLanguage(filename: string): string {
    const ext = filename.split(".").pop()?.toLowerCase() || "";
    const map: Record<string, string> = {
        tsx: "typescript", ts: "typescript", mts: "typescript", cts: "typescript",
        jsx: "javascript", js: "javascript", mjs: "javascript", cjs: "javascript",
        css: "css", scss: "scss", less: "less",
        json: "json", jsonc: "json",
        html: "html", htm: "html",
        md: "markdown", mdx: "markdown",
        svg: "xml", xml: "xml",
        yaml: "yaml", yml: "yaml",
        py: "python", pyw: "python",
        rs: "rust",
        go: "go",
        rb: "ruby",
        java: "java",
        kt: "kotlin",
        swift: "swift",
        c: "c", h: "c",
        cpp: "cpp", hpp: "cpp", cc: "cpp",
        cs: "csharp",
        php: "php",
        sh: "shell", bash: "shell", zsh: "shell",
        sql: "sql",
        graphql: "graphql", gql: "graphql",
        dockerfile: "dockerfile",
        toml: "ini",
        env: "ini",
        ini: "ini",
        lua: "lua",
        r: "r",
    };
    const basename = filename.split("/").pop()?.toLowerCase() || "";
    if (basename === "dockerfile" || basename.startsWith("dockerfile.")) return "dockerfile";
    if (basename === "makefile") return "makefile";
    return map[ext] || "plaintext";
}

/**
 * Lightweight markdown-to-HTML for assistant chat messages.
 * Handles: bold, inline code, code blocks, headers, line breaks.
 * HTML-escapes first to prevent XSS.
 */
function simpleMarkdown(text: string): string {
    // HTML-escape
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Code blocks (```...```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, _lang, code) =>
        `<pre class="bg-zinc-900/50 border border-zinc-700/40 rounded-md p-2 my-1.5 text-xs overflow-x-auto"><code>${code.trim()}</code></pre>`
    );

    // Inline code (`...`)
    html = html.replace(/`([^`]+)`/g, '<code class="bg-zinc-800/60 text-purple-300 px-1 py-0.5 rounded text-xs">$1</code>');

    // Bold (**...**)
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong class="text-zinc-100 font-semibold">$1</strong>');

    // Italic (*...*)
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Headers (### ... and ## ... and # ...)
    html = html.replace(/^### (.+)$/gm, '<div class="font-semibold text-zinc-200 mt-2 mb-0.5 text-xs uppercase tracking-wide">$1</div>');
    html = html.replace(/^## (.+)$/gm, '<div class="font-semibold text-zinc-100 mt-2.5 mb-0.5">$1</div>');
    html = html.replace(/^# (.+)$/gm, '<div class="font-bold text-zinc-50 mt-3 mb-1 text-base">$1</div>');

    // Bullet lists (- ...)
    html = html.replace(/^- (.+)$/gm, '<div class="flex gap-1.5 ml-1"><span class="text-purple-400/70 shrink-0">•</span><span>$1</span></div>');

    // Numbered lists (1. ...)
    html = html.replace(/^(\d+)\. (.+)$/gm, '<div class="flex gap-1.5 ml-1"><span class="text-purple-400/70 shrink-0">$1.</span><span>$2</span></div>');

    return html;
}

export default function Workspace() {
    const { projectId } = useParams<{ projectId: string }>();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { getAccessToken, signOut } = useAuth();
    const { wsConnected, status, previewUrl, iframeSrc, setIframeSrc, hasExistingFiles, files, setFiles, fileTree, messages, sendCommand, isStreaming, streamingFile, assistantStreaming, streamingAssistantMessage, buildStage, patchProposals, sandboxLogs, securityScan, sandboxFailed } = useFoundry(projectId);
    const [input, setInput] = useState("");
    const [attachedImages, setAttachedImages] = useState<{ name: string; dataUrl: string }[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [activeFile, setActiveFile] = useState("src/App.tsx");
    const [openTabs, setOpenTabs] = useState<string[]>(["src/App.tsx"]);
    const [selectedModel, setSelectedModel] = useState("");
    const [showExplorer, setShowExplorer] = useState(false);
    const [showEditor, setShowEditor] = useState(false);
    const [showActivity] = useState(true);
    const [showChat, setShowChat] = useState(true);
    const [showMessages, setShowMessages] = useState(true);
    const [showProfileMenu, setShowProfileMenu] = useState(false);
    const profileMenuRef = useRef<HTMLDivElement>(null);
    const [hasGenerated, setHasGenerated] = useState(false);
    const [chatWidth, setChatWidth] = useState(340);
    const [explorerWidth, setExplorerWidth] = useState(220);
    const [previewWidth, setPreviewWidth] = useState(420);
    const [editorSettings, setEditorSettings] = useState<EditorSettings>(() => {
        try {
            const saved = localStorage.getItem("kith-editor-settings");
            return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
        } catch { return DEFAULT_SETTINGS; }
    });
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const editorRef = useRef<any>(null);
    const monacoRef = useRef<any>(null);
    const bootstrapSentRef = useRef(false);
    const isDragging = useRef<string | null>(null);
    const startX = useRef(0);
    const startWidth = useRef(0);

    // Auto-save manual editor changes to the database; reload preview when save succeeds
    const currentPreviewHref = previewUrl || (iframeSrc ? iframeSrc.split("?")[0] : null);
    const reloadPreview = useCallback(() => {
        if (currentPreviewHref) setIframeSrc(`${currentPreviewHref}?ts=${Date.now()}`);
    }, [currentPreviewHref, setIframeSrc]);
    useAutoSave(projectId, files, 800, { onSaved: reloadPreview });

    // Close profile menu on outside click
    useEffect(() => {
        if (!showProfileMenu) return;
        const handler = (e: MouseEvent) => {
            if (profileMenuRef.current && !profileMenuRef.current.contains(e.target as Node)) {
                setShowProfileMenu(false);
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [showProfileMenu]);

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

    const updateEditorSettings = useCallback((patch: Partial<EditorSettings>) => {
        setEditorSettings(prev => {
            const next = { ...prev, ...patch };
            localStorage.setItem("kith-editor-settings", JSON.stringify(next));
            return next;
        });
    }, []);

    const handleEditorBeforeMount = useCallback((monaco: any) => {
        monacoRef.current = monaco;
        registerThemes(monaco);
    }, []);

    const handleFindReplace = useCallback(() => {
        if (editorRef.current) {
            editorRef.current.getAction("editor.action.startFindReplaceAction")?.run();
        }
    }, []);

    // Auto-scroll chat — on new messages, during streaming, and on status changes
    const streamingContent = streamingFile ? files[streamingFile] : undefined;
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, streamingFile, status, isStreaming, streamingContent, assistantStreaming, streamingAssistantMessage]);

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
            }
        }
    }, [streamingFile, hasGenerated]);

    // When returning to an existing project, reveal panes without regenerating
    useEffect(() => {
        if (hasExistingFiles && !hasGenerated) {
            setHasGenerated(true);
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
        const shouldApplyDesign = searchParams.get("applydesign") === "1";
        const paramKey = shouldApplyDesign ? "applydesign" : "autobuild";

        // hasExistingFiles is null until sandbox_ready arrives — wait for it
        if ((!shouldAutoBuild && !shouldApplyDesign) || !projectId || !wsConnected || bootstrapSentRef.current || hasExistingFiles === null) return;

        // autobuild (from project page): skip if project already has files
        if (shouldAutoBuild && !shouldApplyDesign && hasExistingFiles) {
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
                    const next = new URLSearchParams(searchParams);
                    next.delete(paramKey);
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

    const BUILD_STAGES = ["prd", "design", "capability_gate", "secrets", "sandbox", "code_gen", "validation", "complete"];

    return (
        <>
            <div className="flex flex-col h-screen bg-[#0E0E11] text-zinc-100 overflow-hidden font-sans">

                {/* Build Stage Rail */}
                {buildStage && (
                    <div className="flex items-center gap-1 px-4 py-2 bg-[var(--forge-surface)] border-b border-[var(--forge-border)] shrink-0 overflow-x-auto scrollbar-none">
                        {BUILD_STAGES.map((stage, i) => {
                            const isCurrent = buildStage.stage === stage;
                            const currentIdx = BUILD_STAGES.indexOf(buildStage.stage);
                            const isPast = i < currentIdx;
                            const isError = isCurrent && buildStage.status === "error";
                            return (
                                <div key={stage} className="flex items-center gap-1 shrink-0">
                                    {i > 0 && <div className={`w-6 h-px ${isPast ? "bg-green-500/60" : "bg-zinc-700"}`} />}
                                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-medium ${
                                        isError ? "bg-red-500/10 text-red-400 border border-red-500/30" :
                                        isCurrent ? "bg-[var(--forge-ember)]/10 text-[var(--forge-ember)] border border-[var(--forge-ember)]/30" :
                                        isPast ? "bg-green-500/10 text-green-400" :
                                        "text-zinc-600"
                                    }`}>
                                        {isPast && <span className="text-green-400">&#10003;</span>}
                                        {isCurrent && !isError && <Loader2 className="w-3 h-3 animate-spin" />}
                                        {isError && <Shield className="w-3 h-3" />}
                                        <span>{stage.replace(/_/g, " ")}</span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                <div className="flex flex-1 min-h-0 overflow-hidden">

                {/* PANE 1: Chat UI — collapsible */}
                <div style={{ width: showChat ? chatWidth : 48 }} className="flex flex-col border-r border-[var(--forge-border)] bg-[var(--forge-surface)] shrink-0 overflow-hidden transition-[width] duration-200">
                    {showChat ? (
                        <>
                            <div className="p-4 border-b border-[var(--forge-border)] flex flex-col gap-3">
                                <div className="flex items-center justify-between">
                                    <h1 className="font-bold text-lg bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">Kith Foundry</h1>
                                    <div className="flex items-center gap-1">
                                        <button
                                    onClick={() => projectId && navigate(`/app/projects/${projectId}`)}
                                    disabled={!projectId}
                                    className="p-1.5 rounded-md transition-colors cursor-pointer text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-hover)] disabled:opacity-50"
                                    title="Back to project"
                                >
                                    <ArrowLeft className="w-3.5 h-3.5" />
                                </button>
                                <button
                                    onClick={() => navigate("/app/projects")}
                                    className="p-1.5 rounded-md transition-colors cursor-pointer text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-hover)]"
                                    title="All projects"
                                >
                                    <LayoutGrid className="w-3.5 h-3.5" />
                                </button>
                                <div className="w-px h-4 bg-zinc-700 mx-1" />
                                {/* Profile dropdown */}
                                <div ref={profileMenuRef} className="relative">
                                    <button
                                        onClick={() => setShowProfileMenu(v => !v)}
                                        className={`p-1.5 rounded-md transition-colors cursor-pointer ${showProfileMenu ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-hover)]'}`}
                                        title="Profile & settings"
                                    >
                                        <UserCircle className="w-3.5 h-3.5" />
                                    </button>
                                    {showProfileMenu && (
                                        <div className="absolute left-0 top-full mt-1.5 w-52 bg-[#1a1a24] border border-[var(--forge-border)] rounded-lg shadow-2xl shadow-black/60 z-50 py-1 overflow-hidden">
                                            <div className="px-3 py-2 border-b border-[var(--forge-border)] mb-1">
                                                <p className="text-[11px] font-semibold text-zinc-300">Account</p>
                                            </div>
                                            <Link
                                                to="/app/profile"
                                                onClick={() => setShowProfileMenu(false)}
                                                className="flex items-center gap-2.5 px-3 py-2 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[var(--forge-surface-hover)] transition-colors cursor-pointer"
                                            >
                                                <UserCircle className="w-3.5 h-3.5 shrink-0" />
                                                Profile & Settings
                                            </Link>
                                            <Link
                                                to="/app/profile"
                                                onClick={() => setShowProfileMenu(false)}
                                                className="flex items-center gap-2.5 px-3 py-2 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[var(--forge-surface-hover)] transition-colors cursor-pointer"
                                            >
                                                <Cpu className="w-3.5 h-3.5 shrink-0" />
                                                Model Settings
                                            </Link>
                                            <Link
                                                to="/app/billing"
                                                onClick={() => setShowProfileMenu(false)}
                                                className="flex items-center gap-2.5 px-3 py-2 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[var(--forge-surface-hover)] transition-colors cursor-pointer"
                                            >
                                                <CreditCard className="w-3.5 h-3.5 shrink-0" />
                                                Subscription
                                            </Link>
                                            <Link
                                                to="/app/profile"
                                                onClick={() => setShowProfileMenu(false)}
                                                className="flex items-center gap-2.5 px-3 py-2 text-xs text-zinc-400 hover:text-zinc-100 hover:bg-[var(--forge-surface-hover)] transition-colors cursor-pointer"
                                            >
                                                <Settings className="w-3.5 h-3.5 shrink-0" />
                                                App Settings
                                            </Link>
                                            <div className="border-t border-[var(--forge-border)] mt-1 pt-1">
                                                <button
                                                    onClick={async () => { setShowProfileMenu(false); await signOut(); navigate("/login"); }}
                                                    className="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-red-400 hover:text-red-300 hover:bg-red-950/30 transition-colors cursor-pointer"
                                                >
                                                    <LogOut className="w-3.5 h-3.5 shrink-0" />
                                                    Logout
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                                <button
                                    onClick={() => setShowChat(false)}
                                    className="p-1.5 rounded-md transition-colors cursor-pointer text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-hover)]"
                                    title="Hide chat"
                                >
                                    <PanelLeftClose className="w-3.5 h-3.5" />
                                </button>
                                {hasGenerated && (
                                    <>
                                        <button
                                            onClick={() => setShowExplorer(v => !v)}
                                            className={`p-1.5 rounded-md transition-colors cursor-pointer ${showExplorer ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-500 hover:text-[var(--forge-text-secondary)]'}`}
                                            title={showExplorer ? "Hide explorer" : "Show explorer"}
                                        >
                                            <FolderTree className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                            onClick={() => setShowEditor(v => !v)}
                                            className={`p-1.5 rounded-md transition-colors cursor-pointer ${showEditor ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-500 hover:text-[var(--forge-text-secondary)]'}`}
                                            title={showEditor ? "Hide editor" : "Show editor"}
                                        >
                                            <Code2 className="w-3.5 h-3.5" />
                                        </button>
                                        <button
                                            onClick={() => setShowChat(v => !v)}
                                            className={`p-1.5 rounded-md transition-colors cursor-pointer ${showChat ? 'text-indigo-400 bg-indigo-500/10' : 'text-zinc-500 hover:text-[var(--forge-text-secondary)]'}`}
                                            title={showChat ? "Hide chat" : "Show chat"}
                                        >
                                            <MessageSquare className="w-3.5 h-3.5" />
                                        </button>
                                        <div className="w-px h-4 bg-zinc-700 mx-1" />
                                    </>
                                )}
                                <div className={`w-2 h-2 rounded-full ${status === 'idle' ? 'bg-green-500' : 'bg-amber-500 animate-pulse'}`}></div>
                                <span className="text-xs text-[var(--forge-text-secondary)]">{status === 'idle' ? 'idle' : status.replace(/_/g, ' ')}</span>
                            </div>
                        </div>
                        <ModelSelector
                            selectedModel={selectedModel}
                            onChange={setSelectedModel}
                        />
                    </div>

                    {/* Messages toggle bar */}
                    <button
                        onClick={() => setShowMessages(v => !v)}
                        className="flex items-center gap-2 w-full px-4 py-1.5 border-b border-[var(--forge-border)] text-xs text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-alt)] transition-colors cursor-pointer shrink-0"
                    >
                        {showMessages ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                        <span>Messages {messages.length > 0 ? `(${messages.length})` : ""}</span>
                    </button>

                    <div className={`overflow-y-auto p-4 space-y-3 transition-all duration-200 ${showMessages ? 'flex-1' : 'hidden'}`}>
                        {messages.length === 0 ? (
                            <div className="text-center text-zinc-500 mt-10">
                                <p>What are we building today?</p>
                            </div>
                        ) : (
                            messages.map((msg, i) => {
                                const isActivity = msg.role !== 'user' && msg.role !== 'assistant' && (msg.content.startsWith('✓') || msg.content.startsWith('Saving'));
                                if (isActivity && (!showActivity || showExplorer)) return null;
                                return (
                                    <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                        {msg.role === 'assistant' && (
                                            <span className="text-[10px] text-purple-400/70 mb-0.5 ml-1 font-medium">✦ Kith AI</span>
                                        )}
                                        <div className={`px-3 py-2 rounded-lg max-w-[90%] text-sm ${
                                            msg.role === 'user'
                                                ? 'bg-indigo-600 text-white rounded-br-none'
                                                : msg.role === 'assistant'
                                                    ? 'bg-purple-900/20 text-zinc-200 border border-purple-700/30 rounded-bl-none'
                                                    : msg.content.startsWith('✓')
                                                        ? 'bg-green-900/30 text-green-300 border border-green-800/40 rounded-bl-none'
                                                        : msg.content.startsWith('Error')
                                                            ? 'bg-red-900/30 text-red-300 border border-red-800/40 rounded-bl-none'
                                                            : 'bg-[var(--forge-surface-alt)] text-[var(--forge-text-secondary)] rounded-bl-none'
                                        }`}>
                                            {msg.role === 'assistant' ? (
                                                <div className="whitespace-pre-wrap leading-relaxed" dangerouslySetInnerHTML={{__html: simpleMarkdown(msg.content)}} />
                                            ) : (
                                                msg.content
                                            )}
                                        </div>
                                    </div>
                                );
                            })
                        )}
                        {/* Streaming assistant message */}
                        {assistantStreaming && streamingAssistantMessage && (
                            <div className="flex flex-col items-start">
                                <span className="text-[10px] text-purple-400/70 mb-0.5 ml-1 font-medium">✦ Kith AI</span>
                                <div className="px-3 py-2 rounded-lg max-w-[90%] text-sm bg-purple-900/20 text-zinc-200 border border-purple-700/30 rounded-bl-none">
                                    <div className="whitespace-pre-wrap leading-relaxed" dangerouslySetInnerHTML={{__html: simpleMarkdown(streamingAssistantMessage)}} />
                                    <span className="inline-block w-1.5 h-4 bg-purple-400/60 animate-pulse ml-0.5 align-text-bottom" />
                                </div>
                            </div>
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
                                            ? "Saving files..."
                                            : status === "verifying_build"
                                                ? "Verifying build..."
                                                : status === "analyzing"
                                                    ? "Analyzing request using " + (typeof selectedModel === "string" && selectedModel ? selectedModel : "AI") + "..."
                                                    : status === "reading"
                                                        ? "Reading current project files..."
                                                        : status === "generating"
                                                            ? "Generating code..."
                                                            : status === "reconnecting"
                                                                ? "Reconnecting to server..."
                                                                : "Working..."}
                                </span>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    <div className="p-4 border-t border-[var(--forge-border)] space-y-2">
                        {attachedImages.length > 0 && (
                            <div className="flex flex-wrap gap-1.5">
                                {attachedImages.map((img, i) => (
                                    <div key={i} className="relative group w-12 h-12 rounded-md overflow-hidden border border-[var(--forge-border-muted)] shrink-0">
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
                                        className="w-12 h-12 rounded-md border border-dashed border-[var(--forge-border-muted)] flex items-center justify-center text-zinc-600 hover:text-[var(--forge-text-secondary)] hover:border-zinc-500 transition-colors shrink-0"
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
                                className="w-full bg-[var(--forge-surface-alt)] border border-[var(--forge-border-muted)] rounded-lg pl-4 pr-20 py-3 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-all placeholder:text-[var(--forge-text-faint)]"
                            />
                            <div className="absolute right-2 top-2 flex items-center gap-1">
                                <button
                                    type="button"
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={attachedImages.length >= 20}
                                    className="p-1.5 rounded-md text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-hover)] disabled:opacity-50 transition-colors"
                                    title={`Attach PNG images (${attachedImages.length}/20)`}
                                >
                                    <ImagePlus className="w-4 h-4" />
                                </button>
                                <button
                                    type="submit"
                                    disabled={(!input.trim() && attachedImages.length === 0) || !wsConnected}
                                    className="p-1.5 rounded-md text-[var(--forge-text-secondary)] hover:text-[var(--forge-text)] hover:bg-[var(--forge-surface-hover)] disabled:opacity-50 transition-colors"
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
                        </>
                    ) : (
                        <button
                            onClick={() => setShowChat(true)}
                            className="w-full h-full min-h-[200px] flex flex-col items-center justify-center gap-2 text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-alt)] transition-colors cursor-pointer border-0"
                            title="Show chat"
                        >
                            <MessageSquare className="w-6 h-6" />
                            <span className="text-[10px] font-medium">Chat</span>
                        </button>
                    )}
                </div>

                {/* Resize Handle: Chat ↔ Editor/Preview (hidden when chat collapsed) */}
                {showChat && (
                    <div
                        onMouseDown={(e) => onMouseDown(e, "chat")}
                        className="w-1 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-500/60 bg-transparent transition-colors shrink-0 relative group"
                    >
                        <div className="absolute inset-y-0 -left-1 -right-1" />
                    </div>
                )}

                {/* PANE 3: Editor */}
                {showEditor && (
                    <div className="flex-1 flex flex-col min-w-0 bg-[#0A0A0F]">
                        {/* Tabs */}
                        <div className="flex px-1 bg-[var(--forge-surface)] border-b border-[var(--forge-border)] overflow-x-auto scrollbar-none">
                            {openTabs.map((filename) => (
                                <button
                                    key={filename}
                                    onClick={() => setActiveFile(filename)}
                                    className={`flex items-center gap-1.5 px-3 py-2 text-xs font-mono border-t-[2px] whitespace-nowrap shrink-0 group ${activeFile === filename
                                        ? 'border-indigo-500 text-indigo-300 bg-[#0A0A0F]'
                                        : 'border-transparent text-zinc-500 hover:text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-alt)]'
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

                        {/* Breadcrumb */}
                        <div className="flex items-center gap-1 px-3 py-1 bg-[#0F0F17] border-b border-[var(--forge-border)]/40 text-[11px] text-zinc-500 overflow-x-auto scrollbar-none">
                            {activeFile.split("/").map((seg, i, arr) => (
                                <span key={i} className="flex items-center gap-1 shrink-0">
                                    {i > 0 && <ChevronRight className="w-2.5 h-2.5 opacity-40" />}
                                    <span className={i === arr.length - 1 ? "text-[var(--forge-text-secondary)]" : "hover:text-[var(--forge-text-secondary)] cursor-default"}>{seg}</span>
                                </span>
                            ))}
                        </div>

                        {/* Editor Toolbar */}
                        <EditorToolbar
                            settings={editorSettings}
                            onChange={updateEditorSettings}
                            onFindReplace={handleFindReplace}
                        />

                        {/* Monaco Editor */}
                        <div className="flex-1 relative">
                            <Editor
                                height="100%"
                                language={getLanguage(activeFile)}
                                theme={editorSettings.theme}
                                path={activeFile}
                                value={files[activeFile] || "// File not loaded yet"}
                                beforeMount={handleEditorBeforeMount}
                                onMount={(editor) => { editorRef.current = editor; }}
                                options={{
                                    minimap: { enabled: editorSettings.minimap },
                                    fontSize: editorSettings.fontSize,
                                    tabSize: editorSettings.tabSize,
                                    fontFamily: "'JetBrains Mono', 'Cascadia Code', 'Fira Code', monospace",
                                    fontLigatures: editorSettings.fontLigatures,
                                    padding: { top: 12 },
                                    scrollBeyondLastLine: false,
                                    wordWrap: editorSettings.wordWrap,
                                    lineNumbers: editorSettings.lineNumbers,
                                    renderLineHighlight: 'gutter',
                                    bracketPairColorization: { enabled: editorSettings.bracketPairColorization },
                                    guides: { bracketPairs: true, indentation: true },
                                    smoothScrolling: true,
                                    cursorSmoothCaretAnimation: "on",
                                    cursorBlinking: editorSettings.cursorBlinking,
                                    renderWhitespace: editorSettings.renderWhitespace,
                                    stickyScroll: { enabled: editorSettings.stickyScroll },
                                    readOnly: isStreaming && streamingFile === activeFile,
                                    suggest: {
                                        showKeywords: true,
                                        showSnippets: true,
                                        showClasses: true,
                                        showFunctions: true,
                                        showVariables: true,
                                        showModules: true,
                                        showProperties: true,
                                        showInterfaces: true,
                                        showConstants: true,
                                    },
                                    quickSuggestions: { other: true, comments: false, strings: true },
                                    parameterHints: { enabled: true },
                                    autoClosingBrackets: "always",
                                    autoClosingQuotes: "always",
                                    autoIndent: "full",
                                    formatOnPaste: true,
                                    linkedEditing: true,
                                    colorDecorators: true,
                                    folding: true,
                                    foldingHighlight: true,
                                    showFoldingControls: "mouseover",
                                    matchBrackets: "always",
                                    occurrencesHighlight: "singleFile",
                                    selectionHighlight: true,
                                    dragAndDrop: true,
                                    links: true,
                                    find: {
                                        addExtraSpaceOnTop: true,
                                        autoFindInSelection: "multiline",
                                        seedSearchStringFromSelection: "selection",
                                    },
                                    hover: { enabled: true, delay: 300 },
                                    inlayHints: { enabled: "on" },
                                }}
                                onChange={(value) => {
                                    if (value !== undefined && !(isStreaming && streamingFile === activeFile)) {
                                        setFiles(prev => ({
                                            ...prev,
                                            [activeFile]: value,
                                        }));
                                    }
                                }}
                            />
                        </div>
                    </div>
                )}

                {/* Resize Handle: Editor ↔ Preview (only shown when editor is visible) */}
                {showEditor && (
                    <div
                        onMouseDown={(e) => onMouseDown(e, "preview")}
                        className="w-1 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-500/60 bg-transparent transition-colors shrink-0 relative"
                    >
                        <div className="absolute inset-y-0 -left-1 -right-1" />
                    </div>
                )}

                {/* PANE 4: Live Preview */}
                <div style={{ width: showEditor ? previewWidth : undefined, flex: showEditor ? undefined : 1 }} className="flex flex-col border-l border-[var(--forge-border)] bg-[#0c0c14] shrink-0">
                    <div className="h-10 bg-[var(--forge-surface)] border-b border-[var(--forge-border)] flex items-center px-3 gap-2 z-10">
                        <div className="flex gap-1.5">
                            <div className="w-2.5 h-2.5 rounded-full bg-red-400/80"></div>
                            <div className="w-2.5 h-2.5 rounded-full bg-amber-400/80"></div>
                            <div className="w-2.5 h-2.5 rounded-full bg-green-400/80"></div>
                        </div>
                        <div className="flex-1 bg-[var(--forge-surface-alt)] rounded h-6 px-2 flex items-center text-[11px] text-zinc-500 border border-[var(--forge-border)] font-mono overflow-hidden whitespace-nowrap">
                            {iframeSrc || "preview"}
                        </div>
                        <>
                            <button
                                onClick={reloadPreview}
                                disabled={!currentPreviewHref}
                                className="flex items-center gap-1.5 px-2 py-1 rounded text-[var(--forge-text-secondary)] hover:text-[var(--forge-text)] hover:bg-[var(--forge-surface-hover)] transition-colors text-[11px] font-medium disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                                title={currentPreviewHref ? "Refresh preview" : "Preview not available yet"}
                            >
                                <RefreshCw className="w-3.5 h-3.5" />
                                <span>Refresh</span>
                            </button>
                            <button
                                onClick={() => currentPreviewHref && window.open(currentPreviewHref, "_blank", "noopener,noreferrer")}
                                disabled={!currentPreviewHref}
                                className="p-1 rounded text-[var(--forge-text-secondary)] hover:bg-[var(--forge-surface-hover)] hover:text-[var(--forge-text)] disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-transparent"
                                title={currentPreviewHref ? "Open in new tab" : "Preview not available yet"}
                            >
                                <ExternalLink className="w-3.5 h-3.5" />
                            </button>
                        </>
                    </div>

                    <div className="flex-1 relative overflow-hidden">
                        {sandboxFailed && !iframeSrc && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-[#0c0c14] z-10 p-6 text-center">
                                <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                                    <span className="text-amber-400 text-xl">⚡</span>
                                </div>
                                <div>
                                    <p className="text-zinc-200 font-medium">Sandbox couldn't start</p>
                                    <p className="text-zinc-500 text-sm mt-1">You can still edit files. Reload the page to retry the sandbox.</p>
                                </div>
                                <button
                                    onClick={() => window.location.reload()}
                                    className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
                                >
                                    Retry sandbox
                                </button>
                            </div>
                        )}
                        {!iframeSrc && !sandboxFailed ? (
                            <WelcomeScreen />
                        ) : iframeSrc ? (
                            <iframe
                                key={iframeSrc}
                                ref={(el) => {
                                    if (!el) return;
                                    el.onload = () => {
                                        try {
                                            const iframeWindow = el.contentWindow;
                                            if (!iframeWindow) return;
                                            // Inject error capture script into preview iframe
                                            const script = iframeWindow.document.createElement("script");
                                            script.textContent = `
                                                (function() {
                                                    var reported = {};
                                                    function report(source, message, stack) {
                                                        var key = source + ':' + message;
                                                        if (reported[key]) return;
                                                        reported[key] = true;
                                                        window.parent.postMessage({
                                                            type: 'preview-error',
                                                            source: source,
                                                            message: message,
                                                            stack: stack || ''
                                                        }, '*');
                                                    }
                                                    window.onerror = function(msg, url, line, col, err) {
                                                        report('runtime', String(msg), err ? err.stack : url + ':' + line);
                                                    };
                                                    window.addEventListener('unhandledrejection', function(e) {
                                                        var msg = e.reason ? (e.reason.message || String(e.reason)) : 'Unhandled rejection';
                                                        report('promise', msg, e.reason ? e.reason.stack : '');
                                                    });
                                                    var origError = console.error;
                                                    console.error = function() {
                                                        var msg = Array.prototype.slice.call(arguments).join(' ');
                                                        if (msg.length > 20) report('console', msg.substring(0, 500));
                                                        origError.apply(console, arguments);
                                                    };
                                                })();
                                            `;
                                            iframeWindow.document.head.appendChild(script);
                                        } catch (e) {
                                            // Cross-origin iframe — can't inject (expected for sandbox URLs)
                                        }
                                    };
                                }}
                                src={iframeSrc}
                                className="w-full h-full border-none bg-white"
                                title="Live Preview"
                                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                            />
                        ) : null}
                    </div>
                </div>

                {/* Resize Handle: Preview ↔ Explorer (only shown when explorer is visible) */}
                {showExplorer && (
                    <div
                        onMouseDown={(e) => onMouseDown(e, "explorer")}
                        className="w-1 cursor-col-resize hover:bg-indigo-500/40 active:bg-indigo-500/60 bg-transparent transition-colors shrink-0 relative"
                    >
                        <div className="absolute inset-y-0 -left-1 -right-1" />
                    </div>
                )}

                {/* PANE 5: File Explorer + Activity Log (right side) */}
                {showExplorer && (
                    <div style={{ width: explorerWidth }} className="flex flex-col border-l border-[var(--forge-border)] shrink-0">
                        <div className="flex-1 min-h-0 overflow-hidden">
                            <FileExplorer
                                tree={fileTree}
                                activeFile={activeFile}
                                onFileSelect={handleFileSelect}
                                streamingFile={streamingFile}
                            />
                        </div>
                        {showActivity && (() => {
                            const activityMsgs = messages.filter(m => m.role !== 'user' && (m.content.startsWith('✓') || m.content.startsWith('Saving')));
                            if (activityMsgs.length === 0) return null;
                            return (
                                <div className="border-t border-[var(--forge-border)] max-h-[45%] flex flex-col shrink-0">
                                    <div className="px-3 py-2 flex items-center justify-between border-b border-[var(--forge-border)]">
                                        <span className="text-[11px] font-semibold text-[var(--forge-text-secondary)] uppercase tracking-wider">Activity</span>
                                        <span className="text-[10px] text-zinc-600">{activityMsgs.length}</span>
                                    </div>
                                    <div className="flex-1 overflow-y-auto p-2 space-y-1">
                                        {activityMsgs.map((msg, i) => (
                                            <div key={i} className="px-2 py-1 rounded text-[11px] bg-green-900/20 text-green-300/80 border border-green-900/20 truncate">
                                                {msg.content}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            );
                        })()}

                        {/* Sandbox Logs Panel */}
                        {sandboxLogs.length > 0 && (
                            <div className="border-t border-[var(--forge-border)] max-h-[30%] flex flex-col shrink-0">
                                <div className="px-3 py-2 flex items-center gap-2 border-b border-[var(--forge-border)]">
                                    <Terminal className="w-3 h-3 text-zinc-500" />
                                    <span className="text-[11px] font-semibold text-[var(--forge-text-secondary)] uppercase tracking-wider">Sandbox Logs</span>
                                    <span className="text-[10px] text-zinc-600 ml-auto">{sandboxLogs.length}</span>
                                </div>
                                <div className="flex-1 overflow-y-auto p-2 space-y-0.5 font-mono text-[10px]">
                                    {sandboxLogs.slice(-50).map((log, i) => (
                                        <div key={i} className={`px-1.5 py-0.5 rounded ${
                                            log.level === "error" ? "text-red-400 bg-red-900/10" :
                                            log.level === "warn" ? "text-amber-400 bg-amber-900/10" :
                                            "text-zinc-500"
                                        }`}>
                                            {log.message}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Patch Proposals Panel */}
                        {patchProposals.length > 0 && (
                            <div className="border-t border-[var(--forge-border)] max-h-[25%] flex flex-col shrink-0">
                                <div className="px-3 py-2 flex items-center gap-2 border-b border-[var(--forge-border)]">
                                    <GitBranch className="w-3 h-3 text-zinc-500" />
                                    <span className="text-[11px] font-semibold text-[var(--forge-text-secondary)] uppercase tracking-wider">Patches</span>
                                    <span className="text-[10px] text-zinc-600 ml-auto">{patchProposals.length}</span>
                                </div>
                                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                                    {patchProposals.map((patch, i) => (
                                        <div key={i} className="px-2 py-1.5 rounded text-[11px] bg-[var(--forge-surface-alt)] border border-[var(--forge-border-muted)]">
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="text-zinc-300 font-mono truncate">{patch.file}</span>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                                                    patch.status === "applied" ? "bg-green-900/30 text-green-400" :
                                                    patch.status === "rejected" ? "bg-red-900/30 text-red-400" :
                                                    "bg-zinc-800 text-zinc-500"
                                                }`}>{patch.status}</span>
                                            </div>
                                            <pre className="text-[10px] text-zinc-600 whitespace-pre-wrap max-h-16 overflow-hidden">{patch.diff?.slice(0, 200)}</pre>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Security Scan Panel */}
                        {securityScan && securityScan.violations.length > 0 && (
                            <div className="border-t border-red-500/30 max-h-[20%] flex flex-col shrink-0">
                                <div className="px-3 py-2 flex items-center gap-2 border-b border-red-500/20 bg-red-950/20">
                                    <Shield className="w-3 h-3 text-red-400" />
                                    <span className="text-[11px] font-semibold text-red-400 uppercase tracking-wider">Security</span>
                                    <span className="text-[10px] text-red-500/60 ml-auto">{securityScan.violations.length} issue(s)</span>
                                </div>
                                <div className="flex-1 overflow-y-auto p-2 space-y-1">
                                    {securityScan.violations.map((v, i) => (
                                        <div key={i} className="px-2 py-1 rounded text-[11px] bg-red-900/10 text-red-300 border border-red-900/20">
                                            <span className="text-red-500 font-medium">[{v.category}]</span> {v.detail}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                </div>{/* end inner flex-1 row */}

            </div>{/* end outer flex-col */}

        </>
    );
}
