import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { KPICard } from '../../components/common/KPICard';
import { StatusBadge, PriorityBadge } from '../../components/common/StatusBadge';
import { Avatar } from '../../components/common/Avatar';
import { LeafletMap } from '../../components/maps/LeafletMap';
import { DemoScenarioRunnerModal } from '../../components/demo/DemoScenarioRunnerModal';
import { AIInsightsPanel } from './components/AIInsightsPanel';
import { formatTimeIST, formatDateTimeIST } from '../../utils/formatters';
import { Electrician, Job } from '../../types';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts';
import {
  Activity,
  HardHat,
  Zap,
  Clock,
  ShieldCheck,
  AlertTriangle,
  MapPin,
  TrendingUp,
  Cpu,
  Radio,
  ExternalLink,
  ChevronRight,
  CheckCircle2,
  PieChart as PieIcon,
  BarChart3,
  Calendar,
  Layers,
  History,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const SupervisorDashboard: React.FC = () => {
  const { user } = useAuth();
  const { jobs, electricians, disruptions, auditLogs } = useApp();
  const navigate = useNavigate();

  const [selectedElectrician, setSelectedElectrician] = useState<Electrician | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);

  // Active operational counts
  const activeJobs = jobs.filter(
    (j) =>
      j.status === 'assigned' ||
      j.status === 'dispatched' ||
      j.status === 'acknowledged' ||
      j.status === 'en_route' ||
      j.status === 'in_progress'
  );

  const completedTodayJobs = jobs.filter(
    (j) => j.status === 'completed' || j.status === 'customer_confirmed' || j.status === 'closed'
  );

  const emergencyJobs = jobs.filter(
    (j) => j.priority === 'emergency' && j.status !== 'completed' && j.status !== 'closed'
  );

  const availableTechs = electricians.filter((e) => e.status === 'available');
  const onDutyTechs = electricians.filter((e) => e.status !== 'off_duty');

  // Automated assignments stream (recent jobs with score or assignment)
  const recentAutoAssignments = [...jobs]
    .filter((j) => j.assignedElectricianId)
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 5);

  // Recent operational audit events stream
  const recentAuditEvents = [...auditLogs]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 6);

  // Recharts Data: Job Status Distribution
  const statusCounts = {
    completed: jobs.filter((j) => j.status === 'completed' || j.status === 'closed' || j.status === 'customer_confirmed').length,
    in_progress: jobs.filter((j) => j.status === 'in_progress').length,
    en_route: jobs.filter((j) => j.status === 'en_route').length,
    dispatched: jobs.filter((j) => j.status === 'dispatched' || j.status === 'acknowledged').length,
    assigned: jobs.filter((j) => j.status === 'assigned').length,
  };

  const statusChartData = [
    { name: 'Completed', value: statusCounts.completed, color: '#10b981' }, // emerald
    { name: 'In Progress', value: statusCounts.in_progress, color: '#f59e0b' }, // amber
    { name: 'En Route', value: statusCounts.en_route, color: '#3b82f6' }, // blue
    { name: 'Dispatched', value: statusCounts.dispatched, color: '#8b5cf6' }, // purple
    { name: 'Assigned', value: statusCounts.assigned, color: '#6366f1' }, // indigo
  ].filter((d) => d.value > 0);

  // Recharts Data: Technician Workload vs 8.5h Limit (Top 7 on-duty)
  const techWorkloadData = electricians
    .filter((e) => e.status !== 'off_duty')
    .map((e) => ({
      name: e.name.split(' ')[0], // First name for clean axis
      fullName: e.name,
      hours: e.currentWorkload,
      maxLimit: e.maxDailyHours || 8.5,
    }))
    .sort((a, b) => b.hours - a.hours)
    .slice(0, 7);

  // Priority Distribution
  const priorityBreakdown = [
    { name: 'Emergency', count: jobs.filter((j) => j.priority === 'emergency').length, color: 'bg-rose-500', text: 'text-rose-600', bg: 'bg-rose-50' },
    { name: 'High', count: jobs.filter((j) => j.priority === 'high').length, color: 'bg-amber-500', text: 'text-amber-600', bg: 'bg-amber-50' },
    { name: 'Medium', count: jobs.filter((j) => j.priority === 'medium').length, color: 'bg-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' },
    { name: 'Low', count: jobs.filter((j) => j.priority === 'low').length, color: 'bg-emerald-500', text: 'text-emerald-600', bg: 'bg-emerald-50' },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner: Mysuru Grid Supervision Status */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 p-6 rounded-2xl text-white shadow-xl relative overflow-hidden border border-slate-800">
        <div className="absolute right-0 top-0 bottom-0 w-96 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-500/10 via-indigo-500/5 to-transparent pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Live Supervision Active
              </span>
              <span className="text-xs text-blue-300 font-semibold">
                Mysuru Distribution Circle (CHESCOM)
              </span>
              <span className="text-xs text-slate-400">• Monitoring Only Mode</span>
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight">
              Grid Operations Monitor • {user?.name || 'Meera Kulkarni'}
            </h1>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Supervising automated AI dispatch across 20 Mysuru distribution feeders. Read-only supervision of autonomous candidate scoring, continuous telemetry, and self-healing disruption recovery.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsDemoModalOpen(true)}
              className="px-4 py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md shadow-orange-600/30 transition"
            >
              <Zap className="w-3.5 h-3.5 fill-current" />
              <span>Simulate Disruption</span>
            </button>
            <button
              onClick={() => navigate('/supervisor/workforce')}
              className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl text-xs font-semibold flex items-center gap-2 border border-white/15 transition"
            >
              <Calendar className="w-3.5 h-3.5 text-blue-300" />
              <span>Gantt Timeline</span>
            </button>
            <button
              onClick={() => navigate('/supervisor/map')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md shadow-blue-600/30 transition"
            >
              <Radio className="w-3.5 h-3.5" />
              <span>Full Fleet Map</span>
            </button>
          </div>
        </div>

        {/* Live Operational Metrics Ribbon */}
        <div className="mt-5 pt-4 border-t border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <span className="text-slate-400 block text-[11px]">Automated Dispatch Pipeline</span>
            <span className="font-bold text-emerald-400 flex items-center gap-1 mt-0.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> 100% Autonomous
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[11px]">Active Disruptions Auto-Handled</span>
            <span className="font-bold text-amber-300 flex items-center gap-1 mt-0.5">
              <Activity className="w-3.5 h-3.5" /> {disruptions.filter((d) => d.status === 'detected' || d.status === 'analyzing').length} in auto-recovery
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[11px]">Emergency Outages</span>
            <span className="font-bold text-rose-300 flex items-center gap-1 mt-0.5">
              <AlertTriangle className="w-3.5 h-3.5" /> {emergencyJobs.length} active (45m SLA)
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[11px]">Field Fleet Coverage</span>
            <span className="font-bold text-blue-300 flex items-center gap-1 mt-0.5">
              <HardHat className="w-3.5 h-3.5" /> {onDutyTechs.length} Technicians Deployed
            </span>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Active Field Work"
          value={activeJobs.length}
          icon={Activity}
          description="In-progress or dispatched"
          trend="up"
          change={`${activeJobs.length} active`}
          iconColor="text-blue-600"
          bgColor="bg-blue-50"
        />
        <KPICard
          title="Technician Availability"
          value={`${availableTechs.length} / ${electricians.length}`}
          icon={HardHat}
          description={`${availableTechs.length} ready for dispatch`}
          iconColor="text-emerald-600"
          bgColor="bg-emerald-50"
        />
        <KPICard
          title="SLA Adherence Rate"
          value="98.4%"
          icon={ShieldCheck}
          description="Mysuru Circle benchmark"
          trend="up"
          change="+1.2% this week"
          iconColor="text-indigo-600"
          bgColor="bg-indigo-50"
        />
        <KPICard
          title="Completed Today"
          value={completedTodayJobs.length}
          icon={CheckCircle2}
          description="Verified sign-off reports"
          iconColor="text-teal-600"
          bgColor="bg-teal-50"
        />
      </div>

      {/* AI Intelligence & Predictive Risk Section */}
      <AIInsightsPanel jobs={jobs} electricians={electricians} />

      {/* Visual Analytics Section: Recharts Visualizations */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart 1: Job Status Distribution (Donut Chart) */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <PieIcon className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-extrabold text-slate-900">Job Status Distribution</h3>
            </div>
            <span className="text-[11px] font-bold text-slate-500">{jobs.length} total tickets</span>
          </div>

          <div className="h-48 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusChartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={45}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {statusChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: number, name: string) => [`${val} jobs`, name]}
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs">
            {statusChartData.map((item) => (
              <div key={item.name} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: item.color }} />
                <span className="text-slate-600 truncate">{item.name}:</span>
                <span className="font-bold text-slate-900 ml-auto">{item.value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Chart 2: Technician Workload vs 8.5h Limit */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <BarChart3 className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-extrabold text-slate-900">Workload Balance (Hours)</h3>
            </div>
            <span className="text-[11px] font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
              Limit: 8.5h
            </span>
          </div>

          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={techWorkloadData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis domain={[0, 9]} tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <Tooltip
                  formatter={(val: number) => [`${val} hrs logged`, 'Workload']}
                  labelFormatter={(name) => {
                    const tech = techWorkloadData.find((t) => t.name === name);
                    return tech ? tech.fullName : name;
                  }}
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }}
                />
                <Bar dataKey="hours" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <p className="text-[11px] text-slate-500 pt-2 border-t border-slate-100 flex items-center justify-between">
            <span>Autonomous load balancing prevents technician overtime.</span>
            <button
              onClick={() => navigate('/supervisor/workforce')}
              className="text-indigo-600 font-bold hover:underline"
            >
              View Fleet →
            </button>
          </p>
        </div>

        {/* Breakdown 3: Priority & SLA Status */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
                <AlertTriangle className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-extrabold text-slate-900">Ticket Priority Breakdown</h3>
            </div>
            <span className="text-[11px] font-bold text-emerald-600">SLA 98.4%</span>
          </div>

          <div className="space-y-3 my-auto py-2">
            {priorityBreakdown.map((p) => {
              const pct = jobs.length > 0 ? Math.round((p.count / jobs.length) * 100) : 0;
              return (
                <div key={p.name} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full ${p.color}`} />
                      {p.name} Priority
                    </span>
                    <span className="font-bold text-slate-900">
                      {p.count} <span className="text-slate-400 font-normal">({pct}%)</span>
                    </span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${p.color} transition-all duration-500 rounded-full`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
            <span className="text-slate-500 text-[11px]">Emergency SLA response target: 45 min</span>
            <button
              onClick={() => navigate('/supervisor/jobs')}
              className="text-blue-600 font-bold hover:underline"
            >
              Job Grid →
            </button>
          </div>
        </div>
      </div>

      {/* Central Interactive Map Preview */}
      <div className="bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
        <div className="p-4 sm:px-6 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold text-slate-900">
                Mysuru Field Fleet & Job Telemetry Map
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">
                LIVE TELEMETRY
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Interactive Leaflet view • Centered on Mysuru (`12.2958° N, 76.6394° E`)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-500 hidden md:inline">
              Simulated Demo Locations • Mysuru Grid Telemetry
            </span>
            <button
              onClick={() => navigate('/supervisor/map')}
              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition"
            >
              <span>Expand Map</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4">
          <div className="lg:col-span-3">
            <LeafletMap
              electricians={electricians}
              jobs={activeJobs}
              selectedElectricianId={selectedElectrician?.id}
              selectedJobId={selectedJob?.id}
              onSelectElectrician={(tech) => setSelectedElectrician(tech)}
              onSelectJob={(job) => setSelectedJob(job)}
              height="440px"
            />
          </div>

          {/* Right Sidebar: Quick Inspector */}
          <div className="p-4 border-t lg:border-t-0 lg:border-l border-slate-200 bg-slate-50/60 overflow-y-auto max-h-[440px] space-y-4">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Telemetry Inspector
            </div>

            {selectedElectrician ? (
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-2.5">
                <div className="flex items-center gap-3">
                  <Avatar
                    src={selectedElectrician.avatar}
                    name={selectedElectrician.name}
                    size="md"
                  />
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">{selectedElectrician.name}</h4>
                    <span className="text-[11px] font-mono text-slate-500 block">
                      {selectedElectrician.employeeId}
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5 text-xs text-slate-600 pt-2 border-t border-slate-100">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Duty Status:</span>
                    <span className="font-bold capitalize text-slate-800">
                      {selectedElectrician.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Today's Workload:</span>
                    <span className="font-semibold text-slate-800">
                      {selectedElectrician.currentWorkload}h / {selectedElectrician.maxDailyHours}h
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Last GPS Ping:</span>
                    <span className="font-semibold text-slate-800">
                      {formatTimeIST(selectedElectrician.currentLocation.lastUpdated)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Customer Rating:</span>
                    <span className="font-bold text-amber-600">
                      ★ {selectedElectrician.rating}
                    </span>
                  </div>
                </div>

                <div className="pt-2">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                    Certifications:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {selectedElectrician.certifications.slice(0, 2).map((c, i) => (
                      <span key={i} className="text-[10px] bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded border border-blue-200">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ) : selectedJob ? (
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold text-blue-600">{selectedJob.id}</span>
                  <PriorityBadge priority={selectedJob.priority} />
                </div>
                <h4 className="text-sm font-bold text-slate-900 leading-snug">{selectedJob.title}</h4>
                <div className="space-y-1.5 text-xs text-slate-600 pt-2 border-t border-slate-100">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Status:</span>
                    <StatusBadge status={selectedJob.status} size="sm" />
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Customer:</span>
                    <span className="font-semibold text-slate-800">{selectedJob.customerName}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Assigned Tech:</span>
                    <span className="font-bold text-slate-900">
                      {selectedJob.assignedElectricianName || 'Unassigned'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Locality:</span>
                    <span className="font-semibold text-slate-800 truncate max-w-[120px]">
                      {selectedJob.location.address}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-slate-400 text-xs">
                <MapPin className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p>Click any technician or active job marker on the map to inspect live telemetry.</p>
              </div>
            )}

            {/* Quick Filter Counters */}
            <div className="pt-2 border-t border-slate-200 space-y-1.5 text-xs">
              <div className="flex justify-between text-slate-600">
                <span>Available Technicians:</span>
                <span className="font-bold text-emerald-600">{availableTechs.length}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>En Route to Site:</span>
                <span className="font-bold text-sky-600">
                  {electricians.filter((e) => e.status === 'en_route').length}
                </span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>On-Site Busy:</span>
                <span className="font-bold text-amber-600">
                  {electricians.filter((e) => e.status === 'busy').length}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Section: Live Automated Dispatch Feed + Live System Disruption/Audit Stream */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Stream 1: Recent Automated Scheduling Decisions */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Cpu className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">
                  Automated Scheduling Decisions
                </h3>
                <p className="text-[11px] text-slate-500">Autonomous multi-criteria optimization feed</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/supervisor/scheduling')}
              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              <span>View All Runs</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {recentAutoAssignments.map((j) => (
              <div key={j.id} className="py-3 flex items-center justify-between gap-3 text-xs">
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-600">{j.id}</span>
                    <PriorityBadge priority={j.priority} />
                    <span className="px-1.5 py-0.2 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded text-[10px] font-bold">
                      Auto-Assigned
                    </span>
                  </div>
                  <p className="font-bold text-slate-900 truncate">{j.title}</p>
                  <p className="text-slate-500 text-[11px] truncate">
                    {j.location.address} • Tech: <span className="font-semibold text-slate-800">{j.assignedElectricianName}</span>
                  </p>
                </div>

                <div className="text-right flex-shrink-0">
                  <span className="inline-block px-2 py-0.5 rounded font-bold bg-blue-50 text-blue-700 border border-blue-200 text-xs">
                    Score: 92%
                  </span>
                  <span className="block text-[10px] text-slate-400 mt-0.5">
                    {formatTimeIST(j.createdAt)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Stream 2: Live Operational Audit & Disruption Event Stream */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                <History className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">
                  Live Operations & Disruption Event Stream
                </h3>
                <p className="text-[11px] text-slate-500">Autonomous engine & field event telemetry</p>
              </div>
            </div>
            <button
              onClick={() => navigate('/supervisor/audit')}
              className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              <span>Full Audit Log</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {recentAuditEvents.map((event) => (
              <div key={event.id} className="py-2.5 flex items-start justify-between gap-3 text-xs">
                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-bold text-slate-800">{event.userName}</span>
                    <span className="text-[10px] text-slate-400 font-mono">({event.userRole})</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-600">
                      {event.entityType}
                    </span>
                  </div>
                  <p className="text-slate-700 font-medium leading-tight">
                    {event.action.replace(/_/g, ' ')}
                  </p>
                  {event.reason && (
                    <p className="text-slate-400 text-[11px] truncate max-w-sm">
                      {event.reason}
                    </p>
                  )}
                </div>

                <div className="text-right flex-shrink-0">
                  <span className="text-[11px] text-slate-500 block font-mono">
                    {formatDateTimeIST(event.timestamp).split(',')[1]?.trim() || formatTimeIST(event.timestamp)}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {formatDateTimeIST(event.timestamp).split(',')[0]}
                  </span>
                </div>
              </div>
            ))}

            {recentAuditEvents.length === 0 && (
              <div className="py-8 text-center text-slate-400 text-xs">
                <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-1" />
                <p>No recent audit records found.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Demo Scenario Runner Modal */}
      <DemoScenarioRunnerModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
      />
    </div>
  );
};
