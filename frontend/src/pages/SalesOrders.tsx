import React, { useState } from 'react';
import {
  FileUp,
  Plus,
  Search,
  CheckCircle2,
  Clock,
  Warehouse,
  AlertCircle,
  Truck,
  Trash2,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { SalesOrder, SOLineItem } from '../types/inventory';
import { Modal } from '../components/common/Modal';

export const SalesOrders: React.FC = () => {
  const {
    salesOrders,
    products,
    locations,
    formatCurrency,
    createSalesOrder,
    fulfillSalesOrder,
  } = useInventory();

  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [fulfillingSO, setFulfillingSO] = useState<SalesOrder | null>(null);
  const [fulfillError, setFulfillError] = useState<string | null>(null);

  // Create SO Form state
  const [customerName, setCustomerName] = useState('');
  const [sourceLocationId, setSourceLocationId] = useState(locations[0]?.id || '');
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
  const [soNotes, setSoNotes] = useState('');
  const [lineItems, setLineItems] = useState<SOLineItem[]>([
    {
      productId: products[0]?.id || '',
      sku: products[0]?.sku || '',
      name: products[0]?.name || '',
      orderedQty: 2,
      fulfilledQty: 0,
      unitPrice: products[0]?.sellPrice || 0,
    },
  ]);

  const filteredSOs = salesOrders.filter((so) => {
    const q = searchQuery.toLowerCase();
    return (
      so.soNumber.toLowerCase().includes(q) ||
      so.customerName.toLowerCase().includes(q) ||
      so.sourceLocationName.toLowerCase().includes(q)
    );
  });

  const handleAddLineItem = () => {
    const firstProd = products[0];
    if (!firstProd) return;
    setLineItems((prev) => [
      ...prev,
      {
        productId: firstProd.id,
        sku: firstProd.sku,
        name: firstProd.name,
        orderedQty: 1,
        fulfilledQty: 0,
        unitPrice: firstProd.sellPrice,
      },
    ]);
  };

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
              unitPrice: prod.sellPrice,
            }
          : item
      )
    );
  };

  const handleItemChange = (index: number, field: 'orderedQty' | 'unitPrice', value: number) => {
    setLineItems((prev) =>
      prev.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const calculateTotal = () => {
    return lineItems.reduce((acc, it) => acc + it.orderedQty * it.unitPrice, 0);
  };

  const handleCreateSOSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerName || lineItems.length === 0) return;

    const loc = locations.find((l) => l.id === sourceLocationId) || locations[0];

    createSalesOrder({
      customerName,
      sourceLocationId: loc.id,
      sourceLocationName: loc.name,
      orderDate,
      items: lineItems,
      totalAmount: calculateTotal(),
      notes: soNotes,
    });

    setIsCreateModalOpen(false);
    setCustomerName('');
    setSoNotes('');
  };

  const handleConfirmFulfill = () => {
    if (!fulfillingSO) return;
    setFulfillError(null);
    const res = fulfillSalesOrder(fulfillingSO.id);
    if (!res.success) {
      setFulfillError(res.error || 'Fulfillment failed due to inventory constraint');
    } else {
      setFulfillingSO(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Sales Orders & Customer Fulfillment
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Manage customer demand. Fulfilling an order verifies available stock and writes OUT
            ledger entries.
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-colors self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          Create Sales Order
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
            placeholder="Search by SO #, customer, or location..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
          <span>Total SOs: </span>
          <span className="font-bold text-slate-800 dark:text-slate-200">{salesOrders.length}</span>
        </div>
      </div>

      {/* SOs Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">SO Number</th>
                <th className="py-3 px-3">Customer Name</th>
                <th className="py-3 px-3">Dispatch Warehouse</th>
                <th className="py-3 px-3">Order Date</th>
                <th className="py-3 px-3">Line Items</th>
                <th className="py-3 px-3 text-right">Total Order Value</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredSOs.map((so) => (
                <tr
                  key={so.id}
                  className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                    {so.soNumber}
                  </td>
                  <td className="py-3 px-3 font-semibold text-slate-800 dark:text-slate-200">
                    {so.customerName}
                  </td>
                  <td className="py-3 px-3 text-slate-600 dark:text-slate-300">
                    {so.sourceLocationName}
                  </td>
                  <td className="py-3 px-3 text-slate-500 dark:text-slate-400">
                    {so.orderDate}
                  </td>
                  <td className="py-3 px-3">
                    <div className="flex flex-col gap-0.5">
                      {so.items.map((it, idx) => (
                        <span key={idx} className="text-[11px] text-slate-600 dark:text-slate-300">
                          {it.orderedQty}× {it.name}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                    {formatCurrency(so.totalAmount)}
                  </td>
                  <td className="py-3 px-3 text-center">
                    {so.status === 'fulfilled' ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3" /> Fulfilled
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400 border border-amber-500/20">
                        <Clock className="h-3 w-3" /> Awaiting Dispatch
                      </span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {so.status === 'pending' ? (
                      <button
                        onClick={() => {
                          setFulfillError(null);
                          setFulfillingSO(so);
                        }}
                        className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 text-xs font-semibold text-white shadow-sm shadow-indigo-600/20 transition-all flex items-center gap-1.5 mx-auto"
                      >
                        <Truck className="h-3.5 w-3.5" />
                        Fulfill Order
                      </button>
                    ) : (
                      <span className="text-[11px] text-slate-400 italic">
                        Ledger OUT on {so.fulfilledDate || 'Record'}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Fulfill Order Modal */}
      <Modal
        isOpen={Boolean(fulfillingSO)}
        onClose={() => setFulfillingSO(null)}
        title={`Fulfill Sales Order — ${fulfillingSO?.soNumber}`}
        subtitle={`Dispatch items from ${fulfillingSO?.sourceLocationName}`}
        maxWidth="lg"
      >
        {fulfillingSO && (
          <div className="space-y-4">
            {fulfillError && (
              <div className="flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{fulfillError}</span>
              </div>
            )}

            <div>
              <h4 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Order Items to Pick & Pack
              </h4>
              <div className="divide-y divide-slate-100 dark:divide-slate-800 rounded-xl border border-slate-200 dark:border-slate-800 p-2">
                {fulfillingSO.items.map((it, idx) => {
                  const prod = products.find((p) => p.id === it.productId);
                  const availableInLoc = prod?.locationStock[fulfillingSO.sourceLocationId] || 0;
                  const isSufficient = availableInLoc >= it.orderedQty;

                  return (
                    <div key={idx} className="flex items-center justify-between py-2 px-2 text-xs">
                      <div>
                        <div className="font-bold text-slate-800 dark:text-slate-200">{it.name}</div>
                        <div className="font-mono text-[10px] text-indigo-600 dark:text-indigo-400">
                          {it.sku}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono font-bold text-rose-600 dark:text-rose-400">
                          -{it.orderedQty} units
                        </div>
                        <div
                          className={`text-[10px] font-medium ${
                            isSufficient
                              ? 'text-slate-400'
                              : 'text-rose-600 dark:text-rose-400 font-bold'
                          }`}
                        >
                          Available in warehouse: {availableInLoc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-3 text-xs text-slate-500 dark:text-slate-400">
              Fulfillment triggers automatic stock verification and creates immutable `OUT` ledger
              movements referencing {fulfillingSO.soNumber}.
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={() => setFulfillingSO(null)}
                className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmFulfill}
                className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
              >
                Confirm Dispatch & Write OUT
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Create Sales Order Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create New Sales Order"
        subtitle="Specify customer, dispatch warehouse, and ordered line items"
        maxWidth="2xl"
      >
        <form onSubmit={handleCreateSOSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Customer / Account Name *
              </label>
              <input
                type="text"
                required
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="e.g. NexGen Enterprises"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Dispatch Warehouse *
              </label>
              <select
                value={sourceLocationId}
                onChange={(e) => setSourceLocationId(e.target.value)}
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
              {lineItems.map((item, idx) => {
                const prod = products.find((p) => p.id === item.productId);
                const available = prod?.locationStock[sourceLocationId] || 0;

                return (
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
                      <div className="text-[10px] text-slate-400 mt-0.5 px-1">
                        Stock in selected warehouse: {available} pcs
                      </div>
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
                        value={item.unitPrice}
                        onChange={(e) =>
                          handleItemChange(idx, 'unitPrice', parseFloat(e.target.value) || 0)
                        }
                        placeholder="Price"
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
                );
              })}
            </div>

            <div className="flex justify-between items-center mt-3 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs font-bold">
              <span className="text-slate-500">Calculated Order Total:</span>
              <span className="font-mono text-sm text-indigo-600 dark:text-indigo-400">
                {formatCurrency(calculateTotal())}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Customer Shipping / PO Notes
            </label>
            <input
              type="text"
              value={soNotes}
              onChange={(e) => setSoNotes(e.target.value)}
              placeholder="e.g. Deliver before Friday, standard freight"
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
              Create Sales Order
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
