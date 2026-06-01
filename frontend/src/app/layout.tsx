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
  title: "Chandru Ganeshan | AI Engineer",
  description: "Machine Learning Engineer specializing in Agentic AI and Intelligent Systems.",
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
