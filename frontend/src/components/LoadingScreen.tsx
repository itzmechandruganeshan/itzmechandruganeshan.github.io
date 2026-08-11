"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

export const LoadingScreen = ({ onComplete }: { onComplete: () => void }) => {
    const [progress, setProgress] = useState(0);
    const [status, setStatus] = useState("Initializing kernel...");

    useEffect(() => {
        let currentProgress = 0;
        
        const statuses = [
            "Initializing kernel...",
            "Loading neural pathways...",
            "Establishing LLM connection...",
            "Optimizing context vectors...",
            "Ready."
        ];

        const interval = setInterval(() => {
            currentProgress += Math.floor(Math.random() * 15) + 5;
            if (currentProgress >= 100) {
                currentProgress = 100;
                setProgress(100);
                setStatus("Ready.");
                clearInterval(interval);
                setTimeout(onComplete, 400); // Quick fade out after completion
            } else {
                setProgress(currentProgress);
                const statusIndex = Math.floor((currentProgress / 100) * (statuses.length - 1));
                setStatus(statuses[statusIndex]);
            }
        }, 40); // Fast updates (takes ~600-800ms total)

        return () => clearInterval(interval);
    }, [onComplete]);

    return (
        <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="fixed inset-0 z-[100] bg-[#050505] flex flex-col items-center justify-center font-mono"
        >
            <div className="w-72 max-w-[80vw]">
                <div className="flex justify-between text-[10px] text-gray-500 mb-2 uppercase tracking-widest">
                    <span>CG.AI_BOOT</span>
                    <span>{progress}%</span>
                </div>
                
                {/* Minimalist Progress Bar */}
                <div className="h-[2px] w-full bg-white/10 rounded-full overflow-hidden mb-4 relative">
                    <motion.div 
                        className="absolute top-0 left-0 h-full bg-white rounded-full shadow-[0_0_10px_rgba(255,255,255,0.5)]"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.1 }}
                    />
                </div>
                
                {/* Status text */}
                <div className="text-gray-400 text-xs flex items-center gap-2">
                    <span className="text-white">&gt;</span>
                    {status}
                    {progress < 100 && (
                        <motion.span
                            animate={{ opacity: [0, 1, 0] }}
                            transition={{ repeat: Infinity, duration: 0.5 }}
                            className="inline-block w-1.5 h-3 bg-white align-middle"
                        />
                    )}
                </div>
            </div>
        </motion.div>
    );
};
