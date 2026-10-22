"use client";

import { useEffect, useState } from "react";
import { WS_URL } from "@/data/site";

const API = WS_URL.replace(/^ws/, "http").replace(/\/ws\/chat$/, "");

/** What Chandru is doing right now, from the same routine the chat uses. Renders nothing if the backend is unreachable. */
export function StatusLine() {
    const [line, setLine] = useState<string | null>(null);

    useEffect(() => {
        const ctrl = new AbortController();
        fetch(`${API}/status`, { signal: ctrl.signal })
            .then((r) => (r.ok ? r.json() : null))
            .then((d) => d?.line && setLine(d.line))
            .catch(() => {});
        return () => ctrl.abort();
    }, []);

    return line ? <p className="text-muted">rn: {line}</p> : null;
}
