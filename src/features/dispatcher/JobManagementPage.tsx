import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { DataTable, Column } from '../../components/common/DataTable';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Job, ProblemCategory, JobPriority } from '../../types';
import { ScheduleOptimizeModal } from './ScheduleOptimizeModal';
import { Modal } from '../../components/common/Modal';
import {
  Briefcase,
  Sparkles,
  MapPin,
  Clock,
  HardHat,
  Plus,
  Edit,
  History,
  AlertTriangle,
} from 'lucide-react';

export const JobManagementPage: React.FC = () => {
  const { user } = useAuth();
  const { jobs, electricians, refreshData } = useApp();

  const [selectedJobForOptimize, setSelectedJobForOptimize] = useState<Job | null>(null);
  const [selectedJobForHistory, setSelectedJobForHistory] = useState<Job | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Form states for manual job ticket creation
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newCategory, setNewCategory] = useState<ProblemCategory>('panel_breaker');
  const [newPriority, setNewPriority] = useState<JobPriority>('medium');
  const [newCustomerName, setNewCustomerName] = useState('Metro Commercial Account');
  const [newAddress, setNewAddress] = useState('701 Brazos St, Suite 500');
  const [newDuration, setNewDuration] = useState(2.0);
  const [newSkills, setNewSkills] = useState('Panel & Breaker Upgrades');

  const handleCreateManualJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    // Use mockStore through api
    const newJob = await api.createServiceRequest(
      {
        customerId: 'usr-cust-com-1',
        customerName: newCustomerName,
        customerType: 'commercial',
        customerPhone: '+1 (512) 555-0301',
        customerEmail: 'facilities@metrocorp.com',
        title: newTitle,
        description: newDesc,
        category: newCategory,
        priority: newPriority,
        location: {
          lat: 30.2672 + (Math.random() - 0.5) * 0.04,
          lng: -97.7431 + (Math.random() - 0.5) * 0.04,
          address: newAddress,
          city: 'Austin',
          postalCode: '78701',
        },
        preferredDate: new Date().toISOString().split('T')[0],
        preferredTimeWindow: '08:00 - 12:00',
        attachments: [],
      },
      user
    );

    // Validate directly to create job
    await api.validateRequest(newJob.id, 'Manually created operational ticket', user);
    refreshData();
    setIsCreateModalOpen(false);
    setNewTitle('');
    setNewDesc('');
  };

  const columns: Column<Job>[] = [
    {
      header: 'Job ID',
      accessorKey: 'id',
      className: 'font-mono font-bold text-blue-600',
    },
    {
      header: 'Title & Category',
      cell: (j) => (
        <div>
          <span className="font-bold text-slate-900 block truncate max-w-xs">{j.title}</span>
          <span className="text-[11px] text-slate-500 capitalize">{j.category.replace(/_/g, ' ')} • Req: {j.requestId}</span>
        </div>
      ),
    },
    {
      header: 'Assigned Electrician',
      cell: (j) => (
        <div>
          {j.assignedElectricianName ? (
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
              <HardHat className="w-3.5 h-3.5 text-blue-600" />
              <span>{j.assignedElectricianName}</span>
            </div>
          ) : (
            <span className="text-xs font-bold text-amber-600 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
              Unassigned
            </span>
          )}
        </div>
      ),
    },
    {
      header: 'Est. Duration',
      cell: (j) => (
        <span className="text-xs text-slate-600 font-medium">
          ~{j.estimatedDurationHours} hours
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
      header: 'Scheduling',
      cell: (j) => (
        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => setSelectedJobForOptimize(j)}
            className="px-2.5 py-1 bg-blue-50 hover:bg-blue-600 text-blue-700 hover:text-white rounded-lg text-xs font-bold flex items-center gap-1 transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {j.assignedElectricianId ? 'Re-Optimize' : 'Optimize'}
          </button>
          <button
            onClick={() => setSelectedJobForHistory(j)}
            title="View Audit & Timeline"
            className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
          >
            <History className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Operational Job Management
          </h1>
          <p className="text-sm text-slate-500">
            Monitor, edit, and assign field jobs using constraint-based scheduling
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 self-start sm:self-auto transition"
        >
          <Plus className="w-4 h-4" />
          <span>Create Operational Job</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={jobs}
        searchPlaceholder="Search job ID, title, category or assigned technician..."
        searchFilter={(item, query) =>
          item.id.toLowerCase().includes(query) ||
          item.title.toLowerCase().includes(query) ||
          (item.assignedElectricianName && item.assignedElectricianName.toLowerCase().includes(query)) ||
          item.category.toLowerCase().includes(query)
        }
        filterOptions={[
          {
            label: 'Status',
            key: 'status',
            options: [
              { label: 'Validated', value: 'validated' },
              { label: 'Assigned', value: 'assigned' },
              { label: 'Dispatched', value: 'dispatched' },
              { label: 'In Progress', value: 'in_progress' },
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
        onRowClick={(row) => setSelectedJobForOptimize(row)}
      />

      {/* Manual Job Creation Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Operational Job Ticket"
        subtitle="Direct dispatcher entry without preliminary customer ticket"
        maxWidth="xl"
      >
        <form onSubmit={handleCreateManualJob} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Job Title *
            </label>
            <input
              type="text"
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. 480V Industrial Switchgear Annual Service"
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as ProblemCategory)}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
              >
                <option value="power_outage">Power Outage</option>
                <option value="equipment_failure">Equipment Failure</option>
                <option value="wiring_fault">Wiring Fault</option>
                <option value="panel_breaker">Panel & Breaker</option>
                <option value="preventive_maintenance">Preventive Maintenance</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Priority
              </label>
              <select
                value={newPriority}
                onChange={(e) => setNewPriority(e.target.value as JobPriority)}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="emergency">Emergency</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Estimated Hours
              </label>
              <input
                type="number"
                step="0.5"
                min="0.5"
                max="12"
                value={newDuration}
                onChange={(e) => setNewDuration(Number(e.target.value))}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Customer / Location
              </label>
              <input
                type="text"
                value={newCustomerName}
                onChange={(e) => setNewCustomerName(e.target.value)}
                className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Service Address
            </label>
            <input
              type="text"
              value={newAddress}
              onChange={(e) => setNewAddress(e.target.value)}
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Scope of Work
            </label>
            <textarea
              rows={2}
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="Operational details, safety lock-out procedures..."
              className="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="px-4 py-2 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
            >
              Create Job Ticket
            </button>
          </div>
        </form>
      </Modal>

      {/* Intelligent Scheduling Optimizer Modal */}
      <ScheduleOptimizeModal
        job={selectedJobForOptimize}
        isOpen={!!selectedJobForOptimize}
        onClose={() => setSelectedJobForOptimize(null)}
      />

      {/* Job Timeline & History Modal */}
      {selectedJobForHistory && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedJobForHistory(null)}
          title={`Job Lifecycle History • ${selectedJobForHistory.id}`}
          subtitle={selectedJobForHistory.title}
          maxWidth="lg"
        >
          <div className="space-y-4">
            <div className="pl-6 relative before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200 space-y-3">
              {selectedJobForHistory.timeline.map((ev, i) => (
                <div key={i} className="relative text-xs">
                  <span className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                  <div className="flex items-center gap-2">
                    <StatusBadge status={ev.status} size="sm" />
                    <span className="text-slate-400">
                      {new Date(ev.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                    <span className="font-semibold text-slate-700">by {ev.updatedBy}</span>
                  </div>
                  {ev.notes && <p className="text-slate-600 mt-1 pl-1 bg-slate-50 p-2 rounded">{ev.notes}</p>}
                </div>
              ))}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

