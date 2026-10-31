import React, { useState, useEffect } from 'react';
import { useApp } from '../../../context/AppContext';
import { useAuth } from '../../../context/AuthContext';
import { api } from '../../../services/api/apiClient';
import { Job, Electrician, AssignmentOfferItem } from '../../../types';
import { formatDateTimeIST } from '../../../utils/formatters';
import { StatusBadge, PriorityBadge } from '../../../components/common/StatusBadge';
import {
  Radio,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  UserCheck,
  ChevronDown,
  ChevronUp,
  MapPin,
  Phone,
  Timer,
  Zap,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';

export const SupervisorAssignmentMonitor: React.FC = () => {
  const { user } = useAuth();
  const { jobs, electricians, refreshData } = useApp();

  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number>(Date.now());
  const [manualAssignJob, setManualAssignJob] = useState<Job | null>(null);
  const [selectedTechId, setSelectedTechId] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Tick every second to drive live 60s countdowns and auto-check expired offers
  useEffect(() => {
    const timer = setInterval(() => {
      setNowMs(Date.now());
      // Triggers checkExpiredOffers in mock store
      refreshData();
    }, 1000);
    return () => clearInterval(timer);
  }, [refreshData]);

  // In-flight offers: Jobs with currentOffer that are still offered
  const inFlightJobs = jobs.filter((j) => j.currentOffer && j.currentOffer.status === 'offered');

  // Awaiting manual intervention: status is awaiting_assignment or unassigned
  const unassignedJobs = jobs.filter(
    (j) =>
      j.status === 'awaiting_assignment' ||
      (j.status === 'awaiting_approval' && !j.currentOffer && !j.assignedElectricianId)
  );

  // Jobs that have an assignment history
  const jobsWithHistory = jobs.filter(
    (j) => (j.assignmentHistory && j.assignmentHistory.length > 0) || j.currentOffer
  );

  // Available electricians for manual override modal
  const eligibleManualTechs = electricians.filter(
    (e) => (e.accountStatus === 'active' || !e.accountStatus) && e.status !== 'leave' && e.status !== 'off_duty'
  );

  const handleRetryAssignment = async (jobId: string) => {
    setActionLoading(jobId);
    try {
      await api.startAutomaticAssignment(jobId);
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Error retrying automatic assignment');
    } finally {
      setActionLoading(null);
    }
  };

  const handleManualAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualAssignJob || !selectedTechId || !user) return;
    setActionLoading('manual');
    try {
      await api.assignAndDispatchJob(
        manualAssignJob.id,
        selectedTechId,
        '10:00 AM IST',
        '12:00 PM IST',
        'manual',
        user
      );
      refreshData();
      setManualAssignJob(null);
      setSelectedTechId('');
    } catch (err: any) {
      alert(err.message || 'Error manually assigning job');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                <Radio className="w-3 h-3 text-blue-600 animate-pulse" />
                Live Dispatch Telemetry
              </span>
              <span className="text-xs text-slate-500 font-medium">
                1-by-1 Sequential Candidate Offer (60s SLA)
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-extrabold text-slate-900 tracking-tight">
              Intelligent Electrician Assignment Monitor
            </h2>
            <p className="text-xs text-slate-500 max-w-2xl leading-relaxed">
              Supervise automated sequential dispatch offers. Each nearest eligible technician receives 60 seconds to accept. Inactive, busy, or un-certified electricians are filtered automatically.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-center">
            <button
              onClick={() => refreshData()}
              className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold flex items-center gap-1.5 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>

        {/* Live KPI Metric Pills */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5 pt-4 border-t border-slate-100 text-xs">
          <div className="bg-amber-50/70 border border-amber-200/80 p-3 rounded-xl">
            <span className="text-[11px] font-semibold text-amber-700 block">Active 60s Offers</span>
            <span className="text-xl font-extrabold text-amber-900 mt-0.5 block flex items-center gap-1.5">
              <Timer className="w-4 h-4 text-amber-600" />
              {inFlightJobs.length}
            </span>
          </div>

          <div className="bg-red-50/70 border border-red-200/80 p-3 rounded-xl">
            <span className="text-[11px] font-semibold text-red-700 block">Awaiting Assignment</span>
            <span className="text-xl font-extrabold text-red-900 mt-0.5 block flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-red-600" />
              {unassignedJobs.length}
            </span>
          </div>

          <div className="bg-blue-50/70 border border-blue-200/80 p-3 rounded-xl">
            <span className="text-[11px] font-semibold text-blue-700 block">Total Attempt Logs</span>
            <span className="text-xl font-extrabold text-blue-900 mt-0.5 block flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-blue-600" />
              {jobs.reduce((sum, j) => sum + (j.assignmentHistory?.length || 0), 0)}
            </span>
          </div>

          <div className="bg-emerald-50/70 border border-emerald-200/80 p-3 rounded-xl">
            <span className="text-[11px] font-semibold text-emerald-700 block">Assigned / Dispatched</span>
            <span className="text-xl font-extrabold text-emerald-900 mt-0.5 block flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              {jobs.filter((j) => j.assignedElectricianId && j.status !== 'completed' && j.status !== 'closed').length}
            </span>
          </div>
        </div>
      </div>

      {/* SECTION 1: Active In-Flight Offers (Live 60s Countdowns) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-amber-50/40">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-ping" />
            <h3 className="text-sm font-extrabold text-slate-900">
              Active In-Flight Offers ({inFlightJobs.length})
            </h3>
          </div>
          <span className="text-[11px] font-bold bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full">
            60-Second Real-Time SLA
          </span>
        </div>

        {inFlightJobs.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <Clock className="w-8 h-8 mx-auto text-slate-300 mb-2 stroke-[1.5]" />
            <p className="text-xs font-semibold">No active assignment offers pending acceptance.</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              When a new electrical service request is submitted, the nearest candidate will appear here with an active 60-second countdown.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {inFlightJobs.map((job) => {
              const offer = job.currentOffer!;
              const expiresMs = new Date(offer.expiresAt).getTime();
              const remainingSec = Math.max(0, Math.ceil((expiresMs - nowMs) / 1000));
              const progressPct = Math.min(100, Math.max(0, (remainingSec / 60) * 100));

              return (
                <div key={job.id} className="p-5 sm:px-6 bg-amber-50/10 hover:bg-amber-50/30 transition">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-700">{job.id}</span>
                        <PriorityBadge priority={job.priority} />
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          <Timer className="w-3 h-3 animate-spin" />
                          OFFER DISPATCHED • ATTEMPT #{offer.attemptNumber}
                        </span>
                      </div>

                      <h4 className="text-sm font-bold text-slate-900">{job.title}</h4>
                      <p className="text-xs text-slate-600 line-clamp-1">{job.description}</p>

                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-400" />
                          {job.location.address}
                        </span>
                        <span>•</span>
                        <span>Customer: <b>{job.customerName}</b> ({job.customerPhone})</span>
                      </div>
                    </div>

                    {/* Offered Tech & Countdown Column */}
                    <div className="flex items-center gap-4 bg-white p-3.5 rounded-xl border border-amber-200/80 shadow-xs lg:min-w-[340px]">
                      <div className="relative w-12 h-12 flex-shrink-0 flex items-center justify-center">
                        <svg className="w-12 h-12 transform -rotate-90">
                          <circle
                            cx="24"
                            cy="24"
                            r="20"
                            stroke="#fed7aa"
                            strokeWidth="3.5"
                            fill="transparent"
                          />
                          <circle
                            cx="24"
                            cy="24"
                            r="20"
                            stroke={remainingSec <= 15 ? '#ef4444' : '#f59e0b'}
                            strokeWidth="3.5"
                            strokeDasharray={125.6}
                            strokeDashoffset={125.6 * (1 - progressPct / 100)}
                            strokeLinecap="round"
                            fill="transparent"
                            className="transition-all duration-1000 ease-linear"
                          />
                        </svg>
                        <span
                          className={`absolute font-mono text-xs font-extrabold ${
                            remainingSec <= 15 ? 'text-red-600 animate-pulse' : 'text-amber-800'
                          }`}
                        >
                          {remainingSec}s
                        </span>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] uppercase font-bold text-amber-700 tracking-wider">
                            Contacting Candidate
                          </span>
                          <span className="text-[11px] font-bold text-slate-700">
                            ~{offer.estimatedDistanceKm?.toFixed(1) || '1.8'} km
                          </span>
                        </div>
                        <h5 className="text-xs font-bold text-slate-900 truncate">{offer.technicianName}</h5>
                        <p className="text-[11px] text-slate-500">
                          Expires in {remainingSec}s. Next tech auto-engaged if unaccepted.
                        </p>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <button
                          type="button"
                          onClick={() => setManualAssignJob(job)}
                          className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] font-bold transition whitespace-nowrap"
                        >
                          Manual Override
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 2: Unassigned / Awaiting Intervention Queue */}
      {unassignedJobs.length > 0 && (
        <div className="bg-red-50/50 rounded-2xl border border-red-200 shadow-sm overflow-hidden">
          <div className="p-4 sm:px-6 border-b border-red-100 flex items-center justify-between bg-red-100/40">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <h3 className="text-sm font-extrabold text-red-950">
                Awaiting Assignment Queue ({unassignedJobs.length})
              </h3>
            </div>
            <span className="text-[11px] font-bold bg-red-200 text-red-900 px-2.5 py-0.5 rounded-full">
              Requires Attention
            </span>
          </div>

          <div className="divide-y divide-red-100">
            {unassignedJobs.map((job) => (
              <div key={job.id} className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white/70">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-red-700">{job.id}</span>
                    <PriorityBadge priority={job.priority} />
                    <StatusBadge status={job.status} />
                    <span className="text-[11px] text-slate-500">
                      {job.assignmentHistory?.length || 0} failed candidate attempts
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">{job.title}</h4>
                  <div className="text-xs text-slate-600 flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      {job.location.address}
                    </span>
                    <span>•</span>
                    <span>Customer: {job.customerName} ({job.customerPhone})</span>
                  </div>
                </div>

                <div className="flex items-center gap-2 self-start sm:self-center">
                  <button
                    type="button"
                    disabled={actionLoading === job.id}
                    onClick={() => handleRetryAssignment(job.id)}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-xs transition"
                  >
                    <RotateCcw className={`w-3.5 h-3.5 ${actionLoading === job.id ? 'animate-spin' : ''}`} />
                    <span>Retry Auto-Assignment</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setManualAssignJob(job)}
                    className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition"
                  >
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Assign Manually</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SECTION 3: Complete Assignment History & Step Logs */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div>
            <h3 className="text-sm font-extrabold text-slate-900">
              Complaint Assignment Attempt Logs & Sequential Failover History
            </h3>
            <p className="text-xs text-slate-500">
              Audit trails of 60s offer dispatches, electrician rejections, expirations, and successful acceptances
            </p>
          </div>
          <span className="text-[11px] font-bold bg-slate-200/80 text-slate-700 px-2.5 py-0.5 rounded-full">
            {jobsWithHistory.length} Complaints Monitored
          </span>
        </div>

        {jobsWithHistory.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <p className="text-xs">No assignment attempt history recorded yet.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {jobsWithHistory.map((job) => {
              const isExpanded = expandedJobId === job.id;
              const attempts = job.assignmentHistory || [];
              const finalTech = job.assignedElectricianName;

              return (
                <div key={job.id} className="p-4 sm:px-6 hover:bg-slate-50/50 transition">
                  <div
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer"
                    onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                  >
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-700">{job.id}</span>
                        <PriorityBadge priority={job.priority} />
                        <StatusBadge status={job.status} />
                        <span className="text-[11px] font-semibold text-slate-500">
                          {attempts.length} attempt{attempts.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">{job.title}</h4>
                      <p className="text-xs text-slate-500">
                        Customer: <span className="font-semibold text-slate-700">{job.customerName}</span> • Location: {job.location.address}
                      </p>
                    </div>

                    <div className="flex items-center gap-3">
                      {finalTech ? (
                        <div className="text-right">
                          <span className="text-[11px] text-slate-400 block">Final Assignee</span>
                          <span className="text-xs font-bold text-emerald-700 flex items-center gap-1 justify-end">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            {finalTech}
                          </span>
                        </div>
                      ) : (
                        <div className="text-right">
                          <span className="text-[11px] text-slate-400 block">Current Status</span>
                          <span className="text-xs font-bold text-amber-600">Pending Acceptance</span>
                        </div>
                      )}

                      <button
                        type="button"
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Attempt Flow Timeline */}
                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-slate-100 pl-4 space-y-3 bg-slate-50/50 p-4 rounded-xl border border-slate-200">
                      <h5 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-blue-600" />
                        Sequential Offer Timeline ({job.id})
                      </h5>

                      {attempts.length === 0 ? (
                        <p className="text-xs text-slate-400">No attempts logged.</p>
                      ) : (
                        <div className="relative pl-5 space-y-3 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                          {attempts.map((att, idx) => {
                            let badgeBg = 'bg-slate-100 text-slate-700';
                            let icon = <Clock className="w-3 h-3 text-slate-500" />;

                            if (att.status === 'accepted') {
                              badgeBg = 'bg-emerald-100 text-emerald-800';
                              icon = <CheckCircle2 className="w-3 h-3 text-emerald-600" />;
                            } else if (att.status === 'rejected') {
                              badgeBg = 'bg-red-100 text-red-800';
                              icon = <XCircle className="w-3 h-3 text-red-600" />;
                            } else if (att.status === 'timed_out') {
                              badgeBg = 'bg-amber-100 text-amber-800';
                              icon = <Timer className="w-3 h-3 text-amber-600" />;
                            } else if (att.status === 'offered') {
                              badgeBg = 'bg-blue-100 text-blue-800 animate-pulse';
                              icon = <Radio className="w-3 h-3 text-blue-600" />;
                            }

                            return (
                              <div key={att.offerId || idx} className="relative text-xs">
                                <span className="absolute -left-5 top-1 w-2.5 h-2.5 rounded-full bg-slate-400 ring-4 ring-white" />
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="font-bold text-slate-900">
                                    Attempt {att.attemptNumber}: {att.technicianName}
                                  </span>
                                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-bold uppercase text-[10px] ${badgeBg}`}>
                                    {icon}
                                    {att.status.replace('_', ' ')}
                                  </span>
                                  {att.estimatedDistanceKm && (
                                    <span className="text-[11px] text-slate-500">
                                      (~{att.estimatedDistanceKm.toFixed(1)} km away)
                                    </span>
                                  )}
                                  <span className="text-[11px] text-slate-400">
                                    Offered: {formatDateTimeIST(att.offeredAt)}
                                  </span>
                                </div>

                                {att.responseReason && (
                                  <p className="text-[11px] text-slate-600 mt-1 italic pl-1">
                                    Reason: &quot;{att.responseReason}&quot; (at {formatDateTimeIST(att.respondedAt || att.expiresAt)})
                                  </p>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {finalTech && (
                        <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between text-xs font-bold text-emerald-800">
                          <span>Final Outcome: Job successfully assigned to {finalTech}</span>
                          <span className="bg-emerald-100 px-2 py-0.5 rounded text-[11px]">ACTIVE WORKFLOW</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Manual Override Modal */}
      {manualAssignJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-100">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-blue-600" />
                <h4 className="text-base font-extrabold text-slate-900">Manual Assignment Override</h4>
              </div>
              <button
                type="button"
                onClick={() => setManualAssignJob(null)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-600 mb-4">
              Manually assign complaint <b className="font-mono text-blue-700">{manualAssignJob.id}</b> ({manualAssignJob.title}) to an electrician. This bypasses the 60-second automated sequence.
            </p>

            <form onSubmit={handleManualAssign} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Select Electrician ({eligibleManualTechs.length} Available On-Duty)
                </label>
                <select
                  required
                  value={selectedTechId}
                  onChange={(e) => setSelectedTechId(e.target.value)}
                  className="w-full text-xs font-semibold px-3 py-2.5 rounded-xl border border-slate-300 bg-white focus:outline-hidden focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">-- Choose Electrician --</option>
                  {eligibleManualTechs.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.status}) • Rating {t.rating} ★ • {t.skills.slice(0, 2).join(', ')}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setManualAssignJob(null)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedTechId || actionLoading === 'manual'}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold disabled:opacity-50"
                >
                  {actionLoading === 'manual' ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
