import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  Job,
  ServiceRequest,
  Electrician,
  ApprovalRequest,
  EscalationAlert,
  AuditLogEntry,
  NotificationItem,
  PolicySettings,
  DisruptionRecord,
} from '../types';
import { mockStore } from '../services/mock/mockStore';

interface AppContextType {
  jobs: Job[];
  serviceRequests: ServiceRequest[];
  electricians: Electrician[];
  approvals: ApprovalRequest[];
  escalations: EscalationAlert[];
  disruptions: DisruptionRecord[];
  notifications: NotificationItem[];
  auditLogs: AuditLogEntry[];
  policies: PolicySettings;
  unreadNotificationsCount: number;
  refreshData: () => void;
  resetAllDemoData: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [dataVersion, setDataVersion] = useState(0);

  const refreshData = useCallback(() => {
    setDataVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    // Subscribe to mock store updates
    const unsubscribe = mockStore.subscribe(() => {
      refreshData();
    });
    return () => unsubscribe();
  }, [refreshData]);

  const jobs = mockStore.getJobs();
  const serviceRequests = mockStore.getServiceRequests();
  const electricians = mockStore.getElectricians();
  const approvals = mockStore.getApprovals();
  const escalations = mockStore.getEscalations();
  const disruptions = mockStore.getDisruptions();
  const notifications = mockStore.getNotifications();
  const auditLogs = mockStore.getAuditLogs();
  const policies = mockStore.getPolicies();

  const unreadNotificationsCount = notifications.filter((n) => !n.isRead).length;

  const resetAllDemoData = () => {
    mockStore.resetToDefault();
    refreshData();
  };

  return (
    <AppContext.Provider
      value={{
        jobs,
        serviceRequests,
        electricians,
        approvals,
        escalations,
        disruptions,
        notifications,
        auditLogs,
        policies,
        unreadNotificationsCount,
        refreshData,
        resetAllDemoData,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};

