import { MODE_CLASSIFIER_SYSTEM_PROMPT } from "./prompts/mode-classifier.prompt"
import type { ModeClassificationResult } from "../types/design-mode"

interface ClassifyInput {
  prompt: string
  appName?: string
  appType?: string
  description?: string
  features?: string[]
  targetAudience?: string
  preferredStyle?: string
  productModes: string[]
  styleModes: string[]
}

export async function classifyDesignMode(
  llmCall: (messages: Array<{ role: string; content: string }>) => Promise<string>,
  input: ClassifyInput
): Promise<ModeClassificationResult> {
  const userPrompt = `
Project prompt: ${input.prompt}
App name: ${input.appName ?? ""}
App type: ${input.appType ?? ""}
Description: ${input.description ?? ""}
Features: ${(input.features ?? []).join(", ")}
Target audience: ${input.targetAudience ?? ""}
Preferred style: ${input.preferredStyle ?? ""}

Available product modes:
${input.productModes.join(", ")}

Available style modes:
${input.styleModes.join(", ")}
`

  const raw = await llmCall([
    { role: "system", content: MODE_CLASSIFIER_SYSTEM_PROMPT },
    { role: "user", content: userPrompt }
  ])

  return JSON.parse(raw) as ModeClassificationResult
}
