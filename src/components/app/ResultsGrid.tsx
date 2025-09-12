
'use client';

import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import NeonCard from './NeonCard';
import type { MediaItem } from '@/ai/types';
import { Frown } from 'lucide-react';

interface ResultsGridProps {
  items: MediaItem[];
  isLoading: boolean;
  isFavoritesView: boolean;
  isFavorite: (item: MediaItem) => boolean;
  toggleFavorite: (item: MediaItem) => void;
  openModal: (item: MediaItem) => void;
  hasSearched: boolean;
}

const ResultsGrid: React.FC<ResultsGridProps> = ({
  items,
  isLoading,
  isFavoritesView,
  isFavorite,
  toggleFavorite,
  openModal,
  hasSearched
}) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-72">
            <Skeleton className="h-48 w-full" />
            <div className="space-y-2 mt-4">
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-4 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    let message = "Enter a search to see results.";
    if (isFavoritesView) {
      message = "You haven't saved any favorites yet.";
    } else if (hasSearched) {
      message = "No results found. The site may be broken.";
    }

    return (
      <div className="text-center py-16 flex flex-col items-center justify-center gap-4">
        <Frown className="w-16 h-16 text-muted-foreground/50" />
        <p className="text-xl text-muted-foreground">
          {message}
        </p>
         {hasSearched && !isFavoritesView && (
          <p className="text-sm text-muted-foreground">Try using the AI Scraper Repair tool in the settings.</p>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
      {items.map((item, index) => (
        <NeonCard
          key={`${item.id}-${item.source}-${index}`}
          item={item}
          isFavorite={isFavorite}
          toggleFavorite={toggleFavorite}
        />
      ))}
    </div>
  );
};

export default ResultsGrid;

    