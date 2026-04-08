'use client';

import styles from './LoadingState.module.css';

export default function LoadingState({ stage }) {
  const progress = stage?.progress || 0;
  const label = stage?.label || 'Preparing...';

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.iconContainer}>
          <div className={styles.spinner} />
          <div className={styles.innerDot} />
        </div>

        <div className={styles.stageLabel}>{label}</div>
        <div className={styles.stageSubtext}>This usually takes 15–30 seconds</div>

        <div className={styles.progressTrack}>
          <div
            className={styles.progressBar}
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className={styles.progressText}>{progress}%</div>
      </div>

      {/* Skeleton preview cards */}
      <div className={styles.skeletons}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className={styles.skeleton}>
            <div className={styles.skeletonCircle} />
            <div className={styles.skeletonLine} />
            <div className={`${styles.skeletonLine} ${styles.skeletonMedium}`} />
            <div className={`${styles.skeletonLine} ${styles.skeletonShort}`} />
          </div>
        ))}
      </div>
    </div>
  );
}
