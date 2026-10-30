import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Job, Electrician } from '../../types';
import { formatTimeIST, formatDateTimeIST } from '../../utils/formatters';
import { PriorityBadge, StatusBadge } from '../../components/common/StatusBadge';
import {
  Cpu,
  Layers,
  Sparkles,
  CheckCircle2,
  Sliders,
  TrendingUp,
  MapPin,
  HardHat,
  Clock,
  ShieldCheck,
  Search,
  Info,
} from 'lucide-react';

export const SupervisorAutomatedSchedulingPage: React.FC = () => {
  const { jobs, electricians, policies } = useApp();
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Jobs that have been scheduled/assigned
  const scheduledJobs = jobs
    .filter((j) => j.assignedElectricianId)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  const filteredJobs = scheduledJobs.filter((j) => {
    if (
      searchQuery.trim() &&
      !j.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !j.id.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !(j.assignedElectricianName && j.assignedElectricianName.toLowerCase().includes(searchQuery.toLowerCase()))
    ) {
      return false;
    }
    return true;
  });

  const selectedJob = scheduledJobs.find((j) => j.id === selectedJobId) || scheduledJobs[0];
  const assignedTech = selectedJob
    ? electricians.find((e) => e.id === selectedJob.assignedElectricianId)
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Automated Scheduling Engine Log
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Monitoring Only
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time algorithmic observability into autonomous candidate scoring and dispatch assignments
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Engine Status: Fully Autonomous
          </span>
        </div>
      </div>

      {/* Algorithm Weights Observability Card */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-6 text-white shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-blue-200 border border-white/10 mb-2">
              <Cpu className="w-3.5 h-3.5 text-blue-300" />
              <span>Multi-Criteria Optimization Weights (Read-Only)</span>
            </div>
            <h2 className="text-lg font-bold">Autonomous Dispatch Scoring Formula</h2>
            <p className="text-xs text-slate-300">
              Evaluates all 20 Mysuru technicians instantaneously upon complaint submission. Minimum auto-dispatch threshold: {policies.autoDispatchMinScoreThreshold}%
            </p>
          </div>

          <div className="text-right">
            <span className="text-2xl font-extrabold text-emerald-400">100%</span>
            <span className="text-xs text-slate-300 block">Autonomous Coverage</span>
          </div>
        </div>

        {/* Weights progress bars */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
          <div className="bg-white/10 p-3 rounded-xl border border-white/10">
            <span className="text-[10px] uppercase text-blue-200 font-semibold block">Skill Compatibility</span>
            <span className="text-lg font-extrabold text-white">{policies.weights.skillCompatibility}%</span>
            <span className="text-[10px] text-slate-300 block mt-0.5">CHESCOM / KPTCL Certs</span>
          </div>
          <div className="bg-white/10 p-3 rounded-xl border border-white/10">
            <span className="text-[10px] uppercase text-blue-200 font-semibold block">Travel Proximity</span>
            <span className="text-lg font-extrabold text-white">{policies.weights.proximityTravel}%</span>
            <span className="text-[10px] text-slate-300 block mt-0.5">Mysuru Feeder Distance</span>
          </div>
          <div className="bg-white/10 p-3 rounded-xl border border-white/10">
            <span className="text-[10px] uppercase text-blue-200 font-semibold block">Shift Availability</span>
            <span className="text-lg font-extrabold text-white">{policies.weights.availabilityShift}%</span>
            <span className="text-[10px] text-slate-300 block mt-0.5">Active Duty Window</span>
          </div>
          <div className="bg-white/10 p-3 rounded-xl border border-white/10">
            <span className="text-[10px] uppercase text-blue-200 font-semibold block">Workload Balance</span>
            <span className="text-lg font-extrabold text-white">{policies.weights.workloadBalance}%</span>
            <span className="text-[10px] text-slate-300 block mt-0.5">Fatigue & Max 8.5h Limit</span>
          </div>
          <div className="bg-white/10 p-3 rounded-xl border border-white/10">
            <span className="text-[10px] uppercase text-blue-200 font-semibold block">Deadline Feasibility</span>
            <span className="text-lg font-extrabold text-white">{policies.weights.deadlineFeasibility}%</span>
            <span className="text-[10px] text-slate-300 block mt-0.5">SLA Time Window</span>
          </div>
          <div className="bg-white/10 p-3 rounded-xl border border-white/10">
            <span className="text-[10px] uppercase text-blue-200 font-semibold block">Equipment Match</span>
            <span className="text-lg font-extrabold text-white">{policies.weights.equipmentMatch}%</span>
            <span className="text-[10px] text-slate-300 block mt-0.5">Arc PPE & Testing Kits</span>
          </div>
        </div>
      </div>

      {/* Main Split: Scheduling Decision Stream & Candidate Evaluation Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Automated Decisions */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs flex items-center justify-between gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by job ID, title, or technician..."
                className="w-full pl-9 pr-3.5 py-1.5 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <span className="text-xs text-slate-400 font-semibold whitespace-nowrap">
              {filteredJobs.length} Auto-Dispatched
            </span>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm divide-y divide-slate-100 overflow-hidden">
            {filteredJobs.map((j) => {
              const isSelected = selectedJob?.id === j.id;
              return (
                <div
                  key={j.id}
                  onClick={() => setSelectedJobId(j.id)}
                  className={`p-4 transition cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isSelected ? 'bg-blue-50/70 border-l-4 border-l-blue-600' : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-600">{j.id}</span>
                      <PriorityBadge priority={j.priority} />
                      <StatusBadge status={j.status} size="sm" />
                    </div>
                    <p className="font-bold text-slate-900 text-sm truncate">{j.title}</p>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        {j.location.address}
                      </span>
                      <span className="flex items-center gap-1 font-semibold text-slate-800">
                        <HardHat className="w-3.5 h-3.5 text-blue-600" />
                        {j.assignedElectricianName}
                      </span>
                    </div>
                  </div>

                  <div className="text-right flex-shrink-0">
                    <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 block">
                      Score: 94 / 100
                    </span>
                    <span className="text-[10px] text-slate-400 block mt-1">
                      {formatTimeIST(j.createdAt)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Col: Deep Candidate Evaluation Breakdown */}
        <div>
          {selectedJob && assignedTech ? (
            <div className="bg-white rounded-2xl border-2 border-blue-500 p-5 shadow-md space-y-4 sticky top-20">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                  Autonomous Decision Record
                </span>
                <span className="text-xs font-mono font-bold text-slate-500">{selectedJob.id}</span>
              </div>

              <div>
                <h3 className="font-bold text-slate-900 text-sm">{selectedJob.title}</h3>
                <p className="text-xs text-slate-500 mt-0.5">{selectedJob.location.address}</p>
              </div>

              {/* Selected Candidate Card */}
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex items-center gap-3">
                <img
                  src={assignedTech.avatar}
                  alt={assignedTech.name}
                  className="w-11 h-11 rounded-full object-cover border-2 border-blue-400"
                />
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-slate-900 text-xs">{assignedTech.name}</span>
                    <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.2 rounded">
                      Selected
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500">{assignedTech.employeeId}</p>
                  <p className="text-[11px] text-slate-600">Workload: {assignedTech.currentWorkload}h / 8.5h</p>
                </div>
              </div>

              {/* Score breakdown metrics */}
              <div className="space-y-2 text-xs">
                <span className="font-bold text-slate-700 uppercase tracking-wider text-[10px] block">
                  Candidate Evaluation Factors:
                </span>

                <div className="space-y-1.5 bg-slate-50 p-3 rounded-xl border border-slate-200">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-600">Skill Compatibility:</span>
                    <span className="font-bold text-emerald-600">98 / 100</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-1.5">
                    <div className="bg-emerald-500 h-1.5 rounded-full" style={{ width: '98%' }} />
                  </div>

                  <div className="flex justify-between items-center pt-1">
                    <span className="text-slate-600">Travel Proximity (Mysuru):</span>
                    <span className="font-bold text-blue-600">92 / 100</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-1.5">
                    <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: '92%' }} />
                  </div>

                  <div className="flex justify-between items-center pt-1">
                    <span className="text-slate-600">Shift Availability:</span>
                    <span className="font-bold text-indigo-600">100 / 100</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-1.5">
                    <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: '100%' }} />
                  </div>

                  <div className="flex justify-between items-center pt-1">
                    <span className="text-slate-600">Workload Balance:</span>
                    <span className="font-bold text-amber-600">86 / 100</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-1.5">
                    <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: '86%' }} />
                  </div>
                </div>
              </div>

              {/* Decision Note */}
              <div className="p-3 bg-blue-50/60 rounded-xl border border-blue-200 text-xs text-blue-900 flex items-start gap-2">
                <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  Composite score exceeded the {policies.autoDispatchMinScoreThreshold}% threshold. Automated engine dispatched immediately without holding for manual validation.
                </p>
              </div>

              <div className="text-[11px] text-slate-400 text-right">
                Decision evaluated at: {formatDateTimeIST(selectedJob.createdAt)}
              </div>
            </div>
          ) : (
            <div className="bg-white p-6 rounded-2xl border border-slate-200 text-center text-slate-400 text-xs">
              <Cpu className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p>Select a job from the list to inspect algorithmic score breakdown.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

