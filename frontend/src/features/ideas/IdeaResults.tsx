import { Link, useNavigate, useParams } from "react-router-dom";

export default function IdeaResults() {
    const navigate = useNavigate();
    const { sessionId } = useParams<{ sessionId: string }>();

    return (
        <div className="max-w-4xl mx-auto px-6 py-12">
            <button
                onClick={() => navigate("/app/ideation/discover")}
                className="mb-6 inline-flex items-center gap-2 text-xs font-black uppercase tracking-widest text-tertiary hover:text-on-surface transition-colors"
            >
                <span className="material-symbols-outlined text-base leading-none">arrow_back</span>
                Back to Discovery
            </button>

            <div className="steel-gradient ghost-border rounded-[var(--radius-module)] p-8 sm:p-10">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-black bg-primary-container text-on-primary-container border border-outline-variant/20 mb-4 uppercase tracking-widest">
                    <span className="material-symbols-outlined text-base leading-none">lightbulb</span>
                    Ideation Session
                </div>
                <h1 className="text-2xl sm:text-3xl font-black text-on-surface mb-3 uppercase" style={{ letterSpacing: "-0.05em" }}>
                    Session {sessionId ? sessionId.slice(0, 8) : "Unknown"} is no longer stored as a standalone page.
                </h1>
                <p className="text-sm sm:text-base max-w-2xl mb-8 text-secondary">
                    Ideation results are now presented directly inside the discovery flow so you can compare ideas, save options, and launch C-Suite analysis without context switching.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <Link
                        to="/app/ideation/discover"
                        className="flex items-center justify-center gap-2 h-11 rounded-full bg-primary-container text-on-primary-container text-xs font-black uppercase tracking-widest hover:opacity-80 transition-opacity"
                    >
                        <span className="material-symbols-outlined text-base leading-none">arrow_forward</span>
                        Open Discovery Flow
                    </Link>
                    <Link
                        to="/app/ideation"
                        className="flex items-center justify-center gap-2 h-11 rounded-full border border-outline-variant/30 text-secondary text-xs font-black uppercase tracking-widest hover:bg-surface-container hover:text-on-surface transition-colors"
                    >
                        <span className="material-symbols-outlined text-base leading-none">lightbulb</span>
                        Go to Ideation Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
