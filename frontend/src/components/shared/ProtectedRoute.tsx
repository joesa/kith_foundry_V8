import { Navigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { useTheme } from "../../contexts/ThemeContext";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { user, loading } = useAuth();
    const { theme } = useTheme();

    if (loading) {
        return (
            <div className={`min-h-screen flex items-center justify-center ${theme === "dark" ? "bg-[#0A0A10]" : "bg-[#F8F9FA]"}`}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/login" replace />;
    }

    return <>{children}</>;
}
