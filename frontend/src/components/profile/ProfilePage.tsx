import { useAuth } from "../../contexts/AuthContext";
import { ProviderSettings } from "../ProviderSettings";
import { User } from "lucide-react";

export default function ProfilePage() {
    const { user } = useAuth();

    return (
        <div className="max-w-4xl mx-auto px-6 py-10">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center gap-3 mb-1">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shrink-0">
                        <User className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white">Profile & Settings</h1>
                        <p className="text-sm text-zinc-500">{user?.email}</p>
                    </div>
                </div>
            </div>

            {/* Provider / model settings — rendered inline (no modal overlay) */}
            <ProviderSettings inline />
        </div>
    );
}
