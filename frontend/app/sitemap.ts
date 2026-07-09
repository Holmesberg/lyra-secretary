import type { MetadataRoute } from "next";

const PUBLIC_SITE_ORIGIN = process.env.NEXT_PUBLIC_SITE_URL || "https://lyraos.org";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    {
      url: PUBLIC_SITE_ORIGIN,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${PUBLIC_SITE_ORIGIN}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${PUBLIC_SITE_ORIGIN}/terms`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${PUBLIC_SITE_ORIGIN}/llms.txt`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${PUBLIC_SITE_ORIGIN}/lyraos.md`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.8,
    },
  ];
}
