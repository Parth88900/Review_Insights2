'use client';

import SentimentScore from './SentimentScore';
import InsightsPanel from './InsightsPanel';
import ThemesSection from './ThemesSection';
import ReviewList from './ReviewList';
import styles from './Dashboard.module.css';

export default function Dashboard({ data, filter, filteredReviews, onFilterChange, onReset }) {
  if (!data) return null;

  const { product_name, product_image, source_url, summary, themes, reviews } = data;

  // Truncate URL for display
  const displayUrl = (() => {
    try {
      const url = new URL(source_url);
      return url.hostname + (url.pathname.length > 30 ? url.pathname.slice(0, 30) + '…' : url.pathname);
    } catch {
      return source_url?.slice(0, 50);
    }
  })();

  return (
    <div className={styles.container}>
      {/* Product Header */}
      <div className={styles.productHeader}>
        {product_image && (
          <img
            src={product_image}
            alt={product_name || 'Product'}
            className={styles.productImage}
            onError={(e) => { e.target.style.display = 'none'; }}
          />
        )}
        <div className={styles.productInfo}>
          <h1 className={styles.productName}>
            {product_name || 'Product Analysis'}
          </h1>
          <div className={styles.productMeta}>
            <span>{summary?.total_reviews || reviews?.length || 0} reviews analyzed</span>
            <span>·</span>
            <a
              href={source_url}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.productLink}
            >
              {displayUrl}
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/export/csv`} target="_blank" rel="noopener noreferrer" className={styles.newAnalysisBtn}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export CSV
          </a>
          <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/export/json`} target="_blank" rel="noopener noreferrer" className={styles.newAnalysisBtn}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export JSON
          </a>
          <button className={styles.newAnalysisBtn} onClick={onReset}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Analysis
          </button>
        </div>
      </div>

      {/* Top Row: Sentiment + Insights */}
      <div className={styles.topRow}>
        <SentimentScore summary={summary} />
        <InsightsPanel summary={summary} />
      </div>

      {/* Themes */}
      {themes && themes.length > 0 && (
        <div className={styles.fullWidth}>
          <ThemesSection themes={themes} />
        </div>
      )}

      {/* Reviews */}
      <div className={styles.fullWidth}>
        <ReviewList
          reviews={filteredReviews}
          filter={filter}
          onFilterChange={onFilterChange}
          totalReviews={reviews?.length || 0}
        />
      </div>
    </div>
  );
}
