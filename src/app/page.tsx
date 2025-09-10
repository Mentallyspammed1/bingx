'use client';

import { useEffect, useReducer, useCallback } from 'react';
import { search } from '@/ai/flows/search-flow';
import type { SearchInput, MediaItem } from '@/ai/types';

import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import SearchForm from '@/components/app/SearchForm';
import ResultsGrid from '@/components/app/ResultsGrid';
import MediaModal from '@/components/app/MediaModal';
import Header from '@/components/app/Header';
import SearchHistory from '@/components/app/SearchHistory';

const FAVORITES_STORAGE_KEY = 'neonSearchFavorites';
const HISTORY_STORAGE_KEY = 'neonSearchHistory';

type State = {
  searchParams: Omit<SearchInput, 'page'>;
  results: MediaItem[];
  favorites: MediaItem[];
  history: Omit<SearchInput, 'page'>[];
  isLoading: boolean;
  page: number;
  hasMore: boolean;
  selectedItem: MediaItem | null;
  isFavoritesView: boolean;
};

type Action =
  | { type: 'SET_SEARCH_PARAMS'; payload: Partial<Omit<SearchInput, 'page'>> }
  | { type: 'START_SEARCH' }
  | { type: 'SEARCH_SUCCESS'; payload: { results: MediaItem[], newSearch: boolean } }
  | { type: 'SEARCH_FAILURE' }
  | { type: 'LOAD_MORE' }
  | { type: 'SET_SELECTED_ITEM'; payload: MediaItem | null }
  | { type: 'TOGGLE_FAVORITES_VIEW'; payload: boolean }
  | { type: 'SET_FAVORITES'; payload: MediaItem[] }
  | { type: 'SET_HISTORY'; payload: Omit<SearchInput, 'page'>[] }
  | { type: 'ADD_TO_HISTORY'; payload: Omit<SearchInput, 'page'> }
  | { type: 'CLEAR_HISTORY' }
  | { type: 'SET_PAGE'; payload: number };


const initialState: State = {
  searchParams: { query: '', driver: 'redtube', type: 'videos' },
  results: [],
  favorites: [],
  history: [],
  isLoading: false,
  page: 1,
  hasMore: true,
  selectedItem: null,
  isFavoritesView: false,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_SEARCH_PARAMS':
      return { ...state, searchParams: { ...state.searchParams, ...action.payload } };
    case 'START_SEARCH':
      return { ...state, isLoading: true, page: 1, results: [], hasMore: true };
    case 'SEARCH_SUCCESS':
      return { 
        ...state, 
        isLoading: false, 
        results: action.payload.newSearch ? action.payload.results : [...state.results, ...action.payload.results],
        hasMore: action.payload.results.length > 0,
        page: action.payload.newSearch ? 1 : state.page,
      };
    case 'SEARCH_FAILURE':
      return { ...state, isLoading: false, results: [] };
    case 'LOAD_MORE':
      return { ...state, page: state.page + 1, isLoading: true };
    case 'SET_SELECTED_ITEM':
      return { ...state, selectedItem: action.payload };
    case 'TOGGLE_FAVORITES_VIEW':
      return { ...state, isFavoritesView: action.payload };
    case 'SET_FAVORITES':
      return { ...state, favorites: action.payload };
    case 'SET_HISTORY':
      return { ...state, history: action.payload };
    case 'ADD_TO_HISTORY':
      const newHistory = [action.payload, ...state.history.filter(h => h.query !== action.payload.query || h.driver !== action.payload.driver || h.type !== action.payload.type)].slice(0, 10);
      try {
        localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(newHistory));
      } catch (e) {
        console.error('Failed to save history', e);
      }
      return { ...state, history: newHistory };
    case 'CLEAR_HISTORY':
      try {
        localStorage.removeItem(HISTORY_STORAGE_KEY);
      } catch (e) {
        console.error('Failed to clear history', e);
      }
      return { ...state, history: [] };
    case 'SET_PAGE':
      return { ...state, page: action.payload, isLoading: true };
    default:
      return state;
  }
}

export default function Home() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { searchParams, results, favorites, history, isLoading, page, hasMore, selectedItem, isFavoritesView } = state;
  const { toast } = useToast();

  useEffect(() => {
    try {
      const storedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
      if (storedFavorites) {
        dispatch({ type: 'SET_FAVORITES', payload: JSON.parse(storedFavorites) });
      }
      const storedHistory = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (storedHistory) {
        dispatch({ type: 'SET_HISTORY', payload: JSON.parse(storedHistory) });
      }
    } catch (e) {
      console.error('Failed to load from localStorage', e);
      toast({
        variant: 'destructive',
        title: 'Error loading data',
        description: 'Could not load your saved data from local storage.',
      });
    }
  }, [toast]);

  const saveFavorites = (newFavorites: MediaItem[]) => {
    dispatch({ type: 'SET_FAVORITES', payload: newFavorites });
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

  const performSearch = useCallback(async (params: Omit<SearchInput, 'page'>, searchPage: number, newSearch = false) => {
    if (!params.query.trim()) {
      toast({
        variant: 'destructive',
        title: 'Search query is empty',
        description: 'Please enter something to search for.',
      });
      return;
    }
    
    if (newSearch) {
        dispatch({ type: 'START_SEARCH' });
    } else {
        dispatch({ type: 'SET_PAGE', payload: searchPage });
    }

    if (newSearch) {
      dispatch({ type: 'ADD_TO_HISTORY', payload: params });
    }

    try {
      const searchInput: SearchInput = { ...params, page: searchPage };
      const res = await search(searchInput);
      
      dispatch({ type: 'SEARCH_SUCCESS', payload: { results: res, newSearch } });
    } catch (err: any) {
      console.error(err);
      toast({
        variant: 'destructive',
        title: 'Search Failed',
        description: err.message || 'An unexpected error occurred.',
      });
      dispatch({ type: 'SEARCH_FAILURE' });
    }
  }, [toast]);

  const handleSearchSubmit = () => {
    performSearch(searchParams, 1, true);
  };
  
  const handleHistorySearch = (historyItem: Omit<SearchInput, 'page'>) => {
    dispatch({ type: 'SET_SEARCH_PARAMS', payload: historyItem });
    performSearch(historyItem, 1, true);
  };

  const handleLoadMore = () => {
    performSearch(searchParams, page + 1, false);
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
          setSearchParams={(payload) => dispatch({ type: 'SET_SEARCH_PARAMS', payload })}
          onSubmit={handleSearchSubmit}
          isLoading={isLoading}
          isFavoritesView={isFavoritesView}
          setIsFavoritesView={(payload) => dispatch({ type: 'TOGGLE_FAVORITES_VIEW', payload })}
          favoritesCount={favorites.length}
        />
        <SearchHistory 
          history={history}
          onSearch={handleHistorySearch}
          onClear={() => dispatch({ type: 'CLEAR_HISTORY' })}
        />
      </div>

      <main className="mt-8">
        <ResultsGrid
          items={isFavoritesView ? favorites : results}
          isLoading={isLoading}
          isFavoritesView={isFavoritesView}
          isFavorite={isFavorite}
          toggleFavorite={toggleFavorite}
          openModal={(payload) => dispatch({ type: 'SET_SELECTED_ITEM', payload })}
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
          onClose={() => dispatch({ type: 'SET_SELECTED_ITEM', payload: null })}
        />
      )}
    </div>
  );
}
