'use client';

import { useAnalysis, AppState } from '@/hooks/useAnalysis';
import Header from '@/components/layout/Header';
import URLInput from '@/components/ui/URLInput';
import LoadingState from '@/components/ui/LoadingState';
import ErrorState from '@/components/ui/ErrorState';
import Dashboard from '@/components/analysis/Dashboard';

export default function Home() {
  const {
    state,
    data,
    error,
    loadingStage,
    filter,
    filteredReviews,
    analyze,
    reset,
    setFilter,
  } = useAnalysis();

  return (
    <>
      <Header onReset={reset} />

      <main>
        {state === AppState.IDLE && (
          <URLInput onSubmit={(url) => analyze(url)} />
        )}

        {state === AppState.LOADING && (
          <LoadingState stage={loadingStage} />
        )}

        {state === AppState.ERROR && (
          <ErrorState message={error} onRetry={reset} />
        )}

        {state === AppState.SUCCESS && (
          <Dashboard
            data={data}
            filter={filter}
            filteredReviews={filteredReviews}
            onFilterChange={setFilter}
            onReset={reset}
          />
        )}
      </main>
    </>
  );
}
