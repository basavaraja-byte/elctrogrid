import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { KPICard } from '../../components/common/KPICard';
import { StatusBadge, PriorityBadge, SeverityBadge } from '../../components/common/StatusBadge';
import { LeafletMap } from '../../components/maps/LeafletMap';
import { EscalateModal } from './EscalateModal';
import {
  Activity,
  AlertTriangle,
  Users,
  CheckCircle2,
  Clock,
  Map,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const OperationsDashboard: React.FC = () => {
  const { jobs, electricians, escalations } = useApp();
  const navigate = useNavigate();

  const [isEscalateOpen, setIsEscalateOpen] = useState(false);

  // Workforce stats
  const availableTechs = electricians.filter((e) => e.status === 'available');
  const busyTechs = electricians.filter((e) => e.status === 'busy');
  const enRouteTechs = electricians.filter((e) => e.status === 'en_route');
  const offDutyTechs = electricians.filter((e) => e.status === 'off_duty' || e.status === 'leave');

  // Job stats
  const activeJobs = jobs.filter(
    (j) =>
      j.status === 'assigned' ||
      j.status === 'dispatched' ||
      j.status === 'en_route' ||
      j.status === 'in_progress'
  );
  const completedJobs = jobs.filter(
    (j) => j.status === 'completed' || j.status === 'customer_confirmed' || j.status === 'closed'
  );
  const delayedJobs = jobs.filter((j) => j.isOverdue || j.slaRisk === 'breached');
  const unassignedJobs = jobs.filter(
    (j) => !j.assignedElectricianId && j.status !== 'completed' && j.status !== 'cancelled'
  );
  const emergencyJobs = jobs.filter((j) => j.priority === 'emergency');

  // Compute SLA compliance percentage
  const totalEligible = jobs.length;
  const slaCompliance = Math.round(((totalEligible - delayedJobs.length) / totalEligible) * 100);

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Field Operations Supervision
          </h1>
          <p className="text-sm text-slate-500">
            Real-time workforce deployment, live GPS telematics, SLA adherence & exception routing
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/operations/map')}
            className="px-3.5 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm flex items-center gap-1.5 transition"
          >
            <Map className="w-4 h-4" />
            <span>Full Workforce Map</span>
          </button>
          <button
            onClick={() => setIsEscalateOpen(true)}
            className="px-3.5 py-2 text-xs font-bold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 rounded-xl shadow-xs flex items-center gap-1.5 transition"
          >
            <ShieldAlert className="w-4 h-4 text-rose-600" />
            <span>Escalate Issue</span>
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="SLA Compliance Rate"
          value={`${slaCompliance}%`}
          icon={TrendingUp}
          trend={slaCompliance > 90 ? 'up' : 'down'}
          change={`${delayedJobs.length} delayed`}
          description="Target SLA threshold: 92%"
          iconColor="text-emerald-600"
          bgColor="bg-emerald-50"
        />
        <KPICard
          title="Active Field Crews"
          value={`${activeJobs.length} Jobs`}
          icon={Activity}
          description={`${busyTechs.length} busy • ${enRouteTechs.length} en route`}
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KPICard
          title="Available Technicians"
          value={`${availableTechs.length} / ${electricians.length}`}
          icon={Users}
          description="Ready for emergency dispatch"
          iconColor="text-teal-600"
          bgColor="bg-teal-50"
        />
        <KPICard
          title="Critical SLA Breaches"
          value={delayedJobs.length}
          icon={AlertTriangle}
          trend="down"
          change="Action Required"
          description="Escalate or re-assign"
          iconColor="text-rose-600"
          bgColor="bg-rose-50"
          onClick={() => navigate('/operations/alerts')}
        />
      </div>

      {/* Live Map Preview & Fleet Status split */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Map className="w-4 h-4 text-blue-600" />
              Live Fleet Coordinates & Job Clusters
            </h3>
            <button
              onClick={() => navigate('/operations/map')}
              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-0.5"
            >
              <span>Expand Map</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <LeafletMap
            electricians={electricians}
            jobs={jobs.slice(0, 30)}
            height="380px"
          />
        </div>

        {/* Real-time Fleet Duty Status */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Workforce Readiness</h3>
            <p className="text-xs text-slate-500">Live operational status breakdown</p>

            <div className="mt-4 space-y-3">
              <div className="p-3 bg-emerald-50/70 border border-emerald-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-emerald-950 block">Available on Shift</span>
                  <span className="text-[11px] text-emerald-700">Immediate dispatch capacity</span>
                </div>
                <span className="text-lg font-extrabold text-emerald-700">{availableTechs.length}</span>
              </div>

              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-amber-950 block">Engaged on Jobs</span>
                  <span className="text-[11px] text-amber-700">On-site or staging repair</span>
                </div>
                <span className="text-lg font-extrabold text-amber-700">{busyTechs.length}</span>
              </div>

              <div className="p-3 bg-sky-50/70 border border-sky-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-sky-950 block">En Route / In Transit</span>
                  <span className="text-[11px] text-sky-700">Navigating to customer</span>
                </div>
                <span className="text-lg font-extrabold text-sky-700">{enRouteTechs.length}</span>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between">
                <div>
                  <span className="text-xs font-bold text-slate-800 block">Off Duty / Break</span>
                  <span className="text-[11px] text-slate-500">Not accepting assignments</span>
                </div>
                <span className="text-lg font-extrabold text-slate-700">{offDutyTechs.length}</span>
              </div>
            </div>
          </div>

          <button
            onClick={() => navigate('/operations/workforce')}
            className="w-full mt-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition flex items-center justify-center gap-1.5"
          >
            <span>Inspect All Technicians</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Escalation Dialog */}
      <EscalateModal
        isOpen={isEscalateOpen}
        onClose={() => setIsEscalateOpen(false)}
      />
    </div>
  );
};

