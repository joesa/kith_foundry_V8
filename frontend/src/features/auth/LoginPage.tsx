import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { cn } from "../../lib/utils/cn";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error } = await signIn(email, password);
    setLoading(false);
    if (error) {
      setError(error);
    } else {
      navigate("/app/home");
    }
  };

  return (
    <div className="min-h-screen bg-[#0E0E12] flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-[420px]">
        <div className="bg-[#121216] border-t-2 border-[#E5B5A4] rounded-2xl p-10 shadow-2xl">
          <div className="mb-8">
            <h3 className="text-[10px] font-black tracking-[0.25em] text-[#8890A4] mb-3 uppercase">Secure Access</h3>
            <h1 className="text-white text-[28px] font-black tracking-tight uppercase mb-2">Authentication</h1>
            <p className="text-[#8890A4] text-sm font-medium">Supply operator credentials.</p>
          </div>

          <div className="flex bg-[#1A1C23] rounded-lg p-1 mb-8">
            <div className="flex-1">
               <button className="w-full py-3 rounded-md text-[11px] font-bold uppercase tracking-widest bg-[#E5B5A4] text-[#121216] shadow-sm">
                 Authenticate
               </button>
            </div>
            <div className="flex-1">
               <Link to="/signup" className="flex items-center justify-center w-full py-3 rounded-md text-[11px] font-bold uppercase tracking-widest text-[#8890A4] hover:text-white transition-colors">
                 Register
               </Link>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#8890A4] mb-2.5">
                Data Link (Email)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3.5 text-sm rounded-lg bg-[#EDEDF2] text-black font-semibold placeholder:text-[#8890A4] focus:outline-none focus:ring-2 focus:ring-[#E5B5A4] transition-all"
                placeholder="joesa73@gmail.com"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#8890A4] mb-2.5">
                Cipher (Password)
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3.5 text-sm rounded-lg bg-[#EDEDF2] text-black font-semibold placeholder:text-[#8890A4] focus:outline-none focus:ring-2 focus:ring-[#E5B5A4] transition-all"
                placeholder="••••••••"
                required
              />
            </div>

            {error && (
              <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium">
                {error}
              </div>
            )}

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className={cn(
                  "w-full py-4 rounded-lg font-black uppercase tracking-widest text-xs",
                  "bg-white text-[#121216]",
                  "hover:bg-gray-100 transition-colors flex items-center justify-center gap-3",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-[#121216]/30 border-t-[#121216] rounded-full animate-spin" />
                    Executing...
                  </span>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[18px]">login</span>
                    Execute Login
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-10 flex flex-col items-center gap-4">
            <Link to="/" className="inline-flex items-center text-[11px] text-[#8890A4] hover:text-white font-black tracking-[0.15em] uppercase transition-colors gap-2">
              <span className="material-symbols-outlined text-[16px]">arrow_back</span>
              Return to Gateway
            </Link>
            <button className="text-[9px] text-[#4B5060] hover:text-[#8890A4] font-black tracking-[0.2em] uppercase transition-colors">
              Clear Stale Session
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
