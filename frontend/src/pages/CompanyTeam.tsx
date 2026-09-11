import React, { useState, useEffect } from 'react';
import {
  IconUsers,
  IconUserPlus,
  IconShieldCheck,
  IconKey,
  IconCheck,
  IconCheckCircle2,
  IconAlertCircle,
  IconMail,
  IconLock,
  IconTrash2,
  IconEdit,
  IconRefreshCw,
  IconSend,
  IconSearch,
  IconX,
} from '../components/icons';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { PageMeta } from '../components/common/PageMeta';
import { Modal } from '../components/common/Modal';

const GRANULAR_PERMISSIONS = [
  { id: 'inventory:read', label: 'View Products & Inventory', desc: 'Can view inventory catalog, stock levels, and search items' },
  { id: 'inventory:write', label: 'Add & Edit Products', desc: 'Can create new SKUs, modify pricing, categories, and attributes' },
  { id: 'orders:manage', label: 'Manage Orders & GRN', desc: 'Can create POs/SOs, receive shipments, and fulfill orders' },
  { id: 'transfers:manage', label: 'Transfers & Adjustments', desc: 'Can initiate stock transfers between locations and manual counts' },
  { id: 'reports:view', label: 'View Financial Valuation', desc: 'Can view FIFO/weighted average valuation and ledger audit trails' },
];

export const CompanyTeam: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  const [users, setUsers] = useState<any[]>([]);
  const [pendingRequests, setPendingRequests] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Delete Member Confirmation Modal State
  const [userToDelete, setUserToDelete] = useState<any | null>(null);
  const [isDeletingUser, setIsDeletingUser] = useState(false);

  const filteredUsers = users.filter((u) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (u.full_name && u.full_name.toLowerCase().includes(q)) ||
      (u.email && u.email.toLowerCase().includes(q)) ||
      (u.role && u.role.toLowerCase().includes(q))
    );
  });

  // Add User Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('staff');
  const [permissions, setPermissions] = useState<string[]>(['inventory:read', 'inventory:write']);
  const [sendEmail, setSendEmail] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Edit User Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<any | null>(null);
  const [editFullName, setEditFullName] = useState('');
  const [editRole, setEditRole] = useState('staff');
  const [editPermissions, setEditPermissions] = useState<string[]>([]);
  const [editIsActive, setEditIsActive] = useState(true);
  const [isEditSubmitting, setIsEditSubmitting] = useState(false);

  // Review Email Change Request Modal State
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<any | null>(null);
  const [selectedRequestUser, setSelectedRequestUser] = useState<any | null>(null);
  const [isReviewSubmitting, setIsReviewSubmitting] = useState(false);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const [usersData, requestsData] = await Promise.all([
        api.getCompanyUsers(),
        isAdmin ? api.getEmailChangeRequests().catch(() => []) : Promise.resolve([]),
      ]);
      setUsers(usersData || []);
      setPendingRequests(Array.isArray(requestsData) ? requestsData : []);
    } catch (err: any) {
      showToast(err.message || 'Failed to fetch team members', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
    const handleRefresh = () => loadUsers();
    window.addEventListener('invenza_notifications_refresh', handleRefresh);
    return () => {
      window.removeEventListener('invenza_notifications_refresh', handleRefresh);
    };
  }, [isAdmin]);

  const requestsByUserId = React.useMemo(() => {
    const map: Record<string, any> = {};
    pendingRequests.forEach((req) => {
      if (req.user_id) map[req.user_id] = req;
      if (req.current_email) map[req.current_email.toLowerCase()] = req;
    });
    return map;
  }, [pendingRequests]);

  const openReviewModal = (req: any, u: any) => {
    setSelectedRequest(req);
    setSelectedRequestUser(u);
    setIsReviewModalOpen(true);
  };

  const handleApproveEmailChange = async () => {
    if (!selectedRequest) return;
    setIsReviewSubmitting(true);
    try {
      const res = await api.approveEmailChangeRequest(selectedRequest.id);
      showToast(res.message || `Email change approved! Updated to ${selectedRequest.requested_email}.`, 'success');
      window.dispatchEvent(new CustomEvent('invenza_notifications_refresh'));
      setIsReviewModalOpen(false);
      setSelectedRequest(null);
      setSelectedRequestUser(null);
      loadUsers();
    } catch (err: any) {
      showToast(err.message || 'Failed to approve email change', 'error');
    } finally {
      setIsReviewSubmitting(false);
    }
  };

  const handleRejectEmailChange = async () => {
    if (!selectedRequest) return;
    setIsReviewSubmitting(true);
    try {
      const res = await api.rejectEmailChangeRequest(selectedRequest.id);
      showToast(res.message || 'Email change request rejected.', 'success');
      window.dispatchEvent(new CustomEvent('invenza_notifications_refresh'));
      setIsReviewModalOpen(false);
      setSelectedRequest(null);
      setSelectedRequestUser(null);
      loadUsers();
    } catch (err: any) {
      showToast(err.message || 'Failed to reject email change', 'error');
    } finally {
      setIsReviewSubmitting(false);
    }
  };

  const generatePassword = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*';
    let res = '';
    for (let i = 0; i < 14; i++) {
      res += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setPassword(res);
  };

  const resetAddForm = () => {
    setFullName('');
    setEmail('');
    setPassword('');
    setRole('staff');
    setPermissions(['inventory:read', 'inventory:write']);
    setSendEmail(true);
  };

  const togglePermission = (permId: string) => {
    setPermissions((prev) =>
      prev.includes(permId) ? prev.filter((p) => p !== permId) : [...prev, permId]
    );
  };

  const toggleEditPermission = (permId: string) => {
    setEditPermissions((prev) =>
      prev.includes(permId) ? prev.filter((p) => p !== permId) : [...prev, permId]
    );
  };

  // Open Edit Modal
  const openEditModal = (u: any) => {
    setEditingUser(u);
    setEditFullName(u.full_name || '');
    setEditRole(u.role || 'staff');
    setEditPermissions(Array.isArray(u.permissions) ? [...u.permissions] : []);
    setEditIsActive(u.is_active ?? true);
    setIsEditModalOpen(true);
  };

  // Handle Create User
  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !password.trim()) {
      showToast('Please fill in all required fields', 'error');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.createCompanyUser({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password: password.trim(),
        role: role.toLowerCase(),
        permissions,
        send_email: sendEmail,
      });

      showToast(`User '${fullName}' enrolled successfully! Credentials dispatched to ${email}.`);
      setIsAddModalOpen(false);
      resetAddForm();
      loadUsers();
    } catch (err: any) {
      showToast(err.message || 'Failed to create user', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Update User
  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    const cleanName = editFullName.trim();
    if (!cleanName) {
      showToast('Full name cannot be left blank', 'error');
      return;
    }

    setIsEditSubmitting(true);
    try {
      await api.updateCompanyUser(editingUser.id, {
        full_name: cleanName,
        role: editRole.toLowerCase(),
        permissions: editPermissions,
        is_active: editIsActive,
      });

      showToast(`Team member '${cleanName}' updated successfully.`);
      setIsEditModalOpen(false);
      setEditingUser(null);
      loadUsers();
    } catch (err: any) {
      showToast(err.message || 'Failed to update team member', 'error');
    } finally {
      setIsEditSubmitting(false);
    }
  };

  const handleToggleActive = async (u: any) => {
    try {
      await api.updateCompanyUser(u.id, { is_active: !u.is_active });
      showToast(`User '${u.full_name}' status updated.`);
      loadUsers();
    } catch (err: any) {
      showToast('Failed to update status', 'error');
    }
  };

  const handleConfirmDeleteUser = async () => {
    if (!userToDelete) return;
    setIsDeletingUser(true);
    try {
      await api.deleteCompanyUser(userToDelete.id);
      showToast(`User '${userToDelete.full_name}' removed.`);
      setUserToDelete(null);
      loadUsers();
    } catch (err: any) {
      showToast(err.message || 'Failed to delete user', 'error');
    } finally {
      setIsDeletingUser(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <PageMeta
        title="Team & Granular Access Roles | Invenza Inventory"
        description="Role-based access control (RBAC), team member credential provisioning, and granular inventory permission matrices."
        canonicalPath="/team"
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className={`fixed top-5 right-5 z-50 px-4 py-3 rounded-lg shadow-modal flex items-center gap-3 border text-xs font-semibold ${
          toastMessage.type === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-950 dark:border-emerald-500/40 dark:text-emerald-300'
            : 'bg-rose-50 border-rose-200 text-rose-900 dark:bg-rose-950 dark:border-rose-500/40 dark:text-rose-300'
        }`}>
          {toastMessage.type === 'success' ? (
            <IconCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
          ) : (
            <IconAlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-xl bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 shadow-card">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded font-mono text-[10px] font-bold bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/20 mb-2">
            <IconShieldCheck className="w-3.5 h-3.5" />
            <span>Role-Based Access Control (RBAC)</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Company Team & Role Management
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
            Invite team members to <strong>{user?.companyName || 'your organization'}</strong>, assign granular operational permissions, and dispatch credentials.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            generatePassword();
            setIsAddModalOpen(true);
          }}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold shadow-subtle transition-colors shrink-0 self-start md:self-auto"
        >
          <IconUserPlus className="w-4 h-4" />
          <span>Add Team Member</span>
        </button>
      </div>

      {/* Users Table */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-card overflow-hidden">
        <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative w-full sm:w-72">
            <IconSearch className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search team by name, email, or role..."
              className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] pl-8 pr-3 py-1.5 text-xs text-slate-700 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-teal-500 transition-colors"
            />
          </div>

          <div className="flex items-center gap-3 self-end sm:self-auto">
            <span className="text-xs text-slate-400 font-mono">
              {filteredUsers.length} of {users.length} members
            </span>
            <button
              type="button"
              onClick={loadUsers}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] hover:bg-slate-200 dark:hover:bg-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-300 transition-colors"
            >
              <IconRefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-[#F6F8FA] dark:bg-[#0C1017] text-slate-600 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">Operator</th>
                <th className="py-3 px-3">Role Tier</th>
                <th className="py-3 px-3">Granted Permissions</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Enrolled</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400">
                    {searchQuery ? 'No team members matching search query.' : "No team members found. Click 'Add Team Member' to invite staff."}
                  </td>
                </tr>
              ) : (
              filteredUsers.map((u) => {
                const pendingReq = requestsByUserId[u.id] || requestsByUserId[u.email?.toLowerCase()];
                return (
                  <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-teal-500/10 text-teal-700 dark:text-teal-400 font-bold flex items-center justify-center text-xs shrink-0">
                          {u.full_name?.charAt(0) || 'U'}
                        </div>
                        <div className="min-w-0">
                          <div className="font-bold text-slate-800 dark:text-slate-200 truncate">
                            {u.full_name}
                          </div>
                          <div className="text-[11px] font-mono text-slate-400 truncate">
                            {u.email}
                          </div>
                          {pendingReq && (
                            <div className="text-[10px] font-mono text-amber-600 dark:text-amber-400 font-semibold flex items-center gap-1 mt-0.5 truncate">
                              <span>→ Requested: {pendingReq.requested_email}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-3">
                      <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                        {u.role}
                      </span>
                    </td>

                    <td className="py-3.5 px-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {(u.permissions || []).length === 0 ? (
                          <span className="text-slate-500 text-[11px]">Default read access</span>
                        ) : (
                          (u.permissions || []).map((p: string) => (
                            <span key={p} className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 text-[10px] font-mono border border-slate-200/60 dark:border-transparent">
                              {p}
                            </span>
                          ))
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-3">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleToggleActive(u)}
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                            u.is_active
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20'
                              : 'bg-rose-50 text-rose-800 border border-rose-200 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20'
                          }`}
                          title="Click to toggle user status"
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                          <span>{u.is_active ? 'Active' : 'Suspended'}</span>
                        </button>

                        {pendingReq && (
                          <button
                            type="button"
                            onClick={() => openReviewModal(pendingReq, u)}
                            className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[10px] font-bold bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 dark:bg-amber-500/15 dark:hover:bg-amber-500/25 dark:text-amber-300 dark:border-amber-500/30 transition-all shadow-sm group"
                            title="Email change requested. Click to review and approve or reject."
                          >
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping" />
                            <span>Request</span>
                            <span className="text-[9px] px-1 py-0.2 rounded bg-amber-200/70 text-amber-950 dark:bg-amber-500/20 dark:text-amber-200">Email</span>
                          </button>
                        )}
                      </div>
                    </td>

                    <td className="py-3.5 px-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <div className="inline-flex items-center justify-end gap-1.5">
                        {pendingReq && (
                          <button
                            type="button"
                            onClick={() => openReviewModal(pendingReq, u)}
                            className="p-1.5 rounded-md text-amber-600 dark:text-amber-400 hover:bg-amber-500/10 border border-amber-500/30 transition-colors"
                            title="Review Email Change Request"
                          >
                            <IconMail className="w-4 h-4" />
                          </button>
                        )}

                        <button
                          type="button"
                          onClick={() => openEditModal(u)}
                          className="p-1.5 rounded-md text-slate-400 hover:text-teal-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                          title="Edit team member"
                        >
                          <IconEdit className="w-4 h-4" />
                        </button>

                        {u.role !== 'admin' && (
                          <button
                            type="button"
                            onClick={() => setUserToDelete(u)}
                            className="p-1.5 rounded-md text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            title="Remove team member"
                          >
                            <IconTrash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Member Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 rounded-xl shadow-modal relative max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-6 py-4 shrink-0">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Add Team Member</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Assign role, access permissions, and dispatch credentials via email.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              >
                <IconX className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="p-6 overflow-y-auto flex-1 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Alex Rivera"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0C1017] text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-teal-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Work Email Address *
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="alex@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0C1017] text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-teal-500 transition-colors"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      Initial Password *
                    </label>
                    <button
                      type="button"
                      onClick={generatePassword}
                      className="text-[11px] text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1 font-semibold"
                    >
                      <IconKey className="w-3 h-3" />
                      <span>Regenerate</span>
                    </button>
                  </div>
                  <input
                    type="text"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0C1017] text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-teal-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Role Tier
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0C1017] text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-teal-500 transition-colors"
                  >
                    <option value="staff">Staff (Operational Operator)</option>
                    <option value="manager">Manager (Warehouse Oversight)</option>
                    <option value="admin">Company Administrator (Full Access)</option>
                    <option value="viewer">Viewer (Read-Only Access)</option>
                  </select>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Granular Operational Privileges
                  </label>
                  <div className="space-y-2">
                    {GRANULAR_PERMISSIONS.map((p) => (
                      <label key={p.id} className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition-colors">
                        <input
                          type="checkbox"
                          checked={permissions.includes(p.id)}
                          onChange={() => togglePermission(p.id)}
                          className="mt-0.5 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                        />
                        <div className="text-xs">
                          <div className="font-semibold text-slate-800 dark:text-slate-200">{p.label}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5">{p.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-300 pt-2">
                  <input
                    type="checkbox"
                    checked={sendEmail}
                    onChange={(e) => setSendEmail(e.target.checked)}
                    className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                  />
                  <span>Dispatch invitation email with login credentials</span>
                </label>
              </div>

              <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold shadow-subtle transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  <IconSend className="w-3.5 h-3.5" />
                  <span>{isSubmitting ? 'Enrolling...' : 'Enroll Operator'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Member Modal */}
      {isEditModalOpen && editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 rounded-xl shadow-modal relative max-h-[90vh] flex flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-6 py-4 shrink-0">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">Edit Team Member</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Update operator identity, role tier, and operational privileges.
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsEditModalOpen(false);
                  setEditingUser(null);
                }}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              >
                <IconX className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleUpdateUser} className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="p-6 overflow-y-auto flex-1 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Full Name *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Alex Rivera"
                    value={editFullName}
                    onChange={(e) => setEditFullName(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0C1017] text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-teal-500 transition-colors"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Registered Email Address
                  </label>
                  <input
                    type="email"
                    readOnly
                    disabled
                    value={editingUser.email}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 text-xs font-mono text-slate-500 dark:text-slate-400 cursor-not-allowed"
                  />
                  <span className="text-[11px] text-slate-400 mt-1 block">
                    Registered email addresses follow organizational change request approvals.
                  </span>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Role Tier
                  </label>
                  <select
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0C1017] text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-teal-500 transition-colors"
                  >
                    <option value="staff">Staff (Operational Operator)</option>
                    <option value="manager">Manager (Warehouse Oversight)</option>
                    <option value="admin">Company Administrator (Full Access)</option>
                    <option value="viewer">Viewer (Read-Only Access)</option>
                  </select>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Granular Operational Privileges
                  </label>
                  <div className="space-y-2">
                    {GRANULAR_PERMISSIONS.map((p) => (
                      <label key={p.id} className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40 cursor-pointer transition-colors">
                        <input
                          type="checkbox"
                          checked={editPermissions.includes(p.id)}
                          onChange={() => toggleEditPermission(p.id)}
                          className="mt-0.5 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                        />
                        <div className="text-xs">
                          <div className="font-semibold text-slate-800 dark:text-slate-200">{p.label}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5">{p.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                  <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                    Account Status
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-300">
                    <input
                      type="checkbox"
                      checked={editIsActive}
                      onChange={(e) => setEditIsActive(e.target.checked)}
                      className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                    />
                    <span>Account is Active and authorized to access the system</span>
                  </label>
                </div>
              </div>

              <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-3 shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    setIsEditModalOpen(false);
                    setEditingUser(null);
                  }}
                  className="px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isEditSubmitting}
                  className="px-5 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold shadow-subtle transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  <IconCheck className="w-3.5 h-3.5" />
                  <span>{isEditSubmitting ? 'Saving Changes...' : 'Save Changes'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Review Email Change Request Modal */}
      {isReviewModalOpen && selectedRequest && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-modal overflow-hidden animate-in zoom-in-95 duration-150 flex flex-col">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <IconMail className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Review Email Change Request
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Pending administrative approval
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsReviewModalOpen(false);
                  setSelectedRequest(null);
                  setSelectedRequestUser(null);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              >
                <IconX className="w-4 h-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4 text-xs">
              {/* Operator Info */}
              <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 dark:bg-[#0C1017] border border-slate-200 dark:border-slate-800">
                <div className="w-9 h-9 rounded-lg bg-teal-500/10 text-teal-700 dark:text-teal-400 font-bold flex items-center justify-center text-sm shrink-0">
                  {selectedRequestUser?.full_name?.charAt(0) || selectedRequest.user_name?.charAt(0) || 'U'}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold text-slate-800 dark:text-slate-200 truncate">
                    {selectedRequestUser?.full_name || selectedRequest.user_name || 'Team Member'}
                  </div>
                  <div className="text-[11px] text-slate-400 flex items-center gap-2">
                    <span className="uppercase font-mono font-bold text-[9px] px-1.5 py-0.2 rounded bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {selectedRequestUser?.role || 'Staff'}
                    </span>
                    <span>• Submitted {new Date(selectedRequest.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              {/* Email Change Comparison */}
              <div className="space-y-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                    Current Registered Email
                  </label>
                  <div className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-[#0C1017] font-mono text-slate-600 dark:text-slate-400">
                    {selectedRequest.current_email}
                  </div>
                </div>

                <div className="flex justify-center text-slate-400">
                  <span className="text-xs font-bold uppercase tracking-widest font-mono text-amber-600 dark:text-amber-400">
                    ↓ Requested New Email ↓
                  </span>
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-teal-700 dark:text-teal-400 uppercase tracking-wider mb-1">
                    Requested New Email
                  </label>
                  <div className="px-3 py-2 rounded-lg border border-teal-500/30 bg-teal-500/10 font-mono font-bold text-teal-800 dark:text-teal-300">
                    {selectedRequest.requested_email}
                  </div>
                </div>
              </div>

              {/* Reason note if provided */}
              {selectedRequest.reason && (
                <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 text-slate-700 dark:text-slate-300">
                  <span className="font-bold text-amber-700 dark:text-amber-400 block text-[11px] mb-0.5">
                    User Stated Reason:
                  </span>
                  <p className="italic text-xs">"{selectedRequest.reason}"</p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-4 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-3 bg-slate-50/50 dark:bg-[#0C1017]/50">
              <button
                type="button"
                disabled={isReviewSubmitting}
                onClick={handleRejectEmailChange}
                className="px-4 py-2 rounded-lg border border-rose-300 dark:border-rose-800/80 bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/40 text-xs font-semibold transition-colors disabled:opacity-50"
              >
                {isReviewSubmitting ? 'Processing...' : 'Reject Request'}
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={isReviewSubmitting}
                  onClick={() => {
                    setIsReviewModalOpen(false);
                    setSelectedRequest(null);
                    setSelectedRequestUser(null);
                  }}
                  className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isReviewSubmitting}
                  onClick={handleApproveEmailChange}
                  className="px-4 py-2 rounded-lg bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold shadow-subtle transition-colors flex items-center gap-1.5 disabled:opacity-50"
                >
                  <IconCheck className="w-3.5 h-3.5" />
                  <span>{isReviewSubmitting ? 'Approving...' : 'Approve & Update Email'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Remove Member Confirmation Modal */}
      {userToDelete && (
        <Modal
          isOpen={!!userToDelete}
          onClose={() => {
            if (!isDeletingUser) setUserToDelete(null);
          }}
          title="Remove Team Member"
          subtitle="Confirm operator removal & platform credential revocation"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs text-slate-600 dark:text-slate-300">
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-3.5 text-rose-800 dark:text-rose-200">
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-rose-500/20 text-rose-600 dark:text-rose-400 shrink-0">
                  <IconTrash2 className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-bold text-sm text-slate-900 dark:text-white">
                    Are you sure you want to remove <span className="text-rose-600 dark:text-rose-400">{userToDelete.full_name}</span>?
                  </p>
                  <p className="mt-1 font-mono text-[11px] text-slate-500 dark:text-slate-400">
                    {userToDelete.email} &bull; Role: {userToDelete.role}
                  </p>
                </div>
              </div>
            </div>

            <p className="text-slate-500 dark:text-slate-400 leading-relaxed text-[11px]">
              This member will be permanently removed from your organization and their login credentials will be revoked immediately. Any past audit logs or movements logged by this operator will remain preserved.
            </p>

            <div className="flex items-center justify-end gap-2.5 border-t border-slate-200 dark:border-slate-800 pt-3">
              <button
                type="button"
                disabled={isDeletingUser}
                onClick={() => setUserToDelete(null)}
                className="rounded-lg border border-slate-200 dark:border-slate-800 px-3.5 py-2 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeletingUser}
                onClick={handleConfirmDeleteUser}
                className="rounded-lg bg-rose-600 hover:bg-rose-700 px-4 py-2 text-xs font-bold text-white shadow-subtle flex items-center gap-1.5 transition-all shadow-rose-500/20"
              >
                {isDeletingUser ? <IconRefreshCw className="w-3.5 h-3.5 animate-spin" /> : null}
                <span>{isDeletingUser ? 'Removing...' : 'Remove Member'}</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
