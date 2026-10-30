import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import {
  Menu,
  Bell,
  UserCheck,
  RotateCcw,
  LogOut,
  ChevronDown,
  Sparkles,
  Zap,
} from 'lucide-react';
import { RoleSwitcherModal } from './RoleSwitcherModal';
import { NotificationDrawer } from '../notifications/NotificationDrawer';
import { DemoScenarioRunnerModal } from '../demo/DemoScenarioRunnerModal';
import { Avatar } from '../common/Avatar';
import { useNavigate } from 'react-router-dom';

interface TopNavbarProps {
  onToggleSidebar: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({ onToggleSidebar }) => {
  const { user, role, logout } = useAuth();
  const { unreadNotificationsCount, resetAllDemoData } = useApp();
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState(false);
  const [isNotifDrawerOpen, setIsNotifDrawerOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleResetData = () => {
    if (window.confirm('Reset all mock operational data back to the clean seed dataset?')) {
      resetAllDemoData();
      alert('Mock data store has been restored to factory seed state.');
    }
  };

  return (
    <>
      <header className="sticky top-0 z-30 h-16 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-6 flex items-center justify-between shadow-xs">
        {/* Left: Mobile Toggle & System Brand Tag */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="p-2 rounded-lg text-slate-600 hover:bg-slate-100 md:hidden"
          >
            <Menu className="w-5 h-5" />
          </button>

          <div className="flex items-center gap-2">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
              Live Grid Active
            </span>
          </div>
        </div>

        {/* Right: Quick Role Switcher Pill + Notifications + Profile */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Highlighted Role Switcher Button */}
          <button
            onClick={() => setIsRoleModalOpen(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-sm shadow-blue-500/20 text-xs font-semibold transition"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-200" />
            <span className="hidden sm:inline">Role Switcher</span>
            <span className="capitalize bg-white/20 px-1.5 py-0.5 rounded text-[11px]">
              {role?.replace('_', ' ') || 'Select'}
            </span>
          </button>

          {/* Demo Scenario Runner Action Button */}
          <button
            onClick={() => setIsScenarioModalOpen(true)}
            title="Simulate Operational Disruption & Automated Recovery Scenarios"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-xs text-xs font-semibold transition"
          >
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span className="hidden sm:inline">Simulate Disruption</span>
          </button>

          {/* Reset Demo Data Action Button */}
          <button
            onClick={handleResetData}
            title="Reset Mock Data to Initial Seeds"
            className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition hidden lg:flex items-center gap-1.5 text-xs font-medium"
          >
            <RotateCcw className="w-4 h-4 text-slate-500" />
            <span>Reset Demo</span>
          </button>

          {/* Notification Bell */}
          <button
            onClick={() => setIsNotifDrawerOpen(true)}
            className="relative p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition"
          >
            <Bell className="w-5 h-5" />
            {unreadNotificationsCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full bg-rose-600 text-[10px] font-bold text-white flex items-center justify-center animate-bounce">
                {unreadNotificationsCount > 9 ? '9+' : unreadNotificationsCount}
              </span>
            )}
          </button>

          {/* User Profile Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
              className="flex items-center gap-2 p-1 pl-2 rounded-lg hover:bg-slate-100 transition cursor-pointer"
            >
              <Avatar
                name={user?.name || 'User'}
                src={user?.avatar}
                size="sm"
              />
              <span className="text-xs font-semibold text-slate-700 hidden md:block max-w-[120px] truncate">
                {user?.name}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {isProfileMenuOpen && (
              <>
                <div
                  onClick={() => setIsProfileMenuOpen(false)}
                  className="fixed inset-0 z-40"
                />
                <div className="absolute right-0 mt-2 w-56 rounded-xl bg-white shadow-xl border border-slate-200 py-1.5 z-50 animate-fadeIn">
                  <div className="px-4 py-2 border-b border-slate-100">
                    <p className="text-xs font-bold text-slate-900 truncate">{user?.name}</p>
                    <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
                    <span className="inline-block mt-1 text-[10px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                      {role}
                    </span>
                  </div>

                  <button
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      setIsRoleModalOpen(true);
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-blue-50 flex items-center gap-2"
                  >
                    <UserCheck className="w-3.5 h-3.5 text-blue-600" />
                    Switch Role Demo
                  </button>

                  <button
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      setIsScenarioModalOpen(true);
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-amber-700 hover:bg-amber-50 flex items-center gap-2"
                  >
                    <Zap className="w-3.5 h-3.5 text-amber-600" />
                    Simulate Disruption
                  </button>

                  <button
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      handleResetData();
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-slate-700 hover:bg-rose-50 flex items-center gap-2"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-rose-600" />
                    Reset Data to Seed
                  </button>

                  <div className="my-1 border-t border-slate-100" />

                  <button
                    onClick={() => {
                      setIsProfileMenuOpen(false);
                      handleLogout();
                    }}
                    className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2 font-medium"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign Out
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Role Switcher Modal */}
      <RoleSwitcherModal
        isOpen={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
      />

      {/* Demo Scenario Runner Modal */}
      <DemoScenarioRunnerModal
        isOpen={isScenarioModalOpen}
        onClose={() => setIsScenarioModalOpen(false)}
      />

      {/* Notification Drawer */}
      <NotificationDrawer
        isOpen={isNotifDrawerOpen}
        onClose={() => setIsNotifDrawerOpen(false)}
      />
    </>
  );
};

