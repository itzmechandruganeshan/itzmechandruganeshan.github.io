import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { resumeData as d } from "@/data/resume";
import { SITE_URL, plain, slugOf } from "@/data/site";
import { parseBoldText } from "@/utils/textFormatting";
import { AskLink } from "@/components/AskLink";
import { JsonLd } from "@/components/JsonLd";

export const dynamicParams = false;

export const generateStaticParams = () => d.projects.map((p) => ({ slug: slugOf(p.name) }));

const find = (slug: string) => {
    const i = d.projects.findIndex((p) => slugOf(p.name) === slug);
    return i < 0 ? null : { p: d.projects[i], prev: d.projects[i - 1], next: d.projects[i + 1] };
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const found = find((await params).slug);
    if (!found) return {};
    return {
        title: found.p.name,
        description: plain(found.p.description),
        alternates: { canonical: `/projects/${slugOf(found.p.name)}` },
    };
}

export default async function ProjectPage({ params }: { params: Promise<{ slug: string }> }) {
    const found = find((await params).slug);
    if (!found) notFound();
    const { p, prev, next } = found;
    const url = `${SITE_URL}/projects/${slugOf(p.name)}`;

    return (
        <main className="page pt-12" data-project={p.name.split(" - ")[0]}>
            <JsonLd data={{
                "@context": "https://schema.org",
                "@graph": [
                    { "@type": "CreativeWork", name: p.name, description: plain(p.description), url,
                      creator: { "@type": "Person", name: d.name, url: SITE_URL }, keywords: p.skills.join(", ") },
                    { "@type": "BreadcrumbList", itemListElement: [
                        { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
                        { "@type": "ListItem", position: 2, name: p.name, item: url },
                    ] },
                ],
            }} />
            <p className="text-muted"><Link href="/#projects" className="link">projects</Link></p>
            <h1 className="mt-4 text-[24px]">{p.name}</h1>
            <p className="text-muted">{p.company}, {p.period}</p>
            <p className="mt-6">{parseBoldText(p.description)}</p>
            <p className="mt-4">{p.summary}</p>

            <h2 className="mb-3 mt-10 text-[20px]">Impact</h2>
            <ul className="list-disc space-y-2 pl-4 marker:text-muted">
                {p.impact.map((i) => <li key={i}>{i}</li>)}
            </ul>

            <h2 className="mb-3 mt-10 text-[20px]">Stack</h2>
            <p>{p.skills.join(", ")}</p>

            <p className="mt-10 flex flex-wrap gap-x-5">
                {"github" in p && p.github && <a href={p.github} className="link">source</a>}
                <AskLink text={`tell me about ${p.name.split(" - ")[0]}`}>ask me about this</AskLink>
            </p>

            <nav aria-label="Other projects" className="mt-12 space-y-1 text-muted">
                {prev && <p>previous: <Link href={`/projects/${slugOf(prev.name)}`} className="link">{prev.name}</Link></p>}
                {next && <p>next: <Link href={`/projects/${slugOf(next.name)}`} className="link">{next.name}</Link></p>}
            </nav>
        </main>
    );
}
