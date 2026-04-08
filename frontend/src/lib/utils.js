/**
 * Utility helpers for formatting and calculations.
 */

/**
 * Get the color variables for a sentiment label.
 */
export function getSentimentStyle(sentiment) {
  const map = {
    positive: {
      color: 'var(--color-positive)',
      bg: 'var(--color-positive-bg)',
      border: 'var(--color-positive-border)',
      label: 'Positive',
      icon: '↑',
    },
    negative: {
      color: 'var(--color-negative)',
      bg: 'var(--color-negative-bg)',
      border: 'var(--color-negative-border)',
      label: 'Negative',
      icon: '↓',
    },
    neutral: {
      color: 'var(--color-neutral)',
      bg: 'var(--color-neutral-bg)',
      border: 'var(--color-neutral-border)',
      label: 'Neutral',
      icon: '→',
    },
    mixed: {
      color: 'var(--color-mixed)',
      bg: 'var(--color-mixed-bg)',
      border: 'var(--color-mixed-border)',
      label: 'Mixed',
      icon: '⇄',
    },
  };
  return map[sentiment] || map.neutral;
}

/**
 * Format a sentiment score (-1 to 1) as a percentage (0 to 100).
 */
export function scoreToPercent(score) {
  return Math.round(((score + 1) / 2) * 100);
}

/**
 * Format a date string to a readable format.
 */
export function formatDate(dateStr) {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    if (isNaN(date)) return dateStr;
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  } catch {
    return dateStr;
  }
}

/**
 * Truncate text to maxLength with ellipsis.
 */
export function truncate(text, maxLength = 200) {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength).trimEnd() + '…';
}

/**
 * Generate star rating display.
 */
export function renderStars(rating) {
  if (rating == null) return '';
  const full = Math.floor(rating);
  const half = rating % 1 >= 0.5;
  let stars = '★'.repeat(full);
  if (half) stars += '½';
  stars += '☆'.repeat(5 - full - (half ? 1 : 0));
  return stars;
}
