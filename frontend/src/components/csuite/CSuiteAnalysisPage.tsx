import { useEffect, useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import {
    Crown, Code2, TrendingUp, Megaphone, Box, Settings, Palette,
    CheckCircle2, Loader2, XCircle, ArrowRight, Info,
    Sparkles, Zap, ChevronDown, ChevronUp, RotateCcw, X
} from "lucide-react";
import { ExportMenu } from "../shared/ExportMenu";

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
}

const ROLE_META: Record<string, { label: string; icon: any; color: string; gradient: string }> = {
    ceo: { label: "CEO", icon: Crown, color: "text-amber-400", gradient: "from-amber-500/20 to-orange-500/20" },
    cto: { label: "CTO", icon: Code2, color: "text-cyan-400", gradient: "from-cyan-500/20 to-blue-500/20" },
    cfo: { label: "CFO", icon: TrendingUp, color: "text-green-400", gradient: "from-green-500/20 to-emerald-500/20" },
    cmo: { label: "CMO", icon: Megaphone, color: "text-pink-400", gradient: "from-pink-500/20 to-rose-500/20" },
    cpo: { label: "CPO", icon: Box, color: "text-purple-400", gradient: "from-purple-500/20 to-violet-500/20" },
    coo: { label: "COO", icon: Settings, color: "text-blue-400", gradient: "from-blue-500/20 to-indigo-500/20" },
    cdo: { label: "CDO", icon: Palette, color: "text-violet-400", gradient: "from-violet-500/20 to-fuchsia-500/20" },
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
    const [stuck, setStuck] = useState(false); // true when polling timed out with no progress
    const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const pollCountRef = useRef(0);
    const POLL_TIMEOUT = 150; // ~5 min at 2s interval — stop if no progress

    // ── Improvement state ────────────────────────────────────────────────
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
    const [improvePlan, setImprovePlan] = useState<ImprovementPlan | null>(null);
    const [improveLoading, setImproveLoading] = useState(false);
    const [improveRoles, setImproveRoles] = useState<string[] | null>(null); // null=all
    const [applyingImprove, setApplyingImprove] = useState(false);
    const [expandedImproveCard, setExpandedImproveCard] = useState<string | null>(null);
    const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

    // Load existing results or start fresh analysis
    const loadOrStart = async () => {
        setStarted(true);
        setError(null);
        try {
            const token = await getAccessToken();
            // First, try to load existing results
            const statusResp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/status`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (statusResp.ok) {
                const data = await statusResp.json();
                if (data.agents && data.agents.length > 0) {
                    // Results exist — populate state
                    setAgents(data.agents);
                    if (data.project_name) setProjectName(data.project_name);
                    if (data.overall_score != null) setOverallScore(data.overall_score);
                    if (data.overall_verdict) setOverallVerdict(data.overall_verdict);

                    const done = data.agents.every((a: AgentResult) => a.status === "complete" || a.status === "error");
                    if (done) {
                        setAllDone(true);
                        return; // Already complete, no need to poll or re-run
                    }

                    // If ALL agents are still pending (none running/complete), the
                    // background job never started — re-trigger the run.
                    const allPending = data.agents.every((a: AgentResult) => a.status === "pending");
                    if (allPending) {
                        console.warn("All agents stuck in pending — re-triggering run");
                        // fall through to POST /run below
                    } else {
                        // At least one agent is running or has results — just poll
                        pollResults();
                        return;
                    }
                }
            }

            // No existing results — start fresh analysis
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/run`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(body.detail || "Failed to start analysis");
            }
            const data = await resp.json();
            setProjectName(data.project_name || "");
            pollResults();
        } catch (e: any) {
            setError(e.message);
            setStarted(false);
        }
    };

    const pollResults = async () => {
        setStuck(false);
        pollCountRef.current = 0;
        const poll = async () => {
            try {
                pollCountRef.current += 1;
                const token = await getAccessToken();
                const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!resp.ok) return;
                const data = await resp.json();

                if (data.agents) {
                    // Merge: update only agents present in the response,
                    // preserve existing data for agents not in the response
                    setAgents(prev => {
                        const incoming = new Map<string, AgentResult>(data.agents.map((a: AgentResult) => [a.role, a]));
                        return prev.map(existing => {
                            const updated = incoming.get(existing.role);
                            if (!updated) return existing;
                            // Normalize: old DB rows may lack newer array fields
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
                    // Recompute overall from all agents (merged state)
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
                    return;
                }

                // Timeout: if all still pending after POLL_TIMEOUT polls, stop and show "stuck"
                const allPending = data.agents?.every((a: AgentResult) => a.status === "pending");
                if (allPending && pollCountRef.current >= POLL_TIMEOUT) {
                    if (pollingRef.current) clearInterval(pollingRef.current);
                    pollingRef.current = null;
                    setStuck(true);
                }
            } catch (e) {
                console.error("Poll error:", e);
            }
        };
        pollingRef.current = setInterval(poll, 2000);
        poll(); // immediate first poll
    };

    const handleRunAgain = async () => {
        setStuck(false);
        setError(null);
        setAllDone(false);
        if (pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
        }
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/csuite/${projectId}/run`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) {
                const body = await resp.json().catch(() => ({}));
                throw new Error(body.detail || "Failed to start analysis");
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
        if (!corrections.trim()) return;
        setRefining(true);
        setAllDone(false);
        setError(null);
        try {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
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
                throw new Error(body.detail || "Failed to refine analysis");
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

    // ── AI Improve handlers ──────────────────────────────────────────────
    const handleImprove = async (roles?: string[]) => {
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
            setImprovePlan(plan);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setImproveLoading(false);
        }
    };

    const handleApplyImprovement = async () => {
        if (!improvePlan?.improvements) return;
        setApplyingImprove(true);
        setError(null);
        try {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
            const roles = Object.keys(improvePlan.improvements);
            // Build combined enhanced context from all improvements
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

            // Reset only affected agents to pending — keep other agents' results intact
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
        };
    }, []);

    // Auto-load on mount (loads existing results or starts fresh)
    useEffect(() => {
        if (!started) loadOrStart();
    }, []);

    const completedCount = agents.filter(a => a.status === "complete" || a.status === "error").length;
    const avgScore = agents.filter(a => a.score != null).reduce((s, a) => s + (a.score || 0), 0) / Math.max(1, agents.filter(a => a.score != null).length);

    const getVerdictColor = (v: string | null) => {
        if (v === "go") return "text-green-400";
        if (v === "no_go") return "text-red-400";
        if (v === "conditional") return "text-amber-400";
        return "text-zinc-500";
    };

    const getStatusIcon = (status: string) => {
        if (status === "complete") return <CheckCircle2 className="w-4 h-4 text-green-400" />;
        if (status === "running") return <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />;
        if (status === "error") return <XCircle className="w-4 h-4 text-red-400" />;
        return <div className="w-4 h-4 rounded-full border-2 border-zinc-600" />;
    };

    return (
        <div className="max-w-6xl mx-auto px-6 py-10">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                <div className="flex items-center gap-3 mb-2">
                    <Crown className="w-6 h-6 text-amber-400" />
                    <h1 className="text-3xl font-bold text-[var(--kf-text)]">C-Suite Analysis</h1>
                </div>
                {projectName && <p className="text-[var(--kf-text-secondary)] text-lg ml-9">{projectName}</p>}
            </motion.div>

            {stuck && (
                <div className="mb-6 flex items-start justify-between gap-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-5 py-4 text-sm text-amber-100">
                    <div>
                        <div className="font-semibold text-amber-300">Analysis stalled before any agents started.</div>
                        <div className="mt-1 text-amber-100/80">Retry the run to restart the background job and resume the C-suite pass.</div>
                    </div>
                    <button
                        onClick={handleRunAgain}
                        className="shrink-0 rounded-lg border border-amber-400/30 px-3 py-1.5 font-medium text-amber-200 transition-colors hover:bg-amber-400/10"
                    >
                        Run Again
                    </button>
                </div>
            )}

            {/* Overall progress bar */}
            <div className="bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl p-6 mb-8">
                <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-[var(--kf-text-secondary)]">{completedCount}/{agents.length} agents completed</span>
                    <div className="flex items-center gap-3">
                        {overallScore != null ? (
                            <span className="text-lg font-bold text-purple-300">{Math.round(overallScore)}/100</span>
                        ) : agents.some(a => a.score != null) ? (
                            <span className="text-lg font-bold text-[var(--kf-text-secondary)]">{Math.round(avgScore)}/100 avg so far</span>
                        ) : null}
                        {allDone && projectId && (
                            <ExportMenu
                                projectId={projectId}
                                target="csuite"
                                label="Download Report"
                                size="sm"
                            />
                        )}
                        {allDone && overallScore != null && overallScore < 85 && (
                            <button
                                onClick={() => handleImprove()}
                                disabled={improveLoading}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 text-amber-400 text-xs font-medium hover:from-amber-500/30 hover:to-orange-500/30 transition-all disabled:opacity-50"
                            >
                                {improveLoading && !improveRoles ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <Sparkles className="w-3.5 h-3.5" />
                                )}
                                {improveLoading && !improveRoles ? "Analyzing..." : "Improve All"}
                            </button>
                        )}
                    </div>
                </div>
                <div className="h-2 bg-[var(--kf-badge-bg)] rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${(completedCount / agents.length) * 100}%` }}
                        transition={{ duration: 0.5 }}
                    />
                </div>
                {overallVerdict && (
                    <p className={`mt-3 text-sm font-medium ${getVerdictColor(overallVerdict)}`}>
                        Final Verdict: {overallVerdict === "go" ? "GO — Proceed to Build" : overallVerdict === "no_go" ? "NO GO — Needs Rework" : "CONDITIONAL — Review Suggestions"}
                    </p>
                )}
            </div>

            {/* Agent cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mb-8">
                {agents.map((agent, i) => {
                    const meta = ROLE_META[agent.role] || { label: agent.role, icon: Info, color: "text-[var(--kf-text-secondary)]", gradient: "from-zinc-500/20 to-zinc-500/20" };
                    const Icon = meta.icon;
                    const expanded = agent.status === "complete";
                    const isClickable = agent.status === "complete";
                    return (
                        <motion.div
                            key={agent.role}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            onClick={() => isClickable && setSelectedAgent(agent.role)}
                            className={`bg-[var(--kf-surface)] border rounded-xl p-5 transition-all ${
                                isClickable ? "cursor-pointer hover:border-purple-500/40 hover:shadow-lg hover:shadow-purple-500/5" : ""
                            } ${agent.status === "running"
                                ? "border-purple-500/40 shadow-lg shadow-purple-500/5"
                                : agent.status === "complete"
                                    ? "border-[var(--kf-border)]"
                                    : "border-[var(--kf-border)]"
                                }`}
                        >
                            {/* Agent header */}
                            <div className="flex items-center gap-3 mb-3">
                                <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${meta.gradient} flex items-center justify-center`}>
                                    <Icon className={`w-5 h-5 ${meta.color}`} />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-bold text-[var(--kf-text)] text-sm">{meta.label}</span>
                                        {getStatusIcon(agent.status)}
                                    </div>
                                    {agent.score != null && (
                                        <span className="text-xs font-bold text-purple-400">{agent.score}/100</span>
                                    )}
                                </div>
                                {agent.verdict && (
                                    <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${agent.verdict === "go"
                                        ? "text-green-400 border-green-500/30 bg-green-500/10"
                                        : agent.verdict === "no_go"
                                            ? "text-red-400 border-red-500/30 bg-red-500/10"
                                            : "text-amber-400 border-amber-500/30 bg-amber-500/10"
                                        }`}>
                                        {agent.verdict === "no_go" ? "NO GO" : agent.verdict.toUpperCase()}
                                    </span>
                                )}
                            </div>

                            {/* Status indicator */}
                            {agent.status === "running" && (
                                <div className="flex items-center gap-2 text-xs text-purple-400 mb-3">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    Analyzing...
                                </div>
                            )}
                            {agent.status === "pending" && (
                                <div className="text-xs text-zinc-600">Waiting...</div>
                            )}

                            {/* Completed content */}
                            {expanded && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="mt-2 space-y-3 text-xs"
                                >
                                    {agent.recommendation && (
                                        <p className="text-[var(--kf-text-secondary)] leading-relaxed">{agent.recommendation}</p>
                                    )}
                                    {agent.strengths.length > 0 && (
                                        <div>
                                            <span className="text-green-400 font-medium">Strengths</span>
                                            <ul className="mt-1 space-y-0.5">
                                                {agent.strengths.slice(0, 3).map((s, j) => (
                                                    <li key={j} className="text-[var(--kf-text-secondary)] flex items-start gap-1.5">
                                                        <span className="text-green-400 mt-0.5">+</span> {s}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {agent.risks.length > 0 && (
                                        <div>
                                            <span className="text-red-400 font-medium">Risks</span>
                                            <ul className="mt-1 space-y-0.5">
                                                {agent.risks.slice(0, 3).map((r, j) => (
                                                    <li key={j} className="text-[var(--kf-text-secondary)] flex items-start gap-1.5">
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
                                            className="mt-2 w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-medium hover:bg-amber-500/20 transition-colors disabled:opacity-50"
                                        >
                                            {improveLoading && improveRoles?.includes(agent.role) ? (
                                                <Loader2 className="w-3 h-3 animate-spin" />
                                            ) : (
                                                <Zap className="w-3 h-3" />
                                            )}
                                            {improveLoading && improveRoles?.includes(agent.role) ? "Analyzing..." : "Improve"}
                                        </button>
                                    )}
                                    <div className="mt-3 pt-2 border-t border-[var(--kf-border)] flex items-center justify-end">
                                        <span className="text-[10px] text-purple-400/70 flex items-center gap-1">
                                            <ArrowRight className="w-2.5 h-2.5" /> Full analysis
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
                    const meta = ROLE_META[agent.role] || { label: agent.role, icon: Info, color: "text-[var(--kf-text-secondary)]", gradient: "from-zinc-500/20 to-zinc-500/20" };
                    const Icon = meta.icon;
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
                                className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-[#0E0E16] border-l border-[var(--kf-border)] shadow-2xl flex flex-col z-50"
                            >
                                {/* Drawer header */}
                                <div className={`flex items-center justify-between px-6 py-5 bg-gradient-to-r ${meta.gradient} border-b border-[var(--kf-border)]/60`}>
                                    <div className="flex items-center gap-3">
                                        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${meta.gradient} border border-[var(--kf-border)] flex items-center justify-center`}>
                                            <Icon className={`w-5 h-5 ${meta.color}`} />
                                        </div>
                                        <div>
                                            <h2 className="text-lg font-bold text-[var(--kf-text)]">{meta.label} Analysis</h2>
                                            {agent.score != null && (
                                                <div className="flex items-center gap-2">
                                                    <span className={`text-sm font-bold ${meta.color}`}>{agent.score}/100</span>
                                                    {agent.verdict && (
                                                        <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                                                            agent.verdict === "go" ? "text-green-400 border-green-500/30 bg-green-500/10"
                                                            : agent.verdict === "no_go" ? "text-red-400 border-red-500/30 bg-red-500/10"
                                                            : "text-amber-400 border-amber-500/30 bg-amber-500/10"
                                                        }`}>{agent.verdict === "no_go" ? "NO GO" : agent.verdict.toUpperCase()}</span>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    <button onClick={() => setSelectedAgent(null)} className="p-2 rounded-lg hover:bg-[var(--kf-hover-bg)] text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] transition-colors">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                {/* Drawer body */}
                                <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
                                    {/* Executive Summary */}
                                    {agent.recommendation && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Executive Summary</h3>
                                            <p className="text-sm text-[var(--kf-text)] leading-relaxed bg-[var(--kf-surface)] rounded-xl p-4 border border-[var(--kf-border)]">{agent.recommendation}</p>
                                        </div>
                                    )}

                                    {/* Deep Analysis */}
                                    {agent.deep_analysis && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Deep Analysis</h3>
                                            <div className="text-sm text-[var(--kf-text-secondary)] leading-relaxed space-y-3">
                                                {agent.deep_analysis.split(/\n\n+/).map((para, i) => (
                                                    <p key={i} className="text-[var(--kf-text-secondary)]">{para}</p>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Strengths + Risks side by side */}
                                    <div className="grid grid-cols-2 gap-4">
                                        {(agent.strengths ?? []).length > 0 && (
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-green-500/70 mb-2">Strengths</h3>
                                                <ul className="space-y-2">
                                                    {(agent.strengths ?? []).map((s, j) => (
                                                        <li key={j} className="text-xs text-[var(--kf-text-secondary)] flex items-start gap-1.5">
                                                            <span className="text-green-400 mt-0.5 shrink-0">+</span>{s}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {(agent.risks ?? []).length > 0 && (
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-red-500/70 mb-2">Risks</h3>
                                                <ul className="space-y-2">
                                                    {(agent.risks ?? []).map((r, j) => (
                                                        <li key={j} className="text-xs text-[var(--kf-text-secondary)] flex items-start gap-1.5">
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
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-purple-400/70 mb-2">Priority Actions</h3>
                                            <ol className="space-y-2">
                                                {(agent.priority_actions ?? []).map((a, j) => (
                                                    <li key={j} className="text-xs text-[var(--kf-text-secondary)] flex items-start gap-2.5 bg-purple-500/5 border border-purple-500/10 rounded-lg px-3 py-2">
                                                        <span className="text-purple-400 font-bold shrink-0">{j + 1}.</span>{a}
                                                    </li>
                                                ))}
                                            </ol>
                                        </div>
                                    )}

                                    {/* Suggestions */}
                                    {(agent.suggestions ?? []).length > 0 && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-amber-500/70 mb-2">Suggestions</h3>
                                            <ul className="space-y-2">
                                                {(agent.suggestions ?? []).map((s, j) => (
                                                    <li key={j} className="text-xs text-[var(--kf-text-secondary)] flex items-start gap-1.5">
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
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-cyan-500/70 mb-2">Key Metrics</h3>
                                                <ul className="space-y-1.5">
                                                    {(agent.key_metrics ?? []).map((m, j) => (
                                                        <li key={j} className="text-xs text-[var(--kf-text-secondary)] flex items-start gap-1.5">
                                                            <span className="text-cyan-400 mt-0.5 shrink-0">◆</span>{m}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                        {agent.timeline && (
                                            <div>
                                                <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Timeline</h3>
                                                <p className="text-xs text-[var(--kf-text-secondary)] leading-relaxed bg-[var(--kf-surface)] rounded-lg p-3 border border-[var(--kf-border)]/40">{agent.timeline}</p>
                                            </div>
                                        )}
                                    </div>

                                    {/* Competitive Note */}
                                    {agent.competitive_note && (
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-widest text-zinc-500 mb-2">Competitive Perspective</h3>
                                            <p className="text-xs text-[var(--kf-text-secondary)] leading-relaxed italic border-l-2 border-[var(--kf-border-muted)] pl-3">{agent.competitive_note}</p>
                                        </div>
                                    )}
                                </div>

                                {/* Drawer footer */}
                                {agent.score != null && agent.score < 85 && allDone && (
                                    <div className="px-6 py-4 border-t border-[var(--kf-border)]/60 bg-[var(--kf-surface)]">
                                        <button
                                            onClick={(e) => { e.stopPropagation(); setSelectedAgent(null); handleImprove([agent.role]); }}
                                            disabled={improveLoading}
                                            className="w-full flex items-center justify-center gap-2 h-10 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm font-medium hover:bg-amber-500/20 transition-colors disabled:opacity-50"
                                        >
                                            <Zap className="w-4 h-4" /> Improve this analysis
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
                        <div className="bg-gradient-to-br from-amber-500/5 to-orange-500/5 border border-amber-500/20 rounded-2xl p-6">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <Sparkles className="w-5 h-5 text-amber-400" />
                                    <h3 className="text-lg font-bold text-[var(--kf-text)]">AI Improvement Plan</h3>
                                </div>
                                <button
                                    onClick={() => { setImprovePlan(null); setImproveRoles(null); }}
                                    className="p-1 rounded-lg hover:bg-[var(--kf-hover-bg)] text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            {improveLoading ? (
                                <div className="flex items-center gap-3 py-8 justify-center">
                                    <Loader2 className="w-5 h-5 text-amber-400 animate-spin" />
                                    <span className="text-sm text-[var(--kf-text-secondary)]">AI is analyzing scores and generating improvements...</span>
                                </div>
                            ) : improvePlan ? (
                                <>
                                    {improvePlan.summary && (
                                        <p className="text-sm text-[var(--kf-text-secondary)] mb-4 leading-relaxed">{improvePlan.summary}</p>
                                    )}

                                    <div className="space-y-3 mb-5">
                                        {Object.entries(improvePlan.improvements).map(([role, detail]) => {
                                            const meta = ROLE_META[role];
                                            const isExpanded = expandedImproveCard === role;
                                            return (
                                                <div key={role} className="bg-[#0E0E16] border border-[var(--kf-border)] rounded-xl overflow-hidden">
                                                    <button
                                                        onClick={() => setExpandedImproveCard(isExpanded ? null : role)}
                                                        className="w-full flex items-center justify-between px-4 py-3 hover:bg-[var(--kf-hover-bg)]/30 transition-colors"
                                                    >
                                                        <div className="flex items-center gap-3">
                                                            <span className={`font-bold text-sm ${meta?.color || "text-[var(--kf-text-secondary)]"}`}>
                                                                {meta?.label || role.toUpperCase()}
                                                            </span>
                                                            <span className="text-xs text-zinc-500">{detail.current_score}/100</span>
                                                            <ArrowRight className="w-3 h-3 text-zinc-600" />
                                                            <span className="text-xs text-green-400 font-medium">Targeting 85+</span>
                                                        </div>
                                                        {isExpanded ? (
                                                            <ChevronUp className="w-4 h-4 text-zinc-500" />
                                                        ) : (
                                                            <ChevronDown className="w-4 h-4 text-zinc-500" />
                                                        )}
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
                                                                            <span className="text-red-400 font-medium">Key Weaknesses</span>
                                                                            <ul className="mt-1 space-y-0.5">
                                                                                {detail.key_weaknesses.map((w, i) => (
                                                                                    <li key={i} className="text-[var(--kf-text-secondary)] flex items-start gap-1.5">
                                                                                        <span className="text-red-400 mt-0.5">!</span> {w}
                                                                                    </li>
                                                                                ))}
                                                                            </ul>
                                                                        </div>
                                                                    )}
                                                                    {detail.recommended_changes.length > 0 && (
                                                                        <div>
                                                                            <span className="text-green-400 font-medium">Recommended Changes</span>
                                                                            <ul className="mt-1 space-y-0.5">
                                                                                {detail.recommended_changes.map((c, i) => (
                                                                                    <li key={i} className="text-[var(--kf-text-secondary)] flex items-start gap-1.5">
                                                                                        <span className="text-green-400 mt-0.5">+</span> {c}
                                                                                    </li>
                                                                                ))}
                                                                            </ul>
                                                                        </div>
                                                                    )}
                                                                    {detail.enhanced_context && (
                                                                        <div>
                                                                            <span className="text-purple-400 font-medium">Enhanced Context</span>
                                                                            <p className="mt-1 text-[var(--kf-text-secondary)] leading-relaxed bg-[var(--kf-surface)] rounded-lg p-3 border border-[var(--kf-border)]">
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
                                            className="h-9 px-4 rounded-lg border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] text-sm hover:bg-[var(--kf-hover-bg)] transition-colors"
                                        >
                                            Dismiss
                                        </button>
                                        <button
                                            onClick={handleApplyImprovement}
                                            disabled={applyingImprove}
                                            className="flex items-center gap-2 h-9 px-5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 text-black text-sm font-bold hover:from-amber-400 hover:to-orange-400 transition-all disabled:opacity-50 shadow-lg shadow-amber-500/20"
                                        >
                                            {applyingImprove ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <RotateCcw className="w-4 h-4" />
                                            )}
                                            {applyingImprove ? "Re-running..." : `Accept & Re-run ${Object.keys(improvePlan.improvements).length} Agent${Object.keys(improvePlan.improvements).length > 1 ? "s" : ""}`}
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
                    <div className="max-w-3xl mx-auto bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-xl p-4">
                        <label className="block text-sm text-[var(--kf-text-secondary)] mb-2">Corrections / context for re-run (optional)</label>
                        <textarea
                            value={corrections}
                            onChange={(e) => setCorrections(e.target.value)}
                            placeholder="Add clarifications, constraints, target users, pricing assumptions, or technical requirements..."
                            className="w-full min-h-24 bg-[#0E0E16] border border-[var(--kf-border-muted)] rounded-lg px-3 py-2 text-sm text-[var(--kf-text)] placeholder:text-[var(--kf-text-faint)] focus:outline-none focus:ring-1 focus:ring-purple-500"
                        />
                        <div className="mt-3 flex justify-end">
                            <button
                                onClick={handleRefine}
                                disabled={!corrections.trim() || refining}
                                className="h-9 px-4 rounded-lg border border-[var(--kf-border-muted)] text-[var(--kf-text)] text-sm hover:bg-[var(--kf-hover-bg)] disabled:opacity-50"
                            >
                                {refining ? "Refining..." : "Re-run with Corrections"}
                            </button>
                        </div>
                    </div>

                    <div className="flex justify-center">
                        <button
                            onClick={() => navigate(`/project/${projectId}`)}
                            className="flex items-center gap-2 h-12 px-8 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20"
                        >
                            Proceed to Project Dashboard
                            <ArrowRight className="w-4 h-4" />
                        </button>
                    </div>
                </motion.div>
            )}

            {error && (
                <div className="mt-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
                    {error}
                </div>
            )}
        </div>
    );
}
