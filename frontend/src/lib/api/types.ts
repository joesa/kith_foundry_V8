export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  status: string;
  stage: string;
  updated_at: string;
  active_agents: string[];
  created_at?: string;
}

export interface PlatformHome {
  orchestration_phase: string;
  orchestration_detail: string;
  primary_project_id: string | null;
  telemetry: Array<{
    key: string;
    title: string;
    subtitle: string;
    metric_label: string;
    metric_value: string;
    bar_label: string;
    bar_percent: number;
    footer: string;
    ribbon: 'cyan' | 'orange';
  }>;
  activity: Array<{
    agent: string;
    badge: string;
    badge_color: string;
    icon: string;
    border_class: string;
    message: string;
    time: string;
    tag_class?: string | null;
  }>;
  shell_lines: string[];
}

export interface ProjectOverview {
  project_name: string;
  stats: Array<{
    label: string;
    title: string;
    detail: string;
    ribbon: 'cyan' | 'ember';
  }>;
  artifacts: Array<{
    name: string;
    type: string;
    status: string;
    time: string;
  }>;
}

export interface IdeationStep {
  id: number;
  question: string;
  placeholder: string;
}

export interface CuratedIdea {
  id: string;
  title: string;
  sector: string;
  revenue: string;
  confidence: number;
  target_customer: string;
  pain_point: string;
  differentiation: string;
  monetization_model: string;
  execution_difficulty: string;
  market_opportunity: string;
  financial_upside: string;
  monthly_revenue_low: string;
  monthly_revenue_high: string;
  annual_revenue_low: string;
  annual_revenue_high: string;
  presentation_asset_url: string;
}

export interface ExecutiveReport {
  synthesis_title: string;
  synthesis_code: string;
  narrative_primary: string;
  narrative_secondary: string;
  tags: string[];
  chart_heights: number[];
  confidence_score: string;
  latency: string;
  agents: Array<{
    id: string;
    title: string;
    role: string;
    conviction: number;
    quote: string;
    border_color: string;
    avatar_url?: string;
    contribution?: string;
    analysis?: string;
    scoring?: Array<{ label: string; score: number; note: string }>;
    risk_flags?: string[];
    recommendation?: string;
  }>;
  timeline: Array<{
    time: string;
    label: string;
    detail: string;
    done: boolean;
  }>;
  telemetry_latency_ms: number;
  token_load_percent: number;
  analyzing?: boolean;
  project_name?: string;
  completed_roles?: string[];
}

export interface PlanningDoc {
  version_label: string;
  prd_sections: Array<{
    heading: string;
    body?: string | null;
    checklist?: [string, boolean][] | null;
  }>;
  phases: [string, string, string][]; // [label, status: 'complete'|'active'|'pending', route]
  stack_decisions: [string, string][];
}

export interface DesignStudio {
  metrics: Array<{ title: string; value: string; icon: string }>;
  pages: string[];
  tokens: Array<{ label: string; color: string }>;
  agent_name: string;
  agent_status: string;
}

export interface CapabilitiesResponse {
  choices: { database: boolean; authentication: boolean; ai_integration: boolean };
  cards: Array<{ key: string; title: string; description: string; icon: string }>;
}

export interface SecretEntry {
  provider: string;
  model: string;
  status: string;
}

export interface FileTreeNode {
  name: string;
  type: 'folder' | 'file';
  path: string;
  children?: FileTreeNode[] | null;
}

export interface CodeTreeResponse {
  roots: FileTreeNode[];
  default_path: string;
}

export interface CodeFileResponse {
  path: string;
  content: string;
  language: string;
}

export interface SandboxInfo {
  machine_id: string;
  host: string | null;
  preview_url: string | null;
  state: string;
  error?: string | null;
}

export interface SandboxProvisionRequest {
  env?: Record<string, string>;
}

export interface CodeError {
  file: string;
  line: number;
  col: number;
  severity: 'error' | 'warning' | 'info';
  code?: string;
  message: string;
  error_type?: 'compile' | 'runtime' | 'info';
  stack?: string;
  timestamp?: string;
}

export interface SecurityFinding {
  file: string;
  line: number;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  rule: string;
  message: string;
  snippet?: string;
}

export interface SecurityScanResult {
  findings: SecurityFinding[];
  total: number;
  scanned_at: string;
  file_count: number;
}

export interface CodeErrorsResult {
  errors: CodeError[];
  total: number;
  counts?: {
    error: number;
    warning: number;
    info: number;
  };
  sources?: {
    ast: number;
    static: number;
    build: number;
    console: number;
  };
}

export interface CodeRepairResult {
  status: 'fixed' | 'skipped' | 'no_files' | 'unavailable' | 'error';
  source?: 'rule-based' | 'llm' | 'rule+llm';
  message?: string;
  files?: Array<{ file_path: string; content: string }>;
  count?: number;
}

export interface ConsoleErrorsResult {
  errors: CodeError[];
  total: number;
}

export interface BuildRepairResult {
  ok: boolean;
  repaired: boolean;
  message: string;
  repairs?: Array<{
    file: string;
    status: 'repaired' | 'skipped' | 'failed';
    reason?: string;
    original_size?: number;
    repaired_size?: number;
  }>;
  error_count_before?: number;
  error_count_after?: number;
  elapsed_ms?: number;
}

export interface SandboxBuildStatus {
  status: 'unknown' | 'npm_ok' | 'npm_failed' | 'running' | 'vite_error' | 'crashed';
  error: string | null;
  errors?: Array<{
    file: string;
    line: number;
    col: number;
    code: string;
    message: string;
  }>;
  updated_at?: string;
}

export interface BuildContextDebugResponse {
  project: {
    id: string;
    name?: string;
    status?: string;
    description?: string;
  };
  orchestrator: {
    module: string;
    is_fallback: boolean;
    phases: string[];
  };
  capabilities: {
    database: boolean;
    authentication: boolean;
    ai_integration: boolean;
  };
  context_presence: {
    idea_card: boolean;
    executive: boolean;
    planning: boolean;
    design: boolean;
    workspace: boolean;
  };
  context_counts: {
    executive_agents: number;
    prd_sections: number;
    stack_decisions: number;
    design_tokens: number;
    workspace_files: number;
  };
  samples: {
    prd_headings: string[];
    stack_layers: string[];
    design_tokens: Array<{ label?: string; color?: string }>;
    workspace_files: string[];
  };
  workspace_core_files: {
    required: string[];
    present: string[];
    missing: string[];
    llm_generated: boolean;
    user_edited: boolean;
  };
  build_job: {
    id: string | null;
    type: string | null;
    status: string | null;
    result?: unknown;
  };
  prompt: {
    length: number;
    preview: string;
  };
}

export interface DeploymentsResponse {
  summary: {
    uptime: string;
    uptime_delta: string;
    regions: string;
    regions_detail: string;
    total_releases: number;
    rollbacks: number;
  };
  rows: Array<{
    id: string;
    version: string;
    date: string;
    status: 'success' | 'failure';
    env: string;
    url: string;
  }>;
}

export interface LearningResponse {
  panels: Array<{
    title: string;
    icon: string;
    body: string;
    mono_lines?: [string, string][] | null;
    action_label?: string | null;
  }>;
}

export interface AgentFamily {
  id: string;
  title: string;
  description: string;
  agents: string[];
}

export interface AgentRegistry {
  families: AgentFamily[];
  trust_message: string;
}

export interface OrchestrationStep {
  id: string;
  label: string;
  detail: string;
  status: 'complete' | 'active' | 'pending';
}

export interface OrchestrationPipeline {
  steps: OrchestrationStep[];
  active_index: number;
}

export interface ProjectPipeline {
  steps: OrchestrationStep[];
  active_index: number;
  project_status: string;
}

export interface CapabilitySelection {
  database: boolean;
  authentication: boolean;
  ai_integration: boolean;
  ai_provider: string;  // 'openai' | 'anthropic' | 'google' | 'none'
  storage: boolean;
  payments: boolean;
}

export interface ProcessLogLine {
  ts: string;
  level: string;
  source: string;
  message: string;
}

export interface TelemetryPack {
  gauges: Array<{ name: string; value: string; trend: string; percent: number }>;
  series: { labels: string[]; request_rate: number[]; error_rate: number[] };
}

export interface VaultSummary {
  rows: Array<{
    project_id: string;
    project_name: string;
    active_secrets: number;
    last_audit: string;
  }>;
  policy_note: string;
}

export interface WorkspaceSettings {
  workspace_name: string;
  subdomain: string;
}

export type LLMProvider = 'openai' | 'anthropic' | 'google' | 'cohere' | 'mistral';
export type LLMRole = 'orchestrator' | 'code' | 'design' | 'planning' | 'sandbox' | 'review' | 'ideation';

export interface LLMRoleOverride {
  provider: LLMProvider;
  model: string;
}

export interface LLMSettings {
  default_provider: LLMProvider;
  default_model: string;
  use_default_for_all: boolean;
  role_overrides: Partial<Record<LLMRole, LLMRoleOverride>>;
}

export interface LLMSettingsPatch {
  default_provider?: LLMProvider;
  default_model?: string;
  use_default_for_all?: boolean;
  role_overrides?: Partial<Record<LLMRole, LLMRoleOverride>>;
}

export interface LLMCatalogue {
  providers: LLMProvider[];
  roles: LLMRole[];
  models: Record<LLMProvider, string[]>;
}

export interface ProviderKeyStatus {
  provider: LLMProvider;
  configured: boolean;
  masked_value: string | null;
}

export interface LLMProviderKeysResponse {
  keys: ProviderKeyStatus[];
}

export interface ProviderModelsResponse {
  provider: LLMProvider;
  models: string[];
  source: 'live' | 'static';
}

export interface DailyIdeaCard {
  id: string;
  title: string;
  summary: string;
  urgency: string;
  tags: string[];
  // Rich market/financial fields
  target_customer: string;
  pain_point: string;
  differentiation: string;
  market_opportunity: string;
  financial_upside: string;
  monthly_revenue_low: string;
  monthly_revenue_high: string;
  annual_revenue_low: string;
  annual_revenue_high: string;
  presentation_asset_url: string;
  is_saved: boolean;
  is_reserved: boolean;
}

export interface SavedIdeaItem {
  id: string;
  title: string;
  summary: string;
  saved_at: string;
  expires_note: string;
  saved_expires_at: string;
  uniqueness_degraded: boolean;
  status: string;
}

export interface EditorChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  routing_hint?: string | null;
}

export interface PatchPipeline {
  stages: Array<{ id: string; label: string; status: string; detail: string }>;
  protected_zones_note: string;
}

// —— Vault CRUD ——

export interface VaultSecretUpsert {
  provider: string;
  model: string;
  value: string;
  label?: string | null;
}

export interface VaultSecretResponse {
  key: string;
  provider: string;
  model: string;
  status: string;
  updated_at: string;
  masked_value: string;
}

export interface VaultSecretsListResponse {
  items: VaultSecretResponse[];
  policy_note: string;
}

// —— AST Patch Apply ——

export interface PatchApplyRequest {
  file_path: string;
  patch_description: string;
  confirmed: boolean;
  expected_hash?: string | null;
}

export interface PatchApplyResponse {
  success: boolean;
  message: string;
  applied_file: string;
  lock_held_ms: number;
  protected_zone_blocked: boolean;
  dry_run: boolean;
  file_hash?: string | null;
  original_content?: string | null;
  new_content?: string | null;
  import_warnings?: string[] | null;
}

// —— Orchestration Trigger ——

export interface OrchestrateTriggerRequest {
  message: string;
  starting_step?: string | null;
}

export interface OrchestrateTriggerResponse {
  event_sent: boolean;
  pipeline_run_id: string;
  active_step: string;
  message: string;
}

// —— Team Members ——

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: 'Owner' | 'Admin' | 'Developer' | 'Viewer';
  status: 'Active' | 'Invited';
  joined: string;
}

// —— Action responses ——

export interface ProjectActionResponse {
  ok: boolean;
  message: string;
}

export interface TriggerDeployResponse {
  ok: boolean;
  message: string;
  deployment_id: string;
}

export interface AlignmentSessionResponse {
  ok: boolean;
  message: string;
}

// —— Phase 1: Idea flow ——

export interface PromptEnhanceRequest {
  prompt: string;
}

export interface PromptEnhanceResponse {
  original: string;
  enhanced: string;
}

export interface ProjectPromptContext {
  project_name: string;
  original_prompt: string;
  enhanced_prompt: string;
  idea_title: string;
  idea_summary: string;
  target_customer: string;
  pain_point: string;
  differentiation: string;
}

export interface ModeClassifierContext {
  project_name: string;
  product_mode: string;
  description: string;
  capabilities: Record<string, unknown>;
  idea_tags: string[];
  enhanced_prompt: string;
}

export interface PromptSubmitRequest {
  prompt: string;
  mode: 'as_is' | 'enhance_first';
  project_id?: string | null;
  workspace_id?: string | null;
}

export interface PromptSubmitResponse {
  project_id: string;
  job_id: string;
  next_stage: string;
  message: string;
}

export interface IdeaActionRequest {
  action: 'accept' | 'reject' | 'save';
  title?: string;
  capabilities?: CapabilitySelection;
}

export interface IdeaActionResponse {
  result: string;
  project_id?: string | null;
  next_stage?: string | null;
  message: string;
}

export interface QuestionnaireResponse {
  questionnaire_run_id: string;
  questions: Array<{ id: number; question: string; placeholder: string }>;
}

export interface QuestionnaireSubmitResponse {
  job_id: string;
  batch_id: string;
  next_stage: string;
}

export interface IdeaBatchItem {
  id: string;
  rank: number;
  title: string;
  summary: string;
  target_customer: string;
  pain_point: string;
  differentiation: string;
  monetization_model: string;
  execution_difficulty: string;
  sector: string;
  revenue: string;
  confidence: number;
  market_opportunity: string;
  financial_upside: string;
  monthly_revenue_low: string;
  monthly_revenue_high: string;
  annual_revenue_low: string;
  annual_revenue_high: string;
  presentation_asset_url: string;
}

export interface IdeaBatchResponse {
  batch_id: string;
  ideas: IdeaBatchItem[];
}

export interface WorkspaceSavedIdeaItem {
  id: string;
  title: string;
  summary: string;
  saved_at: string;
  saved_expires_at: string;
  expires_note: string;
  uniqueness_degraded: boolean;
  status: string;
}

export interface WorkspaceSavedIdeasResponse {
  items: WorkspaceSavedIdeaItem[];
}

export interface StartSavedIdeaResponse {
  project_id: string;
  job_id: string;
  warning?: string | null;
}

// —— Phase 2: Job tracking ——

export type JobStatus = 'queued' | 'running' | 'paused' | 'waiting_input' | 'retrying' | 'completed' | 'failed' | 'cancelled';

export interface JobDetail {
  id: string;
  project_id: string;
  type: string;
  status: JobStatus;
  started_at?: string | null;
  completed_at?: string | null;
  result?: Record<string, unknown> | null;
}

// —— Phase 3: Build ——

export interface BuildTriggerResponse {
  ok: boolean;
  job_id: string;
  message: string;
}

export type BuildStage =
  | 'idle'
  | 'queued'
  | 'planning'
  | 'generating_code'
  | 'building'
  | 'repairing'
  | 'ready_for_preview'
  | 'failed';

// —— Phase 4: PRD + Architecture ——

export interface PRDDocResponse {
  version_label: string;
  prd_sections: Array<{
    heading: string;
    body?: string | null;
    checklist?: [string, boolean][] | null;
  }>;
}

export interface ArchitectureResponse {
  version_label: string;
  phases: [string, string, string][]; // [label, status: 'complete'|'active'|'pending', route]
  stack_decisions: [string, string][];
  summary: string;
}

// —— Phase 5: Deployment git/vercel ——

export interface GitConnectRequest {
  repo_url?: string | null;
  create_new?: boolean;
}

export interface GitConnectResponse {
  ok: boolean;
  repo_url: string;
  message: string;
}

export interface GitCommitRequest {
  message?: string;
}

export interface GitCommitResponse {
  ok: boolean;
  commit_hash: string;
  job_id: string;
  message: string;
}

export interface VercelDeployRequest {
  project_name?: string | null;
}

export interface VercelDeployResponse {
  ok: boolean;
  deployment_url: string;
  job_id: string;
  message: string;
}

export type DeployStage = 'idle' | 'connecting_git' | 'committing' | 'deploying' | 'deployed' | 'failed';

// —— Phase 6: Secrets intake ——

export interface SecretIntakeSessionResponse {
  session_id: string;
  required_secrets: string[];
  expires_at?: string | null;
  message: string;
}

export interface SecretCreateRequest {
  session_id?: string | null;
  provider: string;
  secret_name: string;
  value: string;
  scope?: 'generated_app' | 'cloud_integration' | 'provider_api_key';
}

export interface SecretCreateResponse {
  id: string;
  provider: string;
  secret_name: string;
  status: string;
  message: string;
}

