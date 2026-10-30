import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { useApp } from '../../context/AppContext';
import { api } from '../../services/api/apiClient';
import { X, CheckCheck, Bell, AlertTriangle, CheckCircle, Info, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface NotificationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const { notifications, refreshData } = useApp();
  const navigate = useNavigate();

  if (!isOpen) return null;

  // Filter for current user's role or ID
  const userNotifications = notifications.filter((n) => {
    if (n.targetUserId && user?.id === n.targetUserId) return true;
    if (n.targetRole && user?.role === n.targetRole) return true;
    if (!n.targetRole && !n.targetUserId) return true;
    return false;
  });

  const handleMarkAll = async () => {
    if (user) {
      await api.markAllNotificationsAsRead(user.role, user.id);
      refreshData();
    }
  };

  const handleItemClick = async (notifId: string, linkUrl?: string) => {
    await api.markNotificationAsRead(notifId);
    refreshData();
    if (linkUrl) {
      navigate(linkUrl);
      onClose();
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'alert':
        return <AlertTriangle className="w-4 h-4 text-rose-600" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-amber-600" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-emerald-600" />;
      default:
        return <Info className="w-4 h-4 text-blue-600" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col animate-slideLeft">
        {/* Header */}
        <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-blue-600" />
            <h3 className="font-bold text-slate-900">Notifications</h3>
            <span className="text-xs bg-blue-100 text-blue-700 font-semibold px-2 py-0.5 rounded-full">
              {userNotifications.filter((n) => !n.isRead).length} unread
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleMarkAll}
              title="Mark all as read"
              className="text-xs text-slate-500 hover:text-blue-600 flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-200/50"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
          {userNotifications.length > 0 ? (
            userNotifications.map((n) => (
              <div
                key={n.id}
                onClick={() => handleItemClick(n.id, n.linkUrl)}
                className={`p-4 transition-colors cursor-pointer flex gap-3 ${
                  n.isRead ? 'bg-white hover:bg-slate-50' : 'bg-blue-50/40 hover:bg-blue-50/70'
                }`}
              >
                <div className="mt-0.5">{getIcon(n.type)}</div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h4
                      className={`text-xs font-bold ${
                        n.isRead ? 'text-slate-700' : 'text-blue-950 font-semibold'
                      }`}
                    >
                      {n.title}
                    </h4>
                    <span className="text-[10px] text-slate-400">
                      {new Date(n.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">{n.message}</p>
                  {n.linkUrl && (
                    <div className="mt-2 flex items-center text-[11px] font-semibold text-blue-600 hover:underline gap-1">
                      <span>View details</span>
                      <ExternalLink className="w-3 h-3" />
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="p-12 text-center text-slate-400 text-xs">
              No notifications for your role.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

