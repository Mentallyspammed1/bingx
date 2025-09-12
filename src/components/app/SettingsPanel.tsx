
'use client';

import React, { useState, useEffect } from 'react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getDrivers, suggestSelectors } from '@/ai/flows/search-flow';
import type { SelectorSuggestionOutput } from '@/ai/types';
import { Wand, AlertTriangle, ClipboardCopy } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';

interface SettingsPanelProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ isOpen, onOpenChange }) => {
  const [drivers, setDrivers] = useState<string[]>([]);
  const [selectedDriver, setSelectedDriver] = useState<string>('');
  const [selectedType, setSelectedType] = useState<'videos' | 'gifs'>('videos');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestion, setSuggestion] = useState<SelectorSuggestionOutput | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  useEffect(() => {
    async function fetchDrivers() {
      try {
        const driverNames = await getDrivers();
        const filteredDrivers = driverNames.filter(d => d.toLowerCase() !== 'mock');
        setDrivers(filteredDrivers);
        if (filteredDrivers.length > 0) {
          setSelectedDriver(filteredDrivers[0]);
        }
      } catch (err) {
        console.error("Failed to fetch drivers", err);
      }
    }
    if (isOpen) {
      fetchDrivers();
    }
  }, [isOpen]);
  
  const handleGenerateSuggestion = async () => {
      if (!selectedDriver) return;
      setIsLoading(true);
      setSuggestion(null);
      setError(null);

      try {
          const result = await suggestSelectors({
              driver: selectedDriver,
              type: selectedType,
              query: 'trending' // Use a common query to get a representative HTML page
          });
          setSuggestion(result);
      } catch (err: any) {
          setError(err.message || 'An unknown error occurred while generating suggestions.');
      } finally {
          setIsLoading(false);
      }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast({ title: "Copied to clipboard!" });
    }).catch(err => {
      toast({ variant: 'destructive', title: "Failed to copy", description: err.message });
    });
  };

  return (
    <Sheet open={isOpen} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-xl w-full flex flex-col">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-2xl">
            <Wand className="h-6 w-6 text-primary" /> AI Scraper Repair
          </SheetTitle>
          <SheetDescription>
            If a site isn't returning results, its structure has likely changed. Use this tool to generate new scraper code.
          </SheetDescription>
        </SheetHeader>
        
        <div className="flex-grow flex flex-col gap-6 py-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Select value={selectedDriver} onValueChange={setSelectedDriver}>
              <SelectTrigger>
                <SelectValue placeholder="Select a site" />
              </SelectTrigger>
              <SelectContent>
                {drivers.map(driver => (
                  <SelectItem key={driver} value={driver}>
                    {driver === 'wow.xxx' ? 'Wow.xxx' : driver.charAt(0).toUpperCase() + driver.slice(1)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedType} onValueChange={(v) => setSelectedType(v as 'videos' | 'gifs')}>
                <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                    <SelectItem value="videos">Videos</SelectItem>
                    <SelectItem value="gifs">GIFs</SelectItem>
                </SelectContent>
            </Select>
            
            <Button onClick={handleGenerateSuggestion} disabled={isLoading || !selectedDriver}>
              {isLoading ? 'Analyzing...' : 'Generate Code'}
            </Button>
          </div>

          <div className="flex-grow overflow-y-auto rounded-lg bg-muted/30 p-4 space-y-4">
            {isLoading && (
              <div className="space-y-4">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-5/6" />
                <Skeleton className="h-20 w-full mt-4" />
                <Skeleton className="h-4 w-1/4 mt-4" />
                <Skeleton className="h-40 w-full" />
              </div>
            )}
            {error && (
              <div className="text-center text-destructive p-4 border border-destructive/50 rounded-lg">
                <AlertTriangle className="mx-auto h-8 w-8 mb-2" />
                <h3 className="font-semibold">Generation Failed</h3>
                <p className="text-sm">{error}</p>
              </div>
            )}
            {suggestion && (
              <div className="space-y-4">
                <div>
                    <h3 className="font-semibold text-lg text-primary">AI Reasoning</h3>
                    <p className="text-sm text-muted-foreground">{suggestion.reasoning}</p>
                </div>
                <div>
                    <div className="flex justify-between items-center mb-2">
                      <h3 className="font-semibold text-lg text-primary">Suggested Code</h3>
                      <Button variant="ghost" size="icon" onClick={() => copyToClipboard(suggestion.suggestedCode)}>
                        <ClipboardCopy className="h-4 w-4" />
                        <span className="sr-only">Copy code</span>
                      </Button>
                    </div>
                    <pre className="bg-background rounded-md p-4 text-xs overflow-x-auto">
                        <code>{suggestion.suggestedCode}</code>
                    </pre>
                </div>
                 <div className="border-t border-border pt-4">
                  <h3 className="font-semibold text-foreground">Next Steps</h3>
                  <p className="text-sm text-muted-foreground">
                    Copy the suggested code and paste it into the corresponding parser function in{' '}
                    <code className="bg-background text-primary px-1 py-0.5 rounded">src/ai/flows/search-flow.ts</code>.
                  </p>
                </div>
              </div>
            )}
            {!isLoading && !error && !suggestion && (
              <div className="text-center text-muted-foreground h-full flex flex-col justify-center items-center">
                <Wand className="h-12 w-12 mb-4 text-muted-foreground/50"/>
                <p>Select a site and click "Generate Code" to get started.</p>
              </div>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
};

export default SettingsPanel;

    