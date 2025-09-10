'use client';

import React from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import NeonCard from './NeonCard';
import type { MediaItem } from '@/ai/types';

interface ResultsGridProps {
  items: MediaItem[];
  isLoading: boolean;
  isFavoritesView: boolean;
  isFavorite: (item: MediaItem) => boolean;
  toggleFavorite: (item: MediaItem) => void;
  openModal: (item: MediaItem) => void;
}

const ResultsGrid: React.FC<ResultsGridProps> = ({
  items,
  isLoading,
  isFavoritesView,
  isFavorite,
  toggleFavorite,
  openModal,
}) => {
  if (isLoading && items.length === 0) {
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
    return (
      <div className="text-center py-16">
        <p className="text-xl text-muted-foreground">
          {isFavoritesView ? "You haven't saved any favorites yet." : "Enter a search to see results."}
        </p>
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
          openModal={openModal}
        />
      ))}
    </div>
  );
};

export default ResultsGrid;
