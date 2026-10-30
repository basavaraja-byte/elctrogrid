import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { EscalationAlert, AlertSeverity } from '../../types';
import { SeverityBadge } from '../../components/common/StatusBadge';
import { EscalateModal } from './EscalateModal';
import {
  ShieldAlert,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Plus,
  Send,
  MessageSquare,
} from 'lucide-react';

export const AlertsEscalationsPage: React.FC = () => {
  const { user } = useAuth();
  const { escalations, jobs, refreshData } = useApp();

  const [isEscalateModalOpen, setIsEscalateModalOpen] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const filteredEscalations = escalations.filter((esc) => {
    if (filterSeverity !== 'all' && esc.severity !== filterSeverity) return false;
    return true;
  });

  const delayedJobs = jobs.filter((j) => j.isOverdue || j.slaRisk === 'breached');
  const emergencyJobs = jobs.filter((j) => j.priority === 'emergency');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            SLA & Alert Centre
          </h1>
          <p className="text-sm text-slate-500">
            Monitor real-time breach warnings, delayed crews, and manage escalated operational matters
          </p>
        </div>

        <button
          onClick={() => setIsEscalateModalOpen(true)}
          className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-md shadow-rose-600/20 flex items-center gap-2 self-start sm:self-auto transition"
        >
          <Plus className="w-4 h-4" />
          <span>Raise New Escalation</span>
        </button>
      </div>

      {/* Critical SLA Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-red-50 border border-red-200 p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-red-700">
              SLA Breaches
            </span>
            <AlertTriangle className="w-4 h-4 text-red-600" />
          </div>
          <span className="text-2xl font-extrabold text-red-900 mt-2 block">
            {delayedJobs.length} Tickets
          </span>
          <p className="text-[11px] text-red-700 mt-1">Exceeded maximum operational deadline</p>
        </div>

        <div className="bg-orange-50 border border-orange-200 p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-orange-700">
              Active Emergencies
            </span>
            <AlertTriangle className="w-4 h-4 text-orange-600" />
          </div>
          <span className="text-2xl font-extrabold text-orange-900 mt-2 block">
            {emergencyJobs.length} Tickets
          </span>
          <p className="text-[11px] text-orange-700 mt-1">45-minute response SLA window</p>
        </div>

        <div className="bg-purple-50 border border-purple-200 p-4 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-purple-700">
              Open Escalations
            </span>
            <ShieldAlert className="w-4 h-4 text-purple-600" />
          </div>
          <span className="text-2xl font-extrabold text-purple-900 mt-2 block">
            {escalations.filter((e) => e.status === 'open').length} Open
          </span>
          <p className="text-[11px] text-purple-700 mt-1">Routed to Dispatch & Management</p>
        </div>
      </div>

      {/* Escalations List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Active Escalations & Exceptions</h3>
            <p className="text-xs text-slate-500">Cross-departmental alerts requiring operational triage</p>
          </div>

          <div className="flex items-center gap-1.5">
            {['all', 'critical', 'high', 'medium'].map((sev) => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2.5 py-1 text-xs font-semibold rounded-lg capitalize transition ${
                  filterSeverity === sev
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                {sev}
              </button>
            ))}
          </div>
        </div>

        <div className="divide-y divide-slate-100">
          {filteredEscalations.map((esc) => (
            <div key={esc.id} className="p-4 sm:px-6 hover:bg-slate-50 transition space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-slate-500">{esc.id}</span>
                  {esc.jobId && (
                    <span className="font-mono text-xs font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                      Job: {esc.jobId}
                    </span>
                  )}
                  <SeverityBadge severity={esc.severity} />
                  <span className="text-xs font-bold uppercase text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                    Status: {esc.status}
                  </span>
                </div>
                <span className="text-xs text-slate-400">
                  {new Date(esc.createdAt).toLocaleString()}
                </span>
              </div>

              <h4 className="text-sm font-bold text-slate-900">{esc.title}</h4>
              <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-2.5 rounded-lg border border-slate-200/80">
                {esc.description}
              </p>

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                <span>
                  Raised by: <b className="text-slate-700">{esc.raisedBy}</b> ({esc.sourceRole})
                </span>
                <span>
                  Routed to: <b className="text-slate-800 capitalize">{esc.assignedToRole}</b>
                </span>
              </div>
            </div>
          ))}

          {filteredEscalations.length === 0 && (
            <div className="p-12 text-center text-xs text-slate-400">
              No escalations matching this filter.
            </div>
          )}
        </div>
      </div>

      <EscalateModal
        isOpen={isEscalateModalOpen}
        onClose={() => setIsEscalateModalOpen(false)}
      />
    </div>
  );
};

