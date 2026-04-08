'use client';

import styles from './InsightsPanel.module.css';

export default function InsightsPanel({ summary }) {
  if (!summary) return null;

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>AI Summary & Insights</h3>

      <p className={styles.summaryText}>{summary.summary_text}</p>

      {summary.strengths?.length > 0 && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>
            <span className={styles.sectionIcon}>✦</span>
            Strengths
          </h4>
          <ul className={styles.list}>
            {summary.strengths.map((item, i) => (
              <li key={i} className={styles.listItem}>
                <span className={styles.bullet} style={{ background: 'var(--color-positive)' }} />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.weaknesses?.length > 0 && (
        <div className={styles.section}>
          <h4 className={styles.sectionTitle}>
            <span className={styles.sectionIcon}>⚑</span>
            Weaknesses
          </h4>
          <ul className={styles.list}>
            {summary.weaknesses.map((item, i) => (
              <li key={i} className={styles.listItem}>
                <span className={styles.bullet} style={{ background: 'var(--color-negative)' }} />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.recommendation && (
        <div className={styles.recommendation}>
          <span className={styles.recommendationIcon}>💡</span>
          <span className={styles.recommendationText}>{summary.recommendation}</span>
        </div>
      )}
    </div>
  );
}
