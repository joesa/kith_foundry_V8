export type SecretProvider =
    | "openai" | "anthropic" | "google" | "supabase" | "stripe" | "custom";

export interface StoredSecret {
    id: string;
    provider: SecretProvider;
    label: string;
    created_at: string;
    last_accessed_at?: string;
}

export interface SecretSubmission {
    provider: SecretProvider;
    label: string;
    value: string;
}

export interface SecretListResponse {
    secrets: StoredSecret[];
}
