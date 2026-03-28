# 04_DATABASE_SCHEMA_SQL.md

```sql
create table workspaces (
  id uuid primary key,
  owner_user_id uuid not null,
  name text not null,
  slug text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table workspace_members (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  user_id uuid not null,
  role text not null check (role in ('owner','admin','member','viewer')),
  created_at timestamptz not null default now(),
  unique (workspace_id, user_id)
);

create table projects (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  owner_user_id uuid not null,
  source_idea_id uuid null,
  name text not null,
  description text null,
  status text not null check (status in ('draft','executive_review','planning','designing','capability_gate','waiting_for_secrets','generating_code','building','repairing','ready_for_preview','deploy_ready','deployed','failed')),
  current_branch text null,
  product_mode text null,
  style_mode text null,
  mode_confidence numeric(5,4) null,
  design_mode_locked boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table generated_ideas (
  id uuid primary key,
  workspace_id uuid not null references workspaces(id) on delete cascade,
  created_by_user_id uuid null,
  idea_title text not null,
  idea_summary text not null,
  target_customer text null,
  pain_point text null,
  differentiation text null,
  monetization_model text null,
  execution_difficulty text null,
  generated_from text not null check (generated_from in ('daily_curated','single_shot','guided_ideation')),
  status text not null check (status in ('saved_only','in_csuite','planned','designing','building','active_project','archived','resurfaced')),
  exclusivity_locked boolean not null default false,
  warning_shown boolean not null default false,
  saved_expires_at timestamptz null,
  uniqueness_degraded boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table project_capability_choices (
  id uuid primary key,
  project_id uuid not null unique references projects(id) on delete cascade,
  wants_database boolean not null default false,
  wants_auth boolean not null default false,
  wants_ai boolean not null default false,
  selected_generated_backend_provider text not null default 'none' check (selected_generated_backend_provider in ('supabase','external_cloud','none')),
  selected_generated_auth_provider text not null default 'none' check (selected_generated_auth_provider in ('supabase','external_cloud','none')),
  selected_generated_storage_provider text not null default 'none' check (selected_generated_storage_provider in ('supabase','external_cloud','none')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table encrypted_user_secrets (
  id uuid primary key,
  user_id uuid not null,
  workspace_id uuid null references workspaces(id) on delete cascade,
  project_id uuid null references projects(id) on delete cascade,
  secret_scope text not null check (secret_scope in ('generated_app','cloud_integration','provider_api_key')),
  provider_name text not null,
  secret_name text not null,
  ciphertext text not null,
  iv text not null,
  auth_tag text not null,
  aad_json jsonb null,
  kms_key_ref text null,
  status text not null check (status in ('active','revoked','rotated')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table secret_access_audit (
  id uuid primary key,
  secret_id uuid not null references encrypted_user_secrets(id) on delete cascade,
  actor_type text not null,
  actor_ref text not null,
  action text not null check (action in ('create','read_for_runtime','rotate','revoke')),
  created_at timestamptz not null default now()
);

create table sandboxes (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  fly_app_name text null,
  region text null,
  status text not null check (status in ('provisioning','syncing','installing','building','running','stopped','failed')),
  preview_url text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table sandbox_builds (
  id uuid primary key,
  sandbox_id uuid not null references sandboxes(id) on delete cascade,
  build_status text not null check (build_status in ('queued','running','success','failed')),
  install_command text null,
  build_command text null,
  start_command text null,
  log_url text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table code_patches (
  id uuid primary key,
  project_id uuid not null references projects(id) on delete cascade,
  target_path text not null,
  diff_text text not null,
  status text not null check (status in ('generated','validated','applied','rejected')),
  source_agent text not null,
  created_at timestamptz not null default now()
);

create table patch_validations (
  id uuid primary key,
  code_patch_id uuid not null references code_patches(id) on delete cascade,
  syntax_ok boolean not null,
  dependency_ok boolean not null,
  runtime_ok boolean not null,
  policy_ok boolean not null default true,
  score numeric(5,2) null,
  notes text null,
  created_at timestamptz not null default now()
);
```
