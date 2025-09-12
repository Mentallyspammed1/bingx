
'use client';

import { useEffect, useReducer, useCallback } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { search, getDrivers } from '@/ai/flows/search-flow';
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
  drivers: string[];
};

type Action =
  | { type: 'SET_DRIVERS'; payload: string[] }
  | { type: 'SET_SEARCH_PARAMS'; payload: Partial<Omit<SearchInput, 'page'>> }
  | { type: 'START_SEARCH'; payload: { params: Omit<SearchInput, 'page'>; page: number } }
  | { type: 'APPEND_RESULTS'; payload: MediaItem[] }
  | { type: 'SET_RESULTS'; payload: MediaItem[] }
  | { type: 'SEARCH_FAILURE' }
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
  drivers: [],
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'SET_DRIVERS':
      return { ...state, drivers: action.payload };
    case 'SET_SEARCH_PARAMS':
      return { ...state, searchParams: { ...state.searchParams, ...action.payload } };
    case 'START_SEARCH':
      return {
        ...state,
        isLoading: true,
        page: action.payload.page,
        results: action.payload.page === 1 ? [] : state.results,
        hasMore: action.payload.page === 1 ? true : state.hasMore,
        isFavoritesView: false,
        searchParams: action.payload.params,
      };
    case 'APPEND_RESULTS':
      return {
        ...state,
        isLoading: false,
        results: [...state.results, ...action.payload],
        hasMore: action.payload.length > 0,
      };
    case 'SET_RESULTS':
       return {
        ...state,
        isLoading: false,
        results: action.payload,
        hasMore: action.payload.length > 0,
      };
    case 'SEARCH_FAILURE':
      return { ...state, isLoading: false, hasMore: false };
    case 'SET_SELECTED_ITEM':
      return { ...state, selectedItem: action.payload };
    case 'TOGGLE_FAVORITES_VIEW':
      return { ...state, isFavoritesView: action.payload, hasMore: !action.payload && state.results.length > 0 };
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
        return { ...state, page: action.payload };
    default:
      return state;
  }
}

export default function Home() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { searchParams, results, favorites, history, isLoading, page, hasMore, selectedItem, isFavoritesView, drivers } = state;
  const { toast } = useToast();
  
  const router = useRouter();
  const pathname = usePathname();
  const urlSearchParams = useSearchParams();

  useEffect(() => {
    async function fetchDrivers() {
        try {
            const driverNames = await getDrivers();
            dispatch({ type: 'SET_DRIVERS', payload: driverNames });
        } catch (error) {
            console.error('Failed to fetch drivers', error);
        }
    }
    fetchDrivers();
  }, []);

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
    }
  }, []);

  const performSearch = useCallback(async (params: Omit<SearchInput, 'page'>, searchPage: number) => {
    if (searchPage === 1 && params.query.trim()) {
        const currentParams = { query: params.query, driver: params.driver, type: params.type };
        dispatch({ type: 'ADD_TO_HISTORY', payload: currentParams });
    }

    dispatch({ type: 'START_SEARCH', payload: { params, page: searchPage } });

    try {
      const searchInput: SearchInput = { ...params, page: searchPage };
      const res = await search(searchInput);
      
      if (searchPage > 1) {
        dispatch({ type: 'APPEND_RESULTS', payload: res });
      } else {
        dispatch({ type: 'SET_RESULTS', payload: res });
      }
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

  useEffect(() => {
    const query = urlSearchParams.get('q');
    const driver = urlSearchParams.get('driver');
    const type = urlSearchParams.get('type');
    const pageNum = parseInt(urlSearchParams.get('page') || '1', 10);
    
    const newSearchParams: Omit<SearchInput, 'page'> = {
      query: query || '',
      driver: driver || 'redtube',
      type: (type === 'videos' || type === 'gifs') ? type : 'videos',
    };
    
    const isNewSearch = newSearchParams.query !== searchParams.query || newSearchParams.driver !== searchParams.driver || newSearchParams.type !== searchParams.type;

    if (query) {
       if (isNewSearch || pageNum !== page) {
         performSearch(newSearchParams, pageNum);
       }
    } else {
        if(results.length > 0) {
            dispatch({ type: 'SET_RESULTS', payload: [] });
        }
    }

    if (isNewSearch) {
        dispatch({ type: 'SET_SEARCH_PARAMS', payload: newSearchParams });
    }

  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSearchParams, performSearch]);


  const updateUrl = (params: Partial<Omit<SearchInput, 'page'>> & { page?: number }) => {
    const newUrlParams = new URLSearchParams(urlSearchParams.toString());
    if (params.query !== undefined) newUrlParams.set('q', params.query);
    if (params.driver !== undefined) newUrlParams.set('driver', params.driver);
    if (params.type !== undefined) newUrlParams.set('type', params.type);
    if (params.page !== undefined) newUrlParams.set('page', String(params.page));
    router.push(`${pathname}?${newUrlParams.toString()}`);
  };

  const handleSearchSubmit = () => {
    if (!searchParams.query.trim()) {
      toast({
        variant: 'destructive',
        title: 'Search query is empty',
        description: 'Please enter something to search for.',
      });
      return;
    }
    updateUrl({ ...searchParams, page: 1 });
  };
  
  const handleHistorySearch = (historyItem: Omit<SearchInput, 'page'>) => {
    updateUrl({ ...historyItem, page: 1 });
  };

  const handleLoadMore = () => {
    const newPage = page + 1;
    updateUrl({ page: newPage });
  };

  const isFavorite = useCallback((item: MediaItem) => {
    return favorites.some(fav => fav.url === item.url);
  }, [favorites]);
  
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

  const toggleFavorite = useCallback((item: MediaItem) => {
    const newFavorites = isFavorite(item)
      ? favorites.filter(fav => fav.url !== item.url)
      : [...favorites, item];
    saveFavorites(newFavorites);
  }, [favorites, isFavorite]);

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
      <Header />
      
      <div className="relative p-1 bg-gradient-to-br from-primary via-secondary to-purple-500 rounded-2xl shadow-2xl shadow-primary/20">
        <div className="bg-card/90 backdrop-blur-sm p-6 sm:p-8 rounded-[14px]">
          <SearchForm
            searchParams={searchParams}
            setSearchParams={(payload) => dispatch({ type: 'SET_SEARCH_PARAMS', payload })}
            onSubmit={handleSearchSubmit}
            isLoading={isLoading}
            isFavoritesView={isFavoritesView}
            setIsFavoritesView={(payload) => dispatch({ type: 'TOGGLE_FAVORITES_VIEW', payload })}
            favoritesCount={favorites.length}
            drivers={drivers}
          />
          <SearchHistory 
            history={history}
            onSearch={handleHistorySearch}
            onClear={() => dispatch({ type: 'CLEAR_HISTORY' })}
          />
        </div>
      </div>

      <main className="mt-8">
        <ResultsGrid
          items={isFavoritesView ? favorites : results}
          isLoading={isLoading && page === 1}
          isFavoritesView={isFavoritesView}
          isFavorite={isFavorite}
          toggleFavorite={toggleFavorite}
          openModal={(payload) => dispatch({ type: 'SET_SELECTED_ITEM', payload })}
          hasSearched={!!urlSearchParams.get('q')}
        />
        {!isFavoritesView && hasMore && results.length > 0 && !isLoading && (
          <div className="w-full flex justify-center mt-8">
            <Button onClick={handleLoadMore} variant="secondary" size="lg" disabled={isLoading}>
              {isLoading ? 'Loading...' : 'Load More'}
            </Button>
          </div>
        )}
         {isLoading && page > 1 && (
          <div className="w-full flex justify-center mt-8">
             <Button variant="secondary" size="lg" disabled>
              Loading...
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

    