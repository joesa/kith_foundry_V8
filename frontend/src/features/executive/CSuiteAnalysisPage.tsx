import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../lib/utils/cn";
import { ExportMenu } from "../../components/system/ExportMenu";

// ── Types ────────────────────────────────────────────────────────────────────

interface AgentResult {
    role: string;
    status: "pending" | "running" | "complete" | "error";
    score: number | null;
    recommendation: string | null;
    deep_analysis: string | null;
    strengths: string[];
    risks: string[];
    suggestions: string[];
    key_metrics: string[];
    timeline: string | null;
    priority_actions: string[];
    competitive_note: string | null;
    verdict: "go" | "no_go" | "conditional" | null;
    error_message?: string | null;
}

interface ImprovementDetail {
    current_score: number;
    key_weaknesses: string[];
    recommended_changes: string[];
    enhanced_context: string;
}

interface ImprovementPlan {
    improvements: Record<string, ImprovementDetail>;
    summary: string;
}

const ROLE_META: Record<string, { label: string; icon: string; color: string; gradient: string }> = {
    ceo:         { label: "CEO",                  icon: "psychology",   color: "text-amber-400",  gradient: "from-amber-500/20 to-orange-500/20" },
    cpo:         { label: "CPO",                  icon: "groups",       color: "text-purple-400", gradient: "from-purple-500/20 to-violet-500/20" },
    cto:         { label: "CTO",                  icon: "code",         color: "text-cyan-400",   gradient: "from-cyan-500/20 to-blue-500/20" },
    cdo:         { label: "CDO",                  icon: "palette",      color: "text-violet-400", gradient: "from-violet-500/20 to-fuchsia-500/20" },
    cfo:         { label: "CFO",                  icon: "payments",     color: "text-green-400",  gradient: "from-green-500/20 to-emerald-500/20" },
    cmo:         { label: "CMO",                  icon: "trending_up",  color: "text-pink-400",   gradient: "from-pink-500/20 to-rose-500/20" },
    coo:         { label: "COO",                  icon: "settings",     color: "text-blue-400",   gradient: "from-blue-500/20 to-indigo-500/20" },
    ciso:        { label: "CISO",                 icon: "security",     color: "text-red-400",    gradient: "from-red-500/20 to-rose-500/20" },
    synthesizer: { label: "Executive Synthesizer", icon: "hub",         color: "text-amber-400",  gradient: "from-amber-500/20 to-orange-500/20" },
};

function createPendingAgents(): AgentResult[] {
    return Object.keys(ROLE_META).map(role => ({
        role,
        status: "pending",
        score: null,
        recommendation: null,
        deep_analysis: null,
        strengths: [],
        risks: [],
        suggestions: [],
        key_metrics: [],
        timeline: null,
        priority_actions: [],
        competitive_note: null,
        verdict: null,
    }));
}

export default function CSuiteAnalysisPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();

    const [agents, setAgents] = useState<AgentResult[]>(createPendingAgents);
    const [overallScore, setOverallScore] = useState<number | null>(null);
    const [overallVerdict, setOverallVerdict] = useState<string | null>(null);
    const [projectName, setProjectName] = useState<string>("");
    const [started, setStarted] = useState(false);
    const [allDone, setAllDone] = useState(false);
    const [corrections, setCorrections] = useState("");
    const [refining, setRefining] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [stuck, setStuck] = useState(false);
    const [stopping, setStopping] = useState(false);
    const [stoppingRole, setStoppingRole] = useState<string | null>(null);
    const [regeneratingRoles, setRegeneratingRoles] = useState<string[]>([]);
    const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const sseRef = useRef<EventSource | null>(null);
    const pollCountRef = useRef(0);
    const autoStartRequestedRef = useRef(false);
    const shouldAutoNavigateOnDoneRef = useRef(false);
    const hasAutoNavigatedRef = useRef(false);
    const POLL_TIMEOUT = 6;  // 6 polls × 30s = 3 min max before stuck detection

    // ── Improvement state ────────────────────────────────────────────────
    const [improvePlan, setImprovePlan] = useState<ImprovementPlan | null>(null);
    const [improveLoading, setImproveLoading] = useState(false);
    const [improveRoles, setImproveRoles] = useState<string[] | null>(null);
    const [applyingImprove, setApplyingImprove] = useState(false);
    const [expandedImproveCard, setExpandedImproveCard] = useState<string | null>(null);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

    // Load existing results or start fresh analysis
    const loadOrStart = async () => {
        if (!projectId || projectId === 'new') return;
        setStarted(true);
        setError(null);
        try {
            const token = await getAccessToken();
            const statusResp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/status`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (statusResp.ok) {
                const data = await statusResp.json();
                if (data.agents && data.agents.length > 0) {
                    setAgents(data.agents);
                    if (data.project_name) setProjectName(data.project_name);
                    if (data.overall_score != null) setOverallScore(data.overall_score);
                    if (data.overall_verdict) setOverallVerdict(data.overall_verdict);

                    const done = data.agents.every((a: AgentResult) => a.status === "complete" || a.status === "error");
                    if (done) {
                        shouldAutoNavigateOnDoneRef.current = false;
                        setAllDone(true);
                        return;
                    }

                    shouldAutoNavigateOnDoneRef.current = true;
                    pollResults();
                    return;
                }
            }

            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/run`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (resp.status === 409) {
                console.log("CSuite run already in progress, polling for results");
                // Immediately check status — if all agents are still pending
                // after a few quick polls, show the stuck banner so user can retry
                pollResults();
                return;
            }
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(_extractErrorMsg(body, resp.status));
            }
            const data = await resp.json();
            setProjectName(data.project_name || "");
            shouldAutoNavigateOnDoneRef.current = true;
            pollResults();
        } catch (e: any) {
            setError(e.message);
            setStarted(false);
            shouldAutoNavigateOnDoneRef.current = false;
        }
    };

    const pollResults = async () => {
        setStuck(false);
        pollCountRef.current = 0;

        const refreshStatus = async () => {
            try {
                pollCountRef.current += 1;
                const token = await getAccessToken();
                const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!resp.ok) return;
                const data = await resp.json();

                if (data.agents) {
                    setAgents(prev => {
                        const incoming = new Map<string, AgentResult>(data.agents.map((a: AgentResult) => [a.role, a]));
                        return prev.map(existing => {
                            const updated = incoming.get(existing.role);
                            if (!updated) return existing;
                            return {
                                ...existing,
                                ...updated,
                                strengths: updated.strengths ?? existing.strengths ?? [],
                                risks: updated.risks ?? existing.risks ?? [],
                                suggestions: updated.suggestions ?? existing.suggestions ?? [],
                                key_metrics: updated.key_metrics ?? existing.key_metrics ?? [],
                                priority_actions: updated.priority_actions ?? existing.priority_actions ?? [],
                            };
                        });
                    });
                }
                if (data.project_name) setProjectName(data.project_name);
                if (data.overall_score != null) setOverallScore(data.overall_score);
                if (data.overall_verdict) setOverallVerdict(data.overall_verdict);

                const done = data.agents?.every((a: AgentResult) => a.status === "complete" || a.status === "error");
                if (done) {
                    setAllDone(true);
                    setAgents(prev => {
                        const scored = prev.filter(a => a.score != null);
                        if (scored.length > 0) {
                            const avg = Math.round(scored.reduce((s, a) => s + (a.score || 0), 0) / scored.length);
                            setOverallScore(avg);
                            setOverallVerdict(avg >= 70 ? "go" : avg >= 50 ? "conditional" : "no_go");
                        }
                        return prev;
                    });
                    if (pollingRef.current) clearInterval(pollingRef.current);
                    if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
                    return;
                }

                const allPending = data.agents?.every((a: AgentResult) => a.status === "pending");
                if (allPending && pollCountRef.current >= POLL_TIMEOUT) {
                    if (pollingRef.current) clearInterval(pollingRef.current);
                    pollingRef.current = null;
                    setStuck(true);
                }
            } catch (e) {
                console.error("Status refresh error:", e);
            }
        };

        const startSSE = async () => {
            const token = await getAccessToken();
            if (!token || !projectId) return;
            const url = `${getApiBaseUrl()}/api/v1/projects/${projectId}/events?token=${encodeURIComponent(token)}`;
            const es = new EventSource(url);
            sseRef.current = es;

            es.onmessage = (evt) => {
                try {
                    const payload = JSON.parse(evt.data);
                    if (payload.type === "csuite_update") {
                        refreshStatus();
                    }
                } catch { /* ignore non-JSON messages */ }
            };

            es.onerror = () => {
                es.close();
                sseRef.current = null;
                if (!pollingRef.current) {
                    pollingRef.current = setInterval(refreshStatus, 30_000);
                }
            };
        };

        refreshStatus();
        startSSE();
        pollingRef.current = setInterval(refreshStatus, 30_000);
    };

    const handleRunAgain = async () => {
        shouldAutoNavigateOnDoneRef.current = false;
        setError(null);
        setAllDone(false);
        setStopping(false);
        setStoppingRole(null);
        if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
        if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/run?force=true`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(_extractErrorMsg(body, resp.status));
            }
            setAgents(createPendingAgents());
            setOverallScore(null);
            setOverallVerdict(null);
            pollResults();
        } catch (e: any) {
            setError(e.message);
        }
    };

    const handleRefine = async () => {
        shouldAutoNavigateOnDoneRef.current = false;
        setRefining(true);
        setAllDone(false);
        setError(null);
        try {
            if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
            if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/refine`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ corrections }),
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(_extractErrorMsg(body, resp.status));
            }

            setAgents(createPendingAgents());
            setOverallScore(null);
            setOverallVerdict(null);

            await pollResults();
        } catch (e: any) {
            setError(e.message);
        } finally {
            setRefining(false);
        }
    };

    // ── Regenerate handlers ──────────────────────────────────────────────
    const _regenRoles = async (roles: string[]) => {
        if (!projectId || roles.length === 0) return;
        shouldAutoNavigateOnDoneRef.current = false;
        setRegeneratingRoles(prev => [...prev, ...roles]);
        setAllDone(false);
        setError(null);
        if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
        if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/improve/apply`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({ roles, enhanced_context: "" }),
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(body.detail || "Failed to regenerate");
            }
            setAgents(prev => prev.map(a =>
                roles.includes(a.role)
                    ? { ...a, status: "pending", score: null, recommendation: null,
                        deep_analysis: null, strengths: [], risks: [], suggestions: [],
                        key_metrics: [], timeline: null, priority_actions: [],
                        competitive_note: null, verdict: null, error_message: null }
                    : a
            ));
            pollResults();
        } catch (e: any) {
            setError(e.message);
            setAllDone(true);
        } finally {
            setRegeneratingRoles(prev => prev.filter(r => !roles.includes(r)));
        }
    };

    const handleRegenerateAll = () => {
        const stoppedRoles = agents
            .filter(a => a.status === "error" && a.error_message === "Stopped by user")
            .map(a => a.role);
        _regenRoles(stoppedRoles);
    };

    const handleRegenerateAgent = (role: string) => _regenRoles([role]);

    const handleStopAll = async () => {
        if (stopping || !projectId) return;
        shouldAutoNavigateOnDoneRef.current = false;
        setStopping(true);
        if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
        if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
        try {
            const token = await getAccessToken();
            await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/stop`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            setAgents(prev => prev.map(a =>
                (a.status === "pending" || a.status === "running")
                    ? { ...a, status: "error", error_message: "Stopped by user" }
                    : a
            ));
            setAllDone(true);
        } catch (e) {
            console.error("Stop all failed:", e);
        } finally {
            setStopping(false);
        }
    };

    const handleStopAgent = async (role: string) => {
        if (stoppingRole || !projectId) return;
        setStoppingRole(role);
        try {
            const token = await getAccessToken();
            await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/stop/${role}`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            setAgents(prev => prev.map(a =>
                a.role === role && (a.status === "pending" || a.status === "running")
                    ? { ...a, status: "error", error_message: "Stopped by user" }
                    : a
            ));
        } catch (e) {
            console.error(`Stop ${role} failed:`, e);
        } finally {
            setStoppingRole(null);
        }
    };

    // ── AI Improve handlers ──────────────────────────────────────────────
    const handleImprove = async (roles?: string[]) => {
        shouldAutoNavigateOnDoneRef.current = false;
        setImproveLoading(true);
        setImproveRoles(roles || null);
        setImprovePlan(null);
        setError(null);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/improve`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ roles: roles || null }),
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(body.detail || "Failed to generate improvement plan");
            }
            const plan = await resp.json();
            setImprovePlan(normalizeImprovePlan(plan));
        } catch (e: any) {
            setError(e.message);
        } finally {
            setImproveLoading(false);
        }
    };

    const handleApplyImprovement = async () => {
        if (!improvePlan?.improvements) return;
        shouldAutoNavigateOnDoneRef.current = false;
        setApplyingImprove(true);
        setError(null);
        try {
            if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
            if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
            const roles = Object.keys(improvePlan.improvements);
            const enhancedParts = roles.map(r => {
                const imp = improvePlan.improvements[r];
                return `[${r.toUpperCase()} Improvements]\n${imp.enhanced_context}`;
            });
            const enhancedContext = enhancedParts.join("\n\n");

            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/improve/apply`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ roles, enhanced_context: enhancedContext }),
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(body.detail || "Failed to apply improvements");
            }

            setAgents(prev => prev.map(a =>
                roles.includes(a.role)
                    ? {
                        ...a,
                        status: "pending",
                        score: null,
                        recommendation: null,
                        deep_analysis: null,
                        strengths: [],
                        risks: [],
                        suggestions: [],
                        key_metrics: [],
                        timeline: null,
                        priority_actions: [],
                        competitive_note: null,
                        verdict: null,
                    }
                    : a
            ));
            setAllDone(false);
            setImprovePlan(null);
            setImproveRoles(null);

            await pollResults();
        } catch (e: any) {
            setError(e.message);
        } finally {
            setApplyingImprove(false);
        }
    };

    useEffect(() => {
        return () => {
            if (pollingRef.current) clearInterval(pollingRef.current);
            if (sseRef.current) { sseRef.current.close(); sseRef.current = null; }
        };
    }, []);

    // Auto-load on mount (loads existing results or starts fresh)
    useEffect(() => {
        if (autoStartRequestedRef.current) return;
        autoStartRequestedRef.current = true;
        if (!started) loadOrStart();
    }, []);

    useEffect(() => {
        if (!allDone || !projectId) return;
        if (!shouldAutoNavigateOnDoneRef.current || hasAutoNavigatedRef.current) return;
        const hasSuccessfulAgent = agents.some((a) => a.status === "complete");
        if (!hasSuccessfulAgent) return;
        hasAutoNavigatedRef.current = true;
        navigate(`/app/projects/${projectId}`, { replace: true });
    }, [allDone, agents, navigate, projectId]);

    // ── Helpers ──────────────────────────────────────────────────────────
    const _extractErrorMsg = (body: any, status: number): string => {
        const detail = body?.detail;
        if (typeof detail === "string") return detail;
        if (status === 402) {
            const limit = detail?.limit ?? "";
            const used = detail?.used ?? "";
            return `Monthly C-Suite analysis limit reached (${used}/${limit} used). Upgrade your plan to run more.`;
        }
        return typeof detail === "object" && detail !== null
            ? JSON.stringify(detail)
            : "Failed to start analysis";
    };

    const normalizeImprovePlan = (raw: any): ImprovementPlan => {
        const rawImprovements = raw?.improvements;
        const improvements = rawImprovements && typeof rawImprovements === "object"
            ? Object.fromEntries(
                Object.entries(rawImprovements).map(([role, detail]) => {
                    const safeDetail = detail && typeof detail === "object" ? detail as Partial<ImprovementDetail> : {};
                    const asStringArray = (value: unknown): string[] => {
                        if (!Array.isArray(value)) return [];
                        return value.map(item => String(item)).filter(Boolean);
                    };

                    return [role, {
                        current_score: typeof safeDetail.current_score === "number" ? safeDetail.current_score : 0,
                        key_weaknesses: asStringArray(safeDetail.key_weaknesses),
                        recommended_changes: asStringArray(safeDetail.recommended_changes),
                        enhanced_context: typeof safeDetail.enhanced_context === "string" ? safeDetail.enhanced_context : "",
                    } satisfies ImprovementDetail];
                })
            )
            : {};

        return {
            improvements,
            summary: typeof raw?.summary === "string" ? raw.summary : "",
        };
    };

    const completedCount = agents.filter(a => a.status === "complete" || a.status === "error").length;
    const avgScore = agents.filter(a => a.score != null).reduce((s, a) => s + (a.score || 0), 0) / Math.max(1, agents.filter(a => a.score != null).length);
    const improveEntries = Object.entries(improvePlan?.improvements ?? {});

    const getVerdictColor = (v: string | null) => {
        if (v === "go") return "text-emerald-400";
        if (v === "no_go") return "text-red-400";
        if (v === "conditional") return "text-amber-400";
        return "text-tertiary";
    };

    const getStatusIcon = (agent: AgentResult) => {
        if (agent.status === "complete") return <span className="material-symbols-outlined text-base leading-none text-emerald-400">check_circle</span>;
        if (agent.status === "running") return <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />;
        if (agent.status === "error" && agent.error_message === "Stopped by user")
            return <span className="material-symbols-outlined text-base leading-none text-tertiary">stop_circle</span>;
        if (agent.status === "error") return <span className="material-symbols-outlined text-base leading-none text-red-400">cancel</span>;
        return <div className="w-4 h-4 rounded-full border-2 border-outline-variant/40" />;
    };

    if (!projectId || projectId === 'new') {
        return (
            <div className="max-w-3xl mx-auto px-6 py-20 text-center">
                <span className="material-symbols-outlined text-5xl text-tertiary mb-4 block">psychology</span>
                <h2 className="text-2xl font-black text-on-surface uppercase mb-3" style={{ letterSpacing: "-0.03em" }}>No Project Selected</h2>
                <p className="text-tertiary mb-6">Save an idea from the Ideation stage first — the C-Suite executive board will then analyse your concept.</p>
                <button
                    onClick={() => navigate(`/app/ideation`)}
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-on-primary font-bold uppercase text-xs tracking-wider hover:opacity-90 transition-opacity"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>lightbulb</span>
                    Go to Ideation
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto px-6 py-10">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                    <span className="material-symbols-outlined text-2xl text-on-primary-container">psychology</span>
                    <h1 className="text-3xl font-black text-on-surface uppercase" style={{ letterSpacing: "-0.05em" }}>C-Suite Analysis</h1>
                </div>
                {projectName && <p className="text-secondary text-lg ml-9">{projectName}</p>}
            </motion.div>

            {stuck && (
                <div className="mb-6 flex items-start justify-between gap-4 steel-gradient rounded-[var(--radius-module)] border border-amber-500/30 px-5 py-4 text-sm text-on-surface">
                    <div>
                        <div className="font-black text-amber-300 uppercase tracking-widest">Analysis stalled before any agents started.</div>
                        <div className="mt-1 text-secondary">Retry the run to restart the background job and resume the C-suite pass.</div>
                    </div>
                    <button
                        onClick={handleRunAgain}
                        className="shrink-0 rounded-full border border-outline-variant/30 px-3 py-1.5 font-black text-xs uppercase tracking-widest text-on-surface transition-colors hover:bg-surface-container"
                    >
                        Run Again
                    </button>
                </div>
            )}

            {/* Overall progress bar */}
            <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 mb-8">
                <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-secondary font-black uppercase tracking-widest">{completedCount}/{agents.length} agents completed</span>
                    <div className="flex items-center gap-3 flex-wrap justify-end">
                        {overallScore != null ? (
                            <span className="text-lg font-black text-on-primary-container bg-primary-container px-3 py-1 rounded-full uppercase tracking-widest">{Math.round(overallScore)}/100</span>
                        ) : agents.some(a => a.score != null) ? (
                            <span className="text-lg font-black text-secondary">{Math.round(avgScore)}/100 avg so far</span>
                        ) : null}
                        {allDone && projectId && (
                            <ExportMenu
                                projectId={projectId}
                                target="csuite"
                                label="Download Report"
                                size="sm"
                            />
                        )}
                        {allDone && (
                            <button
                                onClick={handleRunAgain}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-outline-variant/30 text-tertiary text-xs font-black uppercase tracking-widest hover:border-outline-variant hover:text-on-surface hover:bg-surface-container transition-all"
                            >
                                <span className="material-symbols-outlined text-sm leading-none">refresh</span>
                                Re-run
                            </button>
                        )}
                        {!allDone && agents.some(a => a.status === "pending" || a.status === "running") && (
                            <button
                                onClick={handleStopAll}
                                disabled={stopping}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-outline-variant/30 text-tertiary text-xs font-black uppercase tracking-widest hover:border-red-500/40 hover:text-red-400 hover:bg-surface-container transition-all disabled:opacity-50"
                            >
                                {stopping
                                    ? <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                    : <span className="material-symbols-outlined text-sm leading-none">stop_circle</span>}
                                Stop All
                            </button>
                        )}
                        {allDone && agents.some(a => a.status === "error" && a.error_message === "Stopped by user") && (
                            <button
                                onClick={handleRegenerateAll}
                                disabled={regeneratingRoles.length > 0}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-outline-variant/30 text-on-surface text-xs font-black uppercase tracking-widest hover:border-outline-variant hover:bg-surface-container transition-all disabled:opacity-50"
                            >
                                {regeneratingRoles.length > 0
                                    ? <div className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                    : <span className="material-symbols-outlined text-sm leading-none">refresh</span>}
                                Regenerate All
                            </button>
                        )}
                        {allDone && overallScore != null && overallScore < 85 && (
                            <button
                                onClick={() => handleImprove()}
                                disabled={improveLoading}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-all disabled:opacity-50"
                            >
                                {improveLoading && !improveRoles ? (
                                    <div className="w-3.5 h-3.5 border-2 border-on-primary-container/30 border-t-on-primary-container rounded-full animate-spin" />
                                ) : (
                                    <span className="material-symbols-outlined text-sm leading-none">auto_awesome</span>
                                )}
                                {improveLoading && !improveRoles ? "Analyzing..." : "Improve All"}
                            </button>
                        )}
                    </div>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-secondary rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${(completedCount / agents.length) * 100}%` }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
                {overallVerdict && (
                    <p className={cn("mt-3 text-xs font-black uppercase tracking-widest", getVerdictColor(overallVerdict))}>
                        Final Verdict: {overallVerdict === "go" ? "GO — Proceed to Build" : overallVerdict === "no_go" ? "NO GO — Needs Rework" : "CONDITIONAL — Review Suggestions"}
                    </p>
                )}
            </div>

            {/* Orchestration Timeline */}
            <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 mb-8">
                <h3 className="text-xs font-black uppercase tracking-widest text-secondary mb-4">Orchestration Timeline</h3>
                <div className="flex items-center gap-1 overflow-x-auto pb-2">
                    {agents.map((agent, i) => {
                        const meta = ROLE_META[agent.role] || { label: agent.role, color: "text-tertiary" };
                        const isComplete = agent.status === "complete";
                        const isRunning = agent.status === "running";
                        const isError = agent.status === "error";
                        return (
                            <div key={agent.role} className="flex items-center shrink-0">
                                <div className={cn(
                                    "flex items-center gap-2 px-3 py-2 rounded-lg border transition-all",
                                    isRunning ? "border-primary/40 bg-primary-container/20" :
                                    isComplete ? "border-emerald-500/20 bg-emerald-500/5" :
                                    isError ? "border-red-500/20 bg-surface-container" :
                                    "border-outline-variant/20 bg-surface-container"
                                )}>
                                    {isComplete && <span className="material-symbols-outlined text-xs leading-none text-emerald-400">check_circle</span>}
                                    {isRunning && <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />}
                                    {isError && <span className="material-symbols-outlined text-xs leading-none text-red-400">cancel</span>}
                                    {agent.status === "pending" && <div className="w-3 h-3 rounded-full border border-outline-variant/40" />}
                                    <span className={cn(
                                        "text-[11px] font-black uppercase tracking-widest",
                                        isRunning ? "text-on-primary-container" : isComplete ? meta.color : "text-secondary"
                                    )}>
                                        {meta.label}
                                    </span>
                                </div>
                                {i < agents.length - 1 && (
                                    <div className={cn("w-6 h-px mx-0.5", isComplete ? "bg-emerald-500/40" : "bg-outline-variant/20")} />
                                )}
                            </div>
                        );
                    })}
                </div>
                {agents.some(a => a.status === "running") && (
                    <div className="mt-3 text-xs text-secondary flex items-center gap-1.5 font-black uppercase tracking-widest">
                        <span className="w-3 h-3 border-2 border-secondary border-t-transparent rounded-full animate-spin" />
                        Routing analysis to specialist agents...
                    </div>
                )}
                {allDone && (
                    <p className="mt-3 text-xs text-emerald-400 flex items-center gap-1.5 font-black uppercase tracking-widest">
                        <span className="material-symbols-outlined text-sm leading-none">check_circle</span>
                        Executive synthesis complete — all agents have reported.
                    </p>
                )}
            </div>

            {/* Agent cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
                {agents.map((agent, i) => {
                    const meta = ROLE_META[agent.role] || { label: agent.role, icon: "hub", color: "text-tertiary", gradient: "from-zinc-500/20 to-zinc-500/20" };
                    const expanded = agent.status === "complete";
                    const isClickable = agent.status === "complete";
                    return (
                        <motion.div
                            key={agent.role}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            onClick={() => isClickable && setSelectedAgent(agent.role)}
                            className={cn(
                                "steel-gradient ghost-border rounded-[var(--radius-module)] p-5 transition-all",
                                isClickable ? "cursor-pointer hover:border-outline-variant/60" : "",
                                agent.status === "running" ? "border-primary/40" : ""
                            )}
                        >
                            {/* Agent header */}
                            <div className="flex items-center gap-3 mb-3">
                                <div className={cn("w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center", meta.gradient)}>
                                    <span className={cn("material-symbols-outlined text-xl leading-none", meta.color)}>{meta.icon}</span>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-black text-on-surface text-xs uppercase tracking-widest">{meta.label}</span>
                                        {getStatusIcon(agent)}
                                    </div>
                                    {agent.score != null && (
                                        <span className="text-xs font-black text-on-primary-container">{agent.score}/100</span>
                                    )}
                                </div>
                                {agent.verdict && (
                                    <span className={cn(
                                        "text-[10px] font-black uppercase px-2 py-0.5 rounded-full border tracking-widest",
                                        agent.verdict === "go"
                                            ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                                            : agent.verdict === "no_go"
                                                ? "text-red-400 border-red-500/30 bg-red-500/10"
                                                : "text-amber-400 border-amber-500/30 bg-amber-500/10"
                                    )}>
                                        {agent.verdict === "no_go" ? "NO GO" : agent.verdict.toUpperCase()}
                                    </span>
                                )}
                            </div>

                            {/* Status indicator */}
                            {agent.status === "running" && (
                                <div className="flex items-center gap-2 text-xs text-secondary mb-3 font-black uppercase tracking-widest">
                                    <div className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                    Analyzing...
                                </div>
                            )}
                            {agent.status === "pending" && (
                                <div className="text-xs text-tertiary font-black uppercase tracking-widest">Waiting...</div>
                            )}
                            {(agent.status === "running" || agent.status === "pending") && !stopping && (
                                <button
                                    onClick={(e) => { e.stopPropagation(); handleStopAgent(agent.role); }}
                                    disabled={stoppingRole === agent.role}
                                    className="mt-1 mb-2 w-full flex items-center justify-center gap-1.5 px-2 py-1 rounded-full border border-outline-variant/30 text-tertiary text-[11px] font-black uppercase tracking-widest hover:border-red-500/30 hover:text-red-400 hover:bg-surface-container transition-colors disabled:opacity-50"
                                >
                                    {stoppingRole === agent.role
                                        ? <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                        : <span className="material-symbols-outlined text-sm leading-none">stop_circle</span>}
                                    Stop
                                </button>
                            )}
                            {agent.status === "error" && agent.error_message === "Stopped by user" && (
                                <div className="flex flex-col gap-1.5 mb-2">
                                    <div className="flex items-center gap-1.5 text-xs text-tertiary font-black uppercase tracking-widest">
                                        <span className="material-symbols-outlined text-sm leading-none">stop_circle</span> Stopped
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleRegenerateAgent(agent.role); }}
                                        disabled={regeneratingRoles.includes(agent.role)}
                                        className="w-full flex items-center justify-center gap-1.5 px-2 py-1 rounded-full border border-outline-variant/30 text-on-surface text-[11px] font-black uppercase tracking-widest hover:border-outline-variant hover:bg-surface-container transition-colors disabled:opacity-50"
                                    >
                                        {regeneratingRoles.includes(agent.role)
                                            ? <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                            : <span className="material-symbols-outlined text-sm leading-none">refresh</span>}
                                        Regenerate
                                    </button>
                                </div>
                            )}
                            {agent.status === "error" && agent.error_message !== "Stopped by user" && (
                                <div className="flex flex-col gap-1.5 mb-2">
                                    <div className="flex items-center gap-1.5 text-xs text-red-400/80 truncate" title={agent.error_message ?? undefined}>
                                        <span className="material-symbols-outlined text-sm leading-none shrink-0">cancel</span>
                                        <span className="truncate">{agent.error_message || "Failed"}</span>
                                    </div>
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleRegenerateAgent(agent.role); }}
                                        disabled={regeneratingRoles.includes(agent.role)}
                                        className="w-full flex items-center justify-center gap-1.5 px-2 py-1 rounded-full border border-outline-variant/30 text-on-surface text-[11px] font-black uppercase tracking-widest hover:border-outline-variant hover:bg-surface-container transition-colors disabled:opacity-50"
                                    >
                                        {regeneratingRoles.includes(agent.role)
                                            ? <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                            : <span className="material-symbols-outlined text-sm leading-none">refresh</span>}
                                        Retry
                                    </button>
                                </div>
                            )}

                            {/* Completed content */}
                            {expanded && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="mt-2 space-y-3 text-xs"
                                >
                                    {agent.recommendation && (
                                        <p className="text-secondary leading-relaxed">{agent.recommendation}</p>
                                    )}
                                    {agent.strengths.length > 0 && (
                                        <div>
                                            <span className="text-emerald-400 font-black uppercase tracking-widest">Strengths</span>
                                            <ul className="mt-1 space-y-0.5">
                                                {agent.strengths.slice(0, 3).map((s, j) => (
                                                    <li key={j} className="text-secondary flex items-start gap-1.5">
                                                        <span className="text-emerald-400 mt-0.5">+</span> {s}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {agent.risks.length > 0 && (
                                        <div>
                                            <span className="text-red-400 font-black uppercase tracking-widest">Risks</span>
                                            <ul className="mt-1 space-y-0.5">
                                                {agent.risks.slice(0, 3).map((r, j) => (
                                                    <li key={j} className="text-secondary flex items-start gap-1.5">
                                                        <span className="text-red-400 mt-0.5">!</span> {r}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Per-card Improve button */}
                                    {agent.score != null && agent.score < 85 && allDone && (
                                        <button
                                            onClick={(e) => { e.stopPropagation(); handleImprove([agent.role]); }}
                                            disabled={improveLoading}
                                            className="mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-container text-on-primary-container text-[11px] font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                                        >
                                            {improveLoading && improveRoles?.includes(agent.role) ? (
                                                <div className="w-3 h-3 border-2 border-on-primary-container/30 border-t-on-primary-container rounded-full animate-spin" />
                                            ) : (
                                                <span className="material-symbols-outlined text-sm leading-none">auto_awesome</span>
                                            )}
                                            {improveLoading && improveRoles?.includes(agent.role) ? "Analyzing..." : "Improve"}
                                        </button>
                                    )}
                                    <div className="mt-3 pt-2 border-t border-outline-variant/20 flex items-center justify-end">
                                        <span className="text-[10px] text-secondary flex items-center gap-1 font-black uppercase tracking-widest">
                                            <span className="material-symbols-outlined text-xs leading-none">arrow_forward</span> Full analysis
                                        </span>
                                    </div>
                                </motion.div>
                            )}
                        </motion.div>
                    );
                })}
            </div>

            {/* ── Agent Detail Drawer ──────────────────────────────────── */}
            <AnimatePresence>
                {selectedAgent && (() => {
                    const agent = agents.find(a => a.role === selectedAgent)!;
                    const meta = ROLE_META[agent.role] || { label: agent.role, icon: "hub", color: "text-tertiary", gradient: "from-zinc-500/20 to-zinc-500/20" };
                    return (
                        <motion.div
                            key="agent-drawer-overlay"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setSelectedAgent(null)}
                            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                        >
                            <motion.div
                                key="agent-drawer"
                                initial={{ x: "100%" }}
                                animate={{ x: 0 }}
                                exit={{ x: "100%" }}
                                transition={{ type: "spring", damping: 30, stiffness: 300 }}
                                onClick={e => e.stopPropagation()}
                                className="fixed right-0 top-14 bottom-0 w-full max-w-2xl bg-surface-container border-l border-outline-variant/30 shadow-2xl flex flex-col z-50"
                            >
                                {/* Drawer header */}
                                <div className={cn("flex items-center justify-between px-6 py-5 bg-gradient-to-r border-b border-outline-variant/20", meta.gradient)}>
                                    <div className="flex items-center gap-3">
                                        <div className={cn("w-10 h-10 rounded-lg bg-gradient-to-br border border-outline-variant/20 flex items-center justify-center", meta.gradient)}>
                                            <span className={cn("material-symbols-outlined text-xl leading-none", meta.color)}>{meta.icon}</span>
                                        </div>
                                        <div>
                                            <h2 className="text-lg font-black text-on-surface uppercase" style={{ letterSpacing: "-0.05em" }}>{meta.label} Analysis</h2>
                                            {agent.score != null && (
                                                <div className="flex items-center gap-2">
                                                    <span className={cn("text-sm font-black uppercase tracking-widest", meta.color)}>{agent.score}/100</span>
                                                    {agent.verdict && (
                                                        <span className={cn(
                                                            "text-[10px] font-black uppercase px-2 py-0.5 rounded-full border tracking-widest",
                                                            agent.verdict === "go" ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                                                            : agent.verdict === "no_go" ? "text-red-400 border-red-500/30 bg-red-500/10"
                                                            : "text-amber-400 border-amber-500/30 bg-amber-500/10"
                                                        )}>{agent.verdict === "no_go" ? "NO GO" : agent.verdict.toUpperCase()}</span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <button onClick={() => setSelectedAgent(null)} className="p-2 rounded-lg hover:bg-surface-container text-tertiary hover:text-on-surface transition-colors">
                                        <span className="material-symbols-outlined text-xl">close</span>
                                    </button>
                                </div>

                                {/* Drawer body */}
                                <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
                                    {/* Executive Summary */}
                                    {agent.recommendation && (
                                        <div>
                                            <h3 className="text-xs font-black uppercase tracking-widest text-tertiary mb-2">Executive Summary</h3>
                                            <p className="text-sm text-on-surface leading-relaxed bg-surface rounded-xl p-4 border border-outline-variant/20">{agent.recommendation}</p>
                                        </div>
                                    )}

                                    {/* Deep Analysis */}
                                    {agent.deep_analysis && (
                                        <div>
                                            <h3 className="text-xs font-black uppercase tracking-widest text-tertiary mb-2">Deep Analysis</h3>
                                            <div className="text-sm text-secondary leading-relaxed space-y-3">
                                                {agent.deep_analysis.split(/\n\n+/).map((para, i) => (
                                                    <p key={i} className="text-secondary">{para}</p>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Strengths + Risks side by side */}
                                    <div className="grid grid-cols-2 gap-4">
                                        {(agent.strengths ?? []).length > 0 && (
                                            <div>
                                                <h3 className="text-xs font-black uppercase tracking-widest text-emerald-500/70 mb-2">Strengths</h3>
                                                <ul className="space-y-2">
                                                    {(agent.strengths ?? []).map((s, j) => (
                                                        <li key={j} className="text-xs text-secondary flex items-start gap-1.5">
                                                            <span className="text-emerald-400 mt-0.5 shrink-0">+</span>{s}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {(agent.risks ?? []).length > 0 && (
                                            <div>
                                                <h3 className="text-xs font-black uppercase tracking-widest text-red-500/70 mb-2">Risks</h3>
                                                <ul className="space-y-2">
                                                    {(agent.risks ?? []).map((r, j) => (
                                                        <li key={j} className="text-xs text-secondary flex items-start gap-1.5">
                                                            <span className="text-red-400 mt-0.5 shrink-0">!</span>{r}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>

                                    {/* Priority Actions */}
                                    {(agent.priority_actions ?? []).length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-black uppercase tracking-widest text-on-primary-container/70 mb-2">Priority Actions</h3>
                                            <ol className="space-y-2">
                                                {(agent.priority_actions ?? []).map((a, j) => (
                                                    <li key={j} className="text-xs text-secondary flex items-start gap-2.5 bg-primary-container/20 border border-outline-variant/20 rounded-lg px-3 py-2">
                                                        <span className="text-on-primary-container font-black shrink-0">{j + 1}.</span>{a}
                                                    </li>
                                                ))}
                                            </ol>
                                        </div>
                                    )}

                                    {/* Suggestions */}
                                    {(agent.suggestions ?? []).length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-black uppercase tracking-widest text-amber-500/70 mb-2">Suggestions</h3>
                                            <ul className="space-y-2">
                                                {(agent.suggestions ?? []).map((s, j) => (
                                                    <li key={j} className="text-xs text-secondary flex items-start gap-1.5">
                                                        <span className="text-amber-400 mt-0.5 shrink-0">→</span>{s}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Key Metrics + Timeline */}
                                    <div className="grid grid-cols-2 gap-4">
                                        {(agent.key_metrics ?? []).length > 0 && (
                                            <div>
                                                <h3 className="text-xs font-black uppercase tracking-widest text-cyan-500/70 mb-2">Key Metrics</h3>
                                                <ul className="space-y-1.5">
                                                    {(agent.key_metrics ?? []).map((m, j) => (
                                                        <li key={j} className="text-xs text-secondary flex items-start gap-1.5">
                                                            <span className="text-cyan-400 mt-0.5 shrink-0">◆</span>{m}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {agent.timeline && (
                                            <div>
                                                <h3 className="text-xs font-black uppercase tracking-widest text-tertiary mb-2">Timeline</h3>
                                                <p className="text-xs text-secondary leading-relaxed bg-surface rounded-lg p-3 border border-outline-variant/20">{agent.timeline}</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Competitive Note */}
                                    {agent.competitive_note && (
                                        <div>
                                            <h3 className="text-xs font-black uppercase tracking-widest text-tertiary mb-2">Competitive Perspective</h3>
                                            <p className="text-xs text-secondary leading-relaxed italic border-l-2 border-outline-variant/30 pl-3">{agent.competitive_note}</p>
                                        </div>
                                    )}
                                </div>

                                {/* Drawer footer */}
                                {agent.score != null && agent.score < 85 && allDone && (
                                    <div className="px-6 py-4 border-t border-outline-variant/20 bg-surface">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); setSelectedAgent(null); handleImprove([agent.role]); }}
                                            disabled={improveLoading}
                                            className="w-full flex items-center justify-center gap-2 h-10 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                                        >
                                            <span className="material-symbols-outlined text-base leading-none">auto_awesome</span> Improve this analysis
                                        </button>
                                    </div>
                                )}
                            </motion.div>
                        </motion.div>
                    );
                })()}
            </AnimatePresence>

            {/* ── AI Improvement Plan Panel ────────────────────────────── */}
            <AnimatePresence>
                {(improvePlan || improveLoading) && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mb-8"
                    >
                        <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <span className="material-symbols-outlined text-xl text-on-primary-container">auto_awesome</span>
                                    <h3 className="text-lg font-black text-on-surface uppercase tracking-widest">AI Improvement Plan</h3>
                                </div>
                                <button
                                    onClick={() => { setImprovePlan(null); setImproveRoles(null); }}
                                    className="p-1 rounded-lg hover:bg-surface-container text-tertiary hover:text-on-surface transition-colors"
                                >
                                    <span className="material-symbols-outlined text-base leading-none">close</span>
                                </button>
                            </div>

                            {improveLoading ? (
                                <div className="flex items-center gap-3 py-8 justify-center">
                                    <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                                    <span className="text-sm text-secondary font-black uppercase tracking-widest">AI is analyzing scores and generating improvements...</span>
                                </div>
                            ) : improvePlan ? (
                                <>
                                    {improvePlan.summary && (
                                        <p className="text-sm text-secondary mb-4 leading-relaxed">{improvePlan.summary}</p>
                                    )}

                                    <div className="space-y-3 mb-5">
                                        {improveEntries.length === 0 && (
                                            <div className="rounded-xl border border-outline-variant/20 bg-surface px-4 py-3 text-sm text-secondary">
                                                No agent-specific improvement details were returned for this run.
                                            </div>
                                        )}
                                        {improveEntries.map(([role, detail]) => {
                                            const meta = ROLE_META[role];
                                            const isExpanded = expandedImproveCard === role;
                                            return (
                                                <div key={role} className="bg-surface border border-outline-variant/20 rounded-xl overflow-hidden">
                                                    <button
                                                        onClick={() => setExpandedImproveCard(isExpanded ? null : role)}
                                                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-container/30 transition-colors"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <span className={cn("font-black text-sm uppercase tracking-widest", meta?.color || "text-secondary")}>
                                                                {meta?.label || role.toUpperCase()}
                                                            </span>
                                                            <span className="text-xs text-tertiary font-black uppercase tracking-widest">{detail.current_score}/100</span>
                                                            <span className="material-symbols-outlined text-sm leading-none text-tertiary">arrow_forward</span>
                                                            <span className="text-xs text-emerald-400 font-black uppercase tracking-widest">Targeting 85+</span>
                                                        </div>
                                                        <span className="material-symbols-outlined text-base leading-none text-tertiary">
                                                            {isExpanded ? "expand_less" : "expand_more"}
                                                        </span>
                                                    </button>
                                                    <AnimatePresence>
                                                        {isExpanded && (
                                                            <motion.div
                                                                initial={{ height: 0, opacity: 0 }}
                                                                animate={{ height: "auto", opacity: 1 }}
                                                                exit={{ height: 0, opacity: 0 }}
                                                                className="overflow-hidden"
                                                            >
                                                                <div className="px-4 pb-4 space-y-3 text-xs">
                                                                    {detail.key_weaknesses.length > 0 && (
                                                                        <div>
                                                                            <span className="text-red-400 font-black uppercase tracking-widest">Key Weaknesses</span>
                                                                            <ul className="mt-1 space-y-0.5">
                                                                                {detail.key_weaknesses.map((w, i) => (
                                                                                    <li key={i} className="text-secondary flex items-start gap-1.5">
                                                                                        <span className="text-red-400 mt-0.5">!</span> {w}
                                                                                    </li>
                                                                                ))}
                                                                            </ul>
                                                                        </div>
                                                                    )}
                                                                    {detail.recommended_changes.length > 0 && (
                                                                        <div>
                                                                            <span className="text-emerald-400 font-black uppercase tracking-widest">Recommended Changes</span>
                                                                            <ul className="mt-1 space-y-0.5">
                                                                                {detail.recommended_changes.map((c, i) => (
                                                                                    <li key={i} className="text-secondary flex items-start gap-1.5">
                                                                                        <span className="text-emerald-400 mt-0.5">+</span> {c}
                                                                                    </li>
                                                                                ))}
                                                                            </ul>
                                                                        </div>
                                                                    )}
                                                                    {detail.enhanced_context && (
                                                                        <div>
                                                                            <span className="text-on-primary-container font-black uppercase tracking-widest">Enhanced Context</span>
                                                                            <p className="mt-1 text-secondary leading-relaxed bg-surface rounded-lg p-3 border border-outline-variant/20">
                                                                                {detail.enhanced_context}
                                                                            </p>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </motion.div>
                                                        )}
                                                    </AnimatePresence>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    <div className="flex items-center justify-end gap-3">
                                        <button
                                            onClick={() => { setImprovePlan(null); setImproveRoles(null); }}
                                            className="h-9 px-4 rounded-full border border-outline-variant/30 text-secondary text-xs font-black uppercase tracking-widest hover:bg-surface-container transition-colors"
                                        >
                                            Dismiss
                                        </button>
                                        <button
                                            onClick={handleApplyImprovement}
                                            disabled={applyingImprove || improveEntries.length === 0}
                                            className="flex items-center gap-2 h-9 px-5 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                                        >
                                            {applyingImprove ? (
                                                <div className="w-4 h-4 border-2 border-on-primary-container/30 border-t-on-primary-container rounded-full animate-spin" />
                                            ) : (
                                                <span className="material-symbols-outlined text-base leading-none">refresh</span>
                                            )}
                                            {applyingImprove ? "Re-running..." : `Accept & Re-run ${improveEntries.length} Agent${improveEntries.length > 1 ? "s" : ""}`}
                                        </button>
                                    </div>
                                </>
                            ) : null}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Proceed button */}
            {allDone && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                >
                    <div className="max-w-3xl mx-auto steel-gradient ghost-border rounded-[var(--radius-module)] p-4">
                        <label className="block text-xs text-tertiary mb-2 font-black uppercase tracking-widest">Corrections / context for re-run (optional)</label>
                        <textarea
                            value={corrections}
                            onChange={(e) => setCorrections(e.target.value)}
                            placeholder="Add clarifications, constraints, target users, pricing assumptions, or technical requirements..."
                            className="w-full min-h-24 bg-background border border-outline-variant/30 rounded-lg px-3 py-2 text-sm text-on-surface placeholder:text-tertiary focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                        <div className="mt-3 flex justify-end">
                            <button
                                onClick={handleRefine}
                                disabled={!corrections.trim() || refining}
                                className="h-9 px-4 rounded-full border border-outline-variant/30 text-on-surface text-xs font-black uppercase tracking-widest hover:bg-surface-container disabled:opacity-50 transition-colors"
                            >
                                {refining ? "Refining..." : "Re-run with Corrections"}
                            </button>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <button
                            onClick={() => navigate(`/app/projects/${projectId}`)}
                            className="flex items-center gap-2 h-12 px-8 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity"
                        >
                            Proceed to Project Dashboard
                            <span className="material-symbols-outlined text-base leading-none">arrow_forward</span>
                        </button>
                    </div>
                </motion.div>
            )}

            {error && (
                <div className="mt-4 px-4 py-3 rounded-xl bg-surface-container border border-outline-variant/30 text-on-surface text-sm text-center font-black uppercase tracking-widest">
                    {error}
                </div>
            )}
        </div>
    );
}
