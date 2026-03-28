import type { SavedIdeasResponse, EnhanceResponse, AcceptResponse, QuestionnaireResponse } from "../../types";
import { apiRequest } from "./client";

export const ideationApi = {
    enhance: (token: string, prompt: string) =>
        apiRequest<EnhanceResponse>("/api/v1/ideation/enhance", token, {
            method: "POST",
            body: JSON.stringify({ prompt }),
        }),

    accept: (token: string, payload: {
        name: string;
        description?: string;
        target_audience?: string;
        problem_statement?: string;
        source?: string;
        original_prompt?: string;
        idea_content?: Record<string, unknown>;
    }) =>
        apiRequest<AcceptResponse>("/api/v1/ideation/accept", token, {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    save: (token: string, payload: {
        name: string;
        content: Record<string, unknown>;
        score: number | null;
        source: string;
    }) =>
        apiRequest<{ id: string }>("/api/v1/ideation/save", token, {
            method: "POST",
            body: JSON.stringify(payload),
        }),

    listSaved: (token: string) =>
        apiRequest<SavedIdeasResponse>("/api/v1/ideation/saved", token),

    deleteSaved: (token: string, id: string) =>
        apiRequest<void>(`/api/v1/ideation/saved/${id}`, token, { method: "DELETE" }),

    generateUnique: (token: string) =>
        apiRequest<{ idea: Record<string, unknown> }>("/api/v1/ideation/generate-unique", token, { method: "POST" }),

    questionnaire: (token: string, responses: Record<number, unknown>) =>
        apiRequest<QuestionnaireResponse>("/api/v1/ideation/questionnaire", token, {
            method: "POST",
            body: JSON.stringify({ responses }),
        }),
};
