import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";




export default function HomePage() {
  const [prompt, setPrompt] = useState("");
  const navigate = useNavigate();

  const handleLaunch = () => {
    if (prompt.trim()) {
      // You could pass this state to /ideation/prompt or wherever it needs to go
      navigate("/app/ideation", { state: { initialPrompt: prompt } });
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500 max-w-5xl mx-auto font-sans">
      
      {/* Top Banner (GIT / VERCEL theme) */}
      <div className="relative rounded-2xl bg-[#1A1C23] border border-white/5 overflow-hidden flex flex-col md:flex-row shadow-2xl">
         {/* Background Map - simple gradient placeholder */}
         <div className="absolute inset-0 bg-gradient-to-r from-[#1A1C23] via-[#1A1C23] to-[#252836] opacity-50 z-0"></div>
         <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-[url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop')] bg-cover bg-center opacity-10 mix-blend-screen z-0 mask-image:linear-gradient(to_left,black,transparent)"></div>

         <div className="relative z-10 p-8 md:p-12 flex-1 flex flex-col justify-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 w-fit mb-6">
               <div className="w-2 h-2 rounded-full bg-[#5E81AC] animate-pulse"></div>
               <span className="text-[10px] font-bold text-[#A3B8CC] tracking-widest uppercase">System Active</span>
            </div>

            <h1 className="text-4xl md:text-6xl font-black text-white tracking-tight mb-4 uppercase">
               SHIP YOUR NEXT BIG IDEA EFFORTLESSLY
            </h1>

            <p className="text-[#8890A4] text-lg max-w-2xl mb-10 leading-relaxed">
               Agent mesh is executing Ship to production path for Build me a sleek todo app — an intelligent platf.
            </p>

            <div className="flex flex-wrap items-center gap-4">
               <button className="px-6 py-2.5 rounded-full bg-[#E5B5A4] text-[#1D1B1A] font-bold text-xs tracking-widest uppercase hover:bg-white transition-colors">
                  Daily Idea
               </button>
               <button className="px-6 py-2.5 rounded-full bg-[#15161C] border border-white/10 text-white font-bold text-xs tracking-widest uppercase hover:bg-white/5 transition-colors">
                  Questionnaire
               </button>
               <button className="px-6 py-2.5 rounded-full bg-[#15161C] border border-white/10 text-white font-bold text-xs tracking-widest uppercase hover:bg-white/5 transition-colors">
                  Saved Archive
               </button>
            </div>
         </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         {/* Command Interface */}
         <div className="lg:col-span-2 rounded-2xl bg-[#13141A] border border-white/5 p-6 shadow-xl flex flex-col">
            <div className="mb-4 flex items-center gap-2">
               <div className="w-1.5 h-1.5 rounded-full bg-[#E5B5A4]"></div>
               <span className="text-[10px] font-bold text-[#8890A4] tracking-widest uppercase">Command Interface</span>
            </div>
            
            <h2 className="text-2xl font-black text-white tracking-tight uppercase mb-2">Initiate Protocol</h2>
            <p className="text-sm text-[#8890A4] mb-6">Transmit your requirements to the executive cluster for immediate architectural synthesis.</p>

            <div className="flex-1 bg-[#0E0F14] rounded-xl border border-white/5 p-1 flex flex-col mb-4 focus-within:border-white/20 transition-colors">
               <textarea 
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="e.g. 'Deploy a high-availability microservice architecture for financial ledger reconciliation...'"
                  className="w-full bg-transparent text-white placeholder:text-[#4B5060] p-4 text-sm resize-none focus:outline-none min-h-[120px]"
               />
            </div>

            <div className="flex items-center justify-between mt-auto">
               <div className="flex items-center gap-3">
                  <button className="px-5 py-2 rounded-full bg-[#E5B5A4] text-[#1D1B1A] font-bold text-xs tracking-widest uppercase hover:bg-white transition-colors">
                     Direct
                  </button>
                  <button className="px-4 py-2 rounded-full flex items-center gap-2 text-white font-bold text-xs tracking-widest uppercase hover:bg-white/5 transition-colors">
                     <span className="text-lg">✨</span> Enhance
                  </button>
               </div>
               <button onClick={handleLaunch} className="px-6 py-2.5 rounded-full bg-white text-black font-black text-xs tracking-widest uppercase hover:bg-gray-200 transition-colors flex items-center gap-2">
                  Execute Launch <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
               </button>
            </div>
         </div>

         {/* Telemetry Block */}
         <div className="rounded-2xl bg-[#13141A] border border-white/5 p-6 shadow-xl flex flex-col items-center justify-center min-h-[300px]">
            <div className="w-8 h-8 rounded-full border-2 border-white/10 border-t-[#8890A4] animate-spin mb-4"></div>
            <span className="text-[10px] font-black text-[#8890A4] tracking-widest uppercase">Awaiting Telemetry</span>
         </div>
      </div>

      <div className="pt-4">
         <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6">
            <div>
               <div className="flex items-center gap-2 mb-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#5E81AC]"></div>
                  <span className="text-[10px] font-bold text-[#8890A4] tracking-widest uppercase">Mission Control</span>
               </div>
               <h2 className="text-2xl font-black text-white tracking-tight uppercase">Active Projects</h2>
            </div>
            
            <Link to="/app/projects" className="px-4 py-2 rounded border border-white/10 text-white font-bold text-xs tracking-widest uppercase hover:bg-white/5 transition-colors flex items-center gap-2 mt-4 sm:mt-0">
               All Projects <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </Link>
         </div>

         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Link to="/app/projects" className="block group">
               <div className="rounded-xl bg-[#13141A] border border-white/5 p-5 hover:border-white/20 transition-all shadow-lg hover:shadow-2xl hover:-translate-y-1">
                  <div className="flex items-start justify-between mb-4">
                     <h3 className="text-white font-bold max-w-[80%] leading-tight text-sm">
                        Build me a sleek todo app — an intell...
                     </h3>
                     <div className="px-2 py-0.5 rounded border border-[#2B8B5B]/30 bg-[#2B8B5B]/10 text-[#4CAF50] text-[9px] font-black uppercase tracking-widest flex items-center gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#4CAF50] animate-pulse"></div>
                        Live
                     </div>
                  </div>
                  
                  <div className="mb-4">
                     <div className="flex justify-between text-[10px] font-bold uppercase tracking-widest text-[#8890A4] mb-1.5">
                        <span>Pipeline</span>
                        <span className="text-white">100%</span>
                     </div>
                     <div className="h-1 w-full bg-white/10 rounded-full overflow-hidden">
                        <div className="h-full bg-[#4CAF50] w-full"></div>
                     </div>
                  </div>

                  <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/5 text-[#8890A4]">
                     <span className="text-[10px] font-bold tracking-wider">Mar 26, 10:01 PM</span>
                     <div className="flex items-center gap-2">
                        <button className="p-1.5 rounded hover:bg-white/10 transition-colors text-white/50 hover:text-white">
                           <span className="material-symbols-outlined text-[16px]">delete</span>
                        </button>
                        <button className="p-1.5 rounded hover:bg-white/10 transition-colors text-white">
                           <span className="material-symbols-outlined text-[16px]">arrow_forward</span>
                        </button>
                     </div>
                  </div>
               </div>
            </Link>
         </div>
      </div>
    </div>
  );
}
