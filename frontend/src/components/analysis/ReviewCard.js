'use client';

import { useState } from 'react';
import { getSentimentStyle, truncate } from '@/lib/utils';
import styles from './ReviewCard.module.css';

export default function ReviewCard({ review, index }) {
  const [expanded, setExpanded] = useState(false);
  const sentimentStyle = getSentimentStyle(review.sentiment);

  const initials = review.author
    ? review.author.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'AN';

  const displayText = expanded ? review.text : truncate(review.text, 220);
  const isLong = review.text?.length > 220;

  const stars = review.rating
    ? '★'.repeat(Math.floor(review.rating)) +
      (review.rating % 1 >= 0.5 ? '½' : '') +
      '☆'.repeat(5 - Math.ceil(review.rating))
    : null;

  return (
    <div
      className={styles.card}
      style={{ animationDelay: `${(index % 10) * 50}ms` }}
    >
      <div className={styles.header}>
        <div className={styles.authorRow}>
          <div className={styles.avatar}>{initials}</div>
          <div className={styles.authorInfo}>
            <span className={styles.authorName}>{review.author || 'Anonymous'}</span>
            <div className={styles.authorMeta}>
              {review.date && <span>{review.date}</span>}
              {review.verified && (
                <span className={styles.verifiedBadge}>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                  </svg>
                  Verified
                </span>
              )}
            </div>
          </div>
        </div>

        <span
          className={styles.sentimentBadge}
          style={{
            color: sentimentStyle.color,
            background: sentimentStyle.bg,
            border: `1px solid ${sentimentStyle.border}`,
          }}
        >
          {sentimentStyle.icon} {sentimentStyle.label}
        </span>
      </div>

      {stars && (
        <div className={styles.rating}>
          <span className={styles.stars}>{stars}</span>
          <span className={styles.ratingText}>{review.rating}/5</span>
        </div>
      )}

      {review.title && <h4 className={styles.reviewTitle}>{review.title}</h4>}

      <p className={styles.reviewText}>
        {displayText}
        {isLong && !expanded && (
          <button className={styles.readMore} onClick={() => setExpanded(true)}>
            {' '}Read more
          </button>
        )}
        {expanded && isLong && (
          <button className={styles.readMore} onClick={() => setExpanded(false)}>
            {' '}Show less
          </button>
        )}
      </p>

      {(review.key_phrases?.length > 0 || review.helpful_count > 0) && (
        <div className={styles.footer}>
          {review.key_phrases?.map((phrase, i) => (
            <span key={i} className={styles.keyPhrase}>{phrase}</span>
          ))}
          {review.helpful_count > 0 && (
            <span className={styles.helpful}>
              👍 {review.helpful_count} found helpful
            </span>
          )}
        </div>
      )}
    </div>
  );
}
