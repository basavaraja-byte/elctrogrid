import React from 'react';
import { useApp } from '../../context/AppContext';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { BarChart3, TrendingUp, Users, Star, Award, ShieldCheck } from 'lucide-react';

export const ExecutiveAnalyticsPage: React.FC = () => {
  const { electricians, jobs } = useApp();

  // Multi-quarter volume and revenue trend
  const quarterlyGrowth = [
    { quarter: 'Q1', jobs: 540, sla: 92.4, satisfaction: 4.6 },
    { quarter: 'Q2', jobs: 680, sla: 94.1, satisfaction: 4.7 },
    { quarter: 'Q3', jobs: 820, sla: 95.3, satisfaction: 4.8 },
    { quarter: 'Q4 (Current)', jobs: 940, sla: 96.2, satisfaction: 4.9 },
  ];

  // Top performing electricians
  const topElectricians = [...electricians]
    .sort((a, b) => b.jobsCompletedTotal - a.jobsCompletedTotal)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Executive Analytics & KPIs
        </h1>
        <p className="text-sm text-slate-500">
          Strategic growth insights, workforce productivity, and service quality benchmarks
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">Total Capacity</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">
            {electricians.length} Master Crews
          </span>
          <span className="text-xs text-blue-600 font-semibold mt-1 block">100% active shift coverage</span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">Quarterly Jobs Delivered</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">940 Tickets</span>
          <span className="text-xs text-emerald-600 font-semibold mt-1 flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5" />
            +18.2% vs Q3
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">Customer Rating</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">4.88 / 5.0</span>
          <span className="text-xs text-amber-500 font-semibold mt-1 flex items-center gap-1">
            <Star className="w-3.5 h-3.5 fill-amber-400" />
            98.4% 5-Star Reviews
          </span>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <span className="text-xs font-bold uppercase text-slate-400 block">SLA Excellence Rate</span>
          <span className="text-2xl font-extrabold text-slate-900 mt-1 block">96.2%</span>
          <span className="text-xs text-emerald-600 font-semibold mt-1 block">Zero major regulatory penalties</span>
        </div>
      </div>

      {/* Growth Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h3 className="text-sm font-bold text-slate-900">Quarterly Operational Volume (2025 - 2026)</h3>
            <p className="text-xs text-slate-500">Service request completion scale across municipal grid</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={quarterlyGrowth}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="quarter" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Area type="monotone" dataKey="jobs" stroke="#3b82f6" fill="#eff6ff" strokeWidth={3} name="Delivered Jobs" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Field Techs Table */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Award className="w-4 h-4 text-amber-500" />
              Workforce Productivity Leaders
            </h3>
            <p className="text-xs text-slate-500">Top electricians by completed jobs & satisfaction score</p>

            <div className="mt-4 divide-y divide-slate-100">
              {topElectricians.map((tech, i) => (
                <div key={tech.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2.5">
                    <span className="w-5 h-5 rounded-full bg-slate-100 text-slate-600 font-bold flex items-center justify-center text-[10px]">
                      {i + 1}
                    </span>
                    <img
                      src={tech.avatar}
                      alt={tech.name}
                      className="w-7 h-7 rounded-full object-cover border border-slate-200"
                    />
                    <div>
                      <span className="font-bold text-slate-900 block">{tech.name}</span>
                      <span className="text-[10px] text-slate-500">{tech.skills[0]}</span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="font-extrabold text-blue-700 block">
                      {tech.jobsCompletedTotal} jobs
                    </span>
                    <span className="text-[10px] text-amber-600 font-semibold">
                      ★ {tech.rating}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

