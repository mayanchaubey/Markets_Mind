import { demoChatResponse } from '../data/demoResponses';
import { demoSignals } from '../data/demoSignals';
import { demoVerifyResult } from '../data/demoClaims';

const viteApiUrl = import.meta.env.VITE_API_URL;
if (!viteApiUrl || !viteApiUrl.trim()) {
  throw new Error('VITE_API_URL is missing. Set it in your Vite env files before building.');
}
const normalizedRoot = viteApiUrl.trim().replace(/\/+$/, '');
export const API_ROOT_URL = normalizedRoot;
export const API_BASE_URL = normalizedRoot.endsWith('/api')
  ? normalizedRoot
  : `${normalizedRoot}/api`;
const buildUrl = (endpoint) => `${API_BASE_URL}${endpoint}`;
// We will use a flag to control whether to use demo data immediately for testing without a backend,
// or we can attempt to fetch and catch errors to fallback. We'll do the attempt/fallback approach.

/**
 * Helper to handle fetch with timeout & fallback.
 * Standardizes the response structure: { data, isDemo, error? }
 */
const fetchWithFallback = async (endpoint, options = {}, fallbackData) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 12000); // Increased to 12s for RAG

  try {
    const response = await fetch(buildUrl(endpoint), {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`HTTP_${response.status}`);
    }

    const json = await response.json();
    return { data: json, isDemo: false, error: null };
  } catch (error) {
    clearTimeout(timeoutId);
    console.warn(`[API RECOVERY] ${endpoint} failed:`, error.name === 'AbortError' ? 'Timeout' : error.message);
    
    // Simulate network delay for fallback experience
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    return { 
      data: fallbackData, 
      isDemo: true, 
      error: error.name === 'AbortError' ? 'REQUEST_TIMEOUT' : error.message 
    };
  }
};

export const api = {
  /**
   * Send a chat message.
   * Expected backend response: 
   * { 
   *   answer: string, 
   *   sources: string[], 
   *   confidence: string, 
   *   intent: string, 
   *   intelligence: { context, news, insights }
   * }
   */
  chat: async (query, attachments = [], history = []) => {
    // Stage 3 requires 'query' field and 'history' array
    return fetchWithFallback('/chat', {
      method: 'POST',
      body: JSON.stringify({ 
        query: query, 
        attachments: attachments.map(a => ({
          url: a.url,
          name: a.name,
          mimeType: a.mimeType
        })), 
        history 
      })
    }, demoChatResponse);
  },

  /**
   * Get pre-signed upload URL
   */
  getUploadUrl: async (filename, fileType) => {
    try {
      const response = await fetch(buildUrl('/upload-url'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fileName: filename, fileType }),
      });
      if (!response.ok) throw new Error('Failed to get upload URL');
      return await response.json();
    } catch (err) {
      console.error(err);
      // Demo fallback
      return {
        uploadUrl: 'https://demo-upload.com',
        fileUrl: `https://demo-storage.com/${filename}`,
        isDemo: true,
      };
    }
  },

  /**
   * Upload file to S3 (or demo skip)
   */
  uploadToS3: async (uploadUrl, file) => {
    if (uploadUrl.includes('demo-upload.com')) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      return true;
    }
    const response = await fetch(uploadUrl, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type },
    });
    if (!response.ok) {
      throw new Error('File upload failed');
    }
    return true;
  },

  /**
   * Fetch live radar signals.
   * Stage 3: POST /radar
   */
  getRadarSignals: async (query = "") => {
    return fetchWithFallback('/radar', {
      method: 'POST',
      body: JSON.stringify({ query })
    }, demoSignals);
  },

  /**
   * Verify YouTube claims.
   * Stage 3: POST /factcheck with youtube_url
   */
  verifyClaims: async (url) => {
    return fetchWithFallback('/factcheck', {
      method: 'POST',
      body: JSON.stringify({ youtube_url: url })
    }, demoVerifyResult);
  },

  /**
   * Get consolidated dashboard data (Profile, Stats, Insights)
   */
  getDashboardSummary: async () => {
    return fetchWithFallback('/dashboard/summary', {
      method: 'GET'
    }, {
      user_profile: { name: "Arjun Verma", tier: "Pro Beta User" },
      stats: [
        { label: 'AI Analyzed Tickers', value: '1,204', color: '#58A6FF' },
        { label: 'Active Signals', value: '8', color: '#58A6FF' },
        { label: 'Fact-Checks Run', value: '34', color: '#D29922' },
      ],
      market_overview: [
        { name: 'NIFTY 50', change: '+0.42%', up: true },
        { name: 'SENSEX', change: '+0.38%', up: true },
        { label: 'FII/DII Activity', value: 'Net -₹3,200 Cr', up: false }
      ],
      insight: "Banking sector under short-term pressure due to FII outflows, while PSU and energy stocks show accumulation signals."
    });
  },

  /**
   * Get landing page dynamic data (Ticker, Stats)
   */
  getLandingData: async () => {
    return fetchWithFallback('/landing/data', {
      method: 'GET'
    }, {
      news_items: [
        { tag: 'NSE', text: 'NIFTY 50 surges 1.2% on strong FII inflows amid RBI liquidity boost.', up: true },
        { tag: 'BSE', text: 'Reliance Industries Q4 profit beats estimate by ₹2,400 Cr; shares rally 3.1%.', up: true },
      ],
      stats: [
        { value: 98, suffix: '%', label: 'Signal Accuracy', sub: 'vs. 73% industry avg' },
        { value: 12, suffix: 'K+', label: 'Stocks Monitored', sub: 'NSE · BSE · Global' },
      ]
    });
  }
};
