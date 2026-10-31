import React, { useState } from 'react';
import { Electrician, Job } from '../../../types';
import { useAuth } from '../../../context/AuthContext';
import { useApp } from '../../../context/AppContext';
import { api } from '../../../services/api/apiClient';
import { MYSURU_LOCALITIES } from '../../../data/seedData';
import { Avatar } from '../../../components/common/Avatar';
import {
  Users,
  HardHat,
  Search,
  Plus,
  Filter,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Phone,
  Mail,
  MapPin,
  ShieldCheck,
  Key,
  Copy,
  Edit,
  Eye,
  Trash2,
  X,
  Check,
  Star,
  Activity,
  UserCheck,
  UserX,
  AlertCircle,
  Briefcase,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface SupervisorElectricianManagementProps {
  onClose?: () => void;
}

const AVAILABLE_SKILLS = [
  'Residential Wiring',
  'Commercial Lighting',
  'High Voltage Systems',
  'Panel & Breaker Upgrades',
  'Switchgear Maintenance',
  'Solar & Inverter Systems',
  'EV Charging Stations',
  'Cable Fault Diagnostics',
  'Thermal Imaging Inspection',
  'Emergency Generators',
  'Industrial Wiring',
  'Smart Energy Metering',
];

export const SupervisorElectricianManagement: React.FC<SupervisorElectricianManagementProps> = ({
  onClose,
}) => {
  const { user } = useAuth();
  const { electricians, jobs, refreshData } = useApp();

  const [searchQuery, setSearchQuery] = useState('');
  const [availabilityFilter, setAvailabilityFilter] = useState('all');
  const [accountStatusFilter, setAccountStatusFilter] = useState('all');
  const [skillFilter, setSkillFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [viewingTech, setViewingTech] = useState<Electrician | null>(null);
  const [editingTech, setEditingTech] = useState<Electrician | null>(null);
  const [statusActionTech, setStatusActionTech] = useState<{
    tech: Electrician;
    nextStatus: 'active' | 'inactive' | 'suspended';
  } | null>(null);
  const [createdCredentials, setCreatedCredentials] = useState<{
    tech: Electrician;
    tempPassword: string;
  } | null>(null);
  const [resetPasswordResult, setResetPasswordResult] = useState<{
    tech: Electrician;
    tempPassword: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);

  // New Electrician Form State
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '+91 98450 ',
    registeredAddress: 'Saraswathipuram, Mysuru',
    skills: ['Residential Wiring', 'Commercial Lighting'] as string[],
    certifications: 'Certified Electrical Safety Inspector',
    experienceYears: 4,
    emergencyContact: '+91 98450 00000',
    shift: 'morning',
  });

  // Filter electricians
  const filteredElectricians = electricians.filter((e) => {
    if (availabilityFilter !== 'all' && e.status !== availabilityFilter) return false;
    const acStatus = e.accountStatus || 'active';
    if (accountStatusFilter !== 'all' && acStatus !== accountStatusFilter) return false;
    if (skillFilter !== 'all' && !e.skills.some((s) => s.toLowerCase() === skillFilter.toLowerCase())) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchName = e.name.toLowerCase().includes(q);
      const matchId = e.employeeId.toLowerCase().includes(q) || e.id.toLowerCase().includes(q);
      const matchLoc = (e.registeredAddress || '').toLowerCase().includes(q);
      const matchSkill = e.skills.some((s) => s.toLowerCase().includes(q));
      if (!matchName && !matchId && !matchLoc && !matchSkill) return false;
    }
    return true;
  });

  // Pagination
  const totalPages = Math.ceil(filteredElectricians.length / itemsPerPage) || 1;
  const paginatedElectricians = filteredElectricians.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // KPI counts
  const totalCount = electricians.length;
  const activeCount = electricians.filter((e) => (e.accountStatus || 'active') === 'active').length;
  const availableCount = electricians.filter((e) => e.status === 'available').length;
  const busyCount = electricians.filter((e) => e.status === 'busy' || e.status === 'en_route').length;
  const offlineCount = electricians.filter((e) => e.status === 'off_duty' || e.status === 'leave').length;
  const suspendedCount = electricians.filter((e) => e.accountStatus === 'suspended' || e.accountStatus === 'inactive').length;

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    if (!formData.name || !formData.email || !formData.phone) {
      alert('Please fill all required fields');
      return;
    }

    try {
      const res = (await api.addElectrician(
        {
          ...formData,
          certifications: [formData.certifications],
        },
        user
      )) as unknown as { electrician: Electrician; tempPassword: string };

      setIsAddModalOpen(false);
      setCreatedCredentials({
        tech: res.electrician,
        tempPassword: res.tempPassword,
      });
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Error hiring electrician');
    }
  };

  const handleStatusChange = (tech: Electrician, nextStatus: 'active' | 'inactive' | 'suspended') => {
    if (!user) return;
    try {
      api.updateElectricianAccountStatus(tech.id, nextStatus, user);
      setStatusActionTech(null);
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Failed to update status');
    }
  };

  const handleResetPassword = (tech: Electrician) => {
    if (!user) return;
    try {
      const tempPass = api.resetElectricianPassword(tech.id, user) as unknown as string;
      setResetPasswordResult({ tech, tempPassword: tempPass });
      refreshData();
    } catch (err: any) {
      alert(err.message || 'Error resetting password');
    }
  };

  const handleCopyCredentials = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-5">
      {/* Top Banner & Hiring Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-950 p-5 sm:p-6 rounded-2xl text-white shadow-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-blue-500/20 text-blue-300 border border-blue-500/30">
              Fleet Workforce Management
            </span>
            <span className="text-xs text-slate-400 font-mono">Mysuru Division (20+ Scale)</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-black mt-1">
            Electrician Hiring & Fleet Operations
          </h2>
          <p className="text-xs text-slate-300 max-w-xl mt-1 leading-relaxed">
            Hire new field technicians with auto-generated temporary credentials, configure skill certifications, manage duty & account statuses, and maintain assignment eligibility.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-extrabold rounded-xl text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/30 transition transform active:scale-95 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>+ Add Electrician</span>
          </button>
        </div>
      </div>

      {/* KPI Status Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Fleet</span>
          <span className="text-xl font-black text-slate-900 mt-0.5 block">{totalCount}</span>
          <span className="text-[10px] text-slate-500">Registered Technicians</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Active Accounts</span>
          <span className="text-xl font-black text-emerald-700 mt-0.5 block">{activeCount}</span>
          <span className="text-[10px] text-emerald-600 font-semibold">Eligible for Auto-Dispatch</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Available (Ready)</span>
          <span className="text-xl font-black text-blue-600 mt-0.5 block">{availableCount}</span>
          <span className="text-[10px] text-blue-500">Awaiting 60s Offers</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Busy / En Route</span>
          <span className="text-xl font-black text-amber-600 mt-0.5 block">{busyCount}</span>
          <span className="text-[10px] text-slate-500">On Active Repair Jobs</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Offline / Leave</span>
          <span className="text-xl font-black text-slate-600 mt-0.5 block">{offlineCount}</span>
          <span className="text-[10px] text-slate-400">Off Shift</span>
        </div>
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <span className="text-[10px] uppercase font-bold text-slate-400 block">Suspended / Inactive</span>
          <span className="text-xl font-black text-rose-600 mt-0.5 block">{suspendedCount}</span>
          <span className="text-[10px] text-rose-500">Dispatch Restricted</span>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search by name, employee ID (e.g. MYS-TECH-101), locality, or skill..."
              className="w-full pl-9 pr-4 py-2 text-xs border border-slate-200 rounded-xl bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={availabilityFilter}
              onChange={(e) => {
                setAvailabilityFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700"
            >
              <option value="all">All Availability</option>
              <option value="available">Available Only</option>
              <option value="busy">Busy / On-Site</option>
              <option value="en_route">En Route</option>
              <option value="off_duty">Off Duty</option>
            </select>

            <select
              value={accountStatusFilter}
              onChange={(e) => {
                setAccountStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700"
            >
              <option value="all">All Account Statuses</option>
              <option value="active">Active Accounts</option>
              <option value="inactive">Inactive</option>
              <option value="suspended">Suspended</option>
            </select>

            <select
              value={skillFilter}
              onChange={(e) => {
                setSkillFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="px-3 py-2 text-xs border border-slate-200 rounded-xl bg-white font-medium text-slate-700"
            >
              <option value="all">All Skills</option>
              {AVAILABLE_SKILLS.map((sk) => (
                <option key={sk} value={sk}>
                  {sk}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Electricians Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-4">Technician</th>
                <th className="py-3 px-4">Contact Info</th>
                <th className="py-3 px-4">Skills & Certifications</th>
                <th className="py-3 px-4">Locality / GPS</th>
                <th className="py-3 px-4">Duty Status</th>
                <th className="py-3 px-4">Account Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {paginatedElectricians.map((tech) => {
                const acStatus = tech.accountStatus || 'active';
                const activeJob = tech.currentJobId ? jobs.find((j) => j.id === tech.currentJobId) : null;

                return (
                  <tr key={tech.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2.5">
                        <Avatar name={tech.name} src={tech.avatar} size="sm" />
                        <div>
                          <div className="font-extrabold text-slate-900">{tech.name}</div>
                          <span className="font-mono text-[10px] text-slate-400 block">{tech.employeeId}</span>
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="text-slate-800 font-medium">{tech.phone}</div>
                      <div className="text-slate-400 text-[11px] truncate max-w-[150px]">{tech.email}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1 max-w-[200px]">
                        {tech.skills.slice(0, 2).map((s, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200"
                          >
                            {s}
                          </span>
                        ))}
                        {tech.skills.length > 2 && (
                          <span className="text-[10px] text-slate-400 font-bold">
                            +{tech.skills.length - 2} more
                          </span>
                        )}
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1 font-semibold text-slate-800 truncate max-w-[160px]">
                        <MapPin className="w-3 h-3 text-rose-600 flex-shrink-0" />
                        <span className="truncate">{tech.registeredAddress || 'Mysuru Circle'}</span>
                      </div>
                      <span className="text-[10px] text-slate-400 block">
                        GPS: {tech.currentLocation?.lat.toFixed(3)}, {tech.currentLocation?.lng.toFixed(3)}
                      </span>
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold capitalize ${
                          tech.status === 'available'
                            ? 'bg-emerald-100 text-emerald-800'
                            : tech.status === 'busy'
                            ? 'bg-amber-100 text-amber-800'
                            : tech.status === 'en_route'
                            ? 'bg-sky-100 text-sky-800'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        <span
                          className={`w-1.5 h-1.5 rounded-full ${
                            tech.status === 'available'
                              ? 'bg-emerald-500'
                              : tech.status === 'busy'
                              ? 'bg-amber-500 animate-pulse'
                              : 'bg-slate-400'
                          }`}
                        />
                        {tech.status.replace('_', ' ')}
                      </span>
                      {activeJob && (
                        <span className="block text-[10px] text-slate-400 font-mono mt-0.5">
                          Job: {activeJob.id}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded-md text-[10px] font-extrabold uppercase ${
                          acStatus === 'active'
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                            : acStatus === 'suspended'
                            ? 'bg-rose-50 text-rose-800 border border-rose-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {acStatus}
                      </span>
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => setViewingTech(tech)}
                          className="p-1.5 text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition cursor-pointer"
                          title="View Full Profile"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>

                        <button
                          type="button"
                          onClick={() => setEditingTech(tech)}
                          className="p-1.5 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition cursor-pointer"
                          title="Edit Electrician Info"
                        >
                          <Edit className="w-3.5 h-3.5" />
                        </button>

                        <button
                          type="button"
                          onClick={() => handleResetPassword(tech)}
                          className="p-1.5 text-slate-600 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition cursor-pointer"
                          title="Generate New Temporary Password"
                        >
                          <Key className="w-3.5 h-3.5" />
                        </button>

                        {acStatus === 'active' ? (
                          <button
                            type="button"
                            onClick={() => setStatusActionTech({ tech, nextStatus: 'suspended' })}
                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                            title="Suspend Technician Account"
                          >
                            <UserX className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setStatusActionTech({ tech, nextStatus: 'active' })}
                            className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition cursor-pointer"
                            title="Activate Technician Account"
                          >
                            <UserCheck className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}

              {paginatedElectricians.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-10 text-center text-slate-400">
                    No electricians found matching your query.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
            {Math.min(currentPage * itemsPerPage, filteredElectricians.length)} of {filteredElectricians.length} technicians
          </span>

          <div className="flex items-center gap-1">
            <button
              disabled={currentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 transition cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 font-bold text-slate-700">
              Page {currentPage} of {totalPages}
            </span>
            <button
              disabled={currentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40 transition cursor-pointer"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* ================= MODAL 1: ADD ELECTRICIAN ================= */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-scale-in">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-900 to-indigo-950 text-white">
              <div className="flex items-center gap-2">
                <HardHat className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-extrabold">Hire & Register New Electrician</h3>
              </div>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="w-7 h-7 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g. Nagaraj Rao"
                    className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="nagaraj.r@dispatchgrid.io"
                    className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">Phone Contact *</label>
                  <input
                    type="text"
                    required
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+91 98450 31050"
                    className="w-full p-2.5 border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">Registered Locality *</label>
                  <select
                    value={formData.registeredAddress}
                    onChange={(e) => setFormData({ ...formData, registeredAddress: e.target.value })}
                    className="w-full p-2.5 border border-slate-200 rounded-xl bg-white"
                  >
                    {MYSURU_LOCALITIES.map((loc) => (
                      <option key={loc.name} value={`${loc.name}, Mysuru`}>
                        {loc.name} (Pin: {loc.postalCode})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="font-bold text-slate-700 block mb-1">Electrical Skills & Specializations *</label>
                <div className="flex flex-wrap gap-1.5 p-3 bg-slate-50 border border-slate-200 rounded-xl">
                  {AVAILABLE_SKILLS.map((sk) => {
                    const isSelected = formData.skills.includes(sk);
                    return (
                      <button
                        type="button"
                        key={sk}
                        onClick={() => {
                          if (isSelected) {
                            setFormData({
                              ...formData,
                              skills: formData.skills.filter((s) => s !== sk),
                            });
                          } else {
                            setFormData({
                              ...formData,
                              skills: [...formData.skills, sk],
                            });
                          }
                        }}
                        className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition cursor-pointer ${
                          isSelected
                            ? 'bg-blue-600 text-white shadow-2xs'
                            : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100'
                        }`}
                      >
                        {sk}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="font-bold text-slate-700 block mb-1">Experience (Years)</label>
                  <input
                    type="number"
                    min="1"
                    max="40"
                    value={formData.experienceYears}
                    onChange={(e) => setFormData({ ...formData, experienceYears: parseInt(e.target.value, 10) || 1 })}
                    className="w-full p-2.5 border border-slate-200 rounded-xl"
                  />
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">Work Shift</label>
                  <select
                    value={formData.shift}
                    onChange={(e) => setFormData({ ...formData, shift: e.target.value })}
                    className="w-full p-2.5 border border-slate-200 rounded-xl bg-white"
                  >
                    <option value="morning">Morning (08:00 - 16:30)</option>
                    <option value="afternoon">Afternoon (12:00 - 20:30)</option>
                    <option value="night">Night (20:00 - 04:30)</option>
                    <option value="flexible">Flexible</option>
                  </select>
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">Emergency Contact</label>
                  <input
                    type="text"
                    value={formData.emergencyContact}
                    onChange={(e) => setFormData({ ...formData, emergencyContact: e.target.value })}
                    className="w-full p-2.5 border border-slate-200 rounded-xl"
                  />
                </div>
              </div>

              <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-indigo-900 space-y-1">
                <span className="font-bold flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5 text-indigo-600" />
                  Automatic Temporary Password Generation
                </span>
                <p className="text-[11px] text-indigo-800">
                  A high-entropy temporary password will be generated automatically. You can copy and share the credentials immediately upon registration. The technician will be prompted to change their password on first login.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-xl cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-extrabold rounded-xl shadow-md cursor-pointer"
                >
                  Complete Registration & Generate Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL 2: CREATED CREDENTIALS SUCCESS ================= */}
      {createdCredentials && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-2xl border border-slate-200 space-y-4 animate-scale-in">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-2xl mx-auto flex items-center justify-center shadow-md">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h3 className="text-base font-black text-slate-900">Electrician Successfully Registered!</h3>
              <p className="text-xs text-slate-500">
                {createdCredentials.tech.name} ({createdCredentials.tech.employeeId}) is now active and eligible for automated assignment.
              </p>
            </div>

            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Employee ID:</span>
                <span className="font-bold font-mono text-slate-900">{createdCredentials.tech.employeeId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Login Email:</span>
                <span className="font-bold text-slate-900">{createdCredentials.tech.email}</span>
              </div>
              <div className="flex justify-between items-center border-t border-slate-200/80 pt-2">
                <span className="text-slate-500">Temporary Password:</span>
                <span className="font-mono font-black text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                  {createdCredentials.tempPassword}
                </span>
              </div>
            </div>

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-[11px] text-amber-900">
              * Share these temporary credentials with the electrician. They will be prompted to update their password upon initial login.
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() =>
                  handleCopyCredentials(
                    `ElectroGrid Technician Credentials\nName: ${createdCredentials.tech.name}\nEmployee ID: ${createdCredentials.tech.employeeId}\nEmail: ${createdCredentials.tech.email}\nTemp Password: ${createdCredentials.tempPassword}\nPortal: https://elctrogrid.vercel.app/login`
                  )
                }
                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 shadow-sm cursor-pointer"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
                <span>{copied ? 'Copied to Clipboard!' : 'Copy Credentials'}</span>
              </button>
              <button
                type="button"
                onClick={() => setCreatedCredentials(null)}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl font-bold text-xs cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL 3: VIEW PROFILE ================= */}
      {viewingTech && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-lg rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-scale-in">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-900 text-white">
              <h3 className="text-base font-extrabold flex items-center gap-2">
                <HardHat className="w-5 h-5 text-blue-400" />
                <span>Electrician Master Profile</span>
              </h3>
              <button onClick={() => setViewingTech(null)} className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto text-xs">
              <div className="flex items-center gap-3">
                <Avatar name={viewingTech.name} src={viewingTech.avatar} size="lg" />
                <div>
                  <h4 className="text-base font-extrabold text-slate-900">{viewingTech.name}</h4>
                  <span className="font-mono text-xs font-bold text-slate-500">{viewingTech.employeeId}</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-amber-500 font-bold flex items-center gap-1">
                      <Star className="w-3.5 h-3.5 fill-current" /> ★ {viewingTech.rating || 5.0}
                    </span>
                    <span className="text-slate-400">•</span>
                    <span className="text-slate-600 font-bold">{viewingTech.jobsCompletedTotal || 0} completed repairs</span>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Duty Status</span>
                  <div className="font-bold text-slate-800 capitalize mt-0.5">{viewingTech.status.replace('_', ' ')}</div>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Account Status</span>
                  <div className="font-bold text-slate-800 uppercase mt-0.5">{viewingTech.accountStatus || 'active'}</div>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Shift Window</span>
                  <div className="font-bold text-slate-800 capitalize mt-0.5">{viewingTech.shift} (08:00 - 16:30)</div>
                </div>
                <div>
                  <span className="text-[10px] uppercase font-bold text-slate-400">Daily Workload</span>
                  <div className="font-bold text-slate-800 mt-0.5">{viewingTech.currentWorkload}h / {viewingTech.maxDailyHours}h</div>
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Certified Specializations</span>
                <div className="flex flex-wrap gap-1">
                  {viewingTech.skills.map((s, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-1">Registered Locality</span>
                <div className="flex items-center gap-1.5 text-slate-800 font-medium">
                  <MapPin className="w-4 h-4 text-rose-600" />
                  <span>{viewingTech.registeredAddress || 'Mysuru Circle HQ'}</span>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => setViewingTech(null)}
                className="px-4 py-2 bg-slate-800 text-white rounded-xl text-xs font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL 4: RESET PASSWORD RESULT ================= */}
      {resetPasswordResult && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-sm rounded-2xl p-5 shadow-2xl border border-slate-200 space-y-4 animate-scale-in text-center">
            <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center mx-auto">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-slate-900">New Temporary Password Generated</h3>
              <p className="text-xs text-slate-500 mt-0.5">For {resetPasswordResult.tech.name}</p>
            </div>

            <div className="p-3 bg-slate-50 rounded-xl font-mono text-sm font-black text-indigo-700 border border-slate-200">
              {resetPasswordResult.tempPassword}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => handleCopyCredentials(resetPasswordResult.tempPassword)}
                className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold"
              >
                {copied ? 'Copied!' : 'Copy Password'}
              </button>
              <button
                type="button"
                onClick={() => setResetPasswordResult(null)}
                className="px-3.5 py-2 bg-slate-100 text-slate-700 rounded-xl text-xs font-bold"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= MODAL 5: STATUS CHANGE CONFIRMATION ================= */}
      {statusActionTech && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white w-full max-w-md rounded-2xl p-5 shadow-2xl border border-slate-200 space-y-3 animate-scale-in">
            <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-600" />
              <span>Confirm Account Status Update</span>
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Are you sure you want to change account status for{' '}
              <span className="font-bold text-slate-900">{statusActionTech.tech.name}</span> to{' '}
              <span className="font-black uppercase text-indigo-700">{statusActionTech.nextStatus}</span>?
            </p>
            {statusActionTech.nextStatus === 'suspended' && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-[11px]">
                * Suspending this account will immediately remove the technician from the 60s automatic assignment candidate pool. Existing historical job records will remain intact.
              </div>
            )}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setStatusActionTech(null)}
                className="px-3 py-1.5 text-xs font-bold text-slate-600 hover:bg-slate-100 rounded-lg cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => handleStatusChange(statusActionTech.tech, statusActionTech.nextStatus)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold shadow-xs cursor-pointer"
              >
                Confirm Update
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
