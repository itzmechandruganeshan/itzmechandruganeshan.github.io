import { MetadataRoute } from 'next';
import { resumeData } from '@/data/resume';
import { SITE_URL, slugOf } from '@/data/site';

export const dynamic = 'force-static';

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: SITE_URL, lastModified: now, changeFrequency: 'monthly', priority: 1 },
    { url: `${SITE_URL}/resume`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    ...resumeData.projects.map((p) => ({
      url: `${SITE_URL}/projects/${slugOf(p.name)}`,
      lastModified: now,
      changeFrequency: 'yearly' as const,
      priority: 0.6,
    })),
  ];
}
