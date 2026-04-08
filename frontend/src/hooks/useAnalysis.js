/**
 * Custom hook for managing the review analysis workflow.
 */

'use client';

import { useState, useCallback } from 'react';
import { analyzeReviews, APIError } from '@/lib/api';

// Application states
export const AppState = {
  IDLE: 'idle',
  LOADING: 'loading',
  SUCCESS: 'success',
  ERROR: 'error',
};

// Loading sub-states for progress indication
const LoadingStage = {
  CONNECTING: { label: 'Connecting to server', progress: 10 },
  SCRAPING: { label: 'Scraping product reviews', progress: 30 },
  PREPROCESSING: { label: 'Cleaning & preprocessing text', progress: 50 },
  ANALYZING: { label: 'Analyzing sentiment with AI', progress: 70 },
  SUMMARIZING: { label: 'Generating insights & summary', progress: 85 },
  FINALIZING: { label: 'Preparing your dashboard', progress: 95 },
};

export function useAnalysis() {
  const [state, setState] = useState(AppState.IDLE);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loadingStage, setLoadingStage] = useState(null);
  const [filter, setFilter] = useState('all'); // all | positive | negative | neutral

  const analyze = useCallback(async (url, maxReviews = 20) => {
    setState(AppState.LOADING);
    setError(null);
    setData(null);

    // Simulate loading stages for UX
    const stages = Object.values(LoadingStage);
    let stageIndex = 0;

    setLoadingStage(stages[0]);

    const progressInterval = setInterval(() => {
      stageIndex++;
      if (stageIndex < stages.length) {
        setLoadingStage(stages[stageIndex]);
      }
    }, 2500);

    try {
      const result = await analyzeReviews(url, maxReviews);
      clearInterval(progressInterval);
      setLoadingStage({ label: 'Complete', progress: 100 });

      // Small delay for the 100% state to show
      await new Promise((r) => setTimeout(r, 500));

      setData(result);
      setState(AppState.SUCCESS);
      setLoadingStage(null);
    } catch (err) {
      clearInterval(progressInterval);
      setLoadingStage(null);

      const message =
        err instanceof APIError
          ? err.message
          : 'Something went wrong. Please check your connection and try again.';

      setError(message);
      setState(AppState.ERROR);
    }
  }, []);

  const reset = useCallback(() => {
    setState(AppState.IDLE);
    setData(null);
    setError(null);
    setLoadingStage(null);
    setFilter('all');
  }, []);

  // Filtered reviews
  const filteredReviews =
    data?.reviews?.filter((r) => {
      if (filter === 'all') return true;
      return r.sentiment === filter;
    }) || [];

  return {
    state,
    data,
    error,
    loadingStage,
    filter,
    filteredReviews,
    analyze,
    reset,
    setFilter,
  };
}
