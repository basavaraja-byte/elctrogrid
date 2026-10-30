import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { KPICard } from '../../components/common/KPICard';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { ScheduleOptimizeModal } from './ScheduleOptimizeModal';
import { Job, ServiceRequest } from '../../types';
import {
  Inbox,
  AlertTriangle,
  Users,
  Briefcase,
  CheckCircle,
  Clock,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Calendar,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { useNavigate } from 'react-router-dom';

export const DispatcherDashboard: React.FC = () => {
  const { serviceRequests, jobs, electricians } = useApp();
  const navigate = useNavigate();

  const [selectedJobForOptimize, setSelectedJobForOptimize] = useState<Job | null>(null);

  // KPIs
  const newRequestsCount = serviceRequests.filter(
    (r) => r.status === 'submitted' || r.status === 'under_review'
  ).length;

  const unassignedJobs = jobs.filter(
    (j) => !j.assignedElectricianId && j.status !== 'completed' && j.status !== 'cancelled'
  );

  const activeAssignedJobs = jobs.filter(
    (j) =>
      j.assignedElectricianId &&
      (j.status === 'assigned' ||
        j.status === 'dispatched' ||
        j.status === 'en_route' ||
        j.status === 'in_progress')
  );

  const emergencyJobs = jobs.filter(
    (j) => j.priority === 'emergency' && j.status !== 'completed' && j.status !== 'closed'
  );

  const atRiskJobs = jobs.filter(
    (j) => j.isOverdue || j.slaRisk === 'breached' || j.slaRisk === 'warning'
  );

  // Chart data: Category breakdown
  const categoryCounts: Record<string, number> = {};
  jobs.forEach((j) => {
    const cat = j.category.replace(/_/g, ' ');
    categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
  });

  const categoryChartData = Object.keys(categoryCounts).map((key) => ({
    name: key,
    count: categoryCounts[key],
  }));

  // Status Distribution
  const statusCounts: Record<string, number> = {};
  jobs.forEach((j) => {
    statusCounts[j.status] = (statusCounts[j.status] || 0) + 1;
  });

  const statusChartData = [
    { name: 'Submitted / Review', value: serviceRequests.filter(r => r.status === 'submitted' || r.status === 'under_review').length, color: '#3b82f6' },
    { name: 'Validated', value: statusCounts['validated'] || 0, color: '#14b8a6' },
    { name: 'Assigned / Dispatched', value: (statusCounts['assigned'] || 0) + (statusCounts['dispatched'] || 0), color: '#8b5cf6' },
    { name: 'In Progress / Field', value: (statusCounts['en_route'] || 0) + (statusCounts['in_progress'] || 0), color: '#f59e0b' },
    { name: 'Completed / Closed', value: (statusCounts['completed'] || 0) + (statusCounts['closed'] || 0), color: '#10b981' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Central Dispatch & Scheduling Workspace
          </h1>
          <p className="text-sm text-slate-500">
            Intelligent job routing, workforce scheduling, constraint matching & SLA oversight
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/dispatcher/requests')}
            className="px-3.5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm flex items-center gap-1.5 transition"
          >
            <Inbox className="w-4 h-4" />
            <span>Process Requests ({newRequestsCount})</span>
          </button>
          <button
            onClick={() => navigate('/dispatcher/recovery')}
            className="px-3.5 py-2 text-xs font-bold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-xl shadow-xs flex items-center gap-1.5 transition"
          >
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span>Recovery Centre</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="New Requests"
          value={newRequestsCount}
          icon={Inbox}
          description="Awaiting dispatcher triage"
          trend="up"
          change={`${newRequestsCount} pending`}
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
          onClick={() => navigate('/dispatcher/requests')}
        />
        <KPICard
          title="Unassigned Jobs"
          value={unassignedJobs.length}
          icon={Clock}
          description="Ready for intelligent engine"
          iconColor="text-purple-600"
          bgColor="bg-purple-50"
          onClick={() => navigate('/dispatcher/jobs')}
        />
        <KPICard
          title="Active Field Dispatches"
          value={activeAssignedJobs.length}
          icon={Briefcase}
          description="Technicians en route / on-site"
          iconColor="text-amber-600"
          bgColor="bg-amber-50"
          onClick={() => navigate('/dispatcher/schedule')}
        />
        <KPICard
          title="SLA Risk / Overdue"
          value={atRiskJobs.length}
          icon={AlertTriangle}
          description="Immediate attention required"
          trend="down"
          change="Critical SLA"
          iconColor="text-rose-600"
          bgColor="bg-rose-50"
        />
      </div>

      {/* Emergency Jobs Alert Callout */}
      {emergencyJobs.length > 0 && (
        <div className="bg-red-50/80 border border-red-300 rounded-xl p-4 shadow-xs">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-red-900">
                Critical Priority Emergency Tickets ({emergencyJobs.length})
              </h3>
            </div>
            <span className="text-[11px] text-red-700 font-semibold">Max 45m Response Target</span>
          </div>

          <div className="space-y-2">
            {emergencyJobs.slice(0, 3).map((job) => (
              <div
                key={job.id}
                className="bg-white p-3 rounded-lg border border-red-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-red-700">{job.id}</span>
                    <span className="text-xs font-bold text-slate-900">{job.title}</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">{job.location.address}</p>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-600">
                    {job.assignedElectricianName ? `Assigned: ${job.assignedElectricianName}` : 'Unassigned'}
                  </span>
                  {!job.assignedElectricianId && (
                    <button
                      onClick={() => setSelectedJobForOptimize(job)}
                      className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg flex items-center gap-1 shadow-xs"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      Optimize & Dispatch
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Analytics Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Breakdown Bar Chart */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Job Volume by Electrical Category</h3>
              <p className="text-xs text-slate-500">Distribution across commercial & residential infrastructure</p>
            </div>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categoryChartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <XAxis dataKey="name" angle={-15} textAnchor="end" interval={0} tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Status Distribution Donut Chart */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Operational Pipeline</h3>
            <p className="text-xs text-slate-500">Current lifecycle states across all active tickets</p>
          </div>

          <div className="h-52 w-full my-auto">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {statusChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
            {statusChartData.map((s, idx) => (
              <div key={idx} className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                  <span className="text-slate-600">{s.name}</span>
                </div>
                <span className="font-bold text-slate-800">{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Unassigned Operational Jobs Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Validated Jobs Awaiting Technician Scheduling ({unassignedJobs.length})
            </h3>
            <p className="text-xs text-slate-500">
              Run constraint-aware optimizer to recommend qualified electricians
            </p>
          </div>
          <button
            onClick={() => navigate('/dispatcher/jobs')}
            className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>View All Jobs</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-slate-100 overflow-x-auto">
          {unassignedJobs.slice(0, 5).map((job) => (
            <div
              key={job.id}
              className="p-4 sm:px-6 hover:bg-slate-50 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            >
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs font-bold text-blue-600">{job.id}</span>
                  <PriorityBadge priority={job.priority} />
                  <span className="text-xs text-slate-500">Req: {job.requestId}</span>
                </div>
                <h4 className="text-xs font-bold text-slate-900">{job.title}</h4>
                <p className="text-xs text-slate-500 mt-0.5">{job.location.address}</p>
                <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-600">
                  <span><b>Skills:</b> {job.requiredSkills.join(', ') || 'General'}</span>
                  <span><b>Est:</b> {job.estimatedDurationHours}h</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedJobForOptimize(job)}
                className="px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold shadow-sm flex items-center gap-1.5 self-start sm:self-auto transition"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Optimize Schedule</span>
              </button>
            </div>
          ))}

          {unassignedJobs.length === 0 && (
            <div className="p-8 text-center text-xs text-slate-400">
              All validated operational jobs are assigned and dispatched.
            </div>
          )}
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

