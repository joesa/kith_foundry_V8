import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import {
    Palette,
    Loader2,
    RefreshCw,
    Sparkles,
    X,
    Compass,
    ArrowLeft,
    LayoutGrid,
    Rocket,
} from "lucide-react";
import { Lock, Unlock } from "lucide-react";

/* ═══════════════════════════════════════════════════════════════════════
 * TYPES
 * ═══════════════════════════════════════════════════════════════════════ */

type Phase = "discovering" | "discovery" | "generating" | "gallery";

interface EngineDesignSystem {
  product_overview?: { name?: string; positioning?: string; key_features?: string[]; target_users?: string[] };
  design_tokens?: {
    colors?: Record<string, string>;
    typography?: Record<string, any>;
    spacing?: Record<string, string>;
    borders?: Record<string, string>;
    shadows?: Record<string, string>;
    animations?: Record<string, string>;
  };
  layout_architecture?: Record<string, any>;
  component_specifications?: Array<{ name: string; type?: string; variants?: string[]; css_class?: string; behavior?: string }>;
  interaction_patterns?: Record<string, any>;
  anti_patterns?: string[];
  mode_context?: { product_mode?: string; style_mode?: string };
}

interface CurrentDesignMode {
    productMode: string | null;
    styleMode: string | null;
    confidence: number | null;
    lockedByUser: boolean;
}

interface DesignModeOptions {
    productModes: string[];
    styleModes: string[];
    currentDesignMode?: CurrentDesignMode;
}

interface ProjectSummary {
    name?: string;
}

/* ═══════════════════════════════════════════════════════════════════════
 * DESIGN MODE MODAL
 * ═══════════════════════════════════════════════════════════════════════ */

function DesignModeModal({
    options,
    value,
    recommendedPatterns,
    saving,
    classifying,
    autoDetectedSelection,
    onChange,
    onAutoDetect,
    onApplyAutoSelection,
    onSaveAndLock,
    onUnlock,
    onClose,
}: {
    options: DesignModeOptions;
    value: CurrentDesignMode;
    recommendedPatterns: string[];
    saving: boolean;
    classifying: boolean;
    autoDetectedSelection: CurrentDesignMode | null;
    onChange: (next: CurrentDesignMode) => void;
    onAutoDetect: () => void;
    onApplyAutoSelection: () => void;
    onSaveAndLock: () => void;
    onUnlock: () => void;
    onClose: () => void;
}) {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                className="relative w-full max-w-2xl bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl shadow-2xl overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="px-6 pt-5 pb-4 border-b border-[var(--kf-border)]/40">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30">
                                <Palette className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-[var(--kf-text)]">Design Mode + Style</h2>
                                <p className="text-xs text-[var(--kf-text-secondary)]">Auto-detect the best layout system or lock a manual override</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[var(--kf-hover-bg)] text-[var(--kf-text-faint)]">
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                <div className="px-6 py-5 space-y-5 max-h-[65vh] overflow-y-auto">
                    <div className="flex items-center justify-between gap-3 rounded-xl border border-[var(--kf-border-muted)] bg-[var(--kf-bg)] px-4 py-3">
                        <div>
                            <div className="text-sm font-semibold text-[var(--kf-text)]">Current Selection</div>
                            <div className="text-xs text-[var(--kf-text-secondary)] mt-1">
                                {value.productMode && value.styleMode
                                    ? `${value.productMode} / ${value.styleMode}`
                                    : "No design mode selected yet"}
                            </div>
                            {value.confidence !== null && (
                                <div className="text-[11px] text-[var(--kf-text-faint)] mt-1">
                                    Confidence: {Math.round(value.confidence * 100)}%
                                </div>
                            )}
                        </div>
                        <div className={`text-[11px] px-2 py-1 rounded-full border ${value.lockedByUser ? "border-emerald-500/30 text-emerald-300 bg-emerald-500/10" : "border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] bg-[var(--kf-badge-bg)]"}`}>
                            {value.lockedByUser ? "Locked" : "Auto"}
                        </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                        <div>
                            <label className="text-sm font-semibold text-[var(--kf-text)] mb-2 block">Product Mode</label>
                            <select
                                value={value.productMode || ""}
                                onChange={(e) => onChange({ ...value, productMode: e.target.value || null, lockedByUser: false })}
                                className="w-full h-11 rounded-xl bg-[var(--kf-bg)] border border-[var(--kf-border-muted)] px-3 text-sm text-[var(--kf-text)] focus:outline-none focus:border-purple-500/50"
                            >
                                <option value="">Auto-select</option>
                                {options.productModes.map((mode) => (
                                    <option key={mode} value={mode}>{mode}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="text-sm font-semibold text-[var(--kf-text)] mb-2 block">Style Mode</label>
                            <select
                                value={value.styleMode || ""}
                                onChange={(e) => onChange({ ...value, styleMode: e.target.value || null, lockedByUser: false })}
                                className="w-full h-11 rounded-xl bg-[var(--kf-bg)] border border-[var(--kf-border-muted)] px-3 text-sm text-[var(--kf-text)] focus:outline-none focus:border-purple-500/50"
                            >
                                <option value="">Auto-select</option>
                                {options.styleModes.map((style) => (
                                    <option key={style} value={style}>{style}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {recommendedPatterns.length > 0 && (
                        <div>
                            <label className="text-sm font-semibold text-[var(--kf-text)] mb-2 block">Recommended Patterns</label>
                            <div className="flex flex-wrap gap-2">
                                {recommendedPatterns.slice(0, 10).map((pattern) => (
                                    <span key={pattern} className="px-2.5 py-1 rounded-lg border border-[var(--kf-border-muted)] bg-[var(--kf-badge-bg)] text-[11px] text-[var(--kf-text-secondary)]">
                                        {pattern}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {autoDetectedSelection?.productMode && autoDetectedSelection?.styleMode && (
                        <div className="rounded-xl border border-purple-500/35 bg-purple-500/10 px-4 py-3">
                            <div className="text-sm font-semibold text-purple-200">Auto-detected Selection</div>
                            <div className="text-xs text-purple-100/90 mt-1">
                                {autoDetectedSelection.productMode} / {autoDetectedSelection.styleMode}
                            </div>
                            {autoDetectedSelection.confidence !== null && (
                                <div className="text-[11px] text-purple-200/85 mt-1">
                                    Confidence: {Math.round(autoDetectedSelection.confidence * 100)}%
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="px-6 py-4 border-t border-[var(--kf-border)]/40 flex items-center justify-between gap-3">
                    <button
                        onClick={onAutoDetect}
                        disabled={classifying || saving}
                        className="h-10 px-4 rounded-lg border border-[var(--kf-border-muted)] hover:border-purple-500/40 text-sm text-[var(--kf-text-secondary)] hover:text-purple-300 disabled:opacity-50 flex items-center gap-2"
                    >
                        {classifying ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                        Auto Detect
                    </button>
                    <div className="flex items-center gap-2">
                        {autoDetectedSelection?.productMode && autoDetectedSelection?.styleMode && (
                            <button
                                onClick={onApplyAutoSelection}
                                disabled={saving || classifying}
                                className="h-10 px-4 rounded-lg border border-purple-500/45 hover:border-purple-400 text-sm text-purple-200 hover:text-purple-100 disabled:opacity-50 flex items-center gap-2"
                            >
                                <Sparkles className="w-4 h-4" /> Apply Auto Selection
                            </button>
                        )}
                        {value.lockedByUser && (
                            <button
                                onClick={onUnlock}
                                disabled={saving}
                                className="h-10 px-4 rounded-lg border border-[var(--kf-border-muted)] hover:border-amber-500/40 text-sm text-[var(--kf-text-secondary)] hover:text-amber-300 disabled:opacity-50 flex items-center gap-2"
                            >
                                <Unlock className="w-4 h-4" /> Unlock
                            </button>
                        )}
                        <button
                            onClick={onSaveAndLock}
                            disabled={saving || !value.productMode || !value.styleMode}
                            className="h-10 px-4 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2"
                        >
                            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
                            Save & Lock
                        </button>
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * MAIN COMPONENT
 * ═══════════════════════════════════════════════════════════════════════ */

export default function DesignStudioPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const { getAccessToken, signOut } = useAuth();
    const { theme } = useTheme();

    const [loading, setLoading] = useState(true);
    const [phase, setPhase] = useState<Phase>("discovering");
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const [projectName, setProjectName] = useState<string>("");

    // Design mode selection
    const [showDesignModes, setShowDesignModes] = useState(false);
    const [designModeOptions, setDesignModeOptions] = useState<DesignModeOptions>({ productModes: [], styleModes: [] });
    const [designModeSelection, setDesignModeSelection] = useState<CurrentDesignMode | null>(null);
    const [recommendedPatterns, setRecommendedPatterns] = useState<string[]>([]);
    const [savingDesignMode, setSavingDesignMode] = useState(false);
    const [classifyingDesignMode, setClassifyingDesignMode] = useState(false);
    const [autoDetectedSelection, setAutoDetectedSelection] = useState<CurrentDesignMode | null>(null);

    // Engine design system
    const [engineSystem, setEngineSystem] = useState<EngineDesignSystem | null>(null);
    const [engineGenerating, setEngineGenerating] = useState(false);

    /* ─── API helpers ──────────────────────────────────────────────── */

    const expireSession = useCallback(async () => {
        setLoading(false);
        setError("Session expired. Please log in again.");
        try {
            await signOut();
        } catch {
            // ignore sign-out cleanup errors
        }
        navigate("/login", { replace: true });
    }, [navigate, signOut]);

    const authHeaders = useCallback(async () => {
        const token = await getAccessToken();
        if (!token) return null;
        return { Authorization: `Bearer ${token}` };
    }, [getAccessToken]);

    const ensureAuth = useCallback(async (): Promise<Record<string, string> | null> => {
        const headers = await authHeaders();
        if (!headers) {
            await expireSession();
            return null;
        }
        return headers;
    }, [authHeaders, expireSession]);

    const handleApi401 = useCallback((resp: Response) => {
        if (resp.status === 401) {
            void expireSession();
        }
    }, [expireSession]);

    /* ─── Fetch functions ─────────────────────────────────────────── */

    const fetchDesignModeOptions = useCallback(async () => {
        try {
            const headers = await authHeaders();
            if (!headers) {
                await expireSession();
                return;
            }
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mode-options`, { headers });
            if (resp.status === 401) {
                await expireSession();
                return;
            }
            if (!resp.ok) return;
            const data = await resp.json();
            setDesignModeOptions({
                productModes: data.productModes || [],
                styleModes: data.styleModes || [],
                currentDesignMode: data.currentDesignMode,
            });
            setDesignModeSelection((prev) => {
                if (data.currentDesignMode) {
                    return data.currentDesignMode as CurrentDesignMode;
                }
                return prev ?? {
                    productMode: null,
                    styleMode: null,
                    confidence: null,
                    lockedByUser: false,
                };
            });
        } catch {
            // ignore optional UI bootstrap failures
        }
    }, [authHeaders, expireSession, projectId]);

    const fetchEngineSystem = useCallback(async (): Promise<EngineDesignSystem | null> => {
        try {
            const headers = await authHeaders();
            if (!headers) return null;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/engine/system`,
                { headers }
            );
            if (resp.ok) {
                const data = await resp.json();
                if (data.design_system && data.design_system.design_tokens) {
                    setEngineSystem(data.design_system);
                    return data.design_system;
                }
            }
        } catch { /* engine system not yet generated */ }
        return null;
    }, [authHeaders, projectId]);

    const fetchProjectSummary = useCallback(async () => {
        try {
            const headers = await authHeaders();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}`, { headers });
            if (!resp.ok) return;
            const data: ProjectSummary = await resp.json();
            if (data?.name) setProjectName(data.name);
        } catch {
            // non-blocking UI metadata
        }
    }, [authHeaders, projectId]);

    /* ─── Handlers ────────────────────────────────────────────────── */

    const handleGenerateEngine = async () => {
        setEngineGenerating(true);
        setPhase("generating");
        setError(null);
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/engine/generate`,
                {
                    method: "POST",
                    headers: { ...headers, "Content-Type": "application/json" },
                    body: JSON.stringify({
                        design_mode: designModeSelection?.productMode || undefined,
                        design_style: designModeSelection?.styleMode || undefined,
                        lock_selection: Boolean(designModeSelection?.lockedByUser),
                    }),
                }
            );
            handleApi401(resp);
            if (!resp.ok) throw new Error("Engine design generation failed");
            const data = await resp.json();
            if (data.design_system) {
                setEngineSystem(data.design_system);
            }
            setPhase("gallery");
        } catch (e: any) {
            setError(e.message);
            setPhase("discovery");
        } finally {
            setEngineGenerating(false);
        }
    };

    const handleAutoDetectDesignMode = async () => {
        setClassifyingDesignMode(true);
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/classify-mode`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({
                    prompt: "Classify the best design mode and style from the current project context.",
                }),
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to auto-detect design mode");
            const data = await resp.json();
            setAutoDetectedSelection({
                productMode: data.classification?.productMode || null,
                styleMode: data.classification?.styleMode || null,
                confidence: data.classification?.confidence ?? null,
                lockedByUser: false,
            });
            setRecommendedPatterns(data.recommendedPatterns || []);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setClassifyingDesignMode(false);
        }
    };

    const handleApplyAutoSelection = () => {
        if (!autoDetectedSelection?.productMode || !autoDetectedSelection?.styleMode) return;
        setDesignModeSelection({
            productMode: autoDetectedSelection.productMode,
            styleMode: autoDetectedSelection.styleMode,
            confidence: autoDetectedSelection.confidence,
            lockedByUser: false,
        });
        setShowDesignModes(false);
        setAutoDetectedSelection(null);
        setSuccessMessage("Auto selection applied. You can now generate the design system.");
        setTimeout(() => setSuccessMessage(null), 2600);
    };

    const handleLockDesignMode = async () => {
        if (!designModeSelection?.productMode || !designModeSelection?.styleMode) return;
        setSavingDesignMode(true);
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/lock-mode`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({
                    productMode: designModeSelection.productMode,
                    styleMode: designModeSelection.styleMode,
                    confidence: designModeSelection.confidence ?? 1,
                }),
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to save design mode selection");
            setDesignModeSelection((prev) => prev ? { ...prev, lockedByUser: true } : prev);
            await fetchDesignModeOptions();
            setShowDesignModes(false);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSavingDesignMode(false);
        }
    };

    const handleUnlockDesignMode = async () => {
        setSavingDesignMode(true);
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/unlock-mode`, {
                method: "POST",
                headers,
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to unlock design mode selection");
            setDesignModeSelection((prev) => prev ? { ...prev, lockedByUser: false } : prev);
            await fetchDesignModeOptions();
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSavingDesignMode(false);
        }
    };

    /* ─── Derived ─────────────────────────────────────────────────── */

    const isDark = theme === "dark";
    void isDark; // available for future use

    /* ─── Init ────────────────────────────────────────────────────── */

    useEffect(() => {
        let cancelled = false;

        async function init() {
            await fetchProjectSummary();
            await fetchDesignModeOptions();

            const existingEngine = await fetchEngineSystem();
            if (!cancelled && existingEngine) {
                setPhase("gallery");
            } else if (!cancelled) {
                setPhase("discovery");
            }
            if (!cancelled) setLoading(false);
        }

        init();
        return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [fetchDesignModeOptions, fetchEngineSystem, fetchProjectSummary]);

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
        <div className="h-[calc(100vh-65px)] bg-[var(--kf-bg)] text-[var(--kf-text)] flex flex-col overflow-hidden">
            {/* ── Top bar ──────────────────────────────────────────────── */}
            <div className="h-14 border-b border-[var(--kf-border)]/60 px-5 flex items-center justify-between bg-[var(--kf-surface)] shrink-0">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => navigate(`/project/${projectId}`)}
                        className="flex items-center gap-1.5 h-8 px-2.5 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)] text-xs transition-colors"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" /> Project
                    </button>
                    <div className="flex items-center gap-2">
                        <Palette className="w-4 h-4 text-purple-300" />
                        <h2 className="text-sm font-bold text-[var(--kf-text)]">Design Studio</h2>
                        {projectName && (
                            <span className="text-xs text-[var(--kf-text-secondary)]">• {projectName}</span>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs text-[var(--kf-text-secondary)]">
                        {engineSystem ? "Design System ready" : "No design system yet"}
                    </span>

                    <button
                        onClick={() => navigate(`/project/${projectId}/editor?applydesign=1`)}
                        className="h-8 px-3 rounded-md bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-purple-500/20"
                    >
                        <Rocket className="w-3.5 h-3.5" /> Build with Kith
                    </button>

                    <button
                        onClick={() => navigate("/")}
                        className="h-8 px-2.5 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)] text-xs flex items-center gap-1.5"
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
                            <p className="text-[var(--kf-text-secondary)] mt-4 text-sm font-medium">Loading design system...</p>
                            <p className="text-zinc-600 text-xs mt-1">Checking for existing design tokens and configuration</p>
                        </motion.div>
                    )}

                    {/* ── PHASE: DISCOVERY ────────────────────────────────── */}
                    {phase === "discovery" && (
                        <motion.div
                            key="discovery"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="h-full flex flex-col items-center justify-center"
                        >
                            <div className="max-w-lg text-center">
                                <div className="mx-auto w-16 h-16 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center mb-6">
                                    <Sparkles className="w-8 h-8 text-purple-400" />
                                </div>
                                <h3 className="text-xl font-bold text-[var(--kf-text)] mb-2">Generate Your Design System</h3>
                                <p className="text-sm text-[var(--kf-text-secondary)] mb-6 leading-relaxed">
                                    The AI Design Engine will analyze your project and generate a complete design system —
                                    color tokens, typography, spacing, component specifications, and layout architecture.
                                </p>

                                {/* Mode / Style selection */}
                                <div className="flex items-center justify-center gap-3 mb-6">
                                    <button
                                        onClick={() => setShowDesignModes(true)}
                                        className="flex items-center gap-2 h-9 px-4 rounded-lg border border-[var(--kf-border-muted)] hover:border-purple-500/40 text-[var(--kf-text-secondary)] hover:text-purple-300 text-xs transition-colors"
                                    >
                                        <Palette className="w-3.5 h-3.5" />
                                        {designModeSelection?.productMode && designModeSelection?.styleMode
                                            ? `${designModeSelection.productMode} / ${designModeSelection.styleMode}`
                                            : "Choose Design Mode"}
                                        {designModeSelection?.lockedByUser && <Lock className="w-3 h-3" />}
                                    </button>
                                </div>

                                <button
                                    onClick={handleGenerateEngine}
                                    disabled={engineGenerating}
                                    className="h-11 px-8 rounded-xl bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 mx-auto shadow-lg shadow-purple-500/20"
                                >
                                    {engineGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                    Generate Design System
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
                            className="h-full flex flex-col items-center justify-center"
                        >
                            <Loader2 className="w-10 h-10 text-purple-400 animate-spin mb-4" />
                            <h3 className="text-lg font-bold text-[var(--kf-text)] mb-1">Generating Design System</h3>
                            <p className="text-sm text-[var(--kf-text-secondary)]">
                                Building tokens, components, and layout architecture...
                            </p>
                            {designModeSelection?.productMode && designModeSelection?.styleMode && (
                                <p className="text-xs text-purple-300 mt-2">
                                    Mode: {designModeSelection.productMode} / {designModeSelection.styleMode}
                                </p>
                            )}
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
                            <div className="px-6 pt-5 pb-4 border-b border-[var(--kf-border)]/40">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-[var(--kf-text)]">Design System</h3>
                                        <p className="text-xs text-[var(--kf-text-secondary)] mt-1">
                                            Your design system is ready — tokens, components, and layout
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => setShowDesignModes(true)}
                                            className="h-8 px-3 rounded-md border border-[var(--kf-border-muted)] hover:border-purple-500/40 text-[var(--kf-text-secondary)] hover:text-purple-300 text-xs flex items-center gap-1.5 transition-colors"
                                        >
                                            <Palette className="w-3.5 h-3.5" />
                                            {designModeSelection?.productMode && designModeSelection?.styleMode
                                                ? `${designModeSelection.productMode} / ${designModeSelection.styleMode}`
                                                : "Design Mode"}
                                        </button>
                                        <button
                                            onClick={handleGenerateEngine}
                                            disabled={engineGenerating}
                                            className="h-8 px-4 rounded-md bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                                        >
                                            {engineGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                                            Regenerate System
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Gallery content */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                {engineSystem && (
                                    <div className="rounded-xl border border-purple-500/30 bg-[var(--kf-surface)] p-6">
                                        <div className="flex items-center gap-2 mb-4">
                                            <Sparkles className="w-5 h-5 text-purple-400" />
                                            <h3 className="text-sm font-bold text-[var(--kf-text)]">Design System</h3>
                                            {engineSystem.mode_context && (
                                                <span className="text-xs text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded">
                                                    {engineSystem.mode_context.product_mode} / {engineSystem.mode_context.style_mode}
                                                </span>
                                            )}
                                        </div>

                                        {/* Color tokens */}
                                        {engineSystem.design_tokens?.colors && Object.keys(engineSystem.design_tokens.colors).length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-xs font-semibold text-[var(--kf-text-secondary)] mb-2">Colors</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(engineSystem.design_tokens.colors).map(([name, value]) => (
                                                        <div key={name} className="flex items-center gap-1.5 bg-[var(--kf-bg)] rounded-lg px-2.5 py-1.5">
                                                            <div
                                                                className="w-4 h-4 rounded border border-[var(--kf-border)]"
                                                                style={{ backgroundColor: typeof value === "string" ? value : "#000" }}
                                                            />
                                                            <span className="text-[10px] text-[var(--kf-text-secondary)] font-mono">{name}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Typography */}
                                        {engineSystem.design_tokens?.typography && Object.keys(engineSystem.design_tokens.typography).length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-xs font-semibold text-[var(--kf-text-secondary)] mb-2">Typography</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(engineSystem.design_tokens.typography).map(([name, value]) => (
                                                        <span key={name} className="text-[10px] bg-[var(--kf-bg)] rounded-lg px-2.5 py-1.5 text-[var(--kf-text-secondary)] font-mono">
                                                            {name}: {typeof value === "string" ? value : JSON.stringify(value)}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Spacing */}
                                        {engineSystem.design_tokens?.spacing && Object.keys(engineSystem.design_tokens.spacing).length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-xs font-semibold text-[var(--kf-text-secondary)] mb-2">Spacing</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(engineSystem.design_tokens.spacing).map(([name, value]) => (
                                                        <span key={name} className="text-[10px] bg-[var(--kf-bg)] rounded-lg px-2.5 py-1.5 text-[var(--kf-text-secondary)] font-mono">
                                                            {name}: {value}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Component specifications */}
                                        {engineSystem.component_specifications && engineSystem.component_specifications.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-semibold text-[var(--kf-text-secondary)] mb-2">
                                                    Components ({engineSystem.component_specifications.length})
                                                </h4>
                                                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
                                                    {engineSystem.component_specifications.map((comp, i) => (
                                                        <div key={i} className="text-[11px] bg-[var(--kf-bg)] rounded-lg px-3 py-2 border border-[var(--kf-border)]/40">
                                                            <span className="font-semibold text-[var(--kf-text)]">{comp.name}</span>
                                                            {comp.type && <span className="text-[var(--kf-text-faint)] ml-1">({comp.type})</span>}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {!engineSystem && (
                                    <div className="flex flex-col items-center justify-center py-16 text-center">
                                        <Palette className="w-10 h-10 text-zinc-600 mb-3" />
                                        <p className="text-sm text-[var(--kf-text-secondary)]">No design system generated yet.</p>
                                        <button
                                            onClick={handleGenerateEngine}
                                            disabled={engineGenerating}
                                            className="mt-4 h-9 px-5 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2"
                                        >
                                            <Sparkles className="w-4 h-4" /> Generate Design System
                                        </button>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* ── Design Mode Modal ────────────────────────────────────── */}
            <AnimatePresence>
                {showDesignModes && designModeSelection && (
                    <DesignModeModal
                        options={designModeOptions}
                        value={designModeSelection}
                        recommendedPatterns={recommendedPatterns}
                        saving={savingDesignMode}
                        classifying={classifyingDesignMode}
                        autoDetectedSelection={autoDetectedSelection}
                        onChange={setDesignModeSelection}
                        onAutoDetect={handleAutoDetectDesignMode}
                        onApplyAutoSelection={handleApplyAutoSelection}
                        onSaveAndLock={handleLockDesignMode}
                        onUnlock={handleUnlockDesignMode}
                        onClose={() => {
                            setShowDesignModes(false);
                            setAutoDetectedSelection(null);
                        }}
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
                        className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-3 z-50"
                    >
                        {error}
                        <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                            <X className="w-4 h-4" />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Success toast ─────────────────────────────────────────── */}
            <AnimatePresence>
                {successMessage && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 text-sm flex items-center gap-3 z-50"
                    >
                        {successMessage}
                        <button onClick={() => setSuccessMessage(null)} className="text-emerald-300 hover:text-emerald-200">
                            <X className="w-4 h-4" />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
