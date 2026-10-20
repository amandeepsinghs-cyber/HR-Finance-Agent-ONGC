'use client';

import React from 'react';
import { AnswerContract } from '@/contracts/answerContract';
import { Clock, PieChart, BarChart2, Table as TableIcon, FileText, MapPin, ShieldAlert } from 'lucide-react';

interface HistoryItem {
  id: string;
  question: string;
  contract: AnswerContract;
  timestamp: string;
}

interface HistoryStripProps {
  history: HistoryItem[];
  currentIndex: number;
  onSelect: (item: HistoryItem, index: number) => void;
  isDark?: boolean;
}

export const HistoryStrip: React.FC<HistoryStripProps> = ({
  history,
  currentIndex,
  onSelect,
  isDark = false,
}) => {
  if (history.length <= 1) return null;

  const getVisualIcon = (type?: string) => {
    switch (type) {
      case 'chart':
        return <PieChart className="w-3.5 h-3.5 text-accent" />;
      case 'table':
        return <TableIcon className="w-3.5 h-3.5 text-emerald-500" />;
      case 'document':
        return <FileText className="w-3.5 h-3.5 text-indigo-500" />;
      case 'map':
        return <MapPin className="w-3.5 h-3.5 text-amber-500" />;
      case 'refusal':
        return <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />;
      default:
        return <BarChart2 className="w-3.5 h-3.5 text-zinc-400" />;
    }
  };

  return (
    <div className="w-full flex items-center gap-3 py-2 px-1 overflow-x-auto select-none">
      <div className="flex items-center gap-1.5 text-xs font-semibold text-zinc-400 dark:text-zinc-500 shrink-0 uppercase tracking-wider">
        <Clock className="w-3.5 h-3.5" />
        <span>Canvas History:</span>
      </div>

      <div className="flex items-center gap-2">
        {history.map((item, idx) => {
          const isActive = idx === currentIndex;
          const visType = item.contract.visual?.type || 'chart';
          const title = item.contract.visual?.title || item.question;

          return (
            <button
              key={item.id + idx}
              onClick={() => onSelect(item, idx)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-medium transition-all shrink-0 max-w-[220px] truncate ${
                isActive
                  ? 'border-accent bg-blue-50/80 dark:bg-accent/20 text-accent font-semibold shadow-sm'
                  : isDark
                  ? 'border-zinc-800 bg-zinc-900/60 hover:bg-zinc-800 text-zinc-300'
                  : 'border-zinc-200 bg-white hover:bg-zinc-50 text-zinc-700 shadow-xs'
              }`}
              title={title}
            >
              {getVisualIcon(visType)}
              <span className="truncate">{title}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
