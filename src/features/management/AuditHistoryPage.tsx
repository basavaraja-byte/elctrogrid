import React from 'react';
import { useApp } from '../../context/AppContext';
import { AuditLogEntry } from '../../types';
import { DataTable, Column } from '../../components/common/DataTable';
import { ScrollText, ShieldCheck, Clock, User } from 'lucide-react';

export const AuditHistoryPage: React.FC = () => {
  const { auditLogs } = useApp();

  const columns: Column<AuditLogEntry>[] = [
    {
      header: 'Audit ID',
      accessorKey: 'id',
      className: 'font-mono text-xs font-bold text-slate-500',
    },
    {
      header: 'Timestamp',
      cell: (entry) => (
        <span className="text-xs text-slate-500">
          {new Date(entry.timestamp).toLocaleString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          })}
        </span>
      ),
    },
    {
      header: 'Actor / User',
      cell: (entry) => (
        <div>
          <span className="font-bold text-slate-900 block">{entry.userName}</span>
          <span className="text-[10px] uppercase font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded">
            {entry.userRole}
          </span>
        </div>
      ),
    },
    {
      header: 'Action',
      cell: (entry) => (
        <span className="font-mono text-xs font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
          {entry.action}
        </span>
      ),
    },
    {
      header: 'Entity / Target',
      cell: (entry) => (
        <div className="text-xs">
          <span className="font-mono font-bold text-slate-800 block">{entry.entityId}</span>
          <span className="text-[10px] text-slate-400 capitalize">{entry.entityType.replace('_', ' ')}</span>
        </div>
      ),
    },
    {
      header: 'Change Diff',
      cell: (entry) => (
        <div className="text-xs text-slate-600 max-w-xs">
          {entry.previousValue && (
            <span className="text-rose-600 line-through mr-1 block truncate">
              {entry.previousValue}
            </span>
          )}
          <span className="text-emerald-700 font-semibold block truncate">
            {entry.newValue}
          </span>
        </div>
      ),
    },
    {
      header: 'Reason / Justification',
      cell: (entry) => (
        <span className="text-xs text-slate-600 max-w-xs block truncate" title={entry.reason}>
          {entry.reason || 'Standard operational procedure'}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          System Audit Trail & Compliance Log
        </h1>
        <p className="text-sm text-slate-500">
          Immutable operational record of dispatch events, executive approvals, and status transitions
        </p>
      </div>

      <DataTable
        columns={columns}
        data={auditLogs}
        searchPlaceholder="Search audit action, actor name, entity ID, or reason..."
        searchFilter={(item, query) =>
          Boolean(
            item.id.toLowerCase().includes(query) ||
            item.action.toLowerCase().includes(query) ||
            item.userName.toLowerCase().includes(query) ||
            item.entityId.toLowerCase().includes(query) ||
            (item.reason && item.reason.toLowerCase().includes(query))
          )
        }
        filterOptions={[
          {
            label: 'Actor Role',
            key: 'role',
            options: [
              { label: 'Management', value: 'management' },
              { label: 'Operations', value: 'operations' },
              { label: 'Dispatcher', value: 'dispatcher' },
              { label: 'Electrician', value: 'electrician' },
              { label: 'Customer', value: 'customer' },
            ],
            filterFn: (item, val) => item.userRole === val,
          },
          {
            label: 'Entity Type',
            key: 'entityType',
            options: [
              { label: 'Job', value: 'job' },
              { label: 'Service Request', value: 'service_request' },
              { label: 'Approval', value: 'approval' },
              { label: 'Policy', value: 'policy' },
              { label: 'Disruption', value: 'disruption' },
            ],
            filterFn: (item, val) => item.entityType === val,
          },
        ]}
      />
    </div>
  );
};
