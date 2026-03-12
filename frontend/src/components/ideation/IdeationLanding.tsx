import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Lightbulb, Search, ArrowRight, Sparkles, Bookmark, Trash2, Lock, Users } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";

interface SavedIdeaEntry {
    id: string;
    name: string;
    content: any;
    score: number | null;
    source: string;
    is_claimed: boolean;
    claimed_by_other: boolean;
    created_at: string;
}

export default function IdeationLanding() {
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();
    const [savedIdeas, setSavedIdeas] = useState<SavedIdeaEntry[]>([]);
    const [loadingSaved, setLoadingSaved] = useState(true);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [buildingId, setBuildingId] = useState<string | null>(null);

    useEffect(() => {
        fetchSavedIdeas();
    }, []);

    const fetchSavedIdeas = async () => {
        try {
            const token = await getAccessToken();
            const res = await fetch(`${getApiBaseUrl()}/api/v1/ideation/saved`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                const data = await res.json();
                setSavedIdeas(data.saved_ideas || []);
            }
        } catch (e) {
            console.error("Failed to load saved ideas", e);
        } finally {
            setLoadingSaved(false);
        }
    };

    const handleDeleteSaved = async (id: string) => {
        setDeletingId(id);
        try {
            const token = await getAccessToken();
            await fetch(`${getApiBaseUrl()}/api/v1/ideation/saved/${id}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${token}` },
            });
            setSavedIdeas(prev => prev.filter(s => s.id !== id));
        } catch (e) {
            console.error("Failed to delete saved idea", e);
        } finally {
            setDeletingId(null);
        }
    };

    const handleBuildSaved = async (idea: SavedIdeaEntry) => {
        setBuildingId(idea.id);
        try {
            const token = await getAccessToken();
            const content = idea.content || {};
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/accept`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    name: idea.name,
                    description: content.description || "",
                    target_audience: content.target_market || content.target_audience || "",
                    problem_statement: content.problem_statement || content.why_now || "",
                    source: idea.source || "questionnaire",
                    idea_content: content,
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

    return (
        <div className="max-w-4xl mx-auto px-6 py-16">
            {/* Saved ideas quick-link */}
            <div className="flex justify-end mb-4">
                <button
                    onClick={() => navigate("/ideation/saved")}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl border border-[var(--kf-border)] bg-[var(--kf-surface)] text-sm text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] hover:border-[var(--kf-border-muted)] transition-colors"
                >
                    <Bookmark className="w-4 h-4" />
                    Saved Ideas
                    {!loadingSaved && savedIdeas.length > 0 && (
                        <span className="text-xs bg-purple-500/20 text-purple-300 border border-purple-500/20 px-1.5 py-0.5 rounded-full">
                            {savedIdeas.length}
                        </span>
                    )}
                </button>
            </div>

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-16"
            >
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-500/10 mb-6">
                    <Sparkles className="w-8 h-8 text-purple-400" />
                </div>
                <h1 className="text-4xl font-bold text-[var(--kf-text)] mb-3">
                    What would you like to build?
                </h1>
                <p className="text-lg text-[var(--kf-text-secondary)] max-w-xl mx-auto">
                    Whether you have a clear vision or need inspiration, we'll help you shape it into a validated, buildable product.
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
                {/* Path 1: I have an idea */}
                <motion.button
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    onClick={() => navigate("/ideation/prompt")}
                    className="group relative bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl p-8 text-left hover:border-purple-500/30 hover:bg-[var(--kf-surface-hover)] transition-all"
                >
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative">
                        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/10 flex items-center justify-center mb-5">
                            <Lightbulb className="w-7 h-7 text-amber-400" />
                        </div>
                        <h2 className="text-xl font-bold text-[var(--kf-text)] mb-2 group-hover:text-purple-500 dark:group-hover:text-purple-300 transition-colors">
                            I Have an Idea
                        </h2>
                        <p className="text-[var(--kf-text-secondary)] text-sm mb-6 leading-relaxed">
                            Share your vision and our AI will enhance it into 3 unique variations — each a potential standalone product.
                        </p>
                        <div className="flex items-center gap-2 text-purple-400 text-sm font-medium group-hover:gap-3 transition-all">
                            <span>Describe your idea</span>
                            <ArrowRight className="w-4 h-4" />
                        </div>
                    </div>
                </motion.button>

                {/* Path 2: Help me discover */}
                <motion.button
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                    onClick={() => navigate("/ideation/discover")}
                    className="group relative bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl p-8 text-left hover:border-purple-500/30 hover:bg-[var(--kf-surface-hover)] transition-all"
                >
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative">
                        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-500/10 flex items-center justify-center mb-5">
                            <Search className="w-7 h-7 text-purple-400" />
                        </div>
                        <h2 className="text-xl font-bold text-[var(--kf-text)] mb-2 group-hover:text-purple-500 dark:group-hover:text-purple-300 transition-colors">
                            Help Me Discover
                        </h2>
                        <p className="text-[var(--kf-text-secondary)] text-sm mb-6 leading-relaxed">
                            We'll generate a globally unique idea just for you, or guide you through questions to find your perfect match.
                        </p>
                        <div className="flex items-center gap-2 text-purple-400 text-sm font-medium group-hover:gap-3 transition-all">
                            <span>Discover your idea</span>
                            <ArrowRight className="w-4 h-4" />
                        </div>
                    </div>
                </motion.button>
            </div>

            {/* Saved Ideas Section */}
            {!loadingSaved && savedIdeas.length > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="mt-16 max-w-3xl mx-auto"
                >
                    <div className="flex items-center gap-3 mb-6">
                        <Bookmark className="w-5 h-5 text-zinc-400" />
                        <h2 className="text-xl font-bold text-[var(--kf-text)]">Saved Ideas</h2>
                        <span className="text-xs bg-[var(--kf-badge-bg)] text-[var(--kf-text-secondary)] px-2 py-0.5 rounded-full">{savedIdeas.length}</span>
                    </div>

                    {/* Exclusivity reminder */}
                    <div className="mb-4 flex items-center gap-2 text-xs text-zinc-500">
                        <Users className="w-3.5 h-3.5" />
                        <span>Saved ideas are visible to all users until you start building — then they become exclusively yours.</span>
                    </div>

                    <div className="space-y-3">
                        <AnimatePresence>
                            {savedIdeas.map((idea) => (
                                <motion.div
                                    key={idea.id}
                                    layout
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: "auto" }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-xl p-5 flex items-center gap-4"
                                >
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-sm font-semibold text-[var(--kf-text)] truncate">{idea.name}</h3>
                                            {idea.is_claimed && (
                                                <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold text-purple-300 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-full">
                                                    <Lock className="w-3 h-3" /> Yours
                                                </span>
                                            )}
                                            {idea.claimed_by_other && (
                                                <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-bold text-orange-300 bg-orange-500/10 border border-orange-500/20 px-2 py-0.5 rounded-full">
                                                    <Lock className="w-3 h-3" /> Taken
                                                </span>
                                            )}
                                            {idea.score && (
                                                <span className="shrink-0 text-[10px] font-bold text-purple-300 bg-purple-500/10 px-2 py-0.5 rounded-full">{idea.score}/100</span>
                                            )}
                                        </div>
                                        <p className="text-xs text-zinc-500 truncate">{idea.content?.description || ""}</p>
                                    </div>

                                    <div className="flex items-center gap-2 shrink-0">
                                        {!idea.is_claimed && !idea.claimed_by_other && (
                                            <button
                                                onClick={() => handleBuildSaved(idea)}
                                                disabled={buildingId === idea.id}
                                                className="flex items-center gap-1.5 h-8 px-4 rounded-lg bg-purple-600 text-white text-xs font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
                                            >
                                                <Sparkles className="w-3.5 h-3.5" />
                                                Build
                                            </button>
                                        )}
                                        {idea.claimed_by_other && (
                                            <span className="text-xs text-orange-400/70 italic">Another user is building this</span>
                                        )}
                                        {!idea.is_claimed && (
                                            <button
                                                onClick={() => handleDeleteSaved(idea.id)}
                                                disabled={deletingId === idea.id}
                                                className="h-8 w-8 rounded-lg border border-[var(--kf-border-muted)] flex items-center justify-center text-[var(--kf-text-muted)] hover:text-red-400 hover:border-red-500/30 transition-colors disabled:opacity-50"
                                                title="Remove from saved"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </AnimatePresence>
                    </div>
                </motion.div>
            )}
        </div>
    );
}
