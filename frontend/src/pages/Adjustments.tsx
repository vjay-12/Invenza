import React, { useState } from 'react';
import {
  SlidersHorizontal,
  Plus,
  Search,
  AlertTriangle,
  FileSpreadsheet,
  ShieldAlert,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { AdjustmentReasonCode } from '../types/inventory';
import { ReasonBadge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';

export const Adjustments: React.FC = () => {
  const {
    adjustments,
    products,
    locations,
    createAdjustment,
  } = useInventory();

  const [searchQuery, setSearchQuery] = useState('');
  const [reasonFilter, setReasonFilter] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State
  const [locationId, setLocationId] = useState(locations[0]?.id || '');
  const [productId, setProductId] = useState(products[0]?.id || '');
  const [newCountedStock, setNewCountedStock] = useState<number>(10);
  const [reasonCode, setReasonCode] = useState<AdjustmentReasonCode>('audit');
  const [auditNotes, setAuditNotes] = useState('');

  const selectedProduct = products.find((p) => p.id === productId);
  const currentLocStock = selectedProduct?.locationStock[locationId] || 0;
  const calculatedDelta = newCountedStock - currentLocStock;

  const filteredAdjustments = adjustments.filter((adj) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      adj.adjustmentNumber.toLowerCase().includes(q) ||
      adj.productName.toLowerCase().includes(q) ||
      adj.sku.toLowerCase().includes(q) ||
      adj.locationName.toLowerCase().includes(q) ||
      adj.author.toLowerCase().includes(q);

    const matchesReason = reasonFilter === 'all' || adj.reasonCode === reasonFilter;

    return matchesSearch && matchesReason;
  });

  const handleSubmitAdjustment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!productId || !locationId || calculatedDelta === 0) return;

    createAdjustment(productId, locationId, newCountedStock, reasonCode, auditNotes);
    setIsModalOpen(false);
    setAuditNotes('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Manual Stock Adjustments & Reconciliation
            </h1>
            <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-bold text-amber-600 dark:text-amber-400 border border-amber-500/20">
              Mandatory Reason Codes
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Record physical inventory variances, scrap, damage, and cycle counts. Every adjustment is
            bound to an immutable audit record and justification note.
          </p>
        </div>

        <button
          onClick={() => {
            const cur = products[0]?.locationStock[locations[0]?.id || ''] || 0;
            setNewCountedStock(cur);
            setIsModalOpen(true);
          }}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-colors self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          Record Stock Adjustment
        </button>
      </div>

      {/* Filter toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-4 backdrop-blur-xl">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search adjustment #, SKU, reason, author..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        {/* Reason Code Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'damage', 'loss', 'miscount', 'return', 'audit'].map((r) => (
            <button
              key={r}
              onClick={() => setReasonFilter(r)}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold uppercase whitespace-nowrap transition-all ${
                reasonFilter === r
                  ? 'bg-indigo-600 text-white shadow-sm font-bold'
                  : 'border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              {r === 'all' ? 'All Reasons' : r}
            </button>
          ))}
        </div>
      </div>

      {/* Adjustments Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">Adjustment #</th>
                <th className="py-3 px-3">Date</th>
                <th className="py-3 px-3">Product / SKU</th>
                <th className="py-3 px-3">Warehouse</th>
                <th className="py-3 px-3 text-right">Previous</th>
                <th className="py-3 px-3 text-right">Counted</th>
                <th className="py-3 px-3 text-right">Variance (Delta)</th>
                <th className="py-3 px-3">Reason Code</th>
                <th className="py-3 px-3">Audit Notes</th>
                <th className="py-3 px-4">Author</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredAdjustments.map((adj) => (
                <tr
                  key={adj.id}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {adj.adjustmentNumber}
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                    {adj.date}
                  </td>
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      {adj.productName}
                    </div>
                    <div className="text-[10px] font-mono text-slate-400">{adj.sku}</div>
                  </td>
                  <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                    {adj.locationName}
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-slate-500">
                    {adj.previousStock}
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                    {adj.newStock}
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold">
                    <span
                      className={
                        adj.delta > 0
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-rose-600 dark:text-rose-400'
                      }
                    >
                      {adj.delta > 0 ? `+${adj.delta}` : adj.delta}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    <ReasonBadge reason={adj.reasonCode} />
                  </td>
                  <td className="py-3 px-3 text-slate-600 dark:text-slate-300 max-w-xs truncate">
                    {adj.notes}
                  </td>
                  <td className="py-3 px-4 text-slate-500 dark:text-slate-400 text-[11px]">
                    {adj.author}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Adjustment Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Record Stock Adjustment"
        subtitle="Mandatory reason codes and variance justification required for compliance"
        maxWidth="lg"
      >
        <form onSubmit={handleSubmitAdjustment} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Warehouse Location *
              </label>
              <select
                value={locationId}
                onChange={(e) => {
                  setLocationId(e.target.value);
                  const cur = selectedProduct?.locationStock[e.target.value] || 0;
                  setNewCountedStock(cur);
                }}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs"
              >
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.code} — {loc.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Product SKU *
              </label>
              <select
                value={productId}
                onChange={(e) => {
                  setProductId(e.target.value);
                  const p = products.find((item) => item.id === e.target.value);
                  const cur = p?.locationStock[locationId] || 0;
                  setNewCountedStock(cur);
                }}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-medium"
              >
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} — {p.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Variance Calculation Card */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 p-4">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Current Balance</div>
                <div className="text-base font-mono font-bold text-slate-700 dark:text-slate-300 mt-1">
                  {currentLocStock}
                </div>
              </div>

              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Actual Counted</div>
                <input
                  type="number"
                  required
                  value={newCountedStock}
                  onChange={(e) => setNewCountedStock(parseInt(e.target.value, 10) || 0)}
                  className="w-20 mx-auto text-center rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 py-1 text-base font-mono font-bold text-indigo-600 dark:text-indigo-400 focus:outline-none"
                />
              </div>

              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400">Net Variance</div>
                <div
                  className={`text-base font-mono font-bold mt-1 ${
                    calculatedDelta > 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : calculatedDelta < 0
                      ? 'text-rose-600 dark:text-rose-400'
                      : 'text-slate-400'
                  }`}
                >
                  {calculatedDelta > 0 ? `+${calculatedDelta}` : calculatedDelta}
                </div>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Mandatory Reason Code *
            </label>
            <select
              value={reasonCode}
              onChange={(e) => setReasonCode(e.target.value as AdjustmentReasonCode)}
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-semibold uppercase"
            >
              <option value="audit">AUDIT (Scheduled cycle count reconciliation)</option>
              <option value="damage">DAMAGE (Damaged in transit / dropped warehouse stock)</option>
              <option value="loss">LOSS (Unexplained inventory shrinkage)</option>
              <option value="miscount">MISCOUNT (Previous receiving / order packing error)</option>
              <option value="return">RETURN (Customer return restocking)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Detailed Audit Justification *
            </label>
            <textarea
              required
              rows={3}
              value={auditNotes}
              onChange={(e) => setAuditNotes(e.target.value)}
              placeholder="Describe why this adjustment occurred for permanent ledger audit records..."
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
            />
          </div>

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
              disabled={calculatedDelta === 0}
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Commit Adjustment to Ledger
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
