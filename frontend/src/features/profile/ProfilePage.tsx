import { useAuth } from "../../contexts/AuthContext";
import { ProviderSettings } from "../../components/workspace/ProviderSettings";

export default function ProfilePage() {
    const { user } = useAuth();

    return (
        <div className="max-w-4xl mx-auto px-6 py-10">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-on-primary-container text-lg">person</span>
                    </div>
                    <div>
                        <h1 className="text-2xl font-black uppercase text-on-surface" style={{ letterSpacing: '-0.05em' }}>
                            Profile &amp; Settings
                        </h1>
                        <p className="text-xs font-black uppercase tracking-widest text-tertiary">{user?.email}</p>
                    </div>
                </div>
            </div>

            {/* Provider / model settings — rendered inline (no modal overlay) */}
            <ProviderSettings inline />
        </div>
    );
}
