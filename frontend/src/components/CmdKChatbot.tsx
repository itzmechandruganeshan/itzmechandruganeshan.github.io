"use client";

import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Command, Search, X, Sparkles, Terminal, Cpu, Briefcase, FileText } from "lucide-react";
import { useChat } from "@/context/ChatContext";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from "react-markdown";

export function CmdKChatbot() {
    const { isOpen, closeChat, toggleChat } = useChat();
    const [query, setQuery] = useState("");
    const [messages, setMessages] = useState<{ role: "user" | "ai"; content: string }[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const [sessionId, setSessionId] = useState<string>("");

    const inputRef = useRef<HTMLInputElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);

    // Initialize Session ID with IP Address
    useEffect(() => {
        const fetchIp = async () => {
            try {
                // Fetch public IP address
                const response = await fetch("https://api.ipify.org?format=json");
                const data = await response.json();
                setSessionId(data.ip);
                // Optionally still store it so we don't fetch if not needed, but fetching is fast
                localStorage.setItem("chat_session_id", data.ip);
            } catch (error) {
                console.error("Failed to fetch IP, falling back to local storage or UUID", error);
                // Fallback in case the IP fetch fails (e.g. adblocker)
                let storedSessionId = localStorage.getItem("chat_session_id");
                if (!storedSessionId) {
                    storedSessionId = uuidv4();
                    localStorage.setItem("chat_session_id", storedSessionId);
                }
                setSessionId(storedSessionId);
            }
        };

        fetchIp();
    }, []);

    // WebSocket Connection
    useEffect(() => {
        if (!sessionId) return;

        const wsUrl = `ws://localhost:8000/ws/chat?session_id=${sessionId}`;
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log("WebSocket connected");
        };

        ws.onmessage = async (e) => {
            try {
                let data;
                let isJson = false;

                // Check if the message looks like JSON
                if (typeof e.data === "string" && e.data.trim().startsWith("{")) {
                    try {
                        data = JSON.parse(e.data);
                        isJson = true;
                    } catch (err) {
                        isJson = false;
                    }
                }

                const processTextChunks = async (text: string) => {
                    const textChunks = text
                        .split("|split|")
                        .map((s: string) => s.trim())
                        .filter(Boolean);

                    for (let i = 0; i < textChunks.length; i++) {
                        const chunkText = textChunks[i];

                        if (i === 0) {
                            // Immediately render the first bubble
                            setMessages((prev) => [...prev, { role: "ai", content: chunkText }]);
                        } else {
                            // Artificial delay and typing simulation for subsequent burst bubbles
                            setIsTyping(true);
                            const delay = Math.min(2500, chunkText.length * 40);
                            await new Promise((resolve) => setTimeout(resolve, delay));
                            setIsTyping(false);

                            setMessages((prev) => [...prev, { role: "ai", content: chunkText }]);
                        }
                    }
                };

                if (isJson) {
                    if (data.type === "status") {
                        if (data.action === "typing") setIsTyping(true);
                        if (data.action === "idle") setIsTyping(false);
                    } else if (data.type === "turn_complete") {
                        setIsTyping(false);
                    } else if (data.type === "message" && data.text) {
                        await processTextChunks(data.text);
                    }
                } else if (typeof e.data === "string") {
                    // Handle plain text message
                    await processTextChunks(e.data);
                }
            } catch (err) {
                console.error("Error handling WebSocket message:", err);
            }
        };

        ws.onclose = () => {
            console.log("WebSocket disconnected");
        };

        return () => {
            if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
                ws.close();
            }
        };
    }, [sessionId]);

    // Auto-scroll logic
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, isTyping]);

    // Toggle on Cmd+K or Ctrl+K
    useEffect(() => {
        const down = (e: KeyboardEvent) => {
            if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                toggleChat();
            }
        };

        document.addEventListener("keydown", down);
        return () => document.removeEventListener("keydown", down);
    }, [toggleChat]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen) {
            inputRef.current?.focus();
        }
    }, [isOpen]);

    // Close on Escape
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape") {
                closeChat();
            }
        };
        if (isOpen) {
            document.addEventListener("keydown", handleEscape);
        }
        return () => document.removeEventListener("keydown", handleEscape);
    }, [isOpen, closeChat]);

    const handleSendMessage = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!query.trim() || isTyping || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

        const userMessage = query.trim();
        setQuery("");
        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);

        wsRef.current.send(userMessage);
    };

    const handleSuggestionClick = (suggestion: string) => {
        setQuery(suggestion);
        // We could auto-send here, but letting them read it and hit enter is safer
        inputRef.current?.focus();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={closeChat}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center pt-[15vh] px-4"
                    >
                        {/* Modal */}
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: -20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -20 }}
                            transition={{ duration: 0.15, ease: "easeOut" }}
                            onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside
                            className="bg-[#0f1115] border border-white/10 shadow-2xl rounded-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[70vh]"
                        >
                            {/* Search Bar / Input Area */}
                            <form onSubmit={handleSendMessage} className="relative border-b border-white/10">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    ref={inputRef}
                                    type="text"
                                    placeholder={isTyping ? "Chandru is typing..." : "Ask me anything..."}
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    disabled={isTyping}
                                    className="w-full bg-transparent text-white placeholder-gray-500 py-4 pl-12 pr-12 outline-none text-lg disabled:opacity-50"
                                />
                                <button
                                    type="button"
                                    onClick={closeChat}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 p-1 bg-white/5 hover:bg-white/10 rounded-md text-gray-400 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </form>

                            {/* Content Area */}
                            <div className="overflow-y-auto p-4 flex-1 custom-scrollbar">
                                {messages.length === 0 ? (
                                    // Empty state / Suggestions
                                    <div className="py-10 px-4 md:px-8 max-w-3xl mx-auto w-full">
                                        <div className="mb-6 flex flex-col items-center md:items-start text-center md:text-left">
                                            <div className="inline-flex items-center justify-center p-2.5 bg-blue-500/10 rounded-xl mb-4 border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.15)]">
                                                <Sparkles className="w-5 h-5 text-blue-400" />
                                            </div>
                                            <h3 className="text-xl font-semibold text-white mb-1.5">Welcome to CG.AI Engine</h3>
                                            <p className="text-gray-400 text-sm max-w-md">
                                                Ask me any technical questions about my work, architecture decisions, or machine learning experience.
                                            </p>
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                                            {[
                                                {
                                                    icon: <Terminal className="w-4 h-4 text-emerald-400 mb-3" />,
                                                    title: "Agentic Systems",
                                                    query: "How do you architect multi-agent workflows?",
                                                },
                                                {
                                                    icon: <Cpu className="w-4 h-4 text-cyan-400 mb-3" />,
                                                    title: "RAG & Vector Search",
                                                    query: "Explain your production RAG pipelines.",
                                                },
                                                {
                                                    icon: <Briefcase className="w-4 h-4 text-purple-400 mb-3" />,
                                                    title: "Project Impact",
                                                    query: "What was your role in the Tpay AI chatbot?",
                                                },
                                                {
                                                    icon: <FileText className="w-4 h-4 text-amber-400 mb-3" />,
                                                    title: "Context & Profile",
                                                    query: "Give me a summary of your resume.",
                                                },
                                            ].map((suggestion, i) => (
                                                <button
                                                    key={i}
                                                    onClick={() => handleSuggestionClick(suggestion.query)}
                                                    className="group flex flex-col text-left p-4 rounded-xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 hover:border-white/10 transition-all hover:-translate-y-0.5"
                                                >
                                                    <div className="flex justify-between items-start w-full">
                                                        {suggestion.icon}
                                                        <Search className="w-3.5 h-3.5 text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                                                    </div>
                                                    <span className="text-gray-200 font-medium text-sm mb-1.5">{suggestion.title}</span>
                                                    <span className="text-gray-500 text-xs leading-relaxed group-hover:text-gray-400 transition-colors">
                                                        "{suggestion.query}"
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    // Chat History
                                    <div className="space-y-4">
                                        {messages.map((msg, idx) => (
                                            <div
                                                key={idx}
                                                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                                            >
                                                <div
                                                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${msg.role === "user"
                                                        ? "bg-blue-600 text-white"
                                                        : "bg-white/10 text-gray-200 border border-white/5"
                                                        }`}
                                                >
                                                    {msg.role === "ai" ? (
                                                        <div className="prose prose-invert max-w-none prose-p:my-1 prose-pre:my-2 prose-pre:bg-black/50 prose-pre:p-2 prose-pre:rounded-lg text-sm">
                                                            <ReactMarkdown>
                                                                {msg.content}
                                                            </ReactMarkdown>
                                                        </div>
                                                    ) : (
                                                        <span className="text-sm whitespace-pre-wrap">{msg.content}</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                        {isTyping && (
                                            <div className="flex justify-start">
                                                <div className="bg-white/5 border border-white/5 rounded-2xl px-4 py-3 text-gray-400 flex items-center gap-2">
                                                    <span className="flex space-x-1">
                                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                                        <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></span>
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                        <div ref={messagesEndRef} />
                                    </div>
                                )}
                            </div>

                            {/* Footer */}
                            <div className="px-4 py-3 bg-white/5 border-t border-white/10 text-xs text-gray-500 flex justify-between items-center">
                                <div>Press <kbd className="font-sans px-1.5 py-0.5 rounded-md bg-white/10 text-gray-300">esc</kbd> to close</div>
                                <div><span className="text-blue-500 font-medium">CG.AI</span> Engine</div>
                            </div>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
