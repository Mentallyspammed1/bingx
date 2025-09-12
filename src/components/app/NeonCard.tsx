'use client';

import React, { useRef, useState } from 'react';
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
}

const NeonCard: React.FC<NeonCardProps> = ({ item, isFavorite, toggleFavorite }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      if (item.preview_video && videoRef.current) {
        const video = videoRef.current;
        video.currentTime = 0;
        const playPromise = video.play();
        if (playPromise !== undefined) {
          playPromise.then(() => {
            setIsPlaying(true);
          }).catch(error => {
             setIsPlaying(false);
          });
        }
      }
    }, 150); 
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (videoRef.current) {
      const video = videoRef.current;
      video.pause();
      video.currentTime = 0;
      setIsPlaying(false);
    }
  };

  const handleCardClick = () => {
    if (item.url) {
      window.open(item.url, '_blank', 'noopener,noreferrer');
    }
  };

  const favorite = isFavorite(item);

  return (
    <Card
      onClick={handleCardClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group relative overflow-hidden rounded-lg shadow-lg transition-all duration-300 ease-in-out cursor-pointer h-72 flex flex-col bg-card hover:shadow-primary/40 hover:border-primary/50 hover:-translate-y-1"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleCardClick()}
    >
      <CardContent className="relative p-0 h-48 flex-shrink-0 bg-black">
        {item.thumbnail && (
          <Image
            src={item.thumbnail}
            alt={item.title}
            layout="fill"
            objectFit="cover"
            unoptimized
            className={cn(
              "transition-opacity duration-300",
              isPlaying ? "opacity-0" : "opacity-100"
            )}
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
            className={cn(
              "absolute inset-0 w-full h-full object-cover transition-opacity duration-300",
              isPlaying ? "opacity-100" : "opacity-0"
            )}
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
