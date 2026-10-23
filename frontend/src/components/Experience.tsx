import { resumeData } from "@/data/resume";
import { parseBoldText } from "@/utils/textFormatting";

export function Experience() {
    return (
        <section id="experience" aria-labelledby="experience-h" className="pt-14">
            <h2 id="experience-h" className="mb-6 text-[20px]">Experience</h2>
            <div className="space-y-8">
                {resumeData.experience.map((job) => (
                    <article key={job.company + job.period} className="lg:grid lg:grid-cols-[11rem_1fr] lg:gap-x-8 lg:[&>*]:col-start-2">
                        <h3>{job.role}, {job.company}</h3>
                        <p className="text-muted lg:col-start-1! lg:row-start-1 lg:row-span-5">{job.period}<span className="lg:hidden">, </span><span className="lg:block">{job.location}</span></p>
                        <ul className="mt-2 list-disc space-y-2 pl-4 marker:text-muted">
                            {job.achievements.map((a) => <li key={a}>{parseBoldText(a)}</li>)}
                        </ul>
                    </article>
                ))}
            </div>
        </section>
    );
}
