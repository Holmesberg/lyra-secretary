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

const PUBLIC_SITE_ORIGIN = process.env.NEXT_PUBLIC_SITE_URL || "https://lyraos.org";

export const metadata: Metadata = {
  metadataBase: new URL(PUBLIC_SITE_ORIGIN),
  title: "LyraOS - Planning Evidence And Recovery",
  description:
    "A pre-alpha planning and execution instrument that treats task estimates as hypotheses and work sessions as evidence.",
  keywords: [
    "planning evidence",
    "planning accuracy",
    "execution tracking",
    "clean data",
    "behavioral instrumentation",
    "human-AI collaboration",
    "metacognitive measurement",
    "time estimation research",
    "productivity research instrument",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "LyraOS - Planning Evidence And Recovery",
    description:
      "A pre-alpha planning and execution instrument for comparing plans with clean execution evidence.",
    type: "website",
    url: PUBLIC_SITE_ORIGIN,
    siteName: "LyraOS",
    locale: "en_US",
    images: [
      {
        url: "/insights-v2.png",
        width: 875,
        height: 780,
        alt: "LyraOS evidence dashboard with bounded planning and execution summaries.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LyraOS - Planning Evidence And Recovery",
    description:
      "Pre-alpha planning evidence, timers, and bounded execution summaries.",
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
      name: "LyraOS",
      url: PUBLIC_SITE_ORIGIN,
      description:
        "Pre-alpha planning and execution instrument. It treats task estimates as hypotheses, records work sessions as evidence, and keeps behavioral claims bounded by data quality.",
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
        "Clean-data and provenance-aware evidence summaries",
        "Google Calendar integration",
        "Operator readiness diagnostics",
      ],
    },
    {
      "@type": "Organization",
      "@id": `${PUBLIC_SITE_ORIGIN}/#org`,
      name: "LyraOS",
      url: PUBLIC_SITE_ORIGIN,
      description:
        "Independent pre-alpha planning and execution research instrument built in public in Cairo.",
    },
    {
      "@type": "WebSite",
      "@id": `${PUBLIC_SITE_ORIGIN}/#site`,
      url: PUBLIC_SITE_ORIGIN,
      name: "LyraOS",
      description:
        "Planning estimates, execution traces, and bounded evidence about the gap between plans and reality.",
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
        {/* Schema.org JSON-LD - rendered server-side so crawlers see it
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
