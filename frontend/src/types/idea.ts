export interface IdeaContent {
    description?: string;
    target_market?: string;
    target_audience?: string;
    problem_statement?: string;
    why_now?: string;
    revenue_model?: string;
    revenue_potential?: string;
    monthly_revenue_potential?: string;
    differentiator?: string;
    unique_angle?: string;
    key_features?: string[];
    how_it_works?: string;
    go_to_market?: string;
    pricing_model?: string;
    strategic_moat?: string;
    launch_plan_90_day?: string;
    tam?: string;
}

export interface SavedIdea {
    id: string;
    name: string;
    content: IdeaContent;
    score: number | null;
    source: string;
    is_claimed: boolean;
    claimed_by_other: boolean;
    created_at: string;
    saved_expires_at?: string | null;
    uniqueness_degraded?: boolean;
}

export interface Enhancement {
    name: string;
    description: string;
    differentiators: string[];
    target_market: string;
}

export interface SavedIdeasResponse {
    saved_ideas: SavedIdea[];
}

export interface EnhanceResponse {
    enhancements: Enhancement[];
}

export interface AcceptResponse {
    project_id: string;
}

export interface QuestionnaireResponse {
    ideas: IdeaContent[];
}
