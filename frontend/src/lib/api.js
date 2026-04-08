/**
 * API client for communicating with the ReviewInsight backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Analyze product reviews from a given URL.
 * @param {string} url - The product page URL to analyze.
 * @param {number} maxReviews - Maximum number of reviews to process.
 * @returns {Promise<Object>} Analysis results.
 */
export async function analyzeReviews(url, maxReviews = 20) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url, max_reviews: maxReviews }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new APIError(
      error.detail || `Analysis failed with status ${response.status}`,
      response.status
    );
  }

  return response.json();
}

/**
 * Check API health status.
 * @returns {Promise<Object>} Health check response.
 */
export async function checkHealth() {
  const response = await fetch(`${API_BASE}/api/health`);
  if (!response.ok) {
    throw new APIError('API is not available', response.status);
  }
  return response.json();
}

/**
 * Custom API error class with status code.
 */
export class APIError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
  }
}
