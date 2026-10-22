"use client";

import React, { createContext, useCallback, useContext, useState, ReactNode } from "react";

interface ChatContextType {
    isOpen: boolean;
    /** A message queued by "ask me about this" / the hero prompt; the panel sends it once and clears it. */
    pending: string | null;
    openChat: (text?: string) => void;
    closeChat: () => void;
    toggleChat: () => void;
    clearPending: () => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
    const [isOpen, setIsOpen] = useState(false);
    const [pending, setPending] = useState<string | null>(null);

    const openChat = useCallback((text?: string) => {
        setIsOpen(true);
        if (text) setPending(text);
    }, []);
    const closeChat = useCallback(() => setIsOpen(false), []);
    const toggleChat = useCallback(() => setIsOpen((prev) => !prev), []);
    const clearPending = useCallback(() => setPending(null), []);

    return (
        <ChatContext.Provider value={{ isOpen, pending, openChat, closeChat, toggleChat, clearPending }}>
            {children}
        </ChatContext.Provider>
    );
}

export function useChat() {
    const context = useContext(ChatContext);
    if (context === undefined) {
        throw new Error("useChat must be used within a ChatProvider");
    }
    return context;
}
