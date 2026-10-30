import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { DisruptionRecord } from '../../types';
import { formatTimeIST, formatDateTimeIST } from '../../utils/formatters';
import {
  AlertOctagon,
  Activity,
  CheckCircle2,
  Clock,
  MapPin,
  TrendingUp,
  HardHat,
  Search,
  Filter,
  ShieldCheck,
  Zap,
  ArrowRight,
  Sparkles,
  Info,
} from 'lucide-react';

export const SupervisorRecoveryPage: React.FC = () => {
  const { disruptions, jobs, electricians } = useApp();
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedDisruption, setSelectedDisruption] = useState<DisruptionRecord | null>(
    disruptions[0] || null
  );

  const filteredDisruptions = disruptions.filter((d: DisruptionRecord) => {
    if (statusFilter !== 'all' && d.status !== statusFilter) return false;
    return true;
  });

  const activeDisruptions = disruptions.filter(
    (d: DisruptionRecord) => d.status === 'detected' || d.status === 'analyzing'
  );
  const resolvedDisruptions = disruptions.filter((d: DisruptionRecord) => d.status === 'resolved');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Disruption & Recovery Engine Telemetry
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Monitoring Only
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Automated disruption detection, real-time rerouting, and dynamic schedule re-balancing across Mysuru
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-xs font-semibold text-amber-800 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 animate-pulse" />
            <span>{activeDisruptions.length} Active in Auto-Recovery</span>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>{resolvedDisruptions.length} Auto-Mitigated</span>
          </div>
        </div>
      </div>

      {/* Overview Stat Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Total Disruptions Handled</span>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">{disruptions.length}</p>
          <span className="text-[11px] text-slate-500">Telemetry-triggered</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Avg Auto-Recovery Time</span>
          <p className="text-2xl font-extrabold text-blue-600 mt-1">42s</p>
          <span className="text-[11px] text-emerald-600 font-medium">Sub-minute replanning</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Auto-Mitigation Rate</span>
          <p className="text-2xl font-extrabold text-emerald-600 mt-1">100%</p>
          <span className="text-[11px] text-slate-500">Zero manual supervisor actions</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Grid Reliability Impact</span>
          <p className="text-2xl font-extrabold text-indigo-600 mt-1">+14.2%</p>
          <span className="text-[11px] text-slate-500">SLA adherence preserved</span>
        </div>
      </div>

      {/* Disruption Events Table & Detail Split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Disruption Events Feed */}
        <div className="lg:col-span-1 space-y-3">
          <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center justify-between gap-2 text-xs">
            <span className="font-bold text-slate-500 uppercase text-[10px]">Filter by Status:</span>
            <div className="flex gap-1">
              {(['all', 'detected', 'analyzing', 'resolved'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-lg font-semibold capitalize transition ${
                    statusFilter === st
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm divide-y divide-slate-100 overflow-hidden">
            {filteredDisruptions.map((d: DisruptionRecord) => {
              const isSelected = selectedDisruption?.id === d.id;

              return (
                <div
                  key={d.id}
                  onClick={() => setSelectedDisruption(d)}
                  className={`p-4 transition cursor-pointer flex flex-col justify-between gap-2 ${
                    isSelected ? 'bg-amber-50/70 border-l-4 border-l-amber-500' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-slate-600">{d.id}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold capitalize ${
                          d.status === 'resolved'
                            ? 'bg-emerald-100 text-emerald-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {d.status.replace('_', ' ')}
                      </span>
                    </div>

                    <h4 className="font-bold text-slate-900 text-sm leading-snug">{d.title}</h4>
                    <p className="text-xs text-slate-600 line-clamp-2">{d.description}</p>
                  </div>

                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                    <span className="capitalize">{d.type.replace(/_/g, ' ')}</span>
                    <span className="font-mono text-[11px]">{formatTimeIST(d.timestamp)}</span>
                  </div>
                </div>
              );
            })}

            {filteredDisruptions.length === 0 && (
              <div className="p-8 text-center text-slate-400 text-xs">
                <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-1" />
                <p>No disruption events matching the filter criteria.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right 2 Columns: Deep Inspection & Before/After Schedule Comparison */}
        <div className="lg:col-span-2 space-y-4">
          {selectedDisruption ? (
            <div className="space-y-4">
              {/* Event Telemetry Header Card */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-600">{selectedDisruption.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-100 text-amber-900">
                      Telemetry Incident
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold capitalize ${
                        selectedDisruption.status === 'resolved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {selectedDisruption.status.replace('_', ' ')}
                    </span>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    Detected: {formatDateTimeIST(selectedDisruption.timestamp)}
                  </span>
                </div>

                <h3 className="text-base font-extrabold text-slate-900">{selectedDisruption.title}</h3>
                <p className="text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200 leading-relaxed">
                  {selectedDisruption.description}
                </p>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs pt-1">
                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Category</span>
                    <span className="font-semibold text-slate-800 capitalize">
                      {selectedDisruption.type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Affected Tickets</span>
                    <span className="font-bold text-blue-700">
                      {selectedDisruption.affectedJobIds.length} Job(s)
                    </span>
                  </div>
                  <div className="bg-slate-50 p-2.5 rounded-xl border border-slate-200 col-span-2 sm:col-span-1">
                    <span className="text-slate-400 block text-[10px] uppercase font-bold">Remedy Protocol</span>
                    <span className="font-semibold text-emerald-700">
                      Autonomous Reroute
                    </span>
                  </div>
                </div>
              </div>

              {/* ================= VISUAL BEFORE / AFTER SCHEDULE COMPARISON ================= */}
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="p-4 sm:px-6 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-blue-600" />
                    <div>
                      <h3 className="text-sm font-extrabold text-slate-900">
                        Visual Before & After Schedule Comparison
                      </h3>
                      <p className="text-[11px] text-slate-500">
                        {selectedDisruption.proposedResolution?.impactSummary ||
                          'Autonomous engine re-computed feasible schedules without violating SLA parameters.'}
                      </p>
                    </div>
                  </div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                    Autonomous Resolution
                  </span>
                </div>

                <div className="p-4 sm:p-6 space-y-4">
                  {selectedDisruption.proposedResolution?.reassignments &&
                  selectedDisruption.proposedResolution.reassignments.length > 0 ? (
                    selectedDisruption.proposedResolution.reassignments.map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-50/70 rounded-2xl border border-slate-200 p-4 space-y-3"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                              {item.jobId}
                            </span>
                            <span className="font-bold text-slate-900 text-xs truncate max-w-xs">
                              {item.jobTitle}
                            </span>
                          </div>
                          <span className="text-[10px] font-semibold text-slate-400">
                            Reassignment #{idx + 1}
                          </span>
                        </div>

                        {/* Diff Comparison Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {/* Original Schedule Card */}
                          <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-1.5 relative overflow-hidden">
                            <div className="absolute top-0 left-0 right-0 h-1 bg-slate-300" />
                            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider block">
                              Original Schedule (Before Disruption)
                            </span>
                            <div className="flex items-center gap-2">
                              <HardHat className="w-4 h-4 text-slate-500" />
                              <span className="font-bold text-slate-800 text-xs">
                                {item.previousElectricianName || 'Unassigned'}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-100">
                              <span>Window: {item.originalTime}</span>
                              <span className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px]">
                                Disrupted
                              </span>
                            </div>
                          </div>

                          {/* Recovered Schedule Card */}
                          <div className="bg-emerald-50/60 p-3.5 rounded-xl border-2 border-emerald-400 shadow-xs space-y-1.5 relative overflow-hidden">
                            <div className="absolute top-0 left-0 right-0 h-1 bg-emerald-500" />
                            <span className="text-[10px] uppercase font-bold text-emerald-800 tracking-wider block flex items-center justify-between">
                              <span>Recovered Schedule (Autonomous)</span>
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            </span>
                            <div className="flex items-center gap-2">
                              <HardHat className="w-4 h-4 text-emerald-600" />
                              <span className="font-bold text-emerald-950 text-xs">
                                {item.newElectricianName}
                              </span>
                            </div>
                            <div className="flex items-center justify-between text-xs text-emerald-800 pt-1 border-t border-emerald-200">
                              <span>Adjusted: {item.newTime}</span>
                              <span className="px-1.5 py-0.5 bg-emerald-200/80 text-emerald-900 rounded text-[10px] font-bold">
                                Optimized
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Algorithmic Reason Pill */}
                        <div className="bg-white p-2.5 rounded-xl border border-slate-200 text-xs text-slate-700 flex items-start gap-2">
                          <Zap className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                          <div>
                            <span className="font-bold text-slate-900">Optimization Reason: </span>
                            <span>{item.reason}</span>
                          </div>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center text-xs text-slate-400 space-y-1">
                      <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-1" />
                      <p className="font-bold text-slate-700">No schedule changes required</p>
                      <p>All active tickets remained on schedule without violating SLA parameters.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
              <AlertOctagon className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p>Select any disruption event from the list to view autonomous remedy telemetry and schedule comparisons.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
