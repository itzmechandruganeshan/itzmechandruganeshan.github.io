"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";

const navItems = [


    { name: "Experience", href: "#experience" },
    { name: "Projects", href: "#projects" },
];

export const Navbar = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 50);
        };

        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <>
            <motion.nav
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                transition={{ duration: 0.5 }}
                className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${isScrolled ? "bg-black/80 backdrop-blur-md py-4" : "bg-transparent py-6"
                    }`}
            >
                <div className="container mx-auto px-6 flex justify-between items-center">
                    <a href="#" className="text-xl font-bold text-white tracking-tighter">
                        CG<span className="text-blue-500"></span>
                    </a>

                    {/* Desktop Menu */}
                    <div className="hidden md:flex gap-8">
                        {navItems.map((item) => (
                            <a
                                key={item.name}
                                href={item.href}
                                className="text-sm font-medium text-gray-300 hover:text-white transition-colors"
                            >
                                {item.name}
                            </a>
                        ))}
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        className="md:hidden text-white"
                        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                    >
                        {isMobileMenuOpen ? <X /> : <Menu />}
                    </button>
                </div>
            </motion.nav>

            {/* Mobile Menu */}
            <AnimatePresence>
                {isMobileMenuOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: -20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="fixed inset-0 z-40 bg-black pt-24 px-6 md:hidden"
                    >
                        <div className="flex flex-col gap-6 items-center">
                            {navItems.map((item) => (
                                <a
                                    key={item.name}
                                    href={item.href}
                                    className="text-2xl font-bold text-gray-300 hover:text-white transition-colors"
                                    onClick={() => setIsMobileMenuOpen(false)}
                                >
                                    {item.name}
                                </a>
                            ))}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
};
