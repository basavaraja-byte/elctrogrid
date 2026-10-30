import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { formatDateTimeIST } from '../../utils/formatters';
import { AuditLogEntry } from '../../types';
import { DataTable, Column } from '../../components/common/DataTable';
import {
  ScrollText,
  Search,
  Filter,
  ShieldCheck,
  CheckCircle2,
  Clock,
  User,
  Info,
} from 'lucide-react';

export const SupervisorAuditPage: React.FC = () => {
  const { auditLogs } = useApp();
  const [searchQuery, setSearchQuery] = useState('');
  const [actionFilter, setActionFilter] = useState('all');

  const filteredLogs = auditLogs.filter((log) => {
    if (actionFilter !== 'all' && !log.action.toLowerCase().includes(actionFilter.toLowerCase())) {
      return false;
    }
    if (
      searchQuery.trim() &&
      !log.action.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !log.userName.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !log.entityId.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !(log.reason && log.reason.toLowerCase().includes(searchQuery.toLowerCase()))
    ) {
      return false;
    }
    return true;
  });

  const columns: Column<AuditLogEntry>[] = [
    {
      header: 'Timestamp (IST)',
      cell: (log) => (
        <span className="font-mono text-xs text-slate-500 whitespace-nowrap">
          {formatDateTimeIST(log.timestamp)}
        </span>
      ),
    },
    {
      header: 'Action / Event',
      cell: (log) => (
        <div>
          <span className="font-bold text-slate-900 block text-xs">{log.action}</span>
          <span className="text-[11px] text-slate-500 font-mono">
            {log.entityType.toUpperCase()}: {log.entityId}
          </span>
        </div>
      ),
    },
    {
      header: 'Actor / Subsystem',
      cell: (log) => (
        <div className="text-xs">
          <span className="font-semibold text-slate-800 block">{log.userName}</span>
          <span className="text-[10px] text-blue-600 font-medium capitalize">
            {log.userRole.replace('_', ' ')}
          </span>
        </div>
      ),
    },
    {
      header: 'Operational Details',
      cell: (log) => (
        <div className="text-xs text-slate-600 max-w-md truncate">
          {log.reason || (log.newValue ? `Value changed to: ${log.newValue}` : log.action)}
        </div>
      ),
    },
    {
      header: 'Status',
      cell: () => (
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
          <CheckCircle2 className="w-3 h-3" />
          Verified
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              System Audit Trail & Compliance Log
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Monitoring Only
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Immutable, cryptographically verifiable operational record of all grid lifecycle events
          </p>
        </div>

        <div className="px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700">
          Total Log Entries: {auditLogs.length}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by action, actor, target ID, or event details..."
              className="w-full pl-9 pr-3.5 py-2 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="all">All Lifecycle Actions</option>
            <option value="TRANSITION">Status Transitions</option>
            <option value="AUTO_SCHEDULE">Automated Scheduling</option>
            <option value="SUPERVISOR">Supervisor Observations</option>
            <option value="DISPATCH">Dispatches</option>
          </select>
        </div>
      </div>

      {/* Main DataTable */}
      <DataTable
        columns={columns}
        data={filteredLogs}
        pageSize={15}
        emptyMessage="No audit records found matching the specified search criteria."
      />
    </div>
  );
};
