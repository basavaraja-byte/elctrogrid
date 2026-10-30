import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { LeafletMap } from '../../components/maps/LeafletMap';
import { Electrician, Job } from '../../types';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import {
  Map,
  Radio,
  Users,
  HardHat,
  Phone,
  ShieldCheck,
  MapPin,
  Clock,
  X,
} from 'lucide-react';

export const LiveWorkforceMapPage: React.FC = () => {
  const { electricians, jobs } = useApp();

  const [selectedTech, setSelectedTech] = useState<Electrician | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const activeJobs = jobs.filter(
    (j) => j.status !== 'completed' && j.status !== 'closed' && j.status !== 'cancelled'
  );

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Live Workforce & Field Asset Map
          </h1>
          <p className="text-sm text-slate-500">
            Real-time geospatial tracking of 20 certified electricians and active operational sites
          </p>
        </div>
      </div>

      {/* Main Map + Inspection Panel Container */}
      <div className="relative rounded-2xl overflow-hidden border border-slate-200 shadow-md">
        <LeafletMap
          electricians={electricians}
          jobs={activeJobs}
          selectedElectricianId={selectedTech?.id}
          selectedJobId={selectedJob?.id}
          onSelectElectrician={(tech) => {
            setSelectedTech(tech);
            setSelectedJob(null);
          }}
          onSelectJob={(job) => {
            setSelectedJob(job);
            setSelectedTech(null);
          }}
          height="650px"
        />

        {/* Selected Technician Drawer Overlay */}
        {selectedTech && (
          <div className="absolute top-14 right-4 z-[1000] w-80 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-200 p-4 text-xs space-y-3 animate-slideLeft">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">
                Electrician Telemetry
              </span>
              <button
                onClick={() => setSelectedTech(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center gap-3">
              <img
                src={selectedTech.avatar}
                alt={selectedTech.name}
                className="w-11 h-11 rounded-full object-cover border border-slate-200"
              />
              <div>
                <h4 className="font-bold text-slate-900 text-sm">{selectedTech.name}</h4>
                <p className="text-slate-500 font-mono text-[11px]">{selectedTech.employeeId}</p>
              </div>
            </div>

            <div className="space-y-1.5 pt-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Duty Status:</span>
                <span className="font-bold capitalize text-slate-800">
                  {selectedTech.status.replace('_', ' ')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Shift Window:</span>
                <span className="font-semibold text-slate-800">
                  {selectedTech.shiftHours.start} - {selectedTech.shiftHours.end}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Workload:</span>
                <span className="font-semibold text-slate-800">
                  {selectedTech.currentWorkload}h / {selectedTech.maxDailyHours}h
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Satisfaction:</span>
                <span className="font-semibold text-amber-600">
                  ★ {selectedTech.rating} / 5.0
                </span>
              </div>
            </div>

            <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-600">
              <span className="font-bold text-slate-700 block mb-0.5">Fleet Gear:</span>
              <span>{selectedTech.equipment.slice(0, 2).join(', ')}</span>
            </div>

            <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <Radio className="w-3 h-3 text-emerald-500" />
                GPS Ping Verified
              </span>
              <span>{new Date(selectedTech.currentLocation.lastUpdated).toLocaleTimeString()}</span>
            </div>
          </div>
        )}

        {/* Selected Job Drawer Overlay */}
        {selectedJob && (
          <div className="absolute top-14 right-4 z-[1000] w-80 bg-white/95 backdrop-blur-md rounded-2xl shadow-2xl border border-slate-200 p-4 text-xs space-y-3 animate-slideLeft">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <span className="font-bold uppercase tracking-wider text-slate-400 text-[10px]">
                Job Site Details
              </span>
              <button
                onClick={() => setSelectedJob(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="font-mono font-bold text-blue-700">{selectedJob.id}</span>
                <PriorityBadge priority={selectedJob.priority} />
                <StatusBadge status={selectedJob.status} size="sm" />
              </div>
              <h4 className="font-bold text-slate-900 text-sm">{selectedJob.title}</h4>
            </div>

            <div className="space-y-1.5 pt-1 text-slate-600">
              <p><b>Customer:</b> {selectedJob.customerName}</p>
              <p><b>Address:</b> {selectedJob.location.address}</p>
              <p><b>Target Window:</b> {selectedJob.preferredTimeWindow}</p>
              <p>
                <b>Assigned Tech:</b>{' '}
                <span className="text-slate-900 font-bold">
                  {selectedJob.assignedElectricianName || 'Unassigned'}
                </span>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

