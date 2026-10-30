import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { LeafletMap } from '../../components/maps/LeafletMap';
import { Electrician, Job } from '../../types';
import { formatTimeIST, formatDateTimeIST } from '../../utils/formatters';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import {
  Radio,
  MapPin,
  HardHat,
  Search,
  Filter,
  Layers,
  Battery,
  Gauge,
  Phone,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Sparkles,
  Info,
} from 'lucide-react';

export const SupervisorMapPage: React.FC = () => {
  const { electricians, jobs } = useApp();

  const [selectedTechId, setSelectedTechId] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<'all' | 'available' | 'busy' | 'en_route'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const activeJobs = jobs.filter(
    (j) =>
      j.status === 'assigned' ||
      j.status === 'dispatched' ||
      j.status === 'acknowledged' ||
      j.status === 'en_route' ||
      j.status === 'in_progress'
  );

  const filteredElectricians = electricians.filter((t) => {
    if (statusFilter !== 'all' && t.status !== statusFilter) return false;
    if (
      searchQuery.trim() &&
      !t.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !t.employeeId.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !t.skills.some((s) => s.toLowerCase().includes(searchQuery.toLowerCase()))
    ) {
      return false;
    }
    return true;
  });

  const selectedTech = electricians.find((e) => e.id === selectedTechId);
  const selectedJob = jobs.find((j) => j.id === selectedJobId);

  return (
    <div className="space-y-4">
      {/* Page Header with Localization & Simulation Disclaimer */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <h1 className="text-xl font-extrabold text-slate-900 tracking-tight">
              Mysuru Technician Telemetry & Location Map
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Monitoring Only
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span className="font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200/60">
              Simulated Demo Locations • Mysuru Grid Telemetry
            </span>
            <span>• Centered on Mysuru (`12.2958° N, 76.6394° E`)</span>
            <span>• CHESCOM Distribution Feeder Network</span>
          </div>
        </div>

        {/* Quick Fleet Status Counters */}
        <div className="flex items-center gap-2 text-xs">
          <div className="px-3 py-1.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 font-semibold">
            {electricians.filter((e) => e.status === 'available').length} Available
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-sky-50 border border-sky-200 text-sky-800 font-semibold">
            {electricians.filter((e) => e.status === 'en_route').length} En Route
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 font-semibold">
            {electricians.filter((e) => e.status === 'busy').length} On-Site
          </div>
        </div>
      </div>

      {/* Main Map + Side Inspector Split */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Left Column: Map with Embedded Overlays */}
        <div className="lg:col-span-3 space-y-3">
          {/* Controls Bar */}
          <div className="bg-white p-3 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center justify-between gap-2 text-xs">
            {/* Filter Chips */}
            <div className="flex items-center gap-1.5">
              <span className="text-slate-400 font-bold uppercase text-[10px] mr-1">Filter Fleet:</span>
              {(['all', 'available', 'en_route', 'busy'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg font-semibold capitalize transition ${
                    statusFilter === st
                      ? 'bg-blue-600 text-white shadow-xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>

            {/* Disclaimer pill */}
            <div className="flex items-center gap-1 text-[11px] text-slate-500 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
              <Info className="w-3.5 h-3.5 text-blue-500 flex-shrink-0" />
              <span>Simulated GPS pings updated via mock telemetry every 4m</span>
            </div>
          </div>

          {/* Leaflet Map Frame */}
          <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-md">
            <LeafletMap
              electricians={filteredElectricians}
              jobs={activeJobs}
              selectedElectricianId={selectedTechId}
              selectedJobId={selectedJobId}
              onSelectElectrician={(tech) => {
                setSelectedTechId(tech.id);
                setSelectedJobId(null);
              }}
              onSelectJob={(job) => {
                setSelectedJobId(job.id);
                setSelectedTechId(null);
              }}
              height="600px"
            />
          </div>
        </div>

        {/* Right Column: Fleet List & Telemetry Detail Inspector */}
        <div className="space-y-4">
          {/* Selected Item Telemetry Details Card */}
          {selectedTech ? (
            <div className="bg-white p-4 rounded-2xl border-2 border-blue-500 shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                  Technician Telemetry
                </span>
                <span className="text-xs font-bold text-amber-500">★ {selectedTech.rating}</span>
              </div>

              <div className="flex items-center gap-3">
                <img
                  src={selectedTech.avatar}
                  alt={selectedTech.name}
                  className="w-12 h-12 rounded-full object-cover border-2 border-blue-400"
                />
                <div>
                  <h3 className="font-bold text-slate-900 text-sm">{selectedTech.name}</h3>
                  <span className="text-xs font-mono text-slate-500">{selectedTech.employeeId}</span>
                  <span className="block text-[11px] text-emerald-600 font-semibold capitalize">
                    ● {selectedTech.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Telemetry gauges */}
              <div className="grid grid-cols-2 gap-2 text-xs bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="space-y-0.5">
                  <span className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Battery className="w-3 h-3 text-emerald-500" /> Battery
                  </span>
                  <span className="font-bold text-slate-800">89% Charged</span>
                </div>
                <div className="space-y-0.5">
                  <span className="text-[10px] text-slate-400 flex items-center gap-1">
                    <Gauge className="w-3 h-3 text-blue-500" /> Sim Speed
                  </span>
                  <span className="font-bold text-slate-800">
                    {selectedTech.status === 'en_route' ? '28 km/h' : '0 km/h (Stationary)'}
                  </span>
                </div>
                <div className="space-y-0.5 col-span-2 pt-1 border-t border-slate-200">
                  <span className="text-[10px] text-slate-400">GPS Ping Timestamp:</span>
                  <span className="font-mono text-[11px] text-slate-700 block">
                    {formatDateTimeIST(selectedTech.currentLocation.lastUpdated)}
                  </span>
                </div>
              </div>

              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Shift Window:</span>
                  <span className="font-semibold text-slate-800">
                    {selectedTech.shiftHours.start} - {selectedTech.shiftHours.end} IST
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Daily Workload:</span>
                  <span className="font-bold text-slate-900">
                    {selectedTech.currentWorkload}h / {selectedTech.maxDailyHours}h
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Contact:</span>
                  <span className="font-mono text-slate-800">{selectedTech.phone}</span>
                </div>
              </div>

              {/* Certifications */}
              <div>
                <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                  Certifications:
                </span>
                <div className="flex flex-wrap gap-1">
                  {selectedTech.certifications.map((c, i) => (
                    <span
                      key={i}
                      className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200 font-medium"
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setSelectedTechId(null)}
                className="w-full py-1.5 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
              >
                Clear Selection
              </button>
            </div>
          ) : selectedJob ? (
            <div className="bg-white p-4 rounded-2xl border-2 border-indigo-500 shadow-md space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono font-bold text-blue-600">{selectedJob.id}</span>
                <PriorityBadge priority={selectedJob.priority} />
              </div>

              <h3 className="font-bold text-slate-900 text-sm leading-snug">{selectedJob.title}</h3>

              <div className="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-xl border border-slate-200">
                <div className="flex justify-between">
                  <span className="text-slate-400">Status:</span>
                  <StatusBadge status={selectedJob.status} size="sm" />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Customer:</span>
                  <span className="font-semibold text-slate-800">{selectedJob.customerName}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Assigned Tech:</span>
                  <span className="font-bold text-slate-900">{selectedJob.assignedElectricianName || 'Unassigned'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Locality:</span>
                  <span className="font-semibold text-slate-800 truncate max-w-[150px]">{selectedJob.location.address}</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedJobId(null)}
                className="w-full py-1.5 text-xs text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
              >
                Clear Selection
              </button>
            </div>
          ) : null}

          {/* Search & List of Technicians in Mysuru */}
          <div className="bg-white p-4 rounded-2xl border border-slate-200/80 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Mysuru Field Fleet ({filteredElectricians.length})
              </h3>
              <span className="text-[11px] text-blue-600 font-semibold">Click to inspect</span>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search technician name or skill..."
                className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div className="divide-y divide-slate-100 max-h-[380px] overflow-y-auto pr-1">
              {filteredElectricians.map((t) => (
                <div
                  key={t.id}
                  onClick={() => {
                    setSelectedTechId(t.id);
                    setSelectedJobId(null);
                  }}
                  className={`py-2.5 px-2 rounded-xl transition cursor-pointer flex items-center justify-between gap-2 ${
                    selectedTechId === t.id
                      ? 'bg-blue-50/80 border border-blue-200'
                      : 'hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <img
                      src={t.avatar}
                      alt={t.name}
                      className="w-8 h-8 rounded-full object-cover border border-slate-200 flex-shrink-0"
                    />
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-slate-900 truncate">{t.name}</p>
                      <p className="text-[10px] text-slate-500 truncate">
                        {t.employeeId} • {t.skills[0]}
                      </p>
                    </div>
                  </div>

                  <div className="text-right flex-shrink-0">
                    <span
                      className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-bold capitalize ${
                        t.status === 'available'
                          ? 'bg-emerald-50 text-emerald-700'
                          : t.status === 'en_route'
                          ? 'bg-sky-50 text-sky-700'
                          : 'bg-amber-50 text-amber-700'
                      }`}
                    >
                      {t.status.replace('_', ' ')}
                    </span>
                    <span className="block text-[10px] text-slate-400 mt-0.5">
                      {t.currentWorkload}h / 8.5h
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

