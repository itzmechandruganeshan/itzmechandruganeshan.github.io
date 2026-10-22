"use client";

import { useEffect, useRef } from "react";

/** The torch theme's dark layer. Follows the mouse, jumps to keyboard focus; Esc switches back to dark. */
export function Torch() {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const on = () => document.documentElement.dataset.theme === "torch";
        let frame = 0;
        const aim = (x: number, y: number) => {
            cancelAnimationFrame(frame);
            frame = requestAnimationFrame(() => {
                ref.current?.style.setProperty("--x", `${x}px`);
                ref.current?.style.setProperty("--y", `${y}px`);
            });
        };
        const move = (e: MouseEvent) => on() && aim(e.clientX, e.clientY);
        const focus = (e: FocusEvent) => {
            if (!on() || !(e.target instanceof HTMLElement)) return;
            const r = e.target.getBoundingClientRect();
            aim(r.left + r.width / 2, r.top + r.height / 2);
        };
        const key = (e: KeyboardEvent) => {
            if (e.key !== "Escape" || !on()) return;
            document.documentElement.dataset.theme = "dark";
            try {
                localStorage.setItem("theme", "dark");
            } catch {
                /* storage blocked */
            }
        };
        addEventListener("mousemove", move);
        addEventListener("focusin", focus);
        addEventListener("keydown", key);
        return () => {
            cancelAnimationFrame(frame);
            removeEventListener("mousemove", move);
            removeEventListener("focusin", focus);
            removeEventListener("keydown", key);
        };
    }, []);

    return <div ref={ref} aria-hidden className="torch no-print" />;
}
