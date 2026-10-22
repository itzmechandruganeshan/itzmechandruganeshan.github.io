import Link from "next/link";

export default function NotFound() {
    return (
        <main className="mx-auto max-w-[38rem] px-4 pt-16">
            <h1 className="text-[24px]">Page not found</h1>
            <p className="mt-3 text-muted">That address doesn&apos;t exist on this site.</p>
            <p className="mt-6"><Link href="/" className="link">Go to the home page</Link></p>
        </main>
    );
}
