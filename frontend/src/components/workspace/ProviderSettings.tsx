import { useState, useEffect } from "react";
import { cn } from "../../lib/utils/cn";
import { getApiBaseUrl } from "../../lib/runtimeConfig";
import { useAuth } from "../../contexts/AuthContext";

const PROVIDERS = [
    { id: "anthropic", name: "Anthropic", icon: "psychology", color: "#D97757" },
    { id: "openai", name: "OpenAI", icon: "bolt", color: "#10A37F" },
    { id: "openai_compatible", name: "OpenAI Compatible", icon: "dns", color: "#818CF8" },
    { id: "openrouter", name: "OpenRouter", icon: "cloud", color: "#9333EA" },
    { id: "google_ai", name: "Google AI", icon: "auto_awesome", color: "#4285F4" },
    { id: "azure_openai", name: "Azure OpenAI", icon: "cloud_queue", color: "#0078D4" },
    { id: "ollama", name: "Ollama", icon: "memory", color: "#FFFFFF" },
    { id: "lm_studio", name: "LM Studio", icon: "psychology", color: "#22D3EE" },
    { id: "cohere", name: "Cohere", icon: "auto_awesome", color: "#39A275" },
    { id: "huggingface", name: "Hugging Face", icon: "smart_toy", color: "#FFD21E" },
];

interface ProviderEntry {
    id: number;
    name: string;
    provider: string;
    api_key_masked: string;
    base_url: string | null;
    is_default: boolean;
    is_active: boolean;
    created_at: string | null;
    last_used_at: string | null;
}

interface ModelRoutingEntry {
    task_type: string;
    task_label: string;
    provider_id: number | null;
    provider_name: string | null;
    model_id: string | null;
}

interface ProviderSettingsProps {
    onClose?: () => void;
    /** When true, renders inline (no modal overlay, no close button) */
    inline?: boolean;
}

const API = getApiBaseUrl();

export function ProviderSettings({ onClose, inline = false }: ProviderSettingsProps) {
    const { getAccessToken } = useAuth();
    const [providers, setProviders] = useState<ProviderEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState<number | null>(null);

    // Form state
    const [selectedProvider, setSelectedProvider] = useState("anthropic");
    const [keyName, setKeyName] = useState("");
    const [apiKey, setApiKey] = useState("");
    const [baseUrl, setBaseUrl] = useState("");
    const [isDefault, setIsDefault] = useState(false);
    const [showKey, setShowKey] = useState(false);
    const [saving, setSaving] = useState(false);

    // Test state
    const [testingId, setTestingId] = useState<number | null>(null);
    const [testResult, setTestResult] = useState<{ id: number; success: boolean; message: string } | null>(null);

    // Routing state
    const [routings, setRoutings] = useState<ModelRoutingEntry[]>([]);
    const [providerModels, setProviderModels] = useState<Record<number, any[]>>({});

    const fetchProviders = async (token?: string | null) => {
        try {
            const t = token ?? await getAccessToken();
            if (!t) return;
            const res = await fetch(`${API}/api/v1/providers`, {
                headers: { Authorization: `Bearer ${t}` }
            });
            if (!res.ok) {
                const body = await res.text();
                throw new Error(`providers ${res.status}: ${body.slice(0, 180)}`);
            }
            const data = await res.json();
            setProviders(data.providers || []);
        } catch (e) {
            console.error("Failed to load providers", e);
        } finally {
            setLoading(false);
        }
    };

    const fetchRoutings = async (token?: string | null) => {
        try {
            const t = token ?? await getAccessToken();
            if (!t) return;
            const res = await fetch(`${API}/api/v1/model-routing`, {
                headers: { Authorization: `Bearer ${t}` }
            });
            if (!res.ok) {
                const body = await res.text();
                throw new Error(`model-routing ${res.status}: ${body.slice(0, 180)}`);
            }
            const data = await res.json();
            setRoutings(data.routings || []);
        } catch (e) {
            console.error("Failed to load routings", e);
        }
    };

    const loadProviderModels = async (providerId: number) => {
        if (providerModels[providerId]) return;
        try {
            const token = await getAccessToken();
            if (!token) return;
            const res = await fetch(`${API}/api/v1/providers/${providerId}/models`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            setProviderModels(prev => ({ ...prev, [providerId]: data.models || [] }));
        } catch (e) {
            console.error("Failed to load models for provider", providerId, e);
        }
    };

    useEffect(() => {
        // Fetch token once and share it to avoid concurrent refresh races
        getAccessToken().then(async (token) => {
            if (!token) {
                setLoading(false);
                return;
            }
            fetchProviders(token);
            const res = await fetch(`${API}/api/v1/model-routing`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) {
                const body = await res.text();
                throw new Error(`model-routing ${res.status}: ${body.slice(0, 180)}`);
            }
            const data = await res.json();
            const r: ModelRoutingEntry[] = data.routings || [];
            setRoutings(r);
            // Pre-load models for any already-configured providers
            const configuredProviderIds = [...new Set(
                r
                    .map((rt) => rt.provider_id)
                    .filter((providerId): providerId is number => providerId != null)
            )];
            for (const pid of configuredProviderIds) {
                loadProviderModels(pid);
            }
        });
    }, []);

    const resetForm = () => {
        setSelectedProvider("anthropic");
        setKeyName("");
        setApiKey("");
        setBaseUrl("");
        setIsDefault(false);
        setShowKey(false);
        setEditingId(null);
    };

    const handleSubmit = async () => {
        if (!apiKey.trim()) return;
        setSaving(true);
        try {
            const token = await getAccessToken();
            if (editingId) {
                await fetch(`${API}/api/v1/providers/${editingId}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        name: keyName || undefined,
                        api_key: apiKey || undefined,
                        base_url: baseUrl || null,
                    }),
                });
            } else {
                await fetch(`${API}/api/v1/providers`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify({
                        name: keyName || `${PROVIDERS.find(p => p.id === selectedProvider)?.name} Key`,
                        provider: selectedProvider,
                        api_key: apiKey,
                        base_url: baseUrl || null,
                        is_default: isDefault,
                    }),
                });
            }
            await fetchProviders();
            resetForm();
            setShowForm(false);
        } catch (e) {
            console.error("Failed to save provider", e);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Delete this provider key?")) return;
        const token = await getAccessToken();
        await fetch(`${API}/api/v1/providers/${id}`, {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` }
        });
        await fetchProviders();
    };

    const handleSetDefault = async (id: number) => {
        const token = await getAccessToken();
        await fetch(`${API}/api/v1/providers/${id}/default`, {
            method: "PATCH",
            headers: { Authorization: `Bearer ${token}` }
        });
        await fetchProviders();
    };

    const handleToggle = async (id: number) => {
        const token = await getAccessToken();
        await fetch(`${API}/api/v1/providers/${id}/toggle`, {
            method: "PATCH",
            headers: { Authorization: `Bearer ${token}` }
        });
        await fetchProviders();
    };

    const handleTest = async (id: number) => {
        setTestingId(id);
        setTestResult(null);
        try {
            const token = await getAccessToken();
            const res = await fetch(`${API}/api/v1/providers/${id}/test`, {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            setTestResult({ id, success: data.success, message: data.message });
        } catch {
            setTestResult({ id, success: false, message: "Connection failed" });
        } finally {
            setTestingId(null);
        }
    };

    const handleUpdateRouting = async (task_type: string, provider_id: number | null, model_id: string | null) => {
        try {
            const token = await getAccessToken();
            if (provider_id === null) {
                await fetch(`${API}/api/v1/model-routing/${task_type}`, {
                    method: "DELETE",
                    headers: { Authorization: `Bearer ${token}` }
                });
            } else {
                const res = await fetch(`${API}/api/v1/model-routing/${task_type}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`
                    },
                    body: JSON.stringify({ provider_id, model_id }),
                });
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    console.error(`Failed to update routing (${res.status}):`, err.detail || err);
                    return;
                }
            }
            await fetchRoutings();
        } catch (e) {
            console.error("Failed to update routing", e);
        }
    };

    const handleEdit = (p: ProviderEntry) => {
        setEditingId(p.id);
        setSelectedProvider(p.provider);
        setKeyName(p.name);
        setApiKey("");
        setBaseUrl(p.base_url || "");
        setShowForm(true);
    };

    const getProviderInfo = (id: string) => PROVIDERS.find(p => p.id === id) || PROVIDERS[0];

    const formatDate = (iso: string | null) => {
        if (!iso) return null;
        return new Date(iso).toLocaleDateString("en-US", {
            month: "short", day: "numeric", year: "numeric",
            hour: "2-digit", minute: "2-digit"
        });
    };

    const providerInfo = getProviderInfo(selectedProvider);

    const urlPlaceholder = (() => {
        switch (selectedProvider) {
            case "ollama": return "http://localhost:11434";
            case "lm_studio": return "http://localhost:1234/v1";
            case "openai_compatible": return "https://openrouter.ai/api/v1";
            case "azure_openai": return "https://your-resource.openai.azure.com";
            default: return "https://api.example.com/v1";
        }
    })();

    const needsBaseUrl = ["openai_compatible", "azure_openai", "ollama", "lm_studio"].includes(selectedProvider);

    const innerContent = (
        <>
            {/* Header */}
            <div className={cn("flex items-center justify-between", inline ? "mb-6" : "px-6 py-5 border-b border-outline-variant")}>
                {!inline && (
                    <div>
                        <h2 className="text-xl font-black text-on-surface uppercase tracking-widest cinematic-tracking">AI Provider Settings</h2>
                        <p className="text-sm text-tertiary mt-1">
                            Manage your custom API keys for different AI providers.
                        </p>
                    </div>
                )}
                <div className={cn("flex items-center gap-3", inline ? "ml-auto" : "")}>
                    <button
                        onClick={() => { resetForm(); setShowForm(true); }}
                        className="flex items-center gap-2 bg-primary hover:bg-primary/80 text-on-primary text-sm px-4 py-2 rounded-full font-black uppercase tracking-widest transition-colors cursor-pointer"
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
                        Connect Provider
                    </button>
                    {!inline && onClose && (
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-surface-container rounded-full text-tertiary hover:text-on-surface transition-colors cursor-pointer"
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: 20 }}>close</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className={inline ? "" : "flex-1 overflow-y-auto px-6 py-4"}>
                {/* Security banner */}
                <div className="flex items-start gap-3 bg-primary/5 border border-primary/15 rounded-[var(--radius-module)] p-4 mb-6">
                    <span className="material-symbols-outlined text-primary shrink-0 mt-0.5" style={{ fontSize: 20 }}>shield</span>
                    <div>
                        <p className="text-sm font-black text-primary uppercase tracking-widest">Enterprise-Grade Security</p>
                        <p className="text-xs text-tertiary mt-1">
                            Your API keys are encrypted at rest using AES-256. They are never exposed to the client-side
                            and are only decrypted securely within our server environment when making API requests.
                        </p>
                    </div>
                </div>

                {/* Configured Keys */}
                <div className="mb-6">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="material-symbols-outlined text-primary" style={{ fontSize: 16 }}>key</span>
                        <h3 className="text-sm font-black text-on-surface uppercase tracking-widest">Configured Keys</h3>
                        <span className="text-xs bg-surface-container text-secondary px-1.5 py-0.5 rounded-full">{providers.length}</span>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-8">
                            <span className="material-symbols-outlined text-tertiary animate-spin" style={{ fontSize: 20 }}>refresh</span>
                        </div>
                    ) : providers.length === 0 ? (
                        <div className="text-center py-8 text-tertiary">
                            <span className="material-symbols-outlined block mx-auto mb-2 opacity-40" style={{ fontSize: 32 }}>key</span>
                            <p className="text-sm">No providers configured yet</p>
                            <p className="text-xs mt-1">Click "Connect Provider" to add your first API key</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {providers.map(p => {
                                const info = getProviderInfo(p.provider);
                                return (
                                    <div
                                        key={p.id}
                                        className={cn(
                                            "flex items-center gap-4 px-4 py-3 rounded-[var(--radius-module)] border transition-colors steel-gradient ghost-border",
                                            !p.is_active && "opacity-50"
                                        )}
                                    >
                                        <div
                                            className="w-10 h-10 rounded-[var(--radius-module)] flex items-center justify-center shrink-0"
                                            style={{ backgroundColor: info.color + "15" }}
                                        >
                                            <span className="material-symbols-outlined" style={{ fontSize: 20, color: info.color }}>{info.icon}</span>
                                        </div>

                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-black text-on-surface uppercase tracking-widest truncate">{p.name}</span>
                                                {p.is_default && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20 flex items-center gap-1 font-black uppercase tracking-widest">
                                                        <span className="material-symbols-outlined" style={{ fontSize: 10 }}>star</span> Default
                                                    </span>
                                                )}
                                                <span className={cn(
                                                    "text-[10px] px-1.5 py-0.5 rounded-full font-black uppercase tracking-widest",
                                                    p.is_active
                                                        ? "bg-green-500/15 text-green-400 border border-green-500/20"
                                                        : "bg-outline-variant/30 text-tertiary border border-outline-variant/30"
                                                )}>
                                                    {p.is_active ? "Active" : "Inactive"}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2 mt-1 text-xs text-tertiary">
                                                <span>{info.name}</span>
                                                <span>•</span>
                                                <span>Added {formatDate(p.created_at)}</span>
                                                {p.last_used_at && (
                                                    <>
                                                        <span>•</span>
                                                        <span>Last used {formatDate(p.last_used_at)}</span>
                                                    </>
                                                )}
                                                {p.base_url && (
                                                    <>
                                                        <span>•</span>
                                                        <span className="bg-surface-container px-1.5 py-0.5 rounded text-[10px] font-mono truncate max-w-[180px]">
                                                            {p.base_url}
                                                        </span>
                                                    </>
                                                )}
                                            </div>
                                            {/* Test result */}
                                            {testResult && testResult.id === p.id && (
                                                <div className={cn(
                                                    "mt-2 text-xs px-2 py-1 rounded-full",
                                                    testResult.success
                                                        ? "bg-green-500/10 text-green-400 border border-green-500/20"
                                                        : "bg-red-500/10 text-red-400 border border-red-500/20"
                                                )}>
                                                    {testResult.message}
                                                </div>
                                            )}
                                        </div>

                                        {/* Actions */}
                                        <div className="flex items-center gap-1 shrink-0">
                                            <button
                                                onClick={() => handleSetDefault(p.id)}
                                                className={cn(
                                                    "p-1.5 rounded-full hover:bg-surface-container transition-colors cursor-pointer",
                                                    p.is_default ? "text-amber-400" : "text-tertiary hover:text-secondary"
                                                )}
                                                title="Set as default"
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>star</span>
                                            </button>
                                            <button
                                                onClick={() => handleTest(p.id)}
                                                className="p-1.5 rounded-full text-tertiary hover:text-secondary hover:bg-surface-container transition-colors cursor-pointer"
                                                title="Test connection"
                                                disabled={testingId === p.id}
                                            >
                                                {testingId === p.id ? (
                                                    <span className="material-symbols-outlined animate-spin" style={{ fontSize: 14 }}>refresh</span>
                                                ) : (
                                                    <span className="material-symbols-outlined" style={{ fontSize: 14 }}>science</span>
                                                )}
                                            </button>
                                            <button
                                                onClick={() => handleToggle(p.id)}
                                                className={cn(
                                                    "p-1.5 rounded-full hover:bg-surface-container transition-colors cursor-pointer",
                                                    p.is_active ? "text-green-500 hover:text-red-400" : "text-tertiary hover:text-green-400"
                                                )}
                                                title={p.is_active ? "Deactivate" : "Activate"}
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>power_settings_new</span>
                                            </button>
                                            <button
                                                onClick={() => handleEdit(p)}
                                                className="p-1.5 rounded-full text-tertiary hover:text-secondary hover:bg-surface-container transition-colors cursor-pointer"
                                                title="Edit"
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>edit</span>
                                            </button>
                                            <div className="w-px h-4 bg-outline-variant mx-0.5" />
                                            <button
                                                onClick={() => handleDelete(p.id)}
                                                className="p-1.5 rounded-full text-tertiary hover:text-red-400 hover:bg-surface-container transition-colors cursor-pointer"
                                                title="Delete"
                                            >
                                                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>delete</span>
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Model Routing */}
                <div className="mb-6">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-primary" style={{ fontSize: 16 }}>psychology</span>
                            <h3 className="text-sm font-black text-on-surface uppercase tracking-widest">Task Routing</h3>
                        </div>
                        <span className="text-xs text-tertiary">Route specific tasks to specific models</span>
                    </div>
                    <div className="space-y-3">
                        {routings.length === 0 ? (
                            <div className="text-sm text-tertiary text-center py-4">Loading routing configurations...</div>
                        ) : routings.map(r => (
                            <div key={r.task_type} className="flex flex-col gap-2 p-3 rounded-[var(--radius-module)] border border-outline-variant bg-surface steel-gradient ghost-border">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm font-black text-on-surface uppercase tracking-widest">{r.task_label}</span>
                                    <button
                                        onClick={() => handleUpdateRouting(r.task_type, null, null)}
                                        className="text-xs text-tertiary hover:text-secondary disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer font-black uppercase tracking-widest"
                                        disabled={!r.provider_id}
                                    >
                                        Reset to Default
                                    </button>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <select
                                        className="bg-surface-container border border-outline-variant rounded-full px-3 py-2 text-sm text-secondary focus:outline-none focus:border-primary cursor-pointer"
                                        value={r.provider_id || ""}
                                        onChange={(e) => {
                                            const pid = e.target.value ? Number(e.target.value) : null;
                                            if (pid) loadProviderModels(pid);
                                            handleUpdateRouting(r.task_type, pid, null);
                                        }}
                                    >
                                        <option value="">Default Provider</option>
                                        {providers.filter(p => p.is_active).map(p => (
                                            <option key={p.id} value={p.id}>{p.name} ({getProviderInfo(p.provider).name})</option>
                                        ))}
                                    </select>
                                    <select
                                        className="bg-surface-container border border-outline-variant rounded-full px-3 py-2 text-sm text-secondary focus:outline-none focus:border-primary disabled:opacity-50 cursor-pointer"
                                        value={r.model_id || ""}
                                        onChange={(e) => handleUpdateRouting(r.task_type, r.provider_id, e.target.value || null)}
                                        disabled={!r.provider_id}
                                    >
                                        <option value="">Default Model</option>
                                        {r.provider_id && providerModels[r.provider_id]?.map((m: any, idx: number) => {
                                            const modelId = typeof m === 'string' ? m : m.id;
                                            return <option key={`${modelId}-${idx}`} value={modelId}>{modelId}</option>;
                                        })}
                                    </select>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Add/Edit Form */}
                {showForm && (
                    <div className="border border-outline-variant rounded-[var(--radius-module)] p-5 bg-surface steel-gradient ghost-border mb-6">
                        <h3 className="text-sm font-black text-on-surface uppercase tracking-widest mb-4">
                            {editingId ? "Edit Provider" : "Select Provider"}
                        </h3>

                        {/* Provider grid */}
                        {!editingId && (
                            <div className="grid grid-cols-3 gap-2 mb-6">
                                {PROVIDERS.map(p => (
                                    <button
                                        key={p.id}
                                        onClick={() => setSelectedProvider(p.id)}
                                        className={cn(
                                            "flex flex-col items-center gap-2 py-3 px-2 rounded-[var(--radius-module)] border transition-all cursor-pointer",
                                            selectedProvider === p.id
                                                ? "border-primary bg-primary/10 text-on-surface"
                                                : "border-outline-variant hover:border-outline-variant/80 text-secondary hover:text-on-surface"
                                        )}
                                    >
                                        <span className="material-symbols-outlined" style={{ fontSize: 20, color: p.color }}>{p.icon}</span>
                                        <span className="text-xs font-black uppercase tracking-widest">{p.name}</span>
                                    </button>
                                ))}
                            </div>
                        )}

                        {/* Key Name */}
                        <div className="mb-4">
                            <label className="block text-sm font-black text-secondary uppercase tracking-widest mb-1.5">Key Name</label>
                            <div className="relative">
                                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-tertiary" style={{ fontSize: 16 }}>key</span>
                                <input
                                    type="text"
                                    value={keyName}
                                    onChange={e => setKeyName(e.target.value)}
                                    placeholder="e.g. My Production Key"
                                    className="w-full bg-surface-container border border-outline-variant rounded-full pl-10 pr-4 py-2.5 text-sm text-secondary focus:outline-none focus:border-primary placeholder:text-tertiary"
                                />
                            </div>
                            <p className="text-xs text-tertiary mt-1">A friendly name to identify this key.</p>
                        </div>

                        {/* API Key */}
                        <div className="mb-4">
                            <label className="block text-sm font-black text-secondary uppercase tracking-widest mb-1.5">
                                API Key <span className="text-red-400">*</span>
                            </label>
                            <div className="relative">
                                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-primary" style={{ fontSize: 16 }}>key</span>
                                <input
                                    type={showKey ? "text" : "password"}
                                    value={apiKey}
                                    onChange={e => setApiKey(e.target.value)}
                                    placeholder="sk-••••••••••••"
                                    className="w-full bg-surface-container border border-primary/30 rounded-full pl-10 pr-12 py-2.5 text-sm text-secondary focus:outline-none focus:border-primary placeholder:text-tertiary"
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowKey(v => !v)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-tertiary hover:text-secondary cursor-pointer"
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{showKey ? "visibility_off" : "visibility"}</span>
                                </button>
                            </div>
                            <p className="text-xs text-tertiary mt-1 flex items-center gap-1">
                                <span className="material-symbols-outlined" style={{ fontSize: 12 }}>shield</span>
                                Encrypted securely. Never shared with third parties.
                            </p>
                        </div>

                        {/* Base URL */}
                        <div className="mb-4">
                            <label className="block text-sm font-black text-secondary uppercase tracking-widest mb-1.5">
                                Base URL {needsBaseUrl ? "" : "(Optional)"}
                            </label>
                            <div className="relative">
                                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-tertiary" style={{ fontSize: 16 }}>cloud</span>
                                <input
                                    type="text"
                                    value={baseUrl}
                                    onChange={e => setBaseUrl(e.target.value)}
                                    placeholder={urlPlaceholder}
                                    className="w-full bg-surface-container border border-outline-variant rounded-full pl-10 pr-4 py-2.5 text-sm text-secondary focus:outline-none focus:border-primary placeholder:text-tertiary"
                                />
                            </div>
                            <p className="text-xs text-tertiary mt-1">
                                {needsBaseUrl
                                    ? `Required. Example: ${urlPlaceholder}`
                                    : "Required for local models (Ollama, LM Studio) or proxy usage."
                                }
                            </p>
                        </div>

                        {/* Set as default checkbox */}
                        {!editingId && (
                            <div className="flex items-start gap-3 bg-surface border border-outline-variant rounded-[var(--radius-module)] p-3 mb-5">
                                <input
                                    type="checkbox"
                                    id="set-default"
                                    checked={isDefault}
                                    onChange={e => setIsDefault(e.target.checked)}
                                    className="mt-0.5 accent-primary"
                                />
                                <label htmlFor="set-default" className="cursor-pointer">
                                    <p className="text-sm font-black text-on-surface uppercase tracking-widest">
                                        Set as default for {providerInfo.name}
                                    </p>
                                    <p className="text-xs text-tertiary mt-0.5">
                                        New requests for this provider will use this key automatically.
                                    </p>
                                </label>
                            </div>
                        )}

                        {/* Action buttons */}
                        <div className="flex justify-end gap-3 pt-2 border-t border-outline-variant">
                            <button
                                onClick={() => { resetForm(); setShowForm(false); }}
                                className="px-4 py-2 text-sm font-black uppercase tracking-widest text-secondary hover:text-on-surface bg-surface-container hover:bg-surface rounded-full transition-colors cursor-pointer"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSubmit}
                                disabled={!apiKey.trim() || saving}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-black uppercase tracking-widest bg-primary hover:bg-primary/80 text-on-primary rounded-full transition-colors disabled:opacity-40 cursor-pointer"
                            >
                                {saving ? (
                                    <span className="material-symbols-outlined animate-spin" style={{ fontSize: 16 }}>refresh</span>
                                ) : (
                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>check</span>
                                )}
                                {editingId ? "Update Provider" : "Connect Provider"}
                            </button>
                        </div>
                    </div>
                )}

                {/* Footer badges */}
                <div className="flex items-center justify-center gap-6 text-[11px] text-tertiary pt-2 pb-1">
                    <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined" style={{ fontSize: 12 }}>shield</span>
                        Encrypted Storage
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined" style={{ fontSize: 12 }}>dns</span>
                        Server-Side Execution
                    </span>
                    <span className="flex items-center gap-1">
                        <span className="material-symbols-outlined" style={{ fontSize: 12 }}>check</span>
                        Zero-Logging Policy
                    </span>
                </div>
            </div>
        </>
    );

    if (inline) {
        return <div className="w-full">{innerContent}</div>;
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
            <div
                className="w-full max-w-[820px] max-h-[90vh] bg-surface border border-outline-variant rounded-[var(--radius-module)] shadow-2xl flex flex-col overflow-hidden steel-gradient ghost-border"
                style={{ animation: "fadeInScale 0.2s ease" }}
            >
                {innerContent}
            </div>

            {/* Keyframe animation */}
            <style>{`
                @keyframes fadeInScale {
                    from { opacity: 0; transform: scale(0.96); }
                    to { opacity: 1; transform: scale(1); }
                }
            `}</style>
        </div>
    );
}
