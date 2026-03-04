import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowRight, ArrowLeft, Star, Check } from "lucide-react";

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

export default function DiscoverIdeaPage() {
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();
    const [phase, setPhase] = useState<"unique" | "questionnaire" | "generating" | "results">("unique");
    const [step, setStep] = useState(0);
    const [answers, setAnswers] = useState<Answers>({});
    const [uniqueIdea, setUniqueIdea] = useState<any>(null);
    const [generatedIdeas, setGeneratedIdeas] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);
    const [uniqueLoading, setUniqueLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch unique idea on mount
    const fetchUniqueIdea = useCallback(async () => {
        setUniqueLoading(true);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/generate-unique`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
            });
            if (resp.ok) {
                const data = await resp.json();
                setUniqueIdea(data.idea);
            }
        } catch (e) {
            console.error("Failed to generate unique idea:", e);
        } finally {
            setUniqueLoading(false);
        }
    }, [getAccessToken]);

    // Load unique idea when we enter that phase
    useState(() => { fetchUniqueIdea(); });

    const handleAcceptIdea = async (idea: any) => {
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
            navigate(`/csuite/${data.project_id}`);
        } catch (e: any) {
            setError(e.message);
            setLoading(false);
        }
    };

    const handleSubmitQuestionnaire = async () => {
        setPhase("generating");
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/ideation/questionnaire`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
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

    const setAnswer = (qId: number, value: any) => {
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
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/10 mb-6">
                        <Sparkles className="w-8 h-8 text-purple-400" />
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">Your One-Time Unique Idea</h1>
                    <p className="text-zinc-400 mb-10">This idea is generated exclusively for you and will never be shown to anyone else.</p>

                    {uniqueLoading ? (
                        <div className="bg-[#12121A] border border-zinc-800/50 rounded-2xl p-12 flex flex-col items-center">
                            <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mb-4" />
                            <p className="text-zinc-400 text-sm">Generating your unique idea...</p>
                        </div>
                    ) : uniqueIdea ? (
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-[#12121A] border border-zinc-800/50 rounded-2xl p-8 text-left"
                        >
                            <div className="flex items-center gap-3 mb-4">
                                <Star className="w-5 h-5 text-amber-400 fill-amber-400" />
                                <h2 className="text-xl font-bold text-white">{uniqueIdea.name}</h2>
                                {uniqueIdea.score && (
                                    <span className="ml-auto text-sm font-bold px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20">
                                        {uniqueIdea.score}/100
                                    </span>
                                )}
                            </div>
                            <p className="text-zinc-300 mb-6 leading-relaxed">{uniqueIdea.description}</p>

                            {uniqueIdea.target_market && (
                                <div className="text-sm text-zinc-400 mb-2"><strong className="text-zinc-300">Target:</strong> {uniqueIdea.target_market}</div>
                            )}
                            {uniqueIdea.revenue_potential && (
                                <div className="text-sm text-zinc-400 mb-2"><strong className="text-zinc-300">Revenue:</strong> {uniqueIdea.revenue_potential}</div>
                            )}
                            {uniqueIdea.why_now && (
                                <div className="text-sm text-zinc-400 mb-6"><strong className="text-zinc-300">Why Now:</strong> {uniqueIdea.why_now}</div>
                            )}

                            <div className="flex items-center gap-3 justify-end">
                                <button
                                    onClick={() => setPhase("questionnaire")}
                                    className="h-10 px-5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium hover:bg-zinc-800 transition-colors"
                                >
                                    Pass — help me find something else
                                </button>
                                <button
                                    onClick={() => handleAcceptIdea({ ...uniqueIdea, source: "unique_gen" })}
                                    disabled={loading}
                                    className="flex items-center gap-2 h-10 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
                                >
                                    <Check className="w-4 h-4" />
                                    Accept & Build
                                </button>
                            </div>
                        </motion.div>
                    ) : (
                        <div className="bg-[#12121A] border border-zinc-800/50 rounded-2xl p-8 text-center">
                            <p className="text-zinc-400 mb-4">Couldn't generate a unique idea right now.</p>
                            <button
                                onClick={() => setPhase("questionnaire")}
                                className="h-10 px-6 rounded-xl bg-purple-600 text-white text-sm font-medium hover:bg-purple-500 transition-colors"
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
                    <div className="w-16 h-16 border-3 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
                    <h2 className="text-2xl font-bold text-white mb-2">Generating Your Ideas</h2>
                    <p className="text-zinc-400">Our AI is producing 3 globally unique ideas tailored to your answers. Please be patient, this can take up to 2 minutes.</p>
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
                        <h1 className="text-3xl font-bold text-white mb-2">Your Personalized Ideas</h1>
                        <p className="text-zinc-400">3 unique ideas crafted from your profile. Select one to proceed to C-Suite validation.</p>
                    </div>

                    <div className="space-y-6">
                        {generatedIdeas.map((idea, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: i * 0.15 }}
                                className="bg-[#12121A] border border-zinc-800/50 rounded-2xl p-6"
                            >
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <span className="text-lg font-bold text-purple-400">#{i + 1}</span>
                                        <h3 className="text-lg font-bold text-white">{idea.name}</h3>
                                    </div>
                                    {idea.score && (
                                        <span className="text-sm font-bold px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20">
                                            {idea.score}/100
                                        </span>
                                    )}
                                </div>

                                <p className="text-zinc-300 text-sm mb-4 leading-relaxed">{idea.description}</p>

                                {/* Detail fields */}
                                {["target_market", "tam", "revenue_model", "monthly_revenue_potential", "how_it_works", "why_now", "go_to_market", "pricing_model", "strategic_moat", "launch_plan_90_day"].map(field => {
                                    const val = idea[field];
                                    if (!val) return null;
                                    const label = field.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                                    return (
                                        <div key={field} className="text-sm text-zinc-400 mb-2">
                                            <strong className="text-zinc-300">{label}:</strong> {val}
                                        </div>
                                    );
                                })}

                                <div className="flex justify-end gap-3 mt-6">
                                    <button
                                        onClick={() => handleAcceptIdea({ ...idea, source: "questionnaire" })}
                                        disabled={loading}
                                        className="flex items-center gap-2 h-10 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
                                    >
                                        <Sparkles className="w-4 h-4" />
                                        Build This
                                    </button>
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    <div className="flex justify-center mt-8">
                        <button
                            onClick={() => { setPhase("questionnaire"); setStep(0); }}
                            className="text-sm text-zinc-500 hover:text-white transition-colors"
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
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/10 mb-4">
                        <Sparkles className="w-6 h-6 text-purple-400" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-1">Discover Your Idea</h1>
                    <p className="text-zinc-400 text-sm">Answer {QUESTIONS.length} questions to generate 3 personalized ideas</p>
                </div>

                {/* Card */}
                <div className="bg-[#12121A] border border-zinc-800/50 rounded-2xl p-8">
                    {/* Progress */}
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs text-zinc-400 font-medium">Progress</span>
                        <span className="text-xs font-bold text-purple-400">{progress}%</span>
                    </div>
                    <div className="h-1.5 bg-zinc-800 rounded-full mb-6 overflow-hidden">
                        <motion.div
                            className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full"
                            initial={false}
                            animate={{ width: `${progress}%` }}
                            transition={{ duration: 0.3 }}
                        />
                    </div>

                    {/* Category badge */}
                    <span className={`text-[10px] font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full border ${currentQ.categoryColor}`}>
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
                            <h2 className="text-lg font-bold text-white mt-4 mb-6">{currentQ.question}</h2>

                            {currentQ.type === "rating" && (
                                <div className="flex items-center gap-4 justify-center my-6">
                                    <span className="text-sm text-zinc-400">Low</span>
                                    <div className="flex gap-3">
                                        {[1, 2, 3, 4, 5].map(n => (
                                            <button
                                                key={n}
                                                onClick={() => setAnswer(currentQ.id, n)}
                                                className={`w-12 h-12 rounded-full text-sm font-bold transition-all ${answers[currentQ.id] === n
                                                    ? "bg-purple-600 text-white scale-110 shadow-lg shadow-purple-500/30"
                                                    : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                                                    }`}
                                            >
                                                {n}
                                            </button>
                                        ))}
                                    </div>
                                    <span className="text-sm text-zinc-400">High</span>
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
                                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-left transition-all ${selected
                                                    ? "bg-purple-600/20 border-purple-500/40 text-white border"
                                                    : "bg-zinc-800/50 border-zinc-700/50 text-zinc-300 border hover:border-zinc-600"
                                                    }`}
                                            >
                                                <div className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${selected ? "bg-purple-600 border-purple-500" : "border-zinc-600"}`}>
                                                    {selected && <Check className="w-3 h-3 text-white" />}
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
                                    className="w-full min-h-[120px] p-4 bg-zinc-800/50 border border-zinc-700/50 rounded-xl text-white placeholder-zinc-600 resize-none focus:outline-none focus:border-purple-500/50 transition-colors"
                                />
                            )}
                        </motion.div>
                    </AnimatePresence>

                    {/* Navigation */}
                    <div className="flex items-center justify-between mt-8">
                        <button
                            onClick={() => setStep(Math.max(0, step - 1))}
                            disabled={step === 0}
                            className="flex items-center gap-2 h-10 px-5 rounded-xl border border-zinc-700 text-zinc-300 text-sm font-medium hover:bg-zinc-800 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            Back
                        </button>

                        {isLastStep ? (
                            <button
                                onClick={handleSubmitQuestionnaire}
                                disabled={loading}
                                className="flex items-center gap-2 h-10 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20 disabled:opacity-50"
                            >
                                <Sparkles className="w-4 h-4" />
                                Generate Ideas
                            </button>
                        ) : (
                            <button
                                onClick={() => setStep(step + 1)}
                                className="flex items-center gap-2 h-10 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20"
                            >
                                Next
                                <ArrowRight className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>

                {error && (
                    <div className="mt-4 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
                        {error}
                    </div>
                )}
            </motion.div>
        </div>
    );
}
