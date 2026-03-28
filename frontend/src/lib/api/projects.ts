import type { Project, ProjectListResponse } from "../../types";
import { apiRequest } from "./client";

export const projectsApi = {
    list: (token: string) =>
        apiRequest<ProjectListResponse>("/api/v1/projects", token),

    get: (token: string, projectId: string) =>
        apiRequest<Project>(`/api/v1/projects/${projectId}`, token),

    delete: (token: string, projectId: string) =>
        apiRequest<void>(`/api/v1/projects/${projectId}`, token, { method: "DELETE" }),
};
