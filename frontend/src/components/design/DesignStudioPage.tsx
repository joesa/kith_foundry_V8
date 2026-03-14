import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { motion, AnimatePresence } from "framer-motion";
import {
    Palette,
    Monitor,
    Smartphone,
    Tablet,
    Loader2,
    RefreshCw,
    Check,
    CheckCheck,
    Trash2,
    Sparkles,
    Plus,
    X,
    ChevronRight,
    ChevronLeft,
    Compass,
    Zap,
    Eye,
    Square,
    StopCircle,
    MessageSquare,
    Maximize2,
    ArrowLeft,
    LayoutGrid,
    Rocket,
    ImageIcon,
    Search,
    Sun,
    Moon,
    Settings2,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════════════════════
 * TYPES
 * ═══════════════════════════════════════════════════════════════════════ */

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

interface Direction {
    id: string;
    name: string;
    description: string;
    palette: string[];
    style_keywords: string[];
    layout_approach: string;
    html_swatch: string;
}

type Phase = "discovering" | "discovery" | "generating" | "gallery";

const PRIORITY_COLORS_DARK: Record<string, string> = {
    high: "text-red-300 bg-red-500/10 border-red-500/30",
    medium: "text-amber-300 bg-amber-500/10 border-amber-500/30",
    low: "text-sky-300 bg-sky-500/10 border-sky-500/30",
};
const PRIORITY_COLORS_LIGHT: Record<string, string> = {
    high: "text-red-700 bg-red-50 border-red-300/50",
    medium: "text-amber-700 bg-amber-50 border-amber-300/50",
    low: "text-sky-700 bg-sky-50 border-sky-300/50",
};

const DIRECTION_SWATCH_SIZE = { width: 380, height: 240 };
const MOCKUP_PREVIEW_SIZE = { width: 1200, height: 900 };

function ScaledHtmlPreview({
    title,
    html,
    baseWidth,
    baseHeight,
    className = "",
}: {
    title: string;
    html: string;
    baseWidth: number;
    baseHeight: number;
    className?: string;
}) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

    useEffect(() => {
        const node = containerRef.current;
        if (!node) return;

        const updateSize = () => {
            setContainerSize({ width: node.clientWidth, height: node.clientHeight });
        };

        updateSize();

        if (typeof ResizeObserver === "undefined") {
            window.addEventListener("resize", updateSize);
            return () => window.removeEventListener("resize", updateSize);
        }

        const observer = new ResizeObserver((entries) => {
            const entry = entries[0];
            if (!entry) return;
            setContainerSize({
                width: entry.contentRect.width,
                height: entry.contentRect.height,
            });
        });

        observer.observe(node);
        return () => observer.disconnect();
    }, []);

    const scale =
        containerSize.width > 0 && containerSize.height > 0
            ? Math.min(containerSize.width / baseWidth, containerSize.height / baseHeight, 1)
            : 0;

    return (
        <div ref={containerRef} className={`relative overflow-hidden ${className}`}>
            {scale > 0 && (
                <div
                    className="absolute left-1/2 top-1/2"
                    style={{
                        width: baseWidth * scale,
                        height: baseHeight * scale,
                        transform: "translate(-50%, -50%)",
                    }}
                >
                    <iframe
                        id="generated-mockup-frame"
                        title={title}
                        srcDoc={html}
                        className="pointer-events-none border-0"
                        style={{
                            width: baseWidth,
                            height: baseHeight,
                            transform: `scale(${scale})`,
                            transformOrigin: "top left",
                        }}
                        sandbox="allow-scripts"
                    />
                </div>
            )}
        </div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * DIRECTION PICKER MODAL
 * ═══════════════════════════════════════════════════════════════════════ */

function DirectionPickerModal({
    directions,
    loadingDirections,
    onPick,
    onDescribe,
    onClose,
    onStopLoading,
}: {
    directions: Direction[];
    loadingDirections: boolean;
    onPick: (d: Direction, images: string[]) => void;
    onDescribe: (text: string, images: string[]) => void;
    onClose: () => void;
    onStopLoading: () => void;
}) {
    const [customText, setCustomText] = useState("");
    const [referenceImages, setReferenceImages] = useState<{ id: string; url: string; file: File }[]>([]);
    const [isProcessing, setIsProcessing] = useState(false);

    const handleFiles = async (files: FileList | null) => {
        if (!files) return;
        const newImages = Array.from(files).filter(f => f.type.startsWith("image/"));
        if (referenceImages.length + newImages.length > 20) {
            alert("Maximum of 20 reference images allowed.");
            return;
        }

        setIsProcessing(true);
        const processed = await Promise.all(
            newImages.map((file) => new Promise<{ id: string; url: string; file: File }>((resolve) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const img = new Image();
                    img.onload = () => {
                        const canvas = document.createElement("canvas");
                        let width = img.width;
                        let height = img.height;
                        const maxEdge = 800; // compress reference images heavily
                        if (width > height) {
                            if (width > maxEdge) {
                                height = Math.round((height * maxEdge) / width);
                                width = maxEdge;
                            }
                        } else {
                            if (height > maxEdge) {
                                width = Math.round((width * maxEdge) / height);
                                height = maxEdge;
                            }
                        }
                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext("2d");
                        ctx?.drawImage(img, 0, 0, width, height);
                        const url = canvas.toDataURL("image/jpeg", 0.7);
                        resolve({ id: Math.random().toString(36).substring(7), url, file });
                    };
                    img.src = e.target?.result as string;
                };
                reader.readAsDataURL(file);
            }))
        );

        setReferenceImages(prev => [...prev, ...processed]);
        setIsProcessing(false);
    };

    const handleRemoveImage = (id: string) => {
        setReferenceImages(prev => prev.filter(img => img.id !== id));
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl"
            >
                {/* Header */}
                <div className="p-5 border-b border-[var(--kf-border)]/60 flex items-center justify-between">
                    <div>
                        <h2 className="text-lg font-bold text-[var(--kf-text)] flex items-center gap-2">
                            <Compass className="w-5 h-5 text-purple-400" />
                            New Design Direction
                        </h2>
                        <p className="text-xs text-[var(--kf-text-secondary)] mt-1">Choose a completely different visual style, or describe your own</p>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--kf-hover-bg)] text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] transition-colors">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Swatches */}
                <div className="flex-1 overflow-y-auto p-5">
                    {loadingDirections ? (
                        <div className="flex flex-col items-center justify-center py-16">
                            <Loader2 className="w-8 h-8 text-purple-400 animate-spin mb-3" />
                            <p className="text-[var(--kf-text-secondary)] text-sm">Generating design directions...</p>
                            <p className="text-zinc-600 text-xs mt-1">AI is creating 10 unique visual proposals</p>
                            <button
                                onClick={onStopLoading}
                                className="mt-4 h-8 px-4 rounded-lg bg-red-600/20 hover:bg-red-600/30 border border-red-600/40 text-red-400 text-xs font-medium flex items-center gap-1.5 transition-colors"
                            >
                                <StopCircle className="w-3.5 h-3.5" /> Stop
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            {directions.map((d, i) => (
                                <motion.button
                                    key={d.id}
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: i * 0.08 }}
                                    onClick={() => onPick(d, referenceImages.map(img => img.url))}
                                    className="group text-left rounded-xl border border-[var(--kf-border)] hover:border-purple-500/50 bg-[var(--kf-surface)] hover:bg-[var(--kf-surface)] overflow-hidden transition-all duration-200 hover:shadow-lg hover:shadow-purple-500/10"
                                >
                                    {/* Rendered swatch */}
                                    <ScaledHtmlPreview
                                        title={`Swatch: ${d.name}`}
                                        html={d.html_swatch}
                                        baseWidth={DIRECTION_SWATCH_SIZE.width}
                                        baseHeight={DIRECTION_SWATCH_SIZE.height}
                                        className="h-[160px] w-full border-b border-[var(--kf-border)] bg-[var(--kf-bg)]"
                                    />
                                    <div className="p-3">
                                        <h3 className="text-sm font-bold text-[var(--kf-text)] group-hover:text-purple-300 transition-colors">{d.name}</h3>
                                        <p className="text-xs text-[var(--kf-text-secondary)] mt-1 line-clamp-2">{d.description}</p>
                                        {/* Palette dots */}
                                        <div className="flex gap-1.5 mt-2">
                                            {d.palette.map((hex, pi) => (
                                                <div key={pi} className="w-4 h-4 rounded-full border border-[var(--kf-border-muted)]" style={{ background: hex }} title={hex} />
                                            ))}
                                        </div>
                                    </div>
                                </motion.button>
                            ))}
                        </div>
                    )}

                    {/* Custom direction & Image upoad section */}
                    <div className="mt-6 flex flex-col md:flex-row gap-4">
                        {/* Custom direction */}
                        <div className="flex-1 p-4 rounded-xl border border-[var(--kf-border)] bg-[var(--kf-surface)] flex flex-col">
                            <p className="text-xs font-semibold text-[var(--kf-text-secondary)] mb-2">Or describe your own direction:</p>
                            <textarea
                                value={customText}
                                onChange={(e) => setCustomText(e.target.value)}
                                placeholder="e.g., 'Warm retro palette with cream backgrounds, burnt orange accents, rounded generous spacing, and a magazine-like editorial layout'"
                                className="w-full flex-1 min-h-[80px] rounded-lg bg-[var(--kf-surface)] border border-[var(--kf-border-muted)] text-sm text-[var(--kf-text)] p-3 resize-none focus:outline-none focus:border-purple-500/50 placeholder:text-[var(--kf-text-faint)]"
                            />
                        </div>

                        {/* Image upload */}
                        <div className="w-full md:w-80 p-4 rounded-xl border border-[var(--kf-border)] bg-[var(--kf-surface)] flex flex-col items-start">
                            <h4 className="text-xs font-semibold text-[var(--kf-text-secondary)] mb-1 flex items-center gap-1.5">
                                <ImageIcon className="w-3.5 h-3.5" />
                                Inspiration Images (Max 20)
                            </h4>
                            <p className="text-[10px] text-zinc-500 mb-3 leading-tight">
                                Upload screenshots of UIs you like. AI will extract structural hints, mood, and texture (but will NOT copy them exactly).
                            </p>

                            {/* Drop zone */}
                            <label className={`w-full h-16 rounded-lg border-2 border-dashed ${isProcessing ? 'border-purple-500/50 bg-purple-500/5' : 'border-[var(--kf-border-muted)] hover:border-purple-500/40 hover:bg-[var(--kf-badge-bg)]'} flex items-center justify-center cursor-pointer transition-colors mb-3`}>
                                <input type="file" multiple accept="image/*" className="hidden" onChange={(e) => handleFiles(e.target.files)} disabled={isProcessing} />
                                {isProcessing ? (
                                    <Loader2 className="w-4 h-4 text-purple-400 animate-spin" />
                                ) : (
                                    <span className="text-xs text-[var(--kf-text-secondary)] font-medium text-center px-4">
                                        Click or drop images here
                                    </span>
                                )}
                            </label>

                            {/* Image previews */}
                            {referenceImages.length > 0 && (
                                <div className="w-full flex flex-wrap gap-2 max-h-[140px] overflow-y-auto pr-1">
                                    <AnimatePresence>
                                        {referenceImages.map((img) => (
                                            <motion.div
                                                key={img.id}
                                                initial={{ scale: 0.8, opacity: 0 }}
                                                animate={{ scale: 1, opacity: 1 }}
                                                exit={{ scale: 0.8, opacity: 0 }}
                                                className="relative w-12 h-12 rounded border border-[var(--kf-border-muted)] bg-black overflow-hidden group/img shrink-0"
                                            >
                                                <img src={img.url} alt="img" className="w-full h-full object-cover opacity-80" />
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); handleRemoveImage(img.id); }}
                                                    className="absolute top-0 right-0 p-0.5 bg-red-500/80 hover:bg-red-500 text-white rounded-bl opacity-0 group-hover/img:opacity-100 transition-opacity"
                                                >
                                                    <X className="w-3 h-3" />
                                                </button>
                                            </motion.div>
                                        ))}
                                    </AnimatePresence>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="mt-4 flex items-center justify-end gap-3 pt-4 border-t border-[var(--kf-border)]/60">
                        {customText.trim() || referenceImages.length > 0 ? (
                            <button
                                onClick={() => onDescribe(customText.trim(), referenceImages.map(img => img.url))}
                                disabled={isProcessing}
                                className="h-9 px-5 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold flex items-center gap-1.5 shadow-lg shadow-purple-500/20"
                            >
                                <Sparkles className="w-4 h-4" /> Apply Custom Direction
                            </button>
                        ) : null}
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * EXPANDED PREVIEW OVERLAY
 * ═══════════════════════════════════════════════════════════════════════ */

function PreviewOverlay({
    mockup,
    previewDevice,
    setPreviewDevice,
    onClose,
    onNext,
    onPrev,
    hasNext,
    hasPrev,
    onRegenerate,
    onApprove,
    onRevise,
    onDelete,
    isRegenerating,
}: {
    mockup: Mockup;
    previewDevice: "desktop" | "tablet" | "mobile";
    setPreviewDevice: (d: "desktop" | "tablet" | "mobile") => void;
    onClose: () => void;
    onNext: () => void;
    onPrev: () => void;
    hasNext: boolean;
    hasPrev: boolean;
    onRegenerate: () => void;
    onApprove: () => void;
    onRevise: () => void;
    onDelete: () => void;
    isRegenerating: boolean;
}) {
    useEffect(() => {
        const handleKey = (e: KeyboardEvent) => {
            if (e.key === "ArrowRight") onNext();
            else if (e.key === "ArrowLeft") onPrev();
            else if (e.key === "Escape") onClose();
        };
        window.addEventListener("keydown", handleKey);
        return () => window.removeEventListener("keydown", handleKey);
    }, [onNext, onPrev, onClose]);
    const deviceContainerClass: Record<string, string> = {
        desktop: "w-full max-w-[1200px]",
        tablet: "w-full max-w-[860px]",
        mobile: "w-full max-w-[430px]",
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex flex-col"
            onClick={onClose}
        >
            {/* Toolbar */}
            <div
                className="h-14 bg-[var(--kf-surface)] border-b border-[var(--kf-border)]/60 px-5 flex items-center justify-between shrink-0"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center gap-3 min-w-0">
                    <button onClick={onClose} className="p-1.5 rounded-md hover:bg-[var(--kf-hover-bg)] text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)]">
                        <X className="w-4 h-4" />
                    </button>
                    <div className="min-w-0">
                        <h3 className="text-sm font-bold text-[var(--kf-text)] truncate">{mockup.name}</h3>
                        <p className="text-xs text-[var(--kf-text-secondary)] truncate">{mockup.description}</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Device toggle */}
                    <div className="flex items-center gap-1 bg-[var(--kf-hover-bg)] rounded-lg p-1">
                        <button onClick={() => setPreviewDevice("desktop")} className={`p-1.5 rounded ${previewDevice === "desktop" ? "bg-zinc-700 text-white" : "text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)]"}`}><Monitor className="w-4 h-4" /></button>
                        <button onClick={() => setPreviewDevice("tablet")} className={`p-1.5 rounded ${previewDevice === "tablet" ? "bg-zinc-700 text-white" : "text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)]"}`}><Tablet className="w-4 h-4" /></button>
                        <button onClick={() => setPreviewDevice("mobile")} className={`p-1.5 rounded ${previewDevice === "mobile" ? "bg-zinc-700 text-white" : "text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)]"}`}><Smartphone className="w-4 h-4" /></button>
                    </div>

                    <button onClick={onRegenerate} disabled={isRegenerating} className="h-8 px-3 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:border-purple-500/60 hover:bg-purple-500/10 text-xs flex items-center gap-1.5 disabled:opacity-40">
                        {isRegenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Regenerate
                    </button>

                    {mockup.status === "complete" && (
                        <>
                            <button onClick={onRevise} className="h-8 px-3 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)] text-xs">Revise</button>
                            <button onClick={onApprove} className="h-8 px-3 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs flex items-center gap-1.5">
                                <Check className="w-3.5 h-3.5" /> Approve
                            </button>
                        </>
                    )}
                    {mockup.status === "approved" && (
                        <span className="h-8 px-3 rounded-md bg-emerald-600/20 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5" /> Approved
                        </span>
                    )}

                    <button onClick={onDelete} className="h-8 w-8 rounded-md flex items-center justify-center text-zinc-500 hover:text-red-400 hover:bg-red-500/10">
                        <Trash2 className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>

            {/* Prev / Next arrows */}
            {hasPrev && (
                <button
                    onClick={(e) => { e.stopPropagation(); onPrev(); }}
                    className="fixed left-4 top-1/2 -translate-y-1/2 z-[60] p-2 rounded-full bg-black/60 hover:bg-black/80 border border-white/10 text-white transition-colors"
                    aria-label="Previous mockup"
                >
                    <ChevronLeft className="w-6 h-6" />
                </button>
            )}
            {hasNext && (
                <button
                    onClick={(e) => { e.stopPropagation(); onNext(); }}
                    className="fixed right-4 top-1/2 -translate-y-1/2 z-[60] p-2 rounded-full bg-black/60 hover:bg-black/80 border border-white/10 text-white transition-colors"
                    aria-label="Next mockup"
                >
                    <ChevronRight className="w-6 h-6" />
                </button>
            )}

            {/* Preview */}
            <div className="flex-1 overflow-auto flex items-start justify-center p-6" onClick={(e) => e.stopPropagation()}>
                {mockup.component_code ? (
                    <div className={`${deviceContainerClass[previewDevice]} rounded-xl border border-[var(--kf-border-muted)] bg-[var(--kf-bg)] overflow-hidden shadow-2xl`}>
                        <div className="h-8 bg-[var(--kf-surface)] border-b border-[var(--kf-border-muted)] flex items-center px-3 gap-2">
                            <div className="w-2.5 h-2.5 rounded-full bg-red-400" />
                            <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                            <span className="text-[11px] text-[var(--kf-text-secondary)] ml-2">{mockup.name}</span>
                        </div>
                        <iframe
                            key={mockup.id}
                            title={`Preview: ${mockup.name}`}
                            srcDoc={mockup.component_code}
                            className="w-full bg-white"
                            style={{ height: "calc(100vh - 120px)" }}
                            sandbox="allow-scripts"
                        />
                    </div>
                ) : (
                    <div className="text-zinc-500 text-sm mt-32">No preview available</div>
                )}
            </div>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * DESIGN PREFERENCES MODAL
 * ═══════════════════════════════════════════════════════════════════════ */

interface DesignPreferences {
    theme: "light" | "dark";
    style?: string;
    color_preference?: string;
    additional_notes?: string;
}

const STYLE_OPTIONS = [
    { value: "minimal", label: "Minimal", desc: "Clean, lots of whitespace" },
    { value: "bold", label: "Bold", desc: "Strong colors, large type" },
    { value: "corporate", label: "Corporate", desc: "Professional, structured" },
    { value: "playful", label: "Playful", desc: "Rounded, colorful, friendly" },
    { value: "editorial", label: "Editorial", desc: "Typography-driven, magazine feel" },
];

const COLOR_OPTIONS = [
    { value: "blue", label: "Blue tones", color: "#3b82f6" },
    { value: "green", label: "Green tones", color: "#22c55e" },
    { value: "warm", label: "Warm tones", color: "#f97316" },
    { value: "purple", label: "Purple tones", color: "#8b5cf6" },
    { value: "neutral", label: "Neutral", color: "#64748b" },
    { value: "auto", label: "Auto (AI picks)", color: "transparent" },
];

function DesignPreferencesModal({
    onConfirm,
    onClose,
    saving,
}: {
    onConfirm: (prefs: DesignPreferences) => void;
    onClose: () => void;
    saving: boolean;
}) {
    const [selectedTheme, setSelectedTheme] = useState<"light" | "dark">("dark");
    const [selectedStyle, setSelectedStyle] = useState<string | undefined>();
    const [selectedColor, setSelectedColor] = useState<string>("auto");
    const [notes, setNotes] = useState("");

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                className="relative w-full max-w-lg bg-[var(--kf-surface)] border border-[var(--kf-border)] rounded-2xl shadow-2xl overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="px-6 pt-5 pb-4 border-b border-[var(--kf-border)]/40">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30">
                                <Settings2 className="w-5 h-5 text-purple-400" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold text-[var(--kf-text)]">Design Preferences</h2>
                                <p className="text-xs text-[var(--kf-text-secondary)]">Guide the AI to generate consistent mockups</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[var(--kf-hover-bg)] text-[var(--kf-text-faint)]">
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Body */}
                <div className="px-6 py-5 space-y-5 max-h-[60vh] overflow-y-auto">
                    {/* Theme */}
                    <div>
                        <label className="text-sm font-semibold text-[var(--kf-text)] mb-2.5 block">Theme Mode</label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                onClick={() => setSelectedTheme("dark")}
                                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                                    selectedTheme === "dark"
                                        ? "border-purple-500 bg-purple-500/10"
                                        : "border-[var(--kf-border-muted)] bg-[var(--kf-bg)] hover:border-[var(--kf-border)]"
                                }`}
                            >
                                <Moon className="w-5 h-5 text-indigo-400" />
                                <div className="text-left">
                                    <div className="text-sm font-medium text-[var(--kf-text)]">Dark Mode</div>
                                    <div className="text-xs text-[var(--kf-text-secondary)]">Deep, immersive backgrounds</div>
                                </div>
                            </button>
                            <button
                                onClick={() => setSelectedTheme("light")}
                                className={`flex items-center gap-3 p-4 rounded-xl border-2 transition-all ${
                                    selectedTheme === "light"
                                        ? "border-purple-500 bg-purple-500/10"
                                        : "border-[var(--kf-border-muted)] bg-[var(--kf-bg)] hover:border-[var(--kf-border)]"
                                }`}
                            >
                                <Sun className="w-5 h-5 text-amber-400" />
                                <div className="text-left">
                                    <div className="text-sm font-medium text-[var(--kf-text)]">Light Mode</div>
                                    <div className="text-xs text-[var(--kf-text-secondary)]">Clean, bright surfaces</div>
                                </div>
                            </button>
                        </div>
                    </div>

                    {/* Style */}
                    <div>
                        <label className="text-sm font-semibold text-[var(--kf-text)] mb-2.5 block">Design Style</label>
                        <div className="flex flex-wrap gap-2">
                            {STYLE_OPTIONS.map((opt) => (
                                <button
                                    key={opt.value}
                                    onClick={() => setSelectedStyle(selectedStyle === opt.value ? undefined : opt.value)}
                                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                                        selectedStyle === opt.value
                                            ? "border-purple-500 bg-purple-500/15 text-purple-300"
                                            : "border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:border-[var(--kf-border)]"
                                    }`}
                                    title={opt.desc}
                                >
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Color preference */}
                    <div>
                        <label className="text-sm font-semibold text-[var(--kf-text)] mb-2.5 block">Color Preference</label>
                        <div className="flex flex-wrap gap-2">
                            {COLOR_OPTIONS.map((opt) => (
                                <button
                                    key={opt.value}
                                    onClick={() => setSelectedColor(opt.value)}
                                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                                        selectedColor === opt.value
                                            ? "border-purple-500 bg-purple-500/15 text-purple-300"
                                            : "border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:border-[var(--kf-border)]"
                                    }`}
                                >
                                    {opt.color !== "transparent" && (
                                        <span className="w-3 h-3 rounded-full" style={{ backgroundColor: opt.color }} />
                                    )}
                                    {opt.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Additional notes */}
                    <div>
                        <label className="text-sm font-semibold text-[var(--kf-text)] mb-2.5 block">Additional Notes <span className="font-normal text-[var(--kf-text-faint)]">(optional)</span></label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            placeholder="e.g., Use glassmorphism effects, prefer rounded corners, no gradients..."
                            className="w-full h-20 bg-[var(--kf-bg)] border border-[var(--kf-border-muted)] rounded-lg px-3 py-2 text-sm text-[var(--kf-text)] placeholder:text-[var(--kf-text-faint)] focus:outline-none focus:border-purple-500/50 resize-none"
                        />
                    </div>
                </div>

                {/* Footer */}
                <div className="px-6 py-4 border-t border-[var(--kf-border)]/40 flex items-center justify-between">
                    <button
                        onClick={onClose}
                        className="h-9 px-4 rounded-lg text-sm text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() =>
                            onConfirm({
                                theme: selectedTheme,
                                style: selectedStyle,
                                color_preference: selectedColor === "auto" ? undefined : selectedColor,
                                additional_notes: notes.trim() || undefined,
                            })
                        }
                        disabled={saving}
                        className="h-9 px-5 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-500/20"
                    >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                        Confirm & Generate
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════
 * MAIN COMPONENT
 * ═══════════════════════════════════════════════════════════════════════ */

export default function DesignStudioPage() {
    const { projectId } = useParams<{ projectId: string }>();
    const navigate = useNavigate();
    const { getAccessToken, signOut } = useAuth();
    const { theme } = useTheme();

    // Core state
    const [mockups, setMockups] = useState<Mockup[]>([]);
    const [loading, setLoading] = useState(true);
    const [phase, setPhase] = useState<Phase>("discovering");
    const [generating, setGenerating] = useState(false);
    const [regeneratingIds, setRegeneratingIds] = useState<Set<string>>(new Set());
    const [error, setError] = useState<string | null>(null);

    // Preview overlay
    const [expandedMockupId, setExpandedMockupId] = useState<string | null>(null);
    const [previewDevice, setPreviewDevice] = useState<"desktop" | "tablet" | "mobile">("desktop");

    // Direction picker
    const [showDirections, setShowDirections] = useState(false);
    const [directions, setDirections] = useState<Direction[]>([]);
    const [loadingDirections, setLoadingDirections] = useState(false);
    const directionsAbortRef = useRef<AbortController | null>(null);
    const [pendingDirection, setPendingDirection] = useState<string | null>(null);
    const [pendingReferenceImages, setPendingReferenceImages] = useState<string[]>([]);

    // Add screen
    const [addScreenName, setAddScreenName] = useState("");
    const [rediscovering, setRediscovering] = useState(false);

    // Design preferences
    const [showPreferences, setShowPreferences] = useState(false);
    const [designPreferences, setDesignPreferences] = useState<DesignPreferences | null>(null);
    const [savingPreferences, setSavingPreferences] = useState(false);

    // Polling
    const pollRef = useRef<number | null>(null);
    const prevStatusRef = useRef<Record<string, string>>({});

    /* ─── API helpers ──────────────────────────────────────────────── */

    const expireSession = useCallback(async () => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
        setGenerating(false);
        setLoading(false);
        setError("Session expired. Please log in again.");
        try {
            await signOut();
        } catch {
            // ignore sign-out cleanup errors
        }
        navigate("/login", { replace: true });
    }, [navigate, signOut]);

    const authHeaders = useCallback(async () => {
        const token = await getAccessToken();
        if (!token) return null;
        return { Authorization: `Bearer ${token}` };
    }, [getAccessToken]);

    const ensureAuth = useCallback(async (): Promise<Record<string, string> | null> => {
        const headers = await authHeaders();
        if (!headers) {
            await expireSession();
            return null;
        }
        return headers;
    }, [authHeaders, expireSession]);

    const handleApi401 = useCallback((resp: Response) => {
        if (resp.status === 401) {
            void expireSession();
        }
    }, [expireSession]);

    const fetchMockups = useCallback(async () => {
        try {
            const headers = await authHeaders();
            if (!headers) {
                await expireSession();
                return [];
            }
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups`, { headers });
            if (resp.status === 401) {
                await expireSession();
                return [];
            }
            if (resp.ok) {
                const data = await resp.json();
                const next: Mockup[] = data.mockups || [];

                prevStatusRef.current = Object.fromEntries(next.map((m: Mockup) => [m.id, m.status]));
                setMockups(next);

                // Auto-resume polling if backend is actively generating
                const activelyGenerating = next.some((m: Mockup) => m.status === "generating");
                if (activelyGenerating) {
                    setGenerating(true);
                    setPhase("generating");
                    const token = await getAccessToken();
                    if (token) startPolling();
                }

                return next;
            }
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
        return [];
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectId, getAccessToken, authHeaders, expireSession]);

    /* ─── Auto-discover on mount ──────────────────────────────────── */

    useEffect(() => {
        let cancelled = false;

        async function init() {
            const existing = await fetchMockups();

            // Load saved design preferences
            try {
                const headers = await authHeaders();
                if (headers) {
                    const prefsResp = await fetch(
                        `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/preferences`,
                        { headers }
                    );
                    if (prefsResp.ok) {
                        const prefsData = await prefsResp.json();
                        if (prefsData.preferences && prefsData.preferences.theme) {
                            if (!cancelled) setDesignPreferences(prefsData.preferences as DesignPreferences);
                        }
                    }
                }
            } catch { /* ignore — preferences are optional */ }

            // If there are already completed/approved mockups, go to gallery
            const hasCompleted = existing.some(
                (m: Mockup) => m.status === "complete" || m.status === "approved"
            );
            const isGenerating = existing.some((m: Mockup) => m.status === "generating");

            if (isGenerating) {
                setPhase("generating");
            } else if (hasCompleted) {
                setPhase("gallery");
            } else if (existing.length > 0) {
                // Has discovered screens but not generated
                setPhase("discovery");
            } else {
                // No screens at all — auto-discover
                setPhase("discovering");
                if (cancelled) return;
                try {
                    const headers = await authHeaders();
                    if (!headers) {
                        if (!cancelled) navigate("/login", { replace: true });
                        return;
                    }
                    const resp = await fetch(
                        `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/discover`,
                        { method: "POST", headers }
                    );
                    if (resp.status === 401 && !cancelled) {
                        navigate("/login", { replace: true });
                        return;
                    }
                    if (resp.ok) {
                        const data = await resp.json();
                        const screens = (data.screens || []).map((s: any) => ({
                            id: s.id,
                            name: s.name,
                            description: s.description,
                            priority: s.priority,
                            status: s.status,
                            component_code: null,
                            revision_notes: null,
                            created_at: "",
                        })) as Mockup[];
                        if (!cancelled) {
                            setMockups(screens);
                            setPhase("discovery");
                        }
                    }
                } catch (e: any) {
                    if (!cancelled) {
                        setError(e.message);
                        setPhase("discovery");
                    }
                }
            }
        }

        init();
        return () => {
            cancelled = true;
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [projectId]);

    /* ─── Polling ─────────────────────────────────────────────────── */

    const startPolling = useCallback(() => {
        if (pollRef.current) clearInterval(pollRef.current);

        // Grace period: don't end polling in the first few seconds — the
        // backend needs time to delete old mockups and create new pending rows.
        const startedAt = Date.now();
        const GRACE_MS = 8_000; // 8 seconds

        pollRef.current = window.setInterval(async () => {
            try {
                const token = await getAccessToken();
                if (!token) {
                    await expireSession();
                    return;
                }
                const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (resp.status === 401) {
                    await expireSession();
                    return;
                }
                if (!resp.ok) return;
                const data = await resp.json();
                const next: Mockup[] = data.mockups || [];

                prevStatusRef.current = Object.fromEntries(next.map((m) => [m.id, m.status]));
                setMockups(next);

                const done = next.length > 0 && next.every((m) => m.status !== "generating" && m.status !== "pending");
                if (done && Date.now() - startedAt > GRACE_MS) {
                    setGenerating(false);
                    setRegeneratingIds(new Set());
                    clearInterval(pollRef.current!);
                    pollRef.current = null;
                    // Transition to gallery once generation finishes
                    const anyCompleted = next.some((m) => m.status === "complete" || m.status === "approved");
                    if (anyCompleted) setPhase("gallery");
                    else setPhase("discovery");
                }
            } catch { /* ignore polling errors */ }
        }, 2500);
    }, [projectId, getAccessToken, expireSession]);

    /* ─── Handlers ────────────────────────────────────────────────── */

    const handleGenerateAll = async (overrideDirection?: string, overrideImages?: string[], overridePrefs?: DesignPreferences) => {
        // Show preferences modal on first-ever generation (no prefs saved yet)
        if (!designPreferences && !overridePrefs) {
            setShowPreferences(true);
            return;
        }

        const directionToUse = overrideDirection !== undefined ? overrideDirection : pendingDirection;
        const imagesToUse = overrideImages !== undefined ? overrideImages : pendingReferenceImages;
        const prefsToUse = overridePrefs || designPreferences;
        setPendingDirection(null);
        setPendingReferenceImages([]);
        setGenerating(true);
        setPhase("generating");
        setError(null);
        // Mark all existing mockups as pending immediately so the UI shows
        // loading spinners and the poller never concludes "all complete".
        setMockups((prev) =>
            prev.map((m) => ({ ...m, status: "pending" as Mockup["status"], component_code: null }))
        );
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/generate-all`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({
                    design_mode: "ai_free",
                    direction: directionToUse,
                    reference_images: imagesToUse,
                    design_preferences: prefsToUse,
                }),
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to start design generation");
            startPolling();
        } catch (e: any) {
            setError(e.message);
            setGenerating(false);
            setPhase("discovery");
        }
    };

    const handleConfirmPreferences = async (prefs: DesignPreferences) => {
        setSavingPreferences(true);
        try {
            // Save preferences to backend
            const headers = await ensureAuth();
            if (!headers) return;
            await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/preferences`, {
                method: "PUT",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify(prefs),
            });
            setDesignPreferences(prefs);
            setShowPreferences(false);
            // Trigger generation with the new preferences
            await handleGenerateAll(undefined, undefined, prefs);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSavingPreferences(false);
        }
    };

    const handleRegenerateSingle = async (mockupId: string) => {
        setRegeneratingIds((prev) => new Set(prev).add(mockupId));
        setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "generating" } : m)));
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/generate/${mockupId}`,
                { method: "POST", headers }
            );
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to regenerate");
            startPolling();
        } catch (e: any) {
            setError(e.message);
            setRegeneratingIds((prev) => { const s = new Set(prev); s.delete(mockupId); return s; });
            setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "error" } : m)));
        }
    };

    const handleApprove = async (mockupId: string) => {
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/approve`, {
                method: "POST", headers,
            });
            handleApi401(resp);
            setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "approved" } : m)));
        } catch (e: any) { setError(e.message); }
    };

    const handleApproveAll = async () => {
        const toApprove = mockups.filter((m) => m.status === "complete");
        if (!toApprove.length) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const results = await Promise.all(
                toApprove.map((m) =>
                    fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${m.id}/approve`, {
                        method: "POST", headers,
                    })
                )
            );
            if (results.some((r) => r.status === 401)) handleApi401(results[0]);
            setMockups((prev) => prev.map((m) => (m.status === "complete" ? { ...m, status: "approved" } : m)));
        } catch (e: any) { setError(e.message); }
    };

    const handleDelete = async (mockupId: string, mockupName: string) => {
        if (!window.confirm(`Delete "${mockupName}"?`)) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}`,
                { method: "DELETE", headers }
            );
            handleApi401(resp);
            setMockups((prev) => prev.filter((m) => m.id !== mockupId));
            if (expandedMockupId === mockupId) setExpandedMockupId(null);
        } catch (e: any) { setError(e.message); }
    };

    const handleStopAll = async () => {
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/stop`, {
                method: "POST", headers,
            });
            handleApi401(resp);
        } catch { /* best-effort */ } finally {
            setGenerating(false);
            setRegeneratingIds(new Set());
            if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
            const refreshed = await fetchMockups();
            const anyCompleted = refreshed.some((m: Mockup) => m.status === "complete" || m.status === "approved");
            setPhase(anyCompleted ? "gallery" : "discovery");
        }
    };

    const handleStop = async (mockupId: string) => {
        setRegeneratingIds((prev) => { const s = new Set(prev); s.delete(mockupId); return s; });
        setMockups((prev) => prev.map((m) => (m.id === mockupId ? { ...m, status: "pending" } : m)));
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(
                `${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/stop`,
                { method: "POST", headers }
            );
            handleApi401(resp);
        } catch { /* best-effort */ }
    };

    const handleRequestRevision = async (mockupId: string) => {
        const notes = prompt("What changes would you like to see?");
        if (!notes) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/${mockupId}/revise`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ notes }),
            });
            handleApi401(resp);
            fetchMockups();
        } catch (e: any) { setError(e.message); }
    };

    const handleAddScreen = async () => {
        const name = addScreenName.trim();
        if (!name) return;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/mockups/add`, {
                method: "POST",
                headers: { ...headers, "Content-Type": "application/json" },
                body: JSON.stringify({ name, description: "", priority: "important" }),
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to add screen");
            const data = await resp.json();
            setMockups((prev) => [
                ...prev,
                { id: data.id, name: data.name, description: data.description, priority: data.priority, status: data.status, component_code: null, revision_notes: null, created_at: "" },
            ]);
            setAddScreenName("");
        } catch (e: any) { setError(e.message); }
    };

    const handleRediscoverScreens = async () => {
        setRediscovering(true);
        setError(null);
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/rediscover`, {
                method: "POST",
                headers,
            });
            handleApi401(resp);
            if (!resp.ok) throw new Error("Failed to discover additional screens");
            const data = await resp.json();
            if (data.status === "no_new_screens") {
                setError("All necessary screens are already discovered — no new screens found.");
            } else {
                const newScreens = (data.screens || []).map((s: any) => ({
                    id: s.id,
                    name: s.name,
                    description: s.description,
                    priority: s.priority,
                    status: s.status,
                    component_code: null,
                    revision_notes: null,
                    created_at: "",
                })) as Mockup[];
                setMockups((prev) => [...prev, ...newScreens]);
            }
        } catch (e: any) {
            setError(e.message);
        } finally {
            setRediscovering(false);
        }
    };

    const handleOpenDirections = async () => {
        setShowDirections(true);
        if (directions.length > 0) return;
        setLoadingDirections(true);
        setError(null);
        const abortCtrl = new AbortController();
        directionsAbortRef.current = abortCtrl;
        try {
            const headers = await ensureAuth();
            if (!headers) return;
            const resp = await fetch(`${getApiBaseUrl()}/api/v1/projects/${projectId}/design/directions`, {
                method: "POST", headers, signal: abortCtrl.signal,
            });
            handleApi401(resp);
            if (resp.ok) {
                const data = await resp.json();
                setDirections(data.directions || []);
            } else if (resp.status === 404) {
                setDirections([]);
                setError("Could not load design proposals. Use the text area below to describe your own direction.");
            }
        } catch (e: any) {
            if (e?.name === "AbortError") return;
            setError(e?.message || "Failed to load design directions. Describe your own below.");
        } finally {
            setLoadingDirections(false);
            directionsAbortRef.current = null;
        }
    };

    const handleStopDirections = () => {
        directionsAbortRef.current?.abort();
        setLoadingDirections(false);
    };

    const handlePickDirection = (d: Direction, images: string[] = []) => {
        setShowDirections(false);
        setDirections([]);
        const directionDesc = `Direction: ${d.name}\nDescription: ${d.description}\nPalette: ${d.palette.join(", ")}\nStyle: ${d.style_keywords.join(", ")}\nLayout: ${d.layout_approach}`;
        setPendingDirection(directionDesc);
        setPendingReferenceImages(images);
        handleGenerateAll(directionDesc, images);
    };

    const handleDescribeDirection = (text: string, images: string[] = []) => {
        setShowDirections(false);
        setDirections([]);
        const directionText = text ? `Custom direction from user: ${text}` : null;
        setPendingDirection(directionText);
        setPendingReferenceImages(images);
        handleGenerateAll(directionText || undefined, images);
    };

    /* ─── Derived ─────────────────────────────────────────────────── */

    const isDark = theme === "dark";
    const PRIORITY_COLORS = isDark ? PRIORITY_COLORS_DARK : PRIORITY_COLORS_LIGHT;

    const approvedCount = mockups.filter((m) => m.status === "approved").length;
    const generatedCount = mockups.filter((m) => m.status === "complete" || m.status === "approved").length;
    const expandedMockup = mockups.find((m) => m.id === expandedMockupId) || null;

    const groupedByPriority = {
        high: mockups.filter((m) => m.priority === "high"),
        medium: mockups.filter((m) => m.priority === "medium"),
        low: mockups.filter((m) => m.priority === "low"),
    };

    /* ─── Loading state ───────────────────────────────────────────── */

    if (loading) {
        return (
            <div className="flex items-center justify-center h-[60vh]">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            </div>
        );
    }

    /* ═══════════════════════════════════════════════════════════════════════
     * RENDER
     * ═══════════════════════════════════════════════════════════════════════ */

    return (
        <div className="h-[calc(100vh-65px)] bg-[var(--kf-bg)] text-[var(--kf-text)] flex flex-col overflow-hidden">
            {/* ── Top bar ──────────────────────────────────────────────── */}
            <div className="h-14 border-b border-[var(--kf-border)]/60 px-5 flex items-center justify-between bg-[var(--kf-surface)] shrink-0">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => navigate(`/project/${projectId}`)}
                        className="flex items-center gap-1.5 h-8 px-2.5 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)] text-xs transition-colors"
                    >
                        <ArrowLeft className="w-3.5 h-3.5" /> Project
                    </button>
                    <div className="flex items-center gap-2">
                        <Palette className="w-4 h-4 text-purple-300" />
                        <h2 className="text-sm font-bold text-[var(--kf-text)]">Design Studio</h2>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {/* Progress badge */}
                    <span className="text-xs text-[var(--kf-text-secondary)]">
                        {approvedCount} approved &middot; {generatedCount}/{mockups.length || 0} generated
                    </span>

                    {phase === "gallery" && mockups.some((m) => m.status === "complete") && (
                        <button
                            onClick={handleApproveAll}
                            className="h-8 px-3 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium flex items-center gap-1.5"
                        >
                            <CheckCheck className="w-3.5 h-3.5" /> Approve All
                        </button>
                    )}

                    <button
                        onClick={() => navigate(`/project/${projectId}/editor?autobuild=1`)}
                        className="h-8 px-3 rounded-md bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-purple-500/20"
                    >
                        <Rocket className="w-3.5 h-3.5" /> Build with Kith
                    </button>

                    <button
                        onClick={() => navigate("/")}
                        className="h-8 px-2.5 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)] text-xs flex items-center gap-1.5"
                    >
                        <LayoutGrid className="w-3.5 h-3.5" /> All Projects
                    </button>
                </div>
            </div>

            {/* ── Main content area ────────────────────────────────────── */}
            <div className="flex-1 overflow-hidden">
                <AnimatePresence mode="wait">
                    {/* ── PHASE: DISCOVERING ──────────────────────────────── */}
                    {phase === "discovering" && (
                        <motion.div
                            key="discovering"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="h-full flex flex-col items-center justify-center"
                        >
                            <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                            >
                                <Compass className="w-12 h-12 text-purple-400" />
                            </motion.div>
                            <p className="text-[var(--kf-text-secondary)] mt-4 text-sm font-medium">Discovering screens...</p>
                            <p className="text-zinc-600 text-xs mt-1">AI is analyzing your product to determine the right screens</p>

                            {/* Progress timeline */}
                            <div className="mt-8 flex items-center gap-3">
                                {["Analyze", "Infer Screens", "Prioritize"].map((step, i) => (
                                    <div key={step} className="flex items-center gap-2">
                                        <motion.div
                                            initial={{ scale: 0.8, opacity: 0.3 }}
                                            animate={{ scale: 1, opacity: 1 }}
                                            transition={{ delay: i * 0.8, duration: 0.5 }}
                                            className="w-8 h-8 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center text-purple-300 text-xs font-bold"
                                        >
                                            {i + 1}
                                        </motion.div>
                                        <span className="text-xs text-zinc-500">{step}</span>
                                        {i < 2 && <ChevronRight className="w-3 h-3 text-zinc-700" />}
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {/* ── PHASE: DISCOVERY ────────────────────────────────── */}
                    {phase === "discovery" && (
                        <motion.div
                            key="discovery"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="h-full flex flex-col"
                        >
                            {/* Discovery header */}
                            <div className="px-6 pt-5 pb-4 border-b border-[var(--kf-border)]/40">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-[var(--kf-text)]">Screens Discovered</h3>
                                        <p className="text-xs text-[var(--kf-text-secondary)] mt-1">
                                            AI identified {mockups.length} screens for your MVP. Edit, add or remove before generating.
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-zinc-500 mr-2">{mockups.length} screens</span>
                                    </div>
                                </div>
                            </div>

                            {/* Screen cards grid — grouped by priority */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                {(["high", "medium", "low"] as const).map((priority) => {
                                    const items = groupedByPriority[priority];
                                    if (items.length === 0) return null;
                                    const label = priority === "high" ? "Critical" : priority === "medium" ? "Important" : "Nice to Have";
                                    return (
                                        <div key={priority} className="mb-6">
                                            <div className="flex items-center gap-2 mb-3">
                                                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${PRIORITY_COLORS[priority]}`}>
                                                    {label}
                                                </span>
                                                <div className="h-px flex-1 bg-[var(--kf-hover-bg)]" />
                                            </div>
                                            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                                {items.map((m, i) => (
                                                    <motion.div
                                                        key={m.id}
                                                        initial={{ opacity: 0, y: 10 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: i * 0.05 }}
                                                        className="group rounded-xl border border-[var(--kf-border)]/60 bg-[var(--kf-surface)] hover:bg-[var(--kf-badge-bg)] hover:border-[var(--kf-border-muted)] p-4 transition-all"
                                                    >
                                                        <div className="flex items-start justify-between mb-2">
                                                            <h4 className="text-sm font-bold text-[var(--kf-text)]">{m.name}</h4>
                                                            <button
                                                                onClick={() => handleDelete(m.id, m.name)}
                                                                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-zinc-600 hover:text-red-400 transition-all"
                                                            >
                                                                <Trash2 className="w-3 h-3" />
                                                            </button>
                                                        </div>
                                                        <p className="text-xs text-[var(--kf-text-secondary)] line-clamp-2 mb-3">{m.description}</p>
                                                        <div className="flex items-center justify-between">
                                                            <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[m.priority]}`}>
                                                                {m.priority}
                                                            </span>
                                                            <button
                                                                onClick={() => handleRegenerateSingle(m.id)}
                                                                className="h-7 px-2.5 rounded-md bg-purple-600/20 hover:bg-purple-600/30 border border-purple-600/30 text-purple-300 text-[11px] font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all"
                                                            >
                                                                <Zap className="w-3 h-3" /> Generate
                                                            </button>
                                                        </div>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>

                            {/* Bottom dock */}
                            <div className="border-t border-[var(--kf-border)]/60 bg-[var(--kf-surface)] px-6 py-3 flex items-center gap-3 shrink-0">
                                {/* Add screen input */}
                                <div className="flex items-center gap-2 flex-1 max-w-md">
                                    <Plus className="w-4 h-4 text-zinc-500 shrink-0" />
                                    <input
                                        type="text"
                                        value={addScreenName}
                                        onChange={(e) => setAddScreenName(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleAddScreen()}
                                        placeholder="Add a screen..."
                                        className="flex-1 h-8 bg-[var(--kf-surface)] border border-[var(--kf-border-muted)] rounded-lg px-3 text-xs text-[var(--kf-text)] placeholder:text-[var(--kf-text-faint)] focus:outline-none focus:border-purple-500/50"
                                    />
                                    <button
                                        onClick={handleAddScreen}
                                        disabled={!addScreenName.trim()}
                                        className="h-8 px-3 rounded-lg bg-[var(--kf-badge-bg)] hover:bg-[var(--kf-hover-bg)] text-xs text-[var(--kf-text-secondary)] disabled:opacity-30 transition-colors"
                                    >
                                        Add
                                    </button>
                                </div>

                                <div className="flex-1" />

                                {/* Discover More Screens from artifacts */}
                                <button
                                    onClick={handleRediscoverScreens}
                                    disabled={rediscovering}
                                    className="h-9 px-4 rounded-lg border border-[var(--kf-border-muted)] hover:border-purple-500/40 text-[var(--kf-text-secondary)] hover:text-purple-300 text-xs font-medium flex items-center gap-2 transition-colors disabled:opacity-50"
                                >
                                    {rediscovering ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}
                                    {rediscovering ? "Analyzing Artifacts..." : "Discover More Screens"}
                                </button>

                                {/* Pending direction/images badge */}
                                {(pendingDirection || pendingReferenceImages.length > 0) && (
                                    <div className="flex items-center gap-2 h-9 px-3 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs">
                                        <Compass className="w-3.5 h-3.5 shrink-0" />
                                        <span className="truncate max-w-[180px]">
                                            {pendingDirection ? pendingDirection.split("\n")[0].replace("Direction: ", "").replace("Custom direction from user: ", "") : `${pendingReferenceImages.length} images `}
                                            {pendingDirection && pendingReferenceImages.length > 0 && ` + ${pendingReferenceImages.length} images`}
                                        </span>
                                        <button onClick={() => { setPendingDirection(null); setPendingReferenceImages([]); }} className="p-0.5 rounded hover:bg-purple-500/20">
                                            <X className="w-3 h-3" />
                                        </button>
                                    </div>
                                )}

                                {/* Theme preference badge */}
                                {designPreferences ? (
                                    <button
                                        onClick={() => setShowPreferences(true)}
                                        className="flex items-center gap-2 h-9 px-3 rounded-lg bg-[var(--kf-badge-bg)] border border-[var(--kf-border-muted)] hover:border-purple-500/30 text-[var(--kf-text-secondary)] text-xs transition-colors"
                                        title="Change design preferences"
                                    >
                                        {designPreferences.theme === "dark" ? <Moon className="w-3.5 h-3.5" /> : <Sun className="w-3.5 h-3.5" />}
                                        {designPreferences.theme === "dark" ? "Dark" : "Light"}
                                        {designPreferences.style && <span className="text-[var(--kf-text-faint)]">/ {designPreferences.style}</span>}
                                    </button>
                                ) : (
                                    <button
                                        onClick={() => setShowPreferences(true)}
                                        className="flex items-center gap-2 h-9 px-3 rounded-lg border border-dashed border-[var(--kf-border-muted)] hover:border-purple-500/40 text-[var(--kf-text-faint)] hover:text-purple-300 text-xs transition-colors"
                                    >
                                        <Settings2 className="w-3.5 h-3.5" /> Set Preferences
                                    </button>
                                )}

                                {/* New direction */}
                                <button
                                    onClick={handleOpenDirections}
                                    className="h-9 px-4 rounded-lg border border-[var(--kf-border-muted)] hover:border-purple-500/40 text-[var(--kf-text-secondary)] hover:text-purple-300 text-xs font-medium flex items-center gap-2 transition-colors"
                                >
                                    <Compass className="w-3.5 h-3.5" /> {pendingDirection ? "Change Direction" : "New Design Direction"}
                                </button>

                                {/* Generate All */}
                                <button
                                    onClick={() => handleGenerateAll()}
                                    disabled={generating || mockups.length === 0}
                                    className="h-9 px-5 rounded-lg bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-sm font-semibold disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-purple-500/20"
                                >
                                    <Sparkles className="w-4 h-4" /> {pendingDirection ? "Generate with Direction" : "Generate All"}
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {/* ── PHASE: GENERATING ───────────────────────────────── */}
                    {phase === "generating" && (
                        <motion.div
                            key="generating"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="h-full flex flex-col"
                        >
                            {/* Progress header */}
                            <div className="px-6 pt-5 pb-4 border-b border-[var(--kf-border)]/40">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                                        <div>
                                            <h3 className="text-lg font-bold text-[var(--kf-text)]">Generating Designs</h3>
                                            <p className="text-xs text-[var(--kf-text-secondary)] mt-0.5">
                                                {generatedCount}/{mockups.length} complete &mdash; First screen is the north star
                                            </p>
                                        </div>
                                    </div>
                                    <button
                                        onClick={handleStopAll}
                                        className="h-9 px-4 rounded-lg bg-red-600/20 hover:bg-red-600/30 border border-red-600/40 text-red-400 text-sm font-medium flex items-center gap-2 transition-colors"
                                    >
                                        <StopCircle className="w-4 h-4" /> Stop All
                                    </button>
                                </div>

                                {/* Progress bar */}
                                <div className="mt-3 h-1.5 rounded-full bg-[var(--kf-badge-bg)] overflow-hidden">
                                    <motion.div
                                        className="h-full bg-gradient-to-r from-purple-500 to-violet-400 rounded-full"
                                        initial={{ width: 0 }}
                                        animate={{ width: mockups.length > 0 ? `${(generatedCount / mockups.length) * 100}%` : "0%" }}
                                        transition={{ duration: 0.5 }}
                                    />
                                </div>
                            </div>

                            {/* Live preview grid */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                    {mockups.map((m, i) => {
                                        const isGen = m.status === "generating" || regeneratingIds.has(m.id);
                                        const isDone = m.status === "complete" || m.status === "approved";
                                        return (
                                            <motion.div
                                                key={m.id}
                                                initial={{ opacity: 0, scale: 0.95 }}
                                                animate={{ opacity: 1, scale: 1 }}
                                                transition={{ delay: i * 0.04 }}
                                                className={`rounded-xl border overflow-hidden transition-all ${
                                                    isDone ? "border-[var(--kf-border)] bg-[var(--kf-surface)]" : "border-[var(--kf-border)]/40 bg-[var(--kf-surface)]"
                                                }`}
                                            >
                                                {/* Thumbnail area */}
                                                <div className="h-48 relative bg-[var(--kf-bg)] overflow-hidden">
                                                    {isDone && m.component_code ? (
                                                        <ScaledHtmlPreview
                                                            title={m.name}
                                                            html={m.component_code}
                                                            baseWidth={MOCKUP_PREVIEW_SIZE.width}
                                                            baseHeight={MOCKUP_PREVIEW_SIZE.height}
                                                            className="h-full w-full"
                                                        />
                                                    ) : isGen ? (
                                                        <div className="h-full flex items-center justify-center">
                                                            <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                                                        </div>
                                                    ) : m.status === "error" ? (
                                                        <div className="h-full flex items-center justify-center text-red-400 text-xs">Failed</div>
                                                    ) : (
                                                        <div className="h-full flex items-center justify-center">
                                                            <Palette className="w-6 h-6 text-zinc-700" />
                                                        </div>
                                                    )}
                                                    {/* Stop button for individual */}
                                                    {isGen && (
                                                        <button
                                                            onClick={() => handleStop(m.id)}
                                                            className="absolute top-2 right-2 h-6 px-2 rounded bg-red-600/30 border border-red-600/40 text-red-300 text-[10px] flex items-center gap-1 hover:bg-red-600/40"
                                                        >
                                                            <Square className="w-2.5 h-2.5 fill-current" /> Stop
                                                        </button>
                                                    )}
                                                </div>

                                                {/* Info bar */}
                                                <div className="px-3 py-2.5 border-t border-[var(--kf-border)]/40">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-xs font-semibold text-[var(--kf-text)] truncate">{m.name}</span>
                                                        {isDone && (
                                                            <span className="text-[10px] text-emerald-400 font-semibold flex items-center gap-0.5">
                                                                <Check className="w-2.5 h-2.5" /> Done
                                                            </span>
                                                        )}
                                                        {isGen && (
                                                            <span className="text-[10px] text-purple-400">Generating...</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            </div>
                        </motion.div>
                    )}

                    {/* ── PHASE: GALLERY ───────────────────────────────────── */}
                    {phase === "gallery" && (
                        <motion.div
                            key="gallery"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            className="h-full flex flex-col"
                        >
                            {/* Gallery header */}
                            <div className="px-6 pt-5 pb-4 border-b border-[var(--kf-border)]/40">
                                <div className="flex items-center justify-between">
                                    <div>
                                        <h3 className="text-lg font-bold text-[var(--kf-text)]">Design Gallery</h3>
                                        <p className="text-xs text-[var(--kf-text-secondary)] mt-1">
                                            {generatedCount} designs generated &middot; Click to preview and refine
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => setPhase("discovery")}
                                            className="h-8 px-3 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)] text-xs flex items-center gap-1.5"
                                        >
                                            <Eye className="w-3.5 h-3.5" /> View Screens
                                        </button>
                                        <button
                                            onClick={handleOpenDirections}
                                            className="h-8 px-3 rounded-md border border-[var(--kf-border-muted)] hover:border-purple-500/40 text-[var(--kf-text-secondary)] hover:text-purple-300 text-xs flex items-center gap-1.5 transition-colors"
                                        >
                                            <Compass className="w-3.5 h-3.5" /> New Direction
                                        </button>
                                        <button
                                            onClick={() => handleGenerateAll()}
                                            disabled={generating}
                                            className="h-8 px-4 rounded-md bg-gradient-to-r from-purple-600 to-violet-500 hover:from-purple-500 hover:to-violet-400 text-white text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
                                        >
                                            <RefreshCw className="w-3.5 h-3.5" /> Regenerate All
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {/* Gallery grid */}
                            <div className="flex-1 overflow-y-auto px-6 py-5">
                                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                                    {mockups.map((m, i) => {
                                        const isDone = m.status === "complete" || m.status === "approved";
                                        const isGen = m.status === "generating" || regeneratingIds.has(m.id);
                                        return (
                                            <motion.div
                                                key={m.id}
                                                initial={{ opacity: 0, y: 15 }}
                                                animate={{ opacity: 1, y: 0 }}
                                                transition={{ delay: i * 0.05 }}
                                                className={`group rounded-xl border overflow-hidden bg-[var(--kf-surface)] transition-all cursor-pointer hover:shadow-xl hover:shadow-purple-500/5 ${
                                                    m.status === "approved"
                                                        ? "border-emerald-500/30 hover:border-emerald-500/50"
                                                        : "border-[var(--kf-border)]/60 hover:border-[var(--kf-border-muted)]"
                                                }`}
                                                onClick={() => isDone && setExpandedMockupId(m.id)}
                                            >
                                                {/* Thumbnail */}
                                                <div className="h-56 relative bg-[var(--kf-bg)] overflow-hidden">
                                                    {isDone && m.component_code ? (
                                                        <ScaledHtmlPreview
                                                            title={m.name}
                                                            html={m.component_code}
                                                            baseWidth={MOCKUP_PREVIEW_SIZE.width}
                                                            baseHeight={MOCKUP_PREVIEW_SIZE.height}
                                                            className="h-full w-full"
                                                        />
                                                    ) : isGen ? (
                                                        <div className="h-full flex flex-col items-center justify-center">
                                                            <Loader2 className="w-6 h-6 text-purple-400 animate-spin mb-2" />
                                                            <span className="text-xs text-zinc-500">Generating...</span>
                                                        </div>
                                                    ) : m.status === "error" ? (
                                                        <div className="h-full flex flex-col items-center justify-center">
                                                            <span className="text-red-400 text-xs mb-2">Generation failed</span>
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRegenerateSingle(m.id); }}
                                                                className="h-7 px-3 rounded-md border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] text-[11px] flex items-center gap-1"
                                                            >
                                                                <RefreshCw className="w-3 h-3" /> Retry
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <div className="h-full flex flex-col items-center justify-center">
                                                            <Palette className="w-6 h-6 text-zinc-700 mb-2" />
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRegenerateSingle(m.id); }}
                                                                className="h-7 px-3 rounded-md bg-purple-600/20 border border-purple-600/30 text-purple-300 text-[11px] flex items-center gap-1"
                                                            >
                                                                <Zap className="w-3 h-3" /> Generate
                                                            </button>
                                                        </div>
                                                    )}

                                                    {/* Expand icon overlay */}
                                                    {isDone && (
                                                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                                                            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-2">
                                                                <Maximize2 className="w-5 h-5 text-white" />
                                                            </div>
                                                        </div>
                                                    )}

                                                    {/* Status badge */}
                                                    {m.status === "approved" && (
                                                        <div className="absolute top-2 left-2 h-5 px-2 rounded-full bg-emerald-600/80 text-white text-[10px] flex items-center gap-1 backdrop-blur-sm">
                                                            <Check className="w-2.5 h-2.5" /> Approved
                                                        </div>
                                                    )}

                                                    {/* Stop button */}
                                                    {isGen && (
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleStop(m.id); }}
                                                            className="absolute top-2 right-2 h-6 px-2 rounded bg-red-600/30 border border-red-600/40 text-red-300 text-[10px] flex items-center gap-1 hover:bg-red-600/40"
                                                        >
                                                            <Square className="w-2.5 h-2.5 fill-current" /> Stop
                                                        </button>
                                                    )}
                                                </div>

                                                {/* Info bar */}
                                                <div className="px-4 py-3 border-t border-[var(--kf-border)]/40">
                                                    <div className="flex items-center justify-between mb-1">
                                                        <h4 className="text-sm font-bold text-[var(--kf-text)] truncate">{m.name}</h4>
                                                        <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border ${PRIORITY_COLORS[m.priority]}`}>
                                                            {m.priority}
                                                        </span>
                                                    </div>
                                                    <p className="text-xs text-[var(--kf-text-secondary)] line-clamp-1 mb-2">{m.description}</p>

                                                    {/* Actions */}
                                                    <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        {isGen ? (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleStop(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-red-600/40 text-red-400 hover:bg-red-600/20 flex items-center gap-1"
                                                            >
                                                                <Square className="w-2.5 h-2.5 fill-current" /> Stop
                                                            </button>
                                                        ) : (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRegenerateSingle(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] flex items-center gap-1"
                                                            >
                                                                <RefreshCw className="w-2.5 h-2.5" /> Regen
                                                            </button>
                                                        )}
                                                        {m.status === "complete" && (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleApprove(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-emerald-700/60 text-emerald-400 hover:bg-emerald-600/20 flex items-center gap-1"
                                                            >
                                                                <Check className="w-2.5 h-2.5" /> Approve
                                                            </button>
                                                        )}
                                                        {isDone && (
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); handleRequestRevision(m.id); }}
                                                                className="h-6 px-2 rounded text-[10px] border border-[var(--kf-border-muted)] text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] flex items-center gap-1"
                                                            >
                                                                <MessageSquare className="w-2.5 h-2.5" /> Revise
                                                            </button>
                                                        )}
                                                        <div className="flex-1" />
                                                        <button
                                                            onClick={(e) => { e.stopPropagation(); handleDelete(m.id, m.name); }}
                                                            className="h-6 w-6 rounded flex items-center justify-center text-zinc-600 hover:text-red-400 hover:bg-red-500/10"
                                                        >
                                                            <Trash2 className="w-3 h-3" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </motion.div>
                                        );
                                    })}
                                </div>
                            </div>

                            {/* Bottom dock */}
                            <div className="border-t border-[var(--kf-border)]/60 bg-[var(--kf-surface)] px-6 py-3 flex items-center gap-3 shrink-0">
                                <div className="flex items-center gap-2 flex-1 max-w-md">
                                    <Plus className="w-4 h-4 text-zinc-500 shrink-0" />
                                    <input
                                        type="text"
                                        value={addScreenName}
                                        onChange={(e) => setAddScreenName(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleAddScreen()}
                                        placeholder="Add a screen..."
                                        className="flex-1 h-8 bg-[var(--kf-surface)] border border-[var(--kf-border-muted)] rounded-lg px-3 text-xs text-[var(--kf-text)] placeholder:text-[var(--kf-text-faint)] focus:outline-none focus:border-purple-500/50"
                                    />
                                    <button
                                        onClick={handleAddScreen}
                                        disabled={!addScreenName.trim()}
                                        className="h-8 px-3 rounded-lg bg-[var(--kf-badge-bg)] hover:bg-[var(--kf-hover-bg)] text-xs text-[var(--kf-text-secondary)] disabled:opacity-30"
                                    >
                                        Add
                                    </button>
                                </div>
                                <div className="flex-1" />
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* ── Direction picker modal ────────────────────────────────── */}
            <AnimatePresence>
                {showDirections && (
                    <DirectionPickerModal
                        directions={directions}
                        loadingDirections={loadingDirections}
                        onPick={handlePickDirection}
                        onDescribe={handleDescribeDirection}
                        onClose={() => { setShowDirections(false); handleStopDirections(); }}
                        onStopLoading={handleStopDirections}
                    />
                )}
            </AnimatePresence>

            {/* ── Design preferences modal ─────────────────────────────── */}
            <AnimatePresence>
                {showPreferences && (
                    <DesignPreferencesModal
                        onConfirm={handleConfirmPreferences}
                        onClose={() => setShowPreferences(false)}
                        saving={savingPreferences}
                    />
                )}
            </AnimatePresence>

            {/* ── Expanded preview overlay ──────────────────────────────── */}
            <AnimatePresence>
                {expandedMockup && (() => {
                    const navigable = mockups.filter(m => m.status === "complete" || m.status === "approved");
                    const idx = navigable.findIndex(m => m.id === expandedMockup.id);
                    const goPrev = () => idx > 0 && setExpandedMockupId(navigable[idx - 1].id);
                    const goNext = () => idx < navigable.length - 1 && setExpandedMockupId(navigable[idx + 1].id);
                    return (
                        <PreviewOverlay
                            mockup={expandedMockup}
                            previewDevice={previewDevice}
                            setPreviewDevice={setPreviewDevice}
                            onClose={() => setExpandedMockupId(null)}
                            onPrev={goPrev}
                            onNext={goNext}
                            hasPrev={idx > 0}
                            hasNext={idx < navigable.length - 1}
                            onRegenerate={() => handleRegenerateSingle(expandedMockup.id)}
                            onApprove={() => handleApprove(expandedMockup.id)}
                            onRevise={() => handleRequestRevision(expandedMockup.id)}
                            onDelete={() => handleDelete(expandedMockup.id, expandedMockup.name)}
                            isRegenerating={regeneratingIds.has(expandedMockup.id) || expandedMockup.status === "generating"}
                        />
                    );
                })()}
            </AnimatePresence>

            {/* ── Error toast ───────────────────────────────────────────── */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 20 }}
                        className="fixed bottom-6 right-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center gap-3 z-50"
                    >
                        {error}
                        <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
                            <X className="w-4 h-4" />
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
