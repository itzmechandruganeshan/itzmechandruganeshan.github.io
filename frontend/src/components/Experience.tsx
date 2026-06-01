"use client";

import React from "react";
import { motion } from "framer-motion";
import { resumeData } from "@/data/resume";
import { Briefcase, Calendar } from "lucide-react";
import { parseBoldText } from "@/utils/textFormatting";

export const Experience = () => {
    return (
        <section id="experience" className="py-20 md:py-32 bg-transparent relative">
            <div className="absolute top-0 right-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute top-1/2 left-1/4 w-96 h-96 bg-blue-600/5 rounded-full blur-[100px]" />
            </div>

            <div className="container mx-auto px-6 relative z-10">
                <motion.h2
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-3xl md:text-5xl font-bold mb-16 text-center"
                >
                    Professional <span className="text-gradient">Journey</span>
                </motion.h2>

                <div className="max-w-6xl mx-auto space-y-12">
                    {resumeData.experience.map((job, index) => (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 50, rotateX: -10 }}
                            whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                            viewport={{ once: true, amount: 0.2 }}
                            transition={{ duration: 0.7, delay: index * 0.1, ease: "easeOut" }}
                            className="relative pl-8 md:pl-0 perspective-1000"
                        >
                            {/* Timeline line for mobile */}
                            <div className="absolute left-0 top-0 bottom-0 w-px bg-white/10 md:hidden" />
                            <div className="absolute left-[-4px] top-6 w-2 h-2 rounded-full bg-blue-500 md:hidden" />


                            <div className="md:grid md:grid-cols-4 gap-8">
                                <div className="md:col-span-1 mb-4 md:mb-0 md:text-right">
                                    <h4 className="text-lg font-bold text-white">{job.company}</h4>
                                    <div className="flex md:justify-end items-center gap-2 text-sm text-gray-400 mt-1">
                                        <Calendar className="w-3 h-3" />
                                        {job.period}
                                    </div>
                                    <div className="text-sm text-gray-500 mt-1">{job.location}</div>
                                </div>

                                <div className="md:col-span-3 relative">
                                    {/* Timeline dot for desktop */}
                                    <motion.div 
                                        initial={{ scale: 0 }}
                                        whileInView={{ scale: 1 }}
                                        viewport={{ once: true }}
                                        transition={{ duration: 0.4, delay: index * 0.1 + 0.2 }}
                                        className="hidden md:block absolute -left-6 top-2 w-4 h-4 rounded-full bg-blue-900 border-2 border-blue-500 z-10" 
                                    />
                                    <div className="hidden md:block absolute -left-[17px] top-6 bottom-[-48px] w-px bg-white/10" />
                                    <motion.div 
                                        initial={{ scaleY: 0 }}
                                        whileInView={{ scaleY: 1 }}
                                        viewport={{ once: true, margin: "-100px" }}
                                        transition={{ duration: 0.8, delay: index * 0.1 + 0.3 }}
                                        className="hidden md:block absolute -left-[17px] top-6 bottom-[-48px] w-px bg-blue-500 origin-top z-0" 
                                    />

                                    <div className="glass-panel p-6 rounded-2xl border border-white/5 hover:border-blue-500/30 hover:bg-white/[0.04] hover:-translate-y-1 transition-all duration-300">
                                        <h3 className="text-xl font-semibold text-blue-400 mb-4 flex items-center gap-2">
                                            <Briefcase className="w-5 h-5" />
                                            {job.role}
                                        </h3>
                                        <ul className="space-y-3">
                                            {job.achievements.map((achievement, i) => (
                                                <li key={i} className="flex items-start gap-3 text-gray-300">
                                                    <span className="mt-2 w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
                                                    <span className="leading-relaxed">{parseBoldText(achievement)}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
};
