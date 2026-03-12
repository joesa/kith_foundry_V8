import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";

export type ThemeMode = "dark" | "light";

interface ThemeContextType {
    theme: ThemeMode;
    toggleTheme: () => void;
    setTheme: (theme: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

// Default to dark mode for better visual impact
const DEFAULT_THEME: ThemeMode = "dark";

export function ThemeProvider({ children }: { children: ReactNode }) {
    const [theme, setThemeState] = useState<ThemeMode>(DEFAULT_THEME);

    // Apply theme to document and localStorage
    useEffect(() => {
        const root = window.document.documentElement;
        root.classList.remove("dark", "light");
        root.classList.add(theme);

        // Save to localStorage
        localStorage.setItem("kith-theme", theme);

        // Set CSS variables for generated mockups
        const generatedMockup = document.getElementById("generated-mockup-frame");
        if (generatedMockup) {
            const style = document.createElement("style");
            style.id = "mockup-theme-vars";
            const isDark = theme === "dark";
            style.textContent = `
                :root {
                    --mockup-bg: ${isDark ? "#0A0D1A" : "#F8F9FA"};
                    --mockup-surface: ${isDark ? "#121832" : "#FFFFFF"};
                    --mockup-border: ${isDark ? "#2D3A66" : "#E5E7EB"};
                    --mockup-text: ${isDark ? "#E8EEFF" : "#1F2937"};
                    --mockup-muted: ${isDark ? "#9DB0DE" : "#6B7280"};
                    --mockup-primary: ${isDark ? "#7C5CFF" : "#4F46E5"};
                    --mockup-accent: ${isDark ? "#A855F7" : "#8B5CF6"};
                }
            `;
            generatedMockup.appendChild(style);
        }
    }, [theme]);

    const toggleTheme = useCallback(() => {
        setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
    }, []);

    const setTheme = useCallback((newTheme: ThemeMode) => {
        setThemeState(newTheme);
    }, []);

    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error("useTheme must be used within a ThemeProvider");
    }
    return context;
}