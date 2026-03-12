import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { useApiFetch } from "../../hooks/useApiFetch";
import { motion } from "framer-motion";
import { Plus, FolderOpen, Clock, ChevronRight, Sparkles, Trash2, Bookmark } from "lucide-react";

interface ProjectSummary {
    id: string;
    name: string;
    description: string | null;
    status: string;
    created_at: string;
    updated_at: string;
}

export default function DashboardPage() {
    const { loading: authLoading } = useAuth();
    const { theme } = useTheme();
    const apiFetch = useApiFetch();
    const navigate = useNavigate();
    const [projects, setProjects] = useState<ProjectSummary[]>([]);
    const [loading, setLoading] = useState(true);
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [hoveredId, setHoveredId] = useState<string | null>(null);
    const [savedCount, setSavedCount] = useState<number | null>(null);

    useEffect(() => {
        if (authLoading) return;
        const fetchProjects = async () => {
            try {
                const resp = await apiFetch("/api/v1/projects");
                if (resp.ok) {
                    const data = await resp.json();
                    setProjects(data.projects || []);
                }
            } catch (e) {
                console.error("Failed to fetch projects:", e);
            } finally {
                setLoading(false);
            }
        };
        const fetchSavedCount = async () => {
            try {
                const resp = await apiFetch("/api/v1/ideation/saved");
                if (resp.ok) {
                    const data = await resp.json();
                    setSavedCount((data.saved_ideas || []).length);
                }
            } catch {}
        };
        fetchProjects();
        fetchSavedCount();
    }, [authLoading, apiFetch]);

    const handleDelete = async (e: React.MouseEvent, project: ProjectSummary) => {
        e.stopPropagation();
        if (!window.confirm(`Delete "${project.name}"? This cannot be undone.`)) return;
        setDeletingId(project.id);
        try {
            await apiFetch(`/api/v1/projects/${project.id}`, { method: "DELETE" });
            setProjects(prev => prev.filter(p => p.id !== project.id));
        } catch (e) {
            console.error("Failed to delete project:", e);
        } finally {
            setDeletingId(null);
        }
    };

    const isDark = theme === "dark";

    const statusColors: Record<string, string> = {
        ideation: isDark ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-amber-50 text-amber-700 border-amber-300/40",
        csuite_pending: isDark ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-blue-50 text-blue-700 border-blue-300/40",
        csuite_running: isDark ? "bg-blue-500/10 text-blue-400 border-blue-500/20" : "bg-blue-50 text-blue-700 border-blue-300/40",
        csuite_complete: isDark ? "bg-green-500/10 text-green-400 border-green-500/20" : "bg-green-50 text-green-700 border-green-300/40",
        building: isDark ? "bg-purple-500/10 text-purple-400 border-purple-500/20" : "bg-purple-50 text-purple-700 border-purple-300/40",
        deployed: isDark ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-emerald-50 text-emerald-700 border-emerald-300/40",
    };

    const statusLabels: Record<string, string> = {
        ideation: "Ideation",
        csuite_pending: "C-Suite Pending",
        csuite_running: "C-Suite Running",
        csuite_complete: "C-Suite Complete",
        building: "Building",
        deployed: "Deployed",
    };

    const formatDate = (dateStr: string) => {
        const d = new Date(dateStr);
        const now = new Date();
        const diff = now.getTime() - d.getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        if (days < 7) return `${days}d ago`;
        return d.toLocaleDateString();
    };

    const headingClass = isDark ? "text-white" : "text-zinc-900";
    const bodyClass = isDark ? "text-zinc-500" : "text-zinc-600";
    const panelClass = isDark
        ? "bg-[#12121A] border border-zinc-800/50"
        : "bg-white border border-zinc-200 shadow-sm shadow-zinc-200/70";
    const secondaryButtonClass = isDark
        ? "border-zinc-700 bg-zinc-800/50 text-zinc-300 hover:bg-zinc-700 hover:text-white"
        : "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-100 hover:text-zinc-900";

    return (
        <div className="max-w-6xl mx-auto px-6 py-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h1 className={`text-3xl font-bold ${headingClass}`}>Your Projects</h1>
                    <p className={`mt-1 ${bodyClass}`}>Build, iterate, and deploy</p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => navigate("/ideation/saved")}
                        className={`flex items-center gap-2 h-11 px-5 rounded-xl border font-medium transition-all ${secondaryButtonClass}`}
                    >
                        <Bookmark className="w-4 h-4 text-amber-400" />
                        Saved Ideas
                        {savedCount !== null && savedCount > 0 && (
                            <span className={`text-xs px-1.5 py-0.5 rounded-full font-bold ${isDark ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" : "bg-amber-100 text-amber-700 border border-amber-300/50"}`}>
                                {savedCount}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => navigate("/ideation")}
                        className="flex items-center gap-2 h-11 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20"
                    >
                        <Plus className="w-4 h-4" />
                        New Project
                    </button>
                </div>
            </div>

            {/* Saved ideas ready-to-build banner */}
            {savedCount !== null && savedCount > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => navigate("/ideation/saved")}
                    className={`mb-6 flex items-center justify-between gap-4 px-5 py-3.5 rounded-xl border cursor-pointer transition-colors ${isDark ? "border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10" : "border-amber-300/40 bg-amber-50 hover:bg-amber-100"}`}
                >
                    <div className="flex items-center gap-3">
                        <Bookmark className={`w-4 h-4 shrink-0 ${isDark ? "text-amber-400" : "text-amber-600"}`} />
                        <p className={`text-sm ${isDark ? "text-amber-300/90" : "text-amber-800"}`}>
                            You have <span className="font-bold">{savedCount}</span> saved idea{savedCount !== 1 ? "s" : ""} ready to build.
                        </p>
                    </div>
                    <span className={`text-xs font-medium whitespace-nowrap flex items-center gap-1 ${isDark ? "text-amber-400" : "text-amber-700"}`}>
                        View &amp; Build <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                </motion.div>
            )}

            {/* Projects grid */}
            {loading ? (
                    <div className="flex items-center justify-center py-32">
                    <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                </div>
            ) : projects.length === 0 ? (
                /* Empty state */
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center justify-center py-32 text-center"
                >
                    <div className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-6 ${isDark ? "bg-[#12121A] border border-zinc-800/50" : "bg-zinc-100 border border-zinc-200"}`}>
                        <Sparkles className="w-8 h-8 text-purple-500/50" />
                    </div>
                    <h2 className={`text-xl font-semibold mb-2 ${headingClass}`}>Start your first project</h2>
                    <p className={`max-w-sm mb-8 ${bodyClass}`}>
                        Describe your idea and let our AI C-Suite validate, design, and build it for you.
                    </p>
                    <button
                        onClick={() => navigate("/ideation")}
                        className="flex items-center gap-2 h-11 px-8 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20"
                    >
                        <Plus className="w-4 h-4" />
                        New Project
                    </button>
                    {savedCount !== null && savedCount > 0 && (
                        <button
                            onClick={() => navigate("/ideation/saved")}
                            className={`flex items-center gap-2 h-11 px-6 rounded-xl border font-medium transition-all ${isDark ? "border-amber-500/20 bg-amber-500/5 text-amber-300 hover:bg-amber-500/10" : "border-amber-300/40 bg-amber-50 text-amber-700 hover:bg-amber-100"}`}
                        >
                            <Bookmark className="w-4 h-4" />
                            Build a Saved Idea ({savedCount})
                        </button>
                    )}
                </motion.div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map((project, i) => (
                        <motion.div
                            key={project.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            onMouseEnter={() => setHoveredId(project.id)}
                            onMouseLeave={() => setHoveredId(null)}
                            onClick={() => {
                                if (deletingId === project.id) return;
                                if (project.status === "ideation" || project.status === "csuite_pending") {
                                    navigate(`/csuite/${project.id}`);
                                } else {
                                    navigate(`/project/${project.id}`);
                                }
                            }}
                            className={`relative rounded-xl p-5 transition-all cursor-pointer ${panelClass} ${isDark ? "hover:border-purple-500/30 hover:bg-[#14141E]" : "hover:border-purple-300 hover:bg-zinc-50"}`}
                        >
                            {/* Delete button */}
                            {hoveredId === project.id && (
                                <button
                                    onClick={(e) => handleDelete(e, project)}
                                    disabled={deletingId === project.id}
                                    className="absolute top-3 right-3 w-7 h-7 rounded-lg flex items-center justify-center bg-red-500/10 hover:bg-red-500/25 border border-red-500/20 text-red-400 disabled:opacity-50 z-10"
                                    title="Delete project"
                                >
                                    <Trash2 className="w-3.5 h-3.5" />
                                </button>
                            )}

                            <div className="flex items-start justify-between mb-3">
                                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-indigo-500/20 flex items-center justify-center">
                                    <FolderOpen className="w-5 h-5 text-purple-400" />
                                </div>
                                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${hoveredId === project.id ? "mr-8" : ""} ${statusColors[project.status] || statusColors.ideation}`}>
                                    {statusLabels[project.status] || project.status}
                                </span>
                            </div>
                            <h3 className={`font-semibold mb-1 transition-colors truncate ${headingClass} ${isDark ? "group-hover:text-purple-300" : "group-hover:text-purple-700"}`}>
                                {project.name}
                            </h3>
                            <p className={`text-sm line-clamp-2 mb-4 min-h-[2.5rem] ${bodyClass}`}>
                                {project.description || "No description"}
                            </p>
                            <div className={`flex items-center justify-between text-xs ${isDark ? "text-zinc-600" : "text-zinc-500"}`}>
                                <div className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatDate(project.updated_at)}
                                </div>
                                <ChevronRight className={`w-4 h-4 transition-colors ${isDark ? "text-zinc-700 group-hover:text-purple-400" : "text-zinc-400 group-hover:text-purple-600"}`} />
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
