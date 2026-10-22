"use client";

const TORCH_OK = "(pointer: fine) and (prefers-reduced-motion: no-preference)";

// The label is swapped by CSS (.to-dark / .to-torch / .to-light), so it is right before hydration and needs no state.
export function ThemeToggle() {
    const toggle = () => {
        const root = document.documentElement;
        const order = matchMedia(TORCH_OK).matches ? ["light", "dark", "torch"] : ["light", "dark"];
        const current = root.dataset.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        root.dataset.theme = order[(order.indexOf(current) + 1) % order.length];
        try {
            localStorage.setItem("theme", root.dataset.theme);
        } catch {
            /* storage blocked: the choice lasts until reload */
        }
    };
    return (
        <button type="button" onClick={toggle} className="relative z-[45] cursor-pointer text-muted hover:bg-sand hover:text-ink"
            aria-label="Switch colour theme">
            <span className="to-dark">dark</span>
            <span className="to-torch">torch</span>
            <span className="to-light">light</span>
        </button>
    );
}
