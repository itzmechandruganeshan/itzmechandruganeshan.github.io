"use client";

// The label is swapped by CSS (.to-dark / .to-light), so it is right before hydration and needs no state.
export function ThemeToggle() {
    const toggle = () => {
        const root = document.documentElement;
        const dark = (root.dataset.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
        root.dataset.theme = dark ? "light" : "dark";
        try {
            localStorage.setItem("theme", root.dataset.theme);
        } catch {
            /* storage blocked: the choice lasts until reload */
        }
    };
    return (
        <button type="button" onClick={toggle} className="cursor-pointer text-muted hover:bg-sand hover:text-ink" aria-label="Switch colour theme">
            <span className="to-dark">dark</span>
            <span className="to-light">light</span>
        </button>
    );
}
