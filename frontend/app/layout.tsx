import "./globals.css";
import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "LyraOS — Your Cognitive Operating System",
  description:
    "LyraOS tracks the difference between what you planned and what actually happened — then learns how you truly work.",
  openGraph: {
    title: "LyraOS — Your Cognitive Operating System",
    description:
      "An adaptive scheduling instrument that measures the gap between plan and execution.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`dark ${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
