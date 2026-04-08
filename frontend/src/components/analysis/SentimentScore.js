'use client';

import { getSentimentStyle, scoreToPercent } from '@/lib/utils';
import styles from './SentimentScore.module.css';

export default function SentimentScore({ summary }) {
  if (!summary) return null;

  const percent = scoreToPercent(summary.overall_score);
  const sentimentStyle = getSentimentStyle(summary.overall_sentiment);

  // Ring chart calculations
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  const total = summary.total_reviews || 1;
  const posPercent = Math.round((summary.positive_count / total) * 100);
  const negPercent = Math.round((summary.negative_count / total) * 100);
  const neuPercent = 100 - posPercent - negPercent;

  const stars = summary.average_rating
    ? '★'.repeat(Math.floor(summary.average_rating)) +
      (summary.average_rating % 1 >= 0.5 ? '½' : '') +
      '☆'.repeat(5 - Math.ceil(summary.average_rating))
    : null;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Sentiment Overview</span>
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

      <div className={styles.scoreSection}>
        {/* Ring chart */}
        <div className={styles.scoreRing}>
          <svg className={styles.scoreRingSvg} viewBox="0 0 120 120">
            <circle className={styles.scoreRingBg} cx="60" cy="60" r={radius} />
            <circle
              className={styles.scoreRingFg}
              cx="60"
              cy="60"
              r={radius}
              style={{
                stroke: sentimentStyle.color,
                strokeDasharray: circumference,
                strokeDashoffset: offset,
              }}
            />
          </svg>
          <div className={styles.scoreValue}>
            <span className={styles.scoreNumber} style={{ color: sentimentStyle.color }}>
              {percent}
            </span>
            <span className={styles.scoreLabel}>Score</span>
          </div>
        </div>

        {/* Stat bars */}
        <div className={styles.stats}>
          <div className={styles.stat}>
            <div className={styles.statDot} style={{ background: 'var(--color-positive)' }} />
            <span className={styles.statLabel}>Positive</span>
            <div className={styles.statBar}>
              <div
                className={styles.statBarFill}
                style={{ width: `${posPercent}%`, background: 'var(--color-positive)' }}
              />
            </div>
            <span className={styles.statCount}>{summary.positive_count}</span>
          </div>

          <div className={styles.stat}>
            <div className={styles.statDot} style={{ background: 'var(--color-negative)' }} />
            <span className={styles.statLabel}>Negative</span>
            <div className={styles.statBar}>
              <div
                className={styles.statBarFill}
                style={{ width: `${negPercent}%`, background: 'var(--color-negative)' }}
              />
            </div>
            <span className={styles.statCount}>{summary.negative_count}</span>
          </div>

          <div className={styles.stat}>
            <div className={styles.statDot} style={{ background: 'var(--color-neutral)' }} />
            <span className={styles.statLabel}>Neutral</span>
            <div className={styles.statBar}>
              <div
                className={styles.statBarFill}
                style={{ width: `${neuPercent}%`, background: 'var(--color-neutral)' }}
              />
            </div>
            <span className={styles.statCount}>{summary.neutral_count}</span>
          </div>
        </div>
      </div>

      {summary.average_rating && (
        <div className={styles.ratingRow}>
          <span className={styles.ratingStars}>{stars}</span>
          <span className={styles.ratingValue}>
            {summary.average_rating}
            <span className={styles.ratingMax}>/5</span>
          </span>
          <span className={styles.ratingLabel}>Avg. Rating</span>
        </div>
      )}
    </div>
  );
}
