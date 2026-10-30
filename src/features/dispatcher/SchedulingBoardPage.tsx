import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Job, Electrician } from '../../types';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { ScheduleOptimizeModal } from './ScheduleOptimizeModal';
import {
  CalendarDays,
  Clock,
  Sparkles,
  HardHat,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Filter,
  Layers,
} from 'lucide-react';

export const SchedulingBoardPage: React.FC = () => {
  const { jobs, electricians } = useApp();

  const [viewMode, setViewMode] = useState<'daily' | 'weekly'>('daily');
  const [selectedJobForOptimize, setSelectedJobForOptimize] = useState<Job | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );

  const unassignedJobs = jobs.filter(
    (j) => !j.assignedElectricianId && j.status !== 'completed' && j.status !== 'cancelled'
  );

  const hoursSlots = [
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
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Interactive Scheduling Board
          </h1>
          <p className="text-sm text-slate-500">
            Technician timeline view, shift balancing, and assignment conflict detection
          </p>
        </div>

        {/* View Switcher & Date Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-white border border-slate-200 rounded-xl p-1 shadow-xs">
            <button
              onClick={() => setViewMode('daily')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
                viewMode === 'daily'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Daily Timeline
            </button>
            <button
              onClick={() => setViewMode('weekly')}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition ${
                viewMode === 'weekly'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Weekly Overview
            </button>
          </div>

          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-3 py-1.5 text-xs border border-slate-200 rounded-xl bg-white shadow-xs font-medium"
          />
        </div>
      </div>

      {/* Unassigned Operational Jobs Drawer */}
      {unassignedJobs.length > 0 && (
        <div className="bg-amber-50/70 border border-amber-300 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900">
                Unassigned Jobs Queue ({unassignedJobs.length} tickets pending dispatch)
              </h3>
            </div>
            <span className="text-[11px] text-amber-800">
              Click 'Optimize' to match available technicians
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {unassignedJobs.slice(0, 3).map((job) => (
              <div
                key={job.id}
                className="bg-white p-3.5 rounded-xl border border-amber-200 shadow-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs font-bold text-amber-700">{job.id}</span>
                    <PriorityBadge priority={job.priority} />
                  </div>
                  <h4 className="text-xs font-bold text-slate-900 line-clamp-1">{job.title}</h4>
                  <p className="text-[11px] text-slate-500 mt-1 line-clamp-1">
                    📍 {job.location.address}
                  </p>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">~{job.estimatedDurationHours}h duration</span>
                  <button
                    onClick={() => setSelectedJobForOptimize(job)}
                    className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg flex items-center gap-1 transition"
                  >
                    <Sparkles className="w-3 h-3" />
                    Optimize
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Timeline Grid */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
        <div className="min-w-[900px]">
          {/* Timeline Header with Time Slots */}
          <div className="grid grid-cols-12 border-b border-slate-200 bg-slate-50/70 text-xs font-bold text-slate-500 uppercase tracking-wider py-3 px-4">
            <div className="col-span-3">Electrician / Fleet Crew</div>
            <div className="col-span-9 grid grid-cols-10 text-center">
              {hoursSlots.map((h, i) => (
                <div key={i} className="border-l border-slate-200/70 text-[11px]">
                  {h}
                </div>
              ))}
            </div>
          </div>

          {/* Electrician Timeline Rows */}
          <div className="divide-y divide-slate-100">
            {electricians.slice(0, 10).map((tech) => {
              // Find jobs assigned to this technician
              const techJobs = jobs.filter(
                (j) =>
                  j.assignedElectricianId === tech.id &&
                  j.status !== 'completed' &&
                  j.status !== 'closed'
              );

              return (
                <div
                  key={tech.id}
                  className="grid grid-cols-12 items-center py-3 px-4 hover:bg-slate-50/50 transition"
                >
                  {/* Left Column: Electrician Card */}
                  <div className="col-span-3 pr-4 flex items-center gap-2.5">
                    <img
                      src={tech.avatar}
                      alt={tech.name}
                      className="w-8 h-8 rounded-full object-cover border border-slate-200"
                    />
                    <div className="min-w-0">
                      <span className="text-xs font-bold text-slate-900 block truncate">
                        {tech.name}
                      </span>
                      <span className="text-[10px] text-slate-500 capitalize block">
                        {tech.shift} shift • {tech.currentWorkload}h / {tech.maxDailyHours}h
                      </span>
                    </div>
                  </div>

                  {/* Right Column: Timeline Slot Cards */}
                  <div className="col-span-9 grid grid-cols-10 gap-1 h-12 relative border-l border-slate-100 pl-1">
                    {techJobs.length > 0 ? (
                      techJobs.map((job, idx) => {
                        const colSpan = Math.min(5, Math.max(2, Math.round(job.estimatedDurationHours)));
                        return (
                          <div
                            key={job.id}
                            onClick={() => setSelectedJobForOptimize(job)}
                            className="bg-blue-600 text-white rounded-lg p-1.5 shadow-xs cursor-pointer hover:bg-blue-700 transition flex flex-col justify-between overflow-hidden"
                            style={{
                              gridColumn: `span ${colSpan}`,
                            }}
                          >
                            <div className="flex items-center justify-between text-[10px] font-bold">
                              <span className="font-mono">{job.id}</span>
                              <span className="opacity-90">{job.scheduledStartTime || '09:30'}</span>
                            </div>
                            <span className="text-[10px] truncate block opacity-95">
                              {job.title}
                            </span>
                          </div>
                        );
                      })
                    ) : (
                      <div className="col-span-10 flex items-center justify-center text-[11px] text-slate-300 italic">
                        Available • No conflict
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Intelligent Scheduling Optimizer Modal */}
      <ScheduleOptimizeModal
        job={selectedJobForOptimize}
        isOpen={!!selectedJobForOptimize}
        onClose={() => setSelectedJobForOptimize(null)}
      />
    </div>
  );
};

