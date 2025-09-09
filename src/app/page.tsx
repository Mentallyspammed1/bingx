'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Image from 'next/image';
import { search, SearchInput, SearchOutput } from '@/ai/flows/search-flow';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

type MediaItem = SearchOutput[0];

const SKELETON_COUNT = 6;
const FAVORITES_STORAGE_KEY = 'neonSearchFavorites';

export default function Home() {
  const [query, setQuery] = useState('');
  const [driver, setDriver] = useState('redtube');
  const [type, setType] = useState('videos');
  const [results, setResults] = useState<MediaItem[]>([]);
  const [favorites, setFavorites] = useState<MediaItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<MediaItem | null>(null);
  const [isFavoritesView, setIsFavoritesView] = useState(false);

  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    try {
      const storedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
      if (storedFavorites) {
        setFavorites(JSON.parse(storedFavorites));
      }
    } catch (e) {
      console.error('Failed to load favorites from localStorage', e);
    }
  }, []);

  const saveFavorites = (newFavorites: MediaItem[]) => {
    setFavorites(newFavorites);
    try {
      localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(newFavorites));
    } catch (e) {
      console.error('Failed to save favorites to localStorage', e);
    }
  };

  const isFavorite = (item: MediaItem) => {
    return favorites.some(fav => fav.url === item.url);
  };

  const toggleFavorite = (item: MediaItem) => {
    let newFavorites;
    if (isFavorite(item)) {
      newFavorites = favorites.filter(fav => fav.url !== item.url);
    } else {
      newFavorites = [...favorites, item];
    }
    saveFavorites(newFavorites);
  };


  const performSearch = useCallback(async (newPage: number, newSearch = false) => {
    if (!query.trim()) {
      setError('Please enter a search query.');
      return;
    }
    setIsLoading(true);
    setError(null);
    if(newSearch) {
      setResults([]);
    }

    try {
      const searchInput: SearchInput = { query, driver, type, page: newPage };
      const res = await search(searchInput);
      if (newSearch) {
        setResults(res);
      } else {
        setResults(prev => [...prev, ...res]);
      }
      setHasMore(res.length > 0);
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [query, driver, type]);

  const handleSearch = (e?: React.FormEvent) => {
    e?.preventDefault();
    setPage(1);
    performSearch(1, true);
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    performSearch(nextPage, false);
  };

  const openModal = (item: MediaItem) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  const NeonCard = ({ item }: { item: MediaItem }) => {
    const cardRef = useRef<HTMLDivElement>(null);

    const handleMouseEnter = () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = setTimeout(() => {
        const video = cardRef.current?.querySelector('video');
        if (video) video.play().catch(console.error);
      }, 200);
    };

    const handleMouseLeave = () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      const video = cardRef.current?.querySelector('video');
      if (video) video.pause();
    };
    
    return (
      <Card
        ref={cardRef}
        onClick={() => openModal(item)}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="card group"
        tabIndex={0}
      >
        <CardContent className="p-0 card-media-container">
          <div className="relative w-full h-full">
            {item.thumbnail && (
              <Image
                src={item.thumbnail}
                alt={item.title}
                fill
                className="object-cover static-thumb transition-opacity duration-300 group-hover:opacity-10"
                unoptimized
                onError={(e) => e.currentTarget.style.display = 'none'}
              />
            )}
            {item.preview_video && (
              <video
                src={item.preview_video}
                muted
                loop
                playsInline
                className="object-cover w-full h-full absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                preload="metadata"
              ></video>
            )}
             {item.duration && <span className="duration-overlay">{item.duration}</span>}
          </div>
           <Button
              variant="ghost"
              size="icon"
              className={cn("favorite-btn", isFavorite(item) && "is-favorite")}
              onClick={(e) => {
                e.stopPropagation();
                toggleFavorite(item);
              }}
            >
              <Star className={cn("h-6 w-6", isFavorite(item) ? "fill-current" : "")} />
            </Button>
        </CardContent>
        <CardFooter className="card-info">
          <h3 className="card-title">{item.title}</h3>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="card-link"
          >
            {item.source}
          </a>
        </CardFooter>
      </Card>
    );
  };
  
  const renderContent = () => {
    if (isFavoritesView) {
      if (favorites.length === 0) {
        return <p className="col-span-full text-center text-xl text-gray-400 py-10" style={{ textShadow: '0 0 5px var(--neon-pink)' }}>No favorites added yet.</p>;
      }
      return favorites.map((item, index) => <NeonCard key={`${item.id}-${index}`} item={item} />);
    }

    if (isLoading && results.length === 0) {
      return Array.from({ length: SKELETON_COUNT }).map((_, i) => (
        <div key={i} className="skeleton-card">
          <Skeleton className="skeleton-img" />
          <div className="skeleton-info">
            <Skeleton className="skeleton-text" />
            <Skeleton className="skeleton-link" />
          </div>
        </div>
      ));
    }
    
    if (error && results.length === 0) {
      return (
        <Alert variant="destructive" className="col-span-full">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      );
    }
    
    if (results.length > 0) {
      return results.map((item, index) => <NeonCard key={`${item.id}-${index}`} item={item} />);
    }

    return <p id="initialMessage" className="text-center text-xl col-span-full text-gray-400 py-10" style={{textShadow: '0 0 5px var(--neon-cyan)'}}>Enter a query and select options to search...</p>;
  };

  return (
    <>
    <div className="w-full max-w-5xl">
      <header className="w-full search-container p-4 sm:p-6 md:p-8 mb-8" role="search">
        <h1 className="title-main text-3xl sm:text-4xl font-bold text-center mb-6">
          Neon Surf
          <span className="title-sub text-lg block font-normal opacity-80">(Find Videos & GIFs)</span>
        </h1>
        <form onSubmit={handleSearch} className="search-controls flex flex-col sm:flex-row items-stretch sm:space-y-4 sm:space-y-0 sm:space-x-3 md:space-x-4 mb-6">
          <div className="input-wrapper mb-4 sm:mb-0 flex-grow">
            <Input
              id="searchInput"
              type="text"
              placeholder="Enter search query..."
              className="input-neon"
              autoComplete="off"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={isLoading}
            />
            {query && <button type="button" onClick={() => setQuery('')} className="clear-input-btn" aria-label="Clear search query" title="Clear search">×</button>}
          </div>
          
          <Select value={type} onValueChange={setType} disabled={isLoading}>
            <SelectTrigger className="select-neon w-full sm:w-auto">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="videos">Videos</SelectItem>
              <SelectItem value="gifs">GIFs</SelectItem>
            </SelectContent>
          </Select>

          <Select value={driver} onValueChange={setDriver} disabled={isLoading}>
            <SelectTrigger className="select-neon w-full sm:w-auto">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="pornhub">Pornhub</SelectItem>
              <SelectItem value="sex">Sex.com</SelectItem>
              <SelectItem value="redtube">Redtube</SelectItem>
              <SelectItem value="xvideos">XVideos</SelectItem>
              <SelectItem value="xhamster">Xhamster</SelectItem>
              <SelectItem value="youporn">Youporn</SelectItem>
              <SelectItem value="mock">Mock (Test)</SelectItem>
            </SelectContent>
          </Select>
          
          <Button type="submit" className="btn-neon" disabled={isLoading}>
            {isLoading ? <span className="spinner"></span> : 'Search'}
          </Button>
        </form>
         <div className="flex justify-center mb-6">
            <Button onClick={() => setIsFavoritesView(!isFavoritesView)} className="btn-neon">
              {isFavoritesView ? 'Back to Search' : `View Favorites (${favorites.length})`}
            </Button>
          </div>
      </header>

      <main className="w-full flex-grow">
        <div id="resultsDiv" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {renderContent()}
        </div>
      </main>

      {!isFavoritesView && hasMore && results.length > 0 && !isLoading && (
        <div className="w-full flex justify-center mt-8">
          <Button onClick={handleLoadMore} className="btn-neon" disabled={isLoading}>
            {isLoading ? <span className="spinner"></span> : 'Load More'}
          </Button>
        </div>
      )}

      {selectedItem && (
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogContent className="modal-container p-0">
             <div className="modal-content">
                {
                  selectedItem.url && (/\.(mp4|webm|ogv)$/i.test(selectedItem.url)) ? (
                     <video src={selectedItem.url} controls autoPlay className="w-full h-auto max-h-[80vh]"></video>
                  ) : (
                    <Image src={selectedItem.url || selectedItem.preview_video || selectedItem.thumbnail || ''} alt={selectedItem.title} width={800} height={600} className="w-full h-auto max-h-[80vh] object-contain" unoptimized/>
                  )
                }
             </div>
             <div className="modal-link-container">
                <a href={selectedItem.url} target="_blank" rel="noopener noreferrer" className="modal-link">
                  View on {selectedItem.source}
                </a>
             </div>
          </DialogContent>
        </Dialog>
      )}
      </div>

       <style jsx global>{`
        /* Neon Theme Styles */
        .search-container {
            background: rgba(10, 10, 25, 0.9);
            border: 2px solid hsl(var(--neon-pink));
            box-shadow: 0 0 20px hsl(var(--neon-pink)), 0 0 40px hsl(var(--neon-cyan)), 0 0 60px hsl(var(--neon-purple)), inset 0 0 15px rgba(255, 0, 170, 0.5);
            border-radius: 16px;
            animation: searchContainerGlow 6s infinite alternate ease-in-out;
        }
        @keyframes searchContainerGlow {
            0% {
                box-shadow: 0 0 20px hsl(var(--neon-pink)), 0 0 40px hsl(var(--neon-cyan)), 0 0 60px hsl(var(--neon-purple)), inset 0 0 15px rgba(255, 0, 170, 0.5);
                border-color: hsl(var(--neon-pink));
            }
            50% {
                box-shadow: 0 0 30px hsl(var(--neon-cyan)), 0 0 50px hsl(var(--neon-purple)), 0 0 70px hsl(var(--neon-pink)), inset 0 0 20px rgba(0, 229, 255, 0.5);
                border-color: hsl(var(--neon-cyan));
            }
            100% {
                box-shadow: 0 0 20px hsl(var(--neon-purple)), 0 0 40px hsl(var(--neon-pink)), 0 0 60px hsl(var(--neon-cyan)), inset 0 0 15px rgba(157, 0, 255, 0.5);
                border-color: hsl(var(--neon-purple));
            }
        }
        .title-main {
            text-shadow: 0 0 10px hsl(var(--neon-pink)), 0 0 20px hsl(var(--neon-cyan)), 0 0 30px hsl(var(--neon-purple)), 0 0 40px #fff;
        }
        .title-sub {
            text-shadow: 0 0 5px hsl(var(--neon-cyan));
        }
        .input-wrapper {
            position: relative;
        }
        .input-neon, .select-neon > div {
            background: var(--input-bg) !important;
            color: var(--text-color) !important;
            border: 2px solid hsl(var(--neon-cyan)) !important;
            box-shadow: 0 0 10px hsl(var(--neon-cyan)), inset 0 0 8px rgba(0, 229, 255, 0.25);
            transition: all 0.3s ease;
            border-radius: 0.6rem;
        }
        .select-neon > div {
             background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%23ff00aa'%3E%3Cpath fill-rule='evenodd' d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3Csvg%3E");
            background-repeat: no-repeat;
            background-position: right 0.75rem center;
            background-size: 0.9em auto;
        }
        .input-neon:focus, .select-neon:focus-within > div {
            border-color: hsl(var(--neon-green)) !important;
            box-shadow: 0 0 18px hsl(var(--neon-green)), 0 0 30px hsl(var(--neon-cyan)), inset 0 0 10px rgba(57, 255, 20, 0.4) !important;
            outline: none !important;
            animation: focusPulseNeon 1.2s infinite alternate;
        }
        @keyframes focusPulseNeon {
            from {
                box-shadow: 0 0 18px hsl(var(--neon-green)), 0 0 30px hsl(var(--neon-cyan)), inset 0 0 10px rgba(57, 255, 20, 0.4);
            } to {
                box-shadow: 0 0 25px hsl(var(--neon-green)), 0 0 40px hsl(var(--neon-cyan)), inset 0 0 15px rgba(57, 255, 20, 0.6);
            }
        }
        .clear-input-btn {
            position: absolute;
            right: 0.5rem;
            top: 50%;
            transform: translateY(-50%);
            background: transparent;
            border: none;
            color: hsl(var(--neon-pink));
            font-size: 1.8rem;
            line-height: 1;
            cursor: pointer;
            padding: 0.25rem;
            transition: color 0.2s ease, transform 0.2s ease;
            z-index: 10;
        }
        .clear-input-btn:hover {
            color: hsl(var(--neon-green));
            transform: translateY(-50%) scale(1.15) rotate(90deg);
        }
        .btn-neon {
            background: linear-gradient(55deg, hsl(var(--neon-pink)), hsl(var(--neon-purple)), hsl(var(--neon-cyan)));
            background-size: 200% 200%;
            border: 2px solid transparent;
            color: #ffffff;
            text-shadow: 0 0 6px #fff, 0 0 12px hsl(var(--neon-pink)), 0 0 18px hsl(var(--neon-cyan)));
            box-shadow: 0 0 12px hsl(var(--neon-pink)), 0 0 24px hsl(var(--neon-cyan)), 0 0 36px hsl(var(--neon-purple)), inset 0 0 10px rgba(255, 255, 255, 0.3);
            transition: all 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
            position: relative;
            overflow: hidden;
            border-radius: 0.6rem;
            cursor: pointer;
            animation: idleButtonGlow 3s infinite alternate;
        }
        @keyframes idleButtonGlow {
            0% {
                background-position: 0% 50%;
                box-shadow: 0 0 12px hsl(var(--neon-pink)), 0 0 24px hsl(var(--neon-cyan)), 0 0 36px hsl(var(--neon-purple)), inset 0 0 10px rgba(255, 255, 255, 0.3);
            }
            50% {
                background-position: 100% 50%;
                box-shadow: 0 0 15px hsl(var(--neon-cyan)), 0 0 30px hsl(var(--neon-purple)), 0 0 45px hsl(var(--neon-pink)), inset 0 0 12px rgba(255, 255, 255, 0.4);
            }
            100% {
                background-position: 0% 50%;
                box-shadow: 0 0 12px hsl(var(--neon-pink)), 0 0 24px hsl(var(--neon-cyan)), 0 0 36px hsl(var(--neon-purple)), inset 0 0 10px rgba(255, 255, 255, 0.3);
            }
        }
        .btn-neon:hover:not(:disabled) {
            transform: scale(1.04) translateY(-3px);
            box-shadow: 0 0 18px hsl(var(--neon-green)), 0 0 36px hsl(var(--neon-cyan)), 0 0 54px hsl(var(--neon-pink)), inset 0 0 15px rgba(255, 255, 255, 0.6);
            border-color: hsl(var(--neon-green));
            text-shadow: 0 0 8px #fff, 0 0 18px hsl(var(--neon-green)), 0 0 24px hsl(var(--neon-cyan));
            animation-play-state: paused;
        }
        .btn-neon:disabled { opacity: var(--disabled-opacity); }
        .btn-neon .spinner {
            border: 3px solid rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            border-top-color: hsl(var(--neon-pink));
            border-right-color: hsl(var(--neon-cyan));
            width: 1.1rem;
            height: 1.1rem;
            animation: spin 0.8s linear infinite;
            display: inline-block;
            vertical-align: middle;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .card {
            background: var(--card-bg);
            border: 2px solid hsl(var(--neon-cyan));
            box-shadow: 0 0 12px hsl(var(--neon-cyan)), 0 0 24px hsl(var(--neon-pink)), inset 0 0 10px rgba(10, 10, 26, 0.6);
            transition: transform 0.35s cubic-bezier(0.25, 0.1, 0.25, 1), box-shadow 0.4s ease, border-color 0.3s ease;
            cursor: pointer;
            height: 300px;
            display: flex;
            flex-direction: column;
            border-radius: 10px;
            color: inherit;
            position: relative;
        }
        .card:hover, .card:focus-visible {
            transform: translateY(-8px) scale(1.03);
            border-color: hsl(var(--neon-green));
            box-shadow: 0 0 22px hsl(var(--neon-green)), 0 0 40px hsl(var(--neon-cyan)), 0 0 60px hsl(var(--neon-pink)), inset 0 0 15px rgba(10, 10, 26, 0.4);
            outline: none;
        }
        .card-media-container {
            height: 200px;
            background-color: var(--input-bg);
            position: relative;
            overflow: hidden;
            border-radius: 6px 6px 0 0;
        }
        .card-info {
            height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 0.75rem;
            flex-grow: 1;
            overflow: hidden;
        }
        .card-title {
            font-size: 1rem;
            font-weight: 600;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-shadow: 0 0 6px hsl(var(--neon-cyan)), 0 0 10px hsl(var(--neon-pink));
        }
        .card-link {
            color: var(--link-color);
            text-shadow: 0 0 4px hsl(var(--neon-pink));
            font-size: 0.875rem;
            transition: color 0.25s ease, text-shadow 0.25s ease;
            margin-top: auto;
            text-decoration: none;
        }
        .card-link:hover, .card-link:focus {
            color: var(--link-hover-color);
            text-shadow: 0 0 6px hsl(var(--neon-green)), 0 0 8px hsl(var(--neon-cyan));
            text-decoration: underline;
        }
        .duration-overlay {
            position: absolute;
            bottom: 0.5rem;
            right: 0.5rem;
            background: rgba(0, 0, 0, 0.6);
            color: white;
            font-size: 0.75rem;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            z-index: 10;
        }
        .modal-container {
            background: var(--input-bg);
            border: 3px solid hsl(var(--neon-pink));
            box-shadow: 0 0 30px hsl(var(--neon-pink)), 0 0 60px hsl(var(--neon-cyan)), 0 0 90px hsl(var(--neon-purple)), inset 0 0 20px rgba(5, 5, 15, 0.6);
            max-width: 95vw;
            max-height: 95vh;
        }
        .modal-content {
          max-height: calc(95vh - 80px);
        }
        .modal-link-container {
            border-top: 2px solid rgba(255, 255, 255, 0.1);
            box-shadow: inset 0 10px 15px rgba(0, 0, 0, 0.2);
        }
        .modal-link {
            color: var(--link-color);
            font-weight: 600;
            text-shadow: 0 0 5px hsl(var(--neon-pink));
        }
        .modal-link:hover, .modal-link:focus {
            color: var(--link-hover-color);
            text-decoration: underline;
            text-shadow: 0 0 8px hsl(var(--neon-green));
        }
        .skeleton-card {
            background: var(--card-bg);
            border: 2px solid #333959;
            border-radius: 10px;
            height: 300px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: pulse 1.5s infinite ease-in-out;
        }
        .skeleton-img { height: 200px; background-color: #1f253d; }
        .skeleton-info { flex-grow: 1; padding: 0.75rem; display: flex; flex-direction: column; justify-content: space-between; }
        .skeleton-text { height: 1em; background-color: #1f253d; border-radius: 4px; margin-bottom: 0.5rem; width: 90%; }
        .skeleton-link { height: 0.8em; background-color: #1f253d; border-radius: 4px; width: 40%; margin-top: auto; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .favorite-btn {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            background: rgba(0, 0, 0, 0.5);
            color: var(--favorite-btn-color);
            z-index: 50;
            border-radius: 50%;
            transition: color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
        }
        .favorite-btn:hover {
            color: var(--favorite-btn-active-color);
            transform: scale(1.2);
            box-shadow: 0 0 12px var(--favorite-btn-active-color);
        }
        .favorite-btn.is-favorite {
            color: var(--favorite-btn-active-color);
            text-shadow: 0 0 8px var(--favorite-btn-active-color);
            animation: favoritePulse 1.5s infinite alternate;
        }
        @keyframes favoritePulse {
            from {
                text-shadow: 0 0 8px var(--favorite-btn-active-color);
                box-shadow: 0 0 12px var(--favorite-btn-active-color);
            }
            to {
                text-shadow: 0 0 15px var(--favorite-btn-active-color), 0 0 25px var(--favorite-btn-active-color);
                box-shadow: 0 0 18px var(--favorite-btn-active-color), 0 0 30px var(--favorite-btn-active-color);
            }
        }
      `}</style>
    </>
  );
}
