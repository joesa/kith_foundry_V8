import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, FlaskConical, Lightbulb, Sparkles } from "lucide-react";
import { useTheme } from "../../contexts/ThemeContext";

export default function IdeaResults() {
    const navigate = useNavigate();
    const { sessionId } = useParams<{ sessionId: string }>();
    const { theme } = useTheme();
    const isDark = theme === "dark";

    return (
        <div className="max-w-4xl mx-auto px-6 py-12">
            <button
                onClick={() => navigate("/ideation/discover")}
                className={`mb-6 inline-flex items-center gap-2 text-sm transition-colors ${
                    isDark ? "text-zinc-400 hover:text-white" : "text-zinc-600 hover:text-zinc-900"
                }`}
            >
                <ArrowLeft className="w-4 h-4" />
                Back to Discovery
            </button>

            <div className={`rounded-2xl border p-8 sm:p-10 ${
                isDark
                    ? "bg-[#12121A] border-zinc-800/60"
                    : "bg-white border-zinc-200 shadow-sm shadow-zinc-200/60"
            }`}>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20 mb-4">
                    <FlaskConical className="w-3.5 h-3.5" />
                    Ideation Session
                </div>
                <h1 className={`text-2xl sm:text-3xl font-bold mb-3 ${isDark ? "text-white" : "text-zinc-900"}`}>
                    Session {sessionId ? sessionId.slice(0, 8) : "Unknown"} is no longer stored as a standalone page.
                </h1>
                <p className={`text-sm sm:text-base max-w-2xl mb-8 ${isDark ? "text-zinc-400" : "text-zinc-600"}`}>
                    Ideation results are now presented directly inside the discovery flow so you can compare ideas, save options, and launch C-Suite analysis without context switching.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Link
                        to="/ideation/discover"
                        className="flex items-center justify-center gap-2 h-11 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white text-sm font-medium hover:from-purple-500 hover:to-purple-400 transition-all"
                    >
                        <Sparkles className="w-4 h-4" />
                        Open Discovery Flow
                    </Link>
                    <Link
                        to="/ideation"
                        className={`flex items-center justify-center gap-2 h-11 rounded-xl border text-sm font-medium transition-colors ${
                            isDark
                                ? "border-zinc-700 bg-zinc-900/60 text-zinc-200 hover:border-purple-500/40 hover:text-white"
                                : "border-zinc-300 bg-zinc-50 text-zinc-700 hover:border-purple-300 hover:text-zinc-900"
                        }`}
                    >
                        <Lightbulb className="w-4 h-4" />
                        Go to Ideation Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
