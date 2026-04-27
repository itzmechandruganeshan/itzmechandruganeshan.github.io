"use client";

import React from "react";
import { resumeData } from "@/data/resume";
import { Github, Linkedin, Mail } from "lucide-react";

export const Footer = () => {
    return (
        <footer className="bg-transparent py-12">
            <div className="container mx-auto px-6 flex flex-col items-center gap-6">
                <div className="flex gap-6">
                    <a href={resumeData.contact.linkedin} target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
                        <Linkedin className="w-5 h-5" />
                    </a>
                    <a href="https://github.com/itzmechandruganeshan" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
                        <Github className="w-5 h-5" />
                    </a>
                    <a href={`mailto:${resumeData.contact.email}`} className="text-gray-400 hover:text-white transition-colors">
                        <Mail className="w-5 h-5" />
                    </a>
                </div>
                <div className="text-center">
                    <p className="text-gray-400 text-sm mb-2">
                        &copy; {new Date().getFullYear()} {resumeData.name}. All rights reserved.
                    </p>
                    <p className="text-xs text-gray-500 font-mono">
                        Engineered with Next.js 14, React Server Components, and Tailwind CSS.
                    </p>
                </div>
            </div>
        </footer>
    );
};
