"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { resumeData } from "@/data/resume";
import { Github, Star, GitFork } from "lucide-react";
import { parseBoldText } from "@/utils/textFormatting";

interface GithubData {
    stargazers_count: number;
    forks_count: number;
}

const GithubStats = ({ url }: { url: string }) => {
    const [stats, setStats] = useState<GithubData | null>(null);

    useEffect(() => {
        if (!url.startsWith("https://github.com/")) return;
        const repoPath = url.replace("https://github.com/", "");
        
        fetch(`https://api.github.com/repos/${repoPath}`)
            .then(res => res.json())
            .then(data => {
                if (data.stargazers_count !== undefined) {
                    setStats({
                        stargazers_count: data.stargazers_count,
                        forks_count: data.forks_count
                    });
                }
            })
            .catch(console.error);
    }, [url]);

    if (!stats) return null;

    return (
        <div className="flex items-center gap-3 text-xs text-gray-400 font-mono mt-4 border-t border-white/10 pt-4">
            <div className="flex items-center gap-1">
                <Star className="w-3.5 h-3.5" /> {stats.stargazers_count}
            </div>
            <div className="flex items-center gap-1">
                <GitFork className="w-3.5 h-3.5" /> {stats.forks_count}
            </div>
            <div className="flex items-center gap-1 ml-auto text-green-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" /> Live
            </div>
        </div>
    );
};

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
}: {
    project: Project;
}) => {
    return (
        <motion.div
            variants={{
                hidden: { opacity: 0, y: 30, scale: 0.95 },
                visible: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: "easeOut" } }
            }}
            className="group relative p-8 glass-panel rounded-3xl overflow-hidden transition-all duration-500 flex flex-col h-full hover:-translate-y-2 hover:shadow-[0_8px_30px_rgba(255,255,255,0.05)] border border-white/5 hover:border-white/20"
        >
            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10 flex flex-col h-full">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <div className="text-sm font-mono text-gray-500 mb-2">
                            {project.company}
                        </div>
                        <h3 className="text-2xl font-bold group-hover:text-gray-100 text-white transition-colors">
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
                                <li key={i} className="flex gap-3 text-gray-400 text-sm">
                                    <span className="mt-1.5 w-1 h-1 rounded-full bg-gray-500 flex-shrink-0" />
                                    <span>{parseBoldText(point)}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {project.github && project.github.startsWith("https://github.com") && (
                    <GithubStats url={project.github} />
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

                <motion.div 
                    variants={{
                        hidden: {},
                        visible: { transition: { staggerChildren: 0.15 } }
                    }}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, amount: 0.1 }}
                    className="grid md:grid-cols-2 gap-6 max-w-6xl mx-auto"
                >
                    {resumeData.projects.map((project, index) => (
                        <ProjectCard
                            key={index}
                            project={project}
                        />
                    ))}
                </motion.div>
            </div>
        </section>
    );
};
