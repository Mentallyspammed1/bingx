
'use client';

import React from 'react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Search, X } from 'lucide-react';
import type { SearchInput } from '@/ai/types';

interface SearchFormProps {
  searchParams: Omit<SearchInput, 'page'>;
  setSearchParams: (params: Partial<Omit<SearchInput, 'page'>>) => void;
  onSubmit: () => void;
  isLoading: boolean;
  isFavoritesView: boolean;
  setIsFavoritesView: (isFavorites: boolean) => void;
  favoritesCount: number;
  drivers: string[];
}

const SearchForm: React.FC<SearchFormProps> = ({
  searchParams,
  setSearchParams,
  onSubmit,
  isLoading,
  isFavoritesView,
  setIsFavoritesView,
  favoritesCount,
  drivers
}) => {
  const handleInputChange = (key: keyof Omit<SearchInput, 'page'>, value: string) => {
    setSearchParams({ [key]: value });
  };

  const handleClear = () => {
    setSearchParams({ query: '' });
  };

  return (
    <>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end"
      >
        <div className="relative sm:col-span-2 lg:col-span-2">
          <label htmlFor="searchInput" className="sr-only">Search Query</label>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <Input
            id="searchInput"
            type="text"
            placeholder="Search for videos and GIFs..."
            className="pl-10 h-12 text-base"
            autoComplete="off"
            value={searchParams.query}
            onChange={(e) => handleInputChange('query', e.target.value)}
            disabled={isLoading || isFavoritesView}
          />
          {searchParams.query && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="absolute right-2 top-1/2 -translate-y-1/2 h-8 w-8 rounded-full"
              onClick={handleClear}
              aria-label="Clear search query"
            >
              <X className="h-5 w-5" />
            </Button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="typeSelect" className="sr-only">Type</label>
            <Select
              value={searchParams.type}
              onValueChange={(value) => handleInputChange('type', value)}
              disabled={isLoading || isFavoritesView}
            >
              <SelectTrigger className="h-12 text-base">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="videos">Videos</SelectItem>
                <SelectItem value="gifs">GIFs</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label htmlFor="driverSelect" className="sr-only">Source</label>
            <Select
              value={searchParams.driver}
              onValueChange={(value) => handleInputChange('driver', value)}
              disabled={isLoading || isFavoritesView}
            >
              <SelectTrigger className="h-12 text-base">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                 {drivers.map(driver => (
                  <SelectItem key={driver} value={driver.toLowerCase()}>
                    {driver === 'wow.xxx' ? 'Wow.xxx' : driver.charAt(0).toUpperCase() + driver.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <Button type="submit" className="h-12 text-base font-bold" disabled={isLoading || isFavoritesView}>
          {isLoading ? 'Searching...' : 'Search'}
        </Button>
      </form>
      <div className="flex justify-center mt-6">
        <Button onClick={() => setIsFavoritesView(!isFavoritesView)} variant="outline" className="text-base" disabled={isLoading}>
          {isFavoritesView ? 'Back to Search' : `View Favorites (${favoritesCount})`}
        </Button>
      </div>
    </>
  );
};

export default SearchForm;

    