import React from "react";

/** Renders **bold** markers from the resume data as <strong>. */
export const parseBoldText = (text: string): React.ReactNode =>
    text.includes("**")
        ? text.split("**").map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>))
        : text;
