import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { Avatar } from '../common/Avatar';
import {
  LayoutDashboard,
  FileText,
  History,
  HardHat,
  MapPin,
  Clock,
  Map,
  Briefcase,
  Users,
  AlertOctagon,
  ScrollText,
  Cpu,
  Radio,
  Zap,
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user, role } = useAuth();
  const { disruptions } = useApp();

  const activeDisruptionsCount = disruptions.filter(
    (d) => d.status === 'detected' || d.status === 'analyzing'
  ).length;

  // Navigation Links definition per role (strictly 3 business roles)
  const getNavSections = () => {
    switch (role) {
      case 'customer':
        return [
          {
            section: 'Customer Portal',
            items: [
              { label: 'Dashboard', path: '/customer/dashboard', icon: LayoutDashboard },
              { label: 'My Service Requests', path: '/customer/requests', icon: FileText },
              { label: 'Service History & Feedback', path: '/customer/history', icon: History },
            ],
          },
        ];

      case 'technician':
      case 'electrician':
        return [
          {
            section: 'Technician Field Portal',
            items: [
              { label: 'My Field Overview', path: '/technician/dashboard', icon: LayoutDashboard },
              { label: 'Assigned Field Jobs', path: '/technician/jobs', icon: HardHat },
              { label: 'Availability & Shift', path: '/technician/availability', icon: Clock },
              { label: 'Mock GPS Telemetry', path: '/technician/location', icon: MapPin },
            ],
          },
        ];

      case 'supervisor':
      case 'operations':
      case 'dispatcher':
      case 'management':
      default:
        return [
          {
            section: 'Grid Operations Supervision',
            items: [
              { label: 'Operational Overview', path: '/supervisor/overview', icon: LayoutDashboard },
              { label: 'Mysuru Fleet Map', path: '/supervisor/map', icon: Map },
              { label: 'Job Monitoring', path: '/supervisor/jobs', icon: Briefcase },
              { label: 'Workforce Monitoring', path: '/supervisor/workforce', icon: Users },
              { label: 'Automated Scheduling Log', path: '/supervisor/scheduling', icon: Cpu },
              {
                label: 'Disruption & Recovery Log',
                path: '/supervisor/recovery',
                icon: AlertOctagon,
                badge: activeDisruptionsCount > 0 ? activeDisruptionsCount : undefined,
                badgeColor: 'bg-amber-600',
              },
              { label: 'System Audit Trail', path: '/supervisor/audit', icon: ScrollText },
            ],
          },
        ];
    }
  };

  const navSections = getNavSections();

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-900/40 backdrop-blur-xs md:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 left-0 z-40 h-full w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 transition-transform duration-300 ease-in-out md:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-800/80 bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Zap className="w-5 h-5 fill-white text-white" />
            </div>
            <div>
              <span className="text-base font-extrabold tracking-tight text-white">
                Electro<span className="text-blue-400">Grid</span>
              </span>
              <span className="block text-[10px] uppercase font-semibold tracking-wider text-slate-400">
                Electrical Ops Cloud
              </span>
            </div>
          </div>
        </div>

        {/* Current Role Banner */}
        <div className="px-5 py-3 bg-slate-800/40 border-b border-slate-800/60 flex items-center justify-between">
          <span className="text-[11px] font-semibold uppercase text-slate-400">Role Context</span>
          <span className="text-xs font-bold text-blue-400 capitalize bg-blue-950/80 border border-blue-800/60 px-2 py-0.5 rounded">
            {role?.replace('_', ' ') || 'Guest'}
          </span>
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navSections.map((sec, secIdx) => (
            <div key={secIdx}>
              <div className="px-3 mb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {sec.section}
              </div>
              <nav className="space-y-1">
                {sec.items.map((item, itemIdx) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={itemIdx}
                      to={item.path}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                          isActive
                            ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                            : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                        }`
                      }
                    >
                      <div className="flex items-center gap-3">
                        <Icon className="w-4 h-4 opacity-80" />
                        <span>{item.label}</span>
                      </div>
                      {item.badge !== undefined && (
                        <span
                          className={`px-1.5 py-0.5 text-[11px] font-bold text-white rounded-full ${
                            item.badgeColor || 'bg-blue-600'
                          }`}
                        >
                          {item.badge}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* User Card at Bottom */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-800/40">
            <Avatar
              src={user?.avatar}
              name={user?.name || 'User'}
              size="sm"
            />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-white truncate">{user?.name}</p>
              <p className="text-[10px] text-slate-400 truncate">{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

