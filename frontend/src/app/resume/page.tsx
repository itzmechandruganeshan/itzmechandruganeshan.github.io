import type { Metadata } from "next";
import { resumeData as d } from "@/data/resume";
import { GITHUB, RESUME_PDF, SITE_URL } from "@/data/site";
import { parseBoldText } from "@/utils/textFormatting";
import { Experience } from "@/components/Experience";
import { Skills } from "@/components/Skills";
import { JsonLd } from "@/components/JsonLd";

export const metadata: Metadata = {
    title: "Resume",
    description: "Resume of Chandru Ganeshan, AI/ML engineer: experience, projects, skills and education.",
    alternates: { canonical: "/resume" },
};

// The phone number in the data file is deliberately not shown on the public page.
export default function Resume() {
    return (
        <main className="page pt-12">
            <JsonLd data={{
                "@context": "https://schema.org",
                "@type": "ProfilePage",
                mainEntity: { "@type": "Person", name: d.name, jobTitle: d.title, url: SITE_URL, sameAs: [d.contact.linkedin, GITHUB] },
            }} />
            <h1 className="text-[30px]">{d.name}</h1>
            <p className="text-muted">{d.title}, {d.contact.location}</p>
            <p className="mt-4 flex flex-wrap gap-x-5">
                <a href={`mailto:${d.contact.email}`} className="link">{d.contact.email}</a>
                <a href={d.contact.linkedin} className="link">linkedin</a>
                <a href={GITHUB} className="link">github</a>
                <a href={RESUME_PDF} className="link no-print">download pdf</a>
            </p>
            <p className="mt-6">{parseBoldText(d.summary)}</p>
            <Experience />
            <Skills />
        </main>
    );
}
