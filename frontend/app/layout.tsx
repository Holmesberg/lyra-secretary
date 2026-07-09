import "./globals.css";
import type { Metadata } from "next";
import { Chakra_Petch } from "next/font/google";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { getServerSession } from "next-auth";
import { Providers } from "@/components/providers";
import { authOptions } from "@/lib/auth";

const chakra = Chakra_Petch({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  weight: ["300", "400", "500", "600", "700"],
});

const PUBLIC_SITE_ORIGIN = process.env.NEXT_PUBLIC_SITE_URL || "https://barzakh.app";

export const metadata: Metadata = {
  metadataBase: new URL(PUBLIC_SITE_ORIGIN),
  title: "Barzakh — Your Cognitive Operating System",
  description:
    "An AI-native productivity system that treats task estimates as hypotheses and work sessions as evidence — then shows you the pattern.",
  keywords: [
    "AI productivity system",
    "AI-native productivity",
    "adaptive productivity platform",
    "adaptive scheduling",
    "cognitive workflow platform",
    "cognitive operating system",
    "behavior-aware scheduler",
    "human-AI collaboration",
    "metacognitive measurement",
    "planning accuracy",
    "planning accuracy app",
    "neuroadaptive systems",
    "time estimation research",
    "productivity research instrument",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "Barzakh — Your Cognitive Operating System",
    description:
      "An AI-native productivity system that learns the gap between your plans and reality.",
    type: "website",
    url: PUBLIC_SITE_ORIGIN,
    siteName: "Barzakh",
    locale: "en_US",
    images: [
      {
        url: "/insights-v2.png",
        width: 875,
        height: 780,
        alt: "Barzakh insights dashboard with a primary synthesis card and supporting confidence-ranked behavioral evidence.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "Barzakh — Your Cognitive Operating System",
    description:
      "AI-native productivity system for planning accuracy, adaptive scheduling, and behavioral feedback.",
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
      "@id": `${PUBLIC_SITE_ORIGIN}/#app`,
      name: "Barzakh",
      url: PUBLIC_SITE_ORIGIN,
      description:
        "AI-native productivity system and behavior-aware scheduler. Treats task estimates as hypotheses and work sessions as evidence, then uses planned-vs-executed traces to reveal behavioral patterns.",
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
        "Planning accuracy measurement",
        "Adaptive behavioral feedback",
        "Personal bias factor calibration",
        "Archetype-prior shrinkage predictions",
        "Google Calendar integration",
        "Pause pattern prediction",
      ],
    },
    {
      "@type": "Organization",
      "@id": `${PUBLIC_SITE_ORIGIN}/#org`,
      name: "Barzakh",
      url: PUBLIC_SITE_ORIGIN,
      description:
        "Independent AI-native productivity system with behavioral instrumentation for measuring how humans estimate vs execute. Pre-alpha, built in public in Cairo.",
    },
    {
      "@type": "WebSite",
      "@id": `${PUBLIC_SITE_ORIGIN}/#site`,
      url: PUBLIC_SITE_ORIGIN,
      name: "Barzakh",
      description:
        "Are humans wrong about themselves in a structured way that predicts failure?",
      inLanguage: "en",
      publisher: { "@id": `${PUBLIC_SITE_ORIGIN}/#org` },
    },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const session = await getServerSession(authOptions);

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
        <Providers session={session}>{children}</Providers>
      </body>
    </html>
  );
}
