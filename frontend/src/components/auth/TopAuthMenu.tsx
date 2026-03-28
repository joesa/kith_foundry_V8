import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

export function TopAuthMenu() {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();

  const email = user?.email || '';
  const displayName = (user as any)?.displayName || '';
  const label = displayName || email || 'Account';

  return (
    <div className="flex items-center gap-3">
      <span
        className="hidden sm:inline max-w-[140px] truncate text-[10px] font-bold uppercase tracking-widest text-slate-400"
        title={email || undefined}
      >
        {label}
      </span>
      <button
        type="button"
        onClick={async () => {
          await signOut();
          navigate('/login', { replace: true });
        }}
        className="rounded-full border border-slate-600 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-300 hover:border-orange-500/60 hover:text-orange-200 transition-colors"
      >
        Log out
      </button>
    </div>
  );
}
