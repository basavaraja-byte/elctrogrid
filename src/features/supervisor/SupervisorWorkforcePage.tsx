import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Electrician, Job } from '../../types';
import { formatTimeIST, formatDateTimeIST } from '../../utils/formatters';
import { Modal } from '../../components/common/Modal';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import {
  Users,
  HardHat,
  Search,
  Filter,
  Clock,
  MapPin,
  Star,
  CheckCircle2,
  Battery,
  AlertCircle,
  Briefcase,
  ShieldCheck,
  CalendarDays,
  LayoutGrid,
  AlertTriangle,
  Info,
  Calendar,
} from 'lucide-react';

export const SupervisorWorkforcePage: React.FC = () => {
  const { electricians, jobs } = useApp();

  const [activeTab, setActiveTab] = useState<'cards' | 'gantt'>('cards');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [shiftFilter, setShiftFilter] = useState<string>('all');
  const [selectedJobPopup, setSelectedJobPopup] = useState<Job | null>(null);

  const filteredElectricians = electricians.filter((tech) => {
    if (statusFilter !== 'all' && tech.status !== statusFilter) return false;
    if (shiftFilter !== 'all' && tech.shift !== shiftFilter) return false;
    if (
      searchQuery.trim() &&
      !tech.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !tech.employeeId.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !tech.skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase())) &&
      !tech.certifications.some((c) => c.toLowerCase().includes(searchQuery.toLowerCase()))
    ) {
      return false;
    }
    return true;
  });

  const availableCount = electricians.filter((e) => e.status === 'available').length;
  const busyCount = electricians.filter((e) => e.status === 'busy').length;
  const enRouteCount = electricians.filter((e) => e.status === 'en_route').length;
  const totalWorkloadHours = electricians.reduce((acc, e) => acc + e.currentWorkload, 0);
  const avgWorkload = (totalWorkloadHours / (electricians.length || 1)).toFixed(1);

  // Timeline hours (08:00 to 20:00 IST - 12 hour operational window)
  const timelineHours = [
    '08:00',
    '09:00',
    '10:00',
    '11:00',
    '12:00',
    '13:00',
    '14:00',
    '15:00',
    '16:00',
    '17:00',
    '18:00',
    '19:00',
    '20:00',
  ];

  // Helper to parse start minutes from time string (e.g., "09:30" or "09:00 - 12:00")
  const getJobTimelineBounds = (job: Job, defaultSlotIdx: number) => {
    let startHour = 8 + (defaultSlotIdx % 4) * 2.5;
    let startMin = 0;

    if (job.scheduledStartTime) {
      const parts = job.scheduledStartTime.split(':');
      if (parts.length >= 2) {
        startHour = parseInt(parts[0], 10);
        startMin = parseInt(parts[1], 10);
      }
    } else if (job.preferredTimeWindow) {
      const startPart = job.preferredTimeWindow.split('-')[0]?.trim();
      const parts = startPart?.split(':');
      if (parts && parts.length >= 2) {
        startHour = parseInt(parts[0], 10);
        startMin = parseInt(parts[1], 10);
      }
    }

    // Baseline: 08:00 is 0 minutes
    const totalStartMinutes = Math.max(0, (startHour - 8) * 60 + startMin);
    const durationHours = job.estimatedDurationHours || 2;
    const durationMinutes = Math.max(45, durationHours * 60);

    // Total timeline window is 12 hours = 720 minutes
    const leftPct = Math.min(92, Math.max(1, (totalStartMinutes / 720) * 100));
    const widthPct = Math.min(100 - leftPct, Math.max(6, (durationMinutes / 720) * 100));

    return { leftPct, widthPct, startHour, startMin, durationHours };
  };

  return (
    <div className="space-y-6">
      {/* Header with Tab Switcher */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Workforce & Technician Telemetry
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Monitoring Only
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time shift adherence, workload distribution, and schedule timeline across Mysuru
          </p>
        </div>

        {/* View Switcher: Fleet Cards vs Gantt Timeline */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-white border border-slate-200 rounded-xl p-1 shadow-xs">
            <button
              onClick={() => setActiveTab('cards')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'cards'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>Fleet Cards</span>
            </button>
            <button
              onClick={() => setActiveTab('gantt')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition flex items-center gap-1.5 ${
                activeTab === 'gantt'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <CalendarDays className="w-3.5 h-3.5" />
              <span>Schedule Timeline (Gantt)</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Workload Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Total Field Technicians</span>
          <p className="text-2xl font-extrabold text-slate-900 mt-1">{electricians.length}</p>
          <span className="text-[11px] text-slate-500">Mysuru Grid Division</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Avg Daily Workload</span>
          <p className="text-2xl font-extrabold text-blue-600 mt-1">{avgWorkload}h</p>
          <span className="text-[11px] text-slate-500">Max limit 8.5h / day</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Fleet Utilization</span>
          <p className="text-2xl font-extrabold text-indigo-600 mt-1">
            {Math.round(((busyCount + enRouteCount) / electricians.length) * 100)}%
          </p>
          <span className="text-[11px] text-emerald-600 font-medium">Optimal balance</span>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-[11px] font-semibold text-slate-400 uppercase">Customer Rating</span>
          <p className="text-2xl font-extrabold text-amber-500 mt-1">★ 4.8</p>
          <span className="text-[11px] text-slate-500">Across 1,240 field repairs</span>
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
              placeholder="Search by technician name, employee ID, skill, or certification..."
              className="w-full pl-9 pr-3.5 py-2 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Duty Statuses</option>
              <option value="available">Available</option>
              <option value="en_route">En Route</option>
              <option value="busy">Busy / On-Site</option>
            </select>

            <select
              value={shiftFilter}
              onChange={(e) => setShiftFilter(e.target.value)}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Shifts</option>
              <option value="morning">Morning Shift (08:00 - 16:30)</option>
              <option value="afternoon">Afternoon Shift (12:00 - 20:30)</option>
              <option value="night">Night Shift (20:00 - 04:30)</option>
              <option value="flexible">Flexible Shift</option>
            </select>
          </div>
        </div>
      </div>

      {/* ================= TAB 1: FLEET CARDS ================= */}
      {activeTab === 'cards' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredElectricians.map((tech) => {
            const workloadPct = Math.min(100, Math.round((tech.currentWorkload / tech.maxDailyHours) * 100));
            const activeJob = tech.currentJobId ? jobs.find((j) => j.id === tech.currentJobId) : null;

            return (
              <div
                key={tech.id}
                className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md transition space-y-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <img
                      src={tech.avatar}
                      alt={tech.name}
                      className="w-12 h-12 rounded-full object-cover border-2 border-slate-200"
                    />
                    <div>
                      <h3 className="font-bold text-slate-900 text-sm">{tech.name}</h3>
                      <span className="text-xs font-mono text-slate-500 block">{tech.employeeId}</span>
                      <span className="text-[11px] text-slate-400">{tech.phone}</span>
                    </div>
                  </div>

                  <span
                    className={`px-2 py-0.5 rounded text-[11px] font-bold capitalize ${
                      tech.status === 'available'
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : tech.status === 'en_route'
                        ? 'bg-sky-50 text-sky-700 border border-sky-200'
                        : 'bg-amber-50 text-amber-700 border border-amber-200'
                    }`}
                  >
                    {tech.status.replace('_', ' ')}
                  </span>
                </div>

                {/* Workload Progress Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500 font-medium">Daily Workload</span>
                    <span className="font-bold text-slate-800">
                      {tech.currentWorkload}h / {tech.maxDailyHours}h ({workloadPct}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${
                        workloadPct > 80
                          ? 'bg-rose-500'
                          : workloadPct > 50
                          ? 'bg-blue-600'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${workloadPct}%` }}
                    />
                  </div>
                </div>

                {/* Shift & Telemetry Info */}
                <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-2.5 rounded-xl border border-slate-200 text-slate-600">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Shift Timing:</span>
                    <span className="font-semibold text-slate-800">{tech.shiftHours.start} - {tech.shiftHours.end}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Last GPS Ping:</span>
                    <span className="font-semibold text-slate-800">{formatTimeIST(tech.currentLocation.lastUpdated)}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Satisfaction:</span>
                    <span className="font-bold text-amber-600">★ {tech.rating}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Completed Total:</span>
                    <span className="font-semibold text-slate-800">{tech.jobsCompletedTotal} repairs</span>
                  </div>
                </div>

                {/* Active Assigned Job */}
                {activeJob && (
                  <div className="text-xs bg-blue-50/60 p-2.5 rounded-xl border border-blue-200">
                    <span className="text-[10px] font-bold uppercase text-blue-800 block mb-0.5">
                      Currently Assigned Job:
                    </span>
                    <p className="font-bold text-slate-900 truncate">{activeJob.title}</p>
                    <p className="text-[11px] text-slate-500 truncate">{activeJob.location.address}</p>
                  </div>
                )}

                {/* Certifications and Skills */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block">
                    Certifications:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {tech.certifications.slice(0, 2).map((cert, i) => (
                      <span
                        key={i}
                        className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium border border-slate-200"
                      >
                        {cert}
                      </span>
                    ))}
                    {tech.certifications.length > 2 && (
                      <span className="text-[10px] text-slate-400 self-center">
                        +{tech.certifications.length - 2} more
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ================= TAB 2: READ-ONLY GANTT SCHEDULE TIMELINE ================= */}
      {activeTab === 'gantt' && (
        <div className="space-y-4">
          {/* Gantt Legend & Disclaimer Banner */}
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">
                Schedule Status Legend:
              </span>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-blue-600" />
                <span className="text-slate-700">Assigned / Dispatched</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-cyan-600" />
                <span className="text-slate-700">En Route</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-amber-500" />
                <span className="text-slate-700">In Progress</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-emerald-600" />
                <span className="text-slate-700">Completed</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-rose-500 ring-2 ring-rose-300" />
                <span className="text-rose-700 font-semibold">At-Risk / Delayed</span>
              </div>
            </div>

            <div className="text-[11px] text-slate-500 bg-slate-50 px-2.5 py-1 rounded border border-slate-200 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
              <span>Read-only operational timeline • Click any job block to inspect details</span>
            </div>
          </div>

          {/* Main Gantt Timeline Container */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-x-auto">
            <div className="min-w-[1040px]">
              {/* Timeline Time Axis Header */}
              <div className="grid grid-cols-12 border-b border-slate-200 bg-slate-50/80 text-xs font-bold text-slate-600 py-3 px-4">
                <div className="col-span-3 font-bold uppercase tracking-wider text-[11px] text-slate-500">
                  Technician / Shift
                </div>
                <div className="col-span-9 grid grid-cols-12 text-center text-[11px]">
                  {timelineHours.slice(0, 12).map((hour, idx) => (
                    <div key={idx} className="border-l border-slate-200/80 px-1 font-mono text-slate-500">
                      {hour}
                    </div>
                  ))}
                </div>
              </div>

              {/* Rows for Technicians */}
              <div className="divide-y divide-slate-100">
                {filteredElectricians.map((tech) => {
                  const techJobs = jobs.filter(
                    (j) =>
                      j.assignedElectricianId === tech.id &&
                      j.status !== 'cancelled'
                  );

                  return (
                    <div
                      key={tech.id}
                      className="grid grid-cols-12 items-center py-3 px-4 hover:bg-slate-50/50 transition group"
                    >
                      {/* Left Column: Technician Profile & Shift */}
                      <div className="col-span-3 pr-4 flex items-center gap-3">
                        <img
                          src={tech.avatar}
                          alt={tech.name}
                          className="w-9 h-9 rounded-full object-cover border border-slate-200 shadow-xs"
                        />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold text-slate-900 truncate">
                              {tech.name}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {tech.employeeId.replace('MYS-TECH-', 'T')}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-[10px] text-slate-500">
                            <span className="capitalize">{tech.shift} ({tech.shiftHours.start}-{tech.shiftHours.end})</span>
                            <span>•</span>
                            <span className="font-semibold text-slate-700">{tech.currentWorkload}h</span>
                          </div>
                        </div>
                      </div>

                      {/* Right Column: Interactive Timeline Track */}
                      <div className="col-span-9 relative h-12 border-l border-slate-200/80 bg-slate-50/20 rounded-lg overflow-hidden flex items-center">
                        {/* Hour Grid Lines */}
                        <div className="absolute inset-0 grid grid-cols-12 pointer-events-none">
                          {Array.from({ length: 12 }).map((_, i) => (
                            <div key={i} className="border-r border-slate-100 h-full" />
                          ))}
                        </div>

                        {/* Render Scheduled Jobs */}
                        {techJobs.length > 0 ? (
                          techJobs.map((job, idx) => {
                            const { leftPct, widthPct } = getJobTimelineBounds(job, idx);
                            const isAtRisk = job.isOverdue || job.slaRisk === 'warning' || job.slaRisk === 'breached';

                            let blockColor = 'bg-blue-600 text-white border-blue-700';
                            if (job.status === 'completed' || job.status === 'closed') {
                              blockColor = 'bg-emerald-600 text-white border-emerald-700';
                            } else if (job.status === 'en_route') {
                              blockColor = 'bg-cyan-600 text-white border-cyan-700';
                            } else if (job.status === 'in_progress') {
                              blockColor = 'bg-amber-500 text-white border-amber-600';
                            }

                            return (
                              <div
                                key={job.id}
                                onClick={() => setSelectedJobPopup(job)}
                                style={{
                                  left: `${leftPct}%`,
                                  width: `${widthPct}%`,
                                }}
                                className={`absolute h-9 rounded-lg px-2 py-1 shadow-xs cursor-pointer hover:shadow-md transition flex flex-col justify-between border overflow-hidden select-none ${blockColor} ${
                                  isAtRisk ? 'ring-2 ring-rose-400 animate-pulse' : ''
                                }`}
                                title={`${job.id}: ${job.title} (${job.preferredTimeWindow})`}
                              >
                                <div className="flex items-center justify-between gap-1">
                                  <span className="font-mono text-[10px] font-bold truncate">
                                    {job.id}
                                  </span>
                                  {isAtRisk && (
                                    <AlertTriangle className="w-3 h-3 text-white flex-shrink-0" />
                                  )}
                                </div>
                                <span className="text-[10px] font-medium truncate leading-none">
                                  {job.title}
                                </span>
                              </div>
                            );
                          })
                        ) : (
                          <span className="text-[11px] text-slate-400 italic pl-3 select-none">
                            Standby / Ready for autonomous assignment
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}

                {filteredElectricians.length === 0 && (
                  <div className="p-12 text-center text-slate-400 text-xs">
                    <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                    <p>No field technicians matching the filter criteria.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ================= READ-ONLY JOB POPUP MODAL ================= */}
      {selectedJobPopup && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedJobPopup(null)}
          title={`Scheduled Field Assignment • ${selectedJobPopup.id}`}
          subtitle="Read-only timeline inspection of allocated work order"
          maxWidth="lg"
        >
          <div className="space-y-4">
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-slate-600">{selectedJobPopup.id}</span>
                <div className="flex items-center gap-1.5">
                  <PriorityBadge priority={selectedJobPopup.priority} />
                  <StatusBadge status={selectedJobPopup.status} size="sm" />
                </div>
              </div>
              <h3 className="text-sm font-bold text-slate-900">{selectedJobPopup.title}</h3>
              <p className="text-xs text-slate-600 bg-white p-2.5 rounded-lg border border-slate-200">
                {selectedJobPopup.description}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-200">
              <div>
                <span className="text-slate-400 block text-[10px]">Service Location:</span>
                <span className="font-semibold text-slate-800">{selectedJobPopup.location.address}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Assigned Technician:</span>
                <span className="font-bold text-blue-700">{selectedJobPopup.assignedElectricianName}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Scheduled Window:</span>
                <span className="font-semibold text-slate-800">{selectedJobPopup.preferredTimeWindow}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Estimated Duration:</span>
                <span className="font-semibold text-slate-800">~{selectedJobPopup.estimatedDurationHours} Hours</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedJobPopup(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
