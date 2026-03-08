import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import {
    Palette,
    Monitor,
    Smartphone,
    Tablet,
    Loader2,
    RefreshCw,
    Check,
    CheckCheck,
    Trash2,
    Sparkles,
    Plus,
    X,
    ChevronRight,
    Compass,
    Zap,
    Eye,
    Square,
    StopCircle,
    MessageSquare,
    Maximize2,
    ArrowLeft,
    LayoutGrid,
    Rocket,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════════════
 * TYPES
 * ═══════════════════════════════════════════════════════════════════════ */

interface Mockup {
    id: string;
    name: string;
    description: string;
    priority: "high" | "medium" | "low";
    status: "pending" | "generating" | "complete" | "approved" | "revision_requested" | "error";
    component_code: string | null;
    revision_notes: string | null;
    created_at: string;
}

interface Direction {
    id: string;
    name: string;
    description: string;
    palette: string[];
    style_keywords: string[];
    layout_approach: string;
    html_swatch: string;
}

type Phase = "discovering" | "discovery" | "generating" | "gallery";

const PRIORITY_COLORS: Record<string, string> = {
    high: "text-red-300 bg-red-500/10 border-red-500/30",
    medium: "text-amber-300 bg-amber-500/10 border-amber-500/30",
    low: "text-sky-300 bg-sky-500/10 border-sky-500/30",
};

/* ═══════════════════════════════════════════════════════════════════════
 * DIRECTION PICKER MODAL
 * ═══════════════════════════════════════════════════════════════════════ */

function DirectionPickerModal({
    directions,
    loadingDirections,
    onPick,
    onDescribe,
    onClose,
    onStopLoading,
}: {
    directions: Direction[];
    loadingDirections: boolean;
    onPick: (d: Direction) => void;
    onDescribe: (text: string) => void;
    onClose: () => void;
    onStopLoading: () => void;
}) {
    const [customText, setCustomText] = useState("");

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-[#0E1225] border border-zinc-700/60 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl"
            >
                {/* Header */}
                <div className="p-5 border-b border-zinc-800/60 flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-bold text-white flex items-center gap-2">
                            <Compass className="w-5 h-5 text-purple-400" />
                            New Design Direction
                        </h2>
                        <p className="text-xs text-zinc-400 mt-1">Choose a completely different visual style, or describe your own</p>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Swatches */}
                <div className="flex-1 overflow-y-auto p-5">
                    {loadingDirections ? (
                        <div className="flex flex-col items-center justify-center py-16">
                            <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
                            <p className="text-zinc-400 text-sm">Generating design directions...</p>
                            <p className="text-zinc-600 text-xs mt-1">AI is creating 5 unique visual proposals</p>
                            <button
                                onClick={onStopLoading}
                                className="mt-4 h-8 px-4 rounded-lg bg-red-600/20 hover:bg-red-600/30 border border-red-600/40 text-red-400 text-xs font-medium flex items-center gap-1.5 transition-colors"
                            >
                                <StopCircle className="w-3.5 h-3.5" /> Stop
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            {directions.map((d, i) => (
                                <motion.button
                                    key={d.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.08 }}
                                    onClick={() => onPick(d)}
                                    className="group text-left rounded-xl border border-zinc-800 hover:border-purple-500/50 bg-zinc-900/50 hover:bg-zinc-900/80 overflow-hidden transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/10"
                                >
                                    {/* Rendered swatch */}
                                    <div className="h-[160px] w-full overflow-hidden border-b border-zinc-800">
                                        <iframe
                                            title={`Swatch: ${d.name}`}
                                            srcDoc={d.html_swatch}
                                            className="w-[380px] h-[240px] origin-top-left pointer-events-none"
                                            style={{ transform: "scale(0.72)", transformOrigin: "top left" }}
                                            sandbox="allow-scripts"
                                        />
                                    </div>
                                    <div className="p-3">
                                        <h3 className="text-sm font-bold text-white group-hover:text-purple-300 transition-colors">{d.name}</h3>
                                        <p className="text-xs text-zinc-400 mt-1 line-clamp-2">{d.description}</p>
                                        {/* Palette dots */}
                                        <div className="flex gap-1.5 mt-2">
                                            {d.palette.map((hex, pi) => (
                                                <div key={pi} className="w-4 h-4 rounded-full border border-zinc-700" style={{ background: hex }} title={hex} />
                                            ))}
                                        </div>
                                    </div>
                                </motion.button>
                            ))}
                        </div>
                    )}

                    {/* Custom direction */}
                    <div className="mt-6 p-4 rounded-xl border border-zinc-800 bg-zinc-900/40">
                        <p className="text-xs font-semibold text-zinc-400 mb-2">Or describe your own direction:</p>
                        <textarea
                            value={customText}
                            onChange={(e) => setCustomText(e.target.value)}
                            placeholder="e.g., 'Warm retro palette with cream backgrounds, burnt orange accents, rounded generous spacing, and a magazine-like editorial layout'"
                            className="w-full h-20 rounded-lg bg-zinc-900 border border-zinc-700 text-sm text-zinc-200 p-3 resize-none focus:outline-none focus:border-purple-500/50 placeholder:text-zinc-600"
                        />
                        <button
                            onClick={() => customText.trim() && onDescribe(customText.trim())}
                            disabled={!customText.trim()}
                            className="mt-2 h-8 px-4 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold disabled:opacity-40 flex items-center gap-1.5 transition-colors"
                        >
                            <Sparkles className="w-3.5 h-3.5" /> Apply Custom Direction
                        </button>
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * EXPANDED PREVIEW OVERLAY
 * ═══════════════════════════════════════════════════════════════════════ */

function PreviewOverlay({
    mockup,
    previewDevice,
    setPreviewDevice,
    onClose,
    onRegenerate,
    onApprove,
    onRevise,
    onDelete,
    isRegenerating,
}: {
    mockup: Mockup;
    previewDevice: "desktop" | "tablet" | "mobile";
    setPreviewDevice: (d: "desktop" | "tablet" | "mobile") => void;
    onClose: () => void;
    onRegenerate: () => void;
    onApprove: () => void;
    onRevise: () => void;
    onDelete: () => void;
    isRegenerating: boolean;
}) {
    const deviceContainerClass: Record<string, string> = {
        desktop: "w-full max-w-[1200px]",
        tablet: "w-full max-w-[860px]",
        mobile: "w-full max-w-[430px]",
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex flex-col"
            onClick={onClose}
        >
            {/* Toolbar */}
            <div
                className="h-14 bg-[#0A1020] border-b border-zinc-800/60 px-5 flex items-center justify-between shrink-0"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center gap-3 min-w-0">
                    <button onClick={onClose} className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-white">
                        <X className="w-4 h-4" />
                    </button>
                    <div className="min-w-0">
                        <h3 className="text-sm font-bold text-white truncate">{mockup.name}</h3>
                        <p className="text-xs text-zinc-400 truncate">{mockup.description}</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Device toggle */}
                    <div className="flex items-center gap-1 bg-zinc-800/60 rounded-lg p-1">
                        <button onClick={() => setPreviewDevice("desktop")} className={`p-1.5 rounded ${previewDevice === "desktop" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}><Monitor className="w-4 h-4" /></button>
                        <button onClick={() => setPreviewDevice("tablet")} className={`p-1.5 rounded ${previewDevice === "tablet" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}><Tablet className="w-4 h-4" /></button>
                        <button onClick={() => setPreviewDevice("mobile")} className={`p-1.5 rounded ${previewDevice === "mobile" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}><Smartphone className="w-4 h-4" /></button>
                    </div>

                    <button onClick={onRegenerate} disabled={isRegenerating} className="h-8 px-3 rounded-md border border-zinc-700 text-zinc-300 hover:border-purple-500/60 hover:bg-purple-500/10 text-xs flex items-center gap-1.5 disabled:opacity-40">
                        {isRegenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Regenerate
                    </button>

                    {mockup.status === "complete" && (
                        <>
                            <button onClick={onRevise} className="h-8 px-3 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs">Revise</button>
                            <button onClick={onApprove} className="h-8 px-3 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs flex items-center gap-1.5">
                                <Check className="w-3.5 h-3.5" /> Approve
                            </button>
                        </>
                    )}
                    {mockup.status === "approved" && (
                        <span className="h-8 px-3 rounded-md bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5" /> Approved
                        </span>
                    )}

                    <button onClick={onDelete} className="h-8 w-8 rounded-md flex items-center justify-center text-zinc-500 hover:text-red-400 hover:bg-red-500/10">
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Preview */}
            <div className="flex-1 overflow-auto flex items-start justify-center p-6" onClick={(e) => e.stopPropagation()}>
                {mockup.component_code ? (
                    <div className={`${deviceContainerClass[previewDevice]} rounded-xl border border-zinc-700 bg-zinc-950 overflow-hidden shadow-2xl`}>
                        <div className="h-8 bg-zinc-900 border-b border-zinc-700 flex items-center px-3 gap-2">
                            <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                            <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                            <span className="text-[11px] text-zinc-400 ml-2">{mockup.name}</span>
                        </div>
                        <iframe
                            title={`Preview: ${mockup.name}`}
                            srcDoc={mockup.component_code}
                            className="w-full bg-white"
                            style={{ height: "calc(100vh - 120px)" }}
                            sandbox="allow-scripts"
                        />
                    </div>
                ) : (
                    <div className="text-zinc-500 text-sm mt-32">No preview available</div>
                )}
            </div>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * MAIN COMPONENT
 * ═══════════════════════════════════════════════════════════════════════ */

export default function DesignStudioPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();

    // Core state
    const [mockups, setMockups] = useState<Mockup[]>([]);
    const [loading, setLoading] = useState(true);
    const [phase, setPhase] = useState<Phase>("discovering");
    const [generating, setGenerating] = useState(false);
    const [regeneratingIds, setRegeneratingIds] = useState<Set<string>>(new Set());
    const [error, setError] = useState<string | null>(null);

    // Preview overlay
    const [expandedMockupId, setExpandedMockupId] = useState<string | null>(null);
    const [previewDevice, setPreviewDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");

    // Direction picker
    const [showDirections, setShowDirections] = useState(false);
    const [directions, setDirections] = useState<Direction[]>([]);
    const [loadingDirections, setLoadingDirections] = useState(false);
    const directionsAbortRef = useRef<AbortController | null>(null);
    const [pendingDirection, setPendingDirection] = useState<string | null>(null);

    // Add screen
    const [addScreenName, setAddScreenName] = useState("");

    // Polling
    const pollRef = useRef<number | null>(null);
    const prevStatusRef = useRef<Record<string, string>>({});

    /* ─── API helpers ──────────────────────────────────────────────── */

    const authHeaders = useCallback(async () => {
        const token = await getAccessToken();
        if (!token) return null;
        return { Authorization: `Bearer ${token}` };
    }, [getAccessToken]);

    const ensureAuth = useCallback(async (): Promise<Record<string, string> | null> => {
        const headers = await authHeaders();
        if (!headers) {
            setError("Session expired. Please log in again.");
            navigate("/login", { replace: true });
            return null;
        }
        return headers;
    }, [authHeaders, navigate]);

    const handleApi401 = useCallback((resp: Response) => {
        if (resp.status === 401) navigate("/login", { replace: true });
    }, [navigate]);

    const fetchMockups = useCallback(async () => {
        try {
            const headers = await authHeaders();
            if (!headers) {
                setError("Session expired. Please log in again.");
                setLoading(false);
                navigate("/login", { replace: true });
                return [];
            }
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups`, { headers });
            if (resp.status === 401) {
                navigate("/login", { replace: true });
                setLoading(false);
                return [];
            }
            if (resp.ok) {
                const data = await resp.json();
                const next: Mockup[] = data.mockups || [];
                setMockups(next);
                prevStatusRef.current = Object.fromEntries(next.map((m: Mockup) => [m.id, m.status]));

                // Auto-resume polling if backend is actively generating
                const activelyGenerating = next.some((m: Mockup) => m.status === "generating");
                if (activelyGenerating) {
                    setGenerating(true);
                    setPhase("generating");
                    const token = await getAccessToken();
                    if (token) startPolling(token);
                }

                return next;
            }
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
        return [];
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectId, getAccessToken]);

    /* ─── Auto-discover on mount ──────────────────────────────────── */

    useEffect(() => {
        let cancelled = false;

        async function init() {
            const existing = await fetchMockups();

            // If there are already completed/approved mockups, go to gallery
            const hasCompleted = existing.some(
                (m: Mockup) => m.status === "complete" || m.status === "approved"
            );
            const isGenerating = existing.some((m: Mockup) => m.status === "generating");

            if (isGenerating) {
                setPhase("generating");
            } else if (hasCompleted) {
                setPhase("gallery");
            } else if (existing.length > 0) {
                // Has discovered screens but not generated
                setPhase("discovery");
            } else {
                // No screens at all — auto-discover
                setPhase("discovering");
                if (cancelled) return;
                try {
                    const headers = await authHeaders();
                    if (!headers) {
                        if (!cancelled) navigate("/login", { replace: true });
                        return;
                    }
                    const resp = await fetch(
                        `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/discover`,
                        { method: "POST", headers }
                    );
                    if (resp.status === 401 && !cancelled) {
                        navigate("/login", { replace: true });
                        return;
                    }
                    if (resp.ok) {
                        const data = await resp.json();
                        const screens = (data.screens || []).map((s: any) => ({
                            id: s.id,
                            name: s.name,
                            description: s.description,
                            priority: s.priority,
                            status: s.status,
                            component_code: null,
                            revision_notes: null,
                            created_at: "",
                        })) as Mockup[];
                        if (!cancelled) {
                            setMockups(screens);
                            setPhase("discovery");
                        }
                    }
                } catch (e: any) {
                    if (!cancelled) {
                        setError(e.message);
                        setPhase("discovery");
                    }
                }
            }
        }

        init();
        return () => {
            cancelled = true;
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectId]);

    /* ─── Polling ─────────────────────────────────────────────────── */

    const startPolling = useCallback((token: string) => {
        if (pollRef.current) clearInterval(pollRef.current);

        // Grace period: don't end polling in the first few seconds — the
        // backend needs time to delete old mockups and create new pending rows.
        const startedAt = Date.now();
        const GRACE_MS = 8_000; // 8 seconds

        pollRef.current = window.setInterval(async () => {
            try {
                const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!resp.ok) return;
                const data = await resp.json();
                const next: Mockup[] = data.mockups || [];

                prevStatusRef.current = Object.fromEntries(next.map((m) => [m.id, m.status]));
                setMockups(next);

                const done = next.length > 0 && next.every((m) => m.status !== "generating" && m.status !== "pending");
                if (done && Date.now() - startedAt > GRACE_MS) {
                    setGenerating(false);
                    setRegeneratingIds(new Set());
                    clearInterval(pollRef.current!);
                    pollRef.current = null;
                    // Transition to gallery once generation finishes
                    const anyCompleted = next.some((m) => m.status === "complete" || m.status === "approved");
                    if (anyCompleted) setPhase("gallery");
                    else setPhase("discovery");
                }
            } catch { /* ignore polling errors */ }
        }, 2500);
    }, [projectId]);

    /* ─── Handlers ────────────────────────────────────────────────── */

    const handleGenerateAll = async (direction?: string) => {
        const directionToUse = direction || pendingDirection || null;
        setPendingDirection(null);
        setGenerating(true);
        setPhase("generating");
        setError(null);
        // Mark all existing mockups as pending immediately so the UI shows
        // loading spinners and the poller never concludes "all complete".
        setMockups((prev) =>
            prev.map((m) => ({ ...m, status: "pending" as Mockup["status"], component_code: null }))
        );
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/generate-all`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ design_mode: "ai_free", direction: directionToUse }),
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to start design generation");
            const token = await getAccessToken();
            startPolling(token || "");
        } catch (e: any) {
            setError(e.message);
            setGenerating(false);
            setPhase("discovery");
        }
    };

    const handleRegenerateSingle = async (mockupId: string) => {
        setRegeneratingIds((prev) => new Set(prev).add(mockupId));
        setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "generating" } : m)));
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/generate/${mockupId}`,
                { method: "POST", headers }
            );
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to regenerate");
            const token = await getAccessToken();
            startPolling(token || "");
        } catch (e: any) {
            setError(e.message);
            setRegeneratingIds((prev) => { const s = new Set(prev); s.delete(mockupId); return s; });
            setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "error" } : m)));
        }
    };

    const handleApprove = async (mockupId: string) => {
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/approve`, {
                method: "POST", headers,
            });
            handleApi401(resp);
            setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "approved" } : m)));
        } catch (e: any) { setError(e.message); }
    };

    const handleApproveAll = async () => {
        const toApprove = mockups.filter((m) => m.status === "complete");
        if (!toApprove.length) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const results = await Promise.all(
                toApprove.map((m) =>
                    fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${m.id}/approve`, {
                        method: "POST", headers,
                    })
                )
            );
            if (results.some((r) => r.status === 401)) handleApi401(results[0]);
            setMockups((prev) => prev.map((m) => (m.status === "complete" ? { ...m, status: "approved" } : m)));
        } catch (e: any) { setError(e.message); }
    };

    const handleDelete = async (mockupId: string, mockupName: string) => {
        if (!window.confirm(`Delete "${mockupName}"?`)) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}`,
                { method: "DELETE", headers }
            );
            handleApi401(resp);
            setMockups((prev) => prev.filter((m) => m.id !== mockupId));
            if (expandedMockupId === mockupId) setExpandedMockupId(null);
        } catch (e: any) { setError(e.message); }
    };

    const handleStopAll = async () => {
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/stop`, {
                method: "POST", headers,
            });
            handleApi401(resp);
        } catch { /* best-effort */ } finally {
            setGenerating(false);
            setRegeneratingIds(new Set());
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
            const refreshed = await fetchMockups();
            const anyCompleted = refreshed.some((m: Mockup) => m.status === "complete" || m.status === "approved");
            setPhase(anyCompleted ? "gallery" : "discovery");
        }
    };

    const handleStop = async (mockupId: string) => {
        setRegeneratingIds((prev) => { const s = new Set(prev); s.delete(mockupId); return s; });
        setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "pending" } : m)));
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/stop`,
                { method: "POST", headers }
            );
            handleApi401(resp);
        } catch { /* best-effort */ }
    };

    const handleRequestRevision = async (mockupId: string) => {
        const notes = prompt("What changes would you like to see?");
        if (!notes) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/revise`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ notes }),
            });
            handleApi401(resp);
            fetchMockups();
        } catch (e: any) { setError(e.message); }
    };

    const handleAddScreen = async () => {
        const name = addScreenName.trim();
        if (!name) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/add`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ name, description: "", priority: "important" }),
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to add screen");
            const data = await resp.json();
            setMockups((prev) => [
                ...prev,
                { id: data.id, name: data.name, description: data.description, priority: data.priority, status: data.status, component_code: null, revision_notes: null, created_at: "" },
            ]);
            setAddScreenName("");
        } catch (e: any) { setError(e.message); }
    };

    const handleOpenDirections = async () => {
        setShowDirections(true);
        if (directions.length > 0) return;
        setLoadingDirections(true);
        setError(null);
        const abortCtrl = new AbortController();
        directionsAbortRef.current = abortCtrl;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/directions`, {
                method: "POST", headers, signal: abortCtrl.signal,
            });
            handleApi401(resp);
            if (resp.ok) {
                const data = await resp.json();
                setDirections(data.directions || []);
            } else if (resp.status === 404) {
                setDirections([]);
                setError("Could not load design proposals. Use the text area below to describe your own direction.");
            }
        } catch (e: any) {
            if (e?.name === "AbortError") return;
            setError(e?.message || "Failed to load design directions. Describe your own below.");
        } finally {
            setLoadingDirections(false);
            directionsAbortRef.current = null;
        }
    };

    const handleStopDirections = () => {
        directionsAbortRef.current?.abort();
        setLoadingDirections(false);
    };

    const handlePickDirection = (d: Direction) => {
        setShowDirections(false);
        setDirections([]);
        const directionDesc = `Direction: ${d.name}\nDescription: ${d.description}\nPalette: ${d.palette.join(", ")}\nStyle: ${d.style_keywords.join(", ")}\nLayout: ${d.layout_approach}`;
        handleGenerateAll(directionDesc);
    };

    const handleDescribeDirection = (text: string) => {
        setShowDirections(false);
        setDirections([]);
        handleGenerateAll(`Custom direction from user: ${text}`);
    };

    /* ─── Derived ─────────────────────────────────────────────────── */

    const approvedCount = mockups.filter((m) => m.status === "approved").length;
    const generatedCount = mockups.filter((m) => m.status === "complete" || m.status === "approved").length;
    const expandedMockup = mockups.find((m) => m.id === expandedMockupId) || null;

    const groupedByPriority = {
        high: mockups.filter((m) => m.priority === "high"),
        medium: mockups.filter((m) => m.priority === "medium"),
        low: mockups.filter((m) => m.priority === "low"),
    };

    /* ─── Loading state ───────────────────────────────────────────── */

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            </div>
        );
    }

    /* ═══════════════════════════════════════════════════════════════════════
     * RENDER
     * ═══════════════════════════════════════════════════════════════════════ */

    return (
        <div className="h-[calc(100vh-65px)] bg-[#070913] text-zinc-100 flex flex-col overflow-hidden">
            {/* ── Top bar ──────────────────────────────────────────────── */}
            <div className="h-14 border-b border-zinc-800/60 px-5 flex items-center justify-between bg-[#0A1020] shrink-0">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => navigate(`/project/${projectId}`)}
                        className="flex items-center gap-1.5 h-8 px-2.5 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs transition-colors"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" /> Project
                    </button>
                    <div className="flex items-center gap-2">
                        <Palette className="w-4 h-4 text-purple-300" />
                        <h2 className="text-sm font-bold">Design Studio</h2>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Progress badge */}
                    <span className="text-xs text-zinc-400">
                        {approvedCount} approved &middot; {generatedCount}/{mockups.length || 0} generated
                    </span>

                    {phase === "gallery" && mockups.some((m) => m.status === "complete") && (
                        <button
                            onClick={handleApproveAll}
                            className="h-8 px-3 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5"
                        >
                            <CheckCheck className="w-3.5 h-3.5" /> Approve All
                        </button>
                    )}

                    <button
                        onClick={() => navigate(`/project/${projectId}/editor?autobuild=1`)}
                        className="h-8 px-3 rounded-md bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-purple-500/20"
                    >
                        <Rocket className="w-3.5 h-3.5" /> Build with Kith
                    </button>

                    <button
                        onClick={() => navigate("/")}
                        className="h-8 px-2.5 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs flex items-center gap-1.5"
                    >
                        <LayoutGrid className="w-3.5 h-3.5" /> All Projects
                    </button>
                </div>
            </div>

            {/* ── Main content area ────────────────────────────────────── */}
            <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="wait">
                    {/* ── PHASE: DISCOVERING ──────────────────────────────── */}
                    {phase === "discovering" && (
                        <motion.div
                            key="discovering"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="h-full flex flex-col items-center justify-center"
                        >
                            <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                            >
                                <Compass className="w-12 h-12 text-purple-400" />
                            </motion.div>
                            <p className="text-zinc-300 mt-4 text-sm font-medium">Discovering screens...</p>
                            <p className="text-zinc-600 text-xs mt-1">AI is analyzing your product to determine the right screens</p>

                            {/* Progress timeline */}
                            <div className="mt-8 flex items-center gap-3">
                                {["Analyze", "Infer Screens", "Prioritize"].map((step, i) => (
                                    <div key={step} className="flex items-center gap-2">
                                        <motion.div
                                            initial={{ scale: 0.8, opacity: 0.3 }}
                                            animate={{ scale: 1, opacity: 1 }}
                                            transition={{ delay: i * 0.8, duration: 0.5 }}
                                            className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-300 text-xs font-bold"
                                        >
                                            {i + 1}
                                        </motion.div>
                                        <span className="text-xs text-zinc-500">{step}</span>
                                        {i < 2 && <ChevronRight className="w-3 h-3 text-zinc-700" />}
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {/* ── PHASE: DISCOVERY ────────────────────────────────── */}
                    {phase === "discovery" && (
                        <motion.div
                            key="discovery"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="h-full flex flex-col"
                        >
                            {/* Discovery header */}
                            <div className="px-6 pt-5 pb-4 border-b border-zinc-800/40">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-white">Screens Discovered</h3>
                                        <p className="text-xs text-zinc-400 mt-1">
                                            AI identified {mockups.length} screens for your MVP. Edit, add or remove before generating.
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-zinc-500 mr-2">{mockups.length} screens</span>
                                    </div>
                                </div>
                            </div>

                            {/* Screen cards grid — grouped by priority */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                {(["high", "medium", "low"] as const).map((priority) => {
                                    const items = groupedByPriority[priority];
                                    if (items.length === 0) return null;
                                    const label = priority === "high" ? "Critical" : priority === "medium" ? "Important" : "Nice to Have";
                                    return (
                                        <div key={priority} className="mb-6">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${PRIORITY_COLORS[priority]}`}>
                                                    {label}
                                                </span>
                                                <div className="h-px flex-1 bg-zinc-800/60" />
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                                {items.map((m, i) => (
                                                    <motion.div
                                                        key={m.id}
                                                        initial={{ opacity: 0, y: 10 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: i * 0.05 }}
                                                        className="group rounded-xl border border-zinc-800/60 bg-zinc-900/40 hover:bg-zinc-800/40 hover:border-zinc-700 p-4 transition-all"
                                                    >
                                                        <div className="flex items-start justify-between mb-2">
                                                            <h4 className="text-sm font-bold text-white">{m.name}</h4>
                                                            <button
                                                                onClick={() => handleDelete(m.id, m.name)}
                                                                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition-all"
                                                            >
                                                                <Trash2 className="w-3 h-3" />
                                                            </button>
                                                        </div>
                                                        <p className="text-xs text-zinc-400 line-clamp-2 mb-3">{m.description}</p>
                                                        <div className="flex items-center justify-between">
                                                            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[m.priority]}`}>
                                                                {m.priority}
                                                            </span>
                                                            <button
                                                                onClick={() => handleRegenerateSingle(m.id)}
                                                                className="h-7 px-2.5 rounded-md bg-purple-600/20 hover:bg-purple-600/30 border border-purple-600/30 text-purple-300 text-[11px] font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all"
                                                            >
                                                                <Zap className="w-3 h-3" /> Generate
                                                            </button>
                                                        </div>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Bottom dock */}
                            <div className="border-t border-zinc-800/60 bg-[#0A1020] px-6 py-3 flex items-center gap-3 shrink-0">
                                {/* Add screen input */}
                                <div className="flex items-center gap-2 flex-1 max-w-md">
                                    <Plus className="w-4 h-4 text-zinc-500 shrink-0" />
                                    <input
                                        type="text"
                                        value={addScreenName}
                                        onChange={(e) => setAddScreenName(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleAddScreen()}
                                        placeholder="Add a screen..."
                                        className="flex-1 h-8 bg-zinc-900 border border-zinc-700 rounded-lg px-3 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-purple-500/50"
                                    />
                                    <button
                                        onClick={handleAddScreen}
                                        disabled={!addScreenName.trim()}
                                        className="h-8 px-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 disabled:opacity-30 transition-colors"
                                    >
                                        Add
                                    </button>
                                </div>

                                <div className="flex-1" />

                                {/* Pending direction badge */}
                                {pendingDirection && (
                                    <div className="flex items-center gap-2 h-9 px-3 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs">
                                        <Compass className="w-3.5 h-3.5 shrink-0" />
                                        <span className="truncate max-w-[180px]">{pendingDirection.split("\n")[0].replace("Direction: ", "").replace("Custom direction from user: ", "")}</span>
                                        <button onClick={() => setPendingDirection(null)} className="p-0.5 rounded hover:bg-purple-500/20">
                                            <X className="w-3 h-3" />
                                        </button>
                                    </div>
                                )}

                                {/* New direction */}
                                <button
                                    onClick={handleOpenDirections}
                                    className="h-9 px-4 rounded-lg border border-zinc-700 hover:border-purple-500/40 text-zinc-300 hover:text-purple-300 text-xs font-medium flex items-center gap-2 transition-colors"
                                >
                                    <Compass className="w-3.5 h-3.5" /> {pendingDirection ? "Change Direction" : "New Design Direction"}
                                </button>

                                {/* Generate All */}
                                <button
                                    onClick={() => handleGenerateAll()}
                                    disabled={generating || mockups.length === 0}
                                    className="h-9 px-5 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-500/20"
                                >
                                    <Sparkles className="w-4 h-4" /> {pendingDirection ? "Generate with Direction" : "Generate All"}
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {/* ── PHASE: GENERATING ───────────────────────────────── */}
                    {phase === "generating" && (
                        <motion.div
                            key="generating"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="h-full flex flex-col"
                        >
                            {/* Progress header */}
                            <div className="px-6 pt-5 pb-4 border-b border-zinc-800/40">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                                        <div>
                                            <h3 className="text-lg font-bold text-white">Generating Designs</h3>
                                            <p className="text-xs text-zinc-400 mt-0.5">
                                                {generatedCount}/{mockups.length} complete &mdash; First screen is the north star
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={handleStopAll}
                                        className="h-9 px-4 rounded-lg bg-red-600/20 hover:bg-red-600/30 border border-red-600/40 text-red-400 text-sm font-medium flex items-center gap-2 transition-colors"
                                    >
                                        <StopCircle className="w-4 h-4" /> Stop All
                                    </button>
                                </div>

                                {/* Progress bar */}
                                <div className="mt-3 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-purple-500 to-violet-400 rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: mockups.length > 0 ? `${(generatedCount / mockups.length) * 100}%` : "0%" }}
                                        transition={{ duration: 0.5 }}
                                    />
                                </div>
                            </div>

                            {/* Live preview grid */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                    {mockups.map((m, i) => {
                                        const isGen = m.status === "generating" || regeneratingIds.has(m.id);
                                        const isDone = m.status === "complete" || m.status === "approved";
                                        return (
                                            <motion.div
                                                key={m.id}
                                                initial={{ opacity: 0, scale: 0.95 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: i * 0.04 }}
                                                className={`rounded-xl border overflow-hidden transition-all ${
                                                    isDone ? "border-zinc-700/60 bg-zinc-900/40" : "border-zinc-800/40 bg-zinc-900/20"
                                                }`}
                                            >
                                                {/* Thumbnail area */}
                                                <div className="h-48 relative bg-zinc-950 overflow-hidden">
                                                    {isDone && m.component_code ? (
                                                        <iframe
                                                            title={m.name}
                                                            srcDoc={m.component_code}
                                                            className="w-[1200px] h-[800px] origin-top-left pointer-events-none"
                                                            style={{ transform: "scale(0.3)", transformOrigin: "top left" }}
                                                            sandbox="allow-scripts"
                                                        />
                                                    ) : isGen ? (
                                                        <div className="h-full flex items-center justify-center">
                                                            <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                                                        </div>
                                                    ) : m.status === "error" ? (
                                                        <div className="h-full flex items-center justify-center text-red-400 text-xs">Failed</div>
                                                    ) : (
                                                        <div className="h-full flex items-center justify-center">
                                                            <Palette className="w-6 h-6 text-zinc-700" />
                                                        </div>
                                                    )}
                                                    {/* Stop button for individual */}
                                                    {isGen && (
                                                        <button
                                                            onClick={() => handleStop(m.id)}
                                                            className="absolute top-2 right-2 h-6 px-2 rounded bg-red-600/30 border border-red-600/40 text-red-300 text-[10px] flex items-center gap-1 hover:bg-red-600/40"
                                                        >
                                                            <Square className="w-2.5 h-2.5 fill-current" /> Stop
                                                        </button>
                                                    )}
                                                </div>

                                                {/* Info bar */}
                                                <div className="px-3 py-2.5 border-t border-zinc-800/40">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-semibold text-white truncate">{m.name}</span>
                                                        {isDone && (
                                                            <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-0.5">
                                                                <Check className="w-2.5 h-2.5" /> Done
                                                            </span>
                                                        )}
                                                        {isGen && (
                                                            <span className="text-[10px] text-purple-400">Generating...</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {/* ── PHASE: GALLERY ───────────────────────────────────── */}
                    {phase === "gallery" && (
                        <motion.div
                            key="gallery"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="h-full flex flex-col"
                        >
                            {/* Gallery header */}
                            <div className="px-6 pt-5 pb-4 border-b border-zinc-800/40">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-white">Design Gallery</h3>
                                        <p className="text-xs text-zinc-400 mt-1">
                                            {generatedCount} designs generated &middot; Click to preview and refine
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => setPhase("discovery")}
                                            className="h-8 px-3 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs flex items-center gap-1.5"
                                        >
                                            <Eye className="w-3.5 h-3.5" /> View Screens
                                        </button>
                                        <button
                                            onClick={handleOpenDirections}
                                            className="h-8 px-3 rounded-md border border-zinc-700 hover:border-purple-500/40 text-zinc-300 hover:text-purple-300 text-xs flex items-center gap-1.5 transition-colors"
                                        >
                                            <Compass className="w-3.5 h-3.5" /> New Direction
                                        </button>
                                        <button
                                            onClick={() => handleGenerateAll()}
                                            disabled={generating}
                                            className="h-8 px-4 rounded-md bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                                        >
                                            <RefreshCw className="w-3.5 h-3.5" /> Regenerate All
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Gallery grid */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                                    {mockups.map((m, i) => {
                                        const isDone = m.status === "complete" || m.status === "approved";
                                        const isGen = m.status === "generating" || regeneratingIds.has(m.id);
                                        return (
                                            <motion.div
                                                key={m.id}
                                                initial={{ opacity: 0, y: 15 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.05 }}
                                                className={`group rounded-xl border overflow-hidden bg-zinc-900/40 transition-all cursor-pointer hover:shadow-xl hover:shadow-purple-500/5 ${
                                                    m.status === "approved"
                                                        ? "border-emerald-500/30 hover:border-emerald-500/50"
                                                        : "border-zinc-800/60 hover:border-zinc-600"
                                                }`}
                                                onClick={() => isDone && setExpandedMockupId(m.id)}
                                            >
                                                {/* Thumbnail */}
                                                <div className="h-56 relative bg-zinc-950 overflow-hidden">
                                                    {isDone && m.component_code ? (
                                                        <iframe
                                                            title={m.name}
                                                            srcDoc={m.component_code}
                                                            className="w-[1200px] h-[900px] origin-top-left pointer-events-none"
                                                            style={{ transform: "scale(0.3)", transformOrigin: "top left" }}
                                                            sandbox="allow-scripts"
                                                        />
                                                    ) : isGen ? (
                                                        <div className="h-full flex flex-col items-center justify-center">
                                                            <Loader2 className="w-6 h-6 text-purple-400 animate-spin mb-2" />
                                                            <span className="text-xs text-zinc-500">Generating...</span>
                                                        </div>
                                                    ) : m.status === "error" ? (
                                                        <div className="h-full flex flex-col items-center justify-center">
                                                            <span className="text-red-400 text-xs mb-2">Generation failed</span>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRegenerateSingle(m.id); }}
                                                                className="h-7 px-3 rounded-md border border-zinc-700 text-zinc-300 text-[11px] flex items-center gap-1"
                                                            >
                                                                <RefreshCw className="w-3 h-3" /> Retry
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="h-full flex flex-col items-center justify-center">
                                                            <Palette className="w-6 h-6 text-zinc-700 mb-2" />
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRegenerateSingle(m.id); }}
                                                                className="h-7 px-3 rounded-md bg-purple-600/20 border border-purple-600/30 text-purple-300 text-[11px] flex items-center gap-1"
                                                            >
                                                                <Zap className="w-3 h-3" /> Generate
                                                            </button>
                                                        </div>
                                                    )}

                                                    {/* Expand icon overlay */}
                                                    {isDone && (
                                                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                                                            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-2">
                                                                <Maximize2 className="w-5 h-5 text-white" />
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Status badge */}
                                                    {m.status === "approved" && (
                                                        <div className="absolute top-2 left-2 h-5 px-2 rounded-full bg-emerald-600/80 text-white text-[10px] flex items-center gap-1 backdrop-blur-sm">
                                                            <Check className="w-2.5 h-2.5" /> Approved
                                                        </div>
                                                    )}

                                                    {/* Stop button */}
                                                    {isGen && (
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleStop(m.id); }}
                                                            className="absolute top-2 right-2 h-6 px-2 rounded bg-red-600/30 border border-red-600/40 text-red-300 text-[10px] flex items-center gap-1 hover:bg-red-600/40"
                                                        >
                                                            <Square className="w-2.5 h-2.5 fill-current" /> Stop
                                                        </button>
                                                    )}
                                                </div>

                                                {/* Info bar */}
                                                <div className="px-4 py-3 border-t border-zinc-800/40">
                                                    <div className="flex items-center justify-between mb-1">
                                                        <h4 className="text-sm font-bold text-white truncate">{m.name}</h4>
                                                        <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[m.priority]}`}>
                                                            {m.priority}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-zinc-400 line-clamp-1 mb-2">{m.description}</p>

                                                    {/* Actions */}
                                                    <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        {isGen ? (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleStop(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-red-600/40 text-red-400 hover:bg-red-600/20 flex items-center gap-1"
                                                            >
                                                                <Square className="w-2.5 h-2.5 fill-current" /> Stop
                                                            </button>
                                                        ) : (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRegenerateSingle(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-zinc-700 text-zinc-400 hover:text-white flex items-center gap-1"
                                                            >
                                                                <RefreshCw className="w-2.5 h-2.5" /> Regen
                                                            </button>
                                                        )}
                                                        {m.status === "complete" && (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleApprove(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-emerald-700/60 text-emerald-400 hover:bg-emerald-600/20 flex items-center gap-1"
                                                            >
                                                                <Check className="w-2.5 h-2.5" /> Approve
                                                            </button>
                                                        )}
                                                        {isDone && (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRequestRevision(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-zinc-700 text-zinc-400 hover:text-white flex items-center gap-1"
                                                            >
                                                                <MessageSquare className="w-2.5 h-2.5" /> Revise
                                                            </button>
                                                        )}
                                                        <div className="flex-1" />
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleDelete(m.id, m.name); }}
                                                            className="h-6 w-6 rounded flex items-center justify-center text-zinc-600 hover:text-red-400 hover:bg-red-500/10"
                                                        >
                                                            <Trash2 className="w-3 h-3" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Bottom dock */}
                            <div className="border-t border-zinc-800/60 bg-[#0A1020] px-6 py-3 flex items-center gap-3 shrink-0">
                                <div className="flex items-center gap-2 flex-1 max-w-md">
                                    <Plus className="w-4 h-4 text-zinc-500 shrink-0" />
                                    <input
                                        type="text"
                                        value={addScreenName}
                                        onChange={(e) => setAddScreenName(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleAddScreen()}
                                        placeholder="Add a screen..."
                                        className="flex-1 h-8 bg-zinc-900 border border-zinc-700 rounded-lg px-3 text-xs text-zinc-200 placeholder:text-zinc-600 focus:outline-none focus:border-purple-500/50"
                                    />
                                    <button
                                        onClick={handleAddScreen}
                                        disabled={!addScreenName.trim()}
                                        className="h-8 px-3 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs text-zinc-300 disabled:opacity-30"
                                    >
                                        Add
                                    </button>
                                </div>
                                <div className="flex-1" />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* ── Direction picker modal ────────────────────────────────── */}
            <AnimatePresence>
                {showDirections && (
                    <DirectionPickerModal
                        directions={directions}
                        loadingDirections={loadingDirections}
                        onPick={handlePickDirection}
                        onDescribe={handleDescribeDirection}
                        onClose={() => { setShowDirections(false); handleStopDirections(); }}
                        onStopLoading={handleStopDirections}
                    />
                )}
            </AnimatePresence>

            {/* ── Expanded preview overlay ──────────────────────────────── */}
            <AnimatePresence>
                {expandedMockup && (
                    <PreviewOverlay
                        mockup={expandedMockup}
                        previewDevice={previewDevice}
                        setPreviewDevice={setPreviewDevice}
                        onClose={() => setExpandedMockupId(null)}
                        onRegenerate={() => handleRegenerateSingle(expandedMockup.id)}
                        onApprove={() => handleApprove(expandedMockup.id)}
                        onRevise={() => handleRequestRevision(expandedMockup.id)}
                        onDelete={() => handleDelete(expandedMockup.id, expandedMockup.name)}
                        isRegenerating={regeneratingIds.has(expandedMockup.id) || expandedMockup.status === "generating"}
                    />
                )}
            </AnimatePresence>

            {/* ── Error toast ───────────────────────────────────────────── */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm flex items-center gap-3 z-50"
                    >
                        {error}
                        <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                            <X className="w-4 h-4" />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
