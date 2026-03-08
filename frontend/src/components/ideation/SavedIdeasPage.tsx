import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
    Bookmark,
    Sparkles,
    Trash2,
    Lock,
    Users,
    ChevronDown,
    ChevronUp,
    ArrowLeft,
    Target,
    Lightbulb,
    TrendingUp,
    Zap,
    AlertCircle,
} from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";

interface SavedIdeaEntry {
    id: string;
    name: string;
    content: Record<string, any>;
    score: number | null;
    source: string;
    is_claimed: boolean;
    claimed_by_other: boolean;
    created_at: string;
}

function ScoreBadge({ score }: { score: number }) {
    const color =
        score >= 80 ? "text-emerald-300 bg-emerald-500/10 border-emerald-500/20" :
        score >= 60 ? "text-amber-300 bg-amber-500/10 border-amber-500/20" :
                      "text-zinc-300 bg-zinc-500/10 border-zinc-500/20";
    return (
        <span className={`inline-flex items-center text-xs font-bold px-2 py-0.5 rounded-full border ${color}`}>
            {score}/100
        </span>
    );
}

function SourceBadge({ source }: { source: string }) {
    const map: Record<string, { label: string; cls: string }> = {
        questionnaire: { label: "Questionnaire", cls: "text-purple-300 bg-purple-500/10 border-purple-500/20" },
        user_prompt:   { label: "My Idea",       cls: "text-amber-300 bg-amber-500/10 border-amber-500/20" },
        global:        { label: "Discovered",    cls: "text-cyan-300 bg-cyan-500/10 border-cyan-500/20" },
    };
    const { label, cls } = map[source] ?? { label: source, cls: "text-zinc-400 bg-zinc-800 border-zinc-700" };
    return (
        <span className={`inline-flex items-center text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full border ${cls}`}>
            {label}
        </span>
    );
}

function IdeaDetail({ label, icon: Icon, value }: { label: string; icon: any; value?: string }) {
    if (!value) return null;
    return (
        <div>
            <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 mb-1">
                <Icon className="w-3.5 h-3.5" />
                {label}
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">{value}</p>
        </div>
    );
}

function IdeaCard({
    idea,
    onBuild,
    onDelete,
    buildingId,
    deletingId,
}: {
    idea: SavedIdeaEntry;
    onBuild: (idea: SavedIdeaEntry) => void;
    onDelete: (id: string) => void;
    buildingId: string | null;
    deletingId: string | null;
}) {
    const [expanded, setExpanded] = useState(false);
    const c = idea.content || {};
    const savedDate = idea.created_at
        ? new Date(idea.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
        : "";

    const features: string[] = Array.isArray(c.key_features) ? c.key_features : [];

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8, scale: 0.97 }}
            className="bg-[#12121A] border border-zinc-800/50 rounded-2xl overflow-hidden"
        >
            {/* Header row */}
            <div className="p-5 flex items-start gap-4">
                <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                        <h3 className="text-base font-bold text-white truncate">{idea.name}</h3>
                        {idea.is_claimed && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-full">
                                <Lock className="w-3 h-3" /> Building
                            </span>
                        )}
                        {idea.claimed_by_other && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-orange-300 bg-orange-500/10 border border-orange-500/20 px-2 py-0.5 rounded-full">
                                <Lock className="w-3 h-3" /> Taken
                            </span>
                        )}
                        {idea.score != null && <ScoreBadge score={idea.score} />}
                        <SourceBadge source={idea.source} />
                    </div>
                    <p className="text-sm text-zinc-400 line-clamp-2 leading-relaxed">
                        {c.description || c.summary || "No description available."}
                    </p>
                    {savedDate && (
                        <p className="text-xs text-zinc-600 mt-1.5">Saved {savedDate}</p>
                    )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0 ml-2">
                    {!idea.is_claimed && !idea.claimed_by_other && (
                        <button
                            onClick={() => onBuild(idea)}
                            disabled={buildingId === idea.id}
                            className="flex items-center gap-1.5 h-9 px-4 rounded-xl bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
                        >
                            {buildingId === idea.id ? (
                                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                                </svg>
                            ) : (
                                <Sparkles className="w-3.5 h-3.5" />
                            )}
                            Build
                        </button>
                    )}
                    {!idea.is_claimed && (
                        <button
                            onClick={() => onDelete(idea.id)}
                            disabled={deletingId === idea.id}
                            className="h-9 w-9 rounded-xl border border-zinc-700 flex items-center justify-center text-zinc-500 hover:text-red-400 hover:border-red-500/30 transition-colors disabled:opacity-50"
                            title="Remove saved idea"
                        >
                            {deletingId === idea.id ? (
                                <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                                </svg>
                            ) : (
                                <Trash2 className="w-3.5 h-3.5" />
                            )}
                        </button>
                    )}
                    <button
                        onClick={() => setExpanded(v => !v)}
                        className="h-9 w-9 rounded-xl border border-zinc-700 flex items-center justify-center text-zinc-500 hover:text-white hover:border-zinc-500 transition-colors"
                        title={expanded ? "Collapse" : "Expand details"}
                    >
                        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                </div>
            </div>

            {/* Expanded detail */}
            <AnimatePresence initial={false}>
                {expanded && (
                    <motion.div
                        key="details"
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="border-t border-zinc-800/60 px-5 py-5 grid grid-cols-1 md:grid-cols-2 gap-5">
                            <IdeaDetail
                                label="Target Audience"
                                icon={Target}
                                value={c.target_market || c.target_audience}
                            />
                            <IdeaDetail
                                label="Problem & Why Now"
                                icon={AlertCircle}
                                value={c.problem_statement || c.why_now}
                            />
                            <IdeaDetail
                                label="Revenue Model"
                                icon={TrendingUp}
                                value={c.revenue_model}
                            />
                            <IdeaDetail
                                label="Differentiator"
                                icon={Zap}
                                value={c.differentiator || c.unique_angle}
                            />
                            {features.length > 0 && (
                                <div className="md:col-span-2">
                                    <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-zinc-500 mb-2">
                                        <Lightbulb className="w-3.5 h-3.5" />
                                        Key Features
                                    </div>
                                    <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                                        {features.map((f, i) => (
                                            <li key={i} className="flex items-start gap-2 text-sm text-zinc-300">
                                                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0" />
                                                {f}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {idea.claimed_by_other && (
                                <div className="md:col-span-2 flex items-center gap-2 text-sm text-orange-400/80 bg-orange-500/5 border border-orange-500/10 rounded-xl px-4 py-3">
                                    <Users className="w-4 h-4 shrink-0" />
                                    Another user is currently building this idea — it's no longer available.
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

export default function SavedIdeasPage() {
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();
    const [ideas, setIdeas] = useState<SavedIdeaEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [buildingId, setBuildingId] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [filter, setFilter] = useState<"all" | "available" | "building">("all");

    useEffect(() => {
        loadIdeas();
    }, []);

    const loadIdeas = async () => {
        setLoading(true);
        try {
            const token = await getAccessToken();
            const res = await fetch(`${getApiBaseUrl()}/api/v1/ideation/saved`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setIdeas(data.saved_ideas || []);
            }
        } catch (e) {
            console.error("Failed to load saved ideas", e);
        } finally {
            setLoading(false);
        }
    };

    const handleBuild = async (idea: SavedIdeaEntry) => {
        setBuildingId(idea.id);
        try {
            const token = await getAccessToken();
            const c = idea.content || {};
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/accept`, {
                method: "POST",
                headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
                body: JSON.stringify({
                    name: idea.name,
                    description: c.description || "",
                    target_audience: c.target_market || c.target_audience || "",
                    problem_statement: c.problem_statement || c.why_now || "",
                    source: idea.source || "questionnaire",
                    idea_content: c,
                }),
            });
            if (!resp.ok) throw new Error("Failed to create project");
            const data = await resp.json();
            navigate(`/csuite/${data.project_id}`);
        } catch (e) {
            console.error("Failed to build idea", e);
        } finally {
            setBuildingId(null);
        }
    };

    const handleDelete = async (id: string) => {
        if (!window.confirm("Remove this saved idea?")) return;
        setDeletingId(id);
        try {
            const token = await getAccessToken();
            const res = await fetch(`${getApiBaseUrl()}/api/v1/ideation/saved/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) setIdeas(prev => prev.filter(i => i.id !== id));
        } catch (e) {
            console.error("Failed to delete idea", e);
        } finally {
            setDeletingId(null);
        }
    };

    const filtered = ideas.filter(idea => {
        if (filter === "available") return !idea.is_claimed && !idea.claimed_by_other;
        if (filter === "building") return idea.is_claimed;
        return true;
    });

    const availableCount = ideas.filter(i => !i.is_claimed && !i.claimed_by_other).length;
    const buildingCount  = ideas.filter(i => i.is_claimed).length;

    return (
        <div className="max-w-3xl mx-auto px-6 py-12">
            {/* Back */}
            <button
                onClick={() => navigate("/ideation")}
                className="flex items-center gap-2 text-sm text-zinc-500 hover:text-white transition-colors mb-8"
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Ideation
            </button>

            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/10 flex items-center justify-center">
                        <Bookmark className="w-5 h-5 text-amber-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white">Saved Ideas</h1>
                        <p className="text-sm text-zinc-500 mt-0.5">
                            {ideas.length === 0 ? "No ideas saved yet" : `${ideas.length} idea${ideas.length !== 1 ? "s" : ""} saved`}
                        </p>
                    </div>
                </div>
            </div>

            {/* Exclusivity note */}
            {ideas.length > 0 && (
                <p className="flex items-center gap-2 text-xs text-zinc-600 mb-6 mt-4">
                    <Users className="w-3.5 h-3.5 shrink-0" />
                    Ideas are available until someone starts building — then they're locked exclusively to that user.
                </p>
            )}

            {/* Filter tabs */}
            {ideas.length > 0 && (
                <div className="flex gap-2 mb-6">
                    {[
                        { key: "all",       label: `All (${ideas.length})` },
                        { key: "available", label: `Available (${availableCount})` },
                        { key: "building",  label: `Building (${buildingCount})` },
                    ].map(tab => (
                        <button
                            key={tab.key}
                            onClick={() => setFilter(tab.key as any)}
                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                                filter === tab.key
                                    ? "bg-zinc-700 text-white"
                                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/60"
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            )}

            {/* Content */}
            {loading ? (
                <div className="flex flex-col items-center gap-4 py-24 text-zinc-600">
                    <svg className="w-8 h-8 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    <p className="text-sm">Loading saved ideas…</p>
                </div>
            ) : ideas.length === 0 ? (
                <motion.div
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center gap-4 py-24 text-center"
                >
                    <div className="w-16 h-16 rounded-2xl bg-zinc-800/60 border border-zinc-700/50 flex items-center justify-center mb-2">
                        <Bookmark className="w-8 h-8 text-zinc-600" />
                    </div>
                    <h2 className="text-lg font-semibold text-zinc-400">No saved ideas yet</h2>
                    <p className="text-sm text-zinc-600 max-w-xs leading-relaxed">
                        When you find an idea you like, bookmark it — it'll appear here so you can build it later.
                    </p>
                    <button
                        onClick={() => navigate("/ideation")}
                        className="mt-2 flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 transition-colors"
                    >
                        <Sparkles className="w-4 h-4" />
                        Discover Ideas
                    </button>
                </motion.div>
            ) : filtered.length === 0 ? (
                <p className="text-center text-zinc-600 py-16 text-sm">No ideas match this filter.</p>
            ) : (
                <div className="space-y-3">
                    <AnimatePresence>
                        {filtered.map(idea => (
                            <IdeaCard
                                key={idea.id}
                                idea={idea}
                                onBuild={handleBuild}
                                onDelete={handleDelete}
                                buildingId={buildingId}
                                deletingId={deletingId}
                            />
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
}
