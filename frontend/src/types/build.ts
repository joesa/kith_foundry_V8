export type BuildStage =
    | "idle"
    | "queued"
    | "planning"
    | "generating_code"
    | "building"
    | "repairing"
    | "ready_for_preview"
    | "failed";

export type ChatState =
    | "idle"
    | "sending"
    | "processing"
    | "patch_ready"
    | "applying"
    | "rebuilding"
    | "completed"
    | "error";

export interface SandboxStatus {
    id: string;
    project_id: string;
    status: "provisioning" | "running" | "stopped" | "error";
    fly_app_id?: string;
    preview_url?: string;
}

export interface CodePatch {
    id: string;
    file_path: string;
    diff: string;
    status: "proposed" | "accepted" | "rejected" | "applied";
    agent_role: string;
    created_at: string;
}
