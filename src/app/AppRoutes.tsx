import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { RoleRoute } from '../guards/RoleRoute';
import { AppLayout } from '../components/layout/AppLayout';

// Auth
import { LoginPage } from '../features/auth/LoginPage';
import { RegisterPage } from '../features/auth/RegisterPage';
import { AccessDeniedPage } from '../features/auth/AccessDeniedPage';

// Customer
import { CustomerDashboard } from '../features/customer/CustomerDashboard';
import { MyRequestsPage } from '../features/customer/MyRequestsPage';
import { CustomerHistoryPage } from '../features/customer/CustomerHistoryPage';

// Technician
import { ElectricianDashboard } from '../features/electrician/ElectricianDashboard';
import { AssignedJobsPage } from '../features/electrician/AssignedJobsPage';

// Supervisor (Monitoring Only)
import { SupervisorDashboard } from '../features/supervisor/SupervisorDashboard';
import { SupervisorMapPage } from '../features/supervisor/SupervisorMapPage';
import { SupervisorJobsPage } from '../features/supervisor/SupervisorJobsPage';
import { SupervisorWorkforcePage } from '../features/supervisor/SupervisorWorkforcePage';
import { SupervisorAutomatedSchedulingPage } from '../features/supervisor/SupervisorAutomatedSchedulingPage';
import { SupervisorRecoveryPage } from '../features/supervisor/SupervisorRecoveryPage';
import { SupervisorAuditPage } from '../features/supervisor/SupervisorAuditPage';

export const AppRoutes: React.FC = () => {
  const { role, isAuthenticated } = useAuth();

  const getDefaultRoute = () => {
    if (!isAuthenticated) return '/login';
    switch (role) {
      case 'customer':
        return '/customer/dashboard';
      case 'technician':
      case 'electrician':
        return '/technician/dashboard';
      case 'supervisor':
      case 'operations':
      case 'dispatcher':
      case 'management':
      default:
        return '/supervisor/overview';
    }
  };

  return (
    <Routes>
      {/* Public Auth Routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/access-denied" element={<AccessDeniedPage />} />

      {/* Main Authenticated Layout */}
      <Route element={<AppLayout />}>
        {/* ================= ROLE 1: CUSTOMER PORTAL ================= */}
        <Route
          path="/customer/dashboard"
          element={
            <RoleRoute allowedRoles={['customer']}>
              <CustomerDashboard />
            </RoleRoute>
          }
        />
        <Route
          path="/customer/requests"
          element={
            <RoleRoute allowedRoles={['customer']}>
              <MyRequestsPage />
            </RoleRoute>
          }
        />
        <Route
          path="/customer/history"
          element={
            <RoleRoute allowedRoles={['customer']}>
              <CustomerHistoryPage />
            </RoleRoute>
          }
        />

        {/* ================= ROLE 2: TECHNICIAN FIELD PORTAL ================= */}
        <Route
          path="/technician/dashboard"
          element={
            <RoleRoute allowedRoles={['technician', 'electrician']}>
              <ElectricianDashboard />
            </RoleRoute>
          }
        />
        <Route
          path="/technician/jobs"
          element={
            <RoleRoute allowedRoles={['technician', 'electrician']}>
              <AssignedJobsPage />
            </RoleRoute>
          }
        />
        <Route
          path="/technician/availability"
          element={
            <RoleRoute allowedRoles={['technician', 'electrician']}>
              <ElectricianDashboard />
            </RoleRoute>
          }
        />
        <Route
          path="/technician/location"
          element={
            <RoleRoute allowedRoles={['technician', 'electrician']}>
              <ElectricianDashboard />
            </RoleRoute>
          }
        />

        {/* Electrician alias redirects for backward compatibility */}
        <Route path="/electrician/dashboard" element={<Navigate to="/technician/dashboard" replace />} />
        <Route path="/electrician/jobs" element={<Navigate to="/technician/jobs" replace />} />
        <Route path="/electrician/availability" element={<Navigate to="/technician/availability" replace />} />
        <Route path="/electrician/location" element={<Navigate to="/technician/location" replace />} />

        {/* ================= ROLE 3: SUPERVISOR (MONITORING ONLY) ================= */}
        <Route
          path="/supervisor/overview"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorDashboard />
            </RoleRoute>
          }
        />
        <Route
          path="/supervisor/map"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorMapPage />
            </RoleRoute>
          }
        />
        <Route
          path="/supervisor/jobs"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorJobsPage />
            </RoleRoute>
          }
        />
        <Route
          path="/supervisor/workforce"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorWorkforcePage />
            </RoleRoute>
          }
        />
        <Route
          path="/supervisor/scheduling"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorAutomatedSchedulingPage />
            </RoleRoute>
          }
        />
        <Route
          path="/supervisor/recovery"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorRecoveryPage />
            </RoleRoute>
          }
        />
        <Route
          path="/supervisor/audit"
          element={
            <RoleRoute allowedRoles={['supervisor', 'operations', 'dispatcher', 'management']}>
              <SupervisorAuditPage />
            </RoleRoute>
          }
        />

        {/* Legacy role redirection to consolidated Supervisor monitoring views */}
        <Route path="/operations/*" element={<Navigate to="/supervisor/overview" replace />} />
        <Route path="/dispatcher/*" element={<Navigate to="/supervisor/overview" replace />} />
        <Route path="/management/*" element={<Navigate to="/supervisor/overview" replace />} />
      </Route>

      {/* Root redirect */}
      <Route path="/" element={<Navigate to={getDefaultRoute()} replace />} />
      <Route path="*" element={<Navigate to={getDefaultRoute()} replace />} />
    </Routes>
  );
};
