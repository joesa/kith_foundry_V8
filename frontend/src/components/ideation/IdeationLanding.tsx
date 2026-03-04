import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Lightbulb, Search, ArrowRight, Sparkles } from "lucide-react";

export default function IdeationLanding() {
    const navigate = useNavigate();

    return (
        <div className="max-w-4xl mx-auto px-6 py-16">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-16"
            >
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-500/10 mb-6">
                    <Sparkles className="w-8 h-8 text-purple-400" />
                </div>
                <h1 className="text-4xl font-bold text-white mb-3">
                    What would you like to build?
                </h1>
                <p className="text-lg text-zinc-400 max-w-xl mx-auto">
                    Whether you have a clear vision or need inspiration, we'll help you shape it into a validated, buildable product.
                </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-3xl mx-auto">
                {/* Path 1: I have an idea */}
                <motion.button
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                    onClick={() => navigate("/ideation/prompt")}
                    className="group relative bg-[#12121A] border border-zinc-800/50 rounded-2xl p-8 text-left hover:border-purple-500/30 hover:bg-[#14141E] transition-all"
                >
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative">
                        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/10 flex items-center justify-center mb-5">
                            <Lightbulb className="w-7 h-7 text-amber-400" />
                        </div>
                        <h2 className="text-xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
                            I Have an Idea
                        </h2>
                        <p className="text-zinc-400 text-sm mb-6 leading-relaxed">
                            Share your vision and our AI will enhance it into 3 unique variations — each a potential standalone product.
                        </p>
                        <div className="flex items-center gap-2 text-purple-400 text-sm font-medium group-hover:gap-3 transition-all">
                            <span>Describe your idea</span>
                            <ArrowRight className="w-4 h-4" />
                        </div>
                    </div>
                </motion.button>

                {/* Path 2: Help me discover */}
                <motion.button
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.2 }}
                    onClick={() => navigate("/ideation/discover")}
                    className="group relative bg-[#12121A] border border-zinc-800/50 rounded-2xl p-8 text-left hover:border-purple-500/30 hover:bg-[#14141E] transition-all"
                >
                    <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative">
                        <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500/20 to-indigo-500/20 border border-purple-500/10 flex items-center justify-center mb-5">
                            <Search className="w-7 h-7 text-purple-400" />
                        </div>
                        <h2 className="text-xl font-bold text-white mb-2 group-hover:text-purple-300 transition-colors">
                            Help Me Discover
                        </h2>
                        <p className="text-zinc-400 text-sm mb-6 leading-relaxed">
                            We'll generate a globally unique idea just for you, or guide you through questions to find your perfect match.
                        </p>
                        <div className="flex items-center gap-2 text-purple-400 text-sm font-medium group-hover:gap-3 transition-all">
                            <span>Discover your idea</span>
                            <ArrowRight className="w-4 h-4" />
                        </div>
                    </div>
                </motion.button>
            </div>
        </div>
    );
}
