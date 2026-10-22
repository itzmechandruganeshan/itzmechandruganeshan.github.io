"use client";

import { useState } from "react";
import { useChat } from "@/context/ChatContext";

const OPENERS = ["what are you building rn?", "open to roles?", "book a call"];

// The one bold element on the page: a prompt that starts the chat. The block caret blinks while it's empty.
export function HeroComposer() {
    const { openChat } = useChat();
    const [value, setValue] = useState("");

    const submit = (e: React.FormEvent) => {
        e.preventDefault();
        openChat(value.trim() || undefined);
        setValue("");
    };

    return (
        <div className="no-print">
            <form onSubmit={submit} className="flex items-center gap-2 border-b border-ink py-2">
                <span aria-hidden>&gt;</span>
                <div className="relative flex-1">
                    {!value && <span aria-hidden className="caret absolute left-0 top-1/2 -translate-y-1/2" />}
                    <input
                        type="text"
                        aria-label="Text Chandru"
                        placeholder="text me, I read these"
                        value={value}
                        maxLength={500}
                        onChange={(e) => setValue(e.target.value)}
                        className="w-full bg-transparent pl-4 outline-none placeholder:text-muted focus:pl-0 focus:placeholder:text-transparent"
                    />
                </div>
                <button type="submit" className="link">send</button>
            </form>
            <p className="mt-3 flex flex-wrap gap-x-5 text-muted">
                {OPENERS.map((o) => (
                    <button key={o} type="button" onClick={() => openChat(o)} className="cursor-pointer hover:bg-sand hover:text-ink">{o}</button>
                ))}
            </p>
        </div>
    );
}
