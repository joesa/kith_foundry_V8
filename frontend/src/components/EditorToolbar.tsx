import { useState, useRef, useEffect } from "react";
import {
  Settings2,
  Minus,
  Plus,
  Map,
  WrapText,
  Paintbrush,
  ChevronDown,
  Indent,
  Type,
  Hash,
  SplitSquareHorizontal,
  Search,
} from "lucide-react";
import { THEMES, type ThemeMeta } from "./EditorThemes";

export interface EditorSettings {
  theme: string;
  fontSize: number;
  minimap: boolean;
  wordWrap: "on" | "off" | "bounded";
  lineNumbers: "on" | "off" | "relative";
  tabSize: number;
  stickyScroll: boolean;
  bracketPairColorization: boolean;
  fontLigatures: boolean;
  cursorBlinking: "blink" | "smooth" | "phase" | "expand" | "solid";
  renderWhitespace: "none" | "boundary" | "all";
}

export const DEFAULT_SETTINGS: EditorSettings = {
  theme: "kith-dark",
  fontSize: 13,
  minimap: false,
  wordWrap: "on",
  lineNumbers: "on",
  tabSize: 2,
  stickyScroll: true,
  bracketPairColorization: true,
  fontLigatures: true,
  cursorBlinking: "smooth",
  renderWhitespace: "none",
};

interface EditorToolbarProps {
  settings: EditorSettings;
  onChange: (patch: Partial<EditorSettings>) => void;
  onFindReplace?: () => void;
}

function Dropdown({ children, trigger }: { children: React.ReactNode; trigger: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <div onClick={() => setOpen(v => !v)}>{trigger}</div>
      {open && (
        <div className="absolute top-full mt-1 right-0 z-50 min-w-[200px] max-h-[360px] overflow-y-auto bg-[#1E1E2A] border border-[var(--kf-border-muted)] rounded-lg shadow-2xl shadow-black/50 py-1">
          {children}
        </div>
      )}
    </div>
  );
}

function ToolbarButton({
  active,
  title,
  onClick,
  children,
}: {
  active?: boolean;
  title: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={`p-1 rounded transition-colors ${
        active
          ? "text-indigo-400 bg-indigo-500/15"
          : "text-zinc-500 hover:text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)]/50"
      }`}
    >
      {children}
    </button>
  );
}

export function EditorToolbar({ settings, onChange, onFindReplace }: EditorToolbarProps) {
  const currentTheme = THEMES.find(t => t.id === settings.theme);

  return (
    <div className="flex items-center gap-0.5 px-2 py-1 bg-[#0F0F17] border-b border-[var(--kf-border)]/60 text-[11px]">
      {/* Theme picker */}
      <Dropdown
        trigger={
          <button className="flex items-center gap-1.5 px-2 py-1 rounded text-[var(--kf-text-secondary)] hover:text-[var(--kf-text)] hover:bg-[var(--kf-hover-bg)]/50 transition-colors">
            <Paintbrush className="w-3 h-3" />
            <span className="max-w-[100px] truncate">{currentTheme?.label ?? "Theme"}</span>
            <ChevronDown className="w-2.5 h-2.5 opacity-50" />
          </button>
        }
      >
        <div className="px-2 py-1.5 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Dark Themes</div>
        {THEMES.filter(t => t.base === "vs-dark" || t.base === "hc-black").map(t => (
          <ThemeOption key={t.id} theme={t} active={settings.theme === t.id} onSelect={() => onChange({ theme: t.id })} />
        ))}
        <div className="h-px bg-zinc-700/50 my-1" />
        <div className="px-2 py-1.5 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Light Themes</div>
        {THEMES.filter(t => t.base === "vs").map(t => (
          <ThemeOption key={t.id} theme={t} active={settings.theme === t.id} onSelect={() => onChange({ theme: t.id })} />
        ))}
      </Dropdown>

      <div className="w-px h-4 bg-zinc-700/50 mx-1" />

      {/* Font size */}
      <div className="flex items-center gap-0.5">
        <button
          onClick={() => onChange({ fontSize: Math.max(10, settings.fontSize - 1) })}
          className="p-1 rounded text-zinc-500 hover:text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)]/50 transition-colors"
          title="Decrease font size"
        >
          <Minus className="w-3 h-3" />
        </button>
        <span className="text-[var(--kf-text-secondary)] w-6 text-center tabular-nums" title="Font size">{settings.fontSize}</span>
        <button
          onClick={() => onChange({ fontSize: Math.min(28, settings.fontSize + 1) })}
          className="p-1 rounded text-zinc-500 hover:text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)]/50 transition-colors"
          title="Increase font size"
        >
          <Plus className="w-3 h-3" />
        </button>
      </div>

      <div className="w-px h-4 bg-zinc-700/50 mx-1" />

      {/* Quick toggles */}
      <ToolbarButton active={settings.minimap} title="Toggle minimap" onClick={() => onChange({ minimap: !settings.minimap })}>
        <Map className="w-3 h-3" />
      </ToolbarButton>

      <ToolbarButton active={settings.wordWrap === "on"} title="Toggle word wrap" onClick={() => onChange({ wordWrap: settings.wordWrap === "on" ? "off" : "on" })}>
        <WrapText className="w-3 h-3" />
      </ToolbarButton>

      {onFindReplace && (
        <ToolbarButton title="Find & Replace (Ctrl+H)" onClick={onFindReplace}>
          <Search className="w-3 h-3" />
        </ToolbarButton>
      )}

      <div className="flex-1" />

      {/* Settings dropdown */}
      <Dropdown
        trigger={
          <button className="p-1 rounded text-zinc-500 hover:text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)]/50 transition-colors" title="Editor settings">
            <Settings2 className="w-3.5 h-3.5" />
          </button>
        }
      >
        <div className="px-2 py-1.5 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Display</div>

        {/* Tab Size */}
        <SettingsRow icon={<Indent className="w-3 h-3" />} label="Tab Size">
          <select
            value={settings.tabSize}
            onChange={e => onChange({ tabSize: Number(e.target.value) })}
            className="bg-[var(--kf-badge-bg)] text-[var(--kf-text-secondary)] text-[11px] rounded px-1.5 py-0.5 border border-[var(--kf-border-muted)] outline-none"
          >
            <option value={2}>2</option>
            <option value={4}>4</option>
            <option value={8}>8</option>
          </select>
        </SettingsRow>

        {/* Line Numbers */}
        <SettingsRow icon={<Hash className="w-3 h-3" />} label="Line Numbers">
          <select
            value={settings.lineNumbers}
            onChange={e => onChange({ lineNumbers: e.target.value as EditorSettings["lineNumbers"] })}
            className="bg-[var(--kf-badge-bg)] text-[var(--kf-text-secondary)] text-[11px] rounded px-1.5 py-0.5 border border-[var(--kf-border-muted)] outline-none"
          >
            <option value="on">On</option>
            <option value="off">Off</option>
            <option value="relative">Relative</option>
          </select>
        </SettingsRow>

        {/* Cursor Style */}
        <SettingsRow icon={<Type className="w-3 h-3" />} label="Cursor Blink">
          <select
            value={settings.cursorBlinking}
            onChange={e => onChange({ cursorBlinking: e.target.value as EditorSettings["cursorBlinking"] })}
            className="bg-[var(--kf-badge-bg)] text-[var(--kf-text-secondary)] text-[11px] rounded px-1.5 py-0.5 border border-[var(--kf-border-muted)] outline-none"
          >
            <option value="smooth">Smooth</option>
            <option value="blink">Blink</option>
            <option value="phase">Phase</option>
            <option value="expand">Expand</option>
            <option value="solid">Solid</option>
          </select>
        </SettingsRow>

        {/* Whitespace */}
        <SettingsRow icon={<SplitSquareHorizontal className="w-3 h-3" />} label="Whitespace">
          <select
            value={settings.renderWhitespace}
            onChange={e => onChange({ renderWhitespace: e.target.value as EditorSettings["renderWhitespace"] })}
            className="bg-[var(--kf-badge-bg)] text-[var(--kf-text-secondary)] text-[11px] rounded px-1.5 py-0.5 border border-[var(--kf-border-muted)] outline-none"
          >
            <option value="none">None</option>
            <option value="boundary">Boundary</option>
            <option value="all">All</option>
          </select>
        </SettingsRow>

        <div className="h-px bg-zinc-700/50 my-1" />
        <div className="px-2 py-1.5 text-[10px] text-zinc-500 uppercase tracking-wider font-semibold">Features</div>

        <SettingsToggle label="Sticky Scroll" checked={settings.stickyScroll} onChange={v => onChange({ stickyScroll: v })} />
        <SettingsToggle label="Bracket Colorization" checked={settings.bracketPairColorization} onChange={v => onChange({ bracketPairColorization: v })} />
        <SettingsToggle label="Font Ligatures" checked={settings.fontLigatures} onChange={v => onChange({ fontLigatures: v })} />
        <SettingsToggle label="Minimap" checked={settings.minimap} onChange={v => onChange({ minimap: v })} />
        <SettingsToggle label="Word Wrap" checked={settings.wordWrap === "on"} onChange={v => onChange({ wordWrap: v ? "on" : "off" })} />
      </Dropdown>
    </div>
  );
}

function ThemeOption({ theme, active, onSelect }: { theme: ThemeMeta; active: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs transition-colors ${
        active ? "bg-indigo-500/15 text-indigo-300" : "text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)]/50 hover:text-[var(--kf-text)]"
      }`}
    >
      <span className={`w-2.5 h-2.5 rounded-full border ${
        active ? "bg-indigo-500 border-indigo-400" : "border-zinc-600"
      }`} />
      {theme.label}
    </button>
  );
}

function SettingsRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-3 py-1.5 text-xs text-[var(--kf-text-secondary)]">
      <div className="flex items-center gap-2 text-[var(--kf-text-secondary)]">
        {icon}
        <span>{label}</span>
      </div>
      {children}
    </div>
  );
}

function SettingsToggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className="w-full flex items-center justify-between px-3 py-1.5 text-xs text-[var(--kf-text-secondary)] hover:bg-[var(--kf-hover-bg)]/50 transition-colors"
    >
      <span>{label}</span>
      <div className={`w-7 h-4 rounded-full flex items-center px-0.5 transition-colors ${checked ? "bg-indigo-500" : "bg-zinc-700"}`}>
        <div className={`w-3 h-3 rounded-full bg-white transition-transform ${checked ? "translate-x-3" : "translate-x-0"}`} />
      </div>
    </button>
  );
}
