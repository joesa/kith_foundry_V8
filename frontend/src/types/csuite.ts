export type CSuiteRole =
    | "ceo" | "cpo" | "cto" | "cdo"
    | "cfo" | "cmo" | "coo" | "ciso"
    | "synthesizer";

export type AgentStatus = "pending" | "running" | "complete" | "error";
export type Verdict = "go" | "no_go" | "conditional";

export interface AgentResult {
    role: CSuiteRole;
    status: AgentStatus;
    score: number | null;
    recommendation: string | null;
    deep_analysis: string | null;
    strengths: string[];
    risks: string[];
    suggestions: string[];
    key_metrics: string[];
    timeline: string | null;
    priority_actions: string[];
    competitive_note: string | null;
    verdict: Verdict | null;
    error_message?: string | null;
}

export interface CSuiteStatusResponse {
    agents: AgentResult[];
    project_name?: string;
    overall_score?: number | null;
    overall_verdict?: string | null;
}

export interface ImprovementDetail {
    current_score: number;
    key_weaknesses: string[];
    recommended_changes: string[];
    enhanced_context: string;
}

export interface ImprovementPlan {
    improvements: Record<string, ImprovementDetail>;
    summary: string;
}
