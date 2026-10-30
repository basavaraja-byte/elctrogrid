import React from 'react';
import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KPICardProps {
  title: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendLabel?: string;
  icon: LucideIcon;
  iconColor?: string;
  bgColor?: string;
  description?: string;
  onClick?: () => void;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  change,
  trend,
  trendLabel,
  icon: Icon,
  iconColor = 'text-blue-600',
  bgColor = 'bg-blue-50',
  description,
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm hover:shadow transition-all ${
        onClick ? 'cursor-pointer hover:border-blue-300' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          {title}
        </span>
        <div className={`p-2.5 rounded-lg ${bgColor}`}>
          <Icon className={`w-5 h-5 ${iconColor}`} />
        </div>
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <span className="text-2xl font-bold text-slate-900 tracking-tight">{value}</span>

        {change && (
          <div
            className={`flex items-center text-xs font-medium ${
              trend === 'up'
                ? 'text-emerald-600'
                : trend === 'down'
                ? 'text-rose-600'
                : 'text-slate-500'
            }`}
          >
            {trend === 'up' && <TrendingUp className="w-3.5 h-3.5 mr-1" />}
            {trend === 'down' && <TrendingDown className="w-3.5 h-3.5 mr-1" />}
            {trend === 'neutral' && <Minus className="w-3.5 h-3.5 mr-1" />}
            <span>{change}</span>
          </div>
        )}
      </div>

      {(trendLabel || description) && (
        <p className="mt-2 text-xs text-slate-500 line-clamp-1">
          {trendLabel || description}
        </p>
      )}
    </div>
  );
};

