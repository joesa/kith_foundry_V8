import type { CapabilityChoices, CapabilityResponse } from "../../types";
import { apiRequest } from "./client";

export const capabilitiesApi = {
    get: (token: string, projectId: string) =>
        apiRequest<CapabilityResponse>(`/api/v1/projects/${projectId}/capabilities`, token),

    set: (token: string, projectId: string, choices: CapabilityChoices) =>
        apiRequest<CapabilityResponse>(`/api/v1/projects/${projectId}/capabilities`, token, {
            method: "POST",
            body: JSON.stringify(choices),
        }),
};
