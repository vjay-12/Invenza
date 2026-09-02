import React, { useState, useEffect } from 'react';
import {
  Building2,
  Plus,
  Search,
  CheckCircle2,
  XCircle,
  BarChart3,
  Edit,
  Power,
  Shield,
  Send,
  Eye,
  EyeOff,
  RefreshCw,
  Sliders,
  FileText,
  Download,
  AlertCircle,
  Package,
  Users,
  MapPin,
  DollarSign,
  Layers,
  Sparkles,
  Key,
} from 'lucide-react';
import { api } from '../services/api';

export const INDUSTRIES_LIST = [
  'Retail & E-commerce',
  'Pharmaceuticals & Healthcare',
  'Manufacturing & Assembly',
  'Food & Beverage',
  'Electronics & High-Tech',
  'Logistics & Warehousing',
  'Chemicals & Energy',
  'Fashion & Apparel',
  'Construction & Materials',
  'Automotive & Aerospace',
  'General Merchandise',
];

export const AVAILABLE_MODULES = [
  { id: 'products', label: 'Products & SKUs', desc: 'Item catalog, categories, pricing, variants' },
  { id: 'locations', label: 'Warehouses & Locations', desc: 'Storage bins, facilities, capacities' },
  { id: 'orders', label: 'Purchase & Sales Orders', desc: 'PO receipt (GRN) and SO fulfillment' },
  { id: 'transfers', label: 'Stock Transfers', desc: 'Inter-warehouse movement logs' },
  { id: 'adjustments', label: 'Manual Adjustments', desc: 'Cycle counting and shrinkage reason codes' },
  { id: 'ledger', label: 'Immutable Audit Ledger', desc: 'Cryptographic append-only movement stream' },
  { id: 'reports', label: 'Valuation & Reports', desc: 'FIFO and Weighted Average costing analytics' },
  { id: 'storage', label: 'MinIO Document Storage', desc: 'Compliance certificates & file uploads' },
];

export const SuperAdminConsole: React.FC = () => {
  const [companies, setCompanies] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIndustry, setSelectedIndustry] = useState('all');
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Modal States
  const [isProvisionModalOpen, setIsProvisionModalOpen] = useState(false);
  const [isAnalyticsModalOpen, setIsAnalyticsModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  const [activeCompanyForAnalytics, setActiveCompanyForAnalytics] = useState<any>(null);
  const [analyticsData, setAnalyticsData] = useState<any>(null);
  const [platformReport, setPlatformReport] = useState<any>(null);
  const [companyToEdit, setCompanyToEdit] = useState<any>(null);

  // Provision Form State
  const [provCompanyName, setProvCompanyName] = useState('');
  const [provIndustry, setProvIndustry] = useState(INDUSTRIES_LIST[0]);
  const [provLocation, setProvLocation] = useState('');
  const [provCurrency, setProvCurrency] = useState('USD');
  const [provAdminName, setProvAdminName] = useState('');
  const [provAdminEmail, setProvAdminEmail] = useState('');
  const [provAdminPassword, setProvAdminPassword] = useState('');
  const [provShowPassword, setProvShowPassword] = useState(false);
  const [provModules, setProvModules] = useState<string[]>([
    'products', 'locations', 'orders', 'transfers', 'adjustments', 'ledger', 'reports', 'storage'
  ]);
  const [provSendEmail, setProvSendEmail] = useState(true);
  const [isSubmittingProvision, setIsSubmittingProvision] = useState(false);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const loadCompanies = async () => {
    setIsLoading(true);
    try {
      const data = await api.getCompanies(
        searchTerm || undefined,
        selectedIndustry !== 'all' ? selectedIndustry : undefined
      );
      if (data) {
        setCompanies(data);
      }
    } catch (err: any) {
      showToast('Failed to load companies list', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCompanies();
  }, [selectedIndustry]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadCompanies();
  };

  const generateRandomPassword = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%&*';
    let pwd = '';
    for (let i = 0; i < 14; i++) {
      pwd += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setProvAdminPassword(pwd);
    setProvShowPassword(true);
  };

  const handleProvisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!provCompanyName.trim() || !provAdminName.trim() || !provAdminEmail.trim() || !provAdminPassword.trim()) {
      showToast('Please fill in all required fields.', 'error');
      return;
    }

    setIsSubmittingProvision(true);
    try {
      await api.provisionCompany({
        company_name: provCompanyName.trim(),
        industry: provIndustry,
        location: provLocation.trim() || 'Headquarters',
        currency_code: provCurrency,
        admin_full_name: provAdminName.trim(),
        admin_email: provAdminEmail.trim().toLowerCase(),
        admin_password: provAdminPassword.trim(),
        enabled_modules: provModules,
        send_email: provSendEmail,
      });

      showToast(`Company '${provCompanyName}' provisioned! Welcome email dispatched to ${provAdminEmail}.`);
      setIsProvisionModalOpen(false);
      resetProvisionForm();
      loadCompanies();
    } catch (err: any) {
      showToast(err.message || 'Failed to provision company.', 'error');
    } finally {
      setIsSubmittingProvision(false);
    }
  };

  const resetProvisionForm = () => {
    setProvCompanyName('');
    setProvIndustry(INDUSTRIES_LIST[0]);
    setProvLocation('');
    setProvCurrency('USD');
    setProvAdminName('');
    setProvAdminEmail('');
    setProvAdminPassword('');
    setProvModules(['products', 'locations', 'orders', 'transfers', 'adjustments', 'ledger', 'reports', 'storage']);
    setProvSendEmail(true);
  };

  const handleToggleStatus = async (company: any) => {
    try {
      const res = await api.toggleCompanyStatus(company.id);
      if (res && res.success) {
        showToast(res.message);
        loadCompanies();
      }
    } catch (err: any) {
      showToast('Failed to toggle status', 'error');
    }
  };

  const handleOpenAnalytics = async (company: any) => {
    setActiveCompanyForAnalytics(company);
    setIsAnalyticsModalOpen(true);
    setAnalyticsData(null);
    try {
      const data = await api.getCompanyAnalytics(company.id);
      setAnalyticsData(data);
    } catch (err: any) {
      showToast('Failed to fetch company analytics', 'error');
    }
  };

  const handleOpenEdit = (company: any) => {
    setCompanyToEdit({
      ...company,
      enabled_modules: company.enabled_modules || [],
    });
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyToEdit) return;
    try {
      await api.updateCompany(companyToEdit.id, {
        name: companyToEdit.name,
        industry: companyToEdit.industry,
        location: companyToEdit.location,
        currency_code: companyToEdit.currency_code,
        enabled_modules: companyToEdit.enabled_modules,
        is_active: companyToEdit.is_active,
      });
      showToast(`Company '${companyToEdit.name}' updated successfully.`);
      setIsEditModalOpen(false);
      loadCompanies();
    } catch (err: any) {
      showToast('Failed to update company.', 'error');
    }
  };

  const handleOpenReport = async () => {
    setIsReportModalOpen(true);
    try {
      const data = await api.getPlatformReport();
      setPlatformReport(data);
    } catch (err) {
      showToast('Failed to generate platform report', 'error');
    }
  };

  const exportReportCSV = () => {
    if (!platformReport || !platformReport.companies) return;
    const headers = ['Company ID', 'Company Name', 'Industry', 'Location', 'Status', 'Created At'];
    const rows = platformReport.companies.map((c: any) => [
      c.id,
      `"${c.name}"`,
      `"${c.industry}"`,
      `"${c.location}"`,
      c.is_active ? 'Active' : 'Deactivated',
      c.created_at,
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e: any[]) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Invenza_Platform_Report_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleModuleSelection = (modId: string) => {
    setProvModules((prev) =>
      prev.includes(modId) ? prev.filter((m) => m !== modId) : [...prev, modId]
    );
  };

  const toggleEditModuleSelection = (modId: string) => {
    if (!companyToEdit) return;
    const current = companyToEdit.enabled_modules || [];
    const updated = current.includes(modId)
      ? current.filter((m: string) => m !== modId)
      : [...current, modId];
    setCompanyToEdit({ ...companyToEdit, enabled_modules: updated });
  };

  // KPIs
  const totalCompaniesCount = companies.length;
  const activeCount = companies.filter((c) => c.is_active).length;
  const totalIndustriesCount = new Set(companies.map((c) => c.industry)).size;
  const totalProductsAcross = companies.reduce((acc, c) => acc + (c.product_count || 0), 0);

  return (
    <div className="space-y-8 animate-in fade-in duration-300 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-2xl shadow-2xl flex items-center gap-3 border text-sm font-semibold animate-in slide-in-from-top duration-200 ${
          toastMessage.type === 'success'
            ? 'bg-emerald-950/90 border-emerald-500/40 text-emerald-300 backdrop-blur-xl'
            : 'bg-rose-950/90 border-rose-500/40 text-rose-300 backdrop-blur-xl'
        }`}>
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-slate-800 relative overflow-hidden shadow-xl">
        <div className="absolute -right-20 -top-20 w-80 h-80 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-400 text-xs font-semibold border border-indigo-500/30 mb-3">
            <Shield className="w-3.5 h-3.5" />
            <span>Master Super Administrator Core</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
            Enterprise Company & Tenant Management
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Provision dedicated organizations by industry, manage tenant lifecycles, inspect live cross-company analytics, and dispatch admin credentials.
          </p>
        </div>

        <div className="flex items-center gap-3 relative z-10">
          <button
            onClick={handleOpenReport}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-bold flex items-center gap-2 transition-all"
          >
            <FileText className="w-4 h-4 text-indigo-400" />
            <span>Platform Report</span>
          </button>
          <button
            onClick={() => {
              generateRandomPassword();
              setIsProvisionModalOpen(true);
            }}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-500/20 flex items-center gap-2 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Provision New Company</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Companies</span>
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-500">
              <Building2 className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white mt-2">{totalCompaniesCount}</div>
          <div className="text-xs text-slate-500 mt-1">Global enterprise tenants</div>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Active Organizations</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-500">
              <Power className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-emerald-500 mt-2">{activeCount}</div>
          <div className="text-xs text-slate-500 mt-1">{totalCompaniesCount - activeCount} deactivated accounts</div>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Industries Served</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-500">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white mt-2">{totalIndustriesCount}</div>
          <div className="text-xs text-slate-500 mt-1">Custom domain models</div>
        </div>

        <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Platform SKUs</span>
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-500">
              <Package className="w-5 h-5" />
            </div>
          </div>
          <div className="text-2xl font-black text-slate-900 dark:text-white mt-2">{totalProductsAcross}</div>
          <div className="text-xs text-slate-500 mt-1">Cross-tenant inventory items</div>
        </div>
      </div>

      {/* Action Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search company, industry, or location..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:border-indigo-500"
          />
        </form>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500">
            <Sliders className="w-3.5 h-3.5" />
            <span>Industry:</span>
          </div>
          <select
            value={selectedIndustry}
            onChange={(e) => setSelectedIndustry(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="all">All Industries</option>
            {INDUSTRIES_LIST.map((ind) => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>

          <button
            onClick={loadCompanies}
            className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-indigo-500 transition-colors"
            title="Refresh Directory"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Companies Directory Table */}
      <div className="rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-400 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-4">Company & Slug</th>
                <th className="px-6 py-4">Industry Domain</th>
                <th className="px-6 py-4">Location</th>
                <th className="px-6 py-4">Admin Account</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Metrics</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
              {companies.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-12 text-center text-slate-500">
                    <Building2 className="w-8 h-8 mx-auto mb-2 text-slate-400 opacity-50" />
                    <p className="font-semibold">No companies found matching criteria.</p>
                  </td>
                </tr>
              ) : (
                companies.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                    {/* Company Name */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-500 font-bold text-sm border border-indigo-500/20">
                          {c.name.charAt(0)}
                        </div>
                        <div>
                          <div className="font-bold text-slate-900 dark:text-white text-sm">{c.name}</div>
                          <div className="text-[11px] text-slate-400 font-mono">/{c.slug}</div>
                        </div>
                      </div>
                    </td>

                    {/* Industry */}
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20 font-semibold text-[11px]">
                        <Layers className="w-3 h-3" />
                        <span>{c.industry}</span>
                      </span>
                    </td>

                    {/* Location */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-slate-600 dark:text-slate-300">
                        <MapPin className="w-3.5 h-3.5 text-slate-400" />
                        <span>{c.location || 'HQ'}</span>
                      </div>
                    </td>

                    {/* Admin */}
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-800 dark:text-slate-200">{c.admin_name || 'Admin'}</div>
                      <div className="text-[11px] text-slate-400 truncate">{c.admin_email || '—'}</div>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleToggleStatus(c)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold transition-all ${
                          c.is_active
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20'
                            : 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20'
                        }`}
                        title="Click to toggle status"
                      >
                        <span className={`w-1.5 h-1.5 rounded-full ${c.is_active ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
                        <span>{c.is_active ? 'Active' : 'Deactivated'}</span>
                      </button>
                    </td>

                    {/* Metrics */}
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3 text-slate-500 text-[11px]">
                        <span title="Products in company">
                          <strong>{c.product_count}</strong> SKUs
                        </span>
                        <span>&bull;</span>
                        <span title="Users in company">
                          <strong>{c.user_count}</strong> Users
                        </span>
                      </div>
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleOpenAnalytics(c)}
                          className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-indigo-500 transition-colors"
                          title="View Live Analytics"
                        >
                          <BarChart3 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleOpenEdit(c)}
                          className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-indigo-500 transition-colors"
                          title="Edit Company Details"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* PROVISION NEW COMPANY MODAL */}
      {isProvisionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl relative max-h-[90vh] flex flex-col overflow-hidden">
            {/* Modal Header - Always visible at top */}
            <div className="flex items-center justify-between border-b border-slate-800 px-6 sm:px-8 py-5 shrink-0 bg-slate-900 z-10">
              <div>
                <div className="flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-xl font-bold text-white">Provision New Company & Admin</h3>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Creates a clean-slate tenant workspace tailored to the chosen industry and sends credentials via email.
                </p>
              </div>
              <button
                onClick={() => setIsProvisionModalOpen(false)}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                &times;
              </button>
            </div>

            {/* Modal Form Container with Scrollable Body */}
            <form onSubmit={handleProvisionSubmit} className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="p-6 sm:p-8 overflow-y-auto flex-1 space-y-6">
                {/* Section 1: Company Profile */}
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3 flex items-center gap-1.5">
                    <span>1. Company Profile & Industry</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Company Name *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Apex BioPharma"
                        value={provCompanyName}
                        onChange={(e) => setProvCompanyName(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Industry Domain *</label>
                      <select
                        value={provIndustry}
                        onChange={(e) => setProvIndustry(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-semibold text-white focus:outline-none focus:border-indigo-500"
                      >
                        {INDUSTRIES_LIST.map((ind) => (
                          <option key={ind} value={ind}>{ind}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">HQ / Facility Location</label>
                      <input
                        type="text"
                        placeholder="e.g. Chicago, IL, USA"
                        value={provLocation}
                        onChange={(e) => setProvLocation(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Base Currency</label>
                      <select
                        value={provCurrency}
                        onChange={(e) => setProvCurrency(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-semibold text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="USD">USD ($)</option>
                        <option value="EUR">EUR (€)</option>
                        <option value="GBP">GBP (£)</option>
                        <option value="INR">INR (₹)</option>
                        <option value="CAD">CAD ($)</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Section 2: Admin Account */}
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3 flex items-center gap-1.5">
                    <span>2. Admin Account Credentials</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Admin Full Name *</label>
                      <input
                        type="text"
                        required
                        placeholder="e.g. Sarah Connor"
                        value={provAdminName}
                        onChange={(e) => setProvAdminName(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1">Admin Work Email *</label>
                      <input
                        type="email"
                        required
                        placeholder="admin@company.com"
                        value={provAdminEmail}
                        onChange={(e) => setProvAdminEmail(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <div className="flex items-center justify-between mb-1">
                        <label className="block text-xs font-semibold text-slate-300">Initial Password *</label>
                        <button
                          type="button"
                          onClick={generateRandomPassword}
                          className="text-[11px] font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                        >
                          <Sparkles className="w-3 h-3" />
                          <span>Generate Secure Password</span>
                        </button>
                      </div>
                      <div className="relative">
                        <input
                          type={provShowPassword ? 'text' : 'password'}
                          required
                          value={provAdminPassword}
                          onChange={(e) => setProvAdminPassword(e.target.value)}
                          placeholder="••••••••••••"
                          className="w-full pl-3.5 pr-10 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white font-mono placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                        />
                        <button
                          type="button"
                          onClick={() => setProvShowPassword(!provShowPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                        >
                          {provShowPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Section 3: Enabled Modules Checklist */}
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3 flex items-center gap-1.5">
                    <span>3. Enabled Modules for this Company</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {AVAILABLE_MODULES.map((mod) => {
                      const isChecked = provModules.includes(mod.id);
                      return (
                        <div
                          key={mod.id}
                          onClick={() => toggleModuleSelection(mod.id)}
                          className={`p-3 rounded-xl border cursor-pointer transition-all flex items-start gap-2.5 ${
                            isChecked
                              ? 'bg-indigo-950/40 border-indigo-500/50 text-white'
                              : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                          }`}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => {}}
                            className="mt-0.5 rounded border-slate-700 text-indigo-600 focus:ring-0"
                          />
                          <div>
                            <div className="text-xs font-bold text-slate-200">{mod.label}</div>
                            <div className="text-[10px] text-slate-500 leading-tight mt-0.5">{mod.desc}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Section 4: Email Dispatch Toggle */}
                <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-indigo-500 text-white">
                      <Send className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-bold text-white">Send Credentials via Email</div>
                      <div className="text-[11px] text-indigo-300">
                        Dispatches welcome email with login details directly to the newly provisioned Admin.
                      </div>
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={provSendEmail}
                    onChange={(e) => setProvSendEmail(e.target.checked)}
                    className="h-5 w-5 rounded border-slate-700 text-indigo-600 focus:ring-0 cursor-pointer"
                  />
                </div>
              </div>

              {/* Modal Footer - Always cleanly visible at bottom */}
              <div className="flex items-center justify-end gap-3 px-6 sm:px-8 py-4 border-t border-slate-800 shrink-0 bg-slate-900/95 backdrop-blur-md">
                <button
                  type="button"
                  onClick={() => setIsProvisionModalOpen(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-300 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingProvision}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-500/20 flex items-center gap-2 disabled:opacity-50 transition-all"
                >
                  {isSubmittingProvision ? (
                    <span>Provisioning Organization...</span>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Provision Company & Admin</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LIVE ANALYTICS MODAL */}
      {isAnalyticsModalOpen && activeCompanyForAnalytics && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl relative max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 sm:px-8 py-5 shrink-0 bg-slate-900">
              <div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30 uppercase tracking-wider">
                  {activeCompanyForAnalytics.industry}
                </span>
                <h3 className="text-xl font-bold text-white mt-1">{activeCompanyForAnalytics.name}</h3>
                <p className="text-xs text-slate-400">Live operational inventory metrics</p>
              </div>
              <button
                onClick={() => setIsAnalyticsModalOpen(false)}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                &times;
              </button>
            </div>

            <div className="p-6 sm:p-8 overflow-y-auto flex-1">
              {!analyticsData ? (
                <div className="py-12 text-center text-slate-400">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                  <p className="text-xs">Fetching live metrics from database...</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                      <div className="text-[11px] font-bold text-slate-500 uppercase">Inventory SKUs</div>
                      <div className="text-2xl font-black text-white mt-1">{analyticsData.total_products}</div>
                      <div className="text-[10px] text-slate-500">Active catalog items</div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                      <div className="text-[11px] font-bold text-slate-500 uppercase">Total Valuation</div>
                      <div className="text-2xl font-black text-emerald-400 mt-1">
                        ${analyticsData.total_inventory_valuation.toLocaleString()}
                      </div>
                      <div className="text-[10px] text-slate-500">Cost valuation</div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                      <div className="text-[11px] font-bold text-slate-500 uppercase">Movement Transactions</div>
                      <div className="text-2xl font-black text-indigo-400 mt-1">{analyticsData.total_movements}</div>
                      <div className="text-[10px] text-slate-500">Immutable ledger events</div>
                    </div>

                    <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800">
                      <div className="text-[11px] font-bold text-slate-500 uppercase">Company Users</div>
                      <div className="text-2xl font-black text-purple-400 mt-1">{analyticsData.total_users}</div>
                      <div className="text-[10px] text-slate-500">Active staff & admins</div>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-semibold">Account Status:</span>
                    <span className={`px-2.5 py-1 rounded-full font-bold ${
                      analyticsData.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                    }`}>
                      {analyticsData.is_active ? 'Active & Accessible' : 'Deactivated by Super Admin'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* EDIT COMPANY MODAL */}
      {isEditModalOpen && companyToEdit && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl relative max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 sm:px-8 py-5 shrink-0 bg-slate-900">
              <h3 className="text-xl font-bold text-white">Edit Company Metadata</h3>
              <button
                onClick={() => setIsEditModalOpen(false)}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="p-6 sm:p-8 overflow-y-auto flex-1 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Company Name</label>
                  <input
                    type="text"
                    value={companyToEdit.name}
                    onChange={(e) => setCompanyToEdit({ ...companyToEdit, name: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Industry</label>
                  <select
                    value={companyToEdit.industry}
                    onChange={(e) => setCompanyToEdit({ ...companyToEdit, industry: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs font-semibold text-white focus:outline-none focus:border-indigo-500"
                  >
                    {INDUSTRIES_LIST.map((ind) => (
                      <option key={ind} value={ind}>{ind}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Location</label>
                  <input
                    type="text"
                    value={companyToEdit.location || ''}
                    onChange={(e) => setCompanyToEdit({ ...companyToEdit, location: e.target.value })}
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">Enabled Modules</label>
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                    {AVAILABLE_MODULES.map((mod) => {
                      const isChecked = (companyToEdit.enabled_modules || []).includes(mod.id);
                      return (
                        <label
                          key={mod.id}
                          className="flex items-center gap-2 p-2 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 cursor-pointer hover:border-slate-700"
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleEditModuleSelection(mod.id)}
                            className="rounded border-slate-700 text-indigo-600 focus:ring-0"
                          />
                          <span className="truncate">{mod.label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 px-6 sm:px-8 py-4 border-t border-slate-800 shrink-0 bg-slate-900/95">
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-xs font-bold text-slate-300 hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow-lg shadow-indigo-500/20 transition-all"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PLATFORM REPORT MODAL */}
      {isReportModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl relative max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-800 px-6 sm:px-8 py-5 shrink-0 bg-slate-900">
              <div>
                <h3 className="text-xl font-bold text-white">Global Platform Executive Report</h3>
                <p className="text-xs text-slate-400">Aggregated cross-company statistics and tenant audit summary.</p>
              </div>
              <button
                onClick={() => setIsReportModalOpen(false)}
                className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              >
                &times;
              </button>
            </div>

            <div className="p-6 sm:p-8 overflow-y-auto flex-1">
              {!platformReport ? (
                <div className="py-12 text-center text-slate-400">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                  <p className="text-xs">Generating platform summary...</p>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-bold text-slate-400 uppercase">Total Tenants</div>
                      <div className="text-xl font-black text-white mt-1">{platformReport.total_companies}</div>
                    </div>
                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-bold text-slate-400 uppercase">Active / Inactive</div>
                      <div className="text-xl font-black text-emerald-400 mt-1">
                        {platformReport.active_companies} / {platformReport.inactive_companies}
                      </div>
                    </div>
                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800">
                      <div className="text-[10px] font-bold text-slate-400 uppercase">Global Products</div>
                      <div className="text-xl font-black text-indigo-400 mt-1">{platformReport.total_products}</div>
                    </div>
                  </div>

                  <div>
                    <div className="text-xs font-bold text-slate-300 mb-2">Industry Distribution:</div>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(platformReport.industries_breakdown || {}).map(([ind, cnt]) => (
                        <span key={ind} className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300">
                          {ind}: <strong className="text-indigo-400">{cnt as number}</strong>
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {platformReport && (
              <div className="flex items-center justify-between px-6 sm:px-8 py-4 border-t border-slate-800 shrink-0 bg-slate-900/95">
                <span className="text-[11px] text-slate-500">
                  Format: RFC-4180 Standard CSV Export
                </span>
                <button
                  onClick={exportReportCSV}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition-all"
                >
                  <Download className="w-4 h-4" />
                  <span>Download CSV Report</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
