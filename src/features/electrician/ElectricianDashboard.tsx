import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { KPICard } from '../../components/common/KPICard';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Avatar } from '../../components/common/Avatar';
import { CompletionReportModal } from './CompletionReportModal';
import { AvailabilityModal } from './AvailabilityModal';
import { SimulatedLocationModal } from './SimulatedLocationModal';
import { Job, JobStatus } from '../../types';
import {
  HardHat,
  Clock,
  CheckCircle2,
  Navigation,
  Phone,
  Radio,
  Coffee,
  AlertTriangle,
  Play,
  Pause,
  MapPin,
  FileCheck,
  ChevronRight,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const ElectricianDashboard: React.FC = () => {
  const { user } = useAuth();
  const { jobs, electricians, refreshData } = useApp();
  const navigate = useNavigate();

  // Active technician record
  const currentTech =
    electricians.find(
      (e) =>
        e.userId === user?.id ||
        e.id === user?.id ||
        (user?.employeeId && e.employeeId === user.employeeId) ||
        (user?.email && e.email.toLowerCase() === user.email.toLowerCase())
    ) || electricians[0];

  const [selectedJobForReport, setSelectedJobForReport] = useState<Job | null>(null);
  const [isAvailabilityOpen, setIsAvailabilityOpen] = useState(false);
  const [isLocationOpen, setIsLocationOpen] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);

  // Filter jobs assigned to this technician
  const myJobs = jobs.filter(
    (j) => j.assignedElectricianId === currentTech?.id || (user?.id === 'usr-elec-1' && j.assignedElectricianId === 'elec-1')
  );

  const activeJob = myJobs.find(
    (j) =>
      j.status === 'assigned' ||
      j.status === 'dispatched' ||
      j.status === 'acknowledged' ||
      j.status === 'en_route' ||
      j.status === 'in_progress' ||
      j.status === 'on_hold'
  );

  const completedTodayCount = myJobs.filter(
    (j) => j.status === 'completed' || j.status === 'customer_confirmed' || j.status === 'closed'
  ).length;

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

  return (
    <div className="space-y-6">
      {/* Mobile-Friendly Technician Welcome Card */}
      <div className="bg-gradient-to-r from-navy-800 via-slate-900 to-blue-950 p-5 sm:p-7 rounded-2xl text-white shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <Avatar
            src={currentTech?.avatar}
            name={currentTech?.name || 'Technician'}
            size="xl"
            className="border-2 border-blue-400 shadow-md"
          />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-amber-400 font-mono">
                {currentTech?.employeeId}
              </span>
              <span className="text-[11px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded font-semibold capitalize">
                {currentTech?.status.replace('_', ' ')}
              </span>
            </div>
            <h1 className="text-xl font-extrabold tracking-tight mt-0.5">
              {currentTech?.name}
            </h1>
            <p className="text-xs text-slate-300">
              Shift: {currentTech?.shiftHours.start} - {currentTech?.shiftHours.end} • Workload: {currentTech?.currentWorkload}h / {currentTech?.maxDailyHours}h
            </p>
          </div>
        </div>

        {/* Quick Duty Control Buttons */}
        <div className="flex items-center gap-2 self-start sm:self-center">
          <button
            onClick={() => setIsAvailabilityOpen(true)}
            className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 transition border border-white/10"
          >
            <Clock className="w-3.5 h-3.5" />
            Duty Status
          </button>
          <button
            onClick={() => setIsLocationOpen(true)}
            className="px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md shadow-blue-600/30 transition"
          >
            <Radio className="w-3.5 h-3.5 animate-pulse" />
            GPS Telemetry
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KPICard
          title="Assigned Today"
          value={myJobs.length}
          icon={HardHat}
          description="Total work tickets"
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KPICard
          title="Completed"
          value={completedTodayCount}
          icon={CheckCircle2}
          description="Successfully resolved"
          iconColor="text-emerald-600"
          bgColor="bg-emerald-50"
        />
        <KPICard
          title="Hours Logged"
          value={`${currentTech?.currentWorkload || 0}h`}
          icon={Clock}
          description={`Max ${currentTech?.maxDailyHours || 8.5}h daily`}
          iconColor="text-indigo-600"
          bgColor="bg-indigo-50"
        />
        <KPICard
          title="Satisfaction"
          value={`${currentTech?.rating || 4.9}★`}
          icon={CheckCircle2}
          description="Based on client ratings"
          iconColor="text-amber-600"
          bgColor="bg-amber-50"
        />
      </div>

      {/* PRIMARY ACTIVE FIELD WORKSPACE CARD */}
      {activeJob ? (
        <div className="bg-white rounded-2xl border-2 border-blue-500 p-5 shadow-lg relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-blue-600 via-indigo-600 to-amber-500" />

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
                {activeJob.id}
              </span>
              <PriorityBadge priority={activeJob.priority} />
              <StatusBadge status={activeJob.status} />
            </div>

            <span className="text-xs text-slate-500 font-medium">
              Scheduled: {activeJob.preferredTimeWindow} (~{activeJob.estimatedDurationHours}h)
            </span>
          </div>

          <h3 className="text-base font-extrabold text-slate-900 mb-1">
            {activeJob.title}
          </h3>

          <p className="text-xs text-slate-600 mb-4 bg-slate-50 p-3 rounded-xl border border-slate-200 leading-relaxed">
            {activeJob.description}
          </p>

          {/* Location & Customer Info */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs mb-5">
            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex items-start gap-2.5">
              <MapPin className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-900 block">Customer Service Address</span>
                <span className="text-slate-600">{activeJob.location.address}, {activeJob.location.city}</span>
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                    activeJob.location.address
                  )}`}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 text-blue-600 font-bold flex items-center gap-1 hover:underline text-[11px]"
                >
                  <Navigation className="w-3 h-3" />
                  Open Turn-by-Turn Navigation
                </a>
              </div>
            </div>

            <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 flex items-start gap-2.5">
              <Phone className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-slate-900 block">On-Site Client Contact</span>
                <span className="text-slate-600">{activeJob.customerName}</span>
                <a
                  href={`tel:${activeJob.customerPhone}`}
                  className="mt-1 text-emerald-700 font-bold block hover:underline text-[11px]"
                >
                  Call {activeJob.customerPhone}
                </a>
              </div>
            </div>
          </div>

          {/* Equipment & Skills Checklist */}
          <div className="mb-5 bg-blue-50/50 p-3 rounded-xl border border-blue-100 text-xs">
            <span className="font-bold uppercase tracking-wider text-blue-900 text-[10px] block mb-1">
              Required Safety Gear & Procedures
            </span>
            <div className="flex flex-wrap gap-1.5">
              {activeJob.requiredEquipment.map((eq, i) => (
                <span key={i} className="bg-white text-slate-700 border border-blue-200 px-2 py-0.5 rounded text-[11px]">
                  🛡️ {eq}
                </span>
              ))}
              {activeJob.requiredSkills.map((sk, i) => (
                <span key={i} className="bg-blue-100 text-blue-800 border border-blue-200 px-2 py-0.5 rounded text-[11px] font-medium">
                  ⚡ {sk}
                </span>
              ))}
            </div>
          </div>

          {/* PROGRESS STEPPER & TRANSITION BUTTONS */}
          <div className="pt-4 border-t border-slate-200">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Field Status Progression:
              </span>

              <div className="flex flex-wrap items-center gap-2">
                {activeJob.status === 'assigned' || activeJob.status === 'dispatched' ? (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(activeJob, 'acknowledged', 'Technician acknowledged dispatch')}
                    className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5 transition"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Acknowledge Assignment
                  </button>
                ) : null}

                {activeJob.status === 'acknowledged' ? (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(activeJob, 'en_route', 'Technician en route to client site')}
                    className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5 transition"
                  >
                    <Navigation className="w-4 h-4" />
                    Start Travel / En Route
                  </button>
                ) : null}

                {activeJob.status === 'en_route' ? (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(activeJob, 'in_progress', 'Technician on-site. Work begun.')}
                    className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5 transition"
                  >
                    <Play className="w-4 h-4 fill-white" />
                    Arrived & Start Job
                  </button>
                ) : null}

                {activeJob.status === 'in_progress' ? (
                  <>
                    <button
                      disabled={isUpdatingStatus}
                      onClick={() => handleTransitionStatus(activeJob, 'on_hold', 'Job placed on hold: awaiting utility clearance')}
                      className="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition"
                    >
                      <Pause className="w-4 h-4" />
                      Hold
                    </button>
                    <button
                      disabled={isUpdatingStatus}
                      onClick={() => setSelectedJobForReport(activeJob)}
                      className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-md shadow-emerald-600/20 flex items-center gap-1.5 transition"
                    >
                      <FileCheck className="w-4 h-4" />
                      Complete Work & Sign Off
                    </button>
                  </>
                ) : null}

                {activeJob.status === 'on_hold' ? (
                  <button
                    disabled={isUpdatingStatus}
                    onClick={() => handleTransitionStatus(activeJob, 'in_progress', 'Resumed field work')}
                    className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-xl text-xs font-bold flex items-center gap-1.5"
                  >
                    <Play className="w-4 h-4 fill-white" />
                    Resume Work
                  </button>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400">
          <HardHat className="w-10 h-10 mx-auto text-slate-300 mb-2" />
          <h3 className="text-sm font-bold text-slate-700">No Active Jobs Currently in Progress</h3>
          <p className="text-xs text-slate-500 mt-1">
            Check upcoming assignments below or update your shift availability with central dispatch.
          </p>
        </div>
      )}

      {/* Today's Assigned Jobs List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Today's Field Work Tickets</h3>
            <p className="text-xs text-slate-500">All assignments designated to your employee badge</p>
          </div>
          <button
            onClick={() => navigate('/electrician/jobs')}
            className="text-xs font-bold text-blue-600 hover:text-blue-700"
          >
            View All ({myJobs.length})
          </button>
        </div>

        <div className="divide-y divide-slate-100">
          {myJobs.map((job) => (
            <div
              key={job.id}
              className="p-4 sm:px-6 hover:bg-slate-50/50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-bold text-slate-600">{job.id}</span>
                  <PriorityBadge priority={job.priority} />
                  <StatusBadge status={job.status} size="sm" />
                </div>
                <h4 className="text-xs font-bold text-slate-900">{job.title}</h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  📍 {job.location.address} • {job.customerName}
                </p>
              </div>

              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500">{job.preferredTimeWindow}</span>
                {job.status === 'in_progress' && (
                  <button
                    onClick={() => setSelectedJobForReport(job)}
                    className="px-3 py-1 bg-emerald-600 text-white rounded-lg font-bold text-xs"
                  >
                    Sign Off
                  </button>
                )}
              </div>
            </div>
          ))}

          {myJobs.length === 0 && (
            <div className="p-8 text-center text-xs text-slate-400">
              No jobs assigned to this technician profile yet.
            </div>
          )}
        </div>
      </div>

      {/* Completion Report Sign-Off Dialog */}
      <CompletionReportModal
        job={selectedJobForReport}
        isOpen={!!selectedJobForReport}
        onClose={() => setSelectedJobForReport(null)}
      />

      {/* Availability Management Dialog */}
      <AvailabilityModal
        isOpen={isAvailabilityOpen}
        onClose={() => setIsAvailabilityOpen(false)}
      />

      {/* Simulated GPS Location Sharing Dialog */}
      <SimulatedLocationModal
        isOpen={isLocationOpen}
        onClose={() => setIsLocationOpen(false)}
      />
    </div>
  );
};

