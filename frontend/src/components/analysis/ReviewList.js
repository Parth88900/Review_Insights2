'use client';

import ReviewCard from './ReviewCard';
import styles from './ReviewList.module.css';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'positive', label: 'Positive' },
  { key: 'negative', label: 'Negative' },
  { key: 'neutral', label: 'Neutral' },
];

export default function ReviewList({ reviews, filter, onFilterChange, totalReviews }) {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h3 className={styles.title}>Individual Reviews</h3>
          <span className={styles.count}>
            {reviews.length} of {totalReviews} shown
          </span>
        </div>

        <div className={styles.filters}>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={`${styles.filterBtn} ${filter === f.key ? styles.filterBtnActive : ''}`}
              onClick={() => onFilterChange(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {reviews.length > 0 ? (
        <div className={styles.grid}>
          {reviews.map((review, i) => (
            <ReviewCard key={review.id || i} review={review} index={i} />
          ))}
        </div>
      ) : (
        <div className={styles.emptyFilter}>
          No reviews match the selected filter.
        </div>
      )}
    </div>
  );
}
