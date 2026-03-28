import { Link } from "react-router-dom";
import { Compass, Home, Lightbulb, UserCircle } from "lucide-react";
import { useTheme } from "../../contexts/ThemeContext";

export default function NotFoundPage() {
    const { theme } = useTheme();
    const isDark = theme === "dark";

    return (
        <div className="max-w-4xl mx-auto px-6 py-16">
            <div className={`rounded-2xl border p-8 sm:p-10 ${
                isDark
                    ? "bg-[#12121A] border-zinc-800/60"
                    : "bg-white border-zinc-200 shadow-sm shadow-zinc-200/60"
            }`}>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-300 border border-purple-500/20 mb-5">
                    <Compass className="w-3.5 h-3.5" />
                    Page Not Found
                </div>
                <h1 className={`text-3xl font-bold mb-3 ${isDark ? "text-white" : "text-zinc-900"}`}>
                    This screen does not exist yet.
                </h1>
                <p className={`text-sm sm:text-base max-w-2xl mb-8 ${isDark ? "text-zinc-400" : "text-zinc-600"}`}>
                    The link may be outdated, or the page was moved. Use one of these destinations to continue your build workflow.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <Link
                        to="/"
                        className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${
                            isDark
                                ? "border-zinc-700 bg-zinc-900/60 text-zinc-200 hover:border-purple-500/40 hover:text-white"
                                : "border-zinc-300 bg-zinc-50 text-zinc-700 hover:border-purple-300 hover:text-zinc-900"
                        }`}
                    >
                        <Home className="w-4 h-4" />
                        Projects Dashboard
                    </Link>
                    <Link
                        to="/ideation"
                        className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${
                            isDark
                                ? "border-zinc-700 bg-zinc-900/60 text-zinc-200 hover:border-purple-500/40 hover:text-white"
                                : "border-zinc-300 bg-zinc-50 text-zinc-700 hover:border-purple-300 hover:text-zinc-900"
                        }`}
                    >
                        <Lightbulb className="w-4 h-4" />
                        Ideation Flow
                    </Link>
                    <Link
                        to="/profile"
                        className={`flex items-center gap-2 rounded-xl border px-4 py-3 text-sm font-medium transition-colors ${
                            isDark
                                ? "border-zinc-700 bg-zinc-900/60 text-zinc-200 hover:border-purple-500/40 hover:text-white"
                                : "border-zinc-300 bg-zinc-50 text-zinc-700 hover:border-purple-300 hover:text-zinc-900"
                        }`}
                    >
                        <UserCircle className="w-4 h-4" />
                        Profile Settings
                    </Link>
                </div>
            </div>
        </div>
    );
}
