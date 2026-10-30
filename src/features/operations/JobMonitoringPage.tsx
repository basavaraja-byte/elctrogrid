import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { DataTable, Column } from '../../components/common/DataTable';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Job, JobStatus } from '../../types';
import { Modal } from '../../components/common/Modal';
import {
  Compass,
  AlertTriangle,
  HardHat,
  MapPin,
  Clock,
  Eye,
  ShieldAlert,
} from 'lucide-react';
import { EscalateModal } from './EscalateModal';

export const JobMonitoringPage: React.FC = () => {
  const { jobs } = useApp();

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [escalatingJobId, setEscalatingJobId] = useState<string | null>(null);

  const columns: Column<Job>[] = [
    {
      header: 'Job ID',
      accessorKey: 'id',
      className: 'font-mono font-bold text-blue-600',
    },
    {
      header: 'Problem Title',
      cell: (j) => (
        <div>
          <span className="font-bold text-slate-900 block truncate max-w-xs">{j.title}</span>
          <span className="text-[11px] text-slate-500 capitalize">{j.category.replace(/_/g, ' ')} • Customer: {j.customerName}</span>
        </div>
      ),
    },
    {
      header: 'Technician',
      cell: (j) => (
        <span className="text-xs font-semibold text-slate-800">
          {j.assignedElectricianName ? (
            <span className="flex items-center gap-1.5">
              <HardHat className="w-3.5 h-3.5 text-blue-600" />
              {j.assignedElectricianName}
            </span>
          ) : (
            <span className="text-amber-600 font-bold">Unassigned</span>
          )}
        </span>
      ),
    },
    {
      header: 'Priority',
      cell: (j) => <PriorityBadge priority={j.priority} />,
    },
    {
      header: 'Status',
      cell: (j) => <StatusBadge status={j.status} />,
    },
    {
      header: 'SLA Risk',
      cell: (j) => {
        if (j.isOverdue || j.slaRisk === 'breached') {
          return (
            <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-red-100 text-red-800 border border-red-200">
              Breached
            </span>
          );
        }
        if (j.slaRisk === 'warning') {
          return (
            <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-amber-100 text-amber-800 border border-amber-200">
              At Risk
            </span>
          );
        }
        return (
          <span className="text-[11px] text-emerald-700 font-semibold">
            Nominal
          </span>
        );
      },
    },
    {
      header: 'Actions',
      cell: (j) => (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => setSelectedJob(j)}
            className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
            title="Inspect"
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={() => setEscalatingJobId(j.id)}
            className="p-1 rounded text-rose-500 hover:text-rose-700 hover:bg-rose-50"
            title="Escalate"
          >
            <ShieldAlert className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Field Job Monitoring
        </h1>
        <p className="text-sm text-slate-500">
          Supervise active field lifecycle tickets, track SLA milestones, and intervene on critical exceptions
        </p>
      </div>

      <DataTable
        columns={columns}
        data={jobs}
        searchPlaceholder="Search job ID, title, customer, or electrician..."
        searchFilter={(item, query) =>
          Boolean(
            item.id.toLowerCase().includes(query) ||
            item.title.toLowerCase().includes(query) ||
            item.customerName.toLowerCase().includes(query) ||
            (item.assignedElectricianName && item.assignedElectricianName.toLowerCase().includes(query))
          )
        }
        filterOptions={[
          {
            label: 'Job Status',
            key: 'status',
            options: [
              { label: 'Validated', value: 'validated' },
              { label: 'Assigned', value: 'assigned' },
              { label: 'Dispatched', value: 'dispatched' },
              { label: 'En Route', value: 'en_route' },
              { label: 'In Progress', value: 'in_progress' },
              { label: 'On Hold', value: 'on_hold' },
              { label: 'Completed', value: 'completed' },
            ],
            filterFn: (item, val) => item.status === val,
          },
          {
            label: 'Priority',
            key: 'priority',
            options: [
              { label: 'Emergency', value: 'emergency' },
              { label: 'High', value: 'high' },
              { label: 'Medium', value: 'medium' },
              { label: 'Low', value: 'low' },
            ],
            filterFn: (item, val) => item.priority === val,
          },
        ]}
        onRowClick={(j) => setSelectedJob(j)}
      />

      {/* Inspect Dialog */}
      {selectedJob && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedJob(null)}
          title={`Job Inspection • ${selectedJob.id}`}
          subtitle={selectedJob.title}
          maxWidth="lg"
        >
          <div className="space-y-3 text-xs">
            <div className="flex items-center gap-2">
              <PriorityBadge priority={selectedJob.priority} />
              <StatusBadge status={selectedJob.status} />
            </div>
            <p className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-slate-700">
              {selectedJob.description}
            </p>
            <div className="grid grid-cols-2 gap-2 text-slate-600">
              <div><b>Customer:</b> {selectedJob.customerName}</div>
              <div><b>Phone:</b> {selectedJob.customerPhone}</div>
              <div><b>Address:</b> {selectedJob.location.address}</div>
              <div><b>Electrician:</b> {selectedJob.assignedElectricianName || 'Unassigned'}</div>
              <div><b>Window:</b> {selectedJob.preferredTimeWindow}</div>
              <div><b>Duration:</b> ~{selectedJob.estimatedDurationHours}h</div>
            </div>
          </div>
        </Modal>
      )}

      {/* Escalate Dialog */}
      {escalatingJobId && (
        <EscalateModal
          isOpen={true}
          jobId={escalatingJobId}
          onClose={() => setEscalatingJobId(null)}
        />
      )}
    </div>
  );
};
