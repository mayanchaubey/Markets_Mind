import { motion } from 'framer-motion';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ChevronRight,
  BookOpen,
} from 'lucide-react';

const VERDICT_CONFIG = {
  VERIFIED: {
    Icon: CheckCircle2,
    label: 'Verified',
    color: '#1D9E75',
    bg: 'rgba(29,158,117,0.12)',
    border: '#1D9E75',
    barColor: '#1D9E75',
  },
  FALSE: {
    Icon: XCircle,
    label: 'False',
    color: '#E24B4A',
    bg: 'rgba(226,75,74,0.12)',
    border: '#E24B4A',
    barColor: '#E24B4A',
  },
  MISLEADING: {
    Icon: AlertTriangle,
    label: 'Misleading',
    color: '#C1121F',
    bg: 'rgba(193,18,31,0.12)',
    border: '#C1121F',
    barColor: '#C1121F',
  },
  UNKNOWN: {
    Icon: HelpCircle,
    label: 'Unknown',
    color: '#6B7280',
    bg: 'rgba(107,114,128,0.12)',
    border: '#6B7280',
    barColor: '#6B7280',
  },
};

const getConfidence = (verdict) => {
  switch (verdict?.toLowerCase()) {
    case 'verified':
      return 0.8;
    case 'misleading':
      return 0.4;
    case 'false':
      return 0.2;
    default:
      return 0.5;
  }
};

const VerdictBadge = ({ cfg }) => (
  <span
    className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold tracking-tight uppercase"
    style={{
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.border}`,
    }}
  >
    <cfg.Icon className="w-3.5 h-3.5" />
    {cfg.label}
  </span>
);

export const ClaimRow = ({ claim: claimData, index = 0 }) => {
  const { claim, verdict = 'UNKNOWN', explanation, source } = claimData;
  const normalizedVerdict = verdict?.toUpperCase() || 'UNKNOWN';
  const cfg = VERDICT_CONFIG[normalizedVerdict] || VERDICT_CONFIG.UNKNOWN;
  const confidence = claimData.confidence ?? getConfidence(normalizedVerdict);
  const progressColor =
    normalizedVerdict === 'VERIFIED'
      ? '#16a34a'
      : normalizedVerdict === 'MISLEADING'
      ? '#f59e0b'
      : normalizedVerdict === 'FALSE'
      ? '#ef4444'
      : '#6B7280';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.08 }}
      className="card-surface border border-border rounded-2xl hover:shadow-md transition-shadow duration-200"
    >
      <div className="space-y-4 p-5">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <p className="text-base font-semibold text-text-primary leading-snug md:max-w-3xl">
            {claim}
          </p>
          <div className="flex flex-col items-start gap-2 text-right md:items-end">
            <VerdictBadge cfg={cfg} />
            <div className="text-xs text-text-secondary uppercase tracking-wide">
              AI Confidence
              <div className="mt-0.5 text-sm font-semibold" style={{ color: cfg.color }}>
                {Math.round(confidence * 100)}%
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center justify-between text-[10px] text-text-secondary uppercase tracking-wide">
            <span>AI Confidence</span>
            <span style={{ color: progressColor }}>{Math.round(confidence * 100)}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-gray-200 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(100, Math.max(0, confidence * 100))}%`,
                background: progressColor,
              }}
            />
          </div>
          <p className="text-sm text-text-secondary leading-relaxed">{explanation}</p>
        </div>

        <div className="flex items-center justify-between text-[11px] text-text-secondary">
          <div className="flex items-center gap-1">
            <BookOpen className="w-3 h-3" />
            <span>{source}</span>
          </div>
          <div className="inline-flex items-center gap-1 font-semibold" style={{ color: cfg.color }}>
            View Source
            <ChevronRight className="w-3 h-3" />
          </div>
        </div>
      </div>
    </motion.div>
  );
};
