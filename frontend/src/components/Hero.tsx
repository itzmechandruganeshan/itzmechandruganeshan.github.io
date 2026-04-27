"use client";

import React, { useEffect, useRef } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import { ArrowRight, Brain, Cpu, Network, Search, Command } from "lucide-react";
import { resumeData } from "@/data/resume";
import { parseBoldText } from "@/utils/textFormatting";
import { useChat } from "@/context/ChatContext";

export const Hero = () => {
    const { scrollY } = useScroll();
    const y = useTransform(scrollY, [0, 500], [0, 200]);
    const { openChat } = useChat();

    return (
        <section className="relative h-screen flex items-center justify-center overflow-hidden bg-transparent text-white">


            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/90 pointer-events-none z-10" />

            <motion.div
                style={{ y }}
                className="relative z-20 max-w-6xl mx-auto px-6 text-center"
            >


                <motion.h1
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="text-5xl md:text-7xl font-bold tracking-tight mb-6"
                >
                    Hey <span className="animate-wave inline-block">👋</span>, I'm <span className="text-gradient">Chandru Ganeshan</span>
                </motion.h1>

                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                    className="text-xl md:text-2xl text-gray-400 max-w-3xl mx-auto mb-10 leading-relaxed"
                >
                    {parseBoldText(resumeData.summary)}
                </motion.p>

                {/* AI Search Bar Trigger */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, delay: 0.5 }}
                    className="max-w-xl mx-auto mb-10"
                >
                    <button
                        onClick={openChat}
                        className="w-full flex items-center gap-3 px-6 py-4 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all group backdrop-blur-md"
                    >
                        <Search className="w-5 h-5 text-gray-400 group-hover:text-white transition-colors" />
                        <span className="text-gray-400 flex-1 text-left font-mono group-hover:text-white transition-colors">
                            Ask my AI about me...
                        </span>
                        <div className="flex items-center gap-1">
                            <kbd className="hidden sm:inline-flex items-center justify-center h-6 px-2 text-xs font-sans font-medium text-gray-400 bg-white/10 rounded">
                                <Command className="w-3 h-3 mr-1" /> K
                            </kbd>
                        </div>
                    </button>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.6 }}
                    className="flex flex-col sm:flex-row gap-4 justify-center items-center"
                >
                    <a
                        href="#projects"
                        className="group relative px-8 py-4 bg-blue-600 hover:bg-blue-700 rounded-full font-semibold transition-all hover:scale-105 flex items-center gap-2"
                    >
                        Explore My Work
                        <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        <div className="absolute inset-0 rounded-full ring-2 ring-white/20 group-hover:ring-white/40 transition-all" />
                    </a>
                    <a
                        href="#contact"
                        className="px-8 py-4 glass-panel hover:bg-white/10 rounded-full font-semibold transition-all hover:scale-105"
                    >
                        Contact Me
                    </a>
                </motion.div>

                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1, duration: 1 }}
                    className="mt-20 flex justify-center gap-8 text-gray-500"
                >
                    <div className="flex flex-col items-center gap-2">
                        <Brain className="w-6 h-6 text-blue-500" />
                        <span className="text-xs uppercase tracking-widest">Generative AI</span>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <Network className="w-6 h-6 text-purple-500" />
                        <span className="text-xs uppercase tracking-widest">Agentic Systems</span>
                    </div>
                    <div className="flex flex-col items-center gap-2">
                        <Cpu className="w-6 h-6 text-cyan-500" />
                        <span className="text-xs uppercase tracking-widest">ML Ops</span>
                    </div>
                </motion.div>
            </motion.div>
        </section>
    );
};
