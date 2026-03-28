export type ProjectStatus =
    | "ideation"
    | "csuite_pending"
    | "csuite_running"
    | "csuite_complete"
    | "prd_generating"
    | "prd_complete"
    | "design_generating"
    | "design_complete"
    | "capability_gate"
    | "secrets_pending"
    | "building"
    | "build_complete"
    | "deployed";

export interface Project {
    id: string;
    name: string;
    description: string | null;
    status: ProjectStatus;
    overall_score: number | null;
    overall_verdict: "go" | "no_go" | "conditional" | null;
    idea_source: string | null;
    created_at: string;
    updated_at: string;
}

export interface ProjectListResponse {
    projects: Project[];
}
