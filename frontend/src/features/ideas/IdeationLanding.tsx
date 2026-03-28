import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
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
            navigate(`/app/projects/${data.project_id}/executive`);
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
                    onClick={() => navigate("/app/ideation/saved")}
                    className="flex items-center gap-2 px-4 py-2 rounded-full border border-outline-variant/30 bg-surface text-tertiary hover:text-on-surface hover:border-outline-variant transition-colors text-xs font-black uppercase tracking-widest"
                >
                    <span className="material-symbols-outlined text-base leading-none">checklist</span>
                    Saved Ideas
                    {!loadingSaved && savedIdeas.length > 0 && (
                        <span className="text-xs bg-primary-container text-on-primary-container px-1.5 py-0.5 rounded-full font-black">
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
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-container border border-outline-variant/20 mb-6">
                    <span className="material-symbols-outlined text-3xl text-on-primary-container">lightbulb</span>
                </div>
                <h1 className="text-4xl font-black text-on-surface mb-3 uppercase" style={{ letterSpacing: "-0.05em" }}>
                    What would you like to build?
                </h1>
                <p className="text-base text-secondary max-w-xl mx-auto">
                    Whether you have a clear vision or need inspiration, we'll help you shape it into a validated, buildable product.
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
                {/* Path 1: I have an idea */}
                <motion.button
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    onClick={() => navigate("/app/ideation/prompt")}
                    className="group steel-gradient ghost-border rounded-[var(--radius-module)] p-8 text-left hover:border-outline-variant/60 transition-all"
                >
                    <div className="w-14 h-14 rounded-xl bg-primary-container flex items-center justify-center mb-5">
                        <span className="material-symbols-outlined text-2xl text-on-primary-container">lightbulb</span>
                    </div>
                    <h2 className="text-xl font-black text-on-surface mb-2 uppercase" style={{ letterSpacing: "-0.05em" }}>
                        I Have an Idea
                    </h2>
                    <p className="text-secondary text-sm mb-6 leading-relaxed">
                        Share your vision and our AI will enhance it into 3 unique variations — each a potential standalone product.
                    </p>
                    <div className="flex items-center gap-2 text-primary text-xs font-black uppercase tracking-widest">
                        <span>Describe your idea</span>
                        <span className="material-symbols-outlined text-base leading-none">arrow_forward</span>
                    </div>
                </motion.button>

                {/* Path 2: Help me discover */}
                <motion.button
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                    onClick={() => navigate("/app/ideation/discover")}
                    className="group steel-gradient ghost-border rounded-[var(--radius-module)] p-8 text-left hover:border-outline-variant/60 transition-all"
                >
                    <div className="w-14 h-14 rounded-xl bg-primary-container flex items-center justify-center mb-5">
                        <span className="material-symbols-outlined text-2xl text-on-primary-container">psychology</span>
                    </div>
                    <h2 className="text-xl font-black text-on-surface mb-2 uppercase" style={{ letterSpacing: "-0.05em" }}>
                        Help Me Discover
                    </h2>
                    <p className="text-secondary text-sm mb-6 leading-relaxed">
                        We'll generate a globally unique idea just for you, or guide you through questions to find your perfect match.
                    </p>
                    <div className="flex items-center gap-2 text-primary text-xs font-black uppercase tracking-widest">
                        <span>Discover your idea</span>
                        <span className="material-symbols-outlined text-base leading-none">arrow_forward</span>
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
                        <span className="material-symbols-outlined text-xl text-tertiary">checklist</span>
                        <h2 className="text-xl font-black text-on-surface uppercase tracking-widest">Saved Ideas</h2>
                        <span className="text-xs bg-surface-container text-secondary px-2 py-0.5 rounded-full font-black">{savedIdeas.length}</span>
                    </div>

                    {/* Exclusivity reminder */}
                    <div className="mb-4 flex items-center gap-2 text-xs text-tertiary">
                        <span className="material-symbols-outlined text-base leading-none">groups</span>
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
                                    className="steel-gradient ghost-border rounded-[var(--radius-module)] p-5 flex items-center gap-4"
                                >
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-sm font-black text-on-surface truncate uppercase tracking-widest">{idea.name}</h3>
                                            {idea.is_claimed && (
                                                <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-black text-on-primary-container bg-primary-container border border-outline-variant/30 px-2 py-0.5 rounded-full uppercase tracking-widest">
                                                    <span className="material-symbols-outlined text-xs leading-none">lock</span> Yours
                                                </span>
                                            )}
                                            {idea.claimed_by_other && (
                                                <span className="shrink-0 inline-flex items-center gap-1 text-[10px] font-black text-tertiary bg-surface-container border border-outline-variant/30 px-2 py-0.5 rounded-full uppercase tracking-widest">
                                                    <span className="material-symbols-outlined text-xs leading-none">lock</span> Taken
                                                </span>
                                            )}
                                            {idea.score && (
                                                <span className="shrink-0 text-[10px] font-black text-on-primary-container bg-primary-container px-2 py-0.5 rounded-full">{idea.score}/100</span>
                                            )}
                                        </div>
                                        <p className="text-xs text-tertiary truncate">{idea.content?.description || ""}</p>
                                    </div>

                                    <div className="flex items-center gap-2 shrink-0">
                                        {!idea.is_claimed && !idea.claimed_by_other && (
                                            <button
                                                onClick={() => handleBuildSaved(idea)}
                                                disabled={buildingId === idea.id}
                                                className="flex items-center gap-1.5 h-8 px-4 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                                            >
                                                <span className="material-symbols-outlined text-sm leading-none">rocket_launch</span>
                                                Build
                                            </button>
                                        )}
                                        {idea.claimed_by_other && (
                                            <span className="text-xs text-tertiary italic">Another user is building this</span>
                                        )}
                                        {!idea.is_claimed && (
                                            <button
                                                onClick={() => handleDeleteSaved(idea.id)}
                                                disabled={deletingId === idea.id}
                                                className="h-8 w-8 rounded-full border border-outline-variant/30 flex items-center justify-center text-tertiary hover:text-on-surface hover:border-outline-variant transition-colors disabled:opacity-50"
                                                title="Remove from saved"
                                            >
                                                <span className="material-symbols-outlined text-sm leading-none">delete</span>
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
