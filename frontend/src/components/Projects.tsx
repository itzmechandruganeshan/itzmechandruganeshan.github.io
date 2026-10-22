import Link from "next/link";
import { resumeData } from "@/data/resume";
import { slugOf } from "@/data/site";
import { parseBoldText } from "@/utils/textFormatting";
import { AskLink } from "@/components/AskLink";

export function Projects() {
    return (
        <section id="projects" aria-labelledby="projects-h" className="pt-14">
            <h2 id="projects-h" className="mb-6 text-[20px]">Featured projects</h2>
            <div className="space-y-8">
                {resumeData.projects.map((p) => (
                    <article key={p.name}>
                        <h3><Link href={`/projects/${slugOf(p.name)}`} className="link">{p.name}</Link></h3>
                        <p className="text-muted">{p.company}, {p.period}</p>
                        <p className="mt-1">{parseBoldText(p.description)}</p>
                        <p className="mt-1 text-muted">{p.skills.join(", ")}</p>
                        <p className="mt-1 flex gap-x-5">
                            <Link href={`/projects/${slugOf(p.name)}`} className="link">read more</Link>
                            <AskLink text={`tell me about ${p.name.split(" - ")[0]}`}>ask me about this</AskLink>
                        </p>
                    </article>
                ))}
            </div>
        </section>
    );
}
