import React, { useState, useEffect } from 'react';
import {
  IconShieldCheck as Shield,
  IconCheck as CheckCircle2,
  IconAlertCircle as AlertCircle,
  IconAlertTriangle as AlertTriangle,
  IconRefreshCw as RefreshCw,
  IconClock as Clock,
  IconUsers as Users,
  IconBuilding as Building2,
  IconIndianRupee as IndianRupee,
  IconFileText as FileText,
  IconSearch as Search,
  IconEye as Eye,
  IconSlidersHorizontal as Sliders,
  IconLayers as Layers,
} from '../components/icons';
import { api } from '../services/api';
import { PageMeta } from '../components/common/PageMeta';
import { SimpleSelectDropdown, DropdownOption } from '../components/common/SimpleSelectDropdown';

interface SecuritySafeguardsProps {
  onNavigate?: (tab: string, params?: Record<string, string>) => void;
}

export const SecuritySafeguards: React.FC<SecuritySafeguardsProps> = ({ onNavigate }) => {
  const [activeSection, setActiveSection] = useState<'queue' | 'audit'>('queue');
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Approval Queue State
  const [queueRequests, setQueueRequests] = useState<any[]>([]);
  const [isLoadingQueue, setIsLoadingQueue] = useState(true);
  const [queueStatusFilter, setQueueStatusFilter] = useState<string>('all');
  const [queueActionFilter, setQueueActionFilter] = useState<string>('all');
  const [queueSearchTerm, setQueueSearchTerm] = useState<string>('');
  const [processingRequestId, setProcessingRequestId] = useState<string | null>(null);

  // Confirmation Modal for High-Impact Approval/Rejection
  const [actionConfirmModal, setActionConfirmModal] = useState<{
    type: 'approve' | 'reject';
    request: any;
  } | null>(null);
  const [actionNotes, setActionNotes] = useState('');

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);
  const [auditActionFilter, setAuditActionFilter] = useState<string>('all');
  const [auditSearchTerm, setAuditSearchTerm] = useState('');
  const [selectedAuditLogForDetail, setSelectedAuditLogForDetail] = useState<any | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const loadQueue = async () => {
    setIsLoadingQueue(true);
    try {
      const data = await api.getSecurityRequests(queueStatusFilter);
      if (Array.isArray(data)) {
        setQueueRequests(data);
      }
    } catch (err: any) {
      console.warn('Failed to load safeguards queue:', err);
      showToast('Failed to fetch approval queue', 'error');
    } finally {
      setIsLoadingQueue(false);
    }
  };

  const loadAuditLogs = async () => {
    setIsLoadingAudit(true);
    try {
      const data = await api.getAuditLogs({
        action_type: auditActionFilter,
        search: auditSearchTerm || undefined,
        limit: 100,
      });
      if (Array.isArray(data)) {
        setAuditLogs(data);
      }
    } catch (err: any) {
      console.warn('Failed to load audit logs:', err);
      showToast('Failed to fetch audit log', 'error');
    } finally {
      setIsLoadingAudit(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [queueStatusFilter]);

  useEffect(() => {
    if (activeSection === 'audit') {
      loadAuditLogs();
    }
  }, [activeSection, auditActionFilter]);

  const handleExecuteApproval = async () => {
    if (!actionConfirmModal) return;
    const req = actionConfirmModal.request;
    setProcessingRequestId(req.id);
    try {
      await api.approveSecurityRequest(req.id, actionNotes);
      showToast(`Privileged action "${formatActionLabel(req.action_type)}" approved and executed for ${req.tenant_name}.`);
      setActionConfirmModal(null);
      setActionNotes('');
      loadQueue();
      if (activeSection === 'audit') loadAuditLogs();
    } catch (err: any) {
      showToast(err.message || 'Failed to approve request', 'error');
    } finally {
      setProcessingRequestId(null);
    }
  };

  const handleExecuteRejection = async () => {
    if (!actionConfirmModal) return;
    const req = actionConfirmModal.request;
    setProcessingRequestId(req.id);
    try {
      await api.rejectSecurityRequest(req.id, actionNotes || 'Rejected by Super Administrator');
      showToast(`Request "${formatActionLabel(req.action_type)}" rejected for ${req.tenant_name}.`);
      setActionConfirmModal(null);
      setActionNotes('');
      loadQueue();
      if (activeSection === 'audit') loadAuditLogs();
    } catch (err: any) {
      showToast(err.message || 'Failed to reject request', 'error');
    } finally {
      setProcessingRequestId(null);
    }
  };

  // Helper formatting
  const formatActionLabel = (act: string) => {
    return act
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const getActionBadgeColor = (act: string) => {
    if (act.includes('purge') || act.includes('remove_last_admin') || act.includes('deactivate')) {
      return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/25';
    }
    if (act.includes('fee') || act.includes('billing')) {
      return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/25';
    }
    return 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-500/25';
  };

  const pendingQueueCount = queueRequests.filter((r) => r.status === 'pending').length;

  const queueFilterOptions: DropdownOption[] = [
    { value: 'all', label: `All Requests (${queueRequests.length})` },
    { value: 'pending', label: `Pending Approvals (${pendingQueueCount})` },
    { value: 'approved', label: 'Approved Actions' },
    { value: 'rejected', label: 'Rejected Actions' },
  ];

  const queueActionOptions: DropdownOption[] = [
    { value: 'all', label: 'All Action Types' },
    { value: 'ledger_purge', label: 'Ledger Purge' },
    { value: 'export_customer_data', label: 'Export Customer Data' },
    { value: 'remove_last_admin', label: 'Remove Last Admin' },
    { value: 'waive_maintenance_fee', label: 'Waive Maintenance Fee' },
    { value: 'deactivate_tenant', label: 'Deactivate Organization' },
  ];

  const filteredQueueRequests = queueRequests.filter((r) => {
    if (queueActionFilter !== 'all' && r.action_type !== queueActionFilter) return false;
    if (queueSearchTerm.trim()) {
      const q = queueSearchTerm.toLowerCase();
      const match =
        r.action_type?.toLowerCase().includes(q) ||
        r.tenant_name?.toLowerCase().includes(q) ||
        r.requester_name?.toLowerCase().includes(q) ||
        r.requester_email?.toLowerCase().includes(q) ||
        r.target_id?.toLowerCase().includes(q) ||
        r.reason?.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const auditActionOptions: DropdownOption[] = [
    { value: 'all', label: 'All Action Categories' },
    { value: 'company_provisioned', label: 'Company Provisioning' },
    { value: 'company_updated', label: 'Company Detail Updates' },
    { value: 'company_activated', label: 'Company Activations' },
    { value: 'company_deactivated', label: 'Company Deactivations' },
    { value: 'role_changed', label: 'Role & Tier Reassignments' },
    { value: 'permissions_updated', label: 'Permission Overrides' },
    { value: 'member_status_changed', label: 'Member Suspensions' },
    { value: 'billing_fee_updated', label: 'Maintenance Fee Changes' },
    { value: 'setup_fee_updated', label: 'Setup Fee Modifications' },
    { value: 'payment_recorded', label: 'Payment Records' },
    { value: 'lead_status_updated', label: 'Lead Pipeline Updates' },
    { value: 'ledger_purge', label: 'Ledger Purge Authorizations' },
  ];

  return (
    <div className="space-y-4 animate-in fade-in duration-200 pb-6">
      <PageMeta
        title="Security Safeguards & Compliance | Invenza Platform"
        description="Dual-authorization approval queue for high-impact platform actions and compliance-grade audit logging."
        canonicalPath="/security-safeguards"
      />

      {/* Toast Alert */}
      {toastMessage && (
        <div
          className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 border text-sm font-semibold animate-in slide-in-from-top duration-200 ${
            toastMessage.type === 'success'
              ? 'bg-emerald-50 border-emerald-300 text-emerald-700 dark:bg-emerald-950/90 dark:border-emerald-500/40 dark:text-emerald-300 backdrop-blur-xl'
              : 'bg-rose-50 border-rose-300 text-rose-700 dark:bg-rose-950/90 dark:border-rose-500/40 dark:text-rose-300 backdrop-blur-xl'
          }`}
        >
          {toastMessage.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3.5 p-3.5 sm:p-4 rounded-xl bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 shadow-card">
        <div>
          <div className="flex items-center gap-1.5 text-xs font-mono font-medium text-teal-600 dark:text-teal-400 mb-1">
            <Shield className="w-3.5 h-3.5" />
            <span>Multi-Tenant Platform Governance</span>
          </div>
          <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Security Safeguards & Dual Authorization
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 max-w-2xl leading-relaxed">
            Protect tenant integrity through two-man rule sign-offs on sensitive actions and inspect tamper-evident audit logs across the entire platform.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={activeSection === 'queue' ? loadQueue : loadAuditLogs}
            className="px-3.5 py-2 rounded-lg bg-white dark:bg-[#131924] hover:bg-slate-100 dark:hover:bg-[#1A2232] border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-2 transition-all shadow-subtle"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-teal-500 ${(isLoadingQueue || isLoadingAudit) ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Sub-Section Tab Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-2">
        <button
          type="button"
          onClick={() => setActiveSection('queue')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
            activeSection === 'queue'
              ? 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/30'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Approval Queue</span>
          {pendingQueueCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-amber-500 text-white animate-pulse">
              {pendingQueueCount}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveSection('audit')}
          className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold transition-all ${
            activeSection === 'audit'
              ? 'bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/30'
              : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Privileged Audit Log</span>
          <span className="text-[10px] font-mono text-slate-400">12 Mo. Retained</span>
        </button>
      </div>

      {/* SECTION A: APPROVAL QUEUE */}
      {activeSection === 'queue' && (
        <div className="space-y-3.5">
          {/* Action Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3 rounded-xl bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 shadow-card">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search by action, organization, requester email, reference ID..."
                value={queueSearchTerm}
                onChange={(e) => setQueueSearchTerm(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#F8FAFC] dark:bg-[#0C1017] border border-slate-200 dark:border-slate-800 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-teal-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <div className="w-48 shrink-0">
                <SimpleSelectDropdown
                  options={queueActionOptions}
                  value={queueActionFilter}
                  onChange={setQueueActionFilter}
                  placeholder="Action Type"
                />
              </div>
              <div className="w-48 shrink-0">
                <SimpleSelectDropdown
                  options={queueFilterOptions}
                  value={queueStatusFilter}
                  onChange={setQueueStatusFilter}
                  placeholder="Filter Status"
                />
              </div>
            </div>
          </div>

          {/* Queue Items Table */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] overflow-hidden shadow-card">
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left text-xs table-fixed min-w-[900px]">
                <thead className="bg-[#F8FAFC] dark:bg-[#0C1017] border-b border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-semibold text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="w-[26%] px-3.5 py-2.5">Action Requested</th>
                    <th className="w-[20%] px-3.5 py-2.5">Target Organization</th>
                    <th className="w-[22%] px-3.5 py-2.5">Requester Details</th>
                    <th className="w-[12%] px-3.5 py-2.5">Requested At</th>
                    <th className="w-[10%] px-3.5 py-2.5">Status</th>
                    <th className="w-[10%] px-3.5 py-2.5 text-right">Decision</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                  {filteredQueueRequests.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-14 text-center text-slate-500">
                        <Shield className="w-8 h-8 mx-auto mb-2 text-slate-400 opacity-60" />
                        <p className="font-semibold text-sm">No requests found matching criteria</p>
                        <p className="text-xs text-slate-400 mt-1">
                          When sensitive actions (ledger purges, last-admin removals, fee waivers) are initiated, they appear here for dual approval.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    filteredQueueRequests.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
                        {/* Action Requested */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <div className="flex flex-col min-w-0" title={r.reason || formatActionLabel(r.action_type)}>
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className={`inline-flex items-center gap-1 font-mono font-bold text-[10px] px-2 py-0.5 rounded-md border shrink-0 ${getActionBadgeColor(r.action_type)}`}>
                                {formatActionLabel(r.action_type)}
                              </span>
                              {(r.target_id || r.details?.reference_code) && (
                                <span className="font-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20 shrink-0">
                                  {r.target_id || r.details?.reference_code}
                                </span>
                              )}
                            </div>
                            {r.target_name && (
                              <span className="text-[10px] font-medium text-slate-600 dark:text-slate-300 mt-0.5 truncate">
                                Scope: {r.target_name}
                              </span>
                            )}
                            {r.reason && (
                              <span className="text-[11px] text-slate-500 dark:text-slate-400 truncate italic mt-0.5">
                                "{r.reason}"
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Target Organization */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 min-w-0" title={`${r.tenant_name || 'All Organizations'} • ID: ${r.tenant_id}`}>
                            <span className="font-bold text-slate-900 dark:text-white truncate">
                              {r.tenant_name || 'All Organizations'}
                            </span>
                            {r.tenant_id && (
                              <span className="text-[10px] font-mono text-slate-400 truncate">
                                &bull; {r.tenant_id.slice(0, 8)}...
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Requester */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 min-w-0" title={`${r.requester_name || 'Administrator'} • ${r.requester_email}`}>
                            <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                              {r.requester_name || 'Administrator'}
                            </span>
                            <span className="text-[11px] text-slate-400 font-normal truncate">
                              &bull; {r.requester_email}
                            </span>
                          </div>
                        </td>

                        {/* Timestamp */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap text-[11px] font-mono text-slate-500">
                          {new Date(r.created_at).toLocaleDateString()} {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>

                        {/* Status */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${
                              r.status === 'approved'
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/25'
                                : r.status === 'rejected'
                                ? 'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/25'
                                : 'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/25 animate-pulse'
                            }`}
                          >
                            {r.status.toUpperCase()}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="px-3.5 py-2.5 text-right whitespace-nowrap">
                          {r.status === 'pending' ? (
                            <div className="inline-flex items-center justify-end gap-1.5">
                              <button
                                type="button"
                                disabled={processingRequestId === r.id}
                                onClick={() => setActionConfirmModal({ type: 'approve', request: r })}
                                className="px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-[10px] shadow-subtle transition-colors"
                              >
                                Approve
                              </button>
                              <button
                                type="button"
                                disabled={processingRequestId === r.id}
                                onClick={() => setActionConfirmModal({ type: 'reject', request: r })}
                                className="px-2.5 py-1 rounded-md bg-rose-600 hover:bg-rose-700 text-white font-bold text-[10px] shadow-subtle transition-colors"
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span className="text-[11px] text-slate-400 font-mono truncate inline-block max-w-[140px]" title={r.status === 'rejected' ? `Rejected: ${r.rejection_reason || 'Denied'}` : `Signed: ${r.reviewer_name || 'Admin'}`}>
                              {r.status === 'rejected' ? 'Rejected' : `Signed: ${r.reviewer_name?.split('@')[0]?.split(' ')[0] || 'Admin'}`}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECTION B: AUDIT LOG */}
      {activeSection === 'audit' && (
        <div className="space-y-3.5">
          {/* Compliance Retention Banner */}
          <div className="p-3 rounded-xl bg-teal-500/10 border border-teal-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2 text-teal-700 dark:text-teal-300 font-medium">
              <Shield className="w-4 h-4 text-teal-500 shrink-0" />
              <span>
                <strong>Compliance Retention Standard:</strong> All privileged administrative actions across organizations, roles, and billing are immutably logged and preserved for a minimum of 12 months.
              </span>
            </div>
            <span className="text-[11px] font-mono text-teal-600 dark:text-teal-400 shrink-0">
              {auditLogs.length} Records Loaded
            </span>
          </div>

          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 p-3 rounded-xl bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 shadow-card">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search audit records by actor email, organization, or action description..."
                value={auditSearchTerm}
                onChange={(e) => setAuditSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadAuditLogs()}
                className="w-full pl-9 pr-4 py-2 rounded-lg bg-[#F8FAFC] dark:bg-[#0C1017] border border-slate-200 dark:border-slate-800 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div className="w-full sm:w-64 shrink-0">
              <SimpleSelectDropdown
                options={auditActionOptions}
                value={auditActionFilter}
                onChange={setAuditActionFilter}
                placeholder="All Action Types"
              />
            </div>
          </div>

          {/* Audit Logs Table */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] overflow-hidden shadow-card">
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left text-xs table-fixed">
                <thead className="bg-[#F8FAFC] dark:bg-[#0C1017] border-b border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-semibold text-[10px] uppercase tracking-wider">
                  <tr>
                    <th className="w-[15%] px-3.5 py-2.5">Timestamp</th>
                    <th className="w-[20%] px-3.5 py-2.5">Actor / Admin</th>
                    <th className="w-[18%] px-3.5 py-2.5">Organization</th>
                    <th className="w-[16%] px-3.5 py-2.5">Action Type</th>
                    <th className="w-[24%] px-3.5 py-2.5">Description</th>
                    <th className="w-[7%] px-3.5 py-2.5 text-right">Diff</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
                  {auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-6 py-14 text-center text-slate-500">
                        <FileText className="w-8 h-8 mx-auto mb-2 text-slate-400 opacity-60" />
                        <p className="font-semibold text-sm">No audit records found</p>
                        <p className="text-xs text-slate-400 mt-1">
                          Privileged activities and configuration mutations will appear here.
                        </p>
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
                        {/* Timestamp */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap font-mono text-[11px] text-slate-500">
                          {new Date(log.created_at).toLocaleDateString()} {new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>

                        {/* Actor */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 min-w-0" title={`${log.actor_name || 'Super Admin'} • ${log.actor_email}`}>
                            <span className="font-semibold text-slate-900 dark:text-white truncate">
                              {log.actor_name || 'Super Admin'}
                            </span>
                            <span className="text-[11px] text-slate-400 font-normal truncate">
                              &bull; {log.actor_email}
                            </span>
                          </div>
                        </td>

                        {/* Organization */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 min-w-0" title={`${log.tenant_name || 'Platform Wide'}${log.tenant_id ? ` • ${log.tenant_id}` : ''}`}>
                            <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                              {log.tenant_name || 'Platform Wide'}
                            </span>
                            {log.tenant_id && (
                              <span className="text-[10px] font-mono text-slate-400 truncate">
                                &bull; {log.tenant_id.slice(0, 8)}...
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Action Type */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${getActionBadgeColor(log.action_type)}`}>
                            {formatActionLabel(log.action_type)}
                          </span>
                        </td>

                        {/* Description */}
                        <td className="px-3.5 py-2.5 whitespace-nowrap">
                          <div className="text-slate-700 dark:text-slate-300 text-[11px] truncate" title={log.description}>
                            {log.description}
                          </div>
                        </td>

                        {/* Diff Inspector */}
                        <td className="px-3.5 py-2.5 text-right whitespace-nowrap">
                          {(log.before_values || log.after_values) ? (
                            <button
                              type="button"
                              onClick={() => setSelectedAuditLogForDetail(log)}
                              className="p-1 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:text-teal-400 transition-colors border border-slate-200 dark:border-slate-700"
                              title="View Before & After State"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <span className="text-[11px] text-slate-400">&mdash;</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal for Dual-Auth Decision */}
      {actionConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-md rounded-2xl bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 text-xs">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
              <div className={`p-2 rounded-xl ${
                actionConfirmModal.type === 'approve'
                  ? 'bg-emerald-500/10 text-emerald-500'
                  : 'bg-rose-500/10 text-rose-500'
              }`}>
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  {actionConfirmModal.type === 'approve' ? 'Confirm Privileged Execution' : 'Reject Authorization Request'}
                </h3>
                <p className="text-[11px] text-slate-500">
                  Target: {actionConfirmModal.request.tenant_name}
                </p>
              </div>
            </div>

            <div className="p-5 space-y-3.5">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-[#0C1017] border border-slate-200 dark:border-slate-800 space-y-1">
                <div className="flex justify-between text-slate-600 dark:text-slate-400">
                  <span>Action:</span>
                  <span className="font-mono font-bold text-slate-900 dark:text-white">
                    {actionConfirmModal.request.action_type}
                  </span>
                </div>
                <div className="flex justify-between text-slate-600 dark:text-slate-400">
                  <span>Requester:</span>
                  <span className="text-slate-900 dark:text-white">{actionConfirmModal.request.requester_email}</span>
                </div>
              </div>

              {actionConfirmModal.type === 'approve' && (
                <p className="text-slate-600 dark:text-slate-300 leading-relaxed font-medium">
                  Signing off will immediately execute this high-impact action on the live environment and log your identity as the approving Super Administrator.
                </p>
              )}

              <div>
                <label className="block text-slate-600 dark:text-slate-400 font-medium mb-1">
                  {actionConfirmModal.type === 'approve' ? 'Optional Approval Note' : 'Rejection Reason *'}
                </label>
                <input
                  type="text"
                  required={actionConfirmModal.type === 'reject'}
                  placeholder={actionConfirmModal.type === 'approve' ? 'e.g. Verified with tenant director via phone' : 'e.g. Unauthorized request outside SLA'}
                  value={actionNotes}
                  onChange={(e) => setActionNotes(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#F8FAFC] dark:bg-[#0C1017] border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-white focus:outline-none focus:border-teal-500"
                />
              </div>

              <div className="pt-2 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setActionConfirmModal(null)}
                  className="px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] text-slate-700 dark:text-slate-300 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={actionConfirmModal.type === 'approve' ? handleExecuteApproval : handleExecuteRejection}
                  className={`px-4 py-2 rounded-lg text-white font-bold shadow-subtle ${
                    actionConfirmModal.type === 'approve'
                      ? 'bg-emerald-600 hover:bg-emerald-700'
                      : 'bg-rose-600 hover:bg-rose-700'
                  }`}
                >
                  {actionConfirmModal.type === 'approve' ? 'Sign & Execute' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Audit Detail & Diff Modal */}
      {selectedAuditLogForDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-xl rounded-2xl bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden animate-in zoom-in-95 duration-150 text-xs">
            <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Audit Snapshot Details
                </h3>
                <p className="text-[11px] text-slate-500">
                  {selectedAuditLogForDetail.action_type} &bull; {selectedAuditLogForDetail.tenant_name || 'Global'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setSelectedAuditLogForDetail(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold p-1"
              >
                &times;
              </button>
            </div>

            <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto font-mono text-[11px]">
              {selectedAuditLogForDetail.before_values && (
                <div>
                  <div className="text-rose-500 font-bold mb-1">&minus; Previous State (Before Mutation):</div>
                  <pre className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-700 dark:text-rose-300 overflow-x-auto">
                    {JSON.stringify(selectedAuditLogForDetail.before_values, null, 2)}
                  </pre>
                </div>
              )}

              {selectedAuditLogForDetail.after_values && (
                <div>
                  <div className="text-emerald-500 font-bold mb-1">&plus; Applied State (After Mutation):</div>
                  <pre className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300 overflow-x-auto">
                    {JSON.stringify(selectedAuditLogForDetail.after_values, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedAuditLogForDetail(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
