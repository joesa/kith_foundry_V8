import type { SandboxStatus } from "../../types";
import { apiRequest } from "./client";

export const sandboxApi = {
    status: (token: string, projectId: string) =>
        apiRequest<SandboxStatus>(`/api/v1/projects/${projectId}/sandbox/status`, token),

    logs: (token: string, projectId: string, tail?: number) =>
        apiRequest<{ logs: string[] }>(`/api/v1/projects/${projectId}/sandbox/logs${tail ? `?tail=${tail}` : ""}`, token),
};
