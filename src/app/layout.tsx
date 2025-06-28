import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import MinimalErrorBoundary from "@/lib/error-handling/minimal-error-boundary";
import { ThemeProvider } from "@/components/theme/theme-provider";

const inter = Inter({
  subsets: ["latin"],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: "Cival Dashboard - Algorithmic Trading Platform",
  description: "Advanced algorithmic trading dashboard with AI-powered strategies, real-time analytics, and comprehensive risk management",
  keywords: ["algorithmic trading", "trading dashboard", "AI trading", "financial analytics", "risk management"],
  authors: [{ name: "Cival Trading Team" }],
  robots: "noindex, nofollow", // Private trading platform
};

export const viewport = "width=device-width, initial-scale=1";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} font-sans antialiased bg-background text-foreground`}
      >
        <ThemeProvider>
          <MinimalErrorBoundary>
            <div id="root" className="min-h-screen">
              {children}
            </div>
          </MinimalErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
