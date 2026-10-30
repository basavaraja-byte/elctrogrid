import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { PolicySettings } from '../../types';
import {
  Sliders,
  CheckCircle2,
  Save,
  ShieldCheck,
  Zap,
  Clock,
  Scale,
  Sparkles,
} from 'lucide-react';

export const PolicyConfigurationPage: React.FC = () => {
  const { user } = useAuth();
  const { policies, refreshData } = useApp();

  const [formPolicies, setFormPolicies] = useState<PolicySettings>({ ...policies });
  const [isSaving, setIsSaving] = useState(false);
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setIsSaving(true);
    setSavedNotice(false);

    try {
      await api.updatePolicies(formPolicies, user);
      refreshData();
      setSavedNotice(true);
      setTimeout(() => setSavedNotice(false), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const totalWeights =
    formPolicies.weights.skillCompatibility +
    formPolicies.weights.availabilityShift +
    formPolicies.weights.proximityTravel +
    formPolicies.weights.workloadBalance +
    formPolicies.weights.deadlineFeasibility +
    formPolicies.weights.equipmentMatch;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Operational Policy & Scheduling Rules
          </h1>
          <p className="text-sm text-slate-500">
            Configure system-wide dispatch thresholds, overtime boundaries, SLA targets, and optimizer scoring weights
          </p>
        </div>

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 self-start sm:self-auto transition disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          {isSaving ? 'Updating Policies...' : 'Save Configuration'}
        </button>
      </div>

      {savedNotice && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2 shadow-xs animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>Policies successfully updated and logged in the organizational audit trail.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Automatic Dispatch Rules */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
            <Zap className="w-5 h-5 text-blue-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">Hybrid Automated Dispatch Rules</h3>
              <p className="text-xs text-slate-500">Criteria for zero-human automated technician routing</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <label className="p-4 rounded-xl border border-slate-200 flex items-start gap-3 cursor-pointer hover:bg-slate-50">
              <input
                type="checkbox"
                checked={formPolicies.autoDispatchEnabled}
                onChange={(e) =>
                  setFormPolicies({ ...formPolicies, autoDispatchEnabled: e.target.checked })
                }
                className="mt-0.5 accent-blue-600 w-4 h-4"
              />
              <div>
                <span className="font-bold text-slate-900 block">Enable Auto-Dispatch Engine</span>
                <span className="text-[11px] text-slate-500">
                  Automatically assign qualified jobs when candidate score exceeds threshold.
                </span>
              </div>
            </label>

            <label className="p-4 rounded-xl border border-slate-200 flex items-start gap-3 cursor-pointer hover:bg-slate-50">
              <input
                type="checkbox"
                checked={formPolicies.emergencyAutoEscalate}
                onChange={(e) =>
                  setFormPolicies({ ...formPolicies, emergencyAutoEscalate: e.target.checked })
                }
                className="mt-0.5 accent-blue-600 w-4 h-4"
              />
              <div>
                <span className="font-bold text-slate-900 block">Auto-Escalate Critical Emergencies</span>
                <span className="text-[11px] text-slate-500">
                  Notify executive operations immediately upon arrival of any unassigned emergency ticket.
                </span>
              </div>
            </label>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs pt-2">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Minimum Candidate Match Score for Auto-Dispatch ({formPolicies.autoDispatchMinScoreThreshold}%)
              </label>
              <input
                type="range"
                min={50}
                max={95}
                value={formPolicies.autoDispatchMinScoreThreshold}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    autoDispatchMinScoreThreshold: Number(e.target.value),
                  })
                }
                className="w-full accent-blue-600"
              />
              <span className="text-[11px] text-slate-500">
                Jobs scoring below {formPolicies.autoDispatchMinScoreThreshold}% will require dispatcher manual review.
              </span>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Management Authorization Reassignment Threshold
              </label>
              <input
                type="number"
                min={1}
                max={10}
                value={formPolicies.requireManagementApprovalForReassignmentsCount}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    requireManagementApprovalForReassignmentsCount: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-xs"
              />
              <span className="text-[11px] text-slate-500">
                Disruption recovery events reassigning ≥ {formPolicies.requireManagementApprovalForReassignmentsCount} jobs require executive sign-off.
              </span>
            </div>
          </div>
        </div>

        {/* SLA & Shift Hours Policies */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2.5 pb-3 border-b border-slate-100">
            <Clock className="w-5 h-5 text-indigo-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-900">SLA Response Windows & Shift Caps</h3>
              <p className="text-xs text-slate-500">Target response deadlines and overtime prevention</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Emergency Priority SLA (Minutes)
              </label>
              <input
                type="number"
                min={15}
                max={120}
                value={formPolicies.slaEmergencyMinutes}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    slaEmergencyMinutes: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                High Priority SLA (Minutes)
              </label>
              <input
                type="number"
                min={30}
                max={360}
                value={formPolicies.slaHighPriorityMinutes}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    slaHighPriorityMinutes: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">
                Max Daily Shift Workload (Hours)
              </label>
              <input
                type="number"
                step="0.5"
                min={6}
                max={12}
                value={formPolicies.maxDailyWorkloadHours}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    maxDailyWorkloadHours: Number(e.target.value),
                  })
                }
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              />
            </div>
          </div>
        </div>

        {/* Scoring Weights */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <Scale className="w-5 h-5 text-emerald-600" />
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Intelligent Optimizer Scoring Model Weights
                </h3>
                <p className="text-xs text-slate-500">
                  Governs mathematical prioritization when generating schedules (Total: {totalWeights}%)
                </p>
              </div>
            </div>
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded ${
                totalWeights === 100
                  ? 'bg-emerald-100 text-emerald-800'
                  : 'bg-amber-100 text-amber-800'
              }`}
            >
              Sum: {totalWeights}%
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex justify-between font-bold text-slate-800 mb-1">
                <span>Skill Match</span>
                <span>{formPolicies.weights.skillCompatibility}%</span>
              </div>
              <input
                type="range"
                min={5}
                max={50}
                value={formPolicies.weights.skillCompatibility}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    weights: {
                      ...formPolicies.weights,
                      skillCompatibility: Number(e.target.value),
                    },
                  })
                }
                className="w-full accent-blue-600"
              />
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex justify-between font-bold text-slate-800 mb-1">
                <span>Availability & Shift</span>
                <span>{formPolicies.weights.availabilityShift}%</span>
              </div>
              <input
                type="range"
                min={5}
                max={50}
                value={formPolicies.weights.availabilityShift}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    weights: {
                      ...formPolicies.weights,
                      availabilityShift: Number(e.target.value),
                    },
                  })
                }
                className="w-full accent-blue-600"
              />
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex justify-between font-bold text-slate-800 mb-1">
                <span>Proximity & Travel Distance</span>
                <span>{formPolicies.weights.proximityTravel}%</span>
              </div>
              <input
                type="range"
                min={5}
                max={50}
                value={formPolicies.weights.proximityTravel}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    weights: {
                      ...formPolicies.weights,
                      proximityTravel: Number(e.target.value),
                    },
                  })
                }
                className="w-full accent-blue-600"
              />
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex justify-between font-bold text-slate-800 mb-1">
                <span>Workload Balance</span>
                <span>{formPolicies.weights.workloadBalance}%</span>
              </div>
              <input
                type="range"
                min={5}
                max={40}
                value={formPolicies.weights.workloadBalance}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    weights: {
                      ...formPolicies.weights,
                      workloadBalance: Number(e.target.value),
                    },
                  })
                }
                className="w-full accent-blue-600"
              />
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex justify-between font-bold text-slate-800 mb-1">
                <span>Deadline Feasibility</span>
                <span>{formPolicies.weights.deadlineFeasibility}%</span>
              </div>
              <input
                type="range"
                min={5}
                max={30}
                value={formPolicies.weights.deadlineFeasibility}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    weights: {
                      ...formPolicies.weights,
                      deadlineFeasibility: Number(e.target.value),
                    },
                  })
                }
                className="w-full accent-blue-600"
              />
            </div>

            <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex justify-between font-bold text-slate-800 mb-1">
                <span>Equipment Match</span>
                <span>{formPolicies.weights.equipmentMatch}%</span>
              </div>
              <input
                type="range"
                min={5}
                max={30}
                value={formPolicies.weights.equipmentMatch}
                onChange={(e) =>
                  setFormPolicies({
                    ...formPolicies,
                    weights: {
                      ...formPolicies.weights,
                      equipmentMatch: Number(e.target.value),
                    },
                  })
                }
                className="w-full accent-blue-600"
              />
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

