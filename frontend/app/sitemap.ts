import type { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    {
      url: "https://lyraos.org",
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: "https://lyraos.org/privacy",
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: "https://lyraos.org/terms",
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: "https://lyraos.org/llms.txt",
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: "https://lyraos.org/lyraos.md",
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.8,
    },
  ];
}
