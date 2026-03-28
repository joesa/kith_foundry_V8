import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useApiFetch } from "../../hooks/useApiFetch";
import { useAuth } from "../../contexts/AuthContext";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../lib/utils/cn";

// ── Questionnaire Data ──────────────────────────────────────────────────────

interface Question {
    id: number;
    category: string;
    categoryColor: string;
    question: string;
    type: "rating" | "multi" | "text";
    options?: string[];
}

const QUESTIONS: Question[] = [
    { id: 1, category: "PERSONAL", categoryColor: "text-blue-400 border-blue-400", question: "What industries or domains excite you most?", type: "multi", options: ["Technology/SaaS", "Healthcare/Biotech", "Education/EdTech", "Finance/FinTech", "E-commerce/Retail", "Media/Entertainment", "Real Estate/PropTech", "Food/Agriculture", "Energy/CleanTech", "Social Impact/Non-profit"] },
    { id: 2, category: "PERSONAL", categoryColor: "text-blue-400 border-blue-400", question: "What are your strongest skills?", type: "multi", options: ["Software development", "Design/UX", "Marketing/Sales", "Data/Analytics", "Operations/Management", "Finance/Accounting", "Content/Writing", "Research/Strategy"] },
    { id: 3, category: "PERSONAL", categoryColor: "text-blue-400 border-blue-400", question: "How much time can you dedicate weekly?", type: "multi", options: ["< 10 hours (side project)", "10-20 hours (serious side hustle)", "20-40 hours (part-time focus)", "40+ hours (full-time)", "Flexible/Variable"] },
    { id: 4, category: "PROBLEM", categoryColor: "text-orange-400 border-orange-400", question: "What problems frustrate you most in daily life or work?", type: "text" },
    { id: 5, category: "PROBLEM", categoryColor: "text-orange-400 border-orange-400", question: "Rate your frustration with current solutions in your area of interest", type: "rating" },
    { id: 6, category: "PROBLEM", categoryColor: "text-orange-400 border-orange-400", question: "Who would benefit most from your ideal product?", type: "multi", options: ["Individual consumers", "Small businesses", "Enterprise companies", "Developers/Technical users", "Students/Educators", "Healthcare professionals", "Government/Public sector", "Creative professionals"] },
    { id: 7, category: "BUSINESS", categoryColor: "text-green-400 border-green-400", question: "Which business model appeals to you?", type: "multi", options: ["B2B SaaS (recurring revenue)", "B2C Subscription", "Marketplace (take rate)", "E-commerce", "Freemium", "Advertising", "One-time purchase", "Usage-based pricing", "Transaction fees", "Licensing/Royalties", "Consulting/Services", "Affiliate/Referral", "Hybrid model"] },
    { id: 8, category: "BUSINESS", categoryColor: "text-green-400 border-green-400", question: "What scale are you targeting?", type: "multi", options: ["Lifestyle business ($100K-$1M/year)", "Small startup ($1M-$10M/year)", "High-growth ($10M-$100M/year)", "Unicorn potential ($100M+/year)", "Niche/Micro-SaaS ($10K-$100K/year)", "Open to any profitable model"] },
    { id: 9, category: "BUSINESS", categoryColor: "text-green-400 border-green-400", question: "How do you plan to fund this?", type: "multi", options: ["Bootstrapped (self-funded)", "Angel/Seed funding", "VC funding", "Revenue-funded (profitable from day 1)", "Crowdfunding", "Grants/Accelerators", "Friends & Family", "Pre-sales/Customers", "Strategic investors", "Open to any option"] },
    { id: 10, category: "TECHNICAL", categoryColor: "text-cyan-400 border-cyan-400", question: "Rate your technical capability", type: "rating" },
    { id: 11, category: "TECHNICAL", categoryColor: "text-cyan-400 border-cyan-400", question: "For your MVP, would you prefer to:", type: "multi", options: ["Build everything from scratch", "Use no-code/low-code tools", "Hire developers", "Mix of building and no-code", "Use AI code generators", "Outsource development", "Find technical co-founder", "Use existing platforms/APIs", "Open source solutions"] },
    { id: 12, category: "MARKET", categoryColor: "text-pink-400 border-pink-400", question: "Which emerging trends excite you?", type: "multi", options: ["AI/Generative AI", "Blockchain/Web3", "Climate Tech", "Remote Work", "Creator Economy", "Health Tech", "EdTech", "FinTech", "Quantum Computing", "AR/VR/Metaverse", "IoT/Smart Devices", "Autonomous Vehicles", "5G/Edge Computing", "Biotechnology", "Space Tech", "Robotics/Automation"] },
    { id: 13, category: "MARKET", categoryColor: "text-pink-400 border-pink-400", question: "How do you feel about competition?", type: "multi", options: ["Prefer blue ocean (no competition)", "Validated market with room to innovate", "Ready to disrupt established players", "Niche focus within competitive market", "Better execution of existing ideas", "Open to any competitive landscape"] },
    { id: 14, category: "MARKET", categoryColor: "text-pink-400 border-pink-400", question: "Geographic focus?", type: "multi", options: ["Global from day 1", "Start in US, expand later", "Focus on emerging markets", "Specific region/country", "Europe first", "Asia-Pacific", "Latin America", "Remote-first (location agnostic)"] },
    { id: 15, category: "VISION", categoryColor: "text-purple-400 border-purple-400", question: "In one sentence, what impact do you want your product to have?", type: "text" },
];

type Answers = Record<number, string | string[] | number>;

type UniqueIdea = any;

type UniqueIdeaCacheEntry = {
    idea: UniqueIdea | null;
    expiresAt: number;
    promise: Promise<UniqueIdea> | null;
};

const UNIQUE_IDEA_CACHE_TTL_MS = 15000;
const uniqueIdeaCache = new Map<string, UniqueIdeaCacheEntry>();

async function requestUniqueIdea(apiFetch: ReturnType<typeof useApiFetch>, cacheKey: string): Promise<UniqueIdea> {
    const now = Date.now();
    const cached = uniqueIdeaCache.get(cacheKey);

    if (cached?.idea && cached.expiresAt > now) {
        return cached.idea;
    }

    if (cached?.promise) {
        return cached.promise;
    }

    const request = (async () => {
        const resp = await apiFetch("/api/v1/ideation/generate-unique", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });

        if (!resp.ok) {
            let msg = `Request failed (${resp.status}). Try again.`;
            try {
                const errBody = await resp.json();
                if (errBody?.detail) msg = String(errBody.detail);
            } catch {
                /* ignore */
            }
            throw new Error(msg);
        }

        const data = await resp.json();
        const idea = data.idea;
        uniqueIdeaCache.set(cacheKey, {
            idea,
            expiresAt: Date.now() + UNIQUE_IDEA_CACHE_TTL_MS,
            promise: null,
        });
        return idea;
    })();

    uniqueIdeaCache.set(cacheKey, {
        idea: cached?.idea ?? null,
        expiresAt: cached?.expiresAt ?? 0,
        promise: request,
    });

    try {
        return await request;
    } catch (error) {
        uniqueIdeaCache.delete(cacheKey);
        throw error;
    } finally {
        const current = uniqueIdeaCache.get(cacheKey);
        if (current?.promise === request) {
            if (current.idea && current.expiresAt > Date.now()) {
                uniqueIdeaCache.set(cacheKey, {
                    idea: current.idea,
                    expiresAt: current.expiresAt,
                    promise: null,
                });
            } else {
                uniqueIdeaCache.delete(cacheKey);
            }
        }
    }
}

export default function DiscoverIdeaPage() {
    const navigate = useNavigate();
    const apiFetch = useApiFetch();
    const { user } = useAuth();
    const [phase, setPhase] = useState<"unique" | "questionnaire" | "generating" | "results">("unique");
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState<Answers>({});
    const [uniqueIdea, setUniqueIdea] = useState<any>(null);
    const [generatedIdeas, setGeneratedIdeas] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [uniqueLoading, setUniqueLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
    const [savingId, setSavingId] = useState<string | null>(null);
    const uniqueIdeaCacheKey = user?.id ?? "anonymous";

    // Load unique idea when we enter that phase
    useEffect(() => {
        let cancelled = false;

        void (async () => {
            setUniqueLoading(true);
            setError(null);
            try {
                const idea = await requestUniqueIdea(apiFetch, uniqueIdeaCacheKey);
                if (!cancelled) {
                    setUniqueIdea((current: UniqueIdea | null) => current ?? idea);
                }
            } catch (e) {
                if (!cancelled) {
                    console.error("Failed to generate unique idea:", e);
                    setError(e instanceof Error ? e.message : "Failed to generate idea. Check your connection and try again.");
                }
            } finally {
                if (!cancelled) {
                    setUniqueLoading(false);
                }
            }
        })();

        return () => {
            cancelled = true;
        };
    }, [apiFetch, uniqueIdeaCacheKey]);

    const handleFindSomethingElse = () => {
        uniqueIdeaCache.delete(uniqueIdeaCacheKey);
        setUniqueIdea(null);
        setPhase("questionnaire");
    };

    const handleAcceptIdea = async (idea: any) => {
        setLoading(true);
        try {
            const resp = await apiFetch("/api/v1/ideation/accept", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: idea.name,
                    description: idea.description,
                    target_audience: idea.target_market || idea.target_audience,
                    problem_statement: idea.problem_statement || idea.why_now,
                    source: idea.source || "questionnaire",
                    idea_content: idea,
                }),
            });
            if (!resp.ok) throw new Error("Failed to create project");
            const data = await resp.json();
            navigate(`/app/projects/${data.project_id}/executive`);
        } catch (e: any) {
            setError(e.message);
            setLoading(false);
        }
    };

    const handleSaveIdea = async (idea: any) => {
        const key = idea.name;
        setSavingId(key);
        try {
            const resp = await apiFetch("/api/v1/ideation/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: idea.name,
                    content: idea,
                    score: idea.score,
                    source: idea.source || "questionnaire",
                }),
            });
            if (resp.ok) {
                setSavedIds(prev => new Set([...prev, key]));
            }
        } catch (e) {
            console.error("Failed to save idea", e);
        } finally {
            setSavingId(null);
        }
    };

    const handleSubmitQuestionnaire = async () => {
        setPhase("generating");
        try {
            const resp = await apiFetch("/api/v1/ideation/questionnaire", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ responses: answers }),
            });
            if (!resp.ok) throw new Error("Failed to generate ideas");
            const data = await resp.json();
            setGeneratedIdeas(data.ideas || []);
            setPhase("results");
        } catch (e: any) {
            setError(e.message);
            setPhase("questionnaire");
        }
    };

    const setAnswer = (qId: number, value: Answers[number]) => {
        setAnswers(prev => ({ ...prev, [qId]: value }));
    };

    const toggleMulti = (qId: number, option: string) => {
        setAnswers(prev => {
            const curr = (prev[qId] as string[]) || [];
            return {
                ...prev,
                [qId]: curr.includes(option) ? curr.filter(o => o !== option) : [...curr, option],
            };
        });
    };

    const progress = Math.round(((step + 1) / QUESTIONS.length) * 100);
    const currentQ = QUESTIONS[step];
    const isLastStep = step === QUESTIONS.length - 1;

    // ── Unique Idea Phase ────────────────────────────────────────────────────
    if (phase === "unique") {
        return (
            <div className="max-w-3xl mx-auto px-6 py-16">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary-container border border-outline-variant/20 mb-6">
                        <span className="material-symbols-outlined text-3xl text-on-primary-container">psychology</span>
                    </div>
                    <h1 className="text-3xl font-black text-on-surface mb-2 uppercase" style={{ letterSpacing: "-0.05em" }}>
                        Your One-Time Unique Idea
                    </h1>
                    <p className="text-secondary mb-10">This idea is generated exclusively for you and will never be shown to anyone else.</p>

                    {uniqueLoading ? (
                        <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-12 flex flex-col items-center">
                            <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin mb-4" />
                            <p className="text-secondary text-sm">Generating your unique idea...</p>
                        </div>
                    ) : uniqueIdea ? (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="steel-gradient ghost-border rounded-[var(--radius-module)] p-8 text-left"
                        >
                            <div className="flex items-center gap-3 mb-4">
                                <span className="material-symbols-outlined text-xl text-on-primary-container">auto_awesome</span>
                                <h2 className="text-xl font-black text-on-surface uppercase" style={{ letterSpacing: "-0.05em" }}>{uniqueIdea.name}</h2>
                                {uniqueIdea.score && (
                                    <span className="ml-auto text-sm font-black px-3 py-1 rounded-full bg-primary-container text-on-primary-container border border-outline-variant/20 uppercase tracking-widest">
                                        {uniqueIdea.score}/100
                                    </span>
                                )}
                            </div>
                            <p className="text-secondary mb-6 leading-relaxed">{uniqueIdea.description}</p>

                            {uniqueIdea.target_market && (
                                <div className="text-sm text-secondary mb-2"><strong className="text-on-surface font-black uppercase tracking-widest">Target:</strong> {uniqueIdea.target_market}</div>
                            )}
                            {uniqueIdea.revenue_potential && (
                                <div className="text-sm text-secondary mb-2"><strong className="text-on-surface font-black uppercase tracking-widest">Revenue:</strong> {uniqueIdea.revenue_potential}</div>
                            )}
                            {uniqueIdea.why_now && (
                                <div className="text-sm text-secondary mb-6"><strong className="text-on-surface font-black uppercase tracking-widest">Why Now:</strong> {uniqueIdea.why_now}</div>
                            )}

                            <div className="flex items-center gap-3 justify-end flex-wrap">
                                <button
                                    onClick={() => handleSaveIdea({ ...uniqueIdea, source: "unique_gen" })}
                                    disabled={savedIds.has(uniqueIdea.name) || savingId === uniqueIdea.name}
                                    className="flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant/30 text-secondary text-xs font-black uppercase tracking-widest hover:bg-surface-container transition-colors disabled:opacity-50"
                                >
                                    {savedIds.has(uniqueIdea.name)
                                        ? <span className="material-symbols-outlined text-base leading-none text-primary">check_circle</span>
                                        : <span className="material-symbols-outlined text-base leading-none">checklist</span>}
                                    {savedIds.has(uniqueIdea.name) ? "Saved" : "Save for Later"}
                                </button>
                                <button
                                    onClick={handleFindSomethingElse}
                                    className="h-10 px-5 rounded-full border border-outline-variant/30 text-secondary text-xs font-black uppercase tracking-widest hover:bg-surface-container transition-colors"
                                >
                                    Help me find something else
                                </button>
                                <button
                                    onClick={() => handleAcceptIdea({ ...uniqueIdea, source: "unique_gen" })}
                                    disabled={loading}
                                    className="flex items-center gap-2 h-10 px-6 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                                >
                                    <span className="material-symbols-outlined text-base leading-none">check_circle</span>
                                    Accept & Build
                                </button>
                            </div>
                        </motion.div>
                    ) : (
                        <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-8 text-center">
                            <p className="text-secondary mb-4">Couldn't generate a unique idea right now.</p>
                            <button
                                onClick={handleFindSomethingElse}
                                className="h-10 px-6 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity"
                            >
                                Answer questions instead
                            </button>
                        </div>
                    )}
                </motion.div>
            </div>
        );
    }

    // ── Generating Phase ─────────────────────────────────────────────────────
    if (phase === "generating") {
        return (
            <div className="max-w-3xl mx-auto px-6 py-32 text-center">
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="w-16 h-16 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-6" />
                    <h2 className="text-2xl font-black text-on-surface mb-2 uppercase" style={{ letterSpacing: "-0.05em" }}>
                        Generating Your Ideas
                    </h2>
                    <p className="text-secondary">Our AI is producing 3 globally unique ideas tailored to your answers. Please be patient, this can take up to 2 minutes.</p>
                </motion.div>
            </div>
        );
    }

    // ── Results Phase ────────────────────────────────────────────────────────
    if (phase === "results") {
        return (
            <div className="max-w-4xl mx-auto px-6 py-12">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <div className="text-center mb-10">
                        <h1 className="text-3xl font-black text-on-surface mb-2 uppercase" style={{ letterSpacing: "-0.05em" }}>
                            Your Personalized Ideas
                        </h1>
                        <p className="text-secondary">3 unique ideas crafted from your profile. Select one to proceed to C-Suite validation.</p>
                    </div>

                    {/* Exclusivity Info Banner */}
                    <div className="mb-8 steel-gradient ghost-border rounded-[var(--radius-module)] p-5">
                        <div className="flex items-start gap-4">
                            <div className="shrink-0 w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center">
                                <span className="material-symbols-outlined text-xl text-on-primary-container">security</span>
                            </div>
                            <div className="space-y-2 text-sm">
                                <h4 className="font-black text-on-surface uppercase tracking-widest">How Idea Exclusivity Works</h4>
                                <div className="flex items-start gap-2 text-secondary">
                                    <span className="material-symbols-outlined text-base leading-none shrink-0 mt-0.5 text-tertiary">checklist</span>
                                    <span><strong className="text-on-surface font-black">Save for Later</strong> — idea remains visible to all users. Save it to your profile and build when you're ready.</span>
                                </div>
                                <div className="flex items-start gap-2 text-secondary">
                                    <span className="material-symbols-outlined text-base leading-none shrink-0 mt-0.5 text-primary">auto_awesome</span>
                                    <span><strong className="text-on-surface font-black">Build This</strong> — idea becomes <strong className="text-primary">exclusively yours</strong>. No other user will ever see or be able to build this idea.</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-6">
                        {generatedIdeas.map((idea, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.15 }}
                                className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6"
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="text-lg font-black text-primary">#{i + 1}</span>
                                        <h3 className="text-lg font-black text-on-surface uppercase" style={{ letterSpacing: "-0.05em" }}>{idea.name}</h3>
                                    </div>
                                    {idea.score && (
                                        <span className="text-sm font-black px-3 py-1 rounded-full bg-primary-container text-on-primary-container border border-outline-variant/20 uppercase tracking-widest">
                                            {idea.score}/100
                                        </span>
                                    )}
                                </div>

                                <p className="text-secondary text-sm mb-4 leading-relaxed">{idea.description}</p>

                                {/* Detail fields */}
                                {["target_market", "tam", "revenue_model", "monthly_revenue_potential", "how_it_works", "why_now", "go_to_market", "pricing_model", "strategic_moat", "launch_plan_90_day"].map(field => {
                                    const val = idea[field];
                                    if (!val) return null;
                                    const label = field.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                                    return (
                                        <div key={field} className="text-sm text-secondary mb-2">
                                            <strong className="text-on-surface font-black uppercase tracking-widest text-xs">{label}:</strong> {val}
                                        </div>
                                    );
                                })}

                                <div className="flex justify-end gap-3 mt-6">
                                    <button
                                        onClick={() => handleSaveIdea({ ...idea, source: "questionnaire" })}
                                        disabled={savedIds.has(idea.name) || savingId === idea.name}
                                        className="flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant/30 text-secondary text-xs font-black uppercase tracking-widest hover:bg-surface-container transition-colors disabled:opacity-50"
                                    >
                                        {savedIds.has(idea.name)
                                            ? <span className="material-symbols-outlined text-base leading-none text-primary">check_circle</span>
                                            : <span className="material-symbols-outlined text-base leading-none">checklist</span>}
                                        {savedIds.has(idea.name) ? "Saved" : "Save for Later"}
                                    </button>
                                    <button
                                        onClick={() => handleAcceptIdea({ ...idea, source: "questionnaire" })}
                                        disabled={loading}
                                        className="flex items-center gap-2 h-10 px-6 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                                    >
                                        <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>
                                        Build This
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    <div className="flex justify-center mt-8">
                        <button
                            onClick={() => { setPhase("questionnaire"); setStep(0); }}
                            className="text-sm text-tertiary hover:text-on-surface font-black uppercase tracking-widest transition-colors"
                        >
                            Start over with different answers
                        </button>
                    </div>
                </motion.div>
            </div>
        );
    }

    // ── Questionnaire Phase ──────────────────────────────────────────────────
    return (
        <div className="max-w-3xl mx-auto px-6 py-12">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <div className="text-center mb-10">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary-container border border-outline-variant/20 mb-4">
                        <span className="material-symbols-outlined text-2xl text-on-primary-container">psychology</span>
                    </div>
                    <h1 className="text-2xl font-black text-on-surface mb-1 uppercase" style={{ letterSpacing: "-0.05em" }}>
                        Discover Your Idea
                    </h1>
                    <p className="text-secondary text-sm">Answer {QUESTIONS.length} questions to generate 3 personalized ideas</p>
                </div>

                {/* Card */}
                <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-8">
                    {/* Progress */}
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-secondary font-black uppercase tracking-widest">Progress</span>
                        <span className="text-xs font-black text-primary uppercase tracking-widest">{progress}%</span>
                    </div>
                    <div className="h-1.5 bg-surface-container rounded-full mb-6 overflow-hidden">
                        <motion.div
                            className="h-full bg-secondary rounded-full"
                            initial={false}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.3 }}
                        />
                    </div>

                    {/* Category badge */}
                    <span className={cn("text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full border", currentQ.categoryColor)}>
                        {currentQ.category}
                    </span>

                    {/* Question */}
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={currentQ.id}
                            initial={{ opacity: 0, x: 30 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -30 }}
                            transition={{ duration: 0.2 }}
                        >
                            <h2 className="text-lg font-black text-on-surface mt-4 mb-6 uppercase" style={{ letterSpacing: "-0.05em" }}>{currentQ.question}</h2>

                            {currentQ.type === "rating" && (
                                <div className="flex items-center gap-4 justify-center my-6">
                                    <span className="text-sm text-secondary font-black uppercase tracking-widest">Low</span>
                                    <div className="flex gap-3">
                                        {[1, 2, 3, 4, 5].map(n => (
                                            <button
                                                key={n}
                                                onClick={() => setAnswer(currentQ.id, n)}
                                                className={cn(
                                                    "w-12 h-12 rounded-full text-sm font-black uppercase transition-all",
                                                    answers[currentQ.id] === n
                                                        ? "bg-primary-container text-on-primary-container scale-110"
                                                        : "bg-surface-container text-secondary hover:bg-surface-container-high"
                                                )}
                                            >
                                                {n}
                                            </button>
                                        ))}
                                    </div>
                                    <span className="text-sm text-secondary font-black uppercase tracking-widest">High</span>
                                </div>
                            )}

                            {currentQ.type === "multi" && currentQ.options && (
                                <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
                                    {currentQ.options.map(option => {
                                        const selected = ((answers[currentQ.id] as string[]) || []).includes(option);
                                        return (
                                            <button
                                                key={option}
                                                onClick={() => toggleMulti(currentQ.id, option)}
                                                className={cn(
                                                    "w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm text-left transition-all border",
                                                    selected
                                                        ? "bg-primary-container border-outline-variant/40 text-on-primary-container"
                                                        : "bg-surface-container border-outline-variant/30 text-secondary hover:border-outline-variant/60"
                                                )}
                                            >
                                                <div className={cn(
                                                    "w-4 h-4 rounded border flex items-center justify-center shrink-0",
                                                    selected ? "bg-primary-container border-primary" : "border-outline-variant/40"
                                                )}>
                                                    {selected && <span className="material-symbols-outlined text-xs leading-none text-on-primary-container">check</span>}
                                                </div>
                                                {option}
                                            </button>
                                        );
                                    })}
                                </div>
                            )}

                            {currentQ.type === "text" && (
                                <textarea
                                    value={(answers[currentQ.id] as string) || ""}
                                    onChange={(e) => setAnswer(currentQ.id, e.target.value)}
                                    placeholder="Type your answer..."
                                    className="w-full min-h-[120px] p-4 bg-background border border-outline-variant/30 rounded-lg text-on-surface placeholder:text-tertiary resize-none focus:outline-none focus:ring-2 focus:ring-primary transition-colors"
                                />
                            )}
                        </motion.div>
                    </AnimatePresence>

                    {/* Navigation */}
                    <div className="flex items-center justify-between mt-8">
                        <button
                            onClick={() => setStep(Math.max(0, step - 1))}
                            disabled={step === 0}
                            className="flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant/30 text-secondary text-xs font-black uppercase tracking-widest hover:bg-surface-container transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            <span className="material-symbols-outlined text-base leading-none">arrow_back</span>
                            Back
                        </button>

                        {isLastStep ? (
                            <button
                                onClick={handleSubmitQuestionnaire}
                                disabled={loading}
                                className="flex items-center gap-2 h-10 px-6 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity disabled:opacity-50"
                            >
                                <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>
                                Generate Ideas
                            </button>
                        ) : (
                            <button
                                onClick={() => setStep(step + 1)}
                                className="flex items-center gap-2 h-10 px-6 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity"
                            >
                                Next
                                <span className="material-symbols-outlined text-base leading-none">arrow_forward</span>
                            </button>
                        )}
                    </div>
                </div>

                {error && (
                    <div className="mt-4 px-4 py-3 rounded-lg bg-surface-container border border-outline-variant/30 text-on-surface text-sm">
                        {error}
                    </div>
                )}
            </motion.div>
        </div>
    );
}
