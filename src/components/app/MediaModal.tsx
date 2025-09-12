
'use client';

import React, { useEffect, useRef, useState } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { downloadMedia } from '@/app/actions';
import type { MediaItem } from '@/ai/types';
import { Download, Loader2 } from 'lucide-react';

interface MediaModalProps {
  item: MediaItem;
  isOpen: boolean;
  onClose: () => void;
}

const MediaModal: React.FC<MediaModalProps> = ({ item, isOpen, onClose }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (!isOpen && videoRef.current) {
      videoRef.current.pause();
    }
  }, [isOpen]);

  const handleDownload = async () => {
    const urlToDownload = item.preview_video || item.thumbnail;
    if (!urlToDownload) {
      toast({
        variant: 'destructive',
        title: 'Download Failed',
        description: 'No media URL found for this item.',
      });
      return;
    }

    setIsDownloading(true);

    try {
      const result = await downloadMedia(urlToDownload);

      if ('error' in result) {
        throw new Error(result.error);
      }

      const { data, contentType } = result;
      const extension = contentType.split('/')[1] || 'mp4';
      const fileName = `${item.title.replace(/[^a-zA-Z0-9]/g, '_')}.${extension}`;

      const link = document.createElement('a');
      link.href = `data:${contentType};base64,${data}`;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast({
        title: 'Download Started',
        description: `Saving "${fileName}" to your device.`,
      });

    } catch (err: any) {
      toast({
        variant: 'destructive',
        title: 'Download Failed',
        description: err.message || 'An unexpected error occurred.',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const isVideo = item.type === 'videos' || item.preview_video?.endsWith('.mp4') || item.preview_video?.endsWith('.webm');

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl w-full p-0 bg-card/80 backdrop-blur-lg border-primary/30 shadow-2xl shadow-primary/20">
        <DialogTitle className="sr-only">{item.title}</DialogTitle>
        <div className="aspect-video w-full bg-black flex items-center justify-center">
          {isVideo ? (
            <video
              ref={videoRef}
              src={item.preview_video || item.url}
              controls
              autoPlay
              className="w-full h-full object-contain"
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            item.preview_video || item.thumbnail ? (
              <Image
                src={item.preview_video || item.thumbnail || ''}
                alt={item.title}
                fill
                objectFit="contain"
                unoptimized
                className="w-full h-full"
              />
            ) : <p className="text-destructive">Media not available</p>
          )}
        </div>
        <div className="p-4 sm:p-6 border-t border-border flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-lg font-semibold text-foreground truncate flex-1 text-center sm:text-left">{item.title}</p>
          <div className="flex items-center gap-2">
            <Button onClick={handleDownload} variant="outline" disabled={isDownloading}>
              {isDownloading ? (
                <Loader2 className="animate-spin" />
              ) : (
                <Download />
              )}
              Save to device
            </Button>
            <Button asChild variant="secondary">
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                View on {item.source}
              </a>
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MediaModal;
