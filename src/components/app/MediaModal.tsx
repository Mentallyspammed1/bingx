'use client';

import React, { useEffect, useRef } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import type { MediaItem } from '@/ai/types';

interface MediaModalProps {
  item: MediaItem;
  isOpen: boolean;
  onClose: () => void;
}

const MediaModal: React.FC<MediaModalProps> = ({ item, isOpen, onClose }) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!isOpen && videoRef.current) {
      videoRef.current.pause();
    }
  }, [isOpen]);

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
        <div className="p-4 sm:p-6 border-t border-border flex justify-between items-center">
          <p className="text-lg font-semibold text-foreground truncate flex-1 pr-4">{item.title}</p>
          <Button asChild variant="secondary">
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              View on {item.source}
            </a>
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default MediaModal;
