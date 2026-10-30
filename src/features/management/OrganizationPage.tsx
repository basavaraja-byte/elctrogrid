import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { User, UserRole } from '../../types';
import { DataTable, Column } from '../../components/common/DataTable';
import { Modal } from '../../components/common/Modal';
import {
  Building2,
  Users,
  UserPlus,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Edit,
  Mail,
  Phone,
} from 'lucide-react';

export const OrganizationPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const { refreshData } = useApp();

  const [isAddUserOpen, setIsAddUserOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  // Form fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState<UserRole>('electrician');
  const [department, setDepartment] = useState('Regional Field Crew');

  const [localUsers, setLocalUsers] = useState<User[]>([]);

  React.useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    const list = await api.getUsers();
    setLocalUsers(list);
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) return;

    await api.addUser({
      name,
      email,
      phone,
      role,
      department,
      active: true,
    });

    loadUsers();
    refreshData();
    setIsAddUserOpen(false);
    setName('');
    setEmail('');
  };

  const handleToggleActive = async (u: User) => {
    await api.updateUser(u.id, { active: !u.active });
    loadUsers();
    refreshData();
  };

  const columns: Column<User>[] = [
    {
      header: 'Employee / User',
      cell: (u) => (
        <div className="flex items-center gap-2.5">
          <img
            src={u.avatar || 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100'}
            alt={u.name}
            className="w-9 h-9 rounded-full object-cover border border-slate-200"
          />
          <div>
            <span className="font-bold text-slate-900 block">{u.name}</span>
            <span className="text-[11px] text-slate-500">{u.email}</span>
          </div>
        </div>
      ),
    },
    {
      header: 'Role Context',
      cell: (u) => {
        const roleColors: Record<string, string> = {
          management: 'bg-rose-100 text-rose-800',
          operations: 'bg-emerald-100 text-emerald-800',
          supervisor: 'bg-emerald-100 text-emerald-800',
          dispatcher: 'bg-purple-100 text-purple-800',
          electrician: 'bg-amber-100 text-amber-800',
          technician: 'bg-amber-100 text-amber-800',
          customer: 'bg-blue-100 text-blue-800',
        };
        const color = roleColors[u.role] || 'bg-slate-100 text-slate-700';

        return (
          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize ${color}`}>
            {u.role.replace('_', ' ')}
          </span>
        );
      },
    },
    {
      header: 'Department / Division',
      cell: (u) => (
        <span className="text-xs text-slate-600 font-medium">
          {u.department || (u.companyName ? u.companyName : 'Customer Portal Account')}
        </span>
      ),
    },
    {
      header: 'Phone Contact',
      cell: (u) => <span className="text-xs text-slate-500">{u.phone}</span>,
    },
    {
      header: 'Status',
      cell: (u) => (
        <span
          className={`inline-flex items-center gap-1 text-xs font-bold ${
            u.active ? 'text-emerald-700' : 'text-slate-400'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${u.active ? 'bg-emerald-500' : 'bg-slate-300'}`}
          />
          {u.active ? 'Active' : 'Suspended'}
        </span>
      ),
    },
    {
      header: 'Controls',
      cell: (u) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleToggleActive(u);
          }}
          className={`px-2.5 py-1 text-xs font-semibold rounded transition ${
            u.active
              ? 'bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-600'
              : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
          }`}
        >
          {u.active ? 'Deactivate' : 'Activate'}
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Organization & User Directory
          </h1>
          <p className="text-sm text-slate-500">
            Manage employee identities, role-based security clearance, and customer organizational accounts
          </p>
        </div>

        <button
          onClick={() => setIsAddUserOpen(true)}
          className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center gap-2 self-start sm:self-auto transition"
        >
          <UserPlus className="w-4 h-4" />
          <span>Provision New User</span>
        </button>
      </div>

      <DataTable
        columns={columns}
        data={localUsers}
        searchPlaceholder="Search name, email, department, or role..."
        searchFilter={(item, query) =>
          Boolean(
            item.name.toLowerCase().includes(query) ||
            item.email.toLowerCase().includes(query) ||
            item.role.toLowerCase().includes(query) ||
            (item.department && item.department.toLowerCase().includes(query))
          )
        }
        filterOptions={[
          {
            label: 'Role',
            key: 'role',
            options: [
              { label: 'Management', value: 'management' },
              { label: 'Operations', value: 'operations' },
              { label: 'Dispatcher', value: 'dispatcher' },
              { label: 'Electrician', value: 'electrician' },
              { label: 'Customer', value: 'customer' },
            ],
            filterFn: (item, val) => item.role === val,
          },
        ]}
      />

      {/* Add User Modal */}
      <Modal
        isOpen={isAddUserOpen}
        onClose={() => setIsAddUserOpen(false)}
        title="Provision New Organization User"
        subtitle="Add dispatchers, electricians, operations, or customer accounts"
        maxWidth="lg"
      >
        <form onSubmit={handleAddUser} className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Full Name *</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Liam Henderson"
              className="w-full px-3 py-2 border border-slate-200 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Email *</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="liam@dispatchgrid.io"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Phone</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 (512) 555-0144"
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Assigned Role *</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              >
                <option value="electrician">Electrician</option>
                <option value="dispatcher">Dispatcher</option>
                <option value="operations">Operations Manager</option>
                <option value="management">Management</option>
                <option value="customer">Customer</option>
              </select>
            </div>
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Department</label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setIsAddUserOpen(false)}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold shadow-sm"
            >
              Save & Provision Account
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
