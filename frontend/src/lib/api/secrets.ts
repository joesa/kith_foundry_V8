import type { SecretListResponse, SecretSubmission } from "../../types";
import { apiRequest } from "./client";

export const secretsApi = {
    list: (token: string, projectId: string) =>
        apiRequest<SecretListResponse>(`/api/v1/projects/${projectId}/secrets`, token),

    submit: (token: string, projectId: string, secret: SecretSubmission) =>
        apiRequest<{ id: string }>(`/api/v1/projects/${projectId}/secrets`, token, {
            method: "POST",
            body: JSON.stringify(secret),
        }),

    revoke: (token: string, secretId: string) =>
        apiRequest<void>(`/api/v1/secrets/${secretId}/revoke`, token, { method: "POST" }),
};
