import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api/apiClient';
import { Job, JobStatus, JobPriority } from '../../types';
import { DataTable, Column } from '../../components/common/DataTable';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Modal } from '../../components/common/Modal';
import { formatDateIST, formatTimeIST, formatDateTimeIST } from '../../utils/formatters';
import {
  Briefcase,
  Search,
  Filter,
  Eye,
  MapPin,
  Calendar,
  Clock,
  HardHat,
  User,
  ShieldCheck,
  AlertTriangle,
  Info,
  UserCheck,
  Zap,
} from 'lucide-react';

export const SupervisorJobsPage: React.FC = () => {
  const { user } = useAuth();
  const { jobs, electricians, refreshData } = useApp();

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [assignModalJob, setAssignModalJob] = useState<Job | null>(null);
  const [selectedElectricianId, setSelectedElectricianId] = useState<string>('');
  const [isAssigning, setIsAssigning] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const handleAssignSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignModalJob || !selectedElectricianId || !user) return;
    setIsAssigning(true);
    try {
      await api.assignAndDispatchJob(
        assignModalJob.id,
        selectedElectricianId,
        '10:00 AM IST',
        '12:00 PM IST',
        'manual',
        user
      );
      refreshData();
      setAssignModalJob(null);
      setSelectedElectricianId('');
    } catch (err: any) {
      alert(err.message || 'Failed to assign electrician');
    } finally {
      setIsAssigning(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    if (statusFilter !== 'all' && job.status !== statusFilter) return false;
    if (priorityFilter !== 'all' && job.priority !== priorityFilter) return false;
    if (
      searchQuery.trim() &&
      !job.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !job.id.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !job.customerName.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !job.location.address.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !(job.assignedElectricianName && job.assignedElectricianName.toLowerCase().includes(searchQuery.toLowerCase()))
    ) {
      return false;
    }
    return true;
  });

  const columns: Column<Job>[] = [
    {
      header: 'Job ID',
      accessorKey: 'id',
      className: 'font-mono font-bold text-blue-600 whitespace-nowrap',
    },
    {
      header: 'Problem Title & Locality',
      cell: (job) => (
        <div className="max-w-xs">
          <p className="font-bold text-slate-900 truncate">{job.title}</p>
          <div className="flex items-center gap-1 text-[11px] text-slate-500 mt-0.5">
            <MapPin className="w-3 h-3 text-slate-400 flex-shrink-0" />
            <span className="truncate">{job.location.address}</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Customer',
      cell: (job) => (
        <div className="text-xs">
          <span className="font-semibold text-slate-800 block">{job.customerName}</span>
          <span className="text-[11px] text-slate-500">{job.customerPhone}</span>
        </div>
      ),
    },
    {
      header: 'Assigned Technician',
      cell: (job) => (
        <div className="text-xs">
          {job.assignedElectricianName ? (
            <div className="flex items-center gap-1.5 font-semibold text-slate-800">
              <HardHat className="w-3.5 h-3.5 text-blue-600 flex-shrink-0" />
              <span>{job.assignedElectricianName}</span>
            </div>
          ) : (
            <span className="text-slate-400 italic">Unassigned (Awaiting Intake)</span>
          )}
        </div>
      ),
    },
    {
      header: 'Priority',
      cell: (job) => <PriorityBadge priority={job.priority} />,
    },
    {
      header: 'Field Status',
      cell: (job) => <StatusBadge status={job.status} />,
    },
    {
      header: 'Scheduled Window',
      cell: (job) => (
        <div className="text-xs text-slate-600">
          <span className="block font-medium">{job.preferredTimeWindow}</span>
          <span className="text-[11px] text-slate-400">
            {formatDateIST(job.scheduledStartTime || job.createdAt)}
          </span>
        </div>
      ),
    },
    {
      header: 'Actions',
      cell: (job) => (
        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => {
              setAssignModalJob(job);
              setSelectedElectricianId(job.assignedElectricianId || '');
            }}
            className="px-2.5 py-1 text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition flex items-center gap-1 cursor-pointer"
            title="Assign or Reassign Electrician"
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>{job.assignedElectricianId ? 'Reassign' : 'Assign'}</span>
          </button>
          <button
            onClick={() => setSelectedJob(job)}
            className="p-1.5 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition cursor-pointer"
            title="View Job Details"
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Job & Assignment Monitoring
            </h1>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800 uppercase tracking-wider">
              Monitoring Only
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Real-time operational observability across all 16 field lifecycle stages in Mysuru
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-xs font-semibold text-slate-700">
            Total Jobs: {jobs.length}
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-800">
            Active: {jobs.filter((j) => j.status === 'in_progress' || j.status === 'en_route').length}
          </div>
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
              placeholder="Search by job ID, title, customer, technician, or Mysuru locality..."
              className="w-full pl-9 pr-3.5 py-2 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Field Statuses</option>
              <option value="submitted">Submitted</option>
              <option value="assigned">Assigned</option>
              <option value="dispatched">Dispatched</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="en_route">En Route</option>
              <option value="in_progress">In Progress</option>
              <option value="on_hold">On Hold</option>
              <option value="completed">Completed</option>
              <option value="closed">Closed</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Priorities</option>
              <option value="emergency">🚨 Emergency</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <DataTable
        columns={columns}
        data={filteredJobs}
        onRowClick={(job) => setSelectedJob(job)}
        pageSize={12}
        emptyMessage="No electrical jobs matching the specified filter criteria."
      />

      {/* Read-Only Job Details Modal */}
      {selectedJob && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedJob(null)}
          title={`Job Supervision Details • ${selectedJob.id}`}
          subtitle="Read-only field lifecycle telemetry and automated assignment records"
          maxWidth="4xl"
        >
          <div className="space-y-4">
            {/* Header info */}
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-slate-600">{selectedJob.id}</span>
                  <PriorityBadge priority={selectedJob.priority} />
                  <StatusBadge status={selectedJob.status} />
                </div>
                <span className="text-xs text-slate-500">
                  Created: {formatDateTimeIST(selectedJob.createdAt)}
                </span>
              </div>
              <h3 className="text-base font-bold text-slate-900 mt-2">{selectedJob.title}</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed bg-white p-3 rounded-lg border border-slate-200">
                {selectedJob.description}
              </p>
            </div>

            {/* Customer & Location */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold uppercase text-slate-400 block">
                  Customer & Site Information
                </span>
                <p className="font-bold text-slate-900">{selectedJob.customerName}</p>
                <p className="text-slate-600">{selectedJob.location.address}, {selectedJob.location.city}</p>
                <p className="text-slate-600">Phone: {selectedJob.customerPhone}</p>
              </div>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold uppercase text-slate-400 block">
                  Assigned Field Electrician
                </span>
                <p className="font-bold text-slate-900">
                  {selectedJob.assignedElectricianName || 'Automated Intake in Progress'}
                </p>
                <p className="text-slate-600">Target Window: {selectedJob.preferredTimeWindow}</p>
                <p className="text-slate-600">Estimated Duration: ~{selectedJob.estimatedDurationHours} hours</p>
              </div>
            </div>

            {/* Required Safety Gear & Skills */}
            <div className="p-3 bg-blue-50/50 rounded-xl border border-blue-200 text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-900 block mb-1.5">
                Technical Match Criteria:
              </span>
              <div className="flex flex-wrap gap-1.5">
                {selectedJob.requiredSkills.map((s, i) => (
                  <span key={i} className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-medium text-[11px]">
                    ⚡ {s}
                  </span>
                ))}
                {selectedJob.requiredEquipment.map((eq, i) => (
                  <span key={i} className="bg-white text-slate-700 border border-blue-200 px-2 py-0.5 rounded text-[11px]">
                    🛡️ {eq}
                  </span>
                ))}
              </div>
            </div>

            {/* Lifecycle Timeline */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
                Operational Lifecycle Events
              </span>
              <div className="relative pl-6 space-y-3 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                {selectedJob.timeline && selectedJob.timeline.length > 0 ? (
                  selectedJob.timeline.map((ev, idx) => (
                    <div key={idx} className="relative text-xs">
                      <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                      <div className="flex items-center gap-2">
                        <StatusBadge status={ev.status} size="sm" />
                        <span className="text-slate-400">{formatDateTimeIST(ev.timestamp)}</span>
                      </div>
                      <p className="text-slate-600 mt-0.5">{ev.notes}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-400">No timeline events recorded.</p>
                )}
              </div>
            </div>

            {/* Completion Report if completed */}
            {selectedJob.completionReport && (
              <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-xs space-y-2">
                <span className="text-[10px] font-bold uppercase text-emerald-800 block">
                  Field Completion Sign-Off
                </span>
                <p><strong>Fault Identified:</strong> {selectedJob.completionReport.faultIdentified}</p>
                <p><strong>Work Performed:</strong> {selectedJob.completionReport.workPerformed}</p>
                <p><strong>Signed by:</strong> {selectedJob.completionReport.signedOffByElectrician}</p>
              </div>
            )}

            <div className="pt-2 flex items-center justify-between border-t border-slate-100">
              <button
                type="button"
                onClick={() => {
                  setAssignModalJob(selectedJob);
                  setSelectedElectricianId(selectedJob.assignedElectricianId || '');
                }}
                className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition flex items-center gap-1.5 shadow-xs"
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>{selectedJob.assignedElectricianId ? 'Reassign Electrician' : 'Assign Electrician'}</span>
              </button>
              <button
                onClick={() => setSelectedJob(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition"
              >
                Close Supervision Viewer
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Manual Electrician Assignment Modal */}
      {assignModalJob && (
        <Modal
          isOpen={true}
          onClose={() => setAssignModalJob(null)}
          title={`Assign Electrician • ${assignModalJob.id}`}
          subtitle={`Assign an electrician to: ${assignModalJob.title}`}
          maxWidth="2xl"
        >
          <form onSubmit={handleAssignSubmit} className="space-y-4">
            <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-mono font-bold text-blue-700">{assignModalJob.id}</span>
                <PriorityBadge priority={assignModalJob.priority} />
              </div>
              <p className="font-bold text-slate-800">{assignModalJob.title}</p>
              <p className="text-slate-600 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                {assignModalJob.location.address}
              </p>
              {assignModalJob.assignedElectricianName && (
                <p className="text-blue-700 font-semibold pt-1">
                  Currently assigned to: {assignModalJob.assignedElectricianName}
                </p>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                Select Electrician
              </label>
              <select
                value={selectedElectricianId}
                onChange={(e) => setSelectedElectricianId(e.target.value)}
                required
                className="w-full px-3 py-2.5 text-xs border border-slate-200 rounded-xl bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="">-- Choose an Electrician --</option>
                {electricians
                  .filter((e) => e.accountStatus === 'active' || !e.accountStatus)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name} ({e.employeeId}) • Status: {e.status.replace('_', ' ')} • Workload: {e.currentWorkload}h
                    </option>
                  ))}
              </select>
            </div>

            <div className="p-3 bg-blue-50 rounded-xl border border-blue-200 text-xs text-blue-800">
              <span className="font-bold block mb-0.5">Instant Dashboard Synchronization</span>
              Assigning this job will immediately update the selected electrician's dashboard, the customer's portal, and the supervisor tracking monitor across all open tabs.
            </div>

            <div className="pt-2 flex items-center justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setAssignModalJob(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-xl transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!selectedElectricianId || isAssigning}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold rounded-xl shadow-md transition flex items-center gap-1.5"
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>{isAssigning ? 'Assigning...' : 'Confirm Assignment'}</span>
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
