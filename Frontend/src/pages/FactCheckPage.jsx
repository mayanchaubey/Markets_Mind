import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Link,
  Search,
  Zap,
  RefreshCw,
  Paperclip,
} from 'lucide-react';
import { ClaimRow } from '../components/ClaimRow';
import { demoVerifyResult } from '../data/demoClaims';

const FACTCHECK_API_URL =
  import.meta.env.VITE_FACTCHECK_ENDPOINT || 'http://localhost:8000/api/factcheck';
/* ─────────────────────────────────────────────────────────
   SUMMARY STAT CHIP
───────────────────────────────────────────────────────── */
const SummaryStatCard = ({ icon: Icon, count, label, color, description }) => (
  <motion.div
    initial={{ opacity: 0, y: 14 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.4 }}
    className="border border-border rounded-2xl shadow-sm bg-white p-6"
  >
    <div className="flex items-center gap-3 mb-3">
      <div
        className="p-2 rounded-2xl"
        style={{ background: `${color}15`, color }}
      >
        <Icon className="w-5 h-5" />
      </div>
      <span className="text-xs font-semibold text-text-secondary">{label}</span>
    </div>
    <div className="flex items-baseline gap-3">
      <h3 className="text-3xl font-semibold text-text-primary tracking-tight">{count}</h3>
      <span className="text-sm text-text-secondary leading-tight">{description}</span>
    </div>
  </motion.div>
);

export const FactCheckPage = () => {
  const [input, setInput] = useState('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);

  /* Submit FactCheck Query */
  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setIsAnalyzing(true);
    setResult(null);
    setAnalysisError(null);

    try {
      const response = await fetch(FACTCHECK_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtube_url: input.trim() }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Fact check API error ${response.status}`);
      }

      const payload = await response.json();
      const claims = Array.isArray(payload?.claims) ? payload.claims : [];
      const summaryPayload = payload?.summary || {};

      setResult({
        claims,
        summary: {
          true: summaryPayload.verified ?? summaryPayload.true ?? 0,
          false: summaryPayload.false ?? 0,
          misleading: summaryPayload.misleading ?? 0,
        },
        risk_score: payload?.risk_score,
        risk_label: payload?.risk_label
      });
    } catch (err) {
      console.error("Fact check failed:", err);
      setAnalysisError(err.message || 'Unable to verify claims at the moment.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleReset = () => {
    setInput('');
    setResult(null);
    setAnalysisError(null);
  };

  const loadDemoText = () => {
    setInput(demoVerifyResult.originalText);
  };

  const claimRows = result?.claims || [];
  const summary = result?.summary || { true: 0, false: 0, misleading: 0 };
  const unknownCount = Math.max(
    0,
    claimRows.length - (summary.true + summary.false + summary.misleading)
  );

  return (
    <div className="space-y-8 pb-10 bg-white text-text-primary">
      {/* ── HEADER ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-4 bg-white border border-border rounded-2xl shadow-sm p-5"
      >
        <div className="w-12 h-12 rounded-2xl flex items-center justify-center border border-border bg-white shadow-inner">
          <ShieldCheck className="w-6 h-6 text-[#C1121F]" />
        </div>
        <div className="space-y-1">
          <h2 className="text-2xl font-medium text-text-primary tracking-tight">FactCheck AI</h2>
          <p className="text-sm text-text-secondary">Cross-reference finfluencer claims against SEBI disclosures.</p>
          {analysisError && (
            <div className="flex items-center gap-1.5 mt-2 text-xs text-danger-red px-3 py-1 rounded-full border border-danger-red/40 bg-danger-red/10">
              <AlertTriangle className="w-3 h-3" />
              {analysisError}
            </div>
          )}
        </div>
      </motion.div>

      {/* ── INPUT SECTION ── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.98 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="border border-border rounded-2xl bg-white shadow-sm"
      >
        <div className="p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Link className="w-4 h-4 text-[#C1121F]" />
              Paste Transcript or URL
            </h3>
            {!result && !isAnalyzing && (
              <button
                onClick={loadDemoText}
                className="text-xs font-medium text-[#C1121F] hover:text-[#9f0f15] transition-colors"
              >
                Load demo script
              </button>
            )}
          </div>

          <form onSubmit={handleAnalyze} className="space-y-4">
            <div
              className="rounded-2xl border border-border bg-white p-3 transition-all duration-200"
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isAnalyzing || result}
                placeholder="Paste a YouTube video URL, Twitter thread, or directly paste the claims here to verify their authenticity against official market data..."
                className="w-full h-32 md:h-40 resize-none bg-transparent border-none p-2 text-sm text-text-primary placeholder:text-text-secondary focus:outline-none focus:ring-0 focus-visible:ring-2 focus-visible:ring-[#C1121F]/40 leading-relaxed transition-all duration-150"
              />
              <div className="flex items-center justify-between pt-2">
                <div className="flex items-center gap-2">
                  <input
                    type="file"
                    className="hidden"
                    id="factcheck-file-upload"
                    onChange={(e) => {
                      if (e.target.files?.length) {
                        alert(`Selected: ${e.target.files[0].name}. (File upload logic to be implemented)`);
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => document.getElementById('factcheck-file-upload').click()}
                    className="p-1.5 rounded-xl text-text-secondary hover:text-[#C1121F] transition-colors"
                    title="Attach file"
                  >
                    <Paperclip className="w-4 h-4" />
                  </button>
                  <span className="text-[10px] text-text-secondary">PDF, DOCX, TXT, CSV supported</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Zap className="w-4 h-4 text-[#C1121F]" />
                Cross-checking 40+ official sources
              </div>

              {!result ? (
                <button
                  type="submit"
                  disabled={!input.trim() || isAnalyzing}
                className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-[#C1121F] text-white text-sm font-semibold shadow-lg transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed hover:bg-[#941018] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#C1121F]/50"
                >
                  {isAnalyzing ? (
                    <>
                      <motion.div
                        className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
                      />
                      Analyzing claims...
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Run fact-check
                    </>
                  )}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleReset}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-lg border border-gray-300 bg-white text-sm font-semibold text-text-primary shadow-sm hover:border-border"
                >
                  <RefreshCw className="w-4 h-4 text-text-primary" />
                  New analysis
                </button>
              )}
            </div>
          </form>
        </div>
      </motion.div>

      {/* ── RESULTS SECTION ── */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="space-y-8"
          >
            {/* Stats Row */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
              <SummaryStatCard
                icon={CheckCircle2}
                count={summary.true}
                label="Verified"
                color="#1d9e75"
                description="Factually accurate claims"
              />
              <SummaryStatCard
                icon={AlertTriangle}
                count={summary.misleading}
                label="Misleading"
                color="#ba7517"
                description="Lacks context or nuance"
              />
              <SummaryStatCard
                icon={XCircle}
                count={summary.false}
                label="False"
                color="#e24b4a"
                description="Demonstrably incorrect"
              />
              <SummaryStatCard
                icon={HelpCircle}
                count={unknownCount}
                label="Unknown"
                color="#2d6aa0"
                description="Unable to verify via sources"
              />
            </div>

            {/* Claims Breakdown Title */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 py-3 border-b border-border">
              <div className="flex items-center gap-3">
                <Search className="w-4 h-4 text-[#C1121F]" />
                <h3 className="text-sm font-semibold text-text-primary">
                  Extraction & Verdict Breakdown
                </h3>
              </div>
              {result.risk_label && (
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <span className="text-text-secondary uppercase tracking-wider text-[11px]">Overall Video Risk:</span>
                  <span className={`px-3 py-1 rounded-full text-xs border ${
                    result.risk_label === 'High Risk' ? 'bg-red-50 text-red-600 border-red-200' : 
                    result.risk_label === 'Moderate Risk' ? 'bg-amber-50 text-amber-600 border-amber-200' : 
                    'bg-green-50 text-green-600 border-green-200'
                  }`}>
                    {result.risk_label} ({result.risk_score})
                  </span>
                </div>
              )}
            </div>

            {/* Claim Rows List */}
            <div className="space-y-4">
              {claimRows.length === 0 ? (
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center justify-center gap-2 p-10 border border-border rounded-2xl bg-background-card text-sm text-text-secondary"
                >
                  <Zap className="w-6 h-6 text-[#C1121F]" />
                  <p>No claims were extracted from the provided URL.</p>
                </motion.div>
              ) : (
                claimRows.map((claimObj, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: i * 0.1 }}
                  >
                    <ClaimRow claim={claimObj} index={i} />
                  </motion.div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
