import { GITHUB, RESUME_PDF } from "@/data/site";

export function Footer() {
    return (
        <footer className="no-print page pb-16 text-muted">
            <p>
                Chandru Ganeshan, Coimbatore. <a href={RESUME_PDF} className="link">resume (pdf)</a>,{" "}
                <a href={GITHUB} className="link">github</a>.
            </p>
        </footer>
    );
}
