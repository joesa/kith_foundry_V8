/**
 * ExportMenu
 *
 * A compact dropdown that lets the user download data in MD, DOCX, or PDF
 * for a given export target on their project.
 *
 * Usage:
 *   <ExportMenu projectId={id} target="csuite" />
 *   <ExportMenu projectId={id} target="artifacts" label="Download All" />
 *   <ExportMenu projectId={id} target="artifact/prd" label="PRD" size="sm" />
 */
import { useState, useRef, useEffect } from "react";
import { Download, FileText, FileType, File } from "lucide-react";
import { useApiFetch } from "../../hooks/useApiFetch";

type Format = "md" | "docx" | "pdf";

interface FormatMeta {
  fmt: Format;
  label: string;
  ext: string;
  icon: React.ReactNode;
}

const FORMATS: FormatMeta[] = [
  { fmt: "md", label: "Markdown (.md)", ext: "md", icon: <FileText size={14} /> },
  { fmt: "docx", label: "Word (.docx)", ext: "docx", icon: <FileType size={14} /> },
  { fmt: "pdf", label: "PDF (.pdf)", ext: "pdf", icon: <File size={14} /> },
];

interface ExportMenuProps {
  projectId: string;
  /** Export target path segment, e.g. "csuite", "artifacts", or "artifact/prd" */
  target: string;
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

export function ExportMenu({
  projectId,
  target,
  label,
  size = "md",
  className = "",
}: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState<Format | null>(null);
  const [error, setError] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const apiFetch = useApiFetch();

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const download = async (fmt: Format) => {
    setLoading(fmt);
    setError(null);
    try {
      const path = `/api/v1/projects/${projectId}/export/${target}.${fmt}`;
      const resp = await apiFetch(path);
      if (!resp.ok) {
        const msg = await resp.text().catch(() => resp.statusText);
        throw new Error(msg || `HTTP ${resp.status}`);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      // Derive a sensible filename from the Content-Disposition header if present,
      // or fall back to a generated name.
      const cd = resp.headers.get("Content-Disposition") ?? "";
      const match = cd.match(/filename="([^"]+)"/);
      a.download = match?.[1] ?? `${target.replace("/", "_")}.${fmt}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setOpen(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setLoading(null);
    }
  };

  const btnSize = size === "sm"
    ? "px-2 py-1 text-xs gap-1"
    : "px-3 py-1.5 text-sm gap-1.5";

  return (
    <div ref={menuRef} className={`relative inline-block ${className}`}>
      <button
        onClick={() => { setOpen((o) => !o); setError(null); }}
        className={`inline-flex items-center rounded-lg border border-white/20 bg-white/10 hover:bg-white/20 text-white font-medium transition-colors ${btnSize}`}
        title="Download report"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Download size={size === "sm" ? 12 : 14} />
        {label ?? "Download"}
      </button>

      {open && (
        <div className="absolute right-0 mt-1 w-44 rounded-xl shadow-2xl bg-gray-900 border border-white/10 z-50 overflow-hidden">
          {error && (
            <p className="px-3 py-2 text-xs text-red-400 border-b border-white/10">
              {error}
            </p>
          )}
          {FORMATS.map(({ fmt, label: fmtLabel, icon }) => (
            <button
              key={fmt}
              onClick={() => download(fmt)}
              disabled={loading !== null}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-200 hover:bg-white/10 transition-colors disabled:opacity-50"
            >
              {loading === fmt ? (
                <span className="h-3.5 w-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              ) : (
                <span className="text-gray-400">{icon}</span>
              )}
              {fmtLabel}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
