import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { UserRole } from '../../types';
import { Modal } from '../common/Modal';
import {
  UserCheck,
  Zap,
  RotateCcw,
  ShieldCheck,
  Activity,
  HardHat,
  Compass,
  CheckCircle,
} from 'lucide-react';

interface RoleSwitcherModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const RoleSwitcherModal: React.FC<RoleSwitcherModalProps> = ({ isOpen, onClose }) => {
  const { user, switchDemoRole } = useAuth();
  const { resetAllDemoData } = useApp();

  const demoRoles: {
    role: UserRole;
    userId: string;
    label: string;
    title: string;
    desc: string;
    icon: any;
    color: string;
    bg: string;
  }[] = [
    {
      role: 'customer',
      userId: 'usr-cust-ind-1',
      label: 'Individual Customer',
      title: 'Ananya Rao',
      desc: 'Mysuru resident: submit electrical complaints, track technician dispatch, leave feedback',
      icon: UserCheck,
      color: 'text-blue-600',
      bg: 'bg-blue-50 border-blue-200',
    },
    {
      role: 'customer',
      userId: 'usr-cust-com-1',
      label: 'Commercial Customer',
      title: 'Mysore Silk & Handicrafts Emporium (Suresh Nambiar)',
      desc: 'Multi-facility commercial enterprise with industrial power maintenance SLAs',
      icon: UserCheck,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50 border-indigo-200',
    },
    {
      role: 'technician',
      userId: 'usr-tech-18',
      label: 'Field Technician (18th)',
      title: 'Guruprasad Rao • Alanahalli',
      desc: 'MYS-TECH-117: Emergency Generators, Industrial Wiring, Arc Flash Mitigation',
      icon: HardHat,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
    },
    {
      role: 'technician',
      userId: 'usr-tech-1',
      label: 'Lead Field Technician',
      title: 'Pradeep Hegde (Master Wireman)',
      desc: 'Field execution: real-time job transitions, navigation to Mysuru sites, work sign-off',
      icon: HardHat,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
    },
    {
      role: 'supervisor',
      userId: 'usr-sup-1',
      label: 'Grid Operations Supervisor',
      title: 'Meera Kulkarni (Monitoring Only)',
      desc: 'CHESCOM Mysuru circle telemetry, live technician GPS map, and automated scheduling log',
      icon: Activity,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50 border-emerald-200',
    },
  ];

  const handleSelectRole = (role: UserRole, userId: string) => {
    switchDemoRole(role, userId);
    onClose();
  };

  const handleResetData = () => {
    if (window.confirm('Reset all demo data back to clean initial seed dataset?')) {
      resetAllDemoData();
      alert('Demo data has been restored to factory seed state.');
      onClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Switch Demo Role"
      subtitle="Instantly explore ElectroGrid through the lens of any stakeholder"
      maxWidth="2xl"
      footer={
        <div className="flex items-center justify-between w-full">
          <button
            onClick={handleResetData}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50 rounded-lg border border-rose-200 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset All Demo Data
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
          >
            Close
          </button>
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {demoRoles.map((item) => {
          const isSelected = user?.id === item.userId;
          const Icon = item.icon;

          return (
            <div
              key={item.userId}
              onClick={() => handleSelectRole(item.role, item.userId)}
              className={`p-4 rounded-xl border-2 cursor-pointer transition-all relative ${
                isSelected
                  ? 'border-blue-600 bg-blue-50/50 shadow-md ring-2 ring-blue-500/20'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
              }`}
            >
              {isSelected && (
                <span className="absolute top-3 right-3 text-blue-600">
                  <CheckCircle className="w-5 h-5 fill-blue-600 text-white" />
                </span>
              )}

              <div className="flex items-start gap-3">
                <div className={`p-2.5 rounded-lg border ${item.bg}`}>
                  <Icon className={`w-5 h-5 ${item.color}`} />
                </div>
                <div className="flex-1 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      {item.label}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 mt-0.5">{item.title}</h4>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Modal>
  );
};

