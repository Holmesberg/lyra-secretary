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
        url: "/insights-v2.png",
        width: 1392,
        height: 868,
        alt: "LyraOS insights dashboard - 83 sessions analyzed with archetype proximity plus readiness, time-of-day, abandonment, pause, and category insight cards.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LyraOS — Your Cognitive Operating System",
    description:
      "Adaptive scheduling instrument. See your hidden execution patterns in 7 days.",
    images: ["/insights-v2.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

// JSON-LD structured data (Schema.org) for rich-snippet + knowledge-
// graph eligibility. WebApplication + Organization + SoftwareApplication
// so search engines can surface category, pricing (free pre-alpha),
// homepage URL, + the operator attribution. Added 2026-04-23 alongside
// the robots.txt /admin disallow fix.
const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebApplication",
      "@id": "https://lyraos.org/#app",
      name: "LyraOS",
      url: "https://lyraos.org",
      description:
        "Measurement-backed adaptive task scheduler. Records planned vs executed duration per task to learn behavioral patterns, with a research layer that validates whether its own insights actually predict anything.",
      applicationCategory: "ProductivityApplication",
      operatingSystem: "Web",
      offers: {
        "@type": "Offer",
        price: "0",
        priceCurrency: "USD",
        availability: "https://schema.org/LimitedAvailability",
      },
      featureList: [
        "Task planning with duration estimates",
        "Stopwatch timing with pause/resume",
        "Pre- and post-task readiness capture",
        "Personal bias factor calibration",
        "Archetype-prior shrinkage predictions",
        "Google Calendar integration",
        "Pause pattern prediction",
      ],
    },
    {
      "@type": "Organization",
      "@id": "https://lyraos.org/#org",
      name: "LyraOS",
      url: "https://lyraos.org",
      description:
        "Independent research instrument for measuring how humans estimate vs execute. Pre-alpha, built in public in Cairo.",
    },
    {
      "@type": "WebSite",
      "@id": "https://lyraos.org/#site",
      url: "https://lyraos.org",
      name: "LyraOS",
      description:
        "Are humans wrong about themselves in a structured way that predicts failure?",
      inLanguage: "en",
      publisher: { "@id": "https://lyraos.org/#org" },
    },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`dark ${chakra.variable} ${GeistSans.variable} ${GeistMono.variable}`}
    >
      <head>
        {/* Schema.org JSON-LD — rendered server-side so crawlers see it
            without executing JS. Next.js auto-hydrates; no runtime cost. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
