import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { UserRole } from '../../types';
import {
  Zap,
  ArrowRight,
  ShieldCheck,
  UserCheck,
  HardHat,
  Activity,
  Compass,
  Eye,
  EyeOff,
  Lock,
  Mail,
  Info,
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, switchDemoRole } = useAuth();
  const [email, setEmail] = useState('supervisor@dispatchgrid.io');
  const [password, setPassword] = useState('dispatchgrid123');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('Email address is required.');
      return;
    }

    if (!password.trim()) {
      setError('Password is required. (Demo accounts use: dispatchgrid123)');
      return;
    }

    setIsLoading(true);

    try {
      const authedUser = await login(email.trim(), password.trim());
      // Determine redirection based on the authenticated user's real role
      if (authedUser.role === 'customer') {
        navigate('/customer/dashboard');
      } else if (authedUser.role === 'technician' || authedUser.role === 'electrician') {
        navigate('/technician/dashboard');
      } else {
        navigate('/supervisor/overview');
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemo = async (role: UserRole, targetEmail: string, redirectPath: string) => {
    setEmail(targetEmail);
    setPassword('dispatchgrid123');
    setError('');
    setIsLoading(true);
    try {
      const authedUser = await login(targetEmail, 'dispatchgrid123');
      if (authedUser.role === 'customer') {
        navigate('/customer/dashboard');
      } else if (authedUser.role === 'technician' || authedUser.role === 'electrician') {
        navigate('/technician/dashboard');
      } else {
        navigate('/supervisor/overview');
      }
    } catch {
      switchDemoRole(role);
      navigate(redirectPath);
    } finally {
      setIsLoading(false);
    }
  };

  const demoAccounts = [
    {
      role: 'technician' as UserRole,
      name: 'Guruprasad Rao (18th Electrician)',
      type: 'Field Technician • Alanahalli • MYS-TECH-117',
      email: 'guruprasad.r@dispatchgrid.io',
      path: '/technician/dashboard',
      icon: HardHat,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
    },
    {
      role: 'technician' as UserRole,
      name: 'Pradeep Hegde',
      type: 'Lead Technician • Saraswathipuram • MYS-TECH-100',
      email: 'technician@dispatchgrid.io',
      path: '/technician/dashboard',
      icon: HardHat,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
    },
    {
      role: 'customer' as UserRole,
      name: 'Ananya Rao',
      type: 'Customer (Individual • Saraswathipuram)',
      email: 'customer@dispatchgrid.io',
      path: '/customer/dashboard',
      icon: UserCheck,
      color: 'text-blue-600',
      bg: 'bg-blue-50 border-blue-200',
    },
    {
      role: 'customer' as UserRole,
      name: 'Mysore Silk Emporium (Suresh N.)',
      type: 'Customer (Commercial • Sayyaji Rao Rd)',
      email: 'facilities@mysoresilk.in',
      path: '/customer/dashboard',
      icon: UserCheck,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50 border-indigo-200',
    },
    {
      role: 'supervisor' as UserRole,
      name: 'Meera Kulkarni',
      type: 'Supervisor (Monitoring Only)',
      email: 'supervisor@dispatchgrid.io',
      path: '/supervisor/overview',
      icon: Activity,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50 border-emerald-200',
    },
  ];

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="mx-auto w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/30">
          <Zap className="w-7 h-7 fill-white text-white" />
        </div>
        <h2 className="mt-4 text-2xl font-extrabold text-slate-900 tracking-tight">
          Sign in to <span className="text-blue-600">ElectroGrid</span>
        </h2>
        <p className="mt-1 text-sm text-slate-500">
          Intelligent Electrical Field-Service Management & Workforce Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="bg-white py-8 px-6 shadow-xl rounded-2xl sm:px-10 border border-slate-200/80">
          {/* Quick Demo Role Selector */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                1-Click Demo Profiles
              </span>
              <span className="text-[11px] text-blue-600 font-medium">Instant Access</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {demoAccounts.map((account) => {
                const Icon = account.icon;
                return (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => handleQuickDemo(account.role, account.email, account.path)}
                    className="flex items-center gap-2.5 p-2.5 rounded-xl border border-slate-200 hover:border-blue-400 hover:bg-blue-50/40 text-left transition"
                  >
                    <div className={`p-1.5 rounded-lg border ${account.bg}`}>
                      <Icon className={`w-4 h-4 ${account.color}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-bold text-slate-900 truncate">{account.name}</p>
                      <p className="text-[10px] text-slate-500 truncate">{account.type}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white px-3 text-slate-400 font-semibold">Or Sign in with Email</span>
            </div>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-xs text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Account Email
              </label>
              <div className="relative">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@dispatchgrid.io"
                  required
                  className="w-full pl-9 pr-3.5 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition"
                />
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-slate-700">Password</label>
                <span className="text-[11px] text-blue-600 font-medium">Demo: dispatchgrid123</span>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter account password"
                  required
                  className="w-full pl-9 pr-10 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition"
                />
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-600 focus:outline-none"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 p-2.5 rounded-lg flex items-start gap-2 text-xs text-slate-600">
              <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <span>
                <b>Default Password:</b> <code className="text-blue-700 font-bold bg-blue-50 px-1 rounded">dispatchgrid123</code> is enabled across all 20 Mysuru technicians, supervisor & customer accounts.
              </span>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full mt-2 py-2.5 px-4 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/20 flex items-center justify-center gap-2 transition disabled:opacity-60 cursor-pointer"
            >
              {isLoading ? 'Authenticating Credentials...' : 'Sign In'}
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-500">
            Need a customer account?{' '}
            <Link to="/register" className="font-semibold text-blue-600 hover:underline">
              Register here
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

