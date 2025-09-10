'use client';

import React from 'react';
import { History, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { SearchInput } from '@/ai/types';

interface SearchHistoryProps {
  history: Omit<SearchInput, 'page'>[];
  onSearch: (item: Omit<SearchInput, 'page'>) => void;
  onClear: () => void;
}

const SearchHistory: React.FC<SearchHistoryProps> = ({ history, onSearch, onClear }) => {
  if (history.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 border-t border-primary/20 pt-4">
      <div className="flex justify-between items-center mb-2">
        <h3 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
          <History className="h-4 w-4" />
          Recent Searches
        </h3>
        <Button variant="ghost" size="sm" onClick={onClear} className="text-muted-foreground hover:text-destructive">
          <Trash2 className="h-4 w-4 mr-1" />
          Clear
        </Button>
      </div>
      <div className="flex flex-wrap gap-2">
        {history.map((item, index) => (
          <button
            key={index}
            onClick={() => onSearch(item)}
            className="text-xs bg-accent hover:bg-primary/30 text-accent-foreground rounded-full px-3 py-1 transition-colors"
          >
            {item.query}
          </button>
        ))}
      </div>
    </div>
  );
};

export default SearchHistory;
