import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google"; // specific fonts
import "./globals.css";
import { ChatProvider } from "@/context/ChatContext";
import { CmdKChatbot } from "@/components/CmdKChatbot";
import { ScrollProgress } from "@/components/ScrollProgress";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const robotoMono = Roboto_Mono({
  variable: "--font-roboto-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://itzmechandruganeshan.github.io"),
  title: {
    default: "Chandru Ganeshan | AI Engineer",
    template: "%s | Chandru Ganeshan",
  },
  description: "Machine Learning Engineer specializing in Agentic AI, Intelligent Systems, and cutting-edge frontend engineering.",
  keywords: ["AI Engineer", "Machine Learning", "Agentic AI", "Frontend Engineer", "React", "Next.js", "Chandru Ganeshan", "Portfolio"],
  authors: [{ name: "Chandru Ganeshan", url: "https://github.com/itzmechandruganeshan" }],
  creator: "Chandru Ganeshan",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://itzmechandruganeshan.github.io",
    title: "Chandru Ganeshan | AI Engineer",
    description: "Machine Learning Engineer specializing in Agentic AI and Intelligent Systems.",
    siteName: "Chandru Ganeshan Portfolio",
  },
  twitter: {
    card: "summary_large_image",
    title: "Chandru Ganeshan | AI Engineer",
    description: "Machine Learning Engineer specializing in Agentic AI and Intelligent Systems.",
    creator: "@itzmechandru", // Assuming a handle; adjust if needed
  },
  alternates: {
    canonical: "https://itzmechandruganeshan.github.io",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} ${robotoMono.variable} antialiased`}
      >
        <ScrollProgress />
        <ChatProvider>
          {children}
          <CmdKChatbot />
        </ChatProvider>
      </body>
    </html>
  );
}
