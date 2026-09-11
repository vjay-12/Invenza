import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
  role: 'super_admin' | 'admin' | 'manager' | 'staff' | 'viewer' | string;
  tenantId?: string;
  companyName?: string;
  industry?: string;
  enabledModules?: string[];
  permissions?: string[];
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  isCompanyAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  demoLogin: (type: 'super_admin' | 'company_admin' | 'staff') => Promise<void>;
  logout: () => void;
  updateUserLocal: (partial: Partial<AuthUser>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const savedUser = localStorage.getItem('invenza_user');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('invenza_token') || null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Validate or verify session on mount
    const verifySession = async () => {
      if (token) {
        try {
          const profile = await api.getCurrentUser();
          if (profile && profile.email) {
            const updatedUser: AuthUser = {
              id: profile.id || user?.id || 'usr-01',
              email: profile.email,
              fullName: profile.full_name || user?.fullName || 'User',
              role: profile.role || user?.role || 'staff',
              tenantId: profile.tenant_id || user?.tenantId,
              companyName: profile.company_name || user?.companyName,
              industry: profile.industry || user?.industry,
              enabledModules: profile.enabled_modules || user?.enabledModules,
              permissions: profile.permissions || user?.permissions,
            };
            setUser(updatedUser);
            localStorage.setItem('invenza_user', JSON.stringify(updatedUser));
          }
        } catch (err) {
          console.warn('Session verification fallback to stored user:', err);
        }
      }
      setIsLoading(false);
    };

    verifySession();
  }, [token]);

  const login = async (email: string, password: string) => {
    try {
      const data = await api.login({ email, password });
      const authToken = data.access_token;
      const authUser: AuthUser = {
        id: data.tenant_id || 'usr-01',
        email: email.trim().toLowerCase(),
        fullName: data.full_name || 'User',
        role: data.user_role || 'staff',
        tenantId: data.tenant_id,
        companyName: data.company_name || (data.user_role === 'super_admin' ? 'Master Platform' : 'Company Workspace'),
        industry: data.industry || 'General',
        enabledModules: data.enabled_modules || [
          'products', 'locations', 'orders', 'transfers', 'adjustments', 'ledger', 'reports', 'storage'
        ],
        permissions: data.permissions || [],
      };

      setToken(authToken);
      setUser(authUser);
      localStorage.setItem('invenza_token', authToken);
      localStorage.setItem('invenza_user', JSON.stringify(authUser));
    } catch (err) {
      throw err;
    }
  };

  const demoLogin = async (type: 'super_admin' | 'company_admin' | 'staff' = 'super_admin') => {
    if (type === 'super_admin') {
      await login('superadmin@invenza.internal', 'superadmin2026');
    } else if (type === 'company_admin') {
      await login('admin@invenza.internal', 'adminpassword2026');
    } else {
      await login('staff@invenza.internal', 'staffpassword2026');
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('invenza_token');
    localStorage.removeItem('invenza_user');
  };

  const updateUserLocal = (partial: Partial<AuthUser>) => {
    setUser((prev) => {
      if (!prev) return null;
      const updated = { ...prev, ...partial };
      localStorage.setItem('invenza_user', JSON.stringify(updated));
      return updated;
    });
  };

  const isSuperAdmin = user?.role === 'super_admin';
  const isCompanyAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isSuperAdmin,
        isCompanyAdmin,
        isLoading,
        login,
        demoLogin,
        logout,
        updateUserLocal,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
