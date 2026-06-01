"use client";

import React from "react";
import { motion } from "framer-motion";
import { resumeData } from "@/data/resume";
import { Github } from "lucide-react";
import { parseBoldText } from "@/utils/textFormatting";

interface Project {
    name: string;
    company: string;
    description: string;
    summary?: string;
    impact?: string[];
    github?: string;
    skills?: string[];
}

const ProjectCard = ({
    project,
    index,
}: {
    project: Project;
    index: number;
}) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            whileInView={{ opacity: 1, y: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={{ duration: 0.6, delay: index * 0.15, ease: "easeOut" }}
            className="group relative p-8 glass-panel rounded-3xl overflow-hidden transition-all duration-500 flex flex-col h-full hover:-translate-y-2 hover:shadow-[0_8px_30px_rgb(59,130,246,0.12)] border border-white/5 hover:border-blue-500/30"
        >
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10 flex flex-col h-full">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <div className="text-sm font-mono text-purple-400 mb-2">
                            {project.company}
                        </div>
                        <h3 className="text-2xl font-bold group-hover:text-blue-400 transition-colors">
                            {project.name}
                        </h3>
                    </div>
                    {project.github && (
                        <a
                            href={project.github}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 bg-white/10 hover:bg-white/20 rounded-full transition-colors text-white"
                            title="View Source on GitHub"
                        >
                            <Github className="w-5 h-5" />
                        </a>
                    )}
                </div>

                <p className="text-gray-400 mb-6 leading-relaxed">
                    {parseBoldText(project.summary || project.description)}
                </p>

                {project.skills && (
                    <div className="flex flex-wrap gap-2 mb-6">
                        {project.skills.map((skill, i) => (
                            <span
                                key={i}
                                className="px-3 py-1 bg-white/5 border border-white/10 rounded-full text-xs text-gray-300"
                            >
                                {skill}
                            </span>
                        ))}
                    </div>
                )}

                {project.impact && (
                    <div className="mt-auto">
                        <ul className="space-y-2">
                            {project.impact.map((point, i) => (
                                <li key={i} className="flex gap-3 text-gray-500 text-sm">
                                    <span className="mt-1.5 w-1 h-1 rounded-full bg-blue-500 flex-shrink-0" />
                                    <span>{parseBoldText(point)}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </motion.div>
    );
};

export const Projects = () => {
    return (
        <section id="projects" className="py-20 md:py-32 bg-transparent relative">
            <div className="container mx-auto px-6">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="mb-16 md:mb-24 text-center"
                >
                    <h2 className="text-3xl md:text-5xl font-bold mb-6">
                        Featured <span className="text-gradient">Projects</span>
                    </h2>
                </motion.div>

                <div className="grid md:grid-cols-2 gap-6 max-w-6xl mx-auto">
                    {resumeData.projects.map((project, index) => (
                        <ProjectCard
                            key={index}
                            // @ts-ignore
                            project={project}
                            index={index}
                        />
                    ))}
                </div>
            </div>
        </section>
    );
};
