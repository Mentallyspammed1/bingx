'use client';

import { useState, useEffect, useCallback } from 'react';
import { search } from '@/ai/flows/search-flow';
import type { SearchInput, SearchOutput, MediaItem } from '@/ai/types';

import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import SearchForm from '@/components/app/SearchForm';
import ResultsGrid from '@/components/app/ResultsGrid';
import MediaModal from '@/components/app/MediaModal';
import Header from '@/components/app/Header';

const FAVORITES_STORAGE_KEY = 'neonSearchFavorites';

export default function Home() {
  const [searchParams, setSearchParams] = useState<Omit<SearchInput, 'page'>>({
    query: '',
    driver: 'redtube',
    type: 'videos',
  });
  const [results, setResults] = useState<MediaItem[]>([]);
  const [favorites, setFavorites] = useState<MediaItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const [isFavoritesView, setIsFavoritesView] = useState(false);

  const { toast } = useToast();

  useEffect(() => {
    try {
      const storedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
      if (storedFavorites) {
        setFavorites(JSON.parse(storedFavorites));
      }
    } catch (e) {
      console.error('Failed to load favorites from localStorage', e);
      toast({
        variant: 'destructive',
        title: 'Error loading favorites',
        description: 'Could not load your saved favorites from local storage.',
      });
    }
  }, [toast]);

  const saveFavorites = (newFavorites: MediaItem[]) => {
    setFavorites(newFavorites);
    try {
      localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(newFavorites));
    } catch (e) {
      console.error('Failed to save favorites to localStorage', e);
      toast({
        variant: 'destructive',
        title: 'Error saving favorites',
        description: 'Your favorites could not be saved.',
      });
    }
  };

  const performSearch = useCallback(async (searchPage: number, newSearch = false) => {
      if (!searchParams.query.trim()) {
        toast({
          variant: 'destructive',
          title: 'Search query is empty',
          description: 'Please enter something to search for.',
        });
        return;
      }
      setIsLoading(true);
      if (newSearch) {
        setResults([]);
        setHasMore(true);
      }

      try {
        const searchInput: SearchInput = { ...searchParams, page: searchPage };
        const res = await search(searchInput);
        
        if (newSearch) {
          setResults(res);
        } else {
          setResults(prev => [...prev, ...res]);
        }
        setHasMore(res.length > 0);
      } catch (err: any) {
        console.error(err);
        toast({
          variant: 'destructive',
          title: 'Search Failed',
          description: err.message || 'An unexpected error occurred.',
        });
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    },
    [searchParams, toast]
  );

  const handleSearchSubmit = () => {
    setPage(1);
    performSearch(1, true);
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    performSearch(nextPage, false);
  };

  const isFavorite = useCallback((item: MediaItem) => {
    return favorites.some(fav => fav.url === item.url);
  }, [favorites]);

  const toggleFavorite = useCallback((item: MediaItem) => {
    const newFavorites = isFavorite(item)
      ? favorites.filter(fav => fav.url !== item.url)
      : [...favorites, item];
    saveFavorites(newFavorites);
  }, [favorites, isFavorite]);

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <Header />
      
      <div className="bg-card/50 backdrop-blur-sm border border-primary/20 p-6 sm:p-8 rounded-2xl shadow-2xl shadow-primary/10">
        <SearchForm
          searchParams={searchParams}
          setSearchParams={setSearchParams}
          onSubmit={handleSearchSubmit}
          isLoading={isLoading}
          isFavoritesView={isFavoritesView}
          setIsFavoritesView={setIsFavoritesView}
          favoritesCount={favorites.length}
        />
      </div>

      <main className="mt-8">
        <ResultsGrid
          items={isFavoritesView ? favorites : results}
          isLoading={isLoading}
          isFavoritesView={isFavoritesView}
          isFavorite={isFavorite}
          toggleFavorite={toggleFavorite}
          openModal={setSelectedItem}
        />
        {!isFavoritesView && hasMore && results.length > 0 && !isLoading && (
          <div className="w-full flex justify-center mt-8">
            <Button onClick={handleLoadMore} variant="secondary" size="lg" disabled={isLoading}>
              {isLoading ? 'Loading...' : 'Load More'}
            </Button>
          </div>
        )}
      </main>

      {selectedItem && (
        <MediaModal
          item={selectedItem}
          isOpen={!!selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}
    </div>
  );
}
