import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils/cn";
import { pageTransition, staggerContainer, cardEntrance } from "../../lib/utils/motion";
import { ExportMenu } from "../../components/system/ExportMenu";

// ── Types ────────────────────────────────────────────────────────────────────

interface ArtifactInfo {
    type: string;
    title: string;
    status: "pending" | "generating" | "complete";
    content?: string;
    updated_at?: string;
}

interface ProjectInfo {
    id: string;
    name: string;
    description: string;
    status: string;
    overall_score: number | null;
    overall_verdict: string | null;
    idea_source: string | null;
    created_at: string;
}

interface BootstrapPromptData {
    prompt: string;
    word_count: number;
    token_estimate: number;
}

const ARTIFACT_META: Record<string, { label: string; icon: string; description: string }> = {
    executive_brief:   { label: "Executive Brief",           icon: "article",         description: "High-level vision and strategy overview" },
    prd:               { label: "Product Requirements",      icon: "layers",          description: "Detailed feature requirements and specs" },
    tech_spec:         { label: "Technical Spec",            icon: "code",            description: "Architecture, stack, and technical decisions" },
    market_analysis:   { label: "Market Analysis",           icon: "bar_chart",       description: "Market size, competition, positioning" },
    go_to_market:      { label: "Go-to-Market Plan",         icon: "rocket_launch",   description: "Launch strategy and growth channels" },
    user_personas:     { label: "User Personas",             icon: "group",           description: "Target user profiles and behavior patterns" },
    competitive_matrix:{ label: "Competitive Matrix",        icon: "target",          description: "Feature comparison with competitors" },
    roadmap:           { label: "Product Roadmap",           icon: "map",             description: "Phased development timeline" },
    monetization:      { label: "Monetization Plan",         icon: "payments",        description: "Revenue model and pricing strategy" },
    design_system:     { label: "Design System Foundation",  icon: "palette",         description: "Colors, typography, components, and tokens" },
};

export default function ProjectDashboardPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const { getAccessToken } = useAuth();

    const [project, setProject] = useState<ProjectInfo | null>(null);
    const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [regenerating, setRegenerating] = useState(false);
    const [bootstrapData, setBootstrapData] = useState<BootstrapPromptData | null>(null);
    const [bootstrapLoading, setBootstrapLoading] = useState(false);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedArtifact, setExpandedArtifact] = useState<string | null>(null);

    const fetchBootstrapPrompt = async (token: string) => {
        try {
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/bootstrap-prompt`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) return;
            const data = await resp.json();
            if (data?.prompt) setBootstrapData(data);
        } catch {
            // Ignore missing/unavailable saved prompt on initial load
        }
    };

    const fetchProject = async () => {
        try {
            const token = await getAccessToken();
            const [projResp, artsResp] = await Promise.all([
                fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}`, {
                    headers: { Authorization: `Bearer ${token}` },
                }),
                fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts`, {
                    headers: { Authorization: `Bearer ${token}` },
                }),
            ]);
            if (!projResp.ok) throw new Error("Failed to load project");
            const projData = await projResp.json();
            setProject(projData);

            if (artsResp.ok) {
                const artsData = await artsResp.json();
                setArtifacts(artsData.artifacts || []);
            }

            if (token) {
                await fetchBootstrapPrompt(token);
            }
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProject();
    }, [projectId]);

    const handleGenerateArtifacts = async () => {
        setGenerating(true);
        setError(null);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts/generate`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) throw new Error("Failed to start generation");
            // Poll for updates
            const poll = setInterval(async () => {
                const artsResp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (artsResp.ok) {
                    const artsData = await artsResp.json();
                    setArtifacts(artsData.artifacts || []);
                    // Stop only when nothing is still pending or actively generating
                    const stillRunning = artsData.artifacts?.some(
                        (a: ArtifactInfo) => a.status === "pending" || a.status === "generating"
                    );
                    const hasComplete = artsData.artifacts?.some((a: ArtifactInfo) => a.status === "complete");
                    if (!stillRunning && hasComplete) {
                        clearInterval(poll);
                        setGenerating(false);
                        // Auto-build bootstrap prompt via POST (idempotent) so it's ready immediately
                        try {
                            const bsResp = await fetch(
                                `${getApiBaseUrl()}/api/v1/projects/${projectId}/bootstrap-prompt`,
                                { method: "POST", headers: { Authorization: `Bearer ${token}` } }
                            );
                            if (bsResp.ok) {
                                const bsData = await bsResp.json();
                                if (bsData?.prompt) setBootstrapData(bsData);
                            }
                        } catch {
                            // Non-fatal; user can still click Generate manually
                        }
                    }
                }
            }, 3000);
        } catch (e: any) {
            setError(e.message);
            setGenerating(false);
        }
    };

    const handleRegenerateAllArtifacts = async () => {
        setRegenerating(true);
        setError(null);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts/regenerate-all`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) throw new Error("Failed to start regeneration");
            // Poll for updates
            const poll = setInterval(async () => {
                const artsResp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (artsResp.ok) {
                    const artsData = await artsResp.json();
                    setArtifacts(artsData.artifacts || []);
                    // Stop when all artifacts are complete
                    const stillRunning = artsData.artifacts?.some(
                        (a: ArtifactInfo) => a.status === "pending" || a.status === "generating"
                    );
                    const hasComplete = artsData.artifacts?.some((a: ArtifactInfo) => a.status === "complete");
                    if (!stillRunning && hasComplete) {
                        clearInterval(poll);
                        setRegenerating(false);
                        // Auto-build bootstrap prompt via POST (idempotent) so it's ready immediately
                        try {
                            const bsResp = await fetch(
                                `${getApiBaseUrl()}/api/v1/projects/${projectId}/bootstrap-prompt`,
                                { method: "POST", headers: { Authorization: `Bearer ${token}` } }
                            );
                            if (bsResp.ok) {
                                const bsData = await bsResp.json();
                                if (bsData?.prompt) setBootstrapData(bsData);
                            }
                        } catch {
                            // Non-fatal; user can still click Generate manually
                        }
                    }
                }
            }, 3000);
        } catch (e: any) {
            setError(e.message);
            setRegenerating(false);
        }
    };

    const handleGenerateBootstrapPrompt = async () => {
        setBootstrapLoading(true);
        setError(null);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/bootstrap-prompt`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok) {
                throw new Error(data?.detail || "Failed to generate bootstrap prompt");
            }
            setBootstrapData(data);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setBootstrapLoading(false);
        }
    };

    const handleCopyPrompt = async () => {
        if (!bootstrapData?.prompt) return;
        await navigator.clipboard.writeText(bootstrapData.prompt);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    const completedArtifacts = artifacts.filter(a => a.status === "complete" || a.status === "generating").length;
    const totalArtifacts = Object.keys(ARTIFACT_META).length;
    const allArtifactsComplete = totalArtifacts > 0 && completedArtifacts >= totalArtifacts;
    const bootstrapReady = Boolean(bootstrapData?.prompt);
    const canGenerateBootstrap = allArtifactsComplete;
    const canAccessBuildFlow = bootstrapReady;
    const nextStep = !allArtifactsComplete ? "artifacts" : !bootstrapReady ? "bootstrap" : null;
    const lockedActionClass = "opacity-45 saturate-50 cursor-not-allowed pointer-events-none";

    const pulseAnimation = {
        boxShadow: [
            "0 0 0 rgba(var(--color-primary-rgb, 168,85,247),0)",
            "0 0 0 1px rgba(var(--color-primary-rgb, 168,85,247),0.32), 0 0 24px rgba(var(--color-primary-rgb, 168,85,247),0.18)",
            "0 0 0 rgba(var(--color-primary-rgb, 168,85,247),0)",
        ],
        scale: [1, 1.01, 1],
    };
    const pulseTransition = { duration: 2.2, repeat: Infinity, ease: "easeInOut" as const };

    return (
        <motion.div
            {...pageTransition}
            className="max-w-6xl mx-auto px-6 py-10"
        >
            {/* Page Header */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
                <div className="flex items-start justify-between gap-6">
                    <div className="min-w-0">
                        <p className="text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-2">
                            Project
                        </p>
                        <h1
                            className="text-4xl sm:text-5xl md:text-7xl font-black uppercase tracking-tighter leading-none text-on-surface truncate"
                            style={{ letterSpacing: "-0.05em" }}
                        >
                            {project?.name}
                        </h1>
                        <p className="text-tertiary text-sm max-w-2xl leading-relaxed mt-3">
                            {project?.description}
                        </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0 pt-1">
                        {canAccessBuildFlow ? (
                            <motion.div
                                className="rounded-full"
                                animate={{
                                    boxShadow: [
                                        "0 0 0px 0px rgba(168,85,247,0)",
                                        "0 0 0px 3px rgba(168,85,247,0.4), 0 0 22px rgba(168,85,247,0.25)",
                                        "0 0 0px 0px rgba(168,85,247,0)",
                                    ],
                                }}
                                transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.4 }}
                            >
                                <Link
                                    to={`/app/projects/${projectId}/design`}
                                    className={cn(
                                        "flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant",
                                        "text-on-surface font-black uppercase tracking-widest text-[11px]",
                                        "hover:bg-surface-container transition-colors"
                                    )}
                                >
                                    <motion.span
                                        className="material-symbols-outlined text-[18px] text-secondary"
                                        animate={{ rotate: [0, -14, 14, -8, 8, 0] }}
                                        transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 2.5, ease: "easeInOut" }}
                                    >
                                        palette
                                    </motion.span>
                                    Design Studio
                                </Link>
                            </motion.div>
                        ) : (
                            <div className={cn(
                                "flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant",
                                "text-on-surface font-black uppercase tracking-widest text-[11px]",
                                lockedActionClass
                            )}>
                                <span className="material-symbols-outlined text-[18px] text-secondary">palette</span>
                                Design Studio
                            </div>
                        )}
                        {canAccessBuildFlow ? (
                            <motion.div
                                className="rounded-full"
                                animate={{
                                    boxShadow: [
                                        "0 4px 20px rgba(168,85,247,0.18)",
                                        "0 4px 32px rgba(168,85,247,0.65), 0 0 56px rgba(168,85,247,0.22)",
                                        "0 4px 20px rgba(168,85,247,0.18)",
                                    ],
                                    scale: [1, 1.025, 1],
                                }}
                                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                            >
                                <Link
                                    to={`/app/projects/${projectId}/build?autobuild=1`}
                                    className={cn(
                                        "flex items-center gap-2 h-10 px-6 rounded-full",
                                        "bg-primary-container text-on-primary-container",
                                        "font-black uppercase tracking-widest text-[11px]",
                                        "hover:opacity-90 transition-opacity"
                                    )}
                                >
                                    <span className="material-symbols-outlined text-[18px]">code</span>
                                    Open Editor
                                </Link>
                            </motion.div>
                        ) : (
                            <div className={cn(
                                "flex items-center gap-2 h-10 px-6 rounded-full border border-outline-variant",
                                "text-on-surface font-black uppercase tracking-widest text-[11px]",
                                lockedActionClass
                            )}>
                                <span className="material-symbols-outlined text-[18px] text-secondary">code</span>
                                Open Editor
                            </div>
                        )}
                    </div>
                </div>

                {/* Score badge */}
                {project?.overall_score != null && (
                    <div className="flex items-center gap-4 mt-5">
                        <div className="flex items-center gap-2 px-4 py-2 rounded-[var(--radius-module)] steel-gradient ghost-border">
                            <span className="material-symbols-outlined text-[18px] text-secondary">workspace_premium</span>
                            <span className="text-[10px] font-black uppercase tracking-widest text-secondary">C-Suite Score</span>
                            <span className="text-lg font-black text-on-surface" style={{ letterSpacing: "-0.05em" }}>
                                {project.overall_score}/100
                            </span>
                        </div>
                        {project.overall_verdict && (
                            <span className={cn(
                                "text-[10px] font-black uppercase tracking-widest",
                                project.overall_verdict === "go" ? "text-[#34d399]"
                                : project.overall_verdict === "no_go" ? "text-[#f87171]"
                                : "text-[#fbbf24]"
                            )}>
                                {project.overall_verdict === "no_go" ? "NO GO" : project.overall_verdict.toUpperCase()}
                            </span>
                        )}
                        {canAccessBuildFlow ? (
                            <Link
                                to={`/app/projects/${projectId}/executive`}
                                className={cn(
                                    "flex items-center gap-1.5 h-8 px-4 rounded-full border border-outline-variant",
                                    "text-[10px] font-black uppercase tracking-widest text-on-surface",
                                    "hover:bg-surface-container transition-colors"
                                )}
                            >
                                <span className="material-symbols-outlined text-[14px] text-secondary">rocket_launch</span>
                                Improve
                            </Link>
                        ) : (
                            <div className={cn(
                                "flex items-center gap-1.5 h-8 px-4 rounded-full border border-outline-variant",
                                "text-[10px] font-black uppercase tracking-widest text-on-surface",
                                lockedActionClass
                            )}>
                                <span className="material-symbols-outlined text-[14px] text-secondary">rocket_launch</span>
                                Improve
                            </div>
                        )}
                    </div>
                )}

                {/* "Ready to design" nudge banner — slides in when bootstrap is ready */}
                {bootstrapReady && (
                    <motion.div
                        initial={{ opacity: 0, y: -8, height: 0 }}
                        animate={{ opacity: 1, y: 0, height: "auto" }}
                        transition={{ duration: 0.4, ease: "easeOut", delay: 0.2 }}
                        className="mt-4 overflow-hidden"
                    >
                        <motion.div
                            animate={{
                                boxShadow: [
                                    "0 0 0px rgba(168,85,247,0)",
                                    "0 0 18px rgba(168,85,247,0.3)",
                                    "0 0 0px rgba(168,85,247,0)",
                                ],
                            }}
                            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                            className="flex items-center gap-3 px-4 py-3 rounded-[var(--radius-module)] border border-outline-variant bg-surface-container"
                        >
                            <motion.span
                                className="material-symbols-outlined text-[20px] text-secondary shrink-0"
                                animate={{ scale: [1, 1.3, 1], rotate: [0, 12, -12, 0] }}
                                transition={{ duration: 2.2, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
                            >
                                auto_awesome
                            </motion.span>
                            <span className="text-sm text-on-surface leading-snug">
                                Your project is ready — click{" "}
                                <strong className="font-black">Design Studio</strong>{" "}
                                to generate screens or{" "}
                                <strong className="font-black">Open Editor</strong>{" "}
                                to build with AI.
                            </span>
                            <motion.span
                                animate={{ x: [0, 5, 0] }}
                                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
                                className="ml-auto text-[10px] font-black uppercase tracking-widest text-secondary shrink-0"
                            >
                                →
                            </motion.span>
                        </motion.div>
                    </motion.div>
                )}
            </motion.div>

            {/* Bootstrap prompt section */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                <div className={cn(
                    "steel-gradient ghost-border rounded-[var(--radius-module)] p-6 transition-opacity",
                    canGenerateBootstrap ? "opacity-100" : "opacity-60"
                )}>
                    <div className="flex items-start justify-between gap-4 mb-4">
                        <div>
                            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-1">
                                Bootstrap
                            </p>
                            <h2
                                className="font-black uppercase text-on-surface text-lg leading-none"
                                style={{ letterSpacing: "-0.05em" }}
                            >
                                AI Bootstrap Prompt
                            </h2>
                            <p className="text-tertiary text-xs mt-2 leading-relaxed">
                                {bootstrapReady
                                    ? "The AI bootstrap prompt is ready. You can copy it, open Design Studio, or jump into the editor."
                                    : allArtifactsComplete
                                    ? "This prompt is generated automatically as soon as the full artifact set completes."
                                    : "Locked until all project artifacts have been generated."}
                            </p>
                        </div>
                        <div className="flex items-center gap-2 flex-wrap justify-end shrink-0">
                            <motion.button
                                onClick={handleGenerateBootstrapPrompt}
                                disabled={bootstrapLoading || !canGenerateBootstrap}
                                title={!canGenerateBootstrap ? "Generate all project artifacts first" : undefined}
                                animate={nextStep === "bootstrap" && !bootstrapLoading ? pulseAnimation : undefined}
                                transition={nextStep === "bootstrap" && !bootstrapLoading ? pulseTransition : undefined}
                                className={cn(
                                    "flex items-center gap-1.5 h-9 px-4 rounded-full",
                                    "bg-primary-container text-on-primary-container",
                                    "font-black uppercase tracking-widest text-[10px]",
                                    "hover:opacity-90 transition-opacity",
                                    "disabled:opacity-50 disabled:cursor-not-allowed"
                                )}
                            >
                                {bootstrapLoading
                                    ? <><span className="material-symbols-outlined text-[14px] animate-spin">progress_activity</span> Generating…</>
                                    : bootstrapReady
                                    ? <><span className="material-symbols-outlined text-[14px]">refresh</span> Regenerate</>
                                    : <><span className="material-symbols-outlined text-[14px]">auto_awesome</span> Generate</>
                                }
                            </motion.button>
                            <button
                                onClick={handleCopyPrompt}
                                disabled={!bootstrapData?.prompt}
                                className={cn(
                                    "flex items-center gap-1.5 h-9 px-4 rounded-full border border-outline-variant",
                                    "text-on-surface font-black uppercase tracking-widest text-[10px]",
                                    "hover:bg-surface-container transition-colors",
                                    "disabled:opacity-50 disabled:cursor-not-allowed"
                                )}
                            >
                                <span className="material-symbols-outlined text-[14px] text-secondary">
                                    {copied ? "check" : "content_copy"}
                                </span>
                                {copied ? "Copied" : "Copy Prompt"}
                            </button>
                            {canAccessBuildFlow ? (
                                <Link
                                    to={`/app/projects/${projectId}/build?autobuild=1`}
                                    className={cn(
                                        "flex items-center gap-1.5 h-9 px-4 rounded-full",
                                        "bg-primary-container text-on-primary-container",
                                        "font-black uppercase tracking-widest text-[10px]",
                                        "hover:opacity-90 transition-opacity"
                                    )}
                                >
                                    Build with Kith
                                </Link>
                            ) : (
                                <div className={cn(
                                    "flex items-center gap-1.5 h-9 px-4 rounded-full border border-outline-variant",
                                    "text-on-surface font-black uppercase tracking-widest text-[10px]",
                                    lockedActionClass
                                )}>
                                    Build with Kith
                                </div>
                            )}
                        </div>
                    </div>

                    {bootstrapData ? (
                        <>
                            <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-secondary mb-3">
                                <span>{bootstrapData.word_count} words</span>
                                <span>~{bootstrapData.token_estimate} tokens</span>
                            </div>
                            <div className="max-h-44 overflow-y-auto rounded-[var(--radius-module)] p-3 text-xs whitespace-pre-wrap bg-background border border-outline-variant text-on-surface leading-relaxed">
                                {bootstrapData.prompt}
                            </div>
                        </>
                    ) : (
                        <div className="rounded-[var(--radius-module)] p-3 text-xs bg-background border border-outline-variant text-tertiary">
                            No bootstrap prompt generated yet.
                        </div>
                    )}
                </div>
            </motion.div>

            {/* Artifacts section header */}
            <div className="mb-6 flex items-center justify-between gap-4">
                <div>
                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-1">
                        Deliverables
                    </p>
                    <h2
                        className="font-black uppercase text-on-surface text-xl leading-none"
                        style={{ letterSpacing: "-0.05em" }}
                    >
                        Project Artifacts
                    </h2>
                    <p className="text-tertiary text-sm mt-1">
                        {artifacts.length === 0 ? "No artifacts yet" : `${completedArtifacts}/${totalArtifacts} generated`}
                    </p>
                </div>
                <div className="flex items-center gap-2 flex-wrap justify-end">
                    {(completedArtifacts < totalArtifacts || artifacts.length === 0) && (
                        <motion.button
                            onClick={handleGenerateArtifacts}
                            disabled={generating}
                            animate={nextStep === "artifacts" && !generating ? pulseAnimation : undefined}
                            transition={nextStep === "artifacts" && !generating ? pulseTransition : undefined}
                            className={cn(
                                "flex items-center gap-2 h-10 px-5 rounded-full",
                                "bg-primary-container text-on-primary-container",
                                "font-black uppercase tracking-widest text-[11px]",
                                "hover:opacity-90 transition-opacity",
                                "disabled:opacity-50 disabled:cursor-not-allowed"
                            )}
                        >
                            {generating ? (
                                <>
                                    <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                                    Generating…
                                </>
                            ) : (
                                <>
                                    <span className="material-symbols-outlined text-[16px]">auto_fix_high</span>
                                    Generate All Artifacts
                                </>
                            )}
                        </motion.button>
                    )}
                    {completedArtifacts > 0 && (
                        <button
                            onClick={handleRegenerateAllArtifacts}
                            disabled={regenerating || generating}
                            className={cn(
                                "flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant",
                                "text-on-surface font-black uppercase tracking-widest text-[11px]",
                                "hover:bg-surface-container transition-colors",
                                "disabled:opacity-50 disabled:cursor-not-allowed"
                            )}
                        >
                            <span className={cn("material-symbols-outlined text-[16px] text-secondary", regenerating ? "animate-spin" : "")}>
                                refresh
                            </span>
                            Regenerate All
                        </button>
                    )}
                    {allArtifactsComplete && projectId && (
                        <ExportMenu
                            projectId={projectId}
                            target="artifacts"
                            label="Download All"
                        />
                    )}
                </div>
            </div>

            {/* Artifact grid */}
            <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
            >
                {Object.entries(ARTIFACT_META).map(([type, meta]) => {
                    const artifact = artifacts.find(a => a.type === type);
                    const isComplete = artifact?.status === "complete";
                    const isGenerating = artifact?.status === "generating";
                    const isPending = !artifact || artifact.status === "pending";
                    const isExpanded = expandedArtifact === type;
                    const preview = isComplete && artifact?.content
                        ? artifact.content.slice(0, 120).replace(/\n/g, " ").trim() + (artifact.content.length > 120 ? "..." : "")
                        : null;

                    return (
                        <motion.div
                            key={type}
                            variants={cardEntrance}
                            className={cn(
                                "steel-gradient ghost-border rounded-[var(--radius-module)] overflow-hidden transition-all",
                                isComplete && "hover:border-outline cursor-pointer",
                                isGenerating && "border-outline"
                            )}
                            onClick={() => {
                                if (isComplete) {
                                    setExpandedArtifact(isExpanded ? null : type);
                                }
                            }}
                        >
                            <div className="p-5">
                                <div className="flex items-start gap-3 mb-2">
                                    <div className={cn(
                                        "w-9 h-9 rounded-full flex items-center justify-center shrink-0",
                                        isComplete ? "bg-primary-container" : "bg-surface-container"
                                    )}>
                                        <span className={cn(
                                            "material-symbols-outlined text-[18px]",
                                            isComplete ? "text-on-primary-container" : "text-tertiary"
                                        )}>
                                            {meta.icon}
                                        </span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className={cn(
                                            "text-[11px] font-black uppercase tracking-tight mb-0.5",
                                            isComplete ? "text-on-surface" : "text-tertiary"
                                        )}>
                                            {meta.label}
                                        </h3>
                                        <p className="text-tertiary text-xs leading-relaxed">
                                            {meta.description}
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-1 shrink-0">
                                        {isComplete && (
                                            <span className={cn(
                                                "material-symbols-outlined text-[18px] text-tertiary transition-transform",
                                                isExpanded ? "rotate-180" : ""
                                            )}>
                                                expand_more
                                            </span>
                                        )}
                                        {isComplete && projectId && (
                                            <span onClick={(e) => e.stopPropagation()}>
                                                <ExportMenu
                                                    projectId={projectId}
                                                    target={`artifact/${type}`}
                                                    size="sm"
                                                    label=""
                                                />
                                            </span>
                                        )}
                                        {isGenerating && (
                                            <span className="material-symbols-outlined text-[18px] text-secondary animate-spin">
                                                progress_activity
                                            </span>
                                        )}
                                    </div>
                                </div>

                                {/* Content preview for completed artifacts */}
                                {isComplete && preview && !isExpanded && (
                                    <p className="mt-2 text-[11px] leading-relaxed line-clamp-2 pl-12 text-tertiary">
                                        {preview}
                                    </p>
                                )}

                                {/* Generate button for pending artifacts */}
                                {isPending && !isGenerating && (
                                    <button
                                        disabled={!allArtifactsComplete}
                                        title={!allArtifactsComplete ? "Use Generate All Artifacts to unlock the next step" : undefined}
                                        onClick={async (e) => {
                                            e.stopPropagation();
                                            if (!allArtifactsComplete) return;
                                            try {
                                                const token = await getAccessToken();
                                                await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts/generate-single/${type}`, {
                                                    method: "POST",
                                                    headers: { Authorization: `Bearer ${token}` },
                                                });
                                                // Optimistically set this artifact to generating
                                                setArtifacts(prev => {
                                                    const exists = prev.some(a => a.type === type);
                                                    if (exists) return prev.map(a => a.type === type ? { ...a, status: "generating" as const } : a);
                                                    return [...prev, { type, title: meta.label, status: "generating" as const }];
                                                });
                                                // Poll for completion
                                                const pollSingle = setInterval(async () => {
                                                    try {
                                                        const r = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/artifacts`, {
                                                            headers: { Authorization: `Bearer ${token}` },
                                                        });
                                                        const d = await r.json();
                                                        setArtifacts(d.artifacts || []);
                                                        const a = d.artifacts?.find((a: ArtifactInfo) => a.type === type);
                                                        if (a?.status === "complete" || a?.status === "pending") clearInterval(pollSingle);
                                                    } catch { /* ignore */ }
                                                }, 2000);
                                            } catch { /* ignore */ }
                                        }}
                                        className={cn(
                                            "mt-3 ml-12 flex items-center gap-1.5 h-7 px-3 rounded-full",
                                            "border border-outline-variant text-on-surface",
                                            "text-[10px] font-black uppercase tracking-widest",
                                            "hover:bg-surface-container transition-colors",
                                            "disabled:opacity-40 disabled:cursor-not-allowed"
                                        )}
                                    >
                                        <span className="material-symbols-outlined text-[12px] text-secondary">auto_awesome</span>
                                        Generate
                                    </button>
                                )}
                            </div>

                            {/* Expanded content */}
                            {isExpanded && artifact?.content && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    className="px-5 py-4 max-h-96 overflow-y-auto border-t border-outline-variant"
                                >
                                    <div className="text-xs leading-relaxed whitespace-pre-wrap text-on-surface">
                                        {artifact.content}
                                    </div>
                                </motion.div>
                            )}
                        </motion.div>
                    );
                })}
            </motion.div>

            {/* Error state */}
            {error && (
                <div className="mt-6 px-4 py-3 rounded-[var(--radius-module)] border border-error/20 bg-error/10 text-[#f87171] text-sm text-center font-black uppercase tracking-widest">
                    {error}
                </div>
            )}
        </motion.div>
    );
}
