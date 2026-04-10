'use client';

import { useState } from 'react';
import styles from './URLInput.module.css';

export default function URLInput({ onSubmit, disabled }) {
  const [url, setUrl] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim() && !disabled) {
      let finalUrl = url.trim();
      if (!finalUrl.startsWith('http')) {
        finalUrl = 'https://' + finalUrl;
      }
      onSubmit(finalUrl);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.badge}>
        <span className={styles.badgeDot} />
        AI-Powered Analysis
      </div>

      <h1 className={styles.title}>
        Understand your products<br />
        through reviews.
      </h1>

      <p className={styles.subtitle}>
        Paste any product URL and get instant AI-powered sentiment analysis,
        key themes, and actionable insights from customer reviews.
      </p>

      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.inputIcon}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
        </div>
        <input
          id="url-input"
          type="text"
          className={styles.input}
          placeholder="Paste a product URL (Amazon, Flipkart, etc.)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={disabled}
          autoComplete="url"
          required
        />
        <button
          id="analyze-button"
          type="submit"
          className={styles.submitBtn}
          disabled={disabled || !url.trim()}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          Analyze
        </button>
      </form>

      <div className={styles.features}>
        <div className={styles.feature}>
          <div className={styles.featureIcon}>🔍</div>
          <span className={styles.featureLabel}>Smart Scraping</span>
          <span className={styles.featureDesc}>Multi-platform review extraction</span>
        </div>
        <div className={styles.feature}>
          <div className={styles.featureIcon}>🧠</div>
          <span className={styles.featureLabel}>AI Analysis</span>
          <span className={styles.featureDesc}>GPT-powered sentiment detection</span>
        </div>
        <div className={styles.feature}>
          <div className={styles.featureIcon}>📊</div>
          <span className={styles.featureLabel}>Key Themes</span>
          <span className={styles.featureDesc}>Auto-extracted topic clusters</span>
        </div>
        <div className={styles.feature}>
          <div className={styles.featureIcon}>💡</div>
          <span className={styles.featureLabel}>Insights</span>
          <span className={styles.featureDesc}>Actionable recommendations</span>
        </div>
      </div>
    </div>
  );
}
