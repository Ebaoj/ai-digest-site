import { defineCollection, z } from 'astro:content';

const articles = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    pubDate: z.coerce.date(),
    category: z.enum(['news', 'paper', 'repo', 'analysis']),
    originalUrl: z.string().url().optional(),
    author: z.string().default('AI Digest'),
    readingTime: z.string().optional(),
    tags: z.array(z.string()).default([]),
    image: z.string().optional(),
  }),
});

export const collections = { articles };
