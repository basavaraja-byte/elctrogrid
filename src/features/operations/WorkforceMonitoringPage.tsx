import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Electrician } from '../../types';
import { DataTable, Column } from '../../components/common/DataTable';
import {
  Users,
  HardHat,
  Star,
  Clock,
  Radio,
  Briefcase,
  AlertCircle,
} from 'lucide-react';

export const WorkforceMonitoringPage: React.FC = () => {
  const { electricians, jobs } = useApp();

  const columns: Column<Electrician>[] = [
    {
      header: 'Technician',
      cell: (e) => (
        <div className="flex items-center gap-2.5">
          <img
            src={e.avatar}
            alt={e.name}
            className="w-9 h-9 rounded-full object-cover border border-slate-200"
          />
          <div>
            <span className="font-bold text-slate-900 block">{e.name}</span>
            <span className="text-[11px] text-slate-500 font-mono">{e.employeeId}</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Duty Status',
      cell: (e) => {
        const colors = {
          available: 'bg-emerald-100 text-emerald-800',
          busy: 'bg-amber-100 text-amber-800',
          en_route: 'bg-sky-100 text-sky-800',
          off_duty: 'bg-slate-100 text-slate-700',
          leave: 'bg-rose-100 text-rose-800',
          on_break: 'bg-purple-100 text-purple-800',
        }[e.status] || 'bg-slate-100 text-slate-700';

        return (
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${colors}`}>
            {e.status.replace('_', ' ')}
          </span>
        );
      },
    },
    {
      header: 'Shift & Hours',
      cell: (e) => (
        <div className="text-xs text-slate-600">
          <span className="font-semibold capitalize block">{e.shift} Shift</span>
          <span className="text-[11px] text-slate-500">{e.shiftHours.start} - {e.shiftHours.end}</span>
        </div>
      ),
    },
    {
      header: 'Current Load',
      cell: (e) => {
        const ratio = Math.min(100, Math.round((e.currentWorkload / e.maxDailyHours) * 100));
        const barColor = ratio > 85 ? 'bg-rose-500' : ratio > 60 ? 'bg-amber-500' : 'bg-emerald-500';

        return (
          <div className="w-28">
            <div className="flex justify-between text-[11px] font-semibold text-slate-700 mb-1">
              <span>{e.currentWorkload}h</span>
              <span className="text-slate-400">max {e.maxDailyHours}h</span>
            </div>
            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
              <div className={`h-full ${barColor}`} style={{ width: `${ratio}%` }} />
            </div>
          </div>
        );
      },
    },
    {
      header: 'Active Ticket',
      cell: (e) => {
        const activeJob = jobs.find(
          (j) =>
            j.assignedElectricianId === e.id &&
            (j.status === 'en_route' || j.status === 'in_progress')
        );

        return activeJob ? (
          <div className="text-xs max-w-xs">
            <span className="font-mono font-bold text-blue-700 block">{activeJob.id}</span>
            <span className="truncate block text-slate-600 text-[11px]">{activeJob.title}</span>
          </div>
        ) : (
          <span className="text-xs text-slate-400 italic">Standby</span>
        );
      },
    },
    {
      header: 'Last GPS Ping',
      cell: (e) => (
        <div className="text-xs text-slate-500 flex items-center gap-1.5">
          <Radio className="w-3.5 h-3.5 text-emerald-500 animate-pulse" />
          <span>{new Date(e.currentLocation.lastUpdated).toLocaleTimeString()}</span>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Field Workforce Monitoring
        </h1>
        <p className="text-sm text-slate-500">
          Supervise duty status, workload saturation, active tickets, and telemetry across the electrical crew
        </p>
      </div>

      <DataTable
        columns={columns}
        data={electricians}
        searchPlaceholder="Search technician name, ID, or active ticket..."
        searchFilter={(item, query) =>
          item.name.toLowerCase().includes(query) ||
          item.employeeId.toLowerCase().includes(query) ||
          item.status.toLowerCase().includes(query)
        }
        filterOptions={[
          {
            label: 'Duty Status',
            key: 'status',
            options: [
              { label: 'Available', value: 'available' },
              { label: 'Busy', value: 'busy' },
              { label: 'En Route', value: 'en_route' },
              { label: 'Off Duty', value: 'off_duty' },
            ],
            filterFn: (item, val) => item.status === val,
          },
        ]}
      />
    </div>
  );
};

