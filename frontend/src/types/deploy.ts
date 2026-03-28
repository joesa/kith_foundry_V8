export type DeployState =
    | "idle"
    | "connecting_git"
    | "committing"
    | "deploying"
    | "deployed"
    | "failed";

export interface Deployment {
    id: string;
    project_id: string;
    provider: "vercel" | "other";
    status: DeployState;
    url?: string;
    commit_sha?: string;
    branch?: string;
    created_at: string;
}

export interface DeploymentListResponse {
    deployments: Deployment[];
}
