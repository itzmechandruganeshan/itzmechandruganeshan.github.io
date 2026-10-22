import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";

const item = "hover:bg-sand hover:text-ink";

export function Nav() {
    return (
        <header className="no-print mx-auto flex max-w-[38rem] flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 pt-6">
            <Link href="/" className="font-medium">chandru ganeshan</Link>
            <nav aria-label="Main" className="flex flex-wrap items-baseline gap-x-4 text-muted">
                <Link href="/#experience" className={item}>experience</Link>
                <Link href="/#projects" className={item}>projects</Link>
                <Link href="/resume" className={item}>resume</Link>
                <ThemeToggle />
            </nav>
        </header>
    );
}
