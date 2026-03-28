export type ArtifactType =
    | "executive_brief"
    | "product_requirements"
    | "tech_architecture"
    | "db_plan"
    | "auth_plan"
    | "prd"
    | "tech_spec"
    | "market_analysis"
    | "go_to_market"
    | "user_personas"
    | "competitive_matrix"
    | "roadmap"
    | "monetization"
    | "design_system";

export interface Artifact {
    id: string;
    project_id: string;
    type: ArtifactType;
    title: string;
    content: string;
    version: number;
    status: "pending" | "generating" | "complete";
    created_at: string;
    updated_at: string;
}

export interface ArtifactListResponse {
    artifacts: Artifact[];
}
