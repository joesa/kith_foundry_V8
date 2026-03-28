import type { CSuiteStatusResponse, ImprovementPlan } from "../../types";
import { apiRequest } from "./client";

export const csuiteApi = {
    status: (token: string, projectId: string) =>
        apiRequest<CSuiteStatusResponse>(`/api/v1/csuite/${projectId}/status`, token),

    run: (token: string, projectId: string) =>
        apiRequest<{ project_name: string }>(`/api/v1/csuite/${projectId}/run`, token, { method: "POST" }),

    refine: (token: string, projectId: string, corrections: string) =>
        apiRequest<void>(`/api/v1/csuite/${projectId}/refine`, token, {
            method: "POST",
            body: JSON.stringify({ corrections }),
        }),

    stop: (token: string, projectId: string) =>
        apiRequest<void>(`/api/v1/csuite/${projectId}/stop`, token, { method: "POST" }),

    stopAgent: (token: string, projectId: string, role: string) =>
        apiRequest<void>(`/api/v1/csuite/${projectId}/stop/${role}`, token, { method: "POST" }),

    improve: (token: string, projectId: string, roles?: string[]) =>
        apiRequest<ImprovementPlan>(`/api/v1/csuite/${projectId}/improve`, token, {
            method: "POST",
            body: JSON.stringify({ roles: roles ?? null }),
        }),

    applyImprovement: (token: string, projectId: string, roles: string[], enhancedContext: string) =>
        apiRequest<void>(`/api/v1/csuite/${projectId}/improve/apply`, token, {
            method: "POST",
            body: JSON.stringify({ roles, enhanced_context: enhancedContext }),
        }),
};
