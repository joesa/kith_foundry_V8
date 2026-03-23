import type { FastifyInstance } from "fastify"
import { classifyDesignMode } from "../ai/classify-design-mode"
import { DesignModeService } from "../services/design-mode-service"
import { lockProjectDesignMode, unlockProjectDesignMode, updateProjectDesignMode } from "../services/project-brain-service"
import type { ClassifyDesignModeRequest } from "../types/design-mode"

declare module "fastify" {
  interface FastifyInstance {
    llmCall: (messages: Array<{ role: string; content: string }>) => Promise<string>
    db: { query: (sql: string, params?: unknown[]) => Promise<unknown> }
  }
}

export async function designRoutes(app: FastifyInstance) {
  const designModeService = new DesignModeService()

  app.get("/api/design/mode-options", async (_request, reply) => {
    const [productModes, styleModes] = await Promise.all([
      designModeService.getAllProductModes(),
      designModeService.getAllStyleModes()
    ])

    return reply.send({ productModes, styleModes })
  })

  app.post("/api/design/classify-mode", async (request, reply) => {
    const body = request.body as ClassifyDesignModeRequest

    const [productModes, styleModes] = await Promise.all([
      designModeService.getAllProductModes(),
      designModeService.getAllStyleModes()
    ])

    const classification = await classifyDesignMode(app.llmCall, {
      ...body,
      productModes,
      styleModes
    })

    await updateProjectDesignMode(app.db, {
      projectId: body.projectId,
      productMode: classification.productMode,
      styleMode: classification.styleMode,
      confidence: classification.confidence,
      source: "auto"
    })

    const [blueprint, profile] = await Promise.all([
      designModeService.getBlueprint(classification.productMode),
      designModeService.getDesignProfile(classification.productMode)
    ])

    return reply.send({
      classification,
      blueprint,
      recommendedPatterns: profile?.recommended_patterns ?? []
    })
  })

  app.post("/api/design/lock-mode", async (request, reply) => {
    const body = request.body as {
      projectId: string
      productMode: string
      styleMode: string
    }

    await lockProjectDesignMode(app.db, body)
    return reply.send({ ok: true })
  })

  app.post("/api/design/unlock-mode", async (request, reply) => {
    const body = request.body as { projectId: string }
    await unlockProjectDesignMode(app.db, body.projectId)
    return reply.send({ ok: true })
  })
}
