import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "./globals.css";
import { ChatProvider } from "@/context/ChatContext";
import { ChatPanel } from "@/components/ChatPanel";
import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { Torch } from "@/components/Torch";
import { SITE_URL } from "@/data/site";

const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const DESCRIPTION =
    "AI/ML engineer in Coimbatore building production GenAI: RAG, multi-agent systems and semantic search. Currently at Searce Inc.";

export const metadata: Metadata = {
    metadataBase: new URL(SITE_URL),
    title: { default: "Chandru Ganeshan, AI/ML Engineer", template: "%s | Chandru Ganeshan" },
    description: DESCRIPTION,
    keywords: ["AI engineer", "ML engineer", "GenAI", "RAG", "LangGraph", "semantic search", "Coimbatore", "Chandru Ganeshan"],
    authors: [{ name: "Chandru Ganeshan", url: SITE_URL }],
    openGraph: {
        type: "website",
        locale: "en_IN",
        siteName: "Chandru Ganeshan",
        title: "Chandru Ganeshan, AI/ML Engineer",
        description: DESCRIPTION,
        images: [{ url: "/og.png", width: 1200, height: 630, alt: "Chandru Ganeshan, AI/ML Engineer" }],
    },
    twitter: { card: "summary_large_image", title: "Chandru Ganeshan, AI/ML Engineer", description: DESCRIPTION, images: ["/og.png"] },
};

// Set before first paint so a saved theme never flashes the other one.
// Torch needs a mouse: a saved torch falls back to dark on touch screens.
const themeScript = `try{var t=localStorage.getItem("theme");if(t==="torch"&&!matchMedia("(pointer: fine)").matches)t="dark";if(t==="light"||t==="dark"||t==="torch")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <head>
                <script dangerouslySetInnerHTML={{ __html: themeScript }} />
            </head>
            <body className={geistMono.variable}>
                <ChatProvider>
                    <Nav />
                    {children}
                    <Footer />
                    <Torch />
                    <ChatPanel />
                </ChatProvider>
            </body>
        </html>
    );
}
