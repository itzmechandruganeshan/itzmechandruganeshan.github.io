"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, Terminal, Cpu, Briefcase, FileText, CalendarCheck, Video } from "lucide-react";
import { useChat } from "@/context/ChatContext";
import { v4 as uuidv4 } from "uuid";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/chat";
const VISITOR_KEY = "vm_visitor_id";
const LEGACY_KEY = "vm_session_id";

type Slot = { id: string; start: string; end: string; label: string };
type Card =
    | { kind: "resume"; url: string }
    | { kind: "slots"; tz?: string; slots: Slot[] }
    | { kind: "booking"; label: string; meet_url?: string | null };
type Message =
    | { role: "user"; content: string }
    | { role: "ai"; content: string }
    | { role: "card"; card: Card };

type ServerEvent =
    | { type: "typing"; on: boolean }
    | { type: "burst"; turn_id: string; seq: number; text: string }
    | ({ type: "card"; turn_id: string } & Card)
    | { type: "turn_complete"; turn_id: string }
    | { type: "error"; code: string; text: string }
    | { type: "forgotten" };

// A random id for this browser: lets "Chandru" remember a returning visitor on this device only.
// It identifies nothing about the person and is rotated by "Forget me".
function getVisitorId(): string {
    try {
        const existing = localStorage.getItem(VISITOR_KEY) || localStorage.getItem(LEGACY_KEY);
        const id = existing || uuidv4();
        localStorage.setItem(VISITOR_KEY, id);
        localStorage.removeItem(LEGACY_KEY);
        return id;
    } catch {
        return uuidv4(); // private mode / storage blocked: no memory across visits
    }
}

function rotateVisitorId(): void {
    try {
        localStorage.setItem(VISITOR_KEY, uuidv4());
    } catch {
        /* storage blocked: nothing persisted anyway */
    }
}

export function CmdKChatbot() {
    const { isOpen, closeChat, toggleChat } = useChat();
    const [query, setQuery] = useState("");
    const [messages, setMessages] = useState<Message[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const [connected, setConnected] = useState(false);

    const inputRef = useRef<HTMLInputElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const outboxRef = useRef<string[]>([]);
    const retryRef = useRef(0);
    const reconnectRef = useRef<() => void>(() => {});

    // Connect once the chat is first opened; reconnect with backoff.
    const connect = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState <= WebSocket.OPEN) return;
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
            retryRef.current = 0;
            setConnected(true);
            ws.send(JSON.stringify({
                type: "hello",
                visitor_id: getVisitorId(),
                tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
            }));
            for (const payload of outboxRef.current.splice(0)) ws.send(payload);
        };

        ws.onmessage = (e) => {
            let ev: ServerEvent;
            try {
                ev = JSON.parse(e.data);
            } catch {
                return;
            }
            if (ev.type === "typing") setIsTyping(ev.on);
            else if (ev.type === "burst") setMessages((prev) => [...prev, { role: "ai", content: ev.text }]);
            else if (ev.type === "card") {
                const { type: _t, turn_id: _id, ...card } = ev; // eslint-disable-line @typescript-eslint/no-unused-vars
                setMessages((prev) => [...prev, { role: "card", card: card as Card }]);
            } else if (ev.type === "turn_complete") setIsTyping(false);
            else if (ev.type === "forgotten") {
                rotateVisitorId();
                setMessages((prev) => prev.slice(-2)); // keep only the "done, wiped everything" bubbles
                setIsTyping(false);
            } else if (ev.type === "error") {
                setIsTyping(false);
                setMessages((prev) => [...prev, { role: "ai", content: ev.text }]);
            }
        };

        ws.onclose = () => {
            setConnected(false);
            setIsTyping(false);
            const delay = Math.min(15000, 1000 * 2 ** retryRef.current++);
            setTimeout(() => {
                if (wsRef.current === ws) reconnectRef.current();
            }, delay);
        };
    }, []);

    useEffect(() => {
        reconnectRef.current = connect;
    }, [connect]);

    useEffect(() => {
        if (isOpen) connect();
    }, [isOpen, connect]);

    useEffect(() => () => {
        const ws = wsRef.current;
        wsRef.current = null;
        ws?.close();
    }, []);

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

    useEffect(() => {
        if (isOpen) inputRef.current?.focus();
    }, [isOpen]);

    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === "Escape") closeChat();
        };
        if (isOpen) document.addEventListener("keydown", handleEscape);
        return () => document.removeEventListener("keydown", handleEscape);
    }, [isOpen, closeChat]);

    const send = (payload: object) => {
        const data = JSON.stringify({ ...payload, client_msg_id: uuidv4() });
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(data);
        else {
            outboxRef.current.push(data);
            connect();
        }
    };

    const handleSendMessage = (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        const text = query.trim();
        if (!text) return;
        setQuery("");
        setMessages((prev) => [...prev, { role: "user", content: text }]);
        send({ type: "message", text });
    };

    const pickSlot = (slot: Slot) => {
        setMessages((prev) => [...prev, { role: "user", content: slot.label }]);
        send({ type: "action", action: "pick_slot", slot_id: slot.id, text: slot.label });
    };

    const handleSuggestionClick = (suggestion: string) => {
        setQuery(suggestion);
        inputRef.current?.focus();
    };

    const renderCard = (card: Card) => {
        if (card.kind === "resume") {
            return (
                <a href={card.url} target="_blank" rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-gray-200 hover:bg-white/10">
                    <FileText className="w-4 h-4 text-amber-400" /> Chandru-Ganeshan-Resume.pdf
                </a>
            );
        }
        if (card.kind === "slots") {
            return (
                <div className="flex flex-wrap gap-2">
                    {card.slots.map((s) => (
                        <button key={s.id} onClick={() => pickSlot(s)}
                            className="rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1.5 text-xs text-blue-200 hover:bg-blue-500/20">
                            {s.label}
                        </button>
                    ))}
                </div>
            );
        }
        return (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
                <CalendarCheck className="w-4 h-4" />
                <span>{card.label}</span>
                {card.meet_url && (
                    <a href={card.meet_url} target="_blank" rel="noopener noreferrer" className="ml-auto flex items-center gap-1 underline">
                        <Video className="w-4 h-4" /> Meet
                    </a>
                )}
            </div>
        );
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={closeChat}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center pt-[15vh] px-4"
                    >
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95, y: -20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.95, y: -20 }}
                            transition={{ duration: 0.15, ease: "easeOut" }}
                            onClick={(e) => e.stopPropagation()}
                            className="bg-[#0f1115] border border-white/10 shadow-2xl rounded-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[70vh]"
                        >
                            <form onSubmit={handleSendMessage} className="relative border-b border-white/10">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    ref={inputRef}
                                    type="text"
                                    placeholder="Message Chandru..."
                                    value={query}
                                    maxLength={500}
                                    onChange={(e) => setQuery(e.target.value)}
                                    className="w-full bg-transparent text-white placeholder-gray-500 py-4 pl-12 pr-12 outline-none text-lg"
                                />
                                <button
                                    type="button"
                                    onClick={closeChat}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 p-1 bg-white/5 hover:bg-white/10 rounded-md text-gray-400 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </form>

                            <div className="overflow-y-auto p-4 flex-1 custom-scrollbar">
                                {messages.length === 0 ? (
                                    <div className="py-10 px-4 md:px-8 max-w-3xl mx-auto w-full">
                                        <div className="mb-6 flex flex-col items-center md:items-start text-center md:text-left">
                                            <h3 className="text-xl font-semibold text-white mb-1.5">Hey, it&apos;s Chandru 👋</h3>
                                            <p className="text-gray-400 text-sm max-w-md">
                                                Text me about my work, projects, or just say hi.
                                            </p>
                                        </div>

                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                                            {[
                                                { icon: <Terminal className="w-4 h-4 text-emerald-400 mb-3" />, title: "Agentic Systems", query: "How do you architect multi-agent workflows?" },
                                                { icon: <Cpu className="w-4 h-4 text-cyan-400 mb-3" />, title: "RAG & Search", query: "How do you avoid false positives in search?" },
                                                { icon: <Briefcase className="w-4 h-4 text-purple-400 mb-3" />, title: "Current Work", query: "What are you building at Searce?" },
                                                { icon: <FileText className="w-4 h-4 text-amber-400 mb-3" />, title: "Resume", query: "Can you share your resume?" },
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
                                                        &quot;{suggestion.query}&quot;
                                                    </span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {messages.map((msg, idx) => (
                                            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                                                {msg.role === "card" ? (
                                                    <div className="max-w-[85%]">{renderCard(msg.card)}</div>
                                                ) : (
                                                    <div
                                                        className={`max-w-[85%] rounded-2xl px-4 py-2 ${msg.role === "user"
                                                            ? "bg-blue-600 text-white"
                                                            : "bg-white/10 text-gray-200 border border-white/5"
                                                            }`}
                                                    >
                                                        {msg.role === "ai" ? (
                                                            <div className="prose prose-invert max-w-none prose-p:my-0 text-sm">
                                                                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                                                            </div>
                                                        ) : (
                                                            <span className="text-sm whitespace-pre-wrap">{msg.content}</span>
                                                        )}
                                                    </div>
                                                )}
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

                            <div className="px-4 py-3 bg-white/5 border-t border-white/10 text-xs text-gray-500 flex justify-between items-center">
                                <div className="flex items-center gap-2">
                                    <span>Chats are saved for 30 days so I remember you on this device.</span>
                                    <button
                                        type="button"
                                        onClick={() => send({ type: "forget" })}
                                        className="underline hover:text-gray-300"
                                    >
                                        Forget me
                                    </button>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-500" : "bg-gray-600"}`} />
                                    {isTyping ? "typing..." : connected ? "online" : "connecting..."}
                                </div>
                            </div>
                        </motion.div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
