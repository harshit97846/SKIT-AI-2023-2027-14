import React from "react";

/**
 * Hridaya Rakshak AI — Official Logo Component.
 * Symbolism:
 *  - Outer Shield: "Rakshak" (Guardian / Protector / Defense)
 *  - Inner Heart: "Hridaya" (Cardiac / Cardiovascular Health)
 *  - Cross-cutting ECG pulse: Medical AI / Real-time Intelligence
 */
export const HridayaShieldIcon = ({ size = 38, className = "" }) => {
    return (
        <svg
            width={size}
            height={size}
            viewBox="0 0 100 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className={className}
            style={{ display: "inline-block", verticalAlign: "middle", flexShrink: 0 }}
            aria-hidden="true"
        >
            <defs>
                {/* Shield Gradient */}
                <linearGradient id="hridayaShieldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#0ea5e9" />
                    <stop offset="50%" stopColor="#0d9488" />
                    <stop offset="100%" stopColor="#059669" />
                </linearGradient>

                {/* Heart Gradient */}
                <linearGradient id="hridayaHeartGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#f43f5e" />
                    <stop offset="100%" stopColor="#e11d48" />
                </linearGradient>

                {/* Subtle Inner Glow */}
                <filter id="hridayaGlow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#0d9488" floodOpacity="0.35" />
                </filter>
            </defs>

            {/* Shield Body (Rakshak) */}
            <path
                d="M50 6C66 16 84 17 88 20C90 38 88 64 50 94C12 64 10 38 12 20C16 17 34 16 50 6Z"
                fill="url(#hridayaShieldGrad)"
                filter="url(#hridayaGlow)"
            />

            {/* Inner Shield Inset */}
            <path
                d="M50 12C63 20 77 21 81 23C83 37 81 58 50 84C19 58 17 37 19 23C23 21 37 20 50 12Z"
                fill="#ffffff"
                fillOpacity="0.16"
            />

            {/* Heart Shape (Hridaya) */}
            <path
                d="M50 71C48.5 69.8 28 54 28 39C28 30.5 34.5 24 43 24C46.8 24 50 25.8 50 28.5C50 25.8 53.2 24 57 24C65.5 24 72 30.5 72 39C72 54 51.5 69.8 50 71Z"
                fill="url(#hridayaHeartGrad)"
            />

            {/* Dynamic ECG Lifeline Pulse (AI) */}
            <path
                d="M26 43H36L41 33L47 53L53 27L58 48L63 43H74"
                stroke="#ffffff"
                strokeWidth="3.2"
                strokeLinecap="round"
                strokeLinejoin="round"
            />

            {/* Neural Sparkle / AI Node */}
            <circle cx="53" cy="27" r="2.4" fill="#38bdf8" />
            <circle cx="47" cy="53" r="2.2" fill="#fed7aa" />
        </svg>
    );
};

export const HridayaLogo = ({
    size = 40,
    showSubtitle = true,
    subtitleText = "Cardiovascular Intelligence & Defense",
    theme = "dark",
    className = "",
}) => {
    return (
        <div className={`hridaya-logo-container ${className}`} style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <HridayaShieldIcon size={size} />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
                <span
                    style={{
                        fontSize: size > 40 ? "1.45rem" : "1.2rem",
                        fontWeight: 800,
                        letterSpacing: "-0.02em",
                        background: "linear-gradient(135deg, #0ea5e9 0%, #0d9488 60%, #10b981 100%)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                    }}
                >
                    Hridaya Rakshak <span style={{ color: "#f43f5e", WebkitTextFillColor: "#f43f5e" }}>AI</span>
                </span>
                {showSubtitle && (
                    <span
                        style={{
                            fontSize: "0.68rem",
                            fontWeight: 600,
                            letterSpacing: "0.06em",
                            textTransform: "uppercase",
                            color: theme === "light" ? "#64748b" : "#94a3b8",
                        }}
                    >
                        {subtitleText}
                    </span>
                )}
            </div>
        </div>
    );
};

export default HridayaLogo;
