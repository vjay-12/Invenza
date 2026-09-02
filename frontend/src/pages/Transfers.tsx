import React, { useState } from 'react';
import {
  ArrowLeftRight,
  Plus,
  Search,
  Warehouse,
  CheckCircle2,
  Calendar,
  AlertCircle,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { Modal } from '../components/common/Modal';

export const Transfers: React.FC = () => {
  const {
    transfers,
    locations,
    products,
    createTransfer,
  } = useInventory();

  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Transfer Form State
  const [sourceId, setSourceId] = useState(locations[0]?.id || '');
  const [targetId, setTargetId] = useState(locations[1]?.id || '');
  const [selectedProductId, setSelectedProductId] = useState(products[0]?.id || '');
  const [transferQty, setTransferQty] = useState(5);
  const [transferNotes, setTransferNotes] = useState('');

  const filteredTransfers = transfers.filter((t) => {
    const q = searchQuery.toLowerCase();
    return (
      t.transferNumber.toLowerCase().includes(q) ||
      t.sourceLocationName.toLowerCase().includes(q) ||
      t.targetLocationName.toLowerCase().includes(q)
    );
  });

  const handleSubmitTransfer = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (sourceId === targetId) {
      setErrorMsg('Source warehouse and destination warehouse must be different.');
      return;
    }

    const prod = products.find((p) => p.id === selectedProductId);
    const available = prod?.locationStock[sourceId] || 0;
    if (available < transferQty) {
      setErrorMsg(
        `Insufficient quantity in source warehouse. Available: ${available}, Requested: ${transferQty}`
      );
      return;
    }

    createTransfer(
      sourceId,
      targetId,
      [{ productId: selectedProductId, quantity: transferQty }],
      transferNotes
    );

    setIsModalOpen(false);
    setTransferNotes('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Inter-Warehouse Stock Transfers
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Relocate inventory between hubs. Creates paired cryptographic ledger entries for source
            and destination locations.
          </p>
        </div>

        <button
          onClick={() => {
            setErrorMsg(null);
            setIsModalOpen(true);
          }}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-colors self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          Initiate Stock Transfer
        </button>
      </div>

      {/* Filter toolbar */}
      <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-4 backdrop-blur-xl">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search transfer #, source, or target..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400">
          Total Transfers: <span className="font-bold text-slate-800 dark:text-slate-200">{transfers.length}</span>
        </div>
      </div>

      {/* Transfers List */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">Transfer #</th>
                <th className="py-3 px-3">Date</th>
                <th className="py-3 px-3">Source Warehouse</th>
                <th className="py-3 px-3">Destination Warehouse</th>
                <th className="py-3 px-3">Items Transferred</th>
                <th className="py-3 px-3">Notes</th>
                <th className="py-3 px-4 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredTransfers.map((tr) => (
                <tr
                  key={tr.id}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {tr.transferNumber}
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                    {tr.date}
                  </td>
                  <td className="py-3 px-3 font-semibold text-slate-800 dark:text-slate-200">
                    {tr.sourceLocationName}
                  </td>
                  <td className="py-3 px-3 font-semibold text-slate-800 dark:text-slate-200">
                    {tr.targetLocationName}
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-col gap-0.5">
                      {tr.items.map((it, idx) => (
                        <span key={idx} className="text-[11px] text-slate-700 dark:text-slate-300">
                          <span className="font-bold text-indigo-600 dark:text-indigo-400 font-mono">
                            {it.quantity}×
                          </span>{' '}
                          {it.name}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400 max-w-xs truncate">
                    {tr.notes || 'Regional inventory balance'}
                  </td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      <CheckCircle2 className="h-3 w-3" /> Completed
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transfer Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Initiate Inter-Warehouse Transfer"
        subtitle="Creates synchronized paired movements across locations"
        maxWidth="lg"
      >
        <form onSubmit={handleSubmitTransfer} className="space-y-4">
          {errorMsg && (
            <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Source Warehouse *
              </label>
              <select
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
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
                Destination Warehouse *
              </label>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs"
              >
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.code} — {loc.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t border-slate-100 dark:border-slate-800 pt-3">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Select Product SKU *
              </label>
              <select
                value={selectedProductId}
                onChange={(e) => setSelectedProductId(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-medium"
              >
                {products.map((p) => {
                  const available = p.locationStock[sourceId] || 0;
                  return (
                    <option key={p.id} value={p.id}>
                      {p.sku} — {p.name} (Avail: {available} {p.unitOfMeasure})
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Transfer Quantity *
              </label>
              <input
                type="number"
                min="1"
                required
                value={transferQty}
                onChange={(e) => setTransferQty(parseInt(e.target.value, 10) || 1)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono font-bold"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Transfer Purpose / Notes
            </label>
            <input
              type="text"
              value={transferNotes}
              onChange={(e) => setTransferNotes(e.target.value)}
              placeholder="e.g. Fulfill West Coast shortage"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs"
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
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Execute Stock Transfer
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
