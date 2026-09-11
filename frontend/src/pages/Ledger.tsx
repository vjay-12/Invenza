import React, { useState } from 'react';
import {
  IconLayers,
  IconSearch,
  IconDownload,
  IconShieldCheck,
} from '../components/icons';
import { useInventory } from '../context/InventoryContext';
import { MovementBadge, ReasonBadge } from '../components/common/Badge';
import { PageMeta } from '../components/common/PageMeta';

export const Ledger: React.FC = () => {
  const { ledger, products, locations, selectedLocationId } = useInventory();

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
      'Location',
      'TargetLocation',
      'Quantity',
      'RunningBalance',
      'ReferenceId',
      'ReasonCode',
      'PerformedBy',
      'UnitCost',
    ];

    const rows = filteredMovements.map((m) => [
      `"${m.timestamp}"`,
      `"${m.movementType}"`,
      `"${m.sku}"`,
      `"${m.productName.replace(/"/g, '""')}"`,
      `"${m.locationName || ''}"`,
      `"${m.targetLocationName || ''}"`,
      m.quantity,
      m.runningBalance,
      `"${m.referenceId}"`,
      `"${m.reasonCode || ''}"`,
      `"${m.performedBy}"`,
      m.unitCost || 0,
    ]);

    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `invenza-ledger-audit-${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      <PageMeta
        title="Stock Movement Ledger | Invenza Immutable Audit"
        description="Complete cryptographic double-entry movement ledger stream tracking every receipt, dispatch, transfer, and physical reconciliation."
        canonicalPath="/ledger"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
              Stock Movement Ledger
            </h1>
            <span className="flex items-center gap-1 rounded font-mono text-[10px] font-bold bg-teal-500/10 px-2 py-0.5 text-teal-700 dark:text-teal-400 border border-teal-500/20">
              <IconShieldCheck className="h-3.5 w-3.5" /> Immutable Audit Stream
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Every inventory increase, depletion, adjustment, and transfer is permanently recorded.
            Current balances are calculated by aggregating these transactions.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            type="button"
            onClick={exportLedgerCSV}
            className="flex items-center gap-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] hover:bg-slate-50 dark:hover:bg-slate-800 px-3.5 py-2 text-xs font-bold text-slate-700 dark:text-slate-200 transition-colors shadow-subtle"
          >
            <IconDownload className="h-4 w-4 text-slate-400" />
            Export Ledger Audit (CSV)
          </button>
        </div>
      </div>

      {/* Architecture Explainer Banner */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] p-4 shadow-card flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-500/10 text-teal-700 dark:text-teal-400 border border-teal-500/20">
            <IconLayers className="h-5 w-5" />
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

        <div className="flex items-center gap-2 text-xs font-mono font-semibold shrink-0">
          <div className="rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 px-2.5 py-1 border border-emerald-500/20">
            Receipts: {ledger.filter((m) => m.movementType === 'IN').length}
          </div>
          <div className="rounded bg-rose-500/10 text-rose-700 dark:text-rose-400 px-2.5 py-1 border border-rose-500/20">
            Dispatches: {ledger.filter((m) => m.movementType === 'OUT').length}
          </div>
          <div className="rounded bg-amber-500/10 text-amber-700 dark:text-amber-400 px-2.5 py-1 border border-amber-500/20">
            Adjustments: {ledger.filter((m) => m.movementType === 'ADJUST').length}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] p-3 shadow-card">
        <div className="relative w-full sm:w-80">
          <IconSearch className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by SKU, product, PO/SO #, author..."
            className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] pl-8 pr-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-600"
          />
        </div>

        {/* Movement Type Buttons */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {[
            { id: 'all', label: 'All Movements' },
            { id: 'IN', label: 'IN (PO)' },
            { id: 'OUT', label: 'OUT (SO)' },
            { id: 'TRANSFER', label: 'Transfer' },
            { id: 'ADJUST', label: 'Adjust' },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTypeFilter(t.id)}
              className={`rounded-md px-3 py-1 text-xs font-mono font-semibold whitespace-nowrap transition-colors ${
                typeFilter === t.id
                  ? 'bg-teal-700 text-white shadow-subtle'
                  : 'border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ledger Stream Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-card">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-[#F6F8FA] dark:bg-[#0C1017] text-slate-600 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-2.5 px-4">Timestamp</th>
                <th className="py-2.5 px-3">Movement Type</th>
                <th className="py-2.5 px-3">Product / SKU</th>
                <th className="py-2.5 px-3">Location / Warehouse</th>
                <th className="py-2.5 px-3 text-right">Delta Quantity</th>
                <th className="py-2.5 px-3 text-right">Running Balance</th>
                <th className="py-2.5 px-3">Reference / Order #</th>
                <th className="py-2.5 px-3">Reason / Details</th>
                <th className="py-2.5 px-4">Operator</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredMovements.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <IconLayers className="h-8 w-8 text-slate-300 dark:text-slate-600" />
                      <span className="text-sm font-medium text-slate-500 dark:text-slate-400">
                        {searchQuery || typeFilter !== 'ALL'
                          ? 'No movement ledger entries match your filter criteria.'
                          : 'No movement ledger entries found.'}
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredMovements.map((m) => {
                  const prod = products.find((p) => p.id === m.productId || p.sku === m.sku);
                  const loc = locations.find((l) => l.id === m.locationId);
                  const rawTimestamp = m.timestamp || (m as any).createdAt || new Date().toISOString();
                  const d = new Date(rawTimestamp);
                  const isValid = !isNaN(d.getTime());
                  const dateStr = isValid ? d.toLocaleDateString() : new Date().toLocaleDateString();
                  const timeStr = isValid
                    ? d.toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })
                    : '';
                  const displaySku = m.sku || prod?.sku || 'SKU';
                  const displayProdName = m.productName || prod?.name || 'Inventory Item';
                  const displayLocName = m.locationName || loc?.name || 'Main Fulfillment Center';
                  const displayMvType = m.movementType || (m as any).type || 'IN';
                  const displayBalance = typeof m.runningBalance === 'number' ? m.runningBalance : m.quantity;
                  const displayUom = prod?.unitOfMeasure || 'pcs';

                  return (
                    <tr
                      key={m.id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                    >
                      <td className="py-2.5 px-4 font-mono text-[11px] text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        <div>{dateStr}</div>
                        <div className="text-[10px] text-slate-400">{timeStr}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <MovementBadge type={displayMvType} />
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">
                          {displayProdName}
                        </div>
                        <div className="text-[10px] font-mono text-teal-700 dark:text-teal-400 font-bold">
                          {displaySku}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-700 dark:text-slate-300">
                        <div className="font-medium">{displayLocName}</div>
                        {m.targetLocationName && (
                          <div className="text-[10px] text-sky-600 font-medium">
                            Dest: {m.targetLocationName}
                          </div>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold">
                        <span
                          className={
                            displayMvType === 'IN'
                              ? 'text-emerald-700 dark:text-emerald-400'
                              : displayMvType === 'OUT'
                              ? 'text-rose-700 dark:text-rose-400'
                              : 'text-amber-700 dark:text-amber-400'
                          }
                        >
                          {displayMvType === 'IN' ? '+' : displayMvType === 'OUT' ? '-' : ''}
                          {Math.abs(m.quantity)} {displayUom}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-slate-800 dark:text-slate-200 font-semibold">
                        {displayBalance} {displayUom}
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-700 dark:text-slate-300 text-[11px]">
                        {m.referenceId}
                      </td>
                      <td className="py-2.5 px-3">
                        {m.reasonCode ? (
                          <ReasonBadge reason={m.reasonCode} />
                        ) : (
                          <span className="text-slate-400 text-[11px]">Automatic Ledger Sync</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-slate-500 dark:text-slate-400 text-[11px]">
                        {m.performedBy}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
