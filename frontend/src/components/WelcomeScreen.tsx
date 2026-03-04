import { useEffect, useState } from "react";
import { Sparkles, Code2, Layers, Zap, Palette, Globe } from "lucide-react";

const TIPS = [
    "\"Build me a beautiful todo app with dark mode\"",
    "\"Create a responsive landing page for a SaaS product\"",
    "\"Make a weather dashboard with animated icons\"",
    "\"Design a Kanban board with drag and drop\"",
    "\"Build an expense tracker with charts\"",
];

export function WelcomeScreen() {
    const [activeTip, setActiveTip] = useState(0);
    const [fadeIn, setFadeIn] = useState(false);

    useEffect(() => {
        const t = setTimeout(() => setFadeIn(true), 100);
        return () => clearTimeout(t);
    }, []);

    useEffect(() => {
        const interval = setInterval(() => {
            setActiveTip(prev => (prev + 1) % TIPS.length);
        }, 3500);
        return () => clearInterval(interval);
    }, []);

    return (
        <div
            className={`flex flex-col items-center justify-center h-full w-full transition-opacity duration-700 ${fadeIn ? "opacity-100" : "opacity-0"}`}
            style={{
                background: "linear-gradient(145deg, #0c0c14, #0e0f1a 40%, #110e1c 70%, #0c0c14)",
            }}
        >
            {/* Glow orbs */}
            <div style={{
                position: "absolute", top: "20%", left: "30%",
                width: 300, height: 300,
                background: "radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)",
                borderRadius: "50%", pointerEvents: "none",
                animation: "float 6s ease-in-out infinite",
            }} />
            <div style={{
                position: "absolute", bottom: "25%", right: "20%",
                width: 220, height: 220,
                background: "radial-gradient(circle, rgba(168,85,247,0.06) 0%, transparent 70%)",
                borderRadius: "50%", pointerEvents: "none",
                animation: "float 8s ease-in-out infinite reverse",
            }} />

            {/* Logo */}
            <div className="mb-6" style={{ animation: "float 3s ease-in-out infinite" }}>
                <div style={{
                    width: 56, height: 56,
                    borderRadius: 16,
                    background: "linear-gradient(135deg, #6366f1, #a855f7)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    boxShadow: "0 0 40px rgba(99,102,241,0.3), 0 0 80px rgba(168,85,247,0.15)",
                }}>
                    <Sparkles size={28} color="white" />
                </div>
            </div>

            {/* Title */}
            <h2 style={{
                fontSize: 26, fontWeight: 700,
                background: "linear-gradient(135deg, #818cf8, #c084fc, #f472b6)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                letterSpacing: -0.5,
                marginBottom: 8,
            }}>
                Kith Foundry
            </h2>
            <p style={{ color: "#71717a", fontSize: 13, marginBottom: 32, textAlign: "center", maxWidth: 260 }}>
                Describe your vision. We'll build it live.
            </p>

            {/* Feature cards */}
            <div style={{
                display: "grid", gridTemplateColumns: "1fr 1fr",
                gap: 10, marginBottom: 32, width: "100%", maxWidth: 300, padding: "0 16px",
            }}>
                {[
                    { icon: Code2, label: "Multi-file generation", delay: "0s" },
                    { icon: Layers, label: "Component architecture", delay: "0.1s" },
                    { icon: Palette, label: "Design system aware", delay: "0.2s" },
                    { icon: Globe, label: "Live preview", delay: "0.3s" },
                ].map(({ icon: Icon, label, delay }) => (
                    <div
                        key={label}
                        style={{
                            background: "rgba(255,255,255,0.03)",
                            border: "1px solid rgba(255,255,255,0.06)",
                            borderRadius: 10, padding: "12px 12px",
                            display: "flex", alignItems: "center", gap: 8,
                            animation: `slideUp 0.5s ease ${delay} both`,
                        }}
                    >
                        <Icon size={14} style={{ color: "#818cf8", flexShrink: 0 }} />
                        <span style={{ color: "#a1a1aa", fontSize: 11, lineHeight: 1.3 }}>{label}</span>
                    </div>
                ))}
            </div>

            {/* Rotating tip */}
            <div style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "rgba(99,102,241,0.06)",
                border: "1px solid rgba(99,102,241,0.12)",
                borderRadius: 8, padding: "8px 14px",
                maxWidth: 300,
            }}>
                <Zap size={12} style={{ color: "#6366f1", flexShrink: 0 }} />
                <p
                    key={activeTip}
                    style={{
                        color: "#71717a", fontSize: 11, fontStyle: "italic",
                        animation: "fadeInUp 0.4s ease",
                        margin: 0,
                    }}
                >
                    Try: {TIPS[activeTip]}
                </p>
            </div>

            {/* Subtle waiting indicator */}
            <div style={{
                position: "absolute", bottom: 20,
                display: "flex", alignItems: "center", gap: 6,
            }}>
                <div style={{
                    width: 5, height: 5, borderRadius: "50%",
                    background: "#6366f1",
                    animation: "pulse 2s ease-in-out infinite",
                }} />
                <span style={{ color: "#3f3f46", fontSize: 11 }}>
                    Ready when you are
                </span>
            </div>

            {/* Keyframe styles */}
            <style>{`
                @keyframes float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-8px); }
                }
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(12px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(4px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes pulse {
                    0%, 100% { opacity: 0.4; transform: scale(1); }
                    50% { opacity: 1; transform: scale(1.3); }
                }
            `}</style>
        </div>
    );
}
