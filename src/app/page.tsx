import { Suspense } from 'react';
import SearchClientPage from './SearchClientPage';

export default function Page() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SearchClientPage />
    </Suspense>
  );
}