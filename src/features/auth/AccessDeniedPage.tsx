import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { ShieldX, ArrowLeft, UserCheck } from 'lucide-react';

export const AccessDeniedPage: React.FC = () => {
  const { role, switchDemoRole } = useAuth();
  const navigate = useNavigate();

  const getDashboardPath = () => {
    switch (role) {
      case 'customer':
        return '/customer/dashboard';
      case 'dispatcher':
        return '/dispatcher/dashboard';
      case 'electrician':
        return '/electrician/dashboard';
      case 'operations':
        return '/operations/dashboard';
      case 'management':
        return '/management/dashboard';
      default:
        return '/login';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 shadow-xl p-8 text-center">
        <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-rose-100 shadow-sm">
          <ShieldX className="w-8 h-8" />
        </div>

        <h2 className="text-xl font-extrabold text-slate-900">Access Restricted</h2>
        <p className="text-sm text-slate-600 mt-2 leading-relaxed">
          Your current session role (<span className="font-bold text-slate-800 uppercase">{role}</span>) does not have operational permissions to access this interface.
        </p>

        <div className="mt-6 flex flex-col gap-2.5">
          <button
            onClick={() => navigate(getDashboardPath())}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-sm flex items-center justify-center gap-2 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Return to Authorized Dashboard
          </button>

          <button
            onClick={() => {
              // Open dispatcher dashboard by switching role in demo
              switchDemoRole('dispatcher');
              navigate('/dispatcher/dashboard');
            }}
            className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 flex items-center justify-center gap-2 transition"
          >
            <UserCheck className="w-4 h-4 text-purple-600" />
            Switch to Dispatcher Profile
          </button>
        </div>
      </div>
    </div>
  );
};

