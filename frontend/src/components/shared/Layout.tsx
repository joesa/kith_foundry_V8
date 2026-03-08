import { Outlet, useNavigate, Link, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { LogOut, Anvil, UserCircle, Bookmark } from "lucide-react";

export default function Layout() {
    const { user, signOut } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const onSavedIdeas = location.pathname === "/ideation/saved";

    const handleSignOut = async () => {
        await signOut();
        navigate("/login");
    };

    return (
        <div className="min-h-screen bg-[#0A0A10] text-white">
            {/* Top nav */}
            <header className="h-14 border-b border-zinc-800/50 bg-[#0C0C14]/80 backdrop-blur-md flex items-center px-6 sticky top-0 z-50">
                <button
                    onClick={() => navigate("/")}
                    className="flex items-center gap-2.5 hover:opacity-80 transition-opacity"
                >
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-purple-700 flex items-center justify-center">
                        <Anvil className="w-4.5 h-4.5 text-white" />
                    </div>
                    <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
                        Kith Foundry
                    </span>
                </button>

                <div className="flex-1" />

                {user && (
                    <div className="flex items-center gap-1">
                        <Link
                            to="/ideation/saved"
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                                onSavedIdeas
                                    ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                                    : "text-zinc-400 hover:text-white hover:bg-zinc-800"
                            }`}
                            title="Saved Ideas"
                        >
                            <Bookmark className="w-4 h-4" />
                            <span className="hidden sm:inline">Saved Ideas</span>
                        </Link>
                        <Link
                            to="/profile"
                            className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors text-sm"
                            title="Profile & Settings"
                        >
                            <UserCircle className="w-4 h-4" />
                            <span className="hidden sm:inline">{user.email}</span>
                        </Link>
                        <button
                            onClick={handleSignOut}
                            className="p-2 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-white transition-colors"
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
