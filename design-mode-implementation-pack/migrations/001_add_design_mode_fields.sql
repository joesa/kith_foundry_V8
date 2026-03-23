ALTER TABLE projects
ADD COLUMN product_mode TEXT,
ADD COLUMN style_mode TEXT,
ADD COLUMN mode_confidence NUMERIC(5,4),
ADD COLUMN design_mode_locked BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS project_design_mode_history (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL REFERENCES projects(id),
  product_mode TEXT NOT NULL,
  style_mode TEXT NOT NULL,
  confidence NUMERIC(5,4),
  source TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);
