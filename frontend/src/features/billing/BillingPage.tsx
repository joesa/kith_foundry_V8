/**
 * Billing Management Page — view current subscription, usage, and manage
 * via Stripe Customer Portal.  Requires authentication.
 */
import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { useApiFetch } from "../../hooks/useApiFetch";
import { cn } from "../../lib/utils/cn";

interface SubscriptionData {
    tier: string;
    status: string;
    is_annual: boolean;
    seat_count: number;
    byok_discount_applied: boolean;
    current_period_end: string | null;
    limits: {
        projects: number | null;
        csuite_runs_mo: number | null;
        design_screens_mo: number | null;
        artifact_sets_mo: number | null;
    };
    usage: {
        billing_month: string;
        csuite_runs: number;
        design_screens: number;
        artifact_sets: number;
        project_count: number;
    };
    packs: Array<{
        pack_type: string;
        remaining: number;
        pack_size: number;
        purchased_at: string;
    }>;
}

const TIER_LABELS: Record<string, string> = {
    free: "Free",
    indie: "Indie",
    pro: "Pro",
    team: "Team",
    enterprise: "Enterprise",
};

function UsageBar({ value, max, label }: { value: number; max: number | null; label: string }) {
    const pct = max === null ? 0 : Math.min((value / max) * 100, 100);
    const fillColor = pct > 90 ? "bg-error" : pct > 70 ? "bg-warning" : "bg-secondary";

    return (
        <div className="mb-3">
            <div className="flex justify-between text-xs mb-1.5">
                <span className="text-on-surface/60 font-black uppercase tracking-widest text-[0.6rem]">{label}</span>
                <span className="font-mono text-on-surface/80">
                    {value}{max !== null ? ` / ${max}` : " / ∞"}
                </span>
            </div>
            {max !== null && (
                <div className="h-1.5 bg-surface-container rounded-full overflow-hidden">
                    <div
                        className={cn("h-full rounded-full transition-all duration-500", fillColor)}
                        style={{ width: `${pct}%` }}
                    />
                </div>
            )}
        </div>
    );
}

export default function BillingPage() {
    const apiFetch = useApiFetch();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();

    const [sub, setSub] = useState<SubscriptionData | null>(null);
    const [loading, setLoading] = useState(true);
    const [portalLoading, setPortalLoading] = useState(false);
    const [packLoading, setPackLoading] = useState<string | null>(null);

    const checkoutStatus = searchParams.get("checkout");
    const packStatus = searchParams.get("pack");

    const fetchSub = useCallback(async () => {
        try {
            const resp = await apiFetch("/api/v1/billing/subscription");
            if (resp.ok) {
                const data = await resp.json();
                setSub(data);
            }
        } catch {}
        finally { setLoading(false); }
    }, [apiFetch]);

    useEffect(() => { fetchSub(); }, [fetchSub]);

    const openPortal = async () => {
        setPortalLoading(true);
        try {
            const resp = await apiFetch("/api/v1/billing/portal", { method: "POST" });
            if (resp.ok) {
                const data = await resp.json();
                window.open(data.portal_url, "_blank");
            } else {
                const err = await resp.json();
                alert(err.detail || "Could not open billing portal.");
            }
        } catch (e) {
            alert("Failed to open billing portal.");
        } finally {
            setPortalLoading(false);
        }
    };

    const purchasePack = async (pack_type: string) => {
        setPackLoading(pack_type);
        try {
            const resp = await apiFetch("/api/v1/billing/pack/checkout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pack_type }),
            });
            if (resp.ok) {
                const data = await resp.json();
                window.location.href = data.checkout_url;
            } else {
                const err = await resp.json();
                alert(err.detail || "Could not start pack checkout.");
            }
        } catch {
            alert("Failed to start pack checkout.");
        } finally {
            setPackLoading(null);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-secondary border-t-transparent rounded-full animate-spin" />
            </div>
        );
    }

    const tier = sub?.tier ?? "free";
    const isPaid = tier !== "free";

    return (
        <div className="min-h-screen bg-background text-on-surface px-4 py-8">
            <div className="max-w-4xl mx-auto">

                {/* Status banners */}
                {checkoutStatus === "success" && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-6 flex items-center gap-2 bg-success/10 border border-success/30 rounded-[var(--radius-module)] px-4 py-3 text-success"
                    >
                        <span className="material-symbols-outlined text-base flex-shrink-0">check_circle</span>
                        <span className="text-sm font-black uppercase tracking-widest">Subscription activated! Your plan has been upgraded.</span>
                    </motion.div>
                )}
                {checkoutStatus === "cancelled" && (
                    <div className="mb-6 flex items-center gap-2 bg-warning/10 border border-warning/30 rounded-[var(--radius-module)] px-4 py-3 text-warning">
                        <span className="material-symbols-outlined text-base flex-shrink-0">warning</span>
                        <span className="text-sm font-black uppercase tracking-widest">Checkout cancelled. Your plan was not changed.</span>
                    </div>
                )}
                {packStatus === "success" && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mb-6 flex items-center gap-2 bg-primary-container/40 border border-primary-container/60 rounded-[var(--radius-module)] px-4 py-3 text-on-primary-container"
                    >
                        <span className="material-symbols-outlined text-base flex-shrink-0">check_circle</span>
                        <span className="text-sm font-black uppercase tracking-widest">Pack purchased! Your extra usage has been added.</span>
                    </motion.div>
                )}

                <div className="flex items-center justify-between mb-8">
                    <h1 className="text-3xl font-black uppercase" style={{ letterSpacing: "-0.05em" }}>
                        Billing &amp; Usage
                    </h1>
                    {isPaid && (
                        <button
                            onClick={openPortal}
                            disabled={portalLoading}
                            className="flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container border border-outline-variant/20 hover:border-outline-variant/50 text-xs font-black uppercase tracking-widest transition-all disabled:opacity-50"
                        >
                            <span className="material-symbols-outlined text-base">credit_card</span>
                            {portalLoading ? "Opening…" : "Manage Subscription"}
                            <span className="material-symbols-outlined text-sm">open_in_new</span>
                        </button>
                    )}
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
                    {/* Current Plan */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 lg:col-span-1"
                    >
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 rounded-full bg-primary-container flex items-center justify-center">
                                <span className="material-symbols-outlined text-on-primary-container text-lg">bolt</span>
                            </div>
                            <div>
                                <p className="text-[0.6rem] font-black uppercase tracking-widest text-tertiary">Current Plan</p>
                                <p className="font-black text-lg uppercase" style={{ letterSpacing: "-0.05em" }}>{TIER_LABELS[tier] ?? tier}</p>
                            </div>
                        </div>

                        <div className="space-y-2 text-sm mb-4">
                            <div className="flex justify-between">
                                <span className="text-on-surface/50 font-black uppercase tracking-widest text-[0.6rem]">Status</span>
                                <span className={cn(
                                    "font-black uppercase tracking-widest text-[0.6rem]",
                                    sub?.status === "active" || sub?.status === "trialing" ? "text-success" : "text-error"
                                )}>
                                    {sub?.status ?? "active"}
                                </span>
                            </div>
                            {sub?.is_annual && (
                                <div className="flex justify-between">
                                    <span className="text-on-surface/50 font-black uppercase tracking-widest text-[0.6rem]">Billing</span>
                                    <span className="text-success font-black uppercase tracking-widest text-[0.6rem]">Annual (20% off)</span>
                                </div>
                            )}
                            {sub?.byok_discount_applied && (
                                <div className="flex justify-between">
                                    <span className="text-on-surface/50 font-black uppercase tracking-widest text-[0.6rem]">BYOK Discount</span>
                                    <span className="text-success font-black uppercase tracking-widest text-[0.6rem]">Applied (20% off)</span>
                                </div>
                            )}
                            {sub?.seat_count && sub.seat_count > 1 && (
                                <div className="flex justify-between">
                                    <span className="text-on-surface/50 font-black uppercase tracking-widest text-[0.6rem]">Seats</span>
                                    <span className="font-black text-[0.6rem] tracking-widest">{sub.seat_count}</span>
                                </div>
                            )}
                            {sub?.current_period_end && (
                                <div className="flex items-center gap-1 text-on-surface/40">
                                    <span className="material-symbols-outlined text-xs">schedule</span>
                                    <span className="text-[0.6rem] font-black uppercase tracking-widest">
                                        Renews {new Date(sub.current_period_end).toLocaleDateString()}
                                    </span>
                                </div>
                            )}
                        </div>

                        {!isPaid && (
                            <button
                                onClick={() => navigate("/pricing")}
                                className="w-full py-2 rounded-full bg-secondary text-on-surface font-black uppercase tracking-widest text-xs flex items-center justify-center gap-1.5 transition-all hover:opacity-90"
                            >
                                Upgrade Plan
                                <span className="material-symbols-outlined text-sm">arrow_outward</span>
                            </button>
                        )}
                    </motion.div>

                    {/* Usage */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.05 }}
                        className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 lg:col-span-2"
                    >
                        <div className="flex items-center gap-2 mb-5">
                            <span className="material-symbols-outlined text-secondary text-lg">bar_chart</span>
                            <h2 className="font-black uppercase tracking-widest text-xs text-on-surface/80">
                                Usage — {sub?.usage.billing_month}
                            </h2>
                        </div>
                        <UsageBar
                            label="C-Suite Analyses"
                            value={sub?.usage.csuite_runs ?? 0}
                            max={sub?.limits.csuite_runs_mo ?? null}
                        />
                        <UsageBar
                            label="Design Screens"
                            value={sub?.usage.design_screens ?? 0}
                            max={sub?.limits.design_screens_mo ?? null}
                        />
                        <UsageBar
                            label="Artifact Sets"
                            value={sub?.usage.artifact_sets ?? 0}
                            max={sub?.limits.artifact_sets_mo ?? null}
                        />
                        <UsageBar
                            label="Projects"
                            value={sub?.usage.project_count ?? 0}
                            max={sub?.limits.projects ?? null}
                        />
                        <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/30 mt-3">
                            Reset on the 1st of each month.
                        </p>
                    </motion.div>
                </div>

                {/* Active Packs */}
                {(sub?.packs ?? []).length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 mb-8"
                    >
                        <div className="flex items-center gap-2 mb-4">
                            <span className="material-symbols-outlined text-secondary text-lg">inventory_2</span>
                            <h2 className="font-black uppercase tracking-widest text-xs text-on-surface/80">Active Usage Packs</h2>
                        </div>
                        <div className="space-y-2">
                            {sub!.packs.map((p, i) => (
                                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-surface-container border border-outline-variant/20">
                                    <div>
                                        <p className="text-xs font-black uppercase tracking-widest text-on-surface">
                                            {p.pack_type === "csuite_runs" ? "C-Suite Runs" : "Design Screens"} Pack
                                        </p>
                                        <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40 mt-0.5">
                                            Purchased {new Date(p.purchased_at).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-black text-on-surface">{p.remaining}</p>
                                        <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40">remaining</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Buy Add-on Packs */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.15 }}
                    className="steel-gradient ghost-border rounded-[var(--radius-module)] p-6 mb-8"
                >
                    <div className="flex items-center gap-2 mb-4">
                        <span className="material-symbols-outlined text-secondary text-lg">add_box</span>
                        <h2 className="font-black uppercase tracking-widest text-xs text-on-surface/80">Buy Usage Packs</h2>
                        <span className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/30 ml-auto">One-time purchase, no expiry</span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {[
                            { type: "csuite_runs", label: "C-Suite Runs", desc: "+25 C-Suite analyses", price: "$9" },
                            { type: "design_screens", label: "Design Screens", desc: "+50 design screens", price: "$9" },
                        ].map(pack => (
                            <div
                                key={pack.type}
                                className="flex items-center justify-between rounded-lg p-4 bg-surface-container border border-outline-variant/20 hover:border-outline-variant/50 transition-all"
                            >
                                <div>
                                    <p className="text-xs font-black uppercase tracking-widest text-on-surface">{pack.label} Pack</p>
                                    <p className="text-[0.6rem] font-black uppercase tracking-widest text-on-surface/40 mt-0.5">{pack.desc} · {pack.price}</p>
                                </div>
                                <button
                                    onClick={() => purchasePack(pack.type)}
                                    disabled={packLoading === pack.type}
                                    className="px-4 py-2 bg-secondary text-on-surface rounded-full font-black uppercase tracking-widest text-xs transition-all hover:opacity-90 disabled:opacity-50"
                                >
                                    {packLoading === pack.type ? "…" : "Buy"}
                                </button>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* Upgrade CTA for free/indie */}
                {(tier === "free" || tier === "indie") && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        className="rounded-[var(--radius-module)] border border-primary-container bg-primary-container/10 ember-glow p-6 text-center"
                    >
                        <h3 className="text-xl font-black uppercase mb-2" style={{ letterSpacing: "-0.05em" }}>
                            {tier === "free" ? "Unlock unlimited building" : "Go unlimited with Pro"}
                        </h3>
                        <p className="text-on-surface/50 mb-4 text-sm font-black uppercase tracking-widest">
                            {tier === "free"
                                ? "Upgrade to Indie or Pro and stop hitting limits mid-build."
                                : "Pro gives you unlimited projects, 100 C-Suite runs/mo, and 150 design screens/mo."
                            }
                        </p>
                        <button
                            onClick={() => navigate("/pricing")}
                            className="px-6 py-2.5 bg-secondary text-on-surface rounded-full font-black uppercase tracking-widest text-xs transition-all hover:opacity-90"
                        >
                            View Plans
                        </button>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
