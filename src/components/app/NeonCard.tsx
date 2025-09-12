
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
  onClick: () => void;
}

const NeonCard: React.FC<NeonCardProps> = ({ item, isFavorite, toggleFavorite, onClick }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleMouseEnter = () => {
    if (!item.preview_video || !videoRef.current) return;
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(async () => {
      const video = videoRef.current;
      if (video) {
        video.currentTime = 0;
        try {
          await video.play();
          setIsPlaying(true);
        } catch (error) {
          console.error("Video play failed:", error);
          setIsPlaying(false);
        }
      }
    }, 150);
  };

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    const video = videoRef.current;
    if (video && !video.paused) {
      video.pause();
      video.currentTime = 0;
      setIsPlaying(false);
    }
  };
  
  const favorite = isFavorite(item);

  return (
    <Card
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className="group relative overflow-hidden rounded-lg shadow-lg transition-all duration-300 ease-in-out h-72 flex flex-col bg-card hover:shadow-primary/40 hover:border-primary/50 hover:-translate-y-1"
    >
      <CardContent 
        onClick={onClick}
        className="relative p-0 h-48 flex-shrink-0 bg-black cursor-pointer"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && onClick()}
        role="button"
        aria-label={`View details for ${item.title}`}
      >
        {item.thumbnail && (
          <Image
            src={item.thumbnail}
            alt={item.title}
            fill
            sizes="(max-width: 640px) 100vw, (max-width: 768px) 50vw, (max-width: 1024px) 33vw, 25vw"
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
            preload="none"
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
            e.stopPropagation(); // Prevent card's onClick from firing
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
