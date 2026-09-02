import React, { useState } from 'react';
import {
  Settings as SettingsIcon,
  Sliders,
  Shield,
  Webhook,
  DollarSign,
  Plus,
  Trash2,
  Check,
  Globe,
  Radio,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { CustomFieldDefinition, CurrencyCode } from '../types/inventory';
import { Modal } from '../components/common/Modal';

export const Settings: React.FC = () => {
  const { customFields, addCustomField, currency, setCurrency } = useInventory();

  // Custom Field Form
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fieldName, setFieldName] = useState('');
  const [fieldKey, setFieldKey] = useState('');
  const [fieldType, setFieldType] = useState<'text' | 'number' | 'date' | 'select'>('text');
  const [optionsStr, setOptionsStr] = useState('');

  // Outbound webhooks state
  const [webhooks, setWebhooks] = useState([
    {
      id: 'wh-1',
      url: 'https://api.company-erp.internal/webhooks/invenza',
      events: ['stock.movement', 'stock.low'],
      isActive: true,
    },
    {
      id: 'wh-2',
      url: 'https://hooks.slack.com/services/T00/B00/XXXX',
      events: ['stock.low'],
      isActive: true,
    },
  ]);

  const [newWebhookUrl, setNewWebhookUrl] = useState('');

  const handleCreateCustomField = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fieldName || !fieldKey) return;

    const options =
      fieldType === 'select'
        ? optionsStr.split(',').map((s) => s.trim()).filter(Boolean)
        : undefined;

    addCustomField({
      name: fieldName,
      key: fieldKey.trim(),
      type: fieldType,
      options,
      required: false,
    });

    setIsModalOpen(false);
    setFieldName('');
    setFieldKey('');
    setOptionsStr('');
  };

  const handleAddWebhook = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWebhookUrl) return;

    setWebhooks((prev) => [
      ...prev,
      {
        id: `wh-${Date.now()}`,
        url: newWebhookUrl,
        events: ['stock.low', 'stock.movement'],
        isActive: true,
      },
    ]);
    setNewWebhookUrl('');
  };

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
          System Settings & Customization Engine
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Configure JSONB dynamic product schemas, user roles, outbound event webhooks, and
          formatting.
        </p>
      </div>

      {/* 1. Dynamic Custom Fields Engine */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
              <Sliders className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Dynamic Product Custom Fields (JSONB)
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Addresses "Limited Customization". Define bespoke fields for any industry (lot
                tracking, expiry, warehouse zone).
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-3.5 py-2 text-xs font-semibold text-white transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Custom Field
          </button>
        </div>

        {/* Existing Custom Fields */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          {customFields.map((cf) => (
            <div
              key={cf.id}
              className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 p-4"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-800 dark:text-slate-200">
                  {cf.name}
                </span>
                <span className="rounded bg-indigo-500/10 px-2 py-0.5 text-[10px] font-mono font-bold uppercase text-indigo-600 dark:text-indigo-400">
                  {cf.type}
                </span>
              </div>
              <div className="mt-1 font-mono text-[11px] text-slate-400">key: {cf.key}</div>
              {cf.options && (
                <div className="mt-2 text-[10px] text-slate-500">
                  Options: {cf.options.join(', ')}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 2. User Roles & Permission Matrix */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
        <div className="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400">
            <Shield className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Role-Based Access Control (RBAC)
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Tenant-scoped security roles and module permissions.
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 uppercase font-semibold text-[10px]">
                <th className="pb-3">Role Tier</th>
                <th className="pb-3 text-center">View Reports</th>
                <th className="pb-3 text-center">Create PO / SO</th>
                <th className="pb-3 text-center">Execute Transfers</th>
                <th className="pb-3 text-center">Manual Adjustments</th>
                <th className="pb-3 text-center">Manage Schema</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              <tr>
                <td className="py-3 font-bold text-slate-900 dark:text-white">
                  Admin (Superuser)
                </td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-emerald-500">✓</td>
              </tr>
              <tr>
                <td className="py-3 font-bold text-slate-900 dark:text-white">
                  Warehouse Staff
                </td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-amber-500 font-medium">Approval req.</td>
                <td className="py-3 text-center text-slate-400">—</td>
              </tr>
              <tr>
                <td className="py-3 font-bold text-slate-900 dark:text-white">
                  Viewer (Auditor)
                </td>
                <td className="py-3 text-center text-emerald-500">✓</td>
                <td className="py-3 text-center text-slate-400">—</td>
                <td className="py-3 text-center text-slate-400">—</td>
                <td className="py-3 text-center text-slate-400">—</td>
                <td className="py-3 text-center text-slate-400">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* 3. Outbound Webhooks Config */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
        <div className="flex items-center gap-3 border-b border-slate-100 dark:border-slate-800 pb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400">
            <Webhook className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white">
              Outbound Event Webhooks
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Fire HTTP POST payloads whenever stock events occur to self-integrate with external
              tools.
            </p>
          </div>
        </div>

        <form onSubmit={handleAddWebhook} className="mt-4 flex gap-3">
          <input
            type="url"
            required
            value={newWebhookUrl}
            onChange={(e) => setNewWebhookUrl(e.target.value)}
            placeholder="https://your-service.com/api/invenza-listener"
            className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-sm"
          >
            Register Webhook
          </button>
        </form>

        <div className="mt-4 space-y-2">
          {webhooks.map((wh) => (
            <div
              key={wh.id}
              className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 p-3 text-xs bg-slate-50/50 dark:bg-slate-800/30"
            >
              <div className="font-mono text-slate-700 dark:text-slate-300 truncate max-w-md">
                {wh.url}
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                  Active
                </span>
                <button
                  onClick={() => setWebhooks((prev) => prev.filter((w) => w.id !== wh.id))}
                  className="text-slate-400 hover:text-rose-500"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Add Custom Field Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Add Dynamic JSONB Custom Field"
        subtitle="This attribute will immediately be available across all product SKUs"
        maxWidth="md"
      >
        <form onSubmit={handleCreateCustomField} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Field Display Name *
            </label>
            <input
              type="text"
              required
              value={fieldName}
              onChange={(e) => {
                setFieldName(e.target.value);
                if (!fieldKey) {
                  setFieldKey(
                    e.target.value
                      .toLowerCase()
                      .replace(/[^a-zA-Z0-9]/g, '')
                  );
                }
              }}
              placeholder="e.g. Storage Zone"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              JSONB Key Identifier *
            </label>
            <input
              type="text"
              required
              value={fieldKey}
              onChange={(e) => setFieldKey(e.target.value)}
              placeholder="e.g. storageZone"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Data Type
            </label>
            <select
              value={fieldType}
              onChange={(e) => setFieldType(e.target.value as any)}
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
            >
              <option value="text">Text (String)</option>
              <option value="number">Numeric (Float / Int)</option>
              <option value="date">Date Picker</option>
              <option value="select">Dropdown Select List</option>
            </select>
          </div>

          {fieldType === 'select' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Dropdown Options (comma separated)
              </label>
              <input
                type="text"
                value={optionsStr}
                onChange={(e) => setOptionsStr(e.target.value)}
                placeholder="Zone A, Zone B, Cold Storage"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
              />
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Create Field
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
