'use client';

import React, { useRef } from 'react';
import Image from 'next/image';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MediaItem } from '@/ai/types';

interface NeonCardProps {
  item: MediaItem;
  isFavorite: (item: MediaItem) => boolean;
  toggleFavorite: (item: MediaItem) => void;
  openModal: (item: MediaItem) => void;
}

const NeonCard: React.FC<NeonCardProps> = ({ item, isFavorite, toggleFavorite, openModal }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    if (item.preview_video && videoRef.current) {
        if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
        
        videoRef.current.currentTime = 0;
        const playPromise = videoRef.current.play();

        if (playPromise !== undefined) {
            playPromise.catch(error => {
                if (error.name !== 'AbortError') {
                    console.error('Preview video play failed:', error);
                }
            });
        }
    }
  };

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.pause();
    }
  };

  const favorite = isFavorite(item);

  return (
    <Card
      onClick={() => openModal(item)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group relative overflow-hidden rounded-lg shadow-lg transition-all duration-300 ease-in-out cursor-pointer h-72 flex flex-col bg-card hover:shadow-primary/40 hover:border-primary/50 hover:-translate-y-1"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && openModal(item)}
    >
      <CardContent className="relative p-0 h-48 flex-shrink-0 bg-black">
        {item.thumbnail && (
          <Image
            src={item.thumbnail}
            alt={item.title}
            layout="fill"
            objectFit="cover"
            unoptimized
            className="transition-opacity duration-300 group-hover:opacity-10"
            onError={(e) => (e.currentTarget.style.display = 'none')}
          />
        )}
        {item.preview_video && (
          <video
            ref={videoRef}
            src={item.preview_video}
            muted
            loop
            playsInline
            preload="auto"
            className="absolute inset-0 w-full h-full object-cover opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          ></video>
        )}
        {item.duration && (
          <span className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded-md">
            {item.duration}
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "absolute top-2 right-2 z-10 text-white/70 hover:text-white bg-black/30 hover:bg-black/50 rounded-full h-8 w-8 transition-all",
            favorite && "text-primary hover:text-primary/80"
          )}
          onClick={(e) => {
            e.stopPropagation();
            toggleFavorite(item);
          }}
          aria-label={favorite ? "Remove from favorites" : "Add to favorites"}
        >
          <Star className={cn("h-5 w-5", favorite ? "fill-current" : "")} />
        </Button>
      </CardContent>
      <CardFooter className="flex-grow p-4 flex flex-col items-start justify-between bg-card">
        <h3 className="font-semibold text-base text-foreground line-clamp-2">{item.title}</h3>
        <p className="text-sm text-secondary">{item.source}</p>
      </CardFooter>
    </Card>
  );
};

export default NeonCard;
