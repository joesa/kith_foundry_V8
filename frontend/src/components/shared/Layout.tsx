import { Outlet, useNavigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { LogOut, Anvil, UserCircle, Bookmark } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";

export default function Layout() {
    const { user, signOut } = useAuth();
    const { theme } = useTheme();
    const navigate = useNavigate();
    const location = useLocation();
    const onSavedIdeas = location.pathname === "/ideation/saved";

    const handleSignOut = async () => {
        await signOut();
        navigate("/login");
    };

    return (
        <div className={`min-h-screen transition-colors duration-300 ${
            theme === "dark"
                ? "bg-[#0A0A10] text-white"
                : "bg-[#F8F9FA] text-zinc-900"
        }`}>
            {/* Top nav */}
            <header className={`h-14 border-b transition-colors duration-300 ${
                theme === "dark"
                    ? "border-zinc-800/50 bg-[#0C0C14]/80 backdrop-blur-md"
                    : "border-zinc-200/50 bg-white/80 backdrop-blur-md"
            } flex items-center px-6 sticky top-0 z-50`}>
                <button
                    onClick={() => navigate("/")}
                    className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
                >
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center">
                        <Anvil className="w-4.5 h-4.5 text-white" />
                    </div>
                    <span className={`text-lg font-bold tracking-tight bg-clip-text text-transparent ${
                        theme === "dark"
                            ? "bg-gradient-to-r from-white to-zinc-400"
                            : "bg-gradient-to-r from-zinc-900 to-zinc-500"
                    }`}>
                        Kith Foundry
                    </span>
                </button>

                <div className="flex-1" />

                {user && (
                    <div className="flex items-center gap-1">
                        <ThemeToggle />
                        <Link
                            to="/ideation/saved"
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                                onSavedIdeas
                                    ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                                    : theme === "dark"
                                        ? "text-zinc-400 hover:text-white hover:bg-zinc-800"
                                        : "text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100"
                            }`}
                            title="Saved Ideas"
                        >
                            <Bookmark className="w-4 h-4" />
                            <span className="hidden sm:inline">Saved Ideas</span>
                        </Link>
                        <Link
                            to="/profile"
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors text-sm ${
                                theme === "dark"
                                    ? "hover:bg-zinc-800 text-zinc-400 hover:text-white"
                                    : "hover:bg-zinc-100 text-zinc-600 hover:text-zinc-900"
                            }`}
                            title="Profile & Settings"
                        >
                            <UserCircle className="w-4 h-4" />
                            <span className="hidden sm:inline">{user.email}</span>
                        </Link>
                        <button
                            onClick={handleSignOut}
                            className={`p-2 rounded-lg transition-colors ${
                                theme === "dark"
                                    ? "hover:bg-zinc-800 text-zinc-400 hover:text-white"
                                    : "hover:bg-zinc-100 text-zinc-600 hover:text-zinc-900"
                            }`}
                            title="Sign out"
                        >
                            <LogOut className="w-4 h-4" />
                        </button>
                    </div>
                )}
            </header>

            {/* Page content */}
            <main>
                <Outlet />
            </main>
        </div>
    );
}
