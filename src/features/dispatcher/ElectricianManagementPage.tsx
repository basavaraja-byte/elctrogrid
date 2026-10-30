import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Electrician } from '../../types';
import { DataTable, Column } from '../../components/common/DataTable';
import { Modal } from '../../components/common/Modal';
import {
  Users,
  HardHat,
  MapPin,
  Clock,
  ShieldCheck,
  Star,
  CheckCircle,
  AlertCircle,
  Eye,
  Wrench,
  Radio,
} from 'lucide-react';

export const ElectricianManagementPage: React.FC = () => {
  const { electricians, jobs } = useApp();
  const [selectedTech, setSelectedTech] = useState<Electrician | null>(null);

  const columns: Column<Electrician>[] = [
    {
      header: 'Electrician',
      cell: (e) => (
        <div className="flex items-center gap-3">
          <img
            src={e.avatar}
            alt={e.name}
            className="w-10 h-10 rounded-full object-cover border border-slate-200"
          />
          <div>
            <span className="font-bold text-slate-900 block">{e.name}</span>
            <span className="text-[11px] text-slate-500 font-mono">{e.employeeId} • {e.phone}</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Status',
      cell: (e) => {
        const statusColors = {
          available: 'bg-emerald-100 text-emerald-800 border-emerald-200',
          busy: 'bg-amber-100 text-amber-800 border-amber-200',
          en_route: 'bg-sky-100 text-sky-800 border-sky-200',
          off_duty: 'bg-slate-100 text-slate-700 border-slate-200',
          leave: 'bg-rose-100 text-rose-800 border-rose-200',
          on_break: 'bg-purple-100 text-purple-800 border-purple-200',
        }[e.status] || 'bg-slate-100 text-slate-700 border-slate-200';

        return (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize border ${statusColors}`}>
            <span className="w-1.5 h-1.5 rounded-full mr-1.5 bg-current"></span>
            {e.status.replace('_', ' ')}
          </span>
        );
      },
    },
    {
      header: 'Shift & Hours',
      cell: (e) => (
        <div className="text-xs text-slate-600">
          <span className="font-semibold block capitalize">{e.shift} Shift</span>
          <span className="text-[11px] text-slate-500">{e.shiftHours.start} - {e.shiftHours.end}</span>
        </div>
      ),
    },
    {
      header: 'Daily Workload',
      cell: (e) => {
        const ratio = Math.min(100, Math.round((e.currentWorkload / e.maxDailyHours) * 100));
        const barColor = ratio > 85 ? 'bg-rose-500' : ratio > 60 ? 'bg-amber-500' : 'bg-emerald-500';

        return (
          <div className="w-32">
            <div className="flex justify-between text-[11px] font-semibold text-slate-700 mb-1">
              <span>{e.currentWorkload}h</span>
              <span className="text-slate-400">max {e.maxDailyHours}h</span>
            </div>
            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
              <div className={`h-full ${barColor}`} style={{ width: `${ratio}%` }} />
            </div>
          </div>
        );
      },
    },
    {
      header: 'Primary Skills',
      cell: (e) => (
        <div className="flex flex-wrap gap-1 max-w-xs">
          {e.skills.slice(0, 2).map((s, idx) => (
            <span key={idx} className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-medium truncate">
              {s}
            </span>
          ))}
          {e.skills.length > 2 && (
            <span className="text-[10px] text-slate-400 font-semibold">
              +{e.skills.length - 2} more
            </span>
          )}
        </div>
      ),
    },
    {
      header: 'Rating',
      cell: (e) => (
        <div className="flex items-center gap-1 text-xs font-bold text-slate-700">
          <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
          <span>{e.rating}</span>
        </div>
      ),
    },
    {
      header: 'Actions',
      cell: (e) => (
        <button
          onClick={(ev) => {
            ev.stopPropagation();
            setSelectedTech(e);
          }}
          className="px-2.5 py-1 text-xs font-semibold rounded bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center gap-1"
        >
          <Eye className="w-3.5 h-3.5" />
          Profile
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Certified Electrician Fleet
          </h1>
          <p className="text-sm text-slate-500">
            Real-time workforce availability, specialized certifications, and workload balance
          </p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={electricians}
        searchPlaceholder="Search electrician name, skills, ID, or certifications..."
        searchFilter={(item, query) =>
          item.name.toLowerCase().includes(query) ||
          item.employeeId.toLowerCase().includes(query) ||
          item.skills.some((s) => s.toLowerCase().includes(query)) ||
          item.certifications.some((c) => c.toLowerCase().includes(query))
        }
        filterOptions={[
          {
            label: 'Status',
            key: 'status',
            options: [
              { label: 'Available', value: 'available' },
              { label: 'Busy', value: 'busy' },
              { label: 'En Route', value: 'en_route' },
              { label: 'Off Duty', value: 'off_duty' },
            ],
            filterFn: (item, val) => item.status === val,
          },
          {
            label: 'Shift',
            key: 'shift',
            options: [
              { label: 'Morning', value: 'morning' },
              { label: 'Afternoon', value: 'afternoon' },
              { label: 'Flexible', value: 'flexible' },
              { label: 'Night', value: 'night' },
            ],
            filterFn: (item, val) => item.shift === val,
          },
        ]}
        onRowClick={(tech) => setSelectedTech(tech)}
      />

      {/* Technician Profile Modal */}
      {selectedTech && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedTech(null)}
          title={`Electrician Profile • ${selectedTech.name}`}
          subtitle={`${selectedTech.employeeId} • Master Field Technician`}
          maxWidth="2xl"
        >
          <div className="space-y-5">
            {/* Top Identity Card */}
            <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
              <img
                src={selectedTech.avatar}
                alt={selectedTech.name}
                className="w-16 h-16 rounded-full object-cover border-2 border-blue-500 shadow-md"
              />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-900">{selectedTech.name}</h3>
                  <span className="text-xs font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">
                    ★ {selectedTech.rating} Rating ({selectedTech.jobsCompletedTotal} jobs completed)
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {selectedTech.email} • {selectedTech.phone}
                </p>
                <div className="mt-2 flex items-center gap-2 text-xs">
                  <span className="font-semibold text-slate-700">Status:</span>
                  <span className="capitalize font-bold text-slate-900">
                    {selectedTech.status.replace('_', ' ')}
                  </span>
                  <span className="text-slate-400">|</span>
                  <span className="font-semibold text-slate-700">Workload:</span>
                  <span>{selectedTech.currentWorkload}h / {selectedTech.maxDailyHours}h</span>
                </div>
              </div>
            </div>

            {/* Certifications & Skills */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white p-4 rounded-xl border border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Official Licenses & Certifications
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-700">
                  {selectedTech.certifications.map((c, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="bg-white p-4 rounded-xl border border-slate-200">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2 flex items-center gap-1.5">
                  <Wrench className="w-4 h-4 text-blue-600" />
                  Equipped Tools & Fleet Gear
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-700">
                  {selectedTech.equipment.map((eq, i) => (
                    <li key={i} className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                      <span>{eq}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* All Technical Skills */}
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Verified Technical Proficiencies
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {selectedTech.skills.map((s, i) => (
                  <span
                    key={i}
                    className="text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200 px-2.5 py-1 rounded-lg"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Simulated GPS Location */}
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between text-xs text-slate-600">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-emerald-500 animate-pulse" />
                <span>
                  <b>Simulated GPS:</b> {selectedTech.currentLocation.lat.toFixed(4)},{' '}
                  {selectedTech.currentLocation.lng.toFixed(4)}
                </span>
              </div>
              <span className="text-[11px] text-slate-400">
                Last ping: {new Date(selectedTech.currentLocation.lastUpdated).toLocaleTimeString()}
              </span>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

