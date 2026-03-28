import type { DeploymentListResponse } from "../../types";
import { apiRequest } from "./client";

export const deployApi = {
    connectGit: (token: string, projectId: string, repoUrl: string) =>
        apiRequest<{ connected: boolean }>(`/api/v1/projects/${projectId}/deploy/git-connect`, token, {
            method: "POST",
            body: JSON.stringify({ repo_url: repoUrl }),
        }),

    commit: (token: string, projectId: string, message: string) =>
        apiRequest<{ commit_sha: string }>(`/api/v1/projects/${projectId}/deploy/commit`, token, {
            method: "POST",
            body: JSON.stringify({ message }),
        }),

    deployVercel: (token: string, projectId: string) =>
        apiRequest<{ deployment_id: string; url: string }>(`/api/v1/projects/${projectId}/deploy/vercel`, token, {
            method: "POST",
        }),

    list: (token: string, projectId: string) =>
        apiRequest<DeploymentListResponse>(`/api/v1/projects/${projectId}/deployments`, token),
};
