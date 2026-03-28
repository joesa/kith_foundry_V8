import type { ArtifactListResponse } from "../../types";
import { apiRequest } from "./client";

export const artifactsApi = {
    list: (token: string, projectId: string) =>
        apiRequest<ArtifactListResponse>(`/api/v1/projects/${projectId}/artifacts`, token),
};
