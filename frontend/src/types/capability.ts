export interface CapabilityChoices {
    wants_database: boolean;
    wants_auth: boolean;
    wants_ai: boolean;
    notes?: string;
}

export interface CapabilityResponse {
    id: string;
    project_id: string;
    choices: CapabilityChoices;
    created_at: string;
}
