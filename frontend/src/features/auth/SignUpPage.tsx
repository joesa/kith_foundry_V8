import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { cn } from "../../lib/utils/cn";

export default function SignUpPage() {
  const [callsign, setCallsign] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { signUp } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error } = await signUp(email, password);
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
        <div className="bg-[#121216] border-t-2 border-[#96C7E8] rounded-2xl p-10 shadow-2xl">
          <div className="mb-8">
            <h3 className="text-[10px] font-black tracking-[0.25em] text-[#8890A4] mb-3 uppercase">Secure Access</h3>
            <h1 className="text-white text-[28px] font-black tracking-tight uppercase mb-2">Initialization</h1>
            <p className="text-[#8890A4] text-sm font-medium">Register new operator credentials.</p>
          </div>

          <div className="flex bg-[#1A1C23] rounded-lg p-1 mb-8">
            <div className="flex-1">
               <Link to="/login" className="flex items-center justify-center w-full py-3 rounded-md text-[11px] font-bold uppercase tracking-widest text-[#8890A4] hover:text-white transition-colors">
                 Authenticate
               </Link>
            </div>
            <div className="flex-1">
               <button className="w-full py-3 rounded-md text-[11px] font-bold uppercase tracking-widest bg-[#96C7E8] text-[#121216] shadow-[0_0_15px_rgba(150,199,232,0.3)]">
                 Register
               </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#8890A4] mb-2.5">
                Callsign
              </label>
              <input
                type="text"
                value={callsign}
                onChange={(e) => setCallsign(e.target.value)}
                className="w-full px-4 py-3.5 text-sm rounded-lg bg-[#0E0E12] border border-white/5 text-white font-semibold placeholder:text-[#4B5060] focus:outline-none focus:border-[#96C7E8] focus:ring-1 focus:ring-[#96C7E8] transition-all focus:bg-[#121216]"
                placeholder="Ops Lead"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#8890A4] mb-2.5">
                Data Link (Email)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3.5 text-sm rounded-lg bg-[#EDEDF2] text-black font-semibold placeholder:text-[#8890A4] focus:outline-none focus:ring-2 focus:ring-[#96C7E8] transition-all"
                placeholder="joesa73@gmail.com"
                required
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
                className="w-full px-4 py-3.5 text-sm rounded-lg bg-[#EDEDF2] text-black font-semibold placeholder:text-[#8890A4] focus:outline-none focus:ring-2 focus:ring-[#96C7E8] transition-all"
                placeholder="••••••••"
                required
                minLength={6}
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
                  "bg-[#96C7E8] text-[#121216] shadow-[0_4px_20px_rgba(150,199,232,0.25)]",
                  "hover:brightness-110 transition-all flex items-center justify-center gap-3",
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
                    <span className="material-symbols-outlined text-[18px]">how_to_reg</span>
                    Execute Registration
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
