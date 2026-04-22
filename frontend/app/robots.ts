import type { MetadataRoute } from "next";

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
        allow: ["/", "/privacy", "/terms"],
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
    sitemap: "https://lyraos.org/sitemap.xml",
    host: "https://lyraos.org",
  };
}
