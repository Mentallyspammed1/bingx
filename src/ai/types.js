"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SelectorSuggestionOutputSchema = exports.SelectorSuggestionInputSchema = exports.SearchOutputSchema = exports.MediaItemSchema = exports.SearchInputSchema = void 0;
const zod_1 = require("zod");
exports.SearchInputSchema = zod_1.z.object({
    query: zod_1.z.string().describe('The search query'),
    driver: zod_1.z.string().describe('The search driver to use'),
    type: zod_1.z.enum(['videos', 'gifs']).describe('The type of content to search for'),
    page: zod_1.z.number().describe('The page number of results to fetch'),
});
exports.MediaItemSchema = zod_1.z.object({
    id: zod_1.z.string(),
    title: zod_1.z.string(),
    url: zod_1.z.string(),
    duration: zod_1.z.string().optional(),
    thumbnail: zod_1.z.string().optional(),
    preview_video: zod_1.z.string().optional(),
    source: zod_1.z.string(),
    type: zod_1.z.string(),
});
exports.SearchOutputSchema = zod_1.z.array(exports.MediaItemSchema);
exports.SelectorSuggestionInputSchema = zod_1.z.object({
    query: zod_1.z.string().describe('The search query that failed'),
    driver: zod_1.z.string().describe('The driver that failed'),
    type: zod_1.z.enum(['videos', 'gifs']).describe('The content type being searched'),
});
exports.SelectorSuggestionOutputSchema = zod_1.z.object({
    reasoning: zod_1.z.string(),
    suggestedCode: zod_1.z.string(),
});
