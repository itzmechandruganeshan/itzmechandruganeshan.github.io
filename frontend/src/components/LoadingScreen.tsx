"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const terminalLines = [
    "Initializing Neural Networks...",
    "Loading Knowledge Base...",
    "Optimizing Agentic Workflows...",
    "Welcome.",
];

export const LoadingScreen = ({ onComplete }: { onComplete: () => void }) => {
    const [currentLineIndex, setCurrentLineIndex] = useState(0);
    const [currentText, setCurrentText] = useState("");
    const [isTyping, setIsTyping] = useState(true);

    useEffect(() => {
        if (currentLineIndex >= terminalLines.length) {
            setTimeout(onComplete, 800); // Wait a bit after "Welcome." before fading out
            return;
        }

        const targetText = terminalLines[currentLineIndex];

        if (isTyping) {
            if (currentText.length < targetText.length) {
                const timeout = setTimeout(() => {
                    setCurrentText(targetText.slice(0, currentText.length + 1));
                }, 30 + Math.random() * 30); // Random typing speed
                return () => clearTimeout(timeout);
            } else {
                setIsTyping(false);
                setTimeout(() => {
                    setCurrentLineIndex((prev) => prev + 1);
                    setCurrentText("");
                    setIsTyping(true);
                }, 500); // Initial pause after completion
            }
        }
    }, [currentText, currentLineIndex, isTyping, onComplete]);

    return (
        <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8 }}
            className="fixed inset-0 z-[100] bg-black flex items-center justify-center font-mono"
        >
            <div className="text-blue-500 text-xl md:text-2xl font-bold">
                <span>&gt; </span>
                {currentText}
                <motion.span
                    animate={{ opacity: [0, 1, 0] }}
                    transition={{ repeat: Infinity, duration: 0.8 }}
                    className="inline-block w-3 h-5 bg-blue-500 ml-1 align-middle"
                />
            </div>
        </motion.div>
    );
};
