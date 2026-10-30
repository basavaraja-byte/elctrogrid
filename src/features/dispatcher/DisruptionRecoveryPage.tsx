import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { DisruptionRecord, DisruptionType, Job } from '../../types';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import {
  AlertTriangle,
  Play,
  RotateCcw,
  CheckCircle2,
  ArrowRight,
  Clock,
  HardHat,
  ShieldAlert,
  ChevronRight,
  Sparkles,
} from 'lucide-react';

export const DisruptionRecoveryPage: React.FC = () => {
  const { user } = useAuth();
  const { electricians, jobs, refreshData, policies } = useApp();

  const [activeDisruption, setActiveDisruption] = useState<DisruptionRecord | null>(null);
  const [selectedType, setSelectedType] = useState<DisruptionType>('electrician_unavailable');
  const [selectedTechId, setSelectedTechId] = useState<string>(electricians[0]?.id || 'elec-1');
  const [customNotes, setCustomNotes] = useState('');
  const [isSimulating, setIsSimulating] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [resolutionNotice, setResolutionNotice] = useState('');

  const handleSimulate = async () => {
    if (!user) return;
    setIsSimulating(true);
    setResolutionNotice('');

    try {
      const record = await api.simulateDisruption(
        {
          type: selectedType,
          targetElectricianId: selectedTechId,
          notes: customNotes || undefined,
        },
        user
      );

      setActiveDisruption(record);
      refreshData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleExecuteResolution = async () => {
    if (!activeDisruption || !user) return;
    setIsApplying(true);

    try {
      await api.applyRecovery(activeDisruption, user);
      refreshData();
      setResolutionNotice(
        `Successfully executed recovery plan. ${activeDisruption.proposedResolution?.reassignments.length} assignments updated and dispatched.`
      );
      setActiveDisruption({ ...activeDisruption, status: 'resolved' });
    } catch (err) {
      console.error(err);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 p-6 sm:p-8 rounded-2xl text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30 mb-2">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Operational Resilience Engine</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Disruption Recovery Centre
            </h1>
            <p className="text-sm text-slate-300 mt-1 max-w-xl">
              Detect sudden field failures, preserve completed jobs, re-compute feasible schedules, and execute automated recovery plans.
            </p>
          </div>
        </div>
      </div>

      {resolutionNotice && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-semibold flex items-center gap-2 shadow-xs">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          <span>{resolutionNotice}</span>
        </div>
      )}

      {/* Disruption Simulator Control Panel */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-slate-900">
              Simulate Operational Field Disruption
            </h2>
            <p className="text-xs text-slate-500">
              Test dynamic re-scheduling algorithms against real constraint scenarios
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Disruption Type Scenario *
            </label>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as DisruptionType)}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="electrician_unavailable">
                🚗 Electrician Unavailable (Vehicle Breakdown / Illness)
              </option>
              <option value="technician_delay">
                ⏱️ Severe Transit Delay (+90 Mins Gridlock)
              </option>
              <option value="emergency_job_injection">
                🚨 Emergency Job Injected (Hospital / Substation Hazard)
              </option>
              <option value="equipment_failure">
                ⚠️ Specialized Equipment Failure (PPE / Fault Locator)
              </option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Target Field Electrician
            </label>
            <select
              value={selectedTechId}
              onChange={(e) => setSelectedTechId(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              {electricians.map((tech) => (
                <option key={tech.id} value={tech.id}>
                  {tech.name} ({tech.status} • {tech.currentWorkload}h workload)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Simulation Incident Notes
            </label>
            <input
              type="text"
              value={customNotes}
              onChange={(e) => setCustomNotes(e.target.value)}
              placeholder="e.g. Blown tire on I-35 southbound corridor"
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSimulate}
            disabled={isSimulating}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 transition disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-white text-white" />
            {isSimulating ? 'Analyzing Impact...' : 'Trigger Disruption Simulation'}
          </button>
        </div>
      </div>

      {/* Disruption Analysis & Proposed Recovery Plan */}
      {activeDisruption && (
        <div className="space-y-4">
          <div className="bg-amber-50/70 border border-amber-300 rounded-xl p-5 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-bold text-amber-800">
                    {activeDisruption.id}
                  </span>
                  <span className="text-xs bg-amber-200 text-amber-900 font-bold px-2 py-0.5 rounded capitalize">
                    {activeDisruption.status}
                  </span>
                </div>
                <h3 className="text-base font-extrabold text-slate-900">
                  {activeDisruption.title}
                </h3>
                <p className="text-xs text-slate-700 mt-1">{activeDisruption.description}</p>
              </div>

              <div className="text-right sm:border-l sm:pl-4 border-amber-200 text-xs text-slate-700">
                <span className="font-bold text-slate-900 block">
                  {activeDisruption.affectedJobIds.length} Job(s) Impacted
                </span>
                <span className="text-[11px] text-slate-500">
                  Detected at {new Date(activeDisruption.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>

          {/* Before-and-After Schedule Comparison */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  Visual Before & After Schedule Comparison
                </h3>
                <p className="text-xs text-slate-500">
                  {activeDisruption.proposedResolution?.impactSummary}
                </p>
              </div>

              {activeDisruption.status !== 'resolved' && (
                <button
                  onClick={handleExecuteResolution}
                  disabled={isApplying}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-lg shadow-sm flex items-center gap-1.5 transition disabled:opacity-50"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  {isApplying ? 'Applying Schedule...' : 'Approve & Execute Revised Schedule'}
                </button>
              )}
            </div>

            <div className="divide-y divide-slate-100 overflow-x-auto">
              {activeDisruption.proposedResolution?.reassignments.map((item, idx) => (
                <div key={idx} className="p-4 sm:px-6 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/60 transition">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-blue-600">{item.jobId}</span>
                      <h4 className="text-xs font-bold text-slate-900 truncate">{item.jobTitle}</h4>
                      {item.requiresApproval && (
                        <span className="text-[10px] font-bold uppercase bg-rose-100 text-rose-800 px-1.5 py-0.5 rounded">
                          Requires Approval
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Reason: <span className="text-slate-700 font-medium">{item.reason}</span>
                    </p>
                  </div>

                  {/* Visual Diff: Before -> After */}
                  <div className="flex items-center gap-3 bg-slate-50 p-2.5 rounded-xl border border-slate-200 text-xs">
                    <div className="text-center min-w-[120px]">
                      <span className="text-[10px] uppercase font-bold text-slate-400 block">
                        Original Assignment
                      </span>
                      <span className="font-bold text-slate-700 block truncate">
                        {item.previousElectricianName}
                      </span>
                      <span className="text-[10px] text-slate-500">{item.originalTime}</span>
                    </div>

                    <ArrowRight className="w-4 h-4 text-blue-600 flex-shrink-0" />

                    <div className="text-center min-w-[120px] bg-emerald-50 p-1.5 rounded-lg border border-emerald-200">
                      <span className="text-[10px] uppercase font-bold text-emerald-800 block">
                        Proposed Replacement
                      </span>
                      <span className="font-bold text-emerald-950 block truncate">
                        {item.newElectricianName}
                      </span>
                      <span className="text-[10px] text-emerald-700 font-semibold">{item.newTime}</span>
                    </div>
                  </div>
                </div>
              ))}

              {(!activeDisruption.proposedResolution?.reassignments ||
                activeDisruption.proposedResolution.reassignments.length === 0) && (
                <div className="p-8 text-center text-xs text-slate-400">
                  No pending future jobs were affected by this technician's schedule.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

