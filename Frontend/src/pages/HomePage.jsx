import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  User, Activity, ShieldCheck, 
  ArrowUpRight, ArrowDownRight, TrendingUp,
  LayoutDashboard, MessageSquare, ChevronRight
} from 'lucide-react';
import { SignalCard } from '../components/SignalCard';
import { api } from '../services/api';
import logo from '../assets/logo.png';

export const HomePage = () => {
  const navigate = useNavigate();
  const [hotPicks, setHotPicks] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [newsItems, setNewsItems] = useState([]);
  const [activeNewsIndex, setActiveNewsIndex] = useState(0);
  const [isLoadingNews, setIsLoadingNews] = useState(true);
  const [newsError, setNewsError] = useState(null);
  const [dashboardError, setDashboardError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        // Fetch hot picks and dashboard summary in parallel
        const [radarRes, dashboardRes] = await Promise.all([
          api.getRadarSignals(),
          api.getDashboardSummary()
        ]);

        const radarData = radarRes.data || radarRes;
        const sorted = [...radarData].sort((a, b) => Math.abs(b.finbert_score) - Math.abs(a.finbert_score));
        setHotPicks(sorted.slice(0, 2));

        const payload = dashboardRes.data || dashboardRes;
        console.log("Dashboard API:", payload);
        setDashboardData(payload);
        setDashboardError(null);
      } catch (err) {
        console.error("Dashboard fetch failed:", err);
        setDashboardError(err?.message || 'Unable to load dashboard data');
        setDashboardData(null);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    let mounted = true;
    const fetchNews = async () => {
      setIsLoadingNews(true);
      try {
        const { data: payload } = await api.getLandingData();
        console.log('News API:', payload);
        if (!mounted) return;
        const items = Array.isArray(payload?.news)
          ? payload.news
          : Array.isArray(payload?.news_items)
            ? payload.news_items
            : [];
        setNewsItems(items);
        setActiveNewsIndex(0);
        setNewsError(null);
      } catch (err) {
        if (!mounted) return;
        console.error('Landing news fetch failed:', err);
        setNewsItems([]);
        setNewsError(err?.message || 'Unable to load news');
      } finally {
        if (!mounted) return;
        setIsLoadingNews(false);
      }
    };

    fetchNews();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!newsItems.length) return;
    const intervalId = setInterval(() => {
      setActiveNewsIndex((prev) => (prev + 1) % newsItems.length);
    }, 10000);
    return () => clearInterval(intervalId);
  }, [newsItems]);

  useEffect(() => {
    if (newsItems.length > 0) {
      setActiveNewsIndex(0);
    }
  }, [newsItems]);

  const formatValue = (value) => (typeof value === 'number'
    ? value.toLocaleString('en-IN', { maximumFractionDigits: Number.isInteger(value) ? 0 : 2 })
    : '--');
  const formatPercent = (value) => (value !== undefined && value !== null
    ? `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
    : '--');

  const user = dashboardData?.user_profile || { name: "User", tier: "Research Beta" };
  const statsSource = dashboardData?.stats;
  const platformStats = [
    { label: 'Signals', value: statsSource?.active_signals, icon: LayoutDashboard, formatter: formatValue },
    { label: 'Analyzed Tickers', value: statsSource?.tickers_analyzed, icon: MessageSquare, formatter: formatValue },
    { label: 'Accuracy', value: statsSource?.accuracy_rate, icon: ShieldCheck, formatter: (val) => (val !== undefined && val !== null ? `${val.toFixed(1)}%` : '--') },
  ];
  const marketOverview = dashboardData?.market_overview;
  const marketCards = [
    {
      name: 'NIFTY 50',
      value: marketOverview?.nifty50?.value,
      change: marketOverview?.nifty50?.change_percent,
      changeRaw: marketOverview?.nifty50?.change,
      up: marketOverview?.nifty50?.change >= 0,
    },
    {
      name: 'SENSEX',
      value: marketOverview?.sensex?.value,
      change: marketOverview?.sensex?.change_percent,
      changeRaw: marketOverview?.sensex?.change,
      up: marketOverview?.sensex?.change >= 0,
    },
  ];
  const topGainers = marketOverview?.top_gainers || [];
  const topLosers = marketOverview?.top_losers || [];
  const insight = dashboardData?.daily_insight || "Market tracking active. Connect to backend for real-time insights.";
  const currentNews = newsItems.length > 0
    ? newsItems[activeNewsIndex % newsItems.length]
    : null;

  return (
    <div className="space-y-8 pb-10 max-w-5xl mx-auto w-full bg-white text-text-primary">
      {/* ── HEADER & PROFILE ── */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid gap-6 lg:grid-cols-[1fr_minmax(280px,360px)] items-start"
      >
        <div className="flex flex-col gap-6">
          <div className="w-16 h-16 rounded-full border border-border flex items-center justify-center bg-white shadow-inner">
            <User className="w-8 h-8 text-[#C1121F]" />
          </div>
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-text-primary">Welcome back, {user.name}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs font-semibold px-2 py-0.5 rounded border border-[#C1121F] text-[#C1121F]">
                {user.tier}
              </span>
              <span className="text-xs text-text-secondary">Market tracking active</span>
            </div>
          </div>
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white border border-border rounded-2xl shadow-sm p-5 w-full"
          >
            <h3 className="text-sm font-semibold text-[#C1121F] uppercase tracking-[0.6em] mb-3">Market Headlines</h3>
            {isLoadingNews ? (
              <div className="space-y-3">
                {[1, 2].map((index) => (
                  <div key={index} className="space-y-2 animate-pulse">
                    <div className="h-3 rounded bg-border w-32" />
                    <div className="h-5 rounded bg-border w-full" />
                    <div className="h-3 rounded bg-border/70 w-2/3" />
                  </div>
                ))}
              </div>
            ) : newsError ? (
              <p className="text-sm text-danger-red">{newsError}</p>
            ) : newsItems.length > 0 && currentNews ? (
            <a
              href={currentNews.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.4em] text-[#C1121F] border border-[#C1121F] rounded-full">
                    {currentNews.tag}
                  </span>
                  <span className="text-[10px] text-text-muted">{currentNews.time}</span>
                </div>
              </div>
              <h3 className="text-lg font-semibold text-text-primary leading-tight">
                {currentNews.headline}
              </h3>
              <div className="text-[13px] font-semibold text-[#E8272A] hover:underline transition-colors">
                Read more →
              </div>
            </a>
            ) : (
              <p className="text-sm text-text-secondary">No news available.</p>
            )}
          </motion.div>
        </div>

        <div className="w-full flex justify-end">
          <div className="w-full max-w-sm lg:max-w-md lg:sticky lg:top-6">
            {/* Market Overview Mini-Card */}
            <div className="bg-white border border-border rounded-2xl shadow-sm p-5 space-y-3">
              {marketCards.map((item) => (
                <div key={item.name} className="flex justify-between items-center text-sm">
                  <div>
                    <span className="text-text-primary">{item.name}</span>
                    <p className="text-[10px] text-text-secondary">{formatValue(item.value)}</p>
                  </div>
                  <div className={`flex flex-col items-end gap-1 ${item.up ? 'text-[#1D9E75]' : 'text-[#E24B4A]'}`}>
                    <span className="flex items-center gap-1 text-sm">
                      {item.up ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {formatPercent(item.change)}
                    </span>
                    {item.changeRaw !== undefined && item.changeRaw !== null && (
                      <span className="text-[10px] text-text-secondary">
                        {item.changeRaw >= 0 ? '+' : ''}
                        {item.changeRaw}
                      </span>
                    )}
                  </div>
                </div>
              ))}
              <div className="flex justify-between items-center text-xs border-t border-border pt-2 text-text-secondary">
                <span>Subscription</span>
                <span className={dashboardData?.user_profile?.subscription_status === 'active' ? 'text-[#1D9E75]' : 'text-text-secondary'}>
                  {dashboardData?.user_profile?.subscription_status || '—'}
                </span>
              </div>
              {(topGainers.length > 0 || topLosers.length > 0) && (
                <div className="space-y-3 pt-3 border-t border-border/30">
                  {topGainers.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-[10px] uppercase tracking-[0.4em] text-text-muted">Top Gainers</p>
                      {topGainers.map((item) => (
                        <div key={item.ticker} className="flex justify-between items-center text-sm">
                          <span className="text-text-primary">{item.ticker}</span>
                          <span className="text-[#1D9E75] text-xs font-semibold">{item.change}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {topLosers.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-[10px] uppercase tracking-[0.4em] text-text-muted">Top Losers</p>
                      {topLosers.map((item) => (
                        <div key={item.ticker} className="flex justify-between items-center text-sm">
                          <span className="text-text-primary">{item.ticker}</span>
                          <span className="text-[#E24B4A] text-xs font-semibold">{item.change}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── AI MARKET INSIGHT ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4 }}
        className="flex flex-col sm:flex-row gap-4 rounded-2xl border border-border bg-white shadow-sm p-6"
      >
        <div className="w-12 h-12 rounded-full flex items-center justify-center border border-border bg-white">
          <img src={logo} alt="MarketMind AI" className="w-15 h-15 object-contain" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-medium text-text-secondary uppercase tracking-[0.4em]">AI Market Insight</h3>
            <span className="inline-flex h-1.5 w-1.5 rounded-full bg-[#C1121F]" />
          </div>
          <span className="block h-[1px] w-10 bg-[#C1121F]/20" />
          <p className="text-base text-text-primary leading-relaxed max-w-3xl italic tracking-tight">
            "{insight}"
          </p>
          {dashboardError && (
            <p className="text-[10px] text-danger-red mt-2">
              {dashboardError}
            </p>
          )}
        </div>
      </motion.div>

      {/* ── PLATFORM STATS ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        {platformStats.map((stat, i) => {
          const Icon = stat.icon;
          const displayValue = stat.formatter ? stat.formatter(stat.value) : (stat.value ?? '--');
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i, duration: 0.4 }}
              className="flex items-center gap-4 rounded-2xl border border-border bg-white shadow-sm p-6"
            >
              <div className="w-10 h-10 rounded-lg border border-border bg-slate-50 flex items-center justify-center text-text-secondary">
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-2xl font-semibold text-text-primary leading-tight">{displayValue}</p>
                <p className="text-xs text-text-secondary uppercase tracking-[0.3em]">{stat.label}</p>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* ── MAIN DASHBOARD GRID ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Col: Core Modules (Quick Launch) */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-text-secondary">
              <LayoutDashboard className="w-5 h-5 text-text-secondary" />
              Quick Launch
            </div>
            <span className="text-xs text-text-secondary">Primary</span>
          </div>

          <NavLink to="/chat" className="group block rounded-2xl border border-border bg-white shadow-sm p-6 transition duration-200 ease-in-out hover:shadow">
            <div className="flex justify-between items-start mb-3">
              <div className="w-10 h-10 rounded-lg border border-border flex items-center justify-center text-text-secondary">
                <MessageSquare className="w-5 h-5" />
              </div>
              <ChevronRight className="w-4 h-4 text-text-secondary transition-colors group-hover:text-[#C1121F]" />
            </div>
            <h4 className="text-sm font-semibold text-text-primary mb-1">AI Terminal</h4>
            <p className="text-xs text-text-secondary leading-relaxed">Chat with our fine-tuned language model about market trends and data.</p>
          </NavLink>

          <NavLink to="/radar" className="group block rounded-2xl border border-border bg-white shadow-sm p-6 transition duration-200 ease-in-out hover:shadow">
            <div className="flex justify-between items-start mb-3">
              <div className="w-10 h-10 rounded-lg border border-border flex items-center justify-center text-text-secondary">
                <Activity className="w-5 h-5" />
              </div>
              <ChevronRight className="w-4 h-4 text-text-secondary transition-colors group-hover:text-[#C1121F]" />
            </div>
            <h4 className="text-sm font-semibold text-text-primary mb-1">Opportunity Radar</h4>
            <p className="text-xs text-text-secondary leading-relaxed">Live signals and trend analysis powered by our FinBERT engine.</p>
          </NavLink>

          <NavLink to="/factcheck" className="group block rounded-2xl border border-border bg-white shadow-sm p-6 transition duration-200 ease-in-out hover:shadow">
            <div className="flex justify-between items-start mb-3">
              <div className="w-10 h-10 rounded-lg border border-border flex items-center justify-center text-text-secondary">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <ChevronRight className="w-4 h-4 text-text-secondary transition-colors group-hover:text-[#C1121F]" />
            </div>
            <h4 className="text-sm font-semibold text-text-primary mb-1">Finfluencer Fact-Check</h4>
            <p className="text-xs text-text-secondary leading-relaxed">Verify claims and rumors against official SEBI and NSE disclosures.</p>
          </NavLink>
        </div>

        {/* Right Col: Today's Hot Picks */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2 flex-wrap text-text-secondary">
              <TrendingUp className="w-4 h-4 text-[#C1121F]" />
              <h3 className="text-sm font-semibold text-text-secondary">Today's Hot Signals</h3>
              <div className="hidden sm:flex items-center gap-2 ml-2 pl-2 border-l-2 border-[#E5E7EB]">
                <span className="text-xs text-text-secondary">Last updated: 2 min ago</span>
              </div>
            </div>
            <NavLink to="/radar" className="text-sm font-semibold text-text-secondary hover:text-[#C1121F]">
              View all radar &rarr;
            </NavLink>
          </div>

          <div className="bg-white border border-border rounded-2xl shadow-sm p-6 min-h-[300px]">
             {isLoading ? (
                <div className="space-y-5">
                 {[1, 2].map((i) => (
                   <div key={i} className="animate-pulse p-4 rounded-2xl border border-border bg-slate-100">
                     <div className="flex items-start gap-4 mb-3">
                       <div className="w-16 h-8 bg-border rounded" />
                       <div className="w-20 h-6 bg-border/50 rounded" />
                     </div>
                     <div className="h-4 bg-border/50 rounded w-full mb-2" />
                     <div className="h-4 bg-border/50 rounded w-2/3 mb-4" />
                     <div className="h-6 bg-border rounded-full w-full" />
                   </div>
                 ))}
               </div>
             ) : (
               <div className="space-y-5">
                 {hotPicks.map((signal, i) => (
                   <motion.div
                     key={signal.ticker}
                     initial={{ opacity: 0, x: 20 }}
                     animate={{ opacity: 1, x: 0 }}
                     transition={{ duration: 0.4, delay: i * 0.15 }}
                     onClick={() => navigate('/chat', { state: { query: `Analyze the recent ${signal.signal_type} signal for ${signal.ticker}` } })}
                     className="block cursor-pointer"
                   >
                     <SignalCard signal={signal} index={i} compact={true} />
                   </motion.div>
                 ))}
               </div>
             )}
          </div>
        </div>

      </div>

    </div>
  );
};
