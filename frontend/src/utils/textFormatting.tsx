import React from "react";

/**
 * Parses a string containing markdown-style bold syntax (**text**) 
 * and returns an array of React nodes with the bolded parts wrapped in <strong> tags.
 * 
 * @param text The text to parse
 * @returns A React node array or the original text if no formatting is found
 */
export const parseBoldText = (text: string): React.ReactNode => {
    if (!text.includes("**")) {
        return text;
    }

    const parts = text.split("**");

    return parts.map((part, index) => {
        // Even indices are variable text, odd indices are bolded text
        // Example: "Hello **world**!" -> ["Hello ", "world", "!"]
        if (index % 2 === 1) {
            return (
                <strong key={index} className="text-blue-400 font-semibold">
                    {part}
                </strong>
            );
        }
        return <span key={index}>{part}</span>;
    });
};
