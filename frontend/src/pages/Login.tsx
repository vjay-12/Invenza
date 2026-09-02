import React, { useState } from 'react';
import {
  ShieldCheck,
  Lock,
  Mail,
  ArrowRight,
  Sparkles,
  Database,
  Layers,
  HardDrive,
  Eye,
  EyeOff,
  AlertCircle,
  KeyRound,
  Zap,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Login: React.FC = () => {
  const { login, demoLogin } = useAuth();

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Sign in form state (empty by default, testing accounts available below)
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      await login(loginEmail, loginPassword);
    } catch (err: any) {
      setErrorMessage(err.message || 'Invalid email or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemo = async (role: 'super_admin' | 'company_admin' | 'staff') => {
    setErrorMessage(null);
    setIsLoading(true);
    try {
      if (role === 'super_admin') {
        setLoginEmail('superadmin@invenza.internal');
        setLoginPassword('superadmin2026');
      } else if (role === 'company_admin') {
        setLoginEmail('admin@invenza.internal');
        setLoginPassword('adminpassword2026');
      } else {
        setLoginEmail('staff@invenza.internal');
        setLoginPassword('staffpassword2026');
      }
      await demoLogin(role);
    } catch (err: any) {
      setErrorMessage(err.message || 'Demo login failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-slate-950 text-slate-100 selection:bg-indigo-500 selection:text-white relative overflow-hidden">
      {/* Dynamic Background Glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/3 w-[600px] h-[600px] bg-blue-600/10 rounded-full blur-[140px] pointer-events-none" />

      {/* Left Column: Brand Hero & Live Architecture Matrix */}
      <div className="lg:w-1/2 p-8 sm:p-12 lg:p-16 flex flex-col justify-between relative z-10 border-b lg:border-b-0 lg:border-r border-slate-800/80 bg-slate-950/60 backdrop-blur-xl">
        <div>
          {/* Logo */}
          <div className="flex items-center gap-3.5 mb-12">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 text-white font-black text-xl shadow-lg shadow-indigo-500/30">
              I
            </div>
            <div>
              <span className="text-2xl font-black tracking-tight text-white">Invenza</span>
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                Multi-Tenant SaaS
              </span>
            </div>
          </div>

          {/* Hero Pitch */}
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-indigo-400 text-xs font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Multi-Tenant Architecture with Strict Data Isolation</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight mb-6">
              Enterprise Inventory, Tailored by Industry.
            </h1>
            <p className="text-slate-400 text-base sm:text-lg leading-relaxed mb-8">
              Super Admin manages cross-company provisioning with automatic email credentials and custom component selection. Company Admins operate in completely isolated workspaces.
            </p>
          </div>

          {/* Core Architectural Pillars */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl mb-12">
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
              <Database className="w-5 h-5 text-indigo-400 mb-2" />
              <div className="text-xs font-bold text-white mb-0.5">PostgreSQL Engine</div>
              <div className="text-[11px] text-slate-400">Strict Tenant Data Isolation</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
              <Layers className="w-5 h-5 text-purple-400 mb-2" />
              <div className="text-xs font-bold text-white mb-0.5">Industry Modules</div>
              <div className="text-[11px] text-slate-400">Custom Enabled Components</div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
              <HardDrive className="w-5 h-5 text-sky-400 mb-2" />
              <div className="text-xs font-bold text-white mb-0.5">Email Notifications</div>
              <div className="text-[11px] text-slate-400">Automated Credential Delivery</div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="pt-6 border-t border-slate-800/80 text-xs text-slate-500 flex flex-wrap items-center justify-between gap-2">
          <span>&copy; 2026 Invenza Cloud Platform.</span>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              FastAPI Core Online
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              MinIO Storage Ready
            </span>
          </div>
        </div>
      </div>

      {/* Right Column: Clean Login Portal */}
      <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-10 lg:p-16 relative z-10">
        <div className="w-full max-w-md">
          {/* Card Container */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-2xl">
            {/* Header */}
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-lg bg-indigo-500/10 text-indigo-400 text-xs font-semibold mb-2">
                <Lock className="w-3.5 h-3.5" />
                <span>Authorized Access Only</span>
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">Sign in to Invenza</h2>
              <p className="text-xs text-slate-400 mt-1">
                Enter your system credentials. Accounts are provisioned by your organization's Administrator.
              </p>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5 animate-in fade-in duration-200">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                    placeholder="name@company.com"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-300">Password</label>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                    placeholder="••••••••"
                    className="w-full pl-10 pr-10 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold text-sm shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <span className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    <span>Authenticating...</span>
                  </div>
                ) : (
                  <>
                    <span>Sign In to Platform</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Demo Credentials for Dev Testing */}
            <div className="mt-6 pt-5 border-t border-slate-800/80">
              <div className="flex items-center justify-between mb-3">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Quick Access Testing Accounts
                </span>
                <span className="text-[10px] text-indigo-400 font-medium flex items-center gap-1">
                  <Zap className="w-3 h-3" /> 1-Click
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickDemo('super_admin')}
                  className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/50 text-left transition-all group"
                >
                  <div className="text-xs font-bold text-white group-hover:text-indigo-400 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Super Admin</span>
                  </div>
                  <div className="text-[10px] text-slate-500 truncate mt-0.5">superadmin@invenza...</div>
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickDemo('company_admin')}
                  className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-indigo-500/50 text-left transition-all group"
                >
                  <div className="text-xs font-bold text-white group-hover:text-indigo-400 flex items-center gap-1.5">
                    <KeyRound className="w-3.5 h-3.5 text-purple-400" />
                    <span>Company Admin</span>
                  </div>
                  <div className="text-[10px] text-slate-500 truncate mt-0.5">admin@invenza...</div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
