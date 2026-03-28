import { lazy, Suspense, type ComponentType } from "react";
import { Routes, Route, Navigate, useParams, generatePath } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";

const CHUNK_RETRY_KEY = "kith.chunk-retry";

function isDynamicImportFailure(error: unknown): boolean {
  const message = String((error as { message?: string })?.message ?? error ?? "").toLowerCase();
  return (
    message.includes("failed to fetch dynamically imported module") ||
    message.includes("importing a module script failed") ||
    message.includes("chunkloaderror") ||
    message.includes("loading chunk")
  );
}

function lazyWithRetry<T extends { default: ComponentType<any> }>(
  importer: () => Promise<T>
) {
  return lazy(async () => {
    try {
      const module = await importer();
      if (typeof window !== "undefined") {
        window.sessionStorage.removeItem(CHUNK_RETRY_KEY);
      }
      return module;
    } catch (error) {
      if (typeof window !== "undefined" && isDynamicImportFailure(error)) {
        const hasRetried = window.sessionStorage.getItem(CHUNK_RETRY_KEY) === "1";
        if (!hasRetried) {
          window.sessionStorage.setItem(CHUNK_RETRY_KEY, "1");
          window.location.reload();
          return new Promise<never>(() => {
            // Intentionally unresolved: the page reload interrupts this render path.
          });
        }
        window.sessionStorage.removeItem(CHUNK_RETRY_KEY);
      }
      throw error;
    }
  });
}

const LoginPage = lazyWithRetry(() => import("./features/auth/LoginPage"));
const SignUpPage = lazyWithRetry(() => import("./features/auth/SignUpPage"));

import ProtectedRoute from "./components/system/ProtectedRoute";
const NotFoundPage = lazyWithRetry(() => import("./components/system/NotFoundPage"));
const AppShell = lazyWithRetry(() => import("./layouts/AppShell").then(m => ({ default: m.AppShell })));
const ProjectShell = lazyWithRetry(() => import("./components/system/ProjectShell"));

const LandingPage = lazyWithRetry(() => import("./features/landing/LandingPage"));
const DashboardPage = lazyWithRetry(() => import("./features/dashboard/DashboardPage"));
const HomePage = lazyWithRetry(() => import("./features/home/HomePage"));
const ProjectDashboardPage = lazyWithRetry(() => import("./features/dashboard/ProjectDashboardPage"));
const IdeationLanding = lazyWithRetry(() => import("./features/ideas/IdeationLanding"));
const IdeaPromptPage = lazyWithRetry(() => import("./features/ideas/IdeaPromptPage"));
const DiscoverIdeaPage = lazyWithRetry(() => import("./features/ideas/DiscoverIdeaPage"));
const SavedIdeasPage = lazyWithRetry(() => import("./features/ideas/SavedIdeasPage"));
const CSuiteAnalysisPage = lazyWithRetry(() => import("./features/executive/CSuiteAnalysisPage"));
const DesignStudioPage = lazyWithRetry(() => import("./features/design-studio/DesignStudioPage"));
const CapabilityGatePage = lazyWithRetry(() => import("./features/capabilities/CapabilityGatePage"));
const SecretsPage = lazyWithRetry(() => import("./features/secrets/SecretsPage"));
const PrdArchitecturePage = lazyWithRetry(() => import("./features/prd/PrdArchitecturePage"));
const DeploymentPage = lazyWithRetry(() => import("./features/deploy/DeploymentPage"));
const Workspace = lazyWithRetry(() => import("./features/build/Workspace"));
const ProfilePage = lazyWithRetry(() => import("./features/profile/ProfilePage"));
const PricingPage = lazyWithRetry(() => import("./features/billing/PricingPage"));
const BillingPage = lazyWithRetry(() => import("./features/billing/BillingPage"));

function RouteFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

function ParamRedirect({ to }: { to: string }) {
  const params = useParams();
  return <Navigate to={generatePath(to, params)} replace />;
}

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/" element={user ? <Navigate to="/app/home" replace /> : <LandingPage />} />
        <Route path="/login" element={user ? <Navigate to="/app/home" replace /> : <LoginPage />} />
        <Route path="/signup" element={user ? <Navigate to="/app/home" replace /> : <SignUpPage />} />
        <Route path="/pricing" element={<PricingPage />} />
        <Route path="/app/projects/new/ideas" element={<Navigate to="/app/ideation" replace />} />

        <Route path="/app" element={<ProtectedRoute><AppShell /></ProtectedRoute>}>
          <Route index element={<Navigate to="home" replace />} />
          <Route path="home" element={<HomePage />} />
          <Route path="projects" element={<DashboardPage />} />
          <Route path="settings" element={<Navigate to="/app/profile" replace />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="billing" element={<BillingPage />} />

          <Route path="ideation" element={<IdeationLanding />} />
          <Route path="ideation/prompt" element={<IdeaPromptPage />} />
          <Route path="ideation/discover" element={<DiscoverIdeaPage />} />
          <Route path="ideation/saved" element={<SavedIdeasPage />} />
          <Route path="projects/new/ideas" element={<Navigate to="/app/ideation" replace />} />

          <Route path="projects/:projectId" element={<ProjectShell />}>
            <Route index element={<ProjectDashboardPage />} />
            <Route path="prompt" element={<IdeaPromptPage />} />
            <Route path="ideas" element={<IdeationLanding />} />
            <Route path="saved-ideas" element={<SavedIdeasPage />} />
            <Route path="executive" element={<CSuiteAnalysisPage />} />
            <Route path="prd" element={<PrdArchitecturePage />} />
            <Route path="design" element={<DesignStudioPage />} />
            <Route path="capabilities" element={<CapabilityGatePage />} />
            <Route path="build" element={<Workspace />} />
            <Route path="secrets" element={<SecretsPage />} />
            <Route path="deploy" element={<DeploymentPage />} />
          </Route>
        </Route>

        <Route path="/ideation" element={<Navigate to="/app/ideation" replace />} />
        <Route path="/ideation/*" element={<Navigate to="/app/ideation" replace />} />
        <Route path="/project/:projectId" element={<ParamRedirect to="/app/projects/:projectId" />} />
        <Route path="/project/:projectId/editor" element={<ParamRedirect to="/app/projects/:projectId/build" />} />
        <Route path="/csuite/:projectId" element={<ParamRedirect to="/app/projects/:projectId/executive" />} />

        <Route path="*" element={user ? <NotFoundPage /> : <Navigate to="/login" replace />} />
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
