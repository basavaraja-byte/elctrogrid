import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

interface RoleRouteProps {
  allowedRoles: UserRole[];
  children: React.ReactNode;
}

export const RoleRoute: React.FC<RoleRouteProps> = ({ allowedRoles, children }) => {
  const { user, role, isAuthenticated } = useAuth();
  const location = useLocation();

  if (!isAuthenticated || !user || !role) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (!allowedRoles.includes(role)) {
    if (role === 'technician' || role === 'electrician') {
      return <Navigate to="/technician/dashboard" replace />;
    }
    if (role === 'customer') {
      return <Navigate to="/customer/dashboard" replace />;
    }
    return <Navigate to="/supervisor/overview" replace />;
  }

  return <>{children}</>;
};

