import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import { Wand2, ArrowRight, Bookmark, BookmarkCheck, Check, RotateCcw, Sparkles } from "lucide-react";

interface Enhancement {
    name: string;
    description: string;
    differentiators: string[];
    target_market: string;
}

export default function IdeaPromptPage() {
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();
    const [prompt, setPrompt] = useState("");
    const [enhancements, setEnhancements] = useState<Enhancement[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [phase, setPhase] = useState<"input" | "enhancements">("input");
    const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
    const [savingId, setSavingId] = useState<string | null>(null);

    const handleSaveEnhancement = async (enh: Enhancement) => {
        const key = enh.name;
        setSavingId(key);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/save`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    name: enh.name,
                    content: { ...enh, source: "user_prompt" },
                    score: null,
                    source: "user_prompt",
                }),
            });
            if (resp.ok) setSavedIds(prev => new Set([...prev, key]));
        } catch (e) {
            console.error("Failed to save idea", e);
        } finally {
            setSavingId(null);
        }
    };

    const handleEnhance = async () => {
        if (!prompt.trim()) return;
        setLoading(true);
        setError(null);

        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/enhance`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ prompt: prompt.trim() }),
            });

            if (!resp.ok) throw new Error("Failed to enhance prompt");
            const data = await resp.json();
            setEnhancements(data.enhancements || []);
            setPhase("enhancements");
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleAcceptEnhancement = async (enhancement: Enhancement) => {
        setLoading(true);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/accept`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    name: enhancement.name,
                    description: enhancement.description,
                    target_audience: enhancement.target_market,
                    source: "user_prompt",
                    original_prompt: prompt,
                }),
            });

            if (!resp.ok) throw new Error("Failed to create project");
            const data = await resp.json();
            navigate(`/csuite/${data.project_id}`);
        } catch (e: any) {
            setError(e.message);
            setLoading(false);
        }
    };

    const handleUseOriginal = async () => {
        setLoading(true);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/accept`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({
                    name: prompt.trim().slice(0, 60),
                    description: prompt.trim(),
                    source: "user_prompt",
                    original_prompt: prompt,
                }),
            });

            if (!resp.ok) throw new Error("Failed to create project");
            const data = await resp.json();
            navigate(`/csuite/${data.project_id}`);
        } catch (e: any) {
            setError(e.message);
            setLoading(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto px-6 py-12">
            <AnimatePresence mode="wait">
                {phase === "input" ? (
                    <motion.div
                        key="input"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <div className="text-center mb-10">
                            <h1 className="text-3xl font-bold text-[var(--kf-text)] mb-2">Describe Your Vision</h1>
                            <p className="text-[var(--kf-text-secondary)]">Tell us what you want to build. Our AI will craft 3 enhanced variations.</p>
                        </div>

                        {/* Prompt input */}
                        <div className="relative group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl opacity-20 group-focus-within:opacity-40 blur transition-opacity" />
                            <div className="relative bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl p-1 group-focus-within:border-purple-500/30 transition-colors">
                                <textarea
                                    value={prompt}
                                    onChange={(e) => setPrompt(e.target.value)}
                                    placeholder="e.g. A platform that connects freelance designers with startups needing brand identity work, featuring AI-powered portfolio matching..."
                                    className="w-full min-h-[200px] p-5 bg-transparent text-[var(--kf-text)] placeholder-[var(--kf-text-faint)] resize-none focus:outline-none text-lg leading-relaxed"
                                    autoFocus
                                />
                                <div className="flex items-center justify-between px-5 pb-4">
                                    <span className="text-xs text-[var(--kf-text-faint)]">{prompt.length} characters</span>
                                    <div className="flex items-center gap-3">
                                        <button
                                            onClick={handleUseOriginal}
                                            disabled={!prompt.trim() || loading}
                                            className="h-10 px-5 rounded-xl border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] text-sm font-medium hover:bg-[var(--kf-hover-bg)] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                                        >
                                            Use as-is
                                        </button>
                                        <button
                                            onClick={handleEnhance}
                                            disabled={!prompt.trim() || loading}
                                            className="flex items-center gap-2 h-10 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
                                        >
                                            {loading ? (
                                                <>
                                                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                                    Enhancing...
                                                </>
                                            ) : (
                                                <>
                                                    <Wand2 className="w-4 h-4" />
                                                    Enhance with AI
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="mt-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                                {error}
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                        key="enhancements"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <div className="text-center mb-10">
                            <h1 className="text-3xl font-bold text-[var(--kf-text)] mb-2">Choose Your Direction</h1>
                            <p className="text-[var(--kf-text-secondary)]">We've crafted 3 unique takes on your idea. Select one to proceed.</p>
                        </div>

                        {/* Original prompt reference */}
                        <div className="bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-xl p-4 mb-8">
                            <span className="text-xs text-[var(--kf-text-muted)] uppercase tracking-wider font-medium">Your original prompt</span>
                            <p className="text-[var(--kf-text-secondary)] text-sm mt-1 line-clamp-2">{prompt}</p>
                        </div>

                        {/* Enhancement cards */}
                        <div className="space-y-4">
                            {enhancements.map((enh, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.1 }}
                                    className="group bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-xl p-6 hover:border-purple-500/30 transition-all"
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 font-bold text-sm">
                                                {i + 1}
                                            </div>
                                            <h3 className="text-lg font-bold text-[var(--kf-text)]">{enh.name}</h3>
                                        </div>
                                    </div>
                                    <p className="text-[var(--kf-text-secondary)] text-sm mb-4 leading-relaxed">{enh.description}</p>

                                    {enh.differentiators?.length > 0 && (
                                        <div className="flex flex-wrap gap-2 mb-4">
                                            {enh.differentiators.map((d, j) => (
                                                <span key={j} className="text-xs px-2.5 py-1 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-300 border border-purple-500/10">
                                                    {d}
                                                </span>
                                            ))}
                                        </div>
                                    )}

                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-zinc-500">
                                            <Sparkles className="w-3 h-3 inline mr-1" />
                                            Target: {enh.target_market}
                                        </span>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={() => handleSaveEnhancement(enh)}
                                                disabled={savedIds.has(enh.name) || savingId === enh.name}
                                                className="flex items-center gap-1.5 h-9 px-3.5 rounded-lg border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] text-sm font-medium hover:bg-[var(--kf-hover-bg)] transition-colors disabled:opacity-50"
                                                title="Save for later"
                                            >
                                                {savingId === enh.name ? (
                                                    <div className="w-3.5 h-3.5 border border-current border-t-transparent rounded-full animate-spin" />
                                                ) : savedIds.has(enh.name) ? (
                                                    <BookmarkCheck className="w-3.5 h-3.5 text-green-400" />
                                                ) : (
                                                    <Bookmark className="w-3.5 h-3.5" />
                                                )}
                                                {savedIds.has(enh.name) ? "Saved" : "Save"}
                                            </button>
                                            <button
                                                onClick={() => handleAcceptEnhancement(enh)}
                                                disabled={loading}
                                                className="flex items-center gap-2 h-9 px-4 rounded-lg bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 transition-colors disabled:opacity-50"
                                            >
                                                <Check className="w-3.5 h-3.5" />
                                                Select
                                            </button>
                                        </div>
                                    </div>
                                </motion.div>
                            ))}
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-between mt-8">
                            <button
                                onClick={() => setPhase("input")}
                                className="flex items-center gap-2 text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] text-sm transition-colors"
                            >
                                <RotateCcw className="w-4 h-4" />
                                Edit prompt
                            </button>
                            <button
                                onClick={handleUseOriginal}
                                disabled={loading}
                                className="flex items-center gap-2 h-10 px-5 rounded-xl border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] text-sm font-medium hover:bg-[var(--kf-hover-bg)] transition-colors disabled:opacity-50"
                            >
                                Skip — use my original prompt
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
