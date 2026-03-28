import { useState, useEffect } from 'react';
import { cn } from '../../lib/utils/cn';
import { getApiBaseUrl } from '../../lib/runtimeConfig';
import { useAuth } from '../../contexts/AuthContext';

interface ConfiguredProvider {
    id: number;
    name: string;
    provider: string;
    is_active: boolean;
    is_default: boolean;
}

interface ModelSelectorProps {
    selectedModel: string;
    onChange: (model: string) => void;
}

const API = getApiBaseUrl();

export function ModelSelector({ selectedModel, onChange }: ModelSelectorProps) {
    const { getAccessToken } = useAuth();
    const [open, setOpen] = useState(false);
    const [providers, setProviders] = useState<ConfiguredProvider[]>([]);
    const [expandedProvider, setExpandedProvider] = useState<number | null>(null);
    const [providerModels, setProviderModels] = useState<Record<number, string[]>>({});
    const [loadingModels, setLoadingModels] = useState<number | null>(null);
    const [customModel, setCustomModel] = useState("");

    const persistCodeGenRouting = async (providerId: number | null, modelId: string | null): Promise<boolean> => {
        if (providerId == null) return false;
        try {
            const token = await getAccessToken();
            const headers: Record<string, string> = { "Content-Type": "application/json" };
            if (token) headers.Authorization = `Bearer ${token}`;
            const res = await fetch(`${API}/api/v1/model-routing/code_gen`, {
                method: "PUT",
                headers,
                body: JSON.stringify({ provider_id: providerId, model_id: modelId }),
            });
            return res.ok;
        } catch (err) {
            console.error("Failed to persist code_gen routing", err);
            return false;
        }
    };

    // Restore saved model on mount
    useEffect(() => {
        const saved = localStorage.getItem('kith_selected_model');
        if (saved && !selectedModel) {
            onChange(saved);
        }
    }, []);

    // Fetch providers and current persisted code_gen routing every time dropdown opens
    useEffect(() => {
        if (!open) return;
        (async () => {
            const token = await getAccessToken();
            const headers: Record<string, string> = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            try {
                const res = await fetch(`${API}/api/v1/providers`, { headers });
                const data = await res.json();
                const active = (data.providers || []).filter((p: ConfiguredProvider) => p.is_active);
                setProviders(active);

                // Prefer persisted code_gen routing over local browser state.
                let routedProviderId: number | null = null;
                try {
                    const rres = await fetch(`${API}/api/v1/model-routing`, { headers });
                    const rdata = await rres.json();
                    const codeGenRouting = (rdata.routings || []).find((r: any) => r.task_type === "code_gen");
                    const routedModel = codeGenRouting?.model_id || "";
                    routedProviderId = codeGenRouting?.provider_id ?? null;
                    if (routedModel) {
                        onChange(routedModel);
                        localStorage.setItem("kith_selected_model", routedModel);
                    }
                } catch (err) {
                    console.error("Failed to fetch model routing", err);
                }

                // Auto-expand the first (or default) provider and fetch its models
                if (active.length > 0) {
                    const defaultP = active.find((p: ConfiguredProvider) => p.is_default) || active[0];
                    const preferred = active.find((p: ConfiguredProvider) => p.id === routedProviderId) || defaultP;
                    setExpandedProvider(preferred.id);
                    if (!providerModels[preferred.id]) {
                        setLoadingModels(preferred.id);
                        try {
                            const mres = await fetch(`${API}/api/v1/providers/${preferred.id}/models`, { headers });
                            const mdata = await mres.json();
                            setProviderModels(prev => ({ ...prev, [preferred.id]: mdata.models || [] }));
                        } catch { /* ignore */ }
                        setLoadingModels(null);
                    }
                }
            } catch (err) {
                console.error("Failed to load providers", err);
            }
        })();
    }, [open]);

    const fetchModels = async (providerId: number) => {
        if (providerModels[providerId]) {
            // Already fetched, just toggle
            setExpandedProvider(expandedProvider === providerId ? null : providerId);
            return;
        }

        setLoadingModels(providerId);
        setExpandedProvider(providerId);
        try {
            const token = await getAccessToken();
            const headers: Record<string, string> = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            const res = await fetch(`${API}/api/v1/providers/${providerId}/models`, { headers });
            const data = await res.json();
            setProviderModels(prev => ({ ...prev, [providerId]: data.models || [] }));
        } catch (e) {
            console.error("Failed to fetch models", e);
            setProviderModels(prev => ({ ...prev, [providerId]: [] }));
        } finally {
            setLoadingModels(null);
        }
    };

    const refreshModels = async (providerId: number, e: React.MouseEvent) => {
        e.stopPropagation();
        setLoadingModels(providerId);
        try {
            const token = await getAccessToken();
            const headers: Record<string, string> = {};
            if (token) headers.Authorization = `Bearer ${token}`;
            const res = await fetch(`${API}/api/v1/providers/${providerId}/models`, { headers });
            const data = await res.json();
            setProviderModels(prev => ({ ...prev, [providerId]: data.models || [] }));
        } catch (err) {
            console.error("Failed to refresh models", err);
        } finally {
            setLoadingModels(null);
        }
    };

    const handleSelect = async (modelId: string, providerId?: number) => {
        if (providerId != null) {
            await persistCodeGenRouting(providerId, modelId);
        }
        onChange(modelId);
        localStorage.setItem('kith_selected_model', modelId);
        setOpen(false);
    };

    const handleCustomSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (customModel.trim()) {
            await handleSelect(customModel.trim(), expandedProvider ?? undefined);
            setCustomModel("");
        }
    };

    const displayName = selectedModel
        ? selectedModel.length > 28 ? "..." + selectedModel.slice(-25) : selectedModel
        : "Select Model";

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(!open)}
                className="flex items-center gap-2 text-xs text-secondary hover:text-on-surface transition-colors bg-surface-container px-3 py-1.5 rounded-full border border-outline-variant w-full cursor-pointer"
            >
                <span className="material-symbols-outlined text-primary shrink-0" style={{ fontSize: 14 }}>psychology</span>
                <span className="truncate flex-1 text-left">{displayName}</span>
                <span className={cn("material-symbols-outlined shrink-0 transition-transform", open ? "rotate-180" : "")} style={{ fontSize: 14 }}>
                    expand_more
                </span>
            </button>

            {open && (
                <div className="absolute top-full left-0 mt-2 w-72 bg-surface border border-outline-variant rounded-[var(--radius-module)] shadow-xl z-50 text-sm overflow-hidden flex flex-col max-h-[420px]">
                    <div className="flex-1 overflow-y-auto">
                        {providers.length === 0 ? (
                            <div className="text-tertiary text-center py-6 px-4">
                                <span className="material-symbols-outlined block mx-auto mb-2 opacity-40" style={{ fontSize: 24 }}>psychology</span>
                                <p className="text-xs">No providers configured</p>
                                <p className="text-[11px] text-tertiary mt-1">
                                    Open Settings to add your API keys
                                </p>
                            </div>
                        ) : (
                            providers.map(p => (
                                <div key={p.id}>
                                    {/* Provider header */}
                                    <div
                                        onClick={() => fetchModels(p.id)}
                                        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-surface-container transition-colors cursor-pointer border-b border-outline-variant"
                                    >
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-black text-secondary uppercase tracking-widest">{p.name}</span>
                                            {p.is_default && (
                                                <span className="text-[9px] px-1 py-px rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20">
                                                    default
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {loadingModels === p.id ? (
                                                <span className="material-symbols-outlined text-tertiary animate-spin" style={{ fontSize: 12 }}>refresh</span>
                                            ) : providerModels[p.id] ? (
                                                <span
                                                    onClick={(e) => refreshModels(p.id, e)}
                                                    className="p-0.5 hover:bg-surface-container rounded-full cursor-pointer"
                                                    title="Refresh models"
                                                >
                                                    <span className="material-symbols-outlined text-tertiary" style={{ fontSize: 12 }}>refresh</span>
                                                </span>
                                            ) : null}
                                            <span className={cn("material-symbols-outlined text-tertiary transition-transform", expandedProvider === p.id ? "rotate-180" : "")} style={{ fontSize: 12 }}>
                                                expand_more
                                            </span>
                                        </div>
                                    </div>

                                    {/* Models list */}
                                    {expandedProvider === p.id && (
                                        <div className="bg-surface-container">
                                            {loadingModels === p.id ? (
                                                <div className="flex items-center justify-center py-3">
                                                    <span className="material-symbols-outlined text-tertiary animate-spin" style={{ fontSize: 16 }}>refresh</span>
                                                    <span className="text-xs text-tertiary ml-2">Fetching models...</span>
                                                </div>
                                            ) : (providerModels[p.id] || []).length === 0 ? (
                                                <div className="text-tertiary text-xs text-center py-3">
                                                    No models found
                                                </div>
                                            ) : (
                                                <div className="max-h-[200px] overflow-y-auto">
                                                    {(providerModels[p.id] || []).map(modelId => (
                                                        <button
                                                            key={modelId}
                                                            onClick={() => handleSelect(modelId, p.id)}
                                                            className={cn(
                                                                "w-full text-left px-4 py-1.5 text-xs truncate transition-colors cursor-pointer flex items-center gap-2",
                                                                selectedModel === modelId
                                                                    ? 'bg-primary/15 text-primary'
                                                                    : 'text-secondary hover:bg-surface-container hover:text-on-surface'
                                                            )}
                                                            title={modelId}
                                                        >
                                                            {selectedModel === modelId && (
                                                                <span className="material-symbols-outlined shrink-0" style={{ fontSize: 12 }}>check</span>
                                                            )}
                                                            <span className="truncate">{modelId}</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ))
                        )}
                    </div>

                    {/* Custom model input */}
                    <div className="border-t border-outline-variant p-2">
                        <form onSubmit={handleCustomSubmit} className="flex gap-2">
                            <input
                                type="text"
                                value={customModel}
                                onChange={(e) => setCustomModel(e.target.value)}
                                placeholder="Custom model ID..."
                                className="flex-1 bg-surface-container border border-outline-variant rounded-full px-2 py-1.5 text-xs text-secondary focus:outline-none focus:border-primary"
                            />
                            <button
                                type="submit"
                                className="bg-surface-container hover:bg-surface border border-outline-variant text-secondary px-3 rounded-full text-xs font-black uppercase tracking-widest transition-colors cursor-pointer"
                            >
                                Set
                            </button>
                        </form>
                    </div>
                </div>
            )}

            {/* Click outside backdrop */}
            {open && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setOpen(false)}
                />
            )}
        </div>
    );
}
