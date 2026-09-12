import React, { createContext, useContext, useState, useEffect, useMemo } from 'react';
import { api } from '../services/api';
import { getTaxConfig, TaxConfig, TaxRegime } from '../utils/taxUtils';

export interface AuthUser {
  id: string;
  email: string;
  fullName: string;
  role: 'super_admin' | 'admin' | 'manager' | 'staff' | 'viewer' | string;
  tenantId?: string;
  companyName?: string;
  industry?: string;
  currencyCode?: string;
  countryCode?: string;
  state?: string;
  taxType?: TaxRegime;
  taxRate?: number;
  taxLabel?: string;
  enabledModules?: string[];
  permissions?: string[];
}

interface AuthContextType {
  user: AuthUser | null;
  token: string | null;
  currencyCode: string;
  countryCode: string;
  state?: string;
  taxType: TaxRegime;
  taxRate: number;
  taxLabel: string;
  taxConfig: TaxConfig;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  isCompanyAdmin: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  demoLogin: (type: 'super_admin' | 'company_admin' | 'staff') => Promise<void>;
  logout: () => void;
  updateUserLocal: (partial: Partial<AuthUser>) => void;
  switchTenant: (tenant: any) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const savedUser = localStorage.getItem('invenza_user');
    if (!savedUser) return null;
    try {
      const parsed: AuthUser = JSON.parse(savedUser);
      // Auto-heal stale sessions where currencyCode is EUR/USD but countryCode is missing or IN
      if (parsed) {
        if (parsed.currencyCode === 'EUR' && (!parsed.countryCode || parsed.countryCode === 'IN')) {
          parsed.countryCode = 'DE';
          parsed.taxType = 'VAT';
          parsed.taxLabel = 'VAT';
          parsed.taxRate = 19.0;
        } else if (parsed.currencyCode === 'USD' && (!parsed.countryCode || parsed.countryCode === 'IN')) {
          parsed.countryCode = 'US';
          parsed.taxType = 'SALES_TAX';
          parsed.taxLabel = 'Sales Tax';
          parsed.taxRate = 7.25;
        }
      }
      return parsed;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('invenza_token') || null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Authoritative dynamic tax config derived from org's locked identity
  const taxConfig = useMemo<TaxConfig>(() => {
    return getTaxConfig(user?.countryCode, user?.state, user?.taxRate, user?.currencyCode);
  }, [user?.countryCode, user?.state, user?.taxRate, user?.currencyCode]);

  useEffect(() => {
    // Validate or verify session on mount
    const verifySession = async () => {
      if (token) {
        try {
          const profile = await api.getCurrentUser();
          if (profile && profile.email) {
            let country = profile.country_code || user?.countryCode;
            const cur = profile.currency_code || user?.currencyCode;
            if (!country || country === 'IN') {
              if (cur === 'EUR') country = 'DE';
              else if (cur === 'USD') country = 'US';
              else country = country || 'IN';
            }
            const state = profile.state || user?.state;
            const cfg = getTaxConfig(country, state, profile.tax_rate, cur);

            const updatedUser: AuthUser = {
              id: profile.id || user?.id || 'usr-01',
              email: profile.email,
              fullName: profile.full_name || user?.fullName || 'User',
              role: profile.role || user?.role || 'staff',
              tenantId: profile.tenant_id || user?.tenantId,
              companyName: profile.company_name || user?.companyName,
              industry: profile.industry || user?.industry,
              currencyCode: cur || cfg.currencyCode,
              countryCode: country,
              state: state,
              taxType: (profile.tax_type as TaxRegime) || user?.taxType || cfg.taxType,
              taxRate: profile.tax_rate !== undefined && profile.tax_rate !== null ? Number(profile.tax_rate) : (user?.taxRate ?? cfg.standardRate),
              taxLabel: profile.tax_label || user?.taxLabel || cfg.taxLabel,
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
      let country = data.country_code;
      const cur = data.currency_code;
      if (!country || country === 'IN') {
        if (cur === 'EUR') country = 'DE';
        else if (cur === 'USD') country = 'US';
        else country = country || 'IN';
      }
      const state = data.state;
      const cfg = getTaxConfig(country, state, data.tax_rate, cur);

      const authUser: AuthUser = {
        id: data.tenant_id || 'usr-01',
        email: email.trim().toLowerCase(),
        fullName: data.full_name || 'User',
        role: data.user_role || 'staff',
        tenantId: data.tenant_id,
        companyName: data.company_name || (data.user_role === 'super_admin' ? 'Master Platform' : 'Company Workspace'),
        industry: data.industry || 'General',
        currencyCode: cur || cfg.currencyCode,
        countryCode: country,
        state: state,
        taxType: (data.tax_type as TaxRegime) || cfg.taxType,
        taxRate: data.tax_rate !== undefined && data.tax_rate !== null ? Number(data.tax_rate) : cfg.standardRate,
        taxLabel: data.tax_label || cfg.taxLabel,
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

  const switchTenant = (tenant: any) => {
    if (!tenant) return;
    const country = tenant.country_code || 'IN';
    const state = tenant.state || '';
    const cfg = getTaxConfig(country, state);
    const currency = tenant.currency_code || cfg.currencyCode;

    setUser((prev) => {
      const updated: AuthUser = {
        ...(prev || {
          id: 'usr-admin',
          email: 'admin@workspace.internal',
          fullName: 'Workspace Administrator',
          role: 'admin',
        }),
        tenantId: tenant.id,
        companyName: tenant.name,
        industry: tenant.industry || 'General',
        countryCode: country,
        currencyCode: currency,
        state: state,
        taxType: cfg.taxType,
        taxRate: cfg.standardRate,
        taxLabel: cfg.taxLabel,
        enabledModules: tenant.enabled_modules || prev?.enabledModules || [
          'products', 'locations', 'orders', 'transfers', 'adjustments', 'ledger', 'reports', 'storage'
        ],
      };
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
        currencyCode: user?.currencyCode || taxConfig.currencyCode,
        countryCode: user?.countryCode || taxConfig.countryCode,
        state: user?.state || taxConfig.stateName,
        taxType: user?.taxType || taxConfig.taxType,
        taxRate: user?.taxRate !== undefined ? user.taxRate : taxConfig.standardRate,
        taxLabel: user?.taxLabel || taxConfig.taxLabel,
        taxConfig,
        isAuthenticated: !!user && !!token,
        isSuperAdmin,
        isCompanyAdmin,
        isLoading,
        login,
        demoLogin,
        logout,
        updateUserLocal,
        switchTenant,
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
