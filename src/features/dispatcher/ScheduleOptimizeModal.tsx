import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { Job, ScheduleRecommendationResult, ElectricianScoreBreakdown } from '../../types';
import { Modal } from '../../components/common/Modal';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import {
  Sparkles,
  CheckCircle,
  AlertTriangle,
  Zap,
  MapPin,
  Clock,
  Briefcase,
  ShieldCheck,
  Send,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

interface ScheduleOptimizeModalProps {
  job: Job | null;
  isOpen: boolean;
  onClose: () => void;
  onAssigned?: (jobId: string, electricianId: string) => void;
}

export const ScheduleOptimizeModal: React.FC<ScheduleOptimizeModalProps> = ({
  job,
  isOpen,
  onClose,
  onAssigned,
}) => {
  const { user } = useAuth();
  const { refreshData, policies } = useApp();

  const [recommendations, setRecommendations] = useState<ScheduleRecommendationResult | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [startTime, setStartTime] = useState('09:30');
  const [endTime, setEndTime] = useState('11:45');
  const [dispatchType, setDispatchType] = useState<'automatic' | 'manual'>('automatic');
  const [isProcessing, setIsProcessing] = useState(false);
  const [showWeightsConfig, setShowWeightsConfig] = useState(false);
  const [weights, setWeights] = useState(policies.weights);

  useEffect(() => {
    if (job && isOpen) {
      runOptimization();
    }
  }, [job, isOpen]);

  const runOptimization = async () => {
    if (!job) return;
    setIsProcessing(true);
    try {
      const res = await api.optimizeSchedule(job.id);
      setRecommendations(res);
      if (res.recommendedElectrician) {
        setSelectedCandidateId(res.recommendedElectrician.electricianId);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDispatch = async () => {
    if (!job || !selectedCandidateId || !user) return;
    setIsProcessing(true);

    try {
      await api.assignAndDispatchJob(
        job.id,
        selectedCandidateId,
        startTime,
        endTime,
        dispatchType,
        user
      );
      refreshData();
      if (onAssigned) onAssigned(job.id, selectedCandidateId);
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  if (!job) return null;

  const topCandidate = recommendations?.recommendedElectrician;
  const isSelectedTop = selectedCandidateId === topCandidate?.electricianId;
  const canAutoDispatch =
    topCandidate &&
    topCandidate.overallScore >= policies.autoDispatchMinScoreThreshold &&
    policies.autoDispatchEnabled;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Intelligent Dispatch Engine"
      subtitle={`Constraint-aware scoring & assignment for ${job.id}`}
      maxWidth="4xl"
    >
      <div className="space-y-6">
        {/* Job Context Banner */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono font-bold text-xs text-blue-600">{job.id}</span>
              <PriorityBadge priority={job.priority} />
              <StatusBadge status={job.status} size="sm" />
            </div>
            <h3 className="text-sm font-bold text-slate-900">{job.title}</h3>
            <p className="text-xs text-slate-500 flex items-center gap-2 mt-1">
              <MapPin className="w-3.5 h-3.5 text-slate-400" />
              {job.location.address}
            </p>
          </div>

          <div className="text-right sm:border-l sm:pl-4 border-slate-200 text-xs text-slate-600">
            <div>
              <b>Duration:</b> ~{job.estimatedDurationHours}h
            </div>
            <div className="mt-0.5">
              <b>Required Skills:</b>{' '}
              <span className="text-blue-700 font-medium">
                {job.requiredSkills.join(', ') || 'Standard Electrical'}
              </span>
            </div>
          </div>
        </div>

        {/* Weights Configuration Drawer */}
        <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-xs">
          <button
            type="button"
            onClick={() => setShowWeightsConfig(!showWeightsConfig)}
            className="w-full flex items-center justify-between text-xs font-bold text-slate-700"
          >
            <span className="flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5 text-blue-600" />
              Scoring Weight Parameters (Policy Defined)
            </span>
            <div className="flex items-center gap-1 text-blue-600">
              <span className="text-[11px]">
                {showWeightsConfig ? 'Hide Settings' : 'View / Adjust Weights'}
              </span>
              {showWeightsConfig ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </div>
          </button>

          {showWeightsConfig && (
            <div className="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <label className="text-slate-500 block text-[11px]">Skill Match ({weights.skillCompatibility}%)</label>
                <input
                  type="range"
                  min={10}
                  max={50}
                  value={weights.skillCompatibility}
                  onChange={(e) => setWeights({ ...weights, skillCompatibility: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
              </div>
              <div>
                <label className="text-slate-500 block text-[11px]">Availability & Shift ({weights.availabilityShift}%)</label>
                <input
                  type="range"
                  min={10}
                  max={50}
                  value={weights.availabilityShift}
                  onChange={(e) => setWeights({ ...weights, availabilityShift: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
              </div>
              <div>
                <label className="text-slate-500 block text-[11px]">Proximity & Distance ({weights.proximityTravel}%)</label>
                <input
                  type="range"
                  min={10}
                  max={50}
                  value={weights.proximityTravel}
                  onChange={(e) => setWeights({ ...weights, proximityTravel: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
              </div>
              <div>
                <label className="text-slate-500 block text-[11px]">Workload Balance ({weights.workloadBalance}%)</label>
                <input
                  type="range"
                  min={5}
                  max={40}
                  value={weights.workloadBalance}
                  onChange={(e) => setWeights({ ...weights, workloadBalance: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
              </div>
              <div>
                <label className="text-slate-500 block text-[11px]">Deadline Feasibility ({weights.deadlineFeasibility}%)</label>
                <input
                  type="range"
                  min={5}
                  max={30}
                  value={weights.deadlineFeasibility}
                  onChange={(e) => setWeights({ ...weights, deadlineFeasibility: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
              </div>
              <div>
                <label className="text-slate-500 block text-[11px]">Equipment Match ({weights.equipmentMatch}%)</label>
                <input
                  type="range"
                  min={5}
                  max={30}
                  value={weights.equipmentMatch}
                  onChange={(e) => setWeights({ ...weights, equipmentMatch: Number(e.target.value) })}
                  className="w-full accent-blue-600"
                />
              </div>
            </div>
          )}
        </div>

        {/* Recommended Top Electrician Card */}
        {topCandidate ? (
          <div
            onClick={() => setSelectedCandidateId(topCandidate.electricianId)}
            className={`p-5 rounded-2xl border-2 transition cursor-pointer relative ${
              isSelectedTop
                ? 'bg-blue-50/60 border-blue-600 shadow-md ring-2 ring-blue-500/20'
                : 'bg-white border-slate-200 hover:border-blue-300'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-600 text-white flex items-center gap-1 shadow-xs">
                  <Sparkles className="w-3.5 h-3.5" />
                  Primary Recommended Candidate
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  ID: {topCandidate.electricianId}
                </span>
              </div>

              {/* Big Score Pill */}
              <div className="flex items-baseline gap-1 bg-white px-3 py-1 rounded-xl border border-blue-200 shadow-xs">
                <span className="text-xl font-extrabold text-blue-700">
                  {topCandidate.overallScore}%
                </span>
                <span className="text-[10px] uppercase font-bold text-slate-400">Match Score</span>
              </div>
            </div>

            <h4 className="text-base font-extrabold text-slate-900">
              {topCandidate.electricianName}
            </h4>

            {/* Why Recommended Pill */}
            <p className="text-xs text-blue-900 font-semibold bg-blue-100/70 p-2.5 rounded-lg mt-2 flex items-center gap-1.5">
              <Zap className="w-4 h-4 text-blue-600 flex-shrink-0" />
              <span>{topCandidate.recommendationReason}</span>
            </p>

            {/* Metrics Breakdown Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-4 text-xs">
              <div className="p-2.5 rounded-lg bg-white border border-slate-200/80">
                <span className="text-[11px] text-slate-400 block">Proximity / Distance</span>
                <span className="font-bold text-slate-800">
                  {topCandidate.metrics.estimatedDistanceKm} km
                </span>
                <span className="text-[10px] text-slate-500 block">
                  ~{topCandidate.metrics.estimatedTravelMinutes} mins travel
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-white border border-slate-200/80">
                <span className="text-[11px] text-slate-400 block">Workload After</span>
                <span className="font-bold text-slate-800">
                  {topCandidate.metrics.workloadAfterHours}h / 8.5h
                </span>
                <span className="text-[10px] text-emerald-600 block font-semibold">
                  Safe workload limit
                </span>
              </div>

              <div className="p-2.5 rounded-lg bg-white border border-slate-200/80">
                <span className="text-[11px] text-slate-400 block">Skill Match</span>
                <span className="font-bold text-slate-800">
                  {topCandidate.scores.skillScore}%
                </span>
                <span className="text-[10px] text-slate-500 block">All criteria met</span>
              </div>

              <div className="p-2.5 rounded-lg bg-white border border-slate-200/80">
                <span className="text-[11px] text-slate-400 block">Shift & Availability</span>
                <span className="font-bold text-slate-800">
                  {topCandidate.scores.availabilityScore}%
                </span>
                <span className="text-[10px] text-slate-500 block">Immediate window</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 bg-red-50 rounded-xl border border-red-200 text-center">
            <AlertTriangle className="w-8 h-8 text-red-600 mx-auto mb-2" />
            <h4 className="text-sm font-bold text-red-900">
              No Feasible Electrician Found
            </h4>
            <p className="text-xs text-red-700 mt-1">
              {recommendations?.infeasibleReasonsSummary.join(' • ') ||
                'All candidates violated mandatory skill or maximum workload constraints.'}
            </p>
          </div>
        )}

        {/* Alternative Candidates List */}
        {recommendations && recommendations.alternatives.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              Alternative Qualified Candidates ({recommendations.alternatives.length})
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {recommendations.alternatives.map((alt) => {
                const isSelected = selectedCandidateId === alt.electricianId;
                return (
                  <div
                    key={alt.electricianId}
                    onClick={() => setSelectedCandidateId(alt.electricianId)}
                    className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50/50 shadow-xs ring-1 ring-blue-500'
                        : 'border-slate-200 hover:border-slate-300 bg-white'
                    }`}
                  >
                    <div>
                      <h5 className="text-xs font-bold text-slate-900">{alt.electricianName}</h5>
                      <p className="text-[11px] text-slate-500">
                        {alt.metrics.estimatedDistanceKm} km away • Workload: {alt.metrics.workloadAfterHours}h
                      </p>
                    </div>
                    <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                      {alt.overallScore}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Dispatch Controls & Time Window */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Dispatch Mode
            </label>
            <select
              value={dispatchType}
              onChange={(e) => setDispatchType(e.target.value as any)}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white"
            >
              <option value="automatic">Automatic Policy Dispatch</option>
              <option value="manual">Manual Dispatch Override</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Scheduled Start Time
            </label>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Scheduled End Time
            </label>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg bg-white"
            />
          </div>
        </div>

        {/* Action Footer */}
        <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Cancel
          </button>

          <button
            type="button"
            disabled={!selectedCandidateId || isProcessing}
            onClick={handleDispatch}
            className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 transition disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            {isProcessing ? 'Executing Dispatch...' : 'Confirm & Dispatch Electrician'}
          </button>
        </div>
      </div>
    </Modal>
  );
};

