import React from 'react';
import { useApp } from '../../context/AppContext';
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
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { BarChart3, TrendingUp, Clock, CheckCircle2, ShieldCheck } from 'lucide-react';

export const OperationalReportsPage: React.FC = () => {
  const { jobs, electricians } = useApp();

  // Weekly Service Volume Trend (Mon to Sun)
  const weeklyTrendData = [
    { day: 'Mon', completed: 18, incoming: 22, slaMet: 95 },
    { day: 'Tue', completed: 21, incoming: 24, slaMet: 93 },
    { day: 'Wed', completed: 25, incoming: 26, slaMet: 96 },
    { day: 'Thu', completed: 19, incoming: 20, slaMet: 92 },
    { day: 'Fri', completed: 24, incoming: 25, slaMet: 94 },
    { day: 'Sat', completed: 14, incoming: 15, slaMet: 97 },
    { day: 'Sun', completed: 9, incoming: 10, slaMet: 98 },
  ];

  // Electrician Workload Distribution
  const workloadData = electricians.slice(0, 8).map((e) => ({
    name: e.name.split(' ')[0],
    hours: e.currentWorkload,
    max: e.maxDailyHours,
  }));

  // Problem Category Share
  const categoryMap: Record<string, number> = {};
  jobs.forEach((j) => {
    categoryMap[j.category] = (categoryMap[j.category] || 0) + 1;
  });

  const categoryPieData = Object.keys(categoryMap).map((cat, i) => ({
    name: cat.replace(/_/g, ' '),
    value: categoryMap[cat],
    color: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'][i % 8],
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Field Operational Reports & Analytics
        </h1>
        <p className="text-sm text-slate-500">
          Executive performance metrics, workload balance, completion turnaround, and compliance trends
        </p>
      </div>

      {/* Summary KPI Highlights */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">Weekly Volume</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">142 Tickets</span>
          <span className="text-xs text-emerald-600 font-semibold mt-1 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5" />
            +8.4% vs last week
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">Avg Resolution Time</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">2.3 Hours</span>
          <span className="text-xs text-slate-500 mt-1 block">From dispatch to sign-off</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">First-Visit Fix Rate</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">94.6%</span>
          <span className="text-xs text-emerald-600 font-semibold mt-1 block">Top tier benchmark</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">Overall SLA Compliance</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">95.2%</span>
          <span className="text-xs text-emerald-600 font-semibold mt-1 block">Target threshold 92%</span>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly Completion Volume Chart */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900">Weekly Job Completion & SLA Performance</h3>
            <p className="text-xs text-slate-500">Volume processed vs compliance percentage</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={weeklyTrendData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="completed" stroke="#3b82f6" strokeWidth={2.5} name="Completed Jobs" />
                <Line type="monotone" dataKey="incoming" stroke="#94a3b8" strokeWidth={2} name="Incoming Requests" strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Technician Workload Distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900">Current Technician Workload (Hours)</h3>
            <p className="text-xs text-slate-500">Distribution across active shifts to avoid overtime</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={workloadData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="hours" fill="#0ea5e9" radius={[4, 4, 0, 0]} name="Assigned Hours" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

