export const SITE_URL = "https://itzmechandruganeshan.github.io";
export const GITHUB = "https://github.com/itzmechandruganeshan";
export const RESUME_PDF = "/resume/chandru-ganeshan-resume.pdf";
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "wss://virtual-me-chandru.fly.dev/ws/chat";

// Project pages live at /projects/<name before " - ">, e.g. "Tpay - AI-Powered..." -> "tpay".
export const slugOf = (name: string) =>
    name.split(" - ")[0].toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export const plain = (text: string) => text.replaceAll("**", "");
