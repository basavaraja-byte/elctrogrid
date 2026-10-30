import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { KPICard } from '../../components/common/KPICard';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { CreateRequestModal } from './CreateRequestModal';
import { RequestDetailPage } from './RequestDetailPage';
import { ServiceRequest } from '../../types';
import { formatDateIST } from '../../utils/formatters';
import {
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Plus,
  ArrowRight,
  HardHat,
  MapPin,
  Calendar,
  Sparkles,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const CustomerDashboard: React.FC = () => {
  const { user } = useAuth();
  const { serviceRequests, jobs, notifications } = useApp();
  const navigate = useNavigate();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedRequestId, setSelectedRequestId] = useState<string | null>(null);

  // Filter requests belonging to this customer
  const customerRequests = serviceRequests.filter(
    (r) => r.customerId === user?.id || (user?.id === 'usr-cust-ind-1' && r.customerId.includes('ind-1'))
  );

  const totalCount = customerRequests.length;
  const activeCount = customerRequests.filter(
    (r) =>
      r.status === 'validated' ||
      r.status === 'assigned' ||
      r.status === 'dispatched' ||
      r.status === 'acknowledged' ||
      r.status === 'en_route' ||
      r.status === 'in_progress'
  ).length;
  const completedCount = customerRequests.filter(
    (r) => r.status === 'completed' || r.status === 'customer_confirmed' || r.status === 'closed'
  ).length;
  const pendingCount = customerRequests.filter(
    (r) => r.status === 'submitted' || r.status === 'under_review'
  ).length;

  // Find most urgent active request
  const activeRequest = customerRequests.find(
    (r) => r.status === 'en_route' || r.status === 'in_progress' || r.status === 'dispatched'
  );

  const activeJob = activeRequest?.associatedJobId
    ? jobs.find((j) => j.id === activeRequest.associatedJobId)
    : undefined;

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-blue-900 via-indigo-900 to-slate-900 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-500/20 to-transparent pointer-events-none" />

        <div className="relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-blue-200 border border-white/10 mb-3">
              <Sparkles className="w-3.5 h-3.5 text-blue-300" />
              <span>Customer Self-Service Hub</span>
              <span className="capitalize">• {user?.customerCategory || 'Individual'}</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Welcome back, {user?.name}
            </h1>
            <p className="text-sm text-slate-300 mt-1 max-w-xl leading-relaxed">
              {user?.companyName
                ? `Managing critical power infrastructure for ${user.companyName}.`
                : 'Manage residential electrical repairs, monitor technician dispatch, and verify safety reports.'}
            </p>
          </div>

          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-500 hover:bg-blue-600 text-white font-bold text-sm shadow-lg shadow-blue-500/30 transition self-start sm:self-center"
          >
            <Plus className="w-4 h-4" />
            <span>Submit New Complaint</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Requests"
          value={totalCount}
          icon={FileText}
          description="Lifetime service complaints"
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KPICard
          title="Active Field Jobs"
          value={activeCount}
          icon={HardHat}
          description="In dispatch or on-site"
          trend="up"
          change={`${activeCount} active`}
          iconColor="text-amber-600"
          bgColor="bg-amber-50"
        />
        <KPICard
          title="Completed Jobs"
          value={completedCount}
          icon={CheckCircle2}
          description="Repairs verified & signed"
          iconColor="text-emerald-600"
          bgColor="bg-emerald-50"
        />
        <KPICard
          title="Pending Review"
          value={pendingCount}
          icon={Clock}
          description="Awaiting dispatch triage"
          iconColor="text-indigo-600"
          bgColor="bg-indigo-50"
        />
      </div>

      {/* Active Service Highlight Card if en_route or in_progress */}
      {activeRequest && activeJob && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50/50 rounded-xl border border-blue-200 p-5 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-600 animate-ping" />
              <h3 className="font-bold text-slate-900 text-sm">
                Active Job in Progress: {activeJob.id}
              </h3>
            </div>
            <StatusBadge status={activeJob.status} />
          </div>

          <p className="text-xs text-slate-700 font-medium mb-3">{activeJob.title}</p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-white/80 p-3 rounded-lg border border-blue-100">
            <div>
              <span className="text-slate-400 block text-[11px]">Assigned Electrician</span>
              <span className="font-bold text-slate-800">
                {activeJob.assignedElectricianName || 'Pending Final Staging'}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Service Location</span>
              <span className="font-semibold text-slate-700 truncate block">
                {activeJob.location.address}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Scheduled Window</span>
              <span className="font-semibold text-slate-700">
                {activeJob.preferredTimeWindow}
              </span>
            </div>
          </div>

          <div className="mt-3 flex justify-end">
            <button
              onClick={() => setSelectedRequestId(activeRequest.id)}
              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              <span>Track Live Progress</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Recent Service Requests Section */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/40">
          <div>
            <h3 className="text-base font-bold text-slate-900">Recent Service Requests</h3>
            <p className="text-xs text-slate-500">Live operational status from Central Dispatch</p>
          </div>
          <button
            onClick={() => navigate('/customer/requests')}
            className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>View All ({customerRequests.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-slate-100 overflow-x-auto">
          {customerRequests.slice(0, 5).map((req) => (
            <div
              key={req.id}
              onClick={() => setSelectedRequestId(req.id)}
              className="p-4 sm:px-6 hover:bg-slate-50 transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-slate-500">{req.id}</span>
                  <PriorityBadge priority={req.priority} />
                  <StatusBadge status={req.status} />
                </div>
                <h4 className="text-sm font-bold text-slate-900">{req.title}</h4>
                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" />
                    {req.location.address}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {formatDateIST(req.submittedAt)}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="px-3 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-white transition"
                >
                  View Details & History
                </button>
              </div>
            </div>
          ))}

          {customerRequests.length === 0 && (
            <div className="p-12 text-center text-slate-400">
              <p className="text-sm">No service requests found for this customer account.</p>
              <button
                onClick={() => setIsCreateModalOpen(true)}
                className="mt-3 px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-bold"
              >
                Submit Your First Complaint
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Modal Dialogs */}
      <CreateRequestModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={(id) => setSelectedRequestId(id)}
      />

      {selectedRequestId && (
        <RequestDetailPage
          requestId={selectedRequestId}
          onClose={() => setSelectedRequestId(null)}
        />
      )}
    </div>
  );
};

