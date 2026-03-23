export async function updateProjectDesignMode(
  db: { query: (sql: string, params?: unknown[]) => Promise<unknown> },
  params: {
    projectId: string
    productMode: string
    styleMode: string
    confidence: number
    source: "auto" | "user"
  }
) {
  await db.query(
    `
    UPDATE projects
    SET product_mode = $2,
        style_mode = $3,
        mode_confidence = $4,
        updated_at = NOW()
    WHERE id = $1
    `,
    [params.projectId, params.productMode, params.styleMode, params.confidence]
  )

  await db.query(
    `
    INSERT INTO project_design_mode_history
      (id, project_id, product_mode, style_mode, confidence, source)
    VALUES
      (gen_random_uuid(), $1, $2, $3, $4, $5)
    `,
    [params.projectId, params.productMode, params.styleMode, params.confidence, params.source]
  )
}

export async function lockProjectDesignMode(
  db: { query: (sql: string, params?: unknown[]) => Promise<unknown> },
  params: {
    projectId: string
    productMode: string
    styleMode: string
  }
) {
  await db.query(
    `
    UPDATE projects
    SET product_mode = $2,
        style_mode = $3,
        design_mode_locked = TRUE,
        updated_at = NOW()
    WHERE id = $1
    `,
    [params.projectId, params.productMode, params.styleMode]
  )
}

export async function unlockProjectDesignMode(
  db: { query: (sql: string, params?: unknown[]) => Promise<unknown> },
  projectId: string
) {
  await db.query(
    `
    UPDATE projects
    SET design_mode_locked = FALSE,
        updated_at = NOW()
    WHERE id = $1
    `,
    [projectId]
  )
}
