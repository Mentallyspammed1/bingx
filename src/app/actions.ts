
'use server';

import axios from 'axios';

export async function downloadMedia(url: string): Promise<{ data: string; contentType: string; } | { error: string }> {
  if (!url) {
    return { error: 'No URL provided.' };
  }

  try {
    const response = await axios.get(url, {
      responseType: 'arraybuffer', // Important for binary data
      timeout: 30000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': new URL(url).origin, // Some sites require a referer
      },
    });

    if (response.status !== 200) {
      return { error: `Failed to fetch media. Status: ${response.status}` };
    }

    const contentType = response.headers['content-type'] || 'application/octet-stream';
    const data = Buffer.from(response.data, 'binary').toString('base64');

    return { data, contentType };
  } catch (error: any) {
    console.error(`Error downloading media from ${url}:`, error.message);
    return { error: 'Could not download the media file. The source might be blocking direct downloads.' };
  }
}
