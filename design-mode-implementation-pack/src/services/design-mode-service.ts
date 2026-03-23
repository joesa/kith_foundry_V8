import fs from "node:fs/promises"
import path from "node:path"
import type { CompositionBlueprint, DesignPack, DesignTypeProfile } from "../types/design-mode"

export class DesignModeService {
  private pack: DesignPack | null = null

  async loadPack(): Promise<DesignPack> {
    if (this.pack) return this.pack

    const filePath = path.join(process.cwd(), "data", "design_mode_engine_pack.json")
    const raw = await fs.readFile(filePath, "utf-8")
    this.pack = JSON.parse(raw) as DesignPack
    return this.pack
  }

  async getAllProductModes(): Promise<string[]> {
    const pack = await this.loadPack()
    return Object.values(pack.product_mode_categories).flat()
  }

  async getAllStyleModes(): Promise<string[]> {
    const pack = await this.loadPack()
    return pack.style_modes
  }

  async getBlueprint(productMode: string): Promise<CompositionBlueprint | null> {
    const pack = await this.loadPack()
    return pack.composition_blueprints[productMode] ?? null
  }

  async getDesignProfile(productMode: string): Promise<DesignTypeProfile | null> {
    const pack = await this.loadPack()
    return pack.design_type_profiles[productMode] ?? null
  }
}
