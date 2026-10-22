"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useChat } from "@/context/ChatContext";
import { RESUME_PDF, WS_URL } from "@/data/site";
import { v4 as uuidv4 } from "uuid";

const VISITOR_KEY = "vm_visitor_id";
const LEGACY_KEY = "vm_session_id";
const SUGGESTIONS = ["what are you building rn?", "open to roles?", "can we book a call?"];

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

// Replies are plain text; only links need to be clickable.
function linkify(text: string): React.ReactNode[] {
    return text.split(/(https?:\/\/[^\s]+)/g).map((part, i) =>
        i % 2 ? <a key={i} href={part} target="_blank" rel="noopener noreferrer" className="link break-all">{part}</a> : part
    );
}

export function ChatPanel() {
    const { isOpen, pending, openChat, closeChat, toggleChat, clearPending } = useChat();
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
    const sendTextRef = useRef<(text: string) => void>(() => {});

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
        messagesEndRef.current?.scrollIntoView({ block: "end" });
    }, [messages, isTyping, isOpen]);

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

    const sendText = (text: string) => {
        setMessages((prev) => [...prev, { role: "user", content: text }]);
        send({ type: "message", text });
    };

    // A message queued from the hero prompt or an "ask me about this" link.
    useEffect(() => {
        sendTextRef.current = sendText;
    });
    useEffect(() => {
        if (pending) {
            sendTextRef.current(pending);
            clearPending();
        }
    }, [pending, clearPending]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        const text = query.trim();
        if (!text) return;
        setQuery("");
        sendText(text);
    };

    const pickSlot = (slot: Slot) => {
        setMessages((prev) => [...prev, { role: "user", content: slot.label }]);
        send({ type: "action", action: "pick_slot", slot_id: slot.id, text: slot.label });
    };

    const renderCard = (card: Card) => {
        if (card.kind === "resume") {
            return <a href={card.url || RESUME_PDF} target="_blank" rel="noopener noreferrer" className="btn">chandru-ganeshan-resume.pdf</a>;
        }
        if (card.kind === "slots") {
            return (
                <div className="flex flex-wrap gap-2">
                    {card.slots.map((s) => (
                        <button key={s.id} type="button" onClick={() => pickSlot(s)} className="btn">{s.label}</button>
                    ))}
                </div>
            );
        }
        return (
            <div className="border border-ink rounded-lg px-3 py-2">
                <p>{card.label}</p>
                {card.meet_url && (
                    <a href={card.meet_url} target="_blank" rel="noopener noreferrer" className="link">open the Meet link</a>
                )}
            </div>
        );
    };

    if (!isOpen) {
        return (
            <button type="button" onClick={() => openChat()} className="btn btn-solid fixed bottom-4 right-4 z-40 no-print">
                text chandru
            </button>
        );
    }

    return (
        <aside
            role="dialog"
            aria-label="Chat with Chandru"
            className="no-print fixed inset-0 z-50 flex flex-col bg-paper md:inset-y-0 md:left-auto md:right-0 md:w-[400px] md:border-l md:border-ink"
        >
            <header className="flex items-baseline justify-between border-b border-rule px-4 py-3">
                <span>
                    chandru <span className="text-muted">{isTyping ? "typing..." : connected ? "online" : "connecting..."}</span>
                </span>
                <button type="button" onClick={closeChat} className="cursor-pointer text-muted hover:bg-sand hover:text-ink">close</button>
            </header>

            <div className="flex-1 overflow-y-auto px-4 py-4" aria-live="polite">
                {messages.length === 0 ? (
                    <div>
                        <p className="text-muted">hey, it&apos;s Chandru. ask about my work, my projects, or whether I&apos;m free to talk.</p>
                        <ul className="mt-4 space-y-1">
                            {SUGGESTIONS.map((s) => (
                                <li key={s}><button type="button" onClick={() => sendText(s)} className="link text-left">{s}</button></li>
                            ))}
                        </ul>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                                {msg.role === "card" ? (
                                    <div className="max-w-[85%]">{renderCard(msg.card)}</div>
                                ) : (
                                    <p className={`max-w-[85%] whitespace-pre-wrap break-words rounded-lg px-3 py-1.5 ${msg.role === "user" ? "bg-ink text-paper" : "border border-rule"}`}>
                                        {msg.role === "ai" ? linkify(msg.content) : msg.content}
                                    </p>
                                )}
                            </div>
                        ))}
                        {isTyping && <p className="text-muted">typing...</p>}
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-rule px-4 py-3">
                <span aria-hidden>&gt;</span>
                <input
                    ref={inputRef}
                    type="text"
                    aria-label="Message Chandru"
                    placeholder="text me"
                    value={query}
                    maxLength={500}
                    onChange={(e) => setQuery(e.target.value)}
                    className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted"
                />
                <button type="submit" className="link">send</button>
            </form>

            <p className="border-t border-rule px-4 py-2 text-muted">
                Chats are saved for 30 days so I remember you on this device.{" "}
                <button type="button" onClick={() => send({ type: "forget" })} className="link">Forget me</button>
            </p>
        </aside>
    );
}
