import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { motion } from "framer-motion";
import { Plus, FolderOpen, Clock, ChevronRight, Sparkles } from "lucide-react";
import { getApiBaseUrl } from "../../lib/runtimeConfig";

interface ProjectSummary {
    id: string;
    name: string;
    description: string | null;
    status: string;
    created_at: string;
    updated_at: string;
}

export default function DashboardPage() {
    const { getAccessToken } = useAuth();
    const navigate = useNavigate();
    const [projects, setProjects] = useState<ProjectSummary[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects`, {
                headers: { Authorization: `Bearer ${token}` },
            });
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

    const statusColors: Record<string, string> = {
        ideation: "bg-amber-500/10 text-amber-400 border-amber-500/20",
        csuite_pending: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        csuite_running: "bg-blue-500/10 text-blue-400 border-blue-500/20",
        csuite_complete: "bg-green-500/10 text-green-400 border-green-500/20",
        building: "bg-purple-500/10 text-purple-400 border-purple-500/20",
        deployed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
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

    return (
        <div className="max-w-6xl mx-auto px-6 py-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-10">
                <div>
                    <h1 className="text-3xl font-bold text-white">Your Projects</h1>
                    <p className="text-zinc-500 mt-1">Build, iterate, and deploy</p>
                </div>
                <button
                    onClick={() => navigate("/ideation")}
                    className="flex items-center gap-2 h-11 px-6 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20"
                >
                    <Plus className="w-4 h-4" />
                    New Project
                </button>
            </div>

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
                    <div className="w-20 h-20 rounded-2xl bg-[#12121A] border border-zinc-800/50 flex items-center justify-center mb-6">
                        <Sparkles className="w-8 h-8 text-purple-500/50" />
                    </div>
                    <h2 className="text-xl font-semibold text-white mb-2">Start your first project</h2>
                    <p className="text-zinc-500 max-w-sm mb-8">
                        Describe your idea and let our AI C-Suite validate, design, and build it for you.
                    </p>
                    <button
                        onClick={() => navigate("/ideation")}
                        className="flex items-center gap-2 h-11 px-8 rounded-xl bg-gradient-to-r from-purple-600 to-purple-500 text-white font-medium hover:from-purple-500 hover:to-purple-400 transition-all shadow-lg shadow-purple-500/20"
                    >
                        <Plus className="w-4 h-4" />
                        New Project
                    </button>
                </motion.div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {projects.map((project, i) => (
                        <motion.div
                            key={project.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            onClick={() => {
                                if (project.status === "ideation" || project.status === "csuite_pending") {
                                    navigate(`/csuite/${project.id}`);
                                } else {
                                    navigate(`/project/${project.id}`);
                                }
                            }}
                            className="group bg-[#12121A] border border-zinc-800/50 rounded-xl p-5 hover:border-purple-500/30 hover:bg-[#14141E] transition-all cursor-pointer"
                        >
                            <div className="flex items-start justify-between mb-3">
                                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500/20 to-indigo-500/20 flex items-center justify-center">
                                    <FolderOpen className="w-5 h-5 text-purple-400" />
                                </div>
                                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${statusColors[project.status] || statusColors.ideation}`}>
                                    {statusLabels[project.status] || project.status}
                                </span>
                            </div>
                            <h3 className="text-white font-semibold mb-1 group-hover:text-purple-300 transition-colors truncate">
                                {project.name}
                            </h3>
                            <p className="text-zinc-500 text-sm line-clamp-2 mb-4 min-h-[2.5rem]">
                                {project.description || "No description"}
                            </p>
                            <div className="flex items-center justify-between text-xs text-zinc-600">
                                <div className="flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {formatDate(project.updated_at)}
                                </div>
                                <ChevronRight className="w-4 h-4 text-zinc-700 group-hover:text-purple-400 transition-colors" />
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
