'use client';

import React from 'react';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Search, X } from 'lucide-react';
import type { SearchInput } from '@/ai/types';

interface SearchFormProps {
  searchParams: Omit<SearchInput, 'page'>;
  setSearchParams: React.Dispatch<React.SetStateAction<Omit<SearchInput, 'page'>>>;
  onSubmit: () => void;
  isLoading: boolean;
  isFavoritesView: boolean;
  setIsFavoritesView: (isFavorites: boolean) => void;
  favoritesCount: number;
}

const SearchForm: React.FC<SearchFormProps> = ({
  searchParams,
  setSearchParams,
  onSubmit,
  isLoading,
  isFavoritesView,
  setIsFavoritesView,
  favoritesCount,
}) => {
  const handleInputChange = (key: keyof typeof searchParams, value: string) => {
    setSearchParams(prev => ({ ...prev, [key]: value }));
  };

  const handleClear = () => {
    setSearchParams(prev => ({ ...prev, query: '' }));
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
            disabled={isLoading}
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
              disabled={isLoading}
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
              disabled={isLoading}
            >
              <SelectTrigger className="h-12 text-base">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pornhub">Pornhub</SelectItem>
                <SelectItem value="sex">Sex.com</SelectItem>
                <SelectItem value="redtube">Redtube</SelectItem>
                <SelectItem value="xvideos">XVideos</SelectItem>
                <SelectItem value="xhamster">Xhamster</SelectItem>
                <SelectItem value="youporn">Youporn</SelectItem>
                <SelectItem value="wow.xxx">Wow.xxx</SelectItem>
                <SelectItem value="mock">Mock (Test)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        
        <Button type="submit" className="h-12 text-base font-bold" disabled={isLoading}>
          {isLoading ? 'Searching...' : 'Search'}
        </Button>
      </form>
      <div className="flex justify-center mt-6">
        <Button onClick={() => setIsFavoritesView(!isFavoritesView)} variant="outline" className="text-base">
          {isFavoritesView ? 'Back to Search' : `View Favorites (${favoritesCount})`}
        </Button>
      </div>
    </>
  );
};

export default SearchForm;
