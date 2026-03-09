import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion } from "framer-motion";
import {
    FileText, Palette, Code2, Rocket,
    Crown, BarChart3, Users, Lightbulb, Map, Layers,
    FileCode, Target, Loader2, Sparkles, ChevronDown
} from "lucide-react";

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

const ARTIFACT_META: Record<string, { label: string; icon: any; color: string; description: string }> = {
    executive_brief: { label: "Executive Brief", icon: FileText, color: "text-amber-400", description: "High-level vision and strategy overview" },
    prd: { label: "Product Requirements", icon: Layers, color: "text-blue-400", description: "Detailed feature requirements and specs" },
    tech_spec: { label: "Technical Spec", icon: FileCode, color: "text-cyan-400", description: "Architecture, stack, and technical decisions" },
    market_analysis: { label: "Market Analysis", icon: BarChart3, color: "text-green-400", description: "Market size, competition, positioning" },
    go_to_market: { label: "Go-to-Market Plan", icon: Rocket, color: "text-orange-400", description: "Launch strategy and growth channels" },
    user_personas: { label: "User Personas", icon: Users, color: "text-pink-400", description: "Target user profiles and behavior patterns" },
    competitive_matrix: { label: "Competitive Matrix", icon: Target, color: "text-red-400", description: "Feature comparison with competitors" },
    roadmap: { label: "Product Roadmap", icon: Map, color: "text-purple-400", description: "Phased development timeline" },
    monetization: { label: "Monetization Plan", icon: Crown, color: "text-emerald-400", description: "Revenue model and pricing strategy" },
    design_system: { label: "Design System Foundation", icon: Palette, color: "text-violet-400", description: "Colors, typography, components, and tokens" },
};

export default function ProjectDashboardPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const { getAccessToken } = useAuth();

    const [project, setProject] = useState<ProjectInfo | null>(null);
    const [artifacts, setArtifacts] = useState<ArtifactInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
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
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            </div>
        );
    }

    const completedArtifacts = artifacts.filter(a => a.status === "complete").length;
    const totalArtifacts = Object.keys(ARTIFACT_META).length;
    const allArtifactsComplete = totalArtifacts > 0 && completedArtifacts === totalArtifacts;
    const bootstrapReady = Boolean(bootstrapData?.prompt);
    const canGenerateBootstrap = allArtifactsComplete;
    const canAccessBuildFlow = bootstrapReady;
    const nextStep = !allArtifactsComplete ? "artifacts" : !bootstrapReady ? "bootstrap" : null;
    const lockedActionClass = "opacity-45 saturate-50 cursor-not-allowed pointer-events-none";
    const pulseAnimation = {
        boxShadow: [
            "0 0 0 rgba(168,85,247,0)",
            "0 0 0 1px rgba(168,85,247,0.32), 0 0 24px rgba(168,85,247,0.18)",
            "0 0 0 rgba(168,85,247,0)",
        ],
        scale: [1, 1.01, 1],
    };
    const pulseTransition = { duration: 2.2, repeat: Infinity, ease: "easeInOut" as const };

    return (
        <div className="max-w-6xl mx-auto px-6 py-10">
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-1">{project?.name}</h1>
                        <p className="text-zinc-400 max-w-2xl">{project?.description}</p>
                    </div>
                    <div className="flex items-center gap-3">
                        {canAccessBuildFlow ? (
                            <motion.div
                                className="rounded-xl"
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
                                    to={`/project/${projectId}/design-studio`}
                                    className="flex items-center gap-2 h-10 px-5 rounded-xl border border-purple-500/50 text-purple-300 text-sm font-medium hover:bg-purple-500/10 hover:border-purple-400 transition-colors"
                                >
                                    <motion.div
                                        animate={{ rotate: [0, -14, 14, -8, 8, 0] }}
                                        transition={{ duration: 1.8, repeat: Infinity, repeatDelay: 2.5, ease: "easeInOut" }}
                                    >
                                        <Palette className="w-4 h-4" />
                                    </motion.div>
                                    Design Studio
                                </Link>
                            </motion.div>
                        ) : (
                            <div className={`flex items-center gap-2 h-10 px-5 rounded-xl border border-zinc-800 bg-zinc-900/40 text-zinc-500 text-sm font-medium ${lockedActionClass}`}>
                                <Palette className="w-4 h-4" />
                                Design Studio
                            </div>
                        )}
                        {canAccessBuildFlow ? (
                            <motion.div
                                className="rounded-xl"
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
                                    to={`/project/${projectId}/editor?autobuild=1`}
                                    className="flex items-center gap-2 h-10 px-5 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all"
                                >
                                    <Code2 className="w-4 h-4" />
                                    Open Editor
                                </Link>
                            </motion.div>
                        ) : (
                            <div className={`flex items-center gap-2 h-10 px-5 rounded-xl bg-zinc-800/60 text-zinc-500 text-sm font-medium ${lockedActionClass}`}>
                                <Code2 className="w-4 h-4" />
                                Open Editor
                            </div>
                        )}
                    </div>
                </div>

                {/* Score badge */}
                {project?.overall_score != null && (
                    <div className="flex items-center gap-4 mt-4">
                        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#12121A] border border-zinc-800/50">
                            <Crown className="w-4 h-4 text-amber-400" />
                            <span className="text-sm text-zinc-300">C-Suite Score:</span>
                            <span className="text-lg font-bold text-purple-400">{project.overall_score}/100</span>
                        </div>
                        {project.overall_verdict && (
                            <span className={`text-sm font-bold uppercase ${project.overall_verdict === "go" ? "text-green-400" : project.overall_verdict === "no_go" ? "text-red-400" : "text-amber-400"}`}>
                                {project.overall_verdict === "no_go" ? "NO GO" : project.overall_verdict.toUpperCase()}
                            </span>
                        )}
                        {canAccessBuildFlow ? (
                            <Link
                                to={`/csuite/${projectId}`}
                                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm font-medium hover:bg-amber-500/20 transition-colors"
                            >
                                <Rocket className="w-3.5 h-3.5" />
                                Improve
                            </Link>
                        ) : (
                            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900/40 border border-zinc-800 text-zinc-500 text-sm font-medium ${lockedActionClass}`}>
                                <Rocket className="w-3.5 h-3.5" />
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
                            className="flex items-center gap-3 px-4 py-3 rounded-xl bg-purple-500/8 border border-purple-500/25"
                        >
                            <motion.div
                                animate={{ scale: [1, 1.3, 1], rotate: [0, 12, -12, 0] }}
                                transition={{ duration: 2.2, repeat: Infinity, repeatDelay: 1.5, ease: "easeInOut" }}
                            >
                                <Sparkles className="w-4 h-4 text-purple-400 flex-shrink-0" />
                            </motion.div>
                            <span className="text-sm text-purple-300 font-medium">
                                Your project is ready — click <strong className="text-purple-200">Design Studio</strong> to generate screens or <strong className="text-purple-200">Open Editor</strong> to build with AI.
                            </span>
                            <motion.div
                                animate={{ x: [0, 5, 0] }}
                                transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
                                className="ml-auto text-purple-400 text-sm font-bold flex-shrink-0"
                            >
                                →
                            </motion.div>
                        </motion.div>
                    </motion.div>
                )}
            </motion.div>

            {/* Bootstrap prompt section */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
                <div className={`bg-[#12121A] border border-zinc-800/50 rounded-xl p-5 transition-opacity ${canGenerateBootstrap ? "opacity-100" : "opacity-60"}`}>
                    <div className="flex items-center justify-between gap-3 mb-3">
                        <div>
                            <h2 className="text-lg font-bold text-white">AI Bootstrap Prompt</h2>
                            <p className="text-xs text-zinc-400 mt-1">
                                {bootstrapReady
                                    ? "The AI bootstrap prompt is ready. You can copy it, open Design Studio, or jump into the editor."
                                    : allArtifactsComplete
                                    ? "This prompt is generated automatically as soon as the full artifact set completes."
                                    : "Locked until all project artifacts have been generated."}
                            </p>
                        </div>
                        <div className="flex items-center gap-2">
                            <motion.button
                                onClick={handleGenerateBootstrapPrompt}
                                disabled={bootstrapLoading || !canGenerateBootstrap}
                                title={!canGenerateBootstrap ? "Generate all project artifacts first" : undefined}
                                animate={nextStep === "bootstrap" && !bootstrapLoading ? pulseAnimation : undefined}
                                transition={nextStep === "bootstrap" && !bootstrapLoading ? pulseTransition : undefined}
                                className="h-9 px-4 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {bootstrapLoading ? "Generating..." : bootstrapReady ? "Regenerate AI Bootstrap Prompt" : "Generate AI Bootstrap Prompt"}
                            </motion.button>
                            <button
                                onClick={handleCopyPrompt}
                                disabled={!bootstrapData?.prompt}
                                className="h-9 px-4 rounded-lg border border-zinc-700 text-zinc-300 text-sm font-medium hover:bg-zinc-800 disabled:opacity-50"
                            >
                                {copied ? "Copied" : "Copy Prompt"}
                            </button>
                            {canAccessBuildFlow ? (
                                <Link
                                    to={`/project/${projectId}/editor?autobuild=1`}
                                    className="h-9 px-4 rounded-lg bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 flex items-center"
                                >
                                    Build with Kith
                                </Link>
                            ) : (
                                <div className={`h-9 px-4 rounded-lg bg-zinc-800/60 text-zinc-500 text-sm font-medium flex items-center ${lockedActionClass}`}>
                                    Build with Kith
                                </div>
                            )}
                        </div>
                    </div>

                    {bootstrapData ? (
                        <>
                            <div className="flex items-center gap-4 text-xs text-zinc-400 mb-3">
                                <span>{bootstrapData.word_count} words</span>
                                <span>~{bootstrapData.token_estimate} tokens</span>
                            </div>
                            <div className="max-h-44 overflow-y-auto rounded-lg border border-zinc-800 bg-[#0E0E16] p-3 text-xs text-zinc-300 whitespace-pre-wrap">
                                {bootstrapData.prompt}
                            </div>
                        </>
                    ) : (
                        <div className="rounded-lg border border-zinc-800 bg-[#0E0E16] p-3 text-xs text-zinc-500">
                            No bootstrap prompt generated yet.
                        </div>
                    )}
                </div>
            </motion.div>

            {/* Artifacts section */}
            <div className="mb-6 flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold text-white">Project Artifacts</h2>
                    <p className="text-sm text-zinc-400 mt-1">{completedArtifacts}/{totalArtifacts} generated</p>
                </div>
                {completedArtifacts < totalArtifacts && (
                    <motion.button
                        onClick={handleGenerateArtifacts}
                        disabled={generating}
                        animate={nextStep === "artifacts" && !generating ? pulseAnimation : undefined}
                        transition={nextStep === "artifacts" && !generating ? pulseTransition : undefined}
                        className="flex items-center gap-2 h-10 px-5 rounded-xl bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
                    >
                        {generating ? (
                            <>
                                <Loader2 className="w-4 h-4 animate-spin" />
                                Generating...
                            </>
                        ) : (
                            <>
                                <Lightbulb className="w-4 h-4" />
                                Generate All Artifacts
                            </>
                        )}
                    </motion.button>
                )}
            </div>

            {/* Artifact grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(ARTIFACT_META).map(([type, meta], i) => {
                    const artifact = artifacts.find(a => a.type === type);
                    const isComplete = artifact?.status === "complete";
                    const isGenerating = artifact?.status === "generating";
                    const isPending = !artifact || artifact.status === "pending";
                    const Icon = meta.icon;
                    const isExpanded = expandedArtifact === type;
                    const preview = isComplete && artifact?.content
                        ? artifact.content.slice(0, 120).replace(/\n/g, " ").trim() + (artifact.content.length > 120 ? "..." : "")
                        : null;

                    return (
                        <motion.div
                            key={type}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.04 }}
                            className={`bg-[#12121A] border rounded-xl overflow-hidden transition-all ${
                                isComplete && allArtifactsComplete
                                    ? "border-zinc-700/50 hover:border-purple-500/30 cursor-pointer"
                                    : isGenerating
                                        ? "border-purple-500/30"
                                        : "border-zinc-800/30"
                            }`}
                            onClick={() => isComplete && allArtifactsComplete && setExpandedArtifact(isExpanded ? null : type)}
                        >
                            <div className="p-5">
                                <div className="flex items-center gap-3 mb-1">
                                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${isComplete ? "bg-zinc-800/80" : "bg-zinc-800/40"}`}>
                                        <Icon className={`w-4.5 h-4.5 ${isComplete ? meta.color : "text-zinc-600"}`} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className={`text-sm font-bold ${isComplete ? "text-white" : "text-zinc-500"}`}>{meta.label}</h3>
                                        <p className="text-xs text-zinc-500">{meta.description}</p>
                                    </div>
                                    {isComplete && (
                                        <ChevronDown className={`w-4 h-4 text-zinc-500 transition-transform flex-shrink-0 ${isExpanded ? "rotate-180" : ""}`} />
                                    )}
                                    {isGenerating && <Loader2 className="w-4 h-4 text-purple-400 animate-spin flex-shrink-0" />}
                                </div>

                                {/* Content preview for completed artifacts */}
                                {isComplete && preview && !isExpanded && (
                                    <p className="mt-2 text-[11px] text-zinc-400 leading-relaxed line-clamp-2 ml-12">
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
                                        className="mt-2 ml-12 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[11px] font-medium hover:bg-purple-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                    >
                                        <Sparkles className="w-3 h-3" />
                                        Generate
                                    </button>
                                )}
                            </div>

                            {/* Expanded content */}
                            {isExpanded && artifact?.content && (
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: "auto", opacity: 1 }}
                                    className="border-t border-zinc-800/50 px-5 py-4 max-h-96 overflow-y-auto"
                                >
                                    <div className="prose prose-sm prose-invert max-w-none text-zinc-300 text-xs leading-relaxed whitespace-pre-wrap">
                                        {artifact.content}
                                    </div>
                                </motion.div>
                            )}
                        </motion.div>
                    );
                })}
            </div>

            {error && (
                <div className="mt-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm text-center">
                    {error}
                </div>
            )}
        </div>
    );
}
