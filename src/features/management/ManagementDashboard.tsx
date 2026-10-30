import React from 'react';
import { useApp } from '../../context/AppContext';
import { KPICard } from '../../components/common/KPICard';
import {
  ShieldCheck,
  Users,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  Building2,
  Briefcase,
  FileCheck,
  ArrowRight,
  Sliders,
  ScrollText,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
} from 'recharts';

export const ManagementDashboard: React.FC = () => {
  const { jobs, serviceRequests, electricians, approvals, escalations } = useApp();
  const navigate = useNavigate();

  const completedJobsCount = jobs.filter(
    (j) => j.status === 'completed' || j.status === 'customer_confirmed' || j.status === 'closed'
  ).length;

  const completionRate = Math.round((completedJobsCount / Math.max(1, jobs.length)) * 100);
  const pendingApprovals = approvals.filter((a) => a.currentStatus === 'pending');
  const delayedJobsCount = jobs.filter((j) => j.isOverdue || j.slaRisk === 'breached').length;
  const slaAchievementRate = Math.round(((jobs.length - delayedJobsCount) / Math.max(1, jobs.length)) * 100);

  // Workforce utilization calculation
  const totalBookedHours = electricians.reduce((sum, e) => sum + e.currentWorkload, 0);
  const totalCapacityHours = electricians.reduce((sum, e) => sum + e.maxDailyHours, 0);
  const workforceUtilization = Math.round((totalBookedHours / Math.max(1, totalCapacityHours)) * 100);

  // Monthly Service Trend
  const monthlyData = [
    { month: 'Jun', volume: 180, sla: 96, revenue: 145 },
    { month: 'Jul', volume: 220, sla: 94, revenue: 178 },
    { month: 'Aug', volume: 245, sla: 95, revenue: 202 },
    { month: 'Sep', volume: 270, sla: 93, revenue: 230 },
    { month: 'Oct', volume: 295, sla: 96, revenue: 254 },
  ];

  return (
    <div className="space-y-6">
      {/* Executive Header */}
      <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-navy-950 p-6 sm:p-8 rounded-2xl text-white shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-slate-300 border border-white/10 mb-2">
            <ShieldCheck className="w-3.5 h-3.5 text-rose-400" />
            <span>Executive Management Control</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            ElectroGrid Operational Governance
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-xl">
            Enterprise oversight, policy thresholds, executive approvals, and organizational performance
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/management/approvals')}
            className="px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-md shadow-rose-600/30 flex items-center gap-1.5 transition"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Pending Approvals ({pendingApprovals.length})</span>
          </button>
          <button
            onClick={() => navigate('/management/policies')}
            className="px-3.5 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white font-bold text-xs border border-white/10 flex items-center gap-1.5 transition"
          >
            <Sliders className="w-4 h-4" />
            <span>Policies</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="SLA Achievement"
          value={`${slaAchievementRate}%`}
          icon={TrendingUp}
          trend={slaAchievementRate >= 92 ? 'up' : 'down'}
          change="Target 92%"
          description="Organization-wide standard"
          iconColor="text-emerald-600"
          bgColor="bg-emerald-50"
        />
        <KPICard
          title="Workforce Utilization"
          value={`${workforceUtilization}%`}
          icon={Users}
          description={`${totalBookedHours.toFixed(0)}h / ${totalCapacityHours.toFixed(0)}h capacity`}
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KPICard
          title="Total Operational Jobs"
          value={jobs.length}
          icon={Briefcase}
          description={`${completedJobsCount} resolved tickets`}
          trend="up"
          change="+14% MoM"
          iconColor="text-indigo-600"
          bgColor="bg-indigo-50"
        />
        <KPICard
          title="Pending Approvals"
          value={pendingApprovals.length}
          icon={ShieldCheck}
          description="High-impact overrides"
          trend="down"
          change="Review Required"
          iconColor="text-rose-600"
          bgColor="bg-rose-50"
          onClick={() => navigate('/management/approvals')}
        />
      </div>

      {/* Critical Approval Requests Callout */}
      {pendingApprovals.length > 0 && (
        <div className="bg-rose-50/70 border border-rose-200 rounded-xl p-5 shadow-xs">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-pulse" />
              <h3 className="text-xs font-bold uppercase tracking-wider text-rose-900">
                Action Required: Executive Schedule & Policy Approvals ({pendingApprovals.length})
              </h3>
            </div>
            <button
              onClick={() => navigate('/management/approvals')}
              className="text-xs font-bold text-rose-700 hover:text-rose-800 flex items-center gap-1"
            >
              <span>Review in Approval Centre</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-2">
            {pendingApprovals.slice(0, 2).map((app) => (
              <div
                key={app.id}
                className="bg-white p-3.5 rounded-lg border border-rose-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs font-bold text-rose-700">{app.id}</span>
                    <span className="text-xs font-bold text-slate-900">{app.title}</span>
                  </div>
                  <p className="text-xs text-slate-600 line-clamp-1">{app.details}</p>
                </div>

                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>From: <b>{app.requestedBy}</b> ({app.requesterRole})</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strategic Performance Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900">Service Volume Growth (MoM)</h3>
            <p className="text-xs text-slate-500">Commercial & residential demand across regional grid</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="volume" fill="#2563eb" radius={[4, 4, 0, 0]} name="Completed Work Tickets" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900">SLA Achievement Benchmark (%)</h3>
            <p className="text-xs text-slate-500">Historical performance vs target operational threshold</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis domain={[90, 100]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="sla" stroke="#10b981" strokeWidth={3} name="SLA Compliance %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

