"use strict"
'use server'
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k
    var desc = Object.getOwnPropertyDescriptor(m, k)
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k] } }
    }
    Object.defineProperty(o, k2, desc)
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k
    o[k2] = m[k]
}))
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v })
}) : function(o, v) {
    o["default"] = v
})
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = []
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k
            return ar
        }
        return ownKeys(o)
    }
    return function (mod) {
        if (mod && mod.__esModule) return mod
        var result = {}
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i])
        __setModuleDefault(result, mod)
        return result
    }
})()
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod }
}
Object.defineProperty(exports, "__esModule", { value: true })
exports.getDrivers = getDrivers
exports.search = search
exports.suggestSelectors = suggestSelectors
/**
 * @fileOverview A search flow for scraping content.
 *
 * - search - A function that handles the scraping process.
 * - getDrivers - Returns a list of available driver names.
 * - suggestSelectors - An AI flow to suggest new CSS selectors for a broken scraper.
 */
const axios_1 = __importDefault(require("axios"))
const cheerio = __importStar(require("cheerio"))
const genkit_1 = require("@/ai/genkit")
const zod_1 = require("zod")
// Helper function to make URLs absolute
function makeAbsolute(urlString, baseUrl) {
    if (!urlString || typeof urlString !== 'string')
        return undefined
    if (urlString.startsWith('data:'))
        return urlString
    if (urlString.startsWith('//'))
        return `https:${urlString}`
    if (urlString.startsWith('http:') || urlString.startsWith('https:'))
        return urlString
    try {
        return new URL(urlString, baseUrl).href
    }
    catch (e) {
        return undefined
    }
}
// --- Driver Definitions ---
const pornhub = {
    name: 'Pornhub',
    videoUrl: (query, page) => `https://www.pornhub.com/video/search?search=${encodeURIComponent(query)}&page=${page}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://www.pornhub.com'
        $('li.videoBox').each((_, element) => {
            const item = $(element)
            const link = item.find('a').first()
            const videoUrl = makeAbsolute(link.attr('href'), baseUrl)
            const videoId = item.attr('_vkey') || videoUrl?.split('viewkey=')[1]
            const title = item.find('a.videoTitle').text().trim() || item.find('.title a').text().trim()
            const img = item.find('img.thumb')
            const thumbnail = makeAbsolute(img.attr('data-mediumthumb') || img.attr('data-thumb_url') || img.attr('data-src') || img.attr('src'), baseUrl)
            const duration = item.find('.duration').text().trim()
            let preview_video
            const scriptTag = item.find('script').html()
            if (scriptTag) {
                try {
                    const mediaDefs = JSON.parse(scriptTag)
                    preview_video = mediaDefs?.media_preview_url?.replace(/\\/g, '')
                }
                catch (e) {
                    const match = scriptTag.match(/media_preview_url":"(.*?)"/)
                    if (match && match[1]) {
                        preview_video = match[1].replace(/\\/g, '')
                    }
                }
            }
            if (videoUrl && title && thumbnail && videoId && !thumbnail.includes('nothumb')) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Pornhub', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://www.pornhub.com/gifs/search?search=${encodeURIComponent(query)}&page=${page}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://www.pornhub.com'
        $('ul.gifs.gifLink > li.gifVideoBlock').each((_, element) => {
            const item = $(element)
            const link = item.find('a').first()
            const gifPageUrl = makeAbsolute(link.attr('href'), baseUrl)
            const gifId = item.attr('data-gif-id') || gifPageUrl?.match(/\/view_gif\/(\d+)/)?.[1]
            const title = link.attr('alt') || item.find('.gif-title').text().trim() || 'Untitled GIF'
            const videoPreview = item.find('video.gifVideo')
            const animatedGifUrl = makeAbsolute(videoPreview.attr('data-mp4') || videoPreview.attr('data-webm') || link.data('mp4'), baseUrl)
            const staticThumbnailUrl = makeAbsolute(item.find('img').attr('data-src') || item.find('img').attr('src'), baseUrl)
            if (gifPageUrl && title && animatedGifUrl && gifId) {
                results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: 'Pornhub', type: 'gifs' })
            }
        })
        return results
    }
}
const xvideos = {
    name: 'XVideos',
    videoUrl: (query, page) => `https://www.xvideos.com/?k=${encodeURIComponent(query.replace(/\s+/g, '+'))}&p=${page > 1 ? page - 1 : 0}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://www.xvideos.com'
        $('div.thumb-block').each((_, element) => {
            const item = $(element)
            const videoId = item.attr('data-id')
            if (!videoId)
                return
            const titleBlock = item.find('p.title a').first()
            const videoUrl = makeAbsolute(titleBlock.attr('href'), baseUrl)
            const title = titleBlock.attr('title') || titleBlock.text().trim()
            const imgBlock = item.find('.thumb-inside img').first()
            const thumbnail = makeAbsolute(imgBlock.attr('data-src') || imgBlock.attr('src'), baseUrl)
            const duration = item.find('span.duration').text().trim()
            const preview_video = makeAbsolute(item.find('.thumb-inside > .thumb > a').attr('data-videopreview') || imgBlock.attr('data-videopreview'), baseUrl)
            if (videoUrl && title && thumbnail) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'XVideos', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://www.xvideos.com/gifs-best/${encodeURIComponent(query)}/${page > 1 ? `d-${page - 1}` : ''}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://www.xvideos.com'
        $('.gif-card').each((_, element) => {
            const item = $(element)
            const link = item.find('a').first()
            const gifPageUrl = makeAbsolute(link.attr('href'), baseUrl)
            const gifId = gifPageUrl?.match(/\/gif\/(.+?)\//)?.[1] || item.data('id')
            const title = item.find('p.gif-title').text().trim() || 'Untitled GIF'
            const img = item.find('img').first()
            const animatedGifUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            if (gifPageUrl && title && animatedGifUrl && gifId) {
                results.push({ id: String(gifId), title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'XVideos', type: 'gifs' })
            }
        })
        return results
    }
}
const redtube = {
    name: 'Redtube',
    videoUrl: (query, page) => `https://www.redtube.com/?search=${encodeURIComponent(query)}&page=${page}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://www.redtube.com'
        $('div.video_item_wrapper, [data-id*="video_"]').each((_, element) => {
            const item = $(element)
            const videoId = item.attr('data-id') || item.attr('id')?.replace('video_', '')
            const link = item.find('a.video_link').first()
            const videoUrl = makeAbsolute(link.attr('href'), baseUrl)
            const title = item.find('.video_title').text().trim()
            const img = item.find('img.video_thumb, img').first()
            const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            const duration = item.find('.video_duration').text().trim()
            const preview_video = makeAbsolute(item.attr('data-preview'), baseUrl)
            if (videoUrl && title && thumbnail && videoId) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Redtube', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://www.redtube.com/gifs/search?search=${encodeURIComponent(query)}&page=${page}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://www.redtube.com'
        $('.gif_item_wrapper, [data-id*="gif_"]').each((_, element) => {
            const item = $(element)
            const gifId = item.attr('data-id')?.replace('gif_', '')
            const link = item.find('a.gif_link').first()
            const gifPageUrl = makeAbsolute(link.attr('href'), baseUrl)
            const title = link.find('.gif_title').text().trim() || 'Untitled GIF'
            const img = item.find('img.gif_thumb, img').first()
            const staticThumbnailUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            const animatedGifUrl = makeAbsolute(item.attr('data-preview'), baseUrl)
            if (gifPageUrl && title && gifId && (staticThumbnailUrl || animatedGifUrl)) {
                results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: 'Redtube', type: 'gifs' })
            }
        })
        return results
    }
}
const sex = {
    name: 'Sex.com',
    videoUrl: (query, page) => `https://www.sex.com/search/videos?query=${encodeURIComponent(query)}&page=${page}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://www.sex.com'
        $('div[id^="video-item-"]').each((_, element) => {
            const item = $(element)
            const videoId = item.attr('id')?.replace('video-item-', '')
            const link = item.find('a[href*="/video/"]').first()
            const videoUrl = makeAbsolute(link.attr('href'), baseUrl)
            const title = item.find('.title').text().trim()
            const img = item.find('img').first()
            const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            const duration = item.find('.duration').text().trim()
            const preview_video = makeAbsolute(item.attr('data-preview-video-url'), baseUrl)
            if (videoUrl && title && thumbnail && videoId) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video: preview_video, source: 'Sex.com', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://www.sex.com/search/gifs?query=${encodeURIComponent(query)}&page=${page}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://www.sex.com'
        $('div[id^="gif-item-"]').each((_, element) => {
            const item = $(element)
            const gifId = item.attr('id')?.replace('gif-item-', '')
            const link = item.find('a[href*="/gif/"]').first()
            const gifPageUrl = makeAbsolute(link.attr('href'), baseUrl)
            const img = item.find('img').first()
            const title = img.attr('alt') || 'Untitled GIF'
            const animatedGifUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            if (gifPageUrl && title && animatedGifUrl && gifId) {
                results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'Sex.com', type: 'gifs' })
            }
        })
        return results
    }
}
const xhamster = {
    name: 'xHamster',
    videoUrl: (query, page) => `https://xhamster.com/search/${encodeURIComponent(query)}?page=${page}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://xhamster.com'
        $('div.video-item').each((_, element) => {
            const item = $(element)
            const link = item.find('a.video-title').first()
            const videoUrl = makeAbsolute(link.attr('href'), baseUrl)
            const videoId = videoUrl?.split('/').pop()?.split('-').pop()
            const title = link.text().trim()
            const img = item.find('img').first()
            const thumbnail = makeAbsolute(img.attr('src'), baseUrl)
            const duration = '' // Not available on search page
            if (videoUrl && title && thumbnail && videoId) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video: thumbnail, source: 'xHamster', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://xhamster.com/gifs/search/${encodeURIComponent(query)}?page=${page}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://xhamster.com'
        $('a.gif-thumb__thumb-container, .thumb-list__item a[href*="/gifs/"]').each((_, element) => {
            const item = $(element)
            const gifPageUrl = makeAbsolute(item.attr('href'), baseUrl)
            const gifId = gifPageUrl?.split('/').pop()
            const img = item.find('img.gif-thumb__image, .thumb-list__item-img')
            const title = img.attr('alt') || 'Untitled GIF'
            const staticThumbnailUrl = makeAbsolute(img.attr('src') || img.attr('data-src'), baseUrl)
            const animatedGifUrl = makeAbsolute(item.attr('data-preview-url') || item.find('video').attr('src') || staticThumbnailUrl, baseUrl)
            if (gifPageUrl && title && gifId && (staticThumbnailUrl || animatedGifUrl)) {
                results.push({ id: gifId, title, url: gifPageUrl, thumbnail: staticThumbnailUrl, preview_video: animatedGifUrl, source: 'xHamster', type: 'gifs' })
            }
        })
        return results
    }
}
const youporn = {
    name: 'YouPorn',
    videoUrl: (query, page) => `https://www.youporn.com/search/?query=${encodeURIComponent(query)}&page=${page}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://www.youporn.com'
        $('.video-list-item').each((_, element) => {
            const container = $(element)
            const videoId = container.attr('id')?.replace('video-list-item-', '')
            const link = container.find('a').first()
            const videoUrl = makeAbsolute(link.attr('href'), baseUrl)
            const title = container.find('.video-title, .video-box-title').text().trim()
            const img = container.find('img.video-thumb, img.contain-image').first()
            const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            const duration = container.find('.video-duration').text().trim()
            const preview_video = makeAbsolute(container.find('.video-preview').attr('data-preview') || img.attr('data-preview'), baseUrl)
            if (videoUrl && title && thumbnail && videoId) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'YouPorn', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://www.youporn.com/search/gifs/?query=${encodeURIComponent(query)}&page=${page}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://www.youporn.com'
        $('.gif-list-item').each((_, element) => {
            const container = $(element)
            const gifId = container.attr('id')?.replace('gif-list-item-', '')
            const link = container.find('a').first()
            const gifPageUrl = makeAbsolute(link.attr('href'), baseUrl)
            const title = container.find('.gif-title').text().trim() || 'Untitled GIF'
            const img = container.find('img.gif-thumb').first()
            const animatedGifUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            if (gifPageUrl && title && animatedGifUrl && gifId) {
                results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'YouPorn', type: 'gifs' })
            }
        })
        return results
    }
}
const wow = {
    name: 'Wow.xxx',
    videoUrl: (query, page) => `https://www.wow.xxx/search/?q=${encodeURIComponent(query)}${page > 1 ? `&page=${page}` : ''}`,
    videoParser: ($) => {
        const results = []
        const baseUrl = 'https://www.wow.xxx'
        $('div.card-video').each((_, element) => {
            const item = $(element)
            const link = item.find('a').first()
            const videoUrl = makeAbsolute(link.attr('href'), baseUrl)
            const videoId = videoUrl?.match(/video\/(.+?)\/$/)?.[1]
            const title = item.find('h5.card-video__title').text().trim()
            const img = item.find('img').first()
            const thumbnail = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            const duration = item.find('div.card-video__duration').text().trim()
            const preview_video = makeAbsolute(img.attr('data-preview'), baseUrl)
            if (videoUrl && title && thumbnail && videoId) {
                results.push({ id: videoId, title, url: videoUrl, duration, thumbnail, preview_video, source: 'Wow.xxx', type: 'videos' })
            }
        })
        return results
    },
    gifUrl: (query, page) => `https://www.wow.xxx/search/gifs/?q=${encodeURIComponent(query)}${page > 1 ? `&page=${page}` : ''}`,
    gifParser: ($) => {
        const results = []
        const baseUrl = 'https://www.wow.xxx'
        $('div.card-gif').each((_, element) => {
            const item = $(element)
            const link = item.find('a').first()
            const gifPageUrl = makeAbsolute(link.attr('href'), baseUrl)
            const gifId = gifPageUrl?.match(/\/gif\/(.+?)\/$/)?.[1]
            const img = item.find('img').first()
            const title = img.attr('alt') || 'Untitled GIF'
            const animatedGifUrl = makeAbsolute(img.attr('data-src') || img.attr('src'), baseUrl)
            if (gifPageUrl && title && animatedGifUrl && gifId) {
                results.push({ id: gifId, title, url: gifPageUrl, thumbnail: animatedGifUrl, preview_video: animatedGifUrl, source: 'Wow.xxx', type: 'gifs' })
            }
        })
        return results
    }
}
const mock = {
    name: 'Mock',
    videoUrl: (query, page) => `http://mock.com/videos?q=${query}&page=${page}`,
    videoParser: (input) => {
        return Array.from({ length: 10 }, (_, i) => ({
            id: `mock-video-${i}-${Date.now()}`,
            title: `Mock Video ${input.query} - Page ${input.page} - Item ${i + 1}`,
            url: `http://mock.com/video/${i}`,
            duration: '0:30',
            thumbnail: `https://placehold.co/320x180/6353F2/FFFFFF?text=Mock+Video+${i + 1}`,
            preview_video: `https://www.w3schools.com/html/mov_bbb.mp4`,
            source: 'Mock',
            type: 'videos',
        }))
    },
    gifUrl: (query, page) => `http://mock.com/gifs?q=${query}&page=${page}`,
    gifParser: (input) => {
        return Array.from({ length: 10 }, (_, i) => ({
            id: `mock-gif-${i}-${Date.now()}`,
            title: `Mock GIF ${input.query} - Page ${input.page} - Item ${i + 1}`,
            url: `http://mock.com/gif/${i}`,
            thumbnail: `https://placehold.co/320x180/BE52F2/FFFFFF?text=Mock+GIF+${i + 1}`,
            preview_video: `https://i.giphy.com/media/VbnUQpnihPSIgIXuZv/giphy.gif`,
            source: 'Mock',
            type: 'gifs'
        }))
    }
}
const drivers = { pornhub, xvideos, redtube, sex, xhamster, youporn, 'wow.xxx': wow, mock }
async function getDrivers() {
    return Object.keys(drivers)
}
async function search(input) {
    const { query, driver: driverName, type, page } = input
    const driver = drivers[driverName.toLowerCase()]
    if (!driver) {
        throw new Error(`Unsupported driver: ${driverName}.`)
    }
    const isVideos = type === 'videos'
    const urlFn = isVideos ? driver.videoUrl : driver.gifUrl
    const parserFn = isVideos ? driver.videoParser : driver.gifParser
    if (!urlFn || !parserFn) {
        throw new Error(`Driver ${driverName} does not support type '${type}'.`)
    }
    if (driverName.toLowerCase() === 'mock') {
        const mockParser = isVideos ? driver.videoParser : driver.gifParser
        return mockParser(input)
    }
    const url = urlFn(query, page)
    try {
        const response = await axios_1.default.get(url, {
            timeout: 30000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            }
        })
        const $ = cheerio.load(response.data)
        const results = parserFn($)
        if (results.length === 0) {
            console.warn(`No results found for ${driver.name} with query "${query}" on page ${page}. The site structure might have changed.`)
        }
        return results
    }
    catch (error) {
        console.error(`Error fetching from ${driver.name}: ${error.message}`)
        if (error.response?.status === 404) {
            return []
        }
        throw new Error(`Failed to fetch results from ${driver.name}. The site may be down or has changed its structure.`)
    }
}
// --- AI Selector Suggestion Flow ---
const SelectorSuggestionOutputSchema = zod_1.z.object({
    reasoning: zod_1.z.string().describe("An explanation of why the selectors might have failed and how the new suggestions were derived."),
    suggestedCode: zod_1.z.string().describe("The complete, updated Javascript code block for the parser function (e.g., `videoParser` or `gifParser`)."),
})
const suggestSelectorsFlow = genkit_1.ai.defineFlow({
    name: 'suggestSelectorsFlow',
    inputSchema: zod_1.z.object({
        driverName: zod_1.z.string(),
        type: zod_1.z.enum(['videos', 'gifs']),
        htmlContent: zod_1.z.string(),
    }),
    outputSchema: SelectorSuggestionOutputSchema,
}, async ({ driverName, type, htmlContent }) => {
    const driver = drivers[driverName.toLowerCase()]
    if (!driver) {
        throw new Error(`Invalid driver name: ${driverName}`)
    }
    const parserFn = type === 'videos' ? driver.videoParser : driver.gifParser
    const currentCode = parserFn.toString()
    const prompt = `
      You are an expert web scraping engineer. A scraper for the site "${driverName}" has failed, likely due to a website update.
      Your task is to analyze the provided HTML snippet and the current (broken) parser function to suggest updated Javascript code.

      **Current Parser Function (${type})**:
      \`\`\`javascript
      ${currentCode}
      \`\`\`

      **HTML Snippet from the search results page**:
      \`\`\`html
      ${htmlContent.substring(0, 8000)}
      \`\`\`

      **Instructions**:
      1.  **Analyze the HTML**: Carefully examine the provided HTML to identify the new structure for media items. Find the main container for each video/gif item.
      2.  **Identify Key Data Points**: Within each item, find the new CSS selectors for:
          *   Title
          *   URL (the link to the media's own page)
          *   Thumbnail Image (prefer higher quality sources like 'data-src' or 'data-thumb_url' over 'src')
          *   Video Duration (if applicable)
          *   Preview Video (if available)
          *   A unique ID for the item.
      3.  **Generate New Code**: Rewrite the entire parser function with the updated selectors. The function should take a Cheerio object ($) as input and return an array of MediaItem objects.
      4.  **Be Thorough**: Ensure all fields in the \`MediaItem\` are populated correctly. Use \`makeAbsolute(url, baseUrl)\` for all URLs.
      5.  **Provide Reasoning**: Explain what changed and why your new selectors will work.

      Return your response in the specified JSON format. The 'suggestedCode' should be a single string containing the complete, ready-to-use Javascript function.
    `
    const { output } = await genkit_1.ai.generate({
        prompt,
        model: 'googleai/gemini-1.5-flash-latest',
        output: { schema: SelectorSuggestionOutputSchema },
    })
    return output
})
async function suggestSelectors(input) {
    const { driver: driverName, type, query } = input
    const driver = drivers[driverName.toLowerCase()]
    if (!driver || driverName.toLowerCase() === 'mock') {
        throw new Error(`Cannot generate suggestions for this driver: ${driverName}`)
    }
    const urlFn = type === 'videos' ? driver.videoUrl : driver.gifUrl
    const url = urlFn(query, 1)
    try {
        const response = await axios_1.default.get(url, {
            timeout: 30000,
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        })
        const result = await suggestSelectorsFlow({
            driverName,
            type,
            htmlContent: response.data,
        })
        return result
    }
    catch (error) {
        console.error(`AI suggestion failed for ${driverName}:`, error)
        throw new Error(`Failed to generate AI suggestions for ${driverName}. Error: ${error.message}`)
    }
}
