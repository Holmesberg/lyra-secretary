import type { MetadataRoute } from "next";

const PUBLIC_SITE_ORIGIN = process.env.NEXT_PUBLIC_SITE_URL || "https://lyraos.org";

/**
 * Marketing surfaces (/, /privacy, /terms) are fair game for crawlers.
 * Authenticated app routes and the API are useless to bots (session-gated
 * and return nothing without a token) so we disallow them explicitly to
 * save crawl budget.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/privacy", "/terms", "/llms.txt", "/lyraos.md"],
        disallow: [
          "/today",
          "/calendar",
          "/table",
          "/insights",
          "/settings",
          "/onboarding",
          "/admin/",
          "/api/",
        ],
      },
    ],
    sitemap: `${PUBLIC_SITE_ORIGIN}/sitemap.xml`,
    host: PUBLIC_SITE_ORIGIN,
  };
}
