import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import {
    Palette,
    Monitor,
    Smartphone,
    Tablet,
    Loader2,
    RefreshCw,
    Check,
    Code2,
    ArrowLeft,
    LayoutGrid,
} from "lucide-react";

interface Mockup {
    id: string;
    name: string;
    description: string;
    priority: "high" | "medium" | "low";
    status: "pending" | "generating" | "complete" | "approved" | "revision_requested" | "error";
    component_code: string | null;
    revision_notes: string | null;
    created_at: string;
}

const PRIORITY_COLORS: Record<string, string> = {
    high: "text-red-300 bg-red-500/10 border-red-500/30",
    medium: "text-amber-300 bg-amber-500/10 border-amber-500/30",
    low: "text-sky-300 bg-sky-500/10 border-sky-500/30",
};

export default function DesignStudioPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const { getAccessToken } = useAuth();

    const [mockups, setMockups] = useState<Mockup[]>([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [selectedMockup, setSelectedMockup] = useState<string | null>(null);
    const [previewDevice, setPreviewDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");
    const [showCode, setShowCode] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const pollRef = useRef<number | null>(null);

    const fetchMockups = async () => {
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (resp.ok) {
                const data = await resp.json();
                const next = data.mockups || [];
                setMockups(next);
                if (!selectedMockup && next.length > 0) {
                    setSelectedMockup(next[0].id);
                }
            }
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMockups();
        return () => {
            if (pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        };
    }, [projectId]);

    const startPolling = (token: string) => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
        }
        pollRef.current = window.setInterval(async () => {
            try {
                const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!resp.ok) return;
                const data = await resp.json();
                const next = data.mockups || [];
                setMockups(next);

                const done = next.length > 0 && next.every((m: Mockup) => m.status !== "generating" && m.status !== "pending");
                if (done) {
                    setGenerating(false);
                    clearInterval(pollRef.current!);
                    pollRef.current = null;
                }
            } catch {
                // ignore polling jitter
            }
        }, 2500);
    };

    const handleGenerateAll = async () => {
        setGenerating(true);
        setError(null);
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/generate-all`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) throw new Error("Failed to start design generation");
            startPolling(token || "");
        } catch (e: any) {
            setError(e.message);
            setGenerating(false);
        }
    };

    const handleApprove = async (mockupId: string) => {
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/approve`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!resp.ok) throw new Error("Failed to approve mockup");
            setMockups(prev => prev.map(m => (m.id === mockupId ? { ...m, status: "approved" } : m)));
        } catch (e: any) {
            setError(e.message);
        }
    };

    const handleRequestRevision = async (mockupId: string) => {
        const notes = prompt("What changes would you like to see?");
        if (!notes) return;
        try {
            const token = await getAccessToken();
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/revise`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`,
                },
                body: JSON.stringify({ notes }),
            });
            if (!resp.ok) throw new Error("Revision request failed");
            fetchMockups();
        } catch (e: any) {
            setError(e.message);
        }
    };

    const currentMockup = mockups.find(m => m.id === selectedMockup);
    const approvedCount = mockups.filter(m => m.status === "approved").length;
    const generatedCount = mockups.filter(m => m.status === "complete" || m.status === "approved").length;

    const deviceContainerClass: Record<string, string> = {
        desktop: "w-full max-w-[1200px]",
        tablet: "w-full max-w-[860px]",
        mobile: "w-full max-w-[430px]",
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            </div>
        );
    }

    return (
        <div className="h-[calc(100vh-65px)] bg-[#070913] text-zinc-100 flex overflow-hidden">
            <aside className="w-[330px] border-r border-zinc-800/60 bg-gradient-to-b from-[#101426] to-[#0B0E1B] flex flex-col">
                <div className="p-4 border-b border-zinc-800/60 space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Palette className="w-4 h-4 text-purple-300" />
                            <h2 className="text-sm font-bold">Design Studio</h2>
                        </div>
                        <button
                            onClick={() => navigate(`/project/${projectId}`)}
                            className="h-8 px-2.5 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs"
                            title="Close and return to project"
                        >
                            Close
                        </button>
                    </div>

                    <div className="flex gap-2">
                        <button
                            onClick={() => navigate(`/project/${projectId}`)}
                            className="flex-1 h-8 rounded-md bg-zinc-800/70 hover:bg-zinc-700 text-xs flex items-center justify-center gap-1.5"
                        >
                            <ArrowLeft className="w-3.5 h-3.5" /> Project
                        </button>
                        <button
                            onClick={() => navigate("/")}
                            className="flex-1 h-8 rounded-md bg-zinc-800/70 hover:bg-zinc-700 text-xs flex items-center justify-center gap-1.5"
                        >
                            <LayoutGrid className="w-3.5 h-3.5" /> All Projects
                        </button>
                    </div>

                    <button
                        onClick={handleGenerateAll}
                        disabled={generating}
                        className="w-full h-9 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-sm font-medium disabled:opacity-60 flex items-center justify-center gap-2"
                    >
                        {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        {mockups.length === 0 ? "Generate Design Mockups" : "Regenerate All"}
                    </button>

                    <div className="text-xs text-zinc-400">
                        {approvedCount} approved · {generatedCount}/{mockups.length || 0} generated
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {mockups.length === 0 ? (
                        <div className="text-center text-zinc-500 text-sm py-10">
                            <Palette className="w-10 h-10 mx-auto mb-3 text-zinc-700" />
                            No mockups yet. Generate to begin.
                        </div>
                    ) : (
                        mockups.map(mockup => {
                            const isSelected = selectedMockup === mockup.id;
                            return (
                                <button
                                    key={mockup.id}
                                    onClick={() => {
                                        setSelectedMockup(mockup.id);
                                        setShowCode(false);
                                    }}
                                    className={`w-full text-left p-3 rounded-lg border transition-all ${isSelected
                                        ? "border-purple-500/60 bg-purple-500/10"
                                        : "border-zinc-800/50 bg-zinc-900/40 hover:bg-zinc-800/40"
                                        }`}
                                >
                                    <div className="flex items-center justify-between gap-2 mb-1">
                                        <span className="text-sm font-semibold text-white truncate">{mockup.name}</span>
                                        <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[mockup.priority] || PRIORITY_COLORS.medium}`}>
                                            {mockup.priority}
                                        </span>
                                    </div>
                                    <p className="text-xs text-zinc-400 line-clamp-2 mb-1.5">{mockup.description}</p>
                                    <p className={`text-[11px] capitalize ${mockup.status === "approved" ? "text-emerald-400 font-semibold" : "text-zinc-500"}`}>
                                        {mockup.status === "approved" ? "✓ Approved" : mockup.status.replace("_", " ")}
                                    </p>
                                </button>
                            );
                        })
                    )}
                </div>
            </aside>

            <main className="flex-1 flex flex-col min-w-0 bg-[#090C18]">
                <div className="h-14 border-b border-zinc-800/60 px-5 flex items-center justify-between bg-[#0A1020]">
                    <div className="min-w-0">
                        <h3 className="text-sm font-bold text-white truncate">{currentMockup?.name || "Select a mockup"}</h3>
                        <p className="text-xs text-zinc-400 truncate">{currentMockup?.description || "Choose a design from the left panel"}</p>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1 bg-zinc-800/60 rounded-lg p-1">
                            <button onClick={() => setPreviewDevice("desktop")} className={`p-1.5 rounded ${previewDevice === "desktop" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}><Monitor className="w-4 h-4" /></button>
                            <button onClick={() => setPreviewDevice("tablet")} className={`p-1.5 rounded ${previewDevice === "tablet" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}><Tablet className="w-4 h-4" /></button>
                            <button onClick={() => setPreviewDevice("mobile")} className={`p-1.5 rounded ${previewDevice === "mobile" ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}><Smartphone className="w-4 h-4" /></button>
                        </div>

                        {currentMockup && currentMockup.status === "approved" && (
                            <>
                                <span className="h-8 px-3 rounded-md bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-1.5">
                                    <Check className="w-3.5 h-3.5" /> Approved
                                </span>
                                <button
                                    onClick={() => handleRequestRevision(currentMockup.id)}
                                    className="h-8 px-3 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs"
                                >
                                    Revise
                                </button>
                            </>
                        )}
                        {currentMockup && currentMockup.status === "complete" && (
                            <>
                                <button
                                    onClick={() => handleRequestRevision(currentMockup.id)}
                                    className="h-8 px-3 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs"
                                >
                                    Revise
                                </button>
                                <button
                                    onClick={() => handleApprove(currentMockup.id)}
                                    className="h-8 px-3 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs flex items-center gap-1.5"
                                >
                                    <Check className="w-3.5 h-3.5" /> Approve
                                </button>
                            </>
                        )}
                    </div>
                </div>

                <div className="flex-1 overflow-auto p-5">
                    {!currentMockup ? (
                        <div className="h-full grid place-items-center text-zinc-500 text-sm">Select a mockup to preview it here.</div>
                    ) : currentMockup.status === "generating" ? (
                        <div className="h-full grid place-items-center text-center">
                            <div>
                                <Loader2 className="w-10 h-10 text-purple-400 animate-spin mx-auto mb-3" />
                                <p className="text-zinc-300 text-sm">Generating {currentMockup.name}...</p>
                            </div>
                        </div>
                    ) : currentMockup.component_code ? (
                        <div className="space-y-4">
                            <div className={`${deviceContainerClass[previewDevice]} mx-auto rounded-xl border border-zinc-700 bg-zinc-950 overflow-hidden shadow-2xl`}>
                                <div className="h-8 bg-zinc-900 border-b border-zinc-700 flex items-center px-3 gap-2">
                                    <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                                    <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                                    <span className="text-[11px] text-zinc-400 ml-2">{currentMockup.name}</span>
                                </div>
                                <iframe
                                    title={`Mockup Preview ${currentMockup.name}`}
                                    srcDoc={currentMockup.component_code}
                                    className="w-full h-[72vh] bg-white"
                                    sandbox="allow-same-origin"
                                />
                            </div>

                            <div className="max-w-[1200px] mx-auto">
                                <button
                                    onClick={() => setShowCode(v => !v)}
                                    className="h-9 px-3 rounded-md border border-zinc-700 text-zinc-300 hover:bg-zinc-800 text-xs flex items-center gap-1.5"
                                >
                                    <Code2 className="w-3.5 h-3.5" />
                                    {showCode ? "Hide Component Code" : "View Component Code"}
                                </button>
                                {showCode && (
                                    <pre className="mt-3 max-h-72 overflow-auto rounded-xl border border-zinc-800 bg-[#070B16] p-4 text-xs text-zinc-300 font-mono whitespace-pre-wrap">
                                        {currentMockup.component_code}
                                    </pre>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="h-full grid place-items-center text-zinc-500 text-sm">Mockup not generated yet.</div>
                    )}
                </div>
            </main>

            {error && (
                <div className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-sm">
                    {error}
                </div>
            )}
        </div>
    );
}
