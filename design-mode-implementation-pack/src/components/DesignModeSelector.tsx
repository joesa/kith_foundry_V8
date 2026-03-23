import React from "react"

type Props = {
  productModes: string[]
  styleModes: string[]
  value: { productMode: string; styleMode: string }
  onChange: (next: { productMode: string; styleMode: string }) => void
}

export function DesignModeSelector({ productModes, styleModes, value, onChange }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <label className="mb-2 block text-sm font-medium">Design Mode</label>
        <select
          className="w-full rounded border px-3 py-2"
          value={value.productMode}
          onChange={(e) => onChange({ ...value, productMode: e.target.value })}
        >
          {productModes.map((mode) => (
            <option key={mode} value={mode}>
              {mode}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium">Style Mode</label>
        <select
          className="w-full rounded border px-3 py-2"
          value={value.styleMode}
          onChange={(e) => onChange({ ...value, styleMode: e.target.value })}
        >
          {styleModes.map((style) => (
            <option key={style} value={style}>
              {style}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
