import type { Metadata } from "next";
import { resumeData as d } from "@/data/resume";
import { GITHUB, SITE_URL } from "@/data/site";
import { parseBoldText } from "@/utils/textFormatting";
import { HeroComposer } from "@/components/HeroComposer";
import { StatusLine } from "@/components/StatusLine";
import { Experience } from "@/components/Experience";
import { Projects } from "@/components/Projects";
import { Skills } from "@/components/Skills";
import { JsonLd } from "@/components/JsonLd";

export const metadata: Metadata = { alternates: { canonical: "/" } };

export default function Home() {
    return (
        <main className="page">
            <JsonLd data={{
                "@context": "https://schema.org",
                "@type": "Person",
                name: d.name,
                jobTitle: d.title,
                url: SITE_URL,
                address: { "@type": "PostalAddress", addressLocality: "Coimbatore", addressCountry: "IN" },
                worksFor: { "@type": "Organization", name: d.experience[0].company },
                alumniOf: d.education.map((e) => ({ "@type": "CollegeOrUniversity", name: e.institution })),
                knowsAbout: d.skills.core,
                sameAs: [d.contact.linkedin, GITHUB],
            }} />
            <section className="pt-16">
                <h1 className="text-[30px]">{d.name}</h1>
                <p className="text-muted">{d.title}, {d.contact.location}</p>
                <p className="mt-6">{parseBoldText(d.summary)}</p>
                <p className="mt-6 flex flex-wrap gap-x-5">
                    <a href={`mailto:${d.contact.email}`} className="link">email</a>
                    <a href={d.contact.linkedin} className="link">linkedin</a>
                    <a href={GITHUB} className="link">github</a>
                </p>
                <div className="mt-8"><HeroComposer /></div>
                <div className="mt-3"><StatusLine /></div>
            </section>
            <Experience />
            <Projects />
            <Skills />
        </main>
    );
}
