import React, { useState } from 'react';
import {
  FileDown,
  Plus,
  Search,
  CheckCircle2,
  Clock,
  Warehouse,
  ArrowRight,
  Package,
  Layers,
  Trash2,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { PurchaseOrder, POLineItem } from '../types/inventory';
import { Modal } from '../components/common/Modal';

export const PurchaseOrders: React.FC = () => {
  const {
    purchaseOrders,
    products,
    locations,
    formatCurrency,
    createPurchaseOrder,
    receiveGoods,
  } = useInventory();

  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [receivingPO, setReceivingPO] = useState<PurchaseOrder | null>(null);
  const [grnNotes, setGrnNotes] = useState('');

  // Create PO Form state
  const [supplierName, setSupplierName] = useState('');
  const [targetLocationId, setTargetLocationId] = useState(locations[0]?.id || '');
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
  const [poNotes, setPoNotes] = useState('');
  const [lineItems, setLineItems] = useState<POLineItem[]>([
    {
      productId: products[0]?.id || '',
      sku: products[0]?.sku || '',
      name: products[0]?.name || '',
      orderedQty: 20,
      receivedQty: 0,
      unitCost: products[0]?.costPrice || 0,
    },
  ]);

  const filteredPOs = purchaseOrders.filter((po) => {
    const q = searchQuery.toLowerCase();
    return (
      po.poNumber.toLowerCase().includes(q) ||
      po.supplierName.toLowerCase().includes(q) ||
      po.targetLocationName.toLowerCase().includes(q)
    );
  });

  // Add line item
  const handleAddLineItem = () => {
    const firstProd = products[0];
    if (!firstProd) return;
    setLineItems((prev) => [
      ...prev,
      {
        productId: firstProd.id,
        sku: firstProd.sku,
        name: firstProd.name,
        orderedQty: 10,
        receivedQty: 0,
        unitCost: firstProd.costPrice,
      },
    ]);
  };

  // Change product in line item
  const handleProductChange = (index: number, productId: string) => {
    const prod = products.find((p) => p.id === productId);
    if (!prod) return;
    setLineItems((prev) =>
      prev.map((item, i) =>
        i === index
          ? {
              ...item,
              productId: prod.id,
              sku: prod.sku,
              name: prod.name,
              unitCost: prod.costPrice,
            }
          : item
      )
    );
  };

  // Change qty or cost
  const handleItemChange = (index: number, field: 'orderedQty' | 'unitCost', value: number) => {
    setLineItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  // Remove line item
  const handleRemoveLineItem = (index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const calculateTotal = () => {
    return lineItems.reduce((acc, it) => acc + it.orderedQty * it.unitCost, 0);
  };

  // Handle PO submit
  const handleCreatePOSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplierName || lineItems.length === 0) return;

    const loc = locations.find((l) => l.id === targetLocationId) || locations[0];

    createPurchaseOrder({
      supplierName,
      targetLocationId: loc.id,
      targetLocationName: loc.name,
      orderDate,
      items: lineItems,
      totalAmount: calculateTotal(),
      notes: poNotes,
    });

    setIsCreateModalOpen(false);
    setSupplierName('');
    setPoNotes('');
  };

  // Handle Confirm Receipt (GRN)
  const handleConfirmGRN = () => {
    if (!receivingPO) return;
    receiveGoods(receivingPO.id, grnNotes);
    setReceivingPO(null);
    setGrnNotes('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Purchase Orders & Goods Receipt (GRN)
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Procure inventory from vendors. Receiving goods automatically creates immutable ledger
            receipt movements.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-colors self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          Create Purchase Order
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
            placeholder="Search by PO #, supplier, or location..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span>Total POs: </span>
          <span className="font-bold text-slate-800 dark:text-slate-200">
            {purchaseOrders.length}
          </span>
        </div>
      </div>

      {/* POs Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">PO Number</th>
                <th className="py-3 px-3">Supplier Name</th>
                <th className="py-3 px-3">Target Warehouse</th>
                <th className="py-3 px-3">Order Date</th>
                <th className="py-3 px-3">Line Items</th>
                <th className="py-3 px-3 text-right">Total Amount</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredPOs.map((po) => (
                <tr
                  key={po.id}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {po.poNumber}
                  </td>
                  <td className="py-3 px-3 font-semibold text-slate-800 dark:text-slate-200">
                    {po.supplierName}
                  </td>
                  <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                    {po.targetLocationName}
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400">
                    {po.orderDate}
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-col gap-0.5">
                      {po.items.map((it, idx) => (
                        <span key={idx} className="text-[11px] text-slate-600 dark:text-slate-300">
                          {it.orderedQty}× {it.name}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                    {formatCurrency(po.totalAmount)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    {po.status === 'received' ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3" /> Received (GRN)
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400 border border-amber-500/20">
                        <Clock className="h-3 w-3" /> Pending Delivery
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {po.status === 'pending' ? (
                      <button
                        onClick={() => setReceivingPO(po)}
                        className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-3 py-1.5 text-xs font-semibold text-white shadow-sm shadow-emerald-600/20 transition-all"
                      >
                        Receive Goods (GRN)
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-400 italic">
                        Ledger IN on {po.receivedDate || 'Record'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Receive Goods (GRN) Modal */}
      <Modal
        isOpen={Boolean(receivingPO)}
        onClose={() => setReceivingPO(null)}
        title={`Process Goods Receipt Note (GRN) — ${receivingPO?.poNumber}`}
        subtitle={`Receiving goods into ${receivingPO?.targetLocationName} automatically writes IN movements to ledger`}
        maxWidth="lg"
      >
        {receivingPO && (
          <div className="space-y-4">
            <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-3 text-xs text-indigo-700 dark:text-indigo-300">
              Confirming receipt will instantly increment stock counts and write immutable ledger
              transactions with unit cost stamps.
            </div>

            <div>
              <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Items Being Received
              </h4>
              <div className="divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800 p-2">
                {receivingPO.items.map((it, idx) => (
                  <div key={idx} className="flex items-center justify-between py-2 px-2 text-xs">
                    <div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">{it.name}</div>
                      <div className="font-mono text-[10px] text-indigo-600 dark:text-indigo-400">
                        {it.sku}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                        +{it.orderedQty} units
                      </div>
                      <div className="text-[10px] text-slate-400">
                        @ {formatCurrency(it.unitCost)}/unit
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Receipt Inspection & Warehouse Notes
              </label>
              <textarea
                rows={2}
                value={grnNotes}
                onChange={(e) => setGrnNotes(e.target.value)}
                placeholder="Cartons verified in good condition, seal intact..."
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => setReceivingPO(null)}
                className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmGRN}
                className="rounded-xl bg-emerald-600 hover:bg-emerald-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-emerald-600/20"
              >
                Confirm Receipt & Write to Ledger
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Create PO Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Purchase Order"
        subtitle="Specify supplier, receiving warehouse, and item quantities"
        maxWidth="2xl"
      >
        <form onSubmit={handleCreatePOSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Supplier / Vendor Name *
              </label>
              <input
                type="text"
                required
                value={supplierName}
                onChange={(e) => setSupplierName(e.target.value)}
                placeholder="e.g. AeroCraft Industrial Supplies"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Receiving Warehouse *
              </label>
              <select
                value={targetLocationId}
                onChange={(e) => setTargetLocationId(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
              >
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.code} — {loc.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Line Items */}
          <div className="border-t border-slate-100 dark:border-slate-800 pt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Order Line Items
              </span>
              <button
                type="button"
                onClick={handleAddLineItem}
                className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
              >
                + Add Another SKU
              </button>
            </div>

            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {lineItems.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 p-2 text-xs bg-slate-50/50 dark:bg-slate-800/40"
                >
                  <div className="flex-1">
                    <select
                      value={item.productId}
                      onChange={(e) => handleProductChange(idx, e.target.value)}
                      className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-1.5 text-xs font-medium"
                    >
                      {products.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.sku} — {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="w-24">
                    <input
                      type="number"
                      min="1"
                      value={item.orderedQty}
                      onChange={(e) =>
                        handleItemChange(idx, 'orderedQty', parseInt(e.target.value, 10) || 1)
                      }
                      placeholder="Qty"
                      className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-1.5 text-xs font-mono font-bold"
                    />
                  </div>

                  <div className="w-28">
                    <input
                      type="number"
                      step="0.01"
                      value={item.unitCost}
                      onChange={(e) =>
                        handleItemChange(idx, 'unitCost', parseFloat(e.target.value) || 0)
                      }
                      placeholder="Cost"
                      className="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 p-1.5 text-xs font-mono"
                    />
                  </div>

                  <button
                    type="button"
                    disabled={lineItems.length === 1}
                    onClick={() => handleRemoveLineItem(idx)}
                    className="p-1 text-slate-400 hover:text-rose-500 disabled:opacity-30"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <div className="flex justify-between items-center mt-3 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs font-bold">
              <span className="text-slate-500">Calculated PO Total:</span>
              <span className="font-mono text-sm text-indigo-600 dark:text-indigo-400">
                {formatCurrency(calculateTotal())}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Order Notes / Delivery Terms
            </label>
            <input
              type="text"
              value={poNotes}
              onChange={(e) => setPoNotes(e.target.value)}
              placeholder="e.g. Deliver via freight dock 3, Net 30"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Issue Purchase Order
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
