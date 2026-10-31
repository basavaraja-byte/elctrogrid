import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { Job, JobStatus } from '../../types';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Avatar } from '../../components/common/Avatar';
import { CompletionReportModal } from './CompletionReportModal';
import { IncomingJobOfferBanner } from './IncomingJobOfferBanner';
import { CompleteComplaintReportModal } from './CompleteComplaintReportModal';
import { api } from '../../services/api/apiClient';
import {
  HardHat,
  MapPin,
  Phone,
  Navigation,
  FileCheck,
  CheckCircle2,
  Clock,
  Play,
  Pause,
  AlertTriangle,
  Search,
  Check,
  DollarSign,
  Lock,
  Receipt,
  Download,
  Banknote,
  FileText,
} from 'lucide-react';

type TabType = 'assigned' | 'accepted' | 'in_progress' | 'completed' | 'all';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const AssignedJobsPage: React.FC = () => {
  const { user } = useAuth();
  const { jobs, electricians, refreshData } = useApp();

  const currentTech =
    electricians.find(
      (e) =>
        e.userId === user?.id ||
        e.id === user?.id ||
        (user?.employeeId && e.employeeId === user.employeeId) ||
        (user?.email && e.email.toLowerCase() === user.email.toLowerCase())
    ) || electricians[0];

  const [selectedJobForReport, setSelectedJobForReport] = useState<Job | null>(null);
  const [selectedJobForComplaintReport, setSelectedJobForComplaintReport] = useState<Job | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('assigned');
  const [searchQuery, setSearchQuery] = useState('');
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  // All jobs assigned to this technician
  const myJobs = jobs.filter(
    (j) =>
      j.assignedElectricianId === currentTech?.id ||
      (user?.id === 'usr-elec-1' && j.assignedElectricianId === 'elec-1') ||
      (user?.role === 'technician' && !j.assignedElectricianId)
  );

  // Tab categorization logic
  const assignedJobs = myJobs.filter((j) => j.status === 'assigned' || j.status === 'dispatched');
  const acceptedJobs = myJobs.filter((j) => j.status === 'acknowledged');
  const inProgressJobs = myJobs.filter(
    (j) => j.status === 'en_route' || j.status === 'in_progress' || j.status === 'on_hold'
  );
  const completedJobs = myJobs.filter(
    (j) => j.status === 'completed' || j.status === 'customer_confirmed' || j.status === 'closed'
  );

  // Filter based on active tab
  let currentTabJobs: Job[] = [];
  if (activeTab === 'assigned') currentTabJobs = assignedJobs;
  else if (activeTab === 'accepted') currentTabJobs = acceptedJobs;
  else if (activeTab === 'in_progress') currentTabJobs = inProgressJobs;
  else if (activeTab === 'completed') currentTabJobs = completedJobs;
  else currentTabJobs = myJobs;

  // Search filter
  const filteredJobs = currentTabJobs.filter((j) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      j.title.toLowerCase().includes(q) ||
      j.id.toLowerCase().includes(q) ||
      j.customerName.toLowerCase().includes(q) ||
      j.location.address.toLowerCase().includes(q)
    );
  });

  const handleTransitionStatus = async (job: Job, nextStatus: JobStatus, note?: string) => {
    if (!user) return;
    setIsUpdatingStatus(true);
    try {
      await api.updateJobStatus(job.id, nextStatus, user, note);
      refreshData();
    } catch (err) {
      console.error(err);
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const handleConfirmCash = async (job: Job) => {
    if (!user) return;
    setIsUpdatingStatus(true);
    try {
      await api.confirmCashPayment(job.id, user);
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Failed to confirm cash payment.');
    } finally {
      setIsUpdatingStatus(false);
    }
  };

  const tabs: { id: TabType; label: string; count: number; color: string; activeBg: string }[] = [
    {
      id: 'assigned',
      label: 'Assigned',
      count: assignedJobs.length,
      color: 'text-blue-600',
      activeBg: 'bg-blue-600 text-white',
    },
    {
      id: 'accepted',
      label: 'Accepted',
      count: acceptedJobs.length,
      color: 'text-cyan-600',
      activeBg: 'bg-cyan-600 text-white',
    },
    {
      id: 'in_progress',
      label: 'In Progress',
      count: inProgressJobs.length,
      color: 'text-amber-600',
      activeBg: 'bg-amber-600 text-white',
    },
    {
      id: 'completed',
      label: 'Completed',
      count: completedJobs.length,
      color: 'text-emerald-600',
      activeBg: 'bg-emerald-600 text-white',
    },
    {
      id: 'all',
      label: 'All Tickets',
      count: myJobs.length,
      color: 'text-slate-600',
      activeBg: 'bg-slate-800 text-white',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Assigned Field Jobs
          </h1>
          <p className="text-sm text-slate-500">
            Work order lifecycle: Assigned → Accepted → In Progress → Completed
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Avatar name={currentTech?.name || 'Technician'} src={currentTech?.avatar} size="sm" />
          <div className="text-xs">
            <p className="font-bold text-slate-800">{currentTech?.name}</p>
            <p className="text-slate-400 font-mono text-[11px]">{currentTech?.employeeId}</p>
          </div>
        </div>
      </div>

      {/* Feature 1: Intelligent Incoming Job Offer Banner with 60s live countdown */}
      {currentTech && (
        <IncomingJobOfferBanner
          currentTech={currentTech}
          onViewReport={(j) => setSelectedJobForComplaintReport(j)}
        />
      )}

      {/* 4 SEGREGATED STAGE TABS */}
      <div className="bg-white p-1.5 rounded-2xl border border-slate-200 shadow-xs flex flex-wrap gap-1">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 min-w-[120px] py-2.5 px-3 rounded-xl text-xs font-bold transition flex items-center justify-center gap-2 cursor-pointer ${
                isActive
                  ? `${tab.activeBg} shadow-sm`
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
              }`}
            >
              <span>{tab.label}</span>
              <span
                className={`px-2 py-0.5 rounded-full text-[11px] font-extrabold ${
                  isActive ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-700'
                }`}
              >
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Search Input */}
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder={`Search ${activeTab.replace('_', ' ')} tickets by title, customer, locality, ID...`}
          className="w-full pl-9 pr-4 py-2.5 text-xs border border-slate-200 rounded-xl bg-white shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500/20"
        />
        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
      </div>

      {/* Jobs Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredJobs.map((job) => (
          <div
            key={job.id}
            className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-blue-700">{job.id}</span>
                  <PriorityBadge priority={job.priority} />
                </div>
                <StatusBadge status={job.status} size="sm" />
              </div>

              <h3 className="text-sm font-bold text-slate-900 mb-1">{job.title}</h3>
              <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed mb-3">
                {job.description}
              </p>

              <div className="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-3 rounded-xl border border-slate-200/80 mb-4">
                <div className="flex items-start gap-2">
                  <MapPin className="w-3.5 h-3.5 text-blue-600 flex-shrink-0 mt-0.5" />
                  <span className="truncate">{job.location.address}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-indigo-600" />
                  <span>Scheduled: {job.preferredTimeWindow} (~{job.estimatedDurationHours}h)</span>
                </div>
                <div className="flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-emerald-600" />
                  <span>{job.customerName} ({job.customerPhone})</span>
                </div>
              </div>

              {/* Payment & Job Closure Status */}
              {job.payment && (job.payment.status === 'completed' || job.status === 'closed') && (
                <div className="mb-3 px-3 py-2 bg-emerald-50 border border-emerald-300 rounded-xl flex items-center justify-between text-xs text-emerald-900 shadow-xs">
                  <div className="flex items-center gap-1.5 font-bold">
                    <Lock className="w-3.5 h-3.5 text-emerald-700" />
                    <span>PAYMENT COMPLETED • JOB CLOSED</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-extrabold text-emerald-800">
                      ₹{job.payment.amountInr.toLocaleString('en-IN')}
                    </span>
                    <a
                      href={`${API_BASE_URL}/api/v1/payments/invoices/${job.invoice?.invoiceNumber || job.payment.receiptNumber || 'EG-2026-000001'}/pdf`}
                      target="_blank"
                      rel="noreferrer"
                      className="px-2 py-0.5 bg-emerald-700 hover:bg-emerald-800 text-white rounded text-[10px] font-bold flex items-center gap-1 shadow-xs transition"
                    >
                      <Receipt className="w-3 h-3" />
                      Receipt PDF
                    </a>
                  </div>
                </div>
              )}

              {/* Pending Payment Request Banner with Cash Confirmation Action */}
              {job.payment && job.payment.status === 'pending' && (
                <div className="mb-3 px-3 py-2.5 bg-amber-50 border border-amber-300 rounded-xl text-xs text-amber-900 shadow-xs space-y-1.5">
                  <div className="flex items-center justify-between font-bold">
                    <span className="flex items-center gap-1 text-amber-800">
                      <Clock className="w-3.5 h-3.5" />
                      Duration: {job.payment.durationFormatted || (job.actualDurationMinutes ? `${job.actualDurationMinutes} mins` : '75 mins')}
                    </span>
                    <span className="text-amber-900 font-extrabold font-mono text-sm">
                      Labour Total: ₹{job.payment.amountInr.toLocaleString('en-IN')}
                    </span>
                  </div>
                  {job.damagedComponents && job.damagedComponents.length > 0 && (
                    <div className="text-[11px] text-amber-800 bg-amber-100/60 p-1.5 rounded flex items-center justify-between">
                      <span>Damaged Parts: {job.damagedComponents.length} reported</span>
                      <span className="font-semibold text-amber-900">Price to be confirmed</span>
                    </div>
                  )}
                  <div className="pt-1 flex items-center justify-between">
                    <span className="text-[10px] text-amber-700 uppercase font-semibold">Payment Pending (Cash / UPI)</span>
                    <button
                      type="button"
                      disabled={isUpdatingStatus}
                      onClick={() => handleConfirmCash(job)}
                      className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center gap-1 shadow-xs transition cursor-pointer"
                    >
                      <Banknote className="w-3.5 h-3.5" />
                      Confirm Cash Received
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Stepper Buttons for this job */}
            <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setSelectedJobForComplaintReport(job)}
                  className="text-xs font-bold text-blue-700 hover:text-blue-900 flex items-center gap-1 hover:underline cursor-pointer"
                  title="View Complete Customer Complaint Report & Attachments"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Full Report</span>
                </button>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                    job.location.address
                  )}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-slate-600 font-bold flex items-center gap-1 hover:underline"
                >
                  <Navigation className="w-3 h-3" />
                  Navigate
                </a>
              </div>

              <div className="flex items-center gap-1.5">
                {/* 1. ASSIGNED -> ACCEPTED */}
                {(job.status === 'assigned' || job.status === 'dispatched') && (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(job, 'acknowledged', 'Accepted assignment')}
                    className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center gap-1 cursor-pointer transition"
                  >
                    <Check className="w-3.5 h-3.5" />
                    Accept Job
                  </button>
                )}

                {/* 2. ACCEPTED -> EN ROUTE */}
                {job.status === 'acknowledged' && (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(job, 'en_route', 'Technician en route to client site')}
                    className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center gap-1 cursor-pointer transition"
                  >
                    <Navigation className="w-3.5 h-3.5" />
                    Start Route (En Route)
                  </button>
                )}

                {/* 3. EN ROUTE -> IN PROGRESS */}
                {job.status === 'en_route' && (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(job, 'in_progress', 'Technician arrived at premises')}
                    className="px-3.5 py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-xs font-bold shadow-xs flex items-center gap-1 cursor-pointer transition"
                  >
                    <Play className="w-3.5 h-3.5 fill-white" />
                    Arrived & Start Job
                  </button>
                )}

                {/* 4. IN PROGRESS -> COMPLETE OR HOLD */}
                {job.status === 'in_progress' && (
                  <>
                    <button
                      disabled={isUpdatingStatus}
                      onClick={() => handleTransitionStatus(job, 'on_hold', 'Job placed on hold: awaiting utility clearance')}
                      className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold cursor-pointer"
                    >
                      <Pause className="w-3 h-3" />
                      Hold
                    </button>
                    <button
                      disabled={isUpdatingStatus}
                      onClick={() => setSelectedJobForReport(job)}
                      className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold flex items-center gap-1 shadow-sm cursor-pointer transition"
                    >
                      <FileCheck className="w-3.5 h-3.5" />
                      Complete & Sign Off
                    </button>
                  </>
                )}

                {job.status === 'on_hold' && (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(job, 'in_progress', 'Resumed electrical work')}
                    className="px-3.5 py-1.5 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-xs font-bold cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 fill-white" />
                    Resume Work
                  </button>
                )}

                {/* 5. COMPLETED */}
                {(job.status === 'completed' || job.status === 'customer_confirmed' || job.status === 'closed') && (
                  <button
                    onClick={() => setSelectedJobForReport(job)}
                    className="px-3 py-1.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-bold flex items-center gap-1 hover:bg-emerald-100 cursor-pointer"
                  >
                    <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                    View Sign-Off
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {filteredJobs.length === 0 && (
          <div className="col-span-full bg-white p-12 text-center text-slate-400 rounded-2xl border border-slate-200">
            <HardHat className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            <p className="text-sm font-bold text-slate-700">
              No tickets in the {activeTab.replace('_', ' ').toUpperCase()} stage
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Select another status tab above to inspect your queue.
            </p>
          </div>
        )}
      </div>

      {/* Completion Report Sign-Off Dialog */}
      <CompletionReportModal
        job={selectedJobForReport}
        isOpen={!!selectedJobForReport}
        onClose={() => setSelectedJobForReport(null)}
      />

      {/* Feature 2: Complete Customer Complaint Report Dialog */}
      <CompleteComplaintReportModal
        job={selectedJobForComplaintReport}
        electrician={currentTech}
        isOpen={Boolean(selectedJobForComplaintReport)}
        onClose={() => setSelectedJobForComplaintReport(null)}
        onOpenWorkReport={(j) => setSelectedJobForReport(j)}
      />
    </div>
  );
};
