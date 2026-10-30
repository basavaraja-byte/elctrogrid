import React from 'react';
import { JobStatus, JobPriority, AlertSeverity } from '../../types';

interface StatusBadgeProps {
  status: JobStatus | string;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '', size = 'md' }) => {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-medium',
    lg: 'px-3 py-1.5 text-sm font-medium',
  }[size];

  const getStatusConfig = (s: string) => {
    switch (s.toLowerCase()) {
      case 'submitted':
        return { label: 'Submitted', bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200' };
      case 'under_review':
        return { label: 'Under Review', bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200' };
      case 'validated':
        return { label: 'Validated', bg: 'bg-teal-50', text: 'text-teal-700', border: 'border-teal-200' };
      case 'scheduling':
        return { label: 'Scheduling', bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200' };
      case 'awaiting_approval':
        return { label: 'Awaiting Approval', bg: 'bg-amber-50', text: 'text-amber-800', border: 'border-amber-300' };
      case 'assigned':
        return { label: 'Assigned', bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200' };
      case 'dispatched':
        return { label: 'Dispatched', bg: 'bg-blue-50', text: 'text-blue-800', border: 'border-blue-300' };
      case 'acknowledged':
        return { label: 'Acknowledged', bg: 'bg-cyan-50', text: 'text-cyan-700', border: 'border-cyan-200' };
      case 'en_route':
        return { label: 'En Route', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' };
      case 'in_progress':
        return { label: 'In Progress', bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200' };
      case 'on_hold':
        return { label: 'On Hold', bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' };
      case 'completed':
        return { label: 'Completed', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' };
      case 'customer_confirmed':
        return { label: 'Confirmed', bg: 'bg-green-50', text: 'text-green-800', border: 'border-green-300' };
      case 'closed':
        return { label: 'Closed', bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-300' };
      case 'cancelled':
        return { label: 'Cancelled', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200' };
      case 'unassigned':
        return { label: 'Unassigned', bg: 'bg-gray-100', text: 'text-gray-700', border: 'border-gray-300' };
      default:
        return { label: s.replace(/_/g, ' '), bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200' };
    }
  };

  const config = getStatusConfig(status);

  return (
    <span
      className={`inline-flex items-center rounded-full border ${config.bg} ${config.text} ${config.border} ${sizeClasses} ${className} capitalize`}
    >
      <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current opacity-70"></span>
      {config.label}
    </span>
  );
};

export const PriorityBadge: React.FC<{ priority: JobPriority; className?: string }> = ({
  priority,
  className = '',
}) => {
  const configs = {
    emergency: { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300', label: 'EMERGENCY' },
    high: { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-300', label: 'High' },
    medium: { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-200', label: 'Medium' },
    low: { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200', label: 'Low' },
  }[priority] || { bg: 'bg-slate-100', text: 'text-slate-700', border: 'border-slate-200', label: priority };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider border ${configs.bg} ${configs.text} ${configs.border} ${className}`}
    >
      {priority === 'emergency' && (
        <span className="w-1.5 h-1.5 rounded-full mr-1 bg-red-600 animate-pulse"></span>
      )}
      {configs.label}
    </span>
  );
};

export const SeverityBadge: React.FC<{ severity: AlertSeverity; className?: string }> = ({
  severity,
  className = '',
}) => {
  const configs = {
    critical: { bg: 'bg-red-500 text-white', label: 'CRITICAL' },
    high: { bg: 'bg-orange-500 text-white', label: 'HIGH' },
    medium: { bg: 'bg-amber-500 text-white', label: 'MEDIUM' },
    low: { bg: 'bg-slate-500 text-white', label: 'LOW' },
  }[severity] || { bg: 'bg-slate-500 text-white', label: severity };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold tracking-wider uppercase ${configs.bg} ${className}`}
    >
      {configs.label}
    </span>
  );
};

