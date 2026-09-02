import React from 'react';
import { MovementType, AdjustmentReasonCode } from '../../types/inventory';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'emerald' | 'amber' | 'rose' | 'sky' | 'indigo' | 'slate' | 'default';
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', size = 'md' }) => {
  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1';
  
  const variants: Record<string, string> = {
    emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20',
    amber: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20',
    rose: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20',
    sky: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20',
    indigo: 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20',
    slate: 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border border-slate-500/20',
    default: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700',
  };

  return (
    <span className={`inline-flex items-center font-medium rounded-full ${sizeClasses} ${variants[variant] || variants.default}`}>
      {children}
    </span>
  );
};

export const MovementBadge: React.FC<{ type: MovementType }> = ({ type }) => {
  switch (type) {
    case 'IN':
      return <Badge variant="emerald">↓ IN (Receipt)</Badge>;
    case 'OUT':
      return <Badge variant="rose">↑ OUT (Dispatch)</Badge>;
    case 'ADJUST':
      return <Badge variant="amber">⟲ ADJUST</Badge>;
    case 'TRANSFER':
      return <Badge variant="sky">⇆ TRANSFER</Badge>;
    default:
      return <Badge variant="slate">{type}</Badge>;
  }
};

export const ReasonBadge: React.FC<{ reason: AdjustmentReasonCode | string }> = ({ reason }) => {
  const reasonColor: Record<string, 'rose' | 'amber' | 'sky' | 'indigo'> = {
    damage: 'rose',
    loss: 'rose',
    miscount: 'amber',
    return: 'sky',
    audit: 'indigo',
  };
  return (
    <Badge variant={reasonColor[reason] || 'slate'} size="sm">
      {reason.toUpperCase()}
    </Badge>
  );
};
