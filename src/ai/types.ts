import { z } from 'zod';

export const SearchInputSchema = z.object({
  query: z.string().describe('The search query'),
  driver: z.string().describe('The search driver to use'),
  type: z.enum(['videos', 'gifs']).describe('The type of content to search for'),
  page: z.number().describe('The page number of results to fetch'),
});
export type SearchInput = z.infer<typeof SearchInputSchema>;

const MediaResultSchema = z.object({
    id: z.string(),
    title: z.string(),
    url: z.string(),
    duration: z.string().optional(),
    thumbnail: z.string().optional(),
    preview_video: z.string().optional(),
    source: z.string(),
    type: z.string(),
});

export const SearchOutputSchema = z.array(MediaResultSchema);
export type SearchOutput = z.infer<typeof SearchOutputSchema>;
