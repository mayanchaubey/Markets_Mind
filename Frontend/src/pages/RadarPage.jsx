import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Zap, TrendingUp, TrendingDown, Minus, Filter, LayoutGrid, AlertCircle, Loader } from 'lucide-react';
import { SignalCard } from '../components/SignalCard';
import { api } from '../services/api';

const parseSignalType = (value) => {
  const normalized = (value || '').toString().toUpperCase();
  if (['BULLISH', 'BEARISH', 'NEUTRAL'].includes(normalized)) return normalized;
  if (normalized.includes('BULL')) return 'BULLISH';
  if (normalized.includes('BEAR')) return 'BEARISH';
  return 'NEUTRAL';
};

const normalizeScore = (score) => {
  if (typeof score !== 'number' || Number.isNaN(score)) return 0;
  if (Math.abs(score) > 1) {
    return Math.max(-1, Math.min(1, score / 100));
  }
  return Math.max(-1, Math.min(1, score));
};

const mapOpportunity = (opportunity = {}) => {
  const ticker = opportunity.ticker || 'N/A';
  const rawSignalText = opportunity.description || opportunity.signal || opportunity.summary || '';
  const signalType = opportunity.signal_type
    ? opportunity.signal_type.toUpperCase()
    : parseSignalType(rawSignalText);

  const scoreValue =
    typeof opportunity.score === 'number'
      ? opportunity.score
      : typeof opportunity.finbert_score === 'number'
        ? opportunity.finbert_score
        : 0;

  const description = rawSignalText || `Opportunity score ${scoreValue.toFixed ? scoreValue.toFixed(2) : scoreValue}`;

  return {
    ticker,
    signal_type: signalType,
    description,
    finbert_score: normalizeScore(scoreValue),
    source: opportunity.source || 'MarketMind Radar',
    timestamp: opportunity.timestamp,
  };
};
/* ─────────────────────────────────────────────────────────
   STATS CARDS
───────────────────────────────────────────────────────── */
const RadarStatCard = ({ title, value, sub, Icon }) => (
  <motion.div
    initial={{ opacity: 0, y: 14 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4 }}
    className="bg-white border border-border rounded-2xl shadow-sm p-5 space-y-3"
  >
    <div className="flex items-center gap-2 mb-1">
      <div className="p-1.5 rounded-full border border-border">
        <Icon className="w-4 h-4 text-text-secondary" />
      </div>
      <span className="text-sm font-semibold text-text-secondary">{title}</span>
    </div>
    <div className="flex items-baseline gap-3">
      <h3 className="text-3xl font-semibold text-text-primary tracking-tight">{value}</h3>
      <span className="text-sm font-medium text-text-secondary">{sub}</span>
    </div>
  </motion.div>
);

export const RadarPage = () => {
  const [filter, setFilter] = useState('ALL');
  const [opportunities, setOpportunities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const fetchOpportunities = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data: payload, error } = await api.getRadarSignals('');
        if (!mounted) return;
        if (!payload) {
          throw new Error(error || 'Empty radar response');
        }
        const rawOpportunities = Array.isArray(payload)
          ? payload
          : Array.isArray(payload?.opportunities)
            ? payload.opportunities
            : Array.isArray(payload?.data)
              ? payload.data
              : [];
        setOpportunities(rawOpportunities.map(mapOpportunity));
      } catch (err) {
        if (!mounted) return;
        console.error('Radar fetch failed:', err);
        setError(err.message || 'Unable to fetch radar data.');
        setOpportunities([]);
      } finally {
        if (!mounted) return;
        setIsLoading(false);
      }
    };

    fetchOpportunities();
    return () => {
      mounted = false;
    };
  }, []);

  const allOpportunities = opportunities;

  // Filter list (only affects visible cards)
  const normalizedFilter = filter.toLowerCase();

  const filteredOpportunities = useMemo(() => {
    console.debug('Radar dataset', {
      filter,
      normalizedFilter,
      totalSignals: allOpportunities.length,
      opportunities: allOpportunities,
    });

    if (normalizedFilter === 'all') {
      console.debug('Radar filter result', {
        filter,
        normalizedFilter,
        filteredCount: allOpportunities.length,
      });
      return allOpportunities;
    }

    const filtered = allOpportunities.filter((o) => {
      const signalType = (o.signal_type || '').toLowerCase();

      if (signalType === normalizedFilter) return true;

      if (!signalType) {
        const text = (o.description || o.signal || '').toLowerCase();
        if (normalizedFilter === 'bullish') return text.includes('bull') || text.includes('buy');
        if (normalizedFilter === 'bearish') return text.includes('bear') || text.includes('sell');
        if (normalizedFilter === 'neutral')
          return text && !text.includes('bull') && !text.includes('bear');
      }

      return false;
    });

    console.debug('Radar filter result', {
      filter,
      normalizedFilter,
      filteredCount: filtered.length,
    });

    return filtered;
  }, [filter, normalizedFilter, allOpportunities]);

  // Derived stats (always from full dataset)
  const totalSignals = allOpportunities.length;
  const bullishCount = allOpportunities.filter((s) => s.signal_type === 'BULLISH').length;
  const bearishCount = allOpportunities.filter((s) => s.signal_type === 'BEARISH').length;
  const bullishRatio = Math.round((bullishCount / totalSignals) * 100) || 0;

  return (
    <div className="space-y-10 pb-10 px-4 sm:px-6 md:px-8 max-w-6xl mx-auto">
      {/* ── HEADER ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-2xl border border-border flex items-center justify-center bg-white shadow-sm">
            <Activity className="w-5 h-5 text-accent-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-text-primary">Opportunity Radar</h2>
            <div className="flex items-center gap-1 text-xs text-text-secondary mt-1">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-primary inline-flex" />
              Live feed — sentiment signals across 12,000+ NSE/BSE tickers
            </div>
            {error && !isLoading && (
              <div className="flex items-center gap-1.5 mt-2 px-3 py-1 rounded-full bg-warning-amber/10 border border-warning-amber/20 text-[11px] text-warning-amber">
                <AlertCircle className="w-3 h-3" />
                Radar feed paused. Retrying shortly.
              </div>
            )}
          </div>
        </div>

        {/* Global actions (mock) */}
        <div className="flex items-center gap-2">
          <button className="flex items-center gap-2 px-4 py-2 rounded-2xl border border-border bg-white text-sm font-semibold text-text-primary shadow-sm hover:shadow">
            <LayoutGrid className="w-4 h-4 text-text-secondary" />
            Grid view
          </button>
        </div>
      </motion.div>

      {/* ── STATS ROW ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <RadarStatCard
          title="Total Signals"
          value={totalSignals}
          sub="last 24h"
          Icon={Activity}
          color="#58A6FF"
        />
        <RadarStatCard
          title="Market Bias"
          value={`${bullishRatio}%`}
          sub="Bullish"
          Icon={bullishRatio > 50 ? TrendingUp : TrendingDown}
          color={bullishRatio > 50 ? '#58A6FF' : '#F85149'}
        />
        <RadarStatCard
          title="Bullish Alerts"
          value={bullishCount}
          sub="tickers"
          Icon={TrendingUp}
          color="#58A6FF"
        />
        <RadarStatCard
          title="Bearish Alerts"
          value={bearishCount}
          sub="tickers"
          Icon={TrendingDown}
          color="#e24b4a"
        />
      </div>

      {/* ── FILTERS AND GRID ── */}
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2 border-b border-border">
          <div className="flex items-center gap-2 text-sm font-semibold text-text-secondary">
            <Filter className="w-4 h-4 text-accent-primary" />
            Signal stream
          </div>

          <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1 sm:pb-0">
            {['ALL', 'BULLISH', 'BEARISH', 'NEUTRAL'].map((type) => {
              const isActive = filter === type;
              return (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 border ${isActive ? 'bg-accent-primary text-white border-accent-primary' : 'bg-white text-text-secondary border-border hover:bg-slate-50'}`}
                >
                  {type === 'ALL' ? 'All' : type.charAt(0) + type.slice(1).toLowerCase()}
                </button>
              );
            })}
          </div>
        </div>

        {/* The Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 min-h-[400px]">
          <AnimatePresence mode="popLayout">
            {isLoading ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="col-span-1 lg:col-span-2 flex flex-col items-center justify-center p-10 bg-white border border-border rounded-2xl shadow-sm text-text-secondary"
              >
                <Loader className="w-8 h-8 animate-spin mb-4 text-accent-primary" />
                <p className="text-sm">Syncing live signals matrix...</p>
              </motion.div>
            ) : error ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="col-span-1 lg:col-span-2 flex flex-col items-center justify-center p-10 bg-white border border-border rounded-2xl shadow-sm text-text-secondary space-y-3"
              >
                <AlertCircle className="w-8 h-8 text-warning-amber" />
                <h3 className="text-text-primary font-semibold">Unable to load radar data</h3>
                <p className="text-sm">{error}</p>
              </motion.div>
            ) : filteredOpportunities.length > 0 ? (
              filteredOpportunities.map((signal, i) => (
                <motion.div
                  key={signal.ticker}
                  layout
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.96 }}
                  transition={{ duration: 0.3, delay: i * 0.04 }}
                >
                  <SignalCard signal={signal} index={i} />
                </motion.div>
              ))
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="col-span-1 lg:col-span-2 flex flex-col items-center justify-center p-12 text-center bg-white border border-border rounded-2xl shadow-sm"
              >
                <div className="w-16 h-16 mb-4 rounded-full border border-border flex items-center justify-center">
                  <Minus className="w-6 h-6 text-text-muted" />
                </div>
                <h3 className="text-text-primary font-semibold mb-1">No signals found</h3>
                <p className="text-text-secondary text-sm">There are no {filter.toLowerCase()} signals matching your criteria at this moment.</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── FOOTER INDICATOR ── */}
      <div className="flex items-center justify-center gap-2 pt-6 pb-2 text-xs text-text-secondary">
        <Zap className="w-4 h-4 text-accent-primary" />
        MarketMind AI Engine is actively scanning 12,000+ sources
      </div>
    </div>
  );
};
