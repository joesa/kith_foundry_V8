import { useState, useEffect } from 'react';
import { ChevronDown, Loader2, RefreshCw, Server } from 'lucide-react';
import { getApiBaseUrl } from '../lib/runtimeConfig';
import { useAuth } from '../contexts/AuthContext';

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

    // Restore saved model on mount
    useEffect(() => {
        const saved = localStorage.getItem('kith_selected_model');
        if (saved && !selectedModel) {
            onChange(saved);
        }
    }, []);

    // Fetch providers & auto-expand first one every time dropdown opens
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
                // Auto-expand the first (or default) provider and fetch its models
                if (active.length > 0) {
                    const defaultP = active.find((p: ConfiguredProvider) => p.is_default) || active[0];
                    setExpandedProvider(defaultP.id);
                    if (!providerModels[defaultP.id]) {
                        setLoadingModels(defaultP.id);
                        try {
                            const mres = await fetch(`${API}/api/v1/providers/${defaultP.id}/models`, { headers });
                            const mdata = await mres.json();
                            setProviderModels(prev => ({ ...prev, [defaultP.id]: mdata.models || [] }));
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

    const handleSelect = (modelId: string) => {
        onChange(modelId);
        localStorage.setItem('kith_selected_model', modelId);
        setOpen(false);
    };

    const handleCustomSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (customModel.trim()) {
            handleSelect(customModel.trim());
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
                className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-200 transition-colors bg-[#1A1A24] px-3 py-1.5 rounded border border-zinc-800 w-full cursor-pointer"
            >
                <Server className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <span className="truncate flex-1 text-left">{displayName}</span>
                <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>

            {open && (
                <div className="absolute top-full left-0 mt-2 w-72 bg-[#1A1A24] border border-zinc-700 rounded-lg shadow-xl z-50 text-sm overflow-hidden flex flex-col max-h-[420px]">
                    <div className="flex-1 overflow-y-auto">
                        {providers.length === 0 ? (
                            <div className="text-zinc-500 text-center py-6 px-4">
                                <Server className="w-6 h-6 mx-auto mb-2 opacity-40" />
                                <p className="text-xs">No providers configured</p>
                                <p className="text-[11px] text-zinc-600 mt-1">
                                    Open Settings to add your API keys
                                </p>
                            </div>
                        ) : (
                            providers.map(p => (
                                <div key={p.id}>
                                    {/* Provider header */}
                                    <div
                                        onClick={() => fetchModels(p.id)}
                                        className="w-full flex items-center justify-between px-3 py-2.5 hover:bg-zinc-800/60 transition-colors cursor-pointer border-b border-zinc-800/50"
                                    >
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-semibold text-zinc-300">{p.name}</span>
                                            {p.is_default && (
                                                <span className="text-[9px] px-1 py-px rounded bg-amber-500/15 text-amber-400 border border-amber-500/20">
                                                    default
                                                </span>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-1">
                                            {loadingModels === p.id ? (
                                                <Loader2 className="w-3 h-3 text-zinc-500 animate-spin" />
                                            ) : providerModels[p.id] ? (
                                                <span
                                                    onClick={(e) => refreshModels(p.id, e)}
                                                    className="p-0.5 hover:bg-zinc-700 rounded cursor-pointer"
                                                    title="Refresh models"
                                                >
                                                    <RefreshCw className="w-3 h-3 text-zinc-600" />
                                                </span>
                                            ) : null}
                                            <ChevronDown className={`w-3 h-3 text-zinc-600 transition-transform ${expandedProvider === p.id ? 'rotate-180' : ''}`} />
                                        </div>
                                    </div>

                                    {/* Models list */}
                                    {expandedProvider === p.id && (
                                        <div className="bg-[#12121A]">
                                            {loadingModels === p.id ? (
                                                <div className="flex items-center justify-center py-3">
                                                    <Loader2 className="w-4 h-4 text-zinc-500 animate-spin" />
                                                    <span className="text-xs text-zinc-600 ml-2">Fetching models...</span>
                                                </div>
                                            ) : (providerModels[p.id] || []).length === 0 ? (
                                                <div className="text-zinc-600 text-xs text-center py-3">
                                                    No models found
                                                </div>
                                            ) : (
                                                <div className="max-h-[200px] overflow-y-auto">
                                                    {(providerModels[p.id] || []).map(modelId => (
                                                        <button
                                                            key={modelId}
                                                            onClick={() => handleSelect(modelId)}
                                                            className={`w-full text-left px-4 py-1.5 text-xs truncate transition-colors cursor-pointer ${selectedModel === modelId
                                                                ? 'bg-indigo-500/15 text-indigo-300'
                                                                : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
                                                                }`}
                                                            title={modelId}
                                                        >
                                                            {modelId}
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
                    <div className="border-t border-zinc-700 p-2">
                        <form onSubmit={handleCustomSubmit} className="flex gap-2">
                            <input
                                type="text"
                                value={customModel}
                                onChange={(e) => setCustomModel(e.target.value)}
                                placeholder="Custom model ID..."
                                className="flex-1 bg-[#12121A] border border-zinc-700 rounded px-2 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
                            />
                            <button
                                type="submit"
                                className="bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-2 rounded text-xs transition-colors cursor-pointer"
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
