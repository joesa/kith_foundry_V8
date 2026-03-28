import { useState, useCallback, useMemo } from "react";
import { cn } from "../../lib/utils/cn";

// File type icon colors
const FILE_ICON_COLORS: Record<string, string> = {
    tsx: "#3B82F6",   // blue
    ts: "#3B82F6",
    jsx: "#F59E0B",   // amber
    js: "#F59E0B",
    css: "#A855F7",   // purple
    json: "#22C55E",  // green
    html: "#EF4444",  // red
    md: "#6B7280",    // gray
    svg: "#F97316",   // orange
};

function getFileColor(name: string): string {
    const ext = name.split(".").pop() || "";
    return FILE_ICON_COLORS[ext] || "#9CA3AF";
}

function getLanguageLabel(name: string): string {
    const ext = name.split(".").pop() || "";
    const labels: Record<string, string> = {
        tsx: "TSX", ts: "TS", jsx: "JSX", js: "JS",
        css: "CSS", json: "JSON", html: "HTML", md: "MD"
    };
    return labels[ext] || ext.toUpperCase();
}

export interface TreeNode {
    name: string;
    path: string;
    type: "file" | "dir";
    children?: TreeNode[];
}

interface FileExplorerProps {
    tree: TreeNode[];
    activeFile: string;
    onFileSelect: (path: string) => void;
    streamingFile: string | null;
}

export function FileExplorer({ tree, activeFile, onFileSelect, streamingFile }: FileExplorerProps) {
    const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set(["src", "src/components", "src/pages", "src/types", "src/utils"]));
    const [searchQuery, setSearchQuery] = useState("");
    const [contextMenu, setContextMenu] = useState<{ x: number; y: number; node: TreeNode } | null>(null);

    const toggleDir = useCallback((path: string) => {
        setExpandedDirs(prev => {
            const next = new Set(prev);
            if (next.has(path)) {
                next.delete(path);
            } else {
                next.add(path);
            }
            return next;
        });
    }, []);

    const handleContextMenu = useCallback((e: React.MouseEvent, node: TreeNode) => {
        e.preventDefault();
        setContextMenu({ x: e.clientX, y: e.clientY, node });
    }, []);

    // Filter tree based on search
    const filteredTree = useMemo(() => {
        if (!searchQuery.trim()) return tree;

        function filterNodes(nodes: TreeNode[]): TreeNode[] {
            return nodes.reduce<TreeNode[]>((acc, node) => {
                if (node.type === "file") {
                    if (node.name.toLowerCase().includes(searchQuery.toLowerCase())) {
                        acc.push(node);
                    }
                } else if (node.children) {
                    const filtered = filterNodes(node.children);
                    if (filtered.length > 0) {
                        acc.push({ ...node, children: filtered });
                    }
                }
                return acc;
            }, []);
        }

        return filterNodes(tree);
    }, [tree, searchQuery]);

    return (
        <div
            className="h-full flex flex-col bg-surface-container-lowest select-none"
            onClick={() => setContextMenu(null)}
        >
            {/* Header */}
            <div className="px-3 py-2.5 border-b border-outline-variant flex items-center justify-between">
                <span className="text-[11px] font-black text-tertiary uppercase tracking-widest">Explorer</span>
                <div className="flex items-center gap-1">
                    <button
                        className="p-1 rounded-full hover:bg-surface-container text-tertiary hover:text-on-surface transition-colors"
                        title="New File"
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>add</span>
                    </button>
                    <button
                        className="p-1 rounded-full hover:bg-surface-container text-tertiary hover:text-on-surface transition-colors"
                        title="New Folder"
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>create_new_folder</span>
                    </button>
                </div>
            </div>

            {/* Search */}
            <div className="px-2 py-1.5 border-b border-outline-variant">
                <div className="flex items-center gap-1.5 bg-surface-container rounded px-2 py-1">
                    <span className="material-symbols-outlined text-tertiary" style={{ fontSize: 12 }}>search</span>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search files..."
                        className="bg-transparent text-xs text-secondary placeholder:text-tertiary outline-none w-full"
                    />
                </div>
            </div>

            {/* Tree */}
            <div className="flex-1 overflow-y-auto overflow-x-hidden py-1">
                {filteredTree.length === 0 ? (
                    <div className="px-3 py-4 text-xs text-tertiary text-center">
                        {searchQuery ? "No matching files" : "No files yet"}
                    </div>
                ) : (
                    <TreeView
                        nodes={filteredTree}
                        depth={0}
                        expandedDirs={expandedDirs}
                        toggleDir={toggleDir}
                        activeFile={activeFile}
                        onFileSelect={onFileSelect}
                        onContextMenu={handleContextMenu}
                        streamingFile={streamingFile}
                    />
                )}
            </div>

            {/* Context Menu */}
            {contextMenu && (
                <div
                    className="fixed z-50 bg-surface-container border border-outline-variant rounded-[var(--radius-module)] shadow-xl py-1 min-w-[160px]"
                    style={{ left: contextMenu.x, top: contextMenu.y }}
                >
                    <ContextMenuItem
                        icon={<span className="material-symbols-outlined" style={{ fontSize: 14 }}>add</span>}
                        label="New File"
                    />
                    <ContextMenuItem
                        icon={<span className="material-symbols-outlined" style={{ fontSize: 14 }}>create_new_folder</span>}
                        label="New Folder"
                    />
                    <div className="h-px bg-outline-variant my-1" />
                    <ContextMenuItem
                        icon={<span className="material-symbols-outlined" style={{ fontSize: 14 }}>delete</span>}
                        label="Delete"
                        danger
                    />
                </div>
            )}
        </div>
    );
}

function ContextMenuItem({ icon, label, danger, onClick }: { icon: React.ReactNode; label: string; danger?: boolean; onClick?: () => void }) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "w-full flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-surface-container transition-colors",
                danger ? "text-red-400 hover:text-red-300" : "text-secondary hover:text-on-surface"
            )}
        >
            {icon}
            {label}
        </button>
    );
}

interface TreeViewProps {
    nodes: TreeNode[];
    depth: number;
    expandedDirs: Set<string>;
    toggleDir: (path: string) => void;
    activeFile: string;
    onFileSelect: (path: string) => void;
    onContextMenu: (e: React.MouseEvent, node: TreeNode) => void;
    streamingFile: string | null;
}

function TreeView({ nodes, depth, expandedDirs, toggleDir, activeFile, onFileSelect, onContextMenu, streamingFile }: TreeViewProps) {
    return (
        <>
            {nodes.map((node) => {
                const isExpanded = expandedDirs.has(node.path);
                const isActive = node.path === activeFile;
                const isStreaming = node.path === streamingFile;
                const paddingLeft = 8 + depth * 14;

                if (node.type === "dir") {
                    return (
                        <div key={node.path}>
                            <button
                                onClick={() => toggleDir(node.path)}
                                onContextMenu={(e) => onContextMenu(e, node)}
                                className="w-full flex items-center gap-1.5 py-[3px] hover:bg-surface-container transition-colors group"
                                style={{ paddingLeft }}
                            >
                                <span className="material-symbols-outlined text-tertiary shrink-0" style={{ fontSize: 12 }}>
                                    {isExpanded ? "expand_more" : "chevron_right"}
                                </span>
                                <span className="material-symbols-outlined shrink-0" style={{ fontSize: 14, color: "#F59E0B", opacity: isExpanded ? 0.8 : 0.6 }}>
                                    {isExpanded ? "folder_open" : "folder"}
                                </span>
                                <span className="text-[12px] text-secondary group-hover:text-on-surface truncate">
                                    {node.name}
                                </span>
                            </button>
                            {isExpanded && node.children && (
                                <TreeView
                                    nodes={node.children}
                                    depth={depth + 1}
                                    expandedDirs={expandedDirs}
                                    toggleDir={toggleDir}
                                    activeFile={activeFile}
                                    onFileSelect={onFileSelect}
                                    onContextMenu={onContextMenu}
                                    streamingFile={streamingFile}
                                />
                            )}
                        </div>
                    );
                }

                return (
                    <button
                        key={node.path}
                        onClick={() => onFileSelect(node.path)}
                        onContextMenu={(e) => onContextMenu(e, node)}
                        className={cn(
                            "w-full flex items-center gap-1.5 py-[3px] transition-colors group",
                            isActive
                                ? "bg-primary/10 text-primary"
                                : "hover:bg-surface-container text-secondary hover:text-on-surface"
                        )}
                        style={{ paddingLeft: paddingLeft + 14 }}
                    >
                        <span
                            className="material-symbols-outlined shrink-0"
                            style={{ fontSize: 14, color: getFileColor(node.name) }}
                        >
                            description
                        </span>
                        <span className="text-[12px] truncate">{node.name}</span>
                        {isStreaming && (
                            <span className="ml-auto mr-2 w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse shrink-0" />
                        )}
                        <span
                            className="text-[9px] text-tertiary opacity-0 group-hover:opacity-100 transition-opacity font-mono shrink-0"
                            style={{ marginLeft: isStreaming ? 0 : "auto", marginRight: 8 }}
                        >
                            {getLanguageLabel(node.name)}
                        </span>
                    </button>
                );
            })}
        </>
    );
}
