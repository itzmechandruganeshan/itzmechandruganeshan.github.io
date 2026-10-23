import { resumeData } from "@/data/resume";

export function Skills() {
    return (
        <section aria-labelledby="skills-h" className="pt-14">
            <h2 id="skills-h" className="mb-6 text-[20px]">Skills</h2>
            <dl className="space-y-2">
                {Object.entries(resumeData.skills).map(([group, items]) => (
                    <div key={group} className="grid grid-cols-[6.5rem_1fr] gap-x-3 lg:grid-cols-[11rem_1fr] lg:gap-x-8">
                        <dt className="text-muted">{group.replace("_", " ")}</dt>
                        <dd>{items.join(", ")}</dd>
                    </div>
                ))}
            </dl>
            <h2 className="mb-3 mt-12 text-[20px]">Education</h2>
            <ul className="space-y-2">
                {resumeData.education.map((e) => (
                    <li key={e.degree}>
                        {e.degree}, {e.institution}
                        <span className="block text-muted">{e.period}</span>
                    </li>
                ))}
            </ul>
        </section>
    );
}
