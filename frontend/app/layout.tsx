import "./globals.css";
import type { Metadata } from "next";
import { Chakra_Petch } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Providers } from "@/components/providers";

const chakra = Chakra_Petch({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://lyraos.org"),
  title: "LyraOS — Your Cognitive Operating System",
  description:
    "A measurement instrument that logs every estimate you make and every outcome that follows — then shows you the pattern. Pre-alpha research tool, built in public in Cairo.",
  keywords: [
    "adaptive scheduling",
    "cognitive operating system",
    "metacognitive measurement",
    "planning accuracy",
    "neuroadaptive systems",
    "time estimation research",
    "productivity research instrument",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "LyraOS — Your Cognitive Operating System",
    description:
      "Lyra tracks the difference between what you planned and what actually happened — then shows you the pattern you couldn't see alone.",
    type: "website",
    url: "https://lyraos.org",
    siteName: "LyraOS",
    locale: "en_US",
    images: [
      {
        url: "/insights-v1.png",
        width: 1160,
        height: 980,
        alt: "LyraOS insights dashboard — 45 sessions analyzed across estimation, time-of-day, abandonment, pause, and category dimensions.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LyraOS — Your Cognitive Operating System",
    description:
      "Adaptive scheduling instrument. See your hidden execution patterns in 7 days.",
    images: ["/insights-v1.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`dark ${chakra.variable} ${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
