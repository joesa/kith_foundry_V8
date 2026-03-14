import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";

// Auth
import LoginPage from "./components/auth/LoginPage";
import SignUpPage from "./components/auth/SignUpPage";

// Shared
import Layout from "./components/shared/Layout";
import ProtectedRoute from "./components/shared/ProtectedRoute";
import NotFoundPage from "./components/shared/NotFoundPage";

// Pages
import DashboardPage from "./components/project/DashboardPage";
import IdeationLanding from "./components/ideation/IdeationLanding";
import IdeaPromptPage from "./components/ideation/IdeaPromptPage";
import DiscoverIdeaPage from "./components/ideation/DiscoverIdeaPage";
import IdeaResults from "./components/ideation/IdeaResults";
import SavedIdeasPage from "./components/ideation/SavedIdeasPage";
import CSuiteAnalysisPage from "./components/csuite/CSuiteAnalysisPage";
import ProjectDashboardPage from "./components/project/ProjectDashboardPage";
import DesignStudioPage from "./components/design/DesignStudioPage";
import Workspace from "./components/Workspace";
import ProfilePage from "./components/profile/ProfilePage";
import PricingPage from "./components/billing/PricingPage";
import BillingPage from "./components/billing/BillingPage";

function AppContent() {
    const { user, loading } = useAuth();
    const { theme } = useTheme();

    if (loading) {
        return (
            <div className={[
                "min-h-screen flex items-center justify-center transition-colors duration-300",
                theme === "dark" ? "bg-[#0A0A10]" : "bg-[#F8F9FA]",
            ].join(" ")}>
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    return (
        <Routes>
            {/* Public auth routes */}
            <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
            <Route path="/signup" element={user ? <Navigate to="/" replace /> : <SignUpPage />} />

            {/* Protected routes with shared layout */}
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/ideation" element={<IdeationLanding />} />
                <Route path="/ideation/prompt" element={<IdeaPromptPage />} />
                <Route path="/ideation/discover" element={<DiscoverIdeaPage />} />
                <Route path="/ideation/results/:sessionId" element={<IdeaResults />} />
                <Route path="/ideation/saved" element={<SavedIdeasPage />} />
                <Route path="/csuite/:projectId" element={<CSuiteAnalysisPage />} />
                <Route path="/project/:projectId" element={<ProjectDashboardPage />} />
                <Route path="/project/:projectId/design-studio" element={<DesignStudioPage />} />
                <Route path="/profile" element={<ProfilePage />} />
                <Route path="/pricing" element={<PricingPage />} />
                <Route path="/billing" element={<BillingPage />} />
            </Route>

            {/* Editor — full-screen, own layout (no top nav) */}
            <Route
                path="/project/:projectId/editor"
                element={<ProtectedRoute><Workspace /></ProtectedRoute>}
            />

            {/* Catch-all */}
            <Route
                path="*"
                element={user ? <ProtectedRoute><NotFoundPage /></ProtectedRoute> : <Navigate to="/login" replace />}
            />
        </Routes>
    );
}

export default function App() {
    return (
        <ThemeProvider>
            <AppContent />
        </ThemeProvider>
    );
}
