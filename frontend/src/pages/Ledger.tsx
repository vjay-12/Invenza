import React, { useState } from 'react';
import {
  Layers,
  Search,
  Filter,
  Download,
  ShieldCheck,
  ArrowDownRight,
  ArrowUpRight,
  SlidersHorizontal,
  ArrowLeftRight,
  Calendar,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { MovementBadge, ReasonBadge } from '../components/common/Badge';
import { MovementType } from '../types/inventory';

export const Ledger: React.FC = () => {
  const { ledger, locations, formatCurrency, selectedLocationId } = useInventory();

  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Filter movements
  const filteredMovements = ledger.filter((m) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesSearch =
      !q ||
      m.productName.toLowerCase().includes(q) ||
      m.sku.toLowerCase().includes(q) ||
      m.referenceId.toLowerCase().includes(q) ||
      m.performedBy.toLowerCase().includes(q);

    const matchesType = typeFilter === 'all' || m.movementType === typeFilter;

    const matchesLocation =
      selectedLocationId === 'all' ||
      m.locationId === selectedLocationId ||
      m.targetLocationId === selectedLocationId;

    return matchesSearch && matchesType && matchesLocation;
  });

  const exportLedgerCSV = () => {
    const headers = [
      'Timestamp',
      'MovementType',
      'SKU',
      'ProductName',
      'Quantity',
      'Location',
      'TargetLocation',
      'ReferenceType',
      'ReferenceID',
      'ReasonCode',
      'PerformedBy',
      'UnitCost',
    ];
    const rows = filteredMovements.map((m) => [
      m.timestamp,
      m.movementType,
      m.sku,
      `"${m.productName.replace(/"/g, '""')}"`,
      m.quantity,
      `"${m.locationName}"`,
      `"${m.targetLocationName || ''}"`,
      m.referenceType,
      m.referenceId,
      m.reasonCode || '',
      `"${m.performedBy}"`,
      m.unitCost,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `invenza_ledger_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Stock Movement Ledger
            </h1>
            <span className="flex items-center gap-1 rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 px-2.5 py-0.5 text-xs font-bold text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
              <ShieldCheck className="h-3.5 w-3.5" /> Immutable Audit Stream
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Every inventory increase, depletion, adjustment, and transfer is permanently recorded.
            Current balances are calculated by aggregating these transactions.
          </p>
        </div>

        <button
          onClick={exportLedgerCSV}
          className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors shadow-sm self-start sm:self-auto"
        >
          <Download className="h-4 w-4 text-slate-400" />
          Export Ledger Audit (CSV)
        </button>
      </div>

      {/* Trust & Architecture Explainer Banner */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 p-4 backdrop-blur-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <Layers className="h-5 w-5" />
          </div>
          <div className="text-xs">
            <div className="font-bold text-slate-800 dark:text-slate-200">
              Zero Mutable Stock Counts: Verified Ledger Math
            </div>
            <div className="text-slate-500 dark:text-slate-400 mt-0.5">
              Traditional inventory tools allow direct overwrites of stock numbers, causing untraceable
              variance. Invenza prevents stock tampering by strictly inserting signed deltas.
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-xs font-semibold shrink-0">
          <div className="rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-3 py-1.5 border border-emerald-500/20">
            Receipts: {ledger.filter((m) => m.movementType === 'IN').length}
          </div>
          <div className="rounded-xl bg-rose-500/10 text-rose-600 dark:text-rose-400 px-3 py-1.5 border border-rose-500/20">
            Dispatches: {ledger.filter((m) => m.movementType === 'OUT').length}
          </div>
          <div className="rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 px-3 py-1.5 border border-amber-500/20">
            Adjustments: {ledger.filter((m) => m.movementType === 'ADJUST').length}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-4 backdrop-blur-xl">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by SKU, product, PO/SO #, author..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        {/* Movement Type Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {[
            { id: 'all', label: 'All Movements' },
            { id: 'IN', label: '↓ IN (PO)', color: 'emerald' },
            { id: 'OUT', label: '↑ OUT (SO)', color: 'rose' },
            { id: 'TRANSFER', label: '⇆ Transfer', color: 'sky' },
            { id: 'ADJUST', label: '⟲ Adjust', color: 'amber' },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTypeFilter(t.id)}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold whitespace-nowrap transition-all ${
                typeFilter === t.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ledger Stream Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-3">Movement Type</th>
                <th className="py-3 px-3">Product / SKU</th>
                <th className="py-3 px-3">Location / Warehouse</th>
                <th className="py-3 px-3 text-right">Delta Quantity</th>
                <th className="py-3 px-3 text-right">Running Balance</th>
                <th className="py-3 px-3">Reference / Order #</th>
                <th className="py-3 px-3">Reason / Details</th>
                <th className="py-3 px-4">Operator</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredMovements.map((m) => (
                <tr
                  key={m.id}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                    <div>{new Date(m.timestamp).toLocaleDateString()}</div>
                    <div className="text-[10px] text-slate-400">
                      {new Date(m.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </div>
                  </td>
                  <td className="py-3 px-3">
                    <MovementBadge type={m.movementType} />
                  </td>
                  <td className="py-3 px-3">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      {m.productName}
                    </div>
                    <div className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 font-bold">
                      {m.sku}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-slate-700 dark:text-slate-300">
                    <div className="font-medium">{m.locationName}</div>
                    {m.targetLocationName && (
                      <div className="text-[10px] text-sky-500 font-medium">
                        → Dest: {m.targetLocationName}
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold text-sm">
                    <span
                      className={
                        m.movementType === 'IN'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : m.movementType === 'OUT'
                          ? 'text-rose-600 dark:text-rose-400'
                          : 'text-amber-600 dark:text-amber-400'
                      }
                    >
                      {m.movementType === 'IN'
                        ? `+${m.quantity}`
                        : m.movementType === 'OUT'
                        ? `-${m.quantity}`
                        : m.quantity > 0
                        ? `+${m.quantity}`
                        : `${m.quantity}`}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-semibold text-slate-700 dark:text-slate-300">
                    {m.runningBalance} pcs
                  </td>
                  <td className="py-3 px-3">
                    <span className="rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-mono font-bold text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
                      {m.referenceId}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    {m.reasonCode ? (
                      <ReasonBadge reason={m.reasonCode} />
                    ) : (
                      <span className="text-[11px] text-slate-400">
                        {m.referenceType === 'PO' ? 'Goods Received' : m.referenceType === 'SO' ? 'Customer Order' : 'Standard'}
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-600 dark:text-slate-300 text-[11px] whitespace-nowrap">
                    {m.performedBy}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
