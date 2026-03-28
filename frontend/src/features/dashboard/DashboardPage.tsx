import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useApiFetch } from "../../hooks/useApiFetch";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils/cn";
import { pageTransition, staggerContainer, cardEntrance } from "../../lib/utils/motion";
import { StatusPill } from "../../components/ui";

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
    const apiFetch = useApiFetch();
    const apiFetchRef = useRef(apiFetch);
    apiFetchRef.current = apiFetch;
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
                const resp = await apiFetchRef.current("/api/v1/projects");
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
                const resp = await apiFetchRef.current("/api/v1/ideation/saved");
                if (resp.ok) {
                    const data = await resp.json();
                    setSavedCount((data.saved_ideas || []).length);
                }
            } catch {}
        };
        fetchProjects();
        fetchSavedCount();
    }, [authLoading]);

    const handleDelete = async (e: React.MouseEvent, project: ProjectSummary) => {
        e.stopPropagation();
        if (!window.confirm(`Delete "${project.name}"? This cannot be undone.`)) return;
        setDeletingId(project.id);
        try {
            await apiFetchRef.current(`/api/v1/projects/${project.id}`, { method: "DELETE" });
            setProjects(prev => prev.filter(p => p.id !== project.id));
        } catch (e) {
            console.error("Failed to delete project:", e);
        } finally {
            setDeletingId(null);
        }
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
        <motion.div
            {...pageTransition}
            className="max-w-6xl mx-auto px-6 py-10"
        >
            {/* Page Header */}
            <div className="flex items-start justify-between mb-8 gap-6">
                <div>
                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-2">
                        Kith Foundry
                    </p>
                    <h1
                        className="text-4xl sm:text-5xl md:text-7xl font-black uppercase tracking-tighter leading-none text-on-surface"
                        style={{ letterSpacing: "-0.05em" }}
                    >
                        Projects
                    </h1>
                    <p className="text-tertiary text-sm max-w-2xl leading-relaxed mt-3">
                        Build, iterate, and deploy your ideas with AI-powered tools.
                    </p>
                </div>
                <div className="flex items-center gap-3 shrink-0 pt-1">
                    <button
                        onClick={() => navigate("/app/ideation/saved")}
                        className={cn(
                            "flex items-center gap-2 h-10 px-5 rounded-full border border-outline-variant",
                            "text-on-surface font-black uppercase tracking-widest text-[11px]",
                            "hover:bg-surface-container transition-colors"
                        )}
                    >
                        <span className="material-symbols-outlined text-[16px] text-secondary">checklist</span>
                        Saved Ideas
                        {savedCount !== null && savedCount > 0 && (
                            <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary-container text-on-primary-container text-[10px] font-black">
                                {savedCount}
                            </span>
                        )}
                    </button>
                    <button
                        onClick={() => navigate("/app/ideation")}
                        className={cn(
                            "flex items-center gap-2 h-10 px-6 rounded-full",
                            "bg-primary-container text-on-primary-container",
                            "font-black uppercase tracking-widest text-[11px]",
                            "hover:opacity-90 transition-opacity"
                        )}
                    >
                        <span className="material-symbols-outlined text-[16px]">add</span>
                        New Project
                    </button>
                </div>
            </div>

            {/* Saved ideas ready-to-build banner */}
            {savedCount !== null && savedCount > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: -8 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={() => navigate("/app/ideation/saved")}
                    className={cn(
                        "mb-6 flex items-center justify-between gap-4 px-5 py-3.5",
                        "rounded-[var(--radius-module)] border border-outline-variant",
                        "bg-surface-container cursor-pointer hover:bg-surface transition-colors"
                    )}
                >
                    <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-[18px] text-secondary shrink-0">checklist</span>
                        <p className="text-sm text-on-surface leading-snug">
                            You have{" "}
                            <span className="font-black">{savedCount}</span>{" "}
                            saved idea{savedCount !== 1 ? "s" : ""} ready to build.
                        </p>
                    </div>
                    <span className="text-[10px] font-black uppercase tracking-widest text-secondary whitespace-nowrap flex items-center gap-1">
                        View &amp; Build
                        <span className="material-symbols-outlined text-[14px]">chevron_right</span>
                    </span>
                </motion.div>
            )}

            {/* Loading state */}
            {loading ? (
                <div className="flex items-center justify-center py-32">
                    <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
            ) : projects.length === 0 ? (
                /* Empty state */
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex flex-col items-center justify-center py-32 text-center"
                >
                    <div className="w-20 h-20 rounded-[var(--radius-module)] steel-gradient ghost-border flex items-center justify-center mb-6">
                        <span className="material-symbols-outlined text-[40px] text-tertiary">folder_open</span>
                    </div>
                    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-secondary mb-3">
                        No Projects Yet
                    </p>
                    <h2
                        className="text-2xl font-black uppercase leading-none text-on-surface mb-3"
                        style={{ letterSpacing: "-0.05em" }}
                    >
                        Start Your First Project
                    </h2>
                    <p className="text-tertiary text-sm max-w-sm leading-relaxed mb-8">
                        Describe your idea and let our AI C-Suite validate, design, and build it for you.
                    </p>
                    <div className="flex flex-col items-center gap-3">
                        <button
                            onClick={() => navigate("/app/ideation")}
                            className={cn(
                                "flex items-center gap-2 h-11 px-8 rounded-full",
                                "bg-primary-container text-on-primary-container",
                                "font-black uppercase tracking-widest text-[11px]",
                                "hover:opacity-90 transition-opacity"
                            )}
                        >
                            <span className="material-symbols-outlined text-[16px]">add</span>
                            New Project
                        </button>
                        {savedCount !== null && savedCount > 0 && (
                            <button
                                onClick={() => navigate("/app/ideation/saved")}
                                className={cn(
                                    "flex items-center gap-2 h-11 px-6 rounded-full border border-outline-variant",
                                    "text-on-surface font-black uppercase tracking-widest text-[11px]",
                                    "hover:bg-surface-container transition-colors"
                                )}
                            >
                                <span className="material-symbols-outlined text-[16px] text-secondary">checklist</span>
                                Build a Saved Idea ({savedCount})
                            </button>
                        )}
                    </div>
                </motion.div>
            ) : (
                /* Projects grid */
                <motion.div
                    variants={staggerContainer}
                    initial="hidden"
                    animate="visible"
                    className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6"
                >
                    {projects.map((project) => (
                        <motion.div
                            key={project.id}
                            variants={cardEntrance}
                            onMouseEnter={() => setHoveredId(project.id)}
                            onMouseLeave={() => setHoveredId(null)}
                            onClick={() => {
                                if (deletingId === project.id) return;
                                const isCsuiteComplete = project.status === "csuite_complete";
                                navigate(isCsuiteComplete ? `/app/projects/${project.id}` : `/app/projects/${project.id}/executive`);
                            }}
                            className={cn(
                                "relative steel-gradient ghost-border rounded-[var(--radius-module)] p-6",
                                "cursor-pointer transition-all hover:border-outline hover:bg-surface-container"
                            )}
                        >
                            {/* Delete button */}
                            {hoveredId === project.id && (
                                <button
                                    onClick={(e) => handleDelete(e, project)}
                                    disabled={deletingId === project.id}
                                    title="Delete project"
                                    className={cn(
                                        "absolute top-4 right-4 w-8 h-8 rounded-full flex items-center justify-center z-10",
                                        "text-error hover:bg-error/10 border border-error/20 transition-colors",
                                        "disabled:opacity-50"
                                    )}
                                >
                                    <span className="material-symbols-outlined text-[16px]">delete</span>
                                </button>
                            )}

                            {/* Card top row */}
                            <div className="flex items-start justify-between mb-4 gap-2">
                                <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center shrink-0">
                                    <span className="material-symbols-outlined text-[20px] text-on-primary-container">folder_open</span>
                                </div>
                                <div className={cn(hoveredId === project.id ? "mr-8" : "")}>
                                    <StatusPill status={project.status} size="sm" />
                                </div>
                            </div>

                            {/* Project name */}
                            <h3 className="font-black uppercase tracking-tight text-on-surface truncate mb-1 text-sm">
                                {project.name}
                            </h3>

                            {/* Description */}
                            <p className="text-tertiary text-sm leading-relaxed line-clamp-2 min-h-[2.5rem] mb-4">
                                {project.description || "No description"}
                            </p>

                            {/* Footer */}
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-1 text-tertiary text-[11px] font-black uppercase tracking-widest">
                                    <span className="material-symbols-outlined text-[14px]">schedule</span>
                                    {formatDate(project.updated_at)}
                                </div>
                                <span className="material-symbols-outlined text-[18px] text-tertiary">chevron_right</span>
                            </div>
                        </motion.div>
                    ))}
                </motion.div>
            )}
        </motion.div>
    );
}
