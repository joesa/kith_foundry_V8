import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../lib/utils/cn";

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
  mode_context?: { product_mode?: string; style_mode?: string; productMode?: string; styleMode?: string };
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

function hasDesignTokens(system: EngineDesignSystem | null | undefined): boolean {
    if (!system?.design_tokens) return false;
    const groups = [
        system.design_tokens.colors,
        system.design_tokens.typography,
        system.design_tokens.spacing,
        system.design_tokens.borders,
        system.design_tokens.shadows,
        system.design_tokens.animations,
    ];
    return groups.some((group) => !!group && Object.keys(group).length > 0);
}

function normalizeEngineSystem(raw: any): EngineDesignSystem | null {
    if (!raw || typeof raw !== "object") return null;
    return raw as EngineDesignSystem;
}

function parseClassification(data: any): CurrentDesignMode | null {
    const classification = data?.classification ?? {};
    const productMode = classification.productMode ?? classification.product_mode ?? null;
    const styleMode = classification.styleMode ?? classification.style_mode ?? null;
    if (!productMode || !styleMode) return null;
    return {
        productMode,
        styleMode,
        confidence: classification.confidence ?? null,
        lockedByUser: false,
    };
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
                className="relative w-full max-w-2xl bg-surface border border-outline-variant/30 rounded-[var(--radius-module)] shadow-2xl overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="px-6 pt-5 pb-4 border-b border-outline-variant/20">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-xl bg-primary-container border border-outline-variant/20">
                                <span className="material-symbols-outlined text-xl text-on-primary-container">palette</span>
                            </div>
                            <div>
                                <h2 className="text-lg font-black text-on-surface uppercase" style={{ letterSpacing: "-0.05em" }}>Design Mode + Style</h2>
                                <p className="text-xs text-secondary">Auto-detect the best layout system or lock a manual override</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-container text-tertiary">
                            <span className="material-symbols-outlined text-xl">close</span>
                        </button>
                    </div>
                </div>

                <div className="px-6 py-5 space-y-5 max-h-[65vh] overflow-y-auto">
                    <div className="flex items-center justify-between gap-3 rounded-xl border border-outline-variant/30 bg-background px-4 py-3">
                        <div>
                            <div className="text-sm font-black text-on-surface uppercase tracking-widest">Current Selection</div>
                            <div className="text-xs text-secondary mt-1">
                                {value.productMode && value.styleMode
                                    ? `${value.productMode} / ${value.styleMode}`
                                    : "No design mode selected yet"}
                            </div>
                            {value.confidence !== null && (
                                <div className="text-[11px] text-tertiary mt-1">
                                    Confidence: {Math.round(value.confidence * 100)}%
                                </div>
                            )}
                        </div>
                        <div className={cn(
                            "text-[11px] px-2 py-1 rounded-full border font-black uppercase tracking-widest",
                            value.lockedByUser
                                ? "border-emerald-500/30 text-emerald-300 bg-emerald-500/10"
                                : "border-outline-variant/30 text-secondary bg-surface-container"
                        )}>
                            {value.lockedByUser ? "Locked" : "Auto"}
                        </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                        <div>
                            <label className="text-xs font-black text-on-surface mb-2 block uppercase tracking-widest">Product Mode</label>
                            <select
                                value={value.productMode || ""}
                                onChange={(e) => onChange({ ...value, productMode: e.target.value || null, lockedByUser: false })}
                                className="w-full h-11 rounded-lg bg-background border border-outline-variant/30 px-3 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                            >
                                <option value="">Auto-select</option>
                                {options.productModes.map((mode) => (
                                    <option key={mode} value={mode}>{mode}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="text-xs font-black text-on-surface mb-2 block uppercase tracking-widest">Style Mode</label>
                            <select
                                value={value.styleMode || ""}
                                onChange={(e) => onChange({ ...value, styleMode: e.target.value || null, lockedByUser: false })}
                                className="w-full h-11 rounded-lg bg-background border border-outline-variant/30 px-3 text-sm text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
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
                            <label className="text-xs font-black text-on-surface mb-2 block uppercase tracking-widest">Recommended Patterns</label>
                            <div className="flex flex-wrap gap-2">
                                {recommendedPatterns.slice(0, 10).map((pattern) => (
                                    <span key={pattern} className="px-2.5 py-1 rounded-lg border border-outline-variant/30 bg-surface-container text-[11px] text-secondary">
                                        {pattern}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {autoDetectedSelection?.productMode && autoDetectedSelection?.styleMode && (
                        <div className="rounded-xl border border-primary/30 bg-primary-container/30 px-4 py-3">
                            <div className="text-sm font-black text-on-surface uppercase tracking-widest">Auto-detected Selection</div>
                            <div className="text-xs text-secondary mt-1">
                                {autoDetectedSelection.productMode} / {autoDetectedSelection.styleMode}
                            </div>
                            {autoDetectedSelection.confidence !== null && (
                                <div className="text-[11px] text-tertiary mt-1">
                                    Confidence: {Math.round(autoDetectedSelection.confidence * 100)}%
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="px-6 py-4 border-t border-outline-variant/20 flex items-center justify-between gap-3">
                    <button
                        onClick={onAutoDetect}
                        disabled={classifying || saving}
                        className="h-10 px-4 rounded-full border border-outline-variant/30 hover:border-primary/40 text-xs text-secondary hover:text-on-surface font-black uppercase tracking-widest disabled:opacity-50 flex items-center gap-2 transition-colors"
                    >
                        {classifying
                            ? <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                            : <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>}
                        Auto Detect
                    </button>
                    <div className="flex items-center gap-2">
                        {autoDetectedSelection?.productMode && autoDetectedSelection?.styleMode && (
                            <button
                                onClick={onApplyAutoSelection}
                                disabled={saving || classifying}
                                className="h-10 px-4 rounded-full border border-primary/40 hover:border-primary text-xs text-on-primary-container font-black uppercase tracking-widest disabled:opacity-50 flex items-center gap-2 transition-colors"
                            >
                                <span className="material-symbols-outlined text-base leading-none">auto_awesome</span> Apply Auto Selection
                            </button>
                        )}
                        {value.lockedByUser && (
                            <button
                                onClick={onUnlock}
                                disabled={saving}
                                className="h-10 px-4 rounded-full border border-outline-variant/30 hover:border-outline-variant text-xs text-secondary font-black uppercase tracking-widest disabled:opacity-50 flex items-center gap-2 transition-colors"
                            >
                                <span className="material-symbols-outlined text-base leading-none">lock_open</span> Unlock
                            </button>
                        )}
                        <button
                            onClick={onSaveAndLock}
                            disabled={saving || !value.productMode || !value.styleMode}
                            className="h-10 px-4 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50 flex items-center gap-2"
                        >
                            {saving
                                ? <div className="w-4 h-4 border-2 border-on-primary-container/30 border-t-on-primary-container rounded-full animate-spin" />
                                : <span className="material-symbols-outlined text-base leading-none">lock</span>}
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
                const normalized = normalizeEngineSystem(data.design_system);
                if (normalized) {
                    setEngineSystem(normalized);
                    return normalized;
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

    const hydrateGeneratedEngineSystem = useCallback(async (
        fallbackSystem?: EngineDesignSystem | null,
    ): Promise<EngineDesignSystem | null> => {
        const normalizedFallback = normalizeEngineSystem(fallbackSystem);
        if (normalizedFallback) {
            setEngineSystem(normalizedFallback);
            if (hasDesignTokens(normalizedFallback)) {
                return normalizedFallback;
            }
        }

        for (let attempt = 0; attempt < 20; attempt += 1) {
            const latest = await fetchEngineSystem();
            if (latest && hasDesignTokens(latest)) {
                return latest;
            }
            await new Promise((resolve) => window.setTimeout(resolve, 1000));
        }

        return normalizedFallback ?? null;
    }, [fetchEngineSystem]);

    /* ─── Handlers ────────────────────────────────────────────────── */

    const handleGenerateEngine = async () => {
        setEngineGenerating(true);
        setPhase("generating");
        setError(null);
        const abortController = new AbortController();
        const timer = setTimeout(() => abortController.abort(), 260_000);
        try {
            const headers = await ensureAuth();
            if (!headers) {
                setPhase("discovery");
                return;
            }
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
                    signal: abortController.signal,
                }
            );
            handleApi401(resp);
            if (!resp.ok) {
                let message = "Engine design generation failed";
                try {
                    const errorData = await resp.json();
                    if (typeof errorData?.detail === "string" && errorData.detail.trim()) {
                        message = errorData.detail;
                    }
                } catch {
                    // Ignore non-JSON error bodies and fall back to the generic message.
                }
                throw new Error(message);
            }
            const data = await resp.json();
            const immediate = normalizeEngineSystem(data.design_system ?? null);
            if (immediate) {
                setEngineSystem(immediate);
            }
            const hydratedSystem = await hydrateGeneratedEngineSystem(immediate);
            if (hydratedSystem) {
                setEngineSystem(hydratedSystem);
            }
            await fetchDesignModeOptions();
            setPhase("gallery");
        } catch (e: any) {
            const msg = e?.name === "AbortError"
                ? "Design generation timed out. Please retry."
                : e.message;
            setError(msg);
            setPhase("discovery");
        } finally {
            clearTimeout(timer);
            setEngineGenerating(false);
        }
    };

    const handleAutoDetectDesignMode = async () => {
        setError(null);
        setSuccessMessage(null);
        setAutoDetectedSelection(null);
        setClassifyingDesignMode(true);
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/auto-select-mode`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
            });
            handleApi401(resp);
            if (!resp.ok) {
                let message = "Failed to auto-detect design mode";
                try {
                    const errorData = await resp.json();
                    if (typeof errorData?.detail === "string" && errorData.detail.trim()) {
                        message = errorData.detail;
                    }
                } catch {
                    // fall back to the default message for non-JSON errors
                }
                throw new Error(message);
            }
            const data = await resp.json();
            const detected = parseClassification(data);
            if (!detected) {
                throw new Error("Auto-detect did not return a valid mode/style pair.");
            }
            setAutoDetectedSelection(detected);
            setDesignModeSelection((prev) => ({
                productMode: detected.productMode,
                styleMode: detected.styleMode,
                confidence: detected.confidence,
                lockedByUser: prev?.lockedByUser ?? false,
            }));
            setRecommendedPatterns(data.recommendedPatterns || []);
            await fetchDesignModeOptions();
            setSuccessMessage(`Auto-detected: ${detected.productMode} / ${detected.styleMode}`);
            window.setTimeout(() => setSuccessMessage(null), 2600);
        } catch (e: any) {
            setError(e?.message || "Failed to auto-detect design mode");
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

    /* ─── Auto-select design mode on studio init ────────────────── */

    const autoSelectDesignMode = useCallback(async (): Promise<CurrentDesignMode | null> => {
        try {
            const headers = await authHeaders();
            if (!headers) return null;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/auto-select-mode`,
                {
                    method: "POST",
                    headers: { ...headers, "Content-Type": "application/json" },
                }
            );
            if (!resp.ok) return null;
            const data = await resp.json();
            const parsed = parseClassification(data);
            if (!parsed) return null;
            const mode: CurrentDesignMode = { ...parsed, lockedByUser: data.source === "locked" };
            if (mode.productMode && mode.styleMode) {
                setDesignModeSelection(mode);
                setRecommendedPatterns(data.recommendedPatterns || []);
                return mode;
            }
        } catch {
            // non-blocking — user can still manually select
        }
        return null;
    }, [authHeaders, projectId]);

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
                // Auto-select design mode when entering discovery phase
                // (only if no mode is already stored on the project)
                void autoSelectDesignMode();
            }
            if (!cancelled) setLoading(false);
        }

        init();
        return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectId]);

    /* ─── Loading state ───────────────────────────────────────────── */

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    /* ═══════════════════════════════════════════════════════════════════════
     * RENDER
     * ═══════════════════════════════════════════════════════════════════════ */

    return (
        <div className="h-[calc(100vh-65px)] bg-background text-on-surface flex flex-col overflow-hidden">
            {/* ── Top bar ──────────────────────────────────────────────── */}
            <div className="h-14 border-b border-outline-variant/20 px-5 flex items-center justify-between bg-surface shrink-0">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => navigate(`/app/projects/${projectId}`)}
                        className="flex items-center gap-1.5 h-8 px-2.5 rounded-full border border-outline-variant/30 text-secondary hover:bg-surface-container text-xs font-black uppercase tracking-widest transition-colors"
                    >
                        <span className="material-symbols-outlined text-sm leading-none">arrow_back</span> Project
                    </button>
                    <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-base text-on-primary-container">palette</span>
                        <h2 className="text-sm font-black text-on-surface uppercase tracking-widest">Design Studio</h2>
                        {projectName && (
                            <span className="text-xs text-secondary">• {projectName}</span>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <span className="text-xs text-tertiary font-black uppercase tracking-widest">
                        {engineSystem ? "Design System ready" : "No design system yet"}
                    </span>

                    <button
                        onClick={() => navigate(`/app/projects/${projectId}/build?applydesign=1`)}
                        className="h-8 px-3 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity flex items-center gap-1.5"
                    >
                        <span className="material-symbols-outlined text-sm leading-none">rocket_launch</span> Build with Kith
                    </button>

                    <button
                        onClick={() => navigate("/app/projects")}
                        className="h-8 px-2.5 rounded-full border border-outline-variant/30 text-secondary hover:bg-surface-container text-xs font-black uppercase tracking-widest flex items-center gap-1.5 transition-colors"
                    >
                        <span className="material-symbols-outlined text-sm leading-none">grid_view</span> All Projects
                    </button>
                </div>
            </div>

            {/* ── Main content area ────────────────────────────────────── */}
            <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="sync">
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
                                <span className="material-symbols-outlined text-5xl text-on-primary-container">color_lens</span>
                            </motion.div>
                            <p className="text-secondary mt-4 text-sm font-black uppercase tracking-widest">Loading design system...</p>
                            <p className="text-tertiary text-xs mt-1">Checking for existing design tokens and configuration</p>
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
                                <div className="mx-auto w-16 h-16 rounded-2xl bg-primary-container border border-outline-variant/20 flex items-center justify-center mb-6">
                                    <span className="material-symbols-outlined text-3xl text-on-primary-container">auto_awesome</span>
                                </div>
                                <h3 className="text-xl font-black text-on-surface mb-2 uppercase" style={{ letterSpacing: "-0.05em" }}>
                                    Generate Your Design System
                                </h3>
                                <p className="text-sm text-secondary mb-6 leading-relaxed">
                                    The AI Design Engine will analyze your project and generate a complete design system —
                                    color tokens, typography, spacing, component specifications, and layout architecture.
                                </p>

                                {/* Mode / Style selection */}
                                <div className="flex items-center justify-center gap-3 mb-6">
                                    <button
                                        onClick={() => setShowDesignModes(true)}
                                        className="flex items-center gap-2 h-9 px-4 rounded-full border border-outline-variant/30 hover:border-outline-variant text-secondary hover:text-on-surface text-xs font-black uppercase tracking-widest transition-colors"
                                    >
                                        <span className="material-symbols-outlined text-base leading-none">palette</span>
                                        {designModeSelection?.productMode && designModeSelection?.styleMode
                                            ? `${designModeSelection.productMode} / ${designModeSelection.styleMode}`
                                            : "Choose Design Mode"}
                                        {designModeSelection?.lockedByUser && (
                                            <span className="material-symbols-outlined text-sm leading-none">lock</span>
                                        )}
                                    </button>
                                </div>

                                <button
                                    onClick={handleGenerateEngine}
                                    disabled={engineGenerating}
                                    className="h-11 px-8 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50 flex items-center gap-2 mx-auto"
                                >
                                    {engineGenerating
                                        ? <div className="w-4 h-4 border-2 border-on-primary-container/30 border-t-on-primary-container rounded-full animate-spin" />
                                        : <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>}
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
                            <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
                            <h3 className="text-lg font-black text-on-surface mb-1 uppercase tracking-widest">Generating Design System</h3>
                            <p className="text-sm text-secondary">
                                Building tokens, components, and layout architecture...
                            </p>
                            {designModeSelection?.productMode && designModeSelection?.styleMode && (
                                <p className="text-xs text-tertiary mt-2 font-black uppercase tracking-widest">
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
                            <div className="px-6 pt-5 pb-4 border-b border-outline-variant/20">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-black text-on-surface uppercase" style={{ letterSpacing: "-0.05em" }}>Design System</h3>
                                        <p className="text-xs text-secondary mt-1 font-black uppercase tracking-widest">
                                            Your design system is ready — tokens, components, and layout
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => setShowDesignModes(true)}
                                            className="h-8 px-3 rounded-full border border-outline-variant/30 hover:border-outline-variant text-secondary hover:text-on-surface text-xs font-black uppercase tracking-widest flex items-center gap-1.5 transition-colors"
                                        >
                                            <span className="material-symbols-outlined text-sm leading-none">palette</span>
                                            {designModeSelection?.productMode && designModeSelection?.styleMode
                                                ? `${designModeSelection.productMode} / ${designModeSelection.styleMode}`
                                                : "Design Mode"}
                                        </button>
                                        <button
                                            onClick={handleGenerateEngine}
                                            disabled={engineGenerating}
                                            className="h-8 px-4 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity flex items-center gap-1.5 disabled:opacity-50"
                                        >
                                            {engineGenerating
                                                ? <div className="w-3.5 h-3.5 border-2 border-on-primary-container/30 border-t-on-primary-container rounded-full animate-spin" />
                                                : <span className="material-symbols-outlined text-sm leading-none">refresh</span>}
                                            Regenerate System
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Gallery content */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                {engineSystem && (
                                    <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6">
                                        <div className="flex items-center gap-2 mb-4">
                                            <span className="material-symbols-outlined text-xl text-on-primary-container">auto_awesome</span>
                                            <h3 className="text-sm font-black text-on-surface uppercase tracking-widest">Design System</h3>
                                            {engineSystem.mode_context && (
                                                <span className="text-xs text-secondary bg-surface-container px-2 py-0.5 rounded font-black uppercase tracking-widest">
                                                    {engineSystem.mode_context.product_mode || engineSystem.mode_context.productMode} / {engineSystem.mode_context.style_mode || engineSystem.mode_context.styleMode}
                                                </span>
                                            )}
                                        </div>

                                        {/* Color tokens */}
                                        {engineSystem.design_tokens?.colors && Object.keys(engineSystem.design_tokens.colors).length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-xs font-black text-secondary mb-2 uppercase tracking-widest">Colors</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(engineSystem.design_tokens.colors).map(([name, value]) => (
                                                        <div key={name} className="flex items-center gap-1.5 bg-background rounded-lg px-2.5 py-1.5 border border-outline-variant/20">
                                                            <div
                                                                className="w-4 h-4 rounded border border-outline-variant/30"
                                                                style={{ backgroundColor: typeof value === "string" ? value : "#000" }}
                                                            />
                                                            <span className="text-[10px] text-secondary font-mono">{name}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Typography */}
                                        {engineSystem.design_tokens?.typography && Object.keys(engineSystem.design_tokens.typography).length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-xs font-black text-secondary mb-2 uppercase tracking-widest">Typography</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(engineSystem.design_tokens.typography).map(([name, value]) => (
                                                        <span key={name} className="text-[10px] bg-background rounded-lg px-2.5 py-1.5 text-secondary font-mono border border-outline-variant/20">
                                                            {name}: {typeof value === "string" ? value : JSON.stringify(value)}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Spacing */}
                                        {engineSystem.design_tokens?.spacing && Object.keys(engineSystem.design_tokens.spacing).length > 0 && (
                                            <div className="mb-4">
                                                <h4 className="text-xs font-black text-secondary mb-2 uppercase tracking-widest">Spacing</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {Object.entries(engineSystem.design_tokens.spacing).map(([name, value]) => (
                                                        <span key={name} className="text-[10px] bg-background rounded-lg px-2.5 py-1.5 text-secondary font-mono border border-outline-variant/20">
                                                            {name}: {value}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Component specifications */}
                                        {engineSystem.component_specifications && engineSystem.component_specifications.length > 0 && (
                                            <div>
                                                <h4 className="text-xs font-black text-secondary mb-2 uppercase tracking-widest">
                                                    Components ({engineSystem.component_specifications.length})
                                                </h4>
                                                <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
                                                    {engineSystem.component_specifications.map((comp, i) => (
                                                        <div key={i} className="text-[11px] bg-background rounded-lg px-3 py-2 border border-outline-variant/20">
                                                            <span className="font-black text-on-surface uppercase tracking-widest">{comp.name}</span>
                                                            {comp.type && <span className="text-tertiary ml-1">({comp.type})</span>}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {!engineSystem && (
                                    <div className="flex flex-col items-center justify-center py-16 text-center">
                                        <span className="material-symbols-outlined text-4xl text-tertiary mb-3">palette</span>
                                        <p className="text-sm text-secondary font-black uppercase tracking-widest">No design system generated yet.</p>
                                        <button
                                            onClick={handleGenerateEngine}
                                            disabled={engineGenerating}
                                            className="mt-4 h-9 px-5 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50 flex items-center gap-2"
                                        >
                                            <span className="material-symbols-outlined text-base leading-none">auto_awesome</span> Generate Design System
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
                        className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm flex items-center gap-3 z-50"
                    >
                        {error}
                        <button onClick={() => setError(null)} className="text-tertiary hover:text-on-surface">
                            <span className="material-symbols-outlined text-base leading-none">close</span>
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
                        className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-primary-container border border-outline-variant/20 text-on-primary-container text-sm flex items-center gap-3 z-50"
                    >
                        {successMessage}
                        <button onClick={() => setSuccessMessage(null)} className="text-on-primary-container/70 hover:text-on-primary-container">
                            <span className="material-symbols-outlined text-base leading-none">close</span>
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
