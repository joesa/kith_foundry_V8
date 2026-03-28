
interface TrustBannerProps {
  message?: string;
  variant?: 'default' | 'security';
}

export function TrustBanner({ message = 'AES-256-GCM Encrypted Channel', variant = 'default' }: TrustBannerProps) {
  return (
    <div className={`inline-flex items-center gap-2.5 px-4 py-2 rounded-full text-[10px] font-medium uppercase tracking-[0.2em] transition-all duration-300 ${
      variant === 'security'
        ? 'bg-primary/[0.06] border border-primary/15 text-primary/80 hover:border-primary/25'
        : 'bg-secondary/[0.06] border border-secondary/15 text-secondary/70 hover:border-secondary/25'
    }`}>
      <span className="material-symbols-outlined w-3.5 h-3.5" style={{ fontVariationSettings: "'FILL' 1, 'wght' 300" }}>shield</span>
      <span>{message}</span>
    </div>
  );
}
