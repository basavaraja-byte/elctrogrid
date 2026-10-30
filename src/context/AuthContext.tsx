import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole, CustomerCategory } from '../types';
import { mockStore } from '../services/mock/mockStore';
import { api } from '../services/api/apiClient';

interface AuthContextType {
  user: User | null;
  role: UserRole | null;
  isAuthenticated: boolean;
  login: (identifier: string, password?: string) => Promise<User>;
  registerCustomer: (details: {
    name: string;
    email: string;
    phone: string;
    password?: string;
    customerCategory: CustomerCategory;
    companyName?: string;
    address: string;
    city: string;
    postalCode: string;
  }) => Promise<User>;
  switchDemoRole: (role: UserRole, specificUserId?: string) => void;
  logout: () => void;
  allDemoUsers: User[];
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_USER_KEY = 'dispatchgrid_current_user_v2';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    try {
      const savedUserStr = localStorage.getItem(AUTH_USER_KEY);
      if (savedUserStr) {
        const parsed = JSON.parse(savedUserStr);
        const liveUser = mockStore.getUserById(parsed.id) || mockStore.findUserByQuery(parsed.email || parsed.id);
        if (liveUser) {
          setUser(liveUser);
          return;
        }
      }
    } catch (e) {
      console.warn('Failed to parse stored user', e);
    }

    // Default to Supervisor (Meera Kulkarni) or Customer (Ananya Rao)
    const defaultSupervisor = mockStore.getUsers().find((u) => u.email === 'supervisor@dispatchgrid.io')
      || mockStore.getUsers().find((u) => u.role === 'supervisor')
      || mockStore.getUsers()[0];

    if (defaultSupervisor) {
      setUser(defaultSupervisor);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(defaultSupervisor));
    }
  }, []);

  const login = async (identifier: string, password?: string): Promise<User> => {
    const { user: authedUser, token } = await api.login(identifier, password);
    setUser(authedUser);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(authedUser));
    localStorage.setItem('dispatchgrid_auth_token', token);
    return authedUser;
  };

  const registerCustomer = async (details: {
    name: string;
    email: string;
    phone: string;
    password?: string;
    customerCategory: CustomerCategory;
    companyName?: string;
    address: string;
    city: string;
    postalCode: string;
  }): Promise<User> => {
    const newUser = mockStore.addUser({
      name: details.name,
      email: details.email,
      phone: details.phone,
      password: details.password || 'dispatchgrid123',
      role: 'customer',
      customerCategory: details.customerCategory,
      companyName: details.companyName,
      commercialLocations:
        details.customerCategory === 'commercial'
          ? [
              {
                lat: 12.2958 + (Math.random() - 0.5) * 0.02,
                lng: 76.6394 + (Math.random() - 0.5) * 0.02,
                address: details.address,
                city: details.city || 'Mysuru',
                postalCode: details.postalCode || '570001',
              },
            ]
          : undefined,
      active: true,
    });

    setUser(newUser);
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(newUser));
    return newUser;
  };

  const switchDemoRole = (targetRole: UserRole, specificUserId?: string) => {
    const users = mockStore.getUsers();
    let targetUser: User | undefined;

    if (specificUserId) {
      targetUser = users.find((u) => u.id === specificUserId);
    }

    if (!targetUser) {
      // Find standard representative for the 3 roles
      if (targetRole === 'customer') {
        targetUser = users.find((u) => u.id === 'usr-cust-ind-1');
      } else if (targetRole === 'technician' || targetRole === 'electrician') {
        targetUser = users.find((u) => u.id === 'usr-tech-1') || users.find((u) => u.role === 'technician');
      } else if (targetRole === 'supervisor' || targetRole === 'operations' || targetRole === 'dispatcher' || targetRole === 'management') {
        targetUser = users.find((u) => u.id === 'usr-sup-1') || users.find((u) => u.role === 'supervisor');
      }
    }

    if (targetUser) {
      setUser(targetUser);
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(targetUser));
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem(AUTH_USER_KEY);
    localStorage.removeItem('dispatchgrid_auth_token');
  };

  const allDemoUsers = mockStore.getUsers();

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || null,
        isAuthenticated: !!user,
        login,
        registerCustomer,
        switchDemoRole,
        logout,
        allDemoUsers,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
