import { useTheme } from "../../contexts/ThemeContext";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();
    const isDark = theme === "dark";

    return (
        <button
            onClick={toggleTheme}
            className={[
                "flex items-center gap-2 px-3 py-2 rounded-lg border transition-all duration-200 group",
                isDark
                    ? "bg-zinc-800/50 hover:bg-zinc-700/50 border-zinc-700/50"
                    : "bg-white hover:bg-zinc-100 border-zinc-200 shadow-sm",
            ].join(" ")}
            aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
        >
            {isDark ? (
                <Sun className="w-5 h-5 text-yellow-400" />
            ) : (
                <Moon className="w-5 h-5 text-indigo-400" />
            )}
            <span className={[
                "text-sm font-medium transition-colors",
                isDark ? "text-zinc-300 group-hover:text-white" : "text-zinc-700 group-hover:text-zinc-950",
            ].join(" ")}>
                {isDark ? "Light" : "Dark"}
            </span>
        </button>
    );
}