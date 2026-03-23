export interface ModeAlternative {
  productMode: string
  styleMode: string
  confidence: number
}

export interface ModeReasoning {
  matchedKeywords: string[]
  matchedFeatures: string[]
  matchedAudienceSignals: string[]
  matchedToneSignals: string[]
}

export interface ModeClassificationResult {
  productMode: string
  styleMode: string
  confidence: number
  alternatives: ModeAlternative[]
  reasoning: ModeReasoning
}

export interface DesignTypeProfile {
  design_type: string
  layout_model: string
  density: string
  recommended_patterns: string[]
}

export interface CompositionBlueprint {
  default_pages: string[]
  section_order: string[]
  responsive_rules: Record<string, string>
}

export interface DesignPack {
  product_mode_categories: Record<string, string[]>
  style_modes: string[]
  design_type_profiles: Record<string, DesignTypeProfile>
  composition_blueprints: Record<string, CompositionBlueprint>
}

export interface ClassifyDesignModeRequest {
  projectId: string
  prompt: string
  appName?: string
  appType?: string
  description?: string
  features?: string[]
  targetAudience?: string
  preferredStyle?: string
}

export interface ClassifyDesignModeResponse {
  classification: ModeClassificationResult
  blueprint?: CompositionBlueprint | null
  recommendedPatterns: string[]
}
