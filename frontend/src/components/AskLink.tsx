"use client";

import { useChat } from "@/context/ChatContext";

/** Opens the chat and sends `text` as the visitor's first message. */
export function AskLink({ text, children }: { text: string; children: React.ReactNode }) {
    const { openChat } = useChat();
    return (
        <button type="button" onClick={() => openChat(text)} className="link">
            {children}
        </button>
    );
}
