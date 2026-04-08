'use client';

import { getSentimentStyle } from '@/lib/utils';
import styles from './ThemesSection.module.css';

export default function ThemesSection({ themes }) {
  if (!themes || themes.length === 0) {
    return (
      <div className={styles.container}>
        <h3 className={styles.title}>Key Themes</h3>
        <div className={styles.empty}>No themes extracted from reviews.</div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <h3 className={styles.title}>Key Themes</h3>
      <div className={styles.grid}>
        {themes.map((theme, i) => {
          const sentimentStyle = getSentimentStyle(theme.sentiment);
          return (
            <div key={i} className={styles.theme}>
              <div className={styles.themeHeader}>
                <span className={styles.themeName}>{theme.name}</span>
                <span
                  className={styles.themeCount}
                  style={{
                    color: sentimentStyle.color,
                    background: sentimentStyle.bg,
                  }}
                >
                  {theme.count}
                </span>
              </div>
              {theme.sample_quotes?.[0] && (
                <p className={styles.themeQuote}>"{theme.sample_quotes[0]}"</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
