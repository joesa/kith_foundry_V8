import { apiGet, apiPatch, apiPost, apiDelete, apiPut } from './http';
import type {
  AgentRegistry,
  AlignmentSessionResponse,
  ArchitectureResponse,
  BuildContextDebugResponse,
  BuildTriggerResponse,
  CapabilitiesResponse,
  CapabilitySelection,
  CodeFileResponse,
  CodeTreeResponse,
  CuratedIdea,
  DailyIdeaCard,
  DeploymentsResponse,
  DesignStudio,
  EditorChatMessage,
  ExecutiveReport,
  FileTreeNode,
  GitCommitRequest,
  GitCommitResponse,
  GitConnectRequest,
  GitConnectResponse,
  IdeaActionRequest,
  IdeaActionResponse,
  IdeaBatchResponse,
  IdeationStep,
  JobDetail,
  LearningResponse,
  OrchestrateTriggerRequest,
  OrchestrateTriggerResponse,
  OrchestrationPipeline,
  PatchApplyRequest,
  PatchApplyResponse,
  PatchPipeline,
  PlanningDoc,
  PlatformHome,
  PRDDocResponse,
  ProcessLogLine,
  ProjectActionResponse,
  ProjectOverview,
  ProjectPipeline,
  ProjectSummary,
  PromptEnhanceRequest,
  PromptEnhanceResponse,
  PromptSubmitRequest,
  PromptSubmitResponse,
  QuestionnaireResponse,
  QuestionnaireSubmitResponse,
  SandboxInfo,
  SandboxProvisionRequest,
  SavedIdeaItem,
  SecretCreateRequest,
  SecretCreateResponse,
  SecretEntry,
  SecretIntakeSessionResponse,
  StartSavedIdeaResponse,
  TeamMember,
  TelemetryPack,
  TriggerDeployResponse,
  VaultSummary,
  VaultSecretUpsert,
  VaultSecretResponse,
  VaultSecretsListResponse,
  VercelDeployRequest,
  VercelDeployResponse,
  WorkspaceSettings,
  WorkspaceSavedIdeaItem,
  LLMSettings,
  LLMSettingsPatch,
  LLMCatalogue,
  ProviderKeyStatus,
  LLMProviderKeysResponse,
  ProviderModelsResponse,
  CodeErrorsResult,
  SecurityScanResult,
  ConsoleErrorsResult,
  BuildRepairResult,
  CodeRepairResult,
  SandboxBuildStatus,
  ProjectPromptContext,
  ModeClassifierContext,
} from './types';

export async function fetchProjects(): Promise<ProjectSummary[]> {
  return apiGet<ProjectSummary[]>('/api/projects');
}

export async function fetchProject(projectId: string): Promise<ProjectSummary> {
  return apiGet<ProjectSummary>(`/api/projects/${projectId}`);
}

export async function deleteProject(projectId: string): Promise<void> {
  await apiDelete(`/api/projects/${projectId}`);
}

export async function renameProject(projectId: string, name: string): Promise<ProjectSummary> {
  return apiPatch<ProjectSummary>(`/api/projects/${projectId}/name`, { name });
}

export async function fetchPlatformHome(): Promise<PlatformHome> {
  return apiGet<PlatformHome>('/api/platform/home');
}

export async function fetchProjectOverview(projectId: string): Promise<ProjectOverview> {
  return apiGet<ProjectOverview>(`/api/projects/${projectId}/overview`);
}

export async function fetchProjectPromptContext(projectId: string): Promise<ProjectPromptContext> {
  return apiGet<ProjectPromptContext>(`/api/projects/${projectId}/prompt-context`);
}

export async function fetchModeClassifierContext(projectId: string): Promise<ModeClassifierContext> {
  return apiGet<ModeClassifierContext>(`/api/projects/${projectId}/mode-context`);
}

export async function fetchIdeationSteps(projectId: string): Promise<IdeationStep[]> {
  const r = await apiGet<{ steps: IdeationStep[] }>(
    `/api/projects/${projectId}/ideation/steps`
  );
  return r.steps;
}

export async function curateIdeas(
  projectId: string,
  answers: Record<string, string>
): Promise<CuratedIdea[]> {
  const r = await apiPost<{ ideas: CuratedIdea[] }, { answers: Record<string, string> }>(
    `/api/projects/${projectId}/ideation/curate`,
    { answers }
  );
  return r.ideas;
}

export async function fetchExecutiveReport(projectId: string): Promise<ExecutiveReport> {
  return apiGet<ExecutiveReport>(`/api/projects/${projectId}/executive`);
}

export async function fetchPlanning(projectId: string): Promise<PlanningDoc> {
  return apiGet<PlanningDoc>(`/api/projects/${projectId}/planning`);
}

export async function fetchDesignStudio(projectId: string): Promise<DesignStudio> {
  return apiGet<DesignStudio>(`/api/projects/${projectId}/design`);
}

export async function fetchCapabilities(projectId: string): Promise<CapabilitiesResponse> {
  return apiGet<CapabilitiesResponse>(`/api/projects/${projectId}/capabilities`);
}

export async function patchCapabilities(
  projectId: string,
  patch: Partial<{ database: boolean; authentication: boolean; ai_integration: boolean }>
): Promise<CapabilitiesResponse> {
  return apiPatch<CapabilitiesResponse>(`/api/projects/${projectId}/capabilities`, patch);
}

export async function fetchSecrets(projectId: string): Promise<SecretEntry[]> {
  const r = await apiGet<{ items: SecretEntry[] }>(`/api/projects/${projectId}/secrets`);
  return r.items;
}

export async function fetchCodeTree(projectId: string): Promise<CodeTreeResponse> {
  return apiGet<CodeTreeResponse>(`/api/projects/${projectId}/code/tree`);
}

export async function fetchCodeFile(projectId: string, path: string): Promise<CodeFileResponse> {
  const q = new URLSearchParams({ path });
  return apiGet<CodeFileResponse>(`/api/projects/${projectId}/code/file?${q}`);
}

export async function fetchSandboxInfo(projectId: string): Promise<SandboxInfo> {
  return apiGet<SandboxInfo>(`/api/projects/${projectId}/sandbox`);
}

export async function provisionSandbox(
  projectId: string,
  req?: SandboxProvisionRequest
): Promise<SandboxInfo> {
  return apiPost<SandboxInfo, SandboxProvisionRequest>(
    `/api/projects/${projectId}/sandbox`,
    req ?? {}
  );
}

export async function teardownSandbox(projectId: string): Promise<void> {
  await apiDelete(`/api/projects/${projectId}/sandbox`);
}

export async function fetchSandboxLogs(projectId: string): Promise<string[]> {
  const r = await apiGet<{ lines: string[] }>(`/api/projects/${projectId}/sandbox/logs`);
  return r.lines;
}

export async function fetchCodeErrors(projectId: string): Promise<CodeErrorsResult> {
  return apiGet<CodeErrorsResult>(`/api/projects/${projectId}/code/errors`);
}

export async function fetchSecurityScan(projectId: string): Promise<SecurityScanResult> {
  return apiGet<SecurityScanResult>(`/api/projects/${projectId}/code/security-scan`);
}

export async function fetchConsoleErrors(projectId: string): Promise<ConsoleErrorsResult> {
  return apiGet<ConsoleErrorsResult>(`/api/projects/${projectId}/sandbox/console-errors`);
}

export async function clearConsoleErrors(projectId: string): Promise<void> {
  await apiDelete(`/api/projects/${projectId}/sandbox/console-errors`);
}

export async function fetchSandboxBuildStatus(projectId: string): Promise<SandboxBuildStatus> {
  return apiGet<SandboxBuildStatus>(`/api/projects/${projectId}/sandbox/build-status`);
}

export async function fetchBuildContextDebug(projectId: string): Promise<BuildContextDebugResponse> {
  return apiGet<BuildContextDebugResponse>(`/api/projects/${projectId}/build/context-debug`);
}

export async function triggerBuildRepair(projectId: string): Promise<BuildRepairResult> {
  return apiPost<BuildRepairResult, Record<string, never>>(`/api/projects/${projectId}/build/repair`, {});
}

export async function repairCodeErrors(projectId: string): Promise<CodeRepairResult> {
  return apiPost<CodeRepairResult, Record<string, never>>(`/api/projects/${projectId}/code/repair`, {});
}


export async function fetchDeployments(projectId: string): Promise<DeploymentsResponse> {
  return apiGet<DeploymentsResponse>(`/api/projects/${projectId}/deployments`);
}

export async function fetchLearning(projectId: string): Promise<LearningResponse> {
  return apiGet<LearningResponse>(`/api/projects/${projectId}/learning`);
}

export async function fetchAgentRegistry(): Promise<AgentRegistry> {
  return apiGet<AgentRegistry>('/api/platform/agents');
}

export async function fetchOrchestrationPipeline(): Promise<OrchestrationPipeline> {
  return apiGet<OrchestrationPipeline>('/api/platform/orchestration');
}

export async function fetchProjectPipeline(projectId: string): Promise<ProjectPipeline> {
  return apiGet<ProjectPipeline>(`/api/projects/${projectId}/pipeline`);
}

export async function fetchProcessLogs(): Promise<ProcessLogLine[]> {
  const r = await apiGet<{ lines: ProcessLogLine[] }>('/api/platform/process-logs');
  return r.lines;
}

export async function fetchPlatformTelemetry(): Promise<TelemetryPack> {
  return apiGet<TelemetryPack>('/api/platform/telemetry');
}

export async function fetchVaultSummary(): Promise<VaultSummary> {
  return apiGet<VaultSummary>('/api/platform/vault-summary');
}

export async function fetchWorkspaceSettings(): Promise<WorkspaceSettings> {
  return apiGet<WorkspaceSettings>('/api/platform/settings');
}

export async function patchWorkspaceSettings(
  patch: Partial<Pick<WorkspaceSettings, 'workspace_name' | 'subdomain'>>
): Promise<WorkspaceSettings> {
  return apiPatch<WorkspaceSettings>('/api/platform/settings', patch);
}

export async function fetchLLMSettings(): Promise<LLMSettings> {
  return apiGet<LLMSettings>('/api/platform/llm-settings');
}

export async function patchLLMSettings(patch: LLMSettingsPatch): Promise<LLMSettings> {
  return apiPatch<LLMSettings>('/api/platform/llm-settings', patch);
}

export async function fetchLLMCatalogue(): Promise<LLMCatalogue> {
  return apiGet<LLMCatalogue>('/api/platform/llm-catalogue');
}

export async function fetchProviderKeys(): Promise<ProviderKeyStatus[]> {
  const r = await apiGet<LLMProviderKeysResponse>('/api/platform/llm-keys');
  return r.keys;
}

export async function setProviderKey(provider: string, apiKey: string): Promise<ProviderKeyStatus> {
  return apiPut<ProviderKeyStatus, { api_key: string }>(`/api/platform/llm-keys/${provider}`, { api_key: apiKey });
}

export async function deleteProviderKey(provider: string): Promise<void> {
  await apiDelete(`/api/platform/llm-keys/${provider}`);
}

export async function fetchProviderModels(provider: string): Promise<ProviderModelsResponse> {
  return apiGet<ProviderModelsResponse>(`/api/platform/llm-keys/${provider}/models`);
}

export async function fetchDailyTopIdea(projectId: string): Promise<DailyIdeaCard> {
  const r = await apiGet<{ idea: DailyIdeaCard }>(`/api/projects/${projectId}/ideas/daily-top`);
  return r.idea;
}

export async function fetchSavedIdeas(projectId: string): Promise<SavedIdeaItem[]> {
  const r = await apiGet<{ items: SavedIdeaItem[] }>(`/api/projects/${projectId}/ideas/saved`);
  return r.items;
}

export async function fetchEditorThread(projectId: string): Promise<EditorChatMessage[]> {
  const r = await apiGet<{ messages: EditorChatMessage[] }>(`/api/projects/${projectId}/editor/thread`);
  return r.messages;
}

export async function postEditorMessage(
  projectId: string,
  message: string,
  filePath?: string | null,
  fileContent?: string | null
): Promise<EditorChatMessage[]> {
  const r = await apiPost<
    { messages: EditorChatMessage[] },
    { message: string; file_path?: string; file_content?: string }
  >(
    `/api/projects/${projectId}/editor/message`,
    {
      message,
      ...(filePath ? { file_path: filePath } : {}),
      ...(fileContent != null ? { file_content: fileContent } : {}),
    }
  );
  return r.messages;
}

/** Phase event emitted by the multi-agent orchestrator. */
export interface AgentPhaseEvent {
  phase: string;
  label: string;
  status: 'running' | 'done';
  result_summary?: string;
}

/**
 * Stream an editor assistant message via SSE.
 * Calls onToken for each text chunk and onDone with the final thread when complete.
 * Calls onPhase (if provided) when the multi-agent orchestrator emits phase progress.
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function streamEditorMessage(
  projectId: string,
  message: string,
  filePath: string | null,
  fileContent: string | null,
  onToken: (token: string) => void,
  onDone: (thread: EditorChatMessage[]) => void,
  onError: (err: string) => void,
  onPhase?: (phase: AgentPhaseEvent) => void,
): AbortController {
  const controller = new AbortController();
  const { signal } = controller;

  (async () => {
    try {
      const { apiPath } = await import('./config');
      const res = await fetch(apiPath(`/api/projects/${projectId}/editor/stream`), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        body: JSON.stringify({
          message,
          ...(filePath ? { file_path: filePath } : {}),
          ...(fileContent != null ? { file_content: fileContent } : {}),
        }),
        signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => `HTTP ${res.status}`);
        onError(text || `Server error ${res.status}`);
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        const parts = buf.split('\n\n');
        buf = parts.pop() ?? '';

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (!raw || raw === '[DONE]') continue;
            try {
              const data = JSON.parse(raw);
              if (typeof data.phase === 'string' && onPhase) {
                onPhase(data as AgentPhaseEvent);
              } else if (typeof data.token === 'string') {
                onToken(data.token);
              }
              if (data.done === true) onDone((data.thread ?? []) as EditorChatMessage[]);
            } catch { /* malformed frame — skip */ }
          }
        }
      }
    } catch (e: unknown) {
      if ((e as {name?: string}).name === 'AbortError') return; // user cancelled
      onError(e instanceof Error ? e.message : String(e));
    }
  })();

  return controller;
}

/**
 * Write (create or overwrite) a file inside the project code workspace.
 * Called whenever a streamed code block completes.
 */
export async function writeCodeFile(
  projectId: string,
  path: string,
  content: string,
): Promise<void> {
  await apiPatch<unknown>(`/api/projects/${projectId}/code/file`, { path, content });
}

/** Delete the cached code workspace so it regenerates fresh on next load. */
export async function resetCodeWorkspace(projectId: string): Promise<void> {
  await apiDelete(`/api/projects/${projectId}/code/workspace`);
}

export async function getPatchPipeline(projectId: string): Promise<PatchPipeline> {
  return apiGet<PatchPipeline>(`/api/projects/${projectId}/patch-pipeline`);
}

// —— Vault CRUD ——

export async function listVaultSecrets(projectId: string): Promise<VaultSecretsListResponse> {
  return apiGet<VaultSecretsListResponse>(`/api/projects/${projectId}/vault`);
}

export async function upsertVaultSecret(
  projectId: string,
  key: string,
  body: VaultSecretUpsert
): Promise<VaultSecretResponse> {
  return apiPost<VaultSecretResponse, VaultSecretUpsert>(
    `/api/projects/${projectId}/vault/${encodeURIComponent(key)}`,
    body
  );
}

export async function deleteVaultSecret(projectId: string, key: string): Promise<void> {
  await apiDelete(`/api/projects/${projectId}/vault/${encodeURIComponent(key)}`);
}

// —— AST Patch Apply ——

export async function applyPatch(
  projectId: string,
  req: PatchApplyRequest
): Promise<PatchApplyResponse> {
  return apiPost<PatchApplyResponse, PatchApplyRequest>(
    `/api/projects/${projectId}/patch/apply`,
    req
  );
}

export async function fetchPatchHistory(
  projectId: string,
  limit = 20
): Promise<{ patches: Array<{ file: string; description: string; status: string; timestamp: string }>; total: number }> {
  return apiGet(`/api/projects/${projectId}/patches?limit=${limit}`);
}

// —— Orchestration Trigger ——

export async function triggerOrchestration(
  projectId: string,
  req: OrchestrateTriggerRequest
): Promise<OrchestrateTriggerResponse> {
  return apiPost<OrchestrateTriggerResponse, OrchestrateTriggerRequest>(
    `/api/projects/${projectId}/orchestrate`,
    req
  );
}

// —— Project creation ——

export async function createProject(
  name: string,
  description: string,
  stage: string = 'ideation'
): Promise<ProjectSummary> {
  return apiPost<ProjectSummary, { name: string; description: string; stage: string }>(
    '/api/projects',
    { name, description, stage }
  );
}

// —— Team members ——

export async function fetchTeamMembers(): Promise<TeamMember[]> {
  const r = await apiGet<{ members: TeamMember[] }>('/api/platform/team');
  return r.members;
}

export async function inviteTeamMember(email: string, role: string): Promise<TeamMember> {
  return apiPost<TeamMember, { email: string; role: string }>('/api/platform/team', { email, role });
}

export async function removeTeamMember(memberId: string): Promise<void> {
  await apiDelete(`/api/platform/team/${memberId}`);
}

// —— Ideas ——

export async function saveIdea(
  projectId: string,
  title: string,
  summary: string
): Promise<SavedIdeaItem> {
  return apiPost<SavedIdeaItem, { title: string; summary: string }>(
    `/api/projects/${projectId}/ideas/save`,
    { title, summary }
  );
}

export async function deleteSavedIdea(projectId: string, ideaId: string): Promise<void> {
  await apiDelete(`/api/projects/${projectId}/ideas/saved/${ideaId}`);
}

// —— Deployment trigger ——

export async function triggerDeploy(projectId: string): Promise<TriggerDeployResponse> {
  return apiPost<TriggerDeployResponse, Record<string, never>>(
    `/api/projects/${projectId}/deployments/trigger`,
    {}
  );
}

// —— Executive actions ——

export async function approveStrategy(projectId: string): Promise<ProjectActionResponse> {
  return apiPost<ProjectActionResponse, Record<string, never>>(
    `/api/projects/${projectId}/executive/approve`,
    {}
  );
}

export async function requestPivot(projectId: string, direction: string = ''): Promise<ProjectActionResponse> {
  return apiPost<ProjectActionResponse, { direction: string }>(
    `/api/projects/${projectId}/executive/pivot`,
    { direction }
  );
}

// —— Design regenerate ——

export async function triggerDesignRegenerate(projectId: string): Promise<ProjectActionResponse> {
  return apiPost<ProjectActionResponse, Record<string, never>>(
    `/api/projects/${projectId}/design/regenerate`,
    {}
  );
}

// —— Learning alignment ——

export async function startAlignmentSession(
  projectId: string,
  panelTitle: string = ''
): Promise<AlignmentSessionResponse> {
  return apiPost<AlignmentSessionResponse, { panel_title: string }>(
    `/api/projects/${projectId}/learning/alignment`,
    { panel_title: panelTitle }
  );
}

// ─── Phase 1: New idea flow ───────────────────────────────────────────────

export async function enhancePrompt(prompt: string): Promise<PromptEnhanceResponse> {
  return apiPost<PromptEnhanceResponse, PromptEnhanceRequest>('/api/prompts/enhance', { prompt });
}

export async function submitPrompt(
  prompt: string,
  mode: 'as_is' | 'enhance_first' = 'as_is',
  projectId?: string | null
): Promise<PromptSubmitResponse> {
  return apiPost<PromptSubmitResponse, PromptSubmitRequest>('/api/prompts/submit', {
    prompt,
    mode,
    project_id: projectId ?? null,
  });
}

function getOrCreateIdeaSeed(): string {
  const key = 'forge_idea_seed';
  let seed = localStorage.getItem(key);
  if (!seed) {
    seed = crypto.randomUUID();
    localStorage.setItem(key, seed);
  }
  return seed;
}

export async function fetchDailyTopIdeaWorkspace(): Promise<DailyIdeaCard> {
  const seed = getOrCreateIdeaSeed();
  const r = await apiGet<{ idea: DailyIdeaCard }>(`/api/ideas/daily?seed=${encodeURIComponent(seed)}`);
  return r.idea;
}

export async function actionDailyIdea(
  ideaId: string,
  action: 'accept' | 'reject' | 'save',
  capabilities?: CapabilitySelection | null,
  title?: string | null
): Promise<IdeaActionResponse> {
  return apiPost<IdeaActionResponse, IdeaActionRequest>(`/api/ideas/daily/${ideaId}/action`, {
    action,
    ...(title ? { title } : {}),
    ...(capabilities ? { capabilities } : {}),
  });
}

export async function fetchQuestionnaire(): Promise<QuestionnaireResponse> {
  return apiGet<QuestionnaireResponse>('/api/ideation/questionnaire');
}

export async function submitQuestionnaire(
  runId: string,
  answers: Record<string, string>
): Promise<QuestionnaireSubmitResponse> {
  return apiPost<QuestionnaireSubmitResponse, { answers: Record<string, string> }>(
    `/api/ideation/questionnaire/${runId}/submit`,
    { answers }
  );
}

export async function fetchIdeaBatch(batchId: string): Promise<IdeaBatchResponse> {
  return apiGet<IdeaBatchResponse>(`/api/ideas/batches/${batchId}`);
}

export async function fetchWorkspaceSavedIdeas(): Promise<WorkspaceSavedIdeaItem[]> {
  const r = await apiGet<{ items: WorkspaceSavedIdeaItem[] }>('/api/saved-ideas');
  return r.items;
}

export async function startSavedIdea(
  ideaId: string,
  capabilities?: CapabilitySelection | null
): Promise<StartSavedIdeaResponse> {
  return apiPost<StartSavedIdeaResponse, { capabilities?: CapabilitySelection | null }>(
    `/api/saved-ideas/${ideaId}/start`,
    capabilities ? { capabilities } : {}
  );
}

// ─── Phase 2: Job tracking ───────────────────────────────────────────────

export async function fetchJob(projectId: string, jobId: string): Promise<JobDetail> {
  return apiGet<JobDetail>(`/api/projects/${projectId}/jobs/${jobId}`);
}

// ─── Phase 3: Build ───────────────────────────────────────────────────────

export async function triggerBuild(projectId: string): Promise<BuildTriggerResponse> {
  return apiPost<BuildTriggerResponse, Record<string, never>>(
    `/api/projects/${projectId}/build`,
    {}
  );
}

/**
 * Stream live build tokens from the backend SSE endpoint.
 * Returns an AbortController to cancel the stream.
 */
export function streamBuildTokens(
  projectId: string,
  jobId: string,
  onToken: (token: string) => void,
  onPhase: (phase: AgentPhaseEvent) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const controller = new AbortController();
  const { signal } = controller;

  (async () => {
    try {
      const { apiPath } = await import('./config');
      const res = await fetch(apiPath(`/api/projects/${projectId}/build/${jobId}/stream`), {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'text/event-stream' },
        signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => `HTTP ${res.status}`);
        onError(text || `Stream error ${res.status}`);
        return;
      }

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        const parts = buf.split('\n\n');
        buf = parts.pop() ?? '';

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            const raw = line.slice(6).trim();
            if (!raw || raw === '[DONE]') continue;
            try {
              const data = JSON.parse(raw);
              if (data.done === true) { onDone(); return; }
              if (typeof data.phase === 'string') onPhase(data as AgentPhaseEvent);
              if (typeof data.token === 'string') onToken(data.token);
            } catch { /* malformed frame */ }
          }
        }
      }
      // Stream ended without explicit done — treat as completion
      onDone();
    } catch (e: unknown) {
      if ((e as { name?: string }).name === 'AbortError') return;
      onError(e instanceof Error ? e.message : String(e));
    }
  })();

  return controller;
}

// ─── Phase 4: PRD + Architecture ─────────────────────────────────────────

export async function fetchPRD(projectId: string): Promise<PRDDocResponse> {
  return apiGet<PRDDocResponse>(`/api/projects/${projectId}/prd`);
}

export async function fetchArchitecture(projectId: string): Promise<ArchitectureResponse> {
  return apiGet<ArchitectureResponse>(`/api/projects/${projectId}/architecture`);
}

// ─── Phase 5: Deployment git/vercel ──────────────────────────────────────

export async function gitConnect(
  projectId: string,
  opts: GitConnectRequest = {}
): Promise<GitConnectResponse> {
  return apiPost<GitConnectResponse, GitConnectRequest>(
    `/api/projects/${projectId}/git/connect`,
    opts
  );
}

export async function gitCommit(
  projectId: string,
  message: string = 'feat: update from Forge'
): Promise<GitCommitResponse> {
  return apiPost<GitCommitResponse, GitCommitRequest>(
    `/api/projects/${projectId}/git/commit`,
    { message }
  );
}

export async function deployVercel(
  projectId: string,
  opts: VercelDeployRequest = {}
): Promise<VercelDeployResponse> {
  return apiPost<VercelDeployResponse, VercelDeployRequest>(
    `/api/projects/${projectId}/deploy/vercel`,
    opts
  );
}

// ─── Phase 6: Secrets intake ──────────────────────────────────────────────

export async function startIntakeSession(projectId?: string | null): Promise<SecretIntakeSessionResponse> {
  const qs = projectId ? `?project_id=${projectId}` : '';
  return apiPost<SecretIntakeSessionResponse, Record<string, never>>(
    `/api/secrets/intake-session${qs}`,
    {}
  );
}

export async function createSecret(req: SecretCreateRequest): Promise<SecretCreateResponse> {
  return apiPost<SecretCreateResponse, SecretCreateRequest>('/api/secrets', req);
}

export async function revokeSecret(secretId: string): Promise<void> {
  await apiPost<void, Record<string, never>>(`/api/secrets/${secretId}/revoke`, {});
}


/** Flatten first root folders for file picker convenience */
export function flattenFiles(nodes: FileTreeNode[], prefix = ''): { path: string; name: string }[] {
  const out: { path: string; name: string }[] = [];
  for (const n of nodes) {
    if (n.type === 'file') out.push({ path: n.path, name: prefix + n.name });
    else if (n.children?.length)
      out.push(...flattenFiles(n.children, `${prefix}${n.name}/`));
  }
  return out;
}
