import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { ThemeProvider, useTheme } from "./contexts/ThemeContext";

// Auth
const LoginPage = lazy(() => import("./components/auth/LoginPage"));
const SignUpPage = lazy(() => import("./components/auth/SignUpPage"));

// Shared
import Layout from "./components/shared/Layout";
import ProtectedRoute from "./components/shared/ProtectedRoute";
const NotFoundPage = lazy(() => import("./components/shared/NotFoundPage"));

// Pages
const DashboardPage = lazy(() => import("./components/project/DashboardPage"));
const IdeationLanding = lazy(() => import("./components/ideation/IdeationLanding"));
const IdeaPromptPage = lazy(() => import("./components/ideation/IdeaPromptPage"));
const DiscoverIdeaPage = lazy(() => import("./components/ideation/DiscoverIdeaPage"));
const IdeaResults = lazy(() => import("./components/ideation/IdeaResults"));
const SavedIdeasPage = lazy(() => import("./components/ideation/SavedIdeasPage"));
const CSuiteAnalysisPage = lazy(() => import("./components/csuite/CSuiteAnalysisPage"));
const ProjectDashboardPage = lazy(() => import("./components/project/ProjectDashboardPage"));
const DesignStudioPage = lazy(() => import("./components/design/DesignStudioPage"));
const Workspace = lazy(() => import("./components/Workspace"));
const ProfilePage = lazy(() => import("./components/profile/ProfilePage"));
const PricingPage = lazy(() => import("./components/billing/PricingPage"));
const BillingPage = lazy(() => import("./components/billing/BillingPage"));


function RouteFallback() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-[var(--bg-primary,#0A0A10)]">
            <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
        </div>
    );
}

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
        <Suspense fallback={<RouteFallback />}>
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
        </Suspense>
    );
}

export default function App() {
    return (
        <ThemeProvider>
            <AppContent />
        </ThemeProvider>
    );
}
