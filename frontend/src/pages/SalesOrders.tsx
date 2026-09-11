import React, { useState, useEffect } from 'react';
import {
  IconFileUp,
  IconPlus,
  IconSearch,
  IconCheck,
  IconClock,
  IconAlertCircle,
  IconAlertTriangle,
  IconTruck,
  IconTrash2,
  IconDownload,
  IconFileText,
  IconWarehouse,
  IconMapPin,
  IconPackage,
} from '../components/icons';
import { useInventory } from '../context/InventoryContext';
import { useTheme } from '../context/ThemeContext';
import { SalesOrder, SOLineItem, Product } from '../types/inventory';
import { Modal } from '../components/common/Modal';
import { PageMeta } from '../components/common/PageMeta';
import { ProductSearchDropdown } from '../components/common/ProductSearchDropdown';
import { WarehouseSelectDropdown } from '../components/common/WarehouseSelectDropdown';
import { StateSelectDropdown } from '../components/common/StateSelectDropdown';
import { api } from '../services/api';

export const SalesOrders: React.FC = () => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const {
    salesOrders,
    products,
    locations,
    selectedLocationId,
    formatCurrency,
    createSalesOrder,
    fulfillSalesOrder,
  } = useInventory();

  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedOrderForDetail, setSelectedOrderForDetail] = useState<SalesOrder | null>(null);
  const [fulfillingSO, setFulfillingSO] = useState<SalesOrder | null>(null);
  const [fulfillError, setFulfillError] = useState<string | null>(null);
  const [isFulfilling, setIsFulfilling] = useState(false);
  const [fulfilledInvoiceNotice, setFulfilledInvoiceNotice] = useState<{
    soNumber: string;
    invoiceNumber: string;
    invoiceId: string;
  } | null>(null);

  const [downloadingSoId, setDownloadingSoId] = useState<string | null>(null);
  const [downloadNotice, setDownloadNotice] = useState<string | null>(null);

  const handleDownloadOrderPdf = async (so: SalesOrder) => {
    setDownloadingSoId(so.id);
    setDownloadNotice(null);
    try {
      if (so.invoiceId) {
        await api.downloadInvoicePdf(so.invoiceId, so.soNumber);
      } else {
        await api.downloadSalesOrderPdf(so.id, so.soNumber);
      }
      setDownloadNotice(`Archived PDF for ${so.soNumber} successfully retrieved from MinIO.`);
      setTimeout(() => setDownloadNotice(null), 4000);
    } catch (err: any) {
      console.error('Failed to download PDF:', err);
      // Fallback in case of network issue
      const fallbackUrl = so.invoiceId ? api.getInvoicePdfUrl(so.invoiceId) : api.getSalesOrderPdfUrl(so.id);
      window.open(fallbackUrl, '_blank');
    } finally {
      setDownloadingSoId(null);
    }
  };

  // Create SO Form state
  const [customerName, setCustomerName] = useState('');
  const [customerGstin, setCustomerGstin] = useState('');
  const [billingAddress, setBillingAddress] = useState('');
  const [billingState, setBillingState] = useState('Karnataka');
  const [billingStateCode, setBillingStateCode] = useState('29');
  const [hasSeparateShipping, setHasSeparateShipping] = useState(false);
  const [shippingAddress, setShippingAddress] = useState('');
  const [shippingState, setShippingState] = useState('Tamil Nadu');
  const [shippingStateCode, setShippingStateCode] = useState('33');
  const [sourceLocationId, setSourceLocationId] = useState(
    selectedLocationId !== 'all' ? selectedLocationId : (locations[0]?.id || '')
  );
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
  const [soNotes, setSoNotes] = useState('');

  // Selected warehouse metadata
  const selectedLocation = locations.find((l) => l.id === selectedLocationId);
  const currentSourceLoc = locations.find((l) => l.id === sourceLocationId);

  useEffect(() => {
    if (selectedLocationId !== 'all') {
      setSourceLocationId(selectedLocationId);
    } else if (!sourceLocationId && locations.length > 0) {
      setSourceLocationId(locations[0].id);
    }
  }, [locations, selectedLocationId]);

  const [lineItems, setLineItems] = useState<SOLineItem[]>([
    {
      productId: products[0]?.id || '',
      sku: products[0]?.sku || '',
      name: products[0]?.name || '',
      orderedQty: 2,
      fulfilledQty: 0,
      unitPrice: products[0]?.sellPrice || 120,
      discountPercent: 0,
    },
  ]);

  const stockShortages = lineItems
    .map((it) => {
      const prod = products.find((p) => p.id === it.productId);
      const avail = sourceLocationId
        ? (prod?.locationStock?.[sourceLocationId] ?? 0)
        : (prod?.currentStock ?? 0);
      return {
        sku: it.sku || prod?.sku || 'Item',
        name: it.name || prod?.name || 'Product',
        orderedQty: it.orderedQty || 0,
        availableStock: avail,
        unit: prod?.unitOfMeasure || 'pcs',
        isZero: avail === 0,
        isShortage: (it.orderedQty || 0) > avail,
      };
    })
    .filter((s) => s.isShortage);

  const handleAddLineItem = () => {
    const candidate = products[0];
    if (!candidate) return;
    setLineItems((prev) => [
      ...prev,
      {
        productId: candidate.id,
        sku: candidate.sku,
        name: candidate.name,
        orderedQty: 1,
        fulfilledQty: 0,
        unitPrice: candidate.sellPrice,
        discountPercent: 0,
      },
    ]);
  };

  const handleUpdateItem = (index: number, updates: Partial<SOLineItem>) => {
    setLineItems((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], ...updates };
      return copy;
    });
  };

  const handleProductSelect = (index: number, prodId: string) => {
    const p = products.find((prod) => prod.id === prodId);
    if (!p) return;
    handleUpdateItem(index, {
      productId: p.id,
      sku: p.sku,
      name: p.name,
      unitPrice: p.sellPrice,
    });
  };

  const handleRemoveItem = (index: number) => {
    if (lineItems.length <= 1) return;
    setLineItems((prev) => prev.filter((_, i) => i !== index));
  };

  const calculateTotalGross = () =>
    lineItems.reduce((acc, it) => acc + (it.orderedQty || 0) * (it.unitPrice || 0), 0);

  const calculateTotalDiscount = () =>
    lineItems.reduce((acc, it) => {
      const gross = (it.orderedQty || 0) * (it.unitPrice || 0);
      const discPct = Math.max(0, Math.min(100, it.discountPercent || 0));
      return acc + (gross * discPct) / 100;
    }, 0);

  const calculateGrandTotal = () =>
    Math.max(0, calculateTotalGross() - calculateTotalDiscount());

  const handleSubmitSO = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customerName || !sourceLocationId || lineItems.length === 0) return;

    if (stockShortages.length > 0) {
      const shortageDetails = stockShortages
        .map((s) => `• ${s.sku} (${s.name}): ${s.isZero ? '0 in stock' : `Only ${s.availableStock} in stock`}, Ordered: ${s.orderedQty} ${s.unit}`)
        .join('\n');
      const proceed = window.confirm(
        `Warning: Warehouse "${currentSourceLoc?.name || 'Selected Warehouse'}" has insufficient stock:\n\n${shortageDetails}\n\nFulfilling and dispatching this order will be blocked until inventory is replenished or transferred.\n\nDo you want to proceed and create this Sales Order anyway?`
      );
      if (!proceed) return;
    }

    const sourceLoc = locations.find((l) => l.id === sourceLocationId);
    const isShipSeparate = hasSeparateShipping && Boolean(shippingAddress.trim());
    const effectiveShipState = isShipSeparate ? shippingState : billingState;
    const effectiveShipCode = isShipSeparate ? shippingStateCode : billingStateCode;

    createSalesOrder({
      customerName,
      customerGstin: customerGstin || undefined,
      billingAddress: billingAddress || undefined,
      shippingAddress: isShipSeparate ? shippingAddress : (billingAddress || undefined),
      billingState: billingState,
      billingStateCode: billingStateCode,
      shippingState: isShipSeparate ? shippingState : undefined,
      shippingStateCode: isShipSeparate ? shippingStateCode : undefined,
      state: effectiveShipState,
      stateCode: effectiveShipCode,
      sourceLocationId,
      sourceLocationName: sourceLoc?.name || 'Warehouse',
      orderDate,
      items: lineItems,
      totalAmount: calculateGrandTotal(),
      notes: soNotes,
    });

    setIsCreateModalOpen(false);
    setCustomerName('');
    setCustomerGstin('');
    setBillingAddress('');
    setShippingAddress('');
    setHasSeparateShipping(false);
    setSoNotes('');
    setSourceLocationId(selectedLocationId !== 'all' ? selectedLocationId : (locations[0]?.id || ''));
  };

  const handleConfirmFulfillment = async () => {
    if (!fulfillingSO) return;
    setFulfillError(null);

    // Validation: check that sufficient stock exists in the source location
    for (const item of fulfillingSO.items) {
      const prod = products.find((p) => p.id === item.productId);
      const available = prod?.locationStock[fulfillingSO.sourceLocationId] || 0;
      if (available < item.orderedQty) {
        setFulfillError(
          `Cannot fulfill order: Insufficient stock for ${item.name} (${item.sku}) in ${fulfillingSO.sourceLocationName}. Required: ${item.orderedQty}, Available: ${available}`
        );
        return;
      }
    }

    setIsFulfilling(true);
    try {
      const res = await fulfillSalesOrder(fulfillingSO.id);
      if (!res.success) {
        setFulfillError(res.error || 'Failed to dispatch order and generate invoice.');
        return;
      }

      setFulfillingSO(null);
      if (res.invoice_number && res.invoice_id) {
        setFulfilledInvoiceNotice({
          soNumber: fulfillingSO.soNumber,
          invoiceNumber: res.invoice_number,
          invoiceId: res.invoice_id,
        });
      }
    } catch (err: any) {
      setFulfillError(err.message || 'Error fulfilling order');
    } finally {
      setIsFulfilling(false);
    }
  };

  const filteredSOs = salesOrders.filter((so) => {
    if (selectedLocationId !== 'all' && so.sourceLocationId !== selectedLocationId) {
      return false;
    }
    const q = searchQuery.toLowerCase();
    return (
      so.soNumber.toLowerCase().includes(q) ||
      so.customerName.toLowerCase().includes(q) ||
      so.sourceLocationName.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      <PageMeta
        title="Sales Orders & Customer Dispatches | Invenza Inventory"
        description="Fulfillment workflow, order dispatches, picking slips, and automated double-entry ledger stock depletion."
        canonicalPath="/sales-orders"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Sales Orders & Customer Fulfillment
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Book sales orders against warehouse stock and manage customer dispatches. Fulfilling an order
            verifies available quantities and automatically records OUT movements in the ledger.
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-2 text-xs font-bold text-white shadow-subtle transition-colors self-start sm:self-auto"
        >
          <IconPlus className="h-4 w-4" />
          Create Sales Order
        </button>
      </div>

      {/* Invoice Generation Success Notification */}
      {fulfilledInvoiceNotice && (
        <div className="rounded-xl border border-teal-500/30 bg-teal-500/10 p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-card animate-fadeIn">
          <div className="flex items-center gap-3">
            <div className="rounded-full bg-teal-600 p-2 text-white shrink-0">
              <IconCheck className="h-4 w-4" />
            </div>
            <div>
              <div className="font-bold text-sm text-teal-950 dark:text-teal-100">
                Order {fulfilledInvoiceNotice.soNumber} Dispatched & Invoiced!
              </div>
              <div className="text-xs text-teal-800 dark:text-teal-200">
                GST Tax Invoice <span className="font-mono font-bold text-teal-900 dark:text-teal-300">{fulfilledInvoiceNotice.invoiceNumber}</span> has been sequentially issued and archived.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 self-end sm:self-auto">
            <button
              type="button"
              onClick={() => api.downloadInvoicePdf(fulfilledInvoiceNotice.invoiceId, fulfilledInvoiceNotice.invoiceNumber)}
              className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-3.5 py-1.5 text-xs font-bold text-white shadow-subtle transition-colors"
            >
              <IconDownload className="h-3.5 w-3.5" />
              <span>Download Tax Invoice PDF</span>
            </button>
            <button
              type="button"
              onClick={() => setFulfilledInvoiceNotice(null)}
              className="text-xs font-semibold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 px-2 py-1"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* MinIO PDF Download Notification */}
      {downloadNotice && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 flex items-center justify-between text-xs text-emerald-800 dark:text-emerald-200 shadow-card animate-fadeIn">
          <div className="flex items-center gap-2">
            <IconCheck className="h-4 w-4 text-emerald-600" />
            <span className="font-semibold">{downloadNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setDownloadNotice(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Active Warehouse Filter Banner */}
      {selectedLocationId !== 'all' && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50/90 dark:border-teal-500/25 dark:bg-teal-500/10 px-4 py-3 text-xs text-teal-900 dark:text-teal-300 shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 shrink-0">
              <IconWarehouse className="h-4 w-4" />
            </div>
            <div>
              <span className="text-slate-600 dark:text-slate-400">Fulfillment Warehouse Filter: </span>
              <strong className="text-slate-900 dark:text-white font-bold">{selectedLocation?.name || 'Warehouse'}</strong>
              {selectedLocation?.code && (
                <span className="ml-2 rounded bg-teal-100/80 dark:bg-teal-500/10 text-teal-800 dark:text-teal-300 border border-teal-300 dark:border-teal-500/20 px-1.5 py-0.5 text-[11px] font-mono font-semibold">
                  {selectedLocation.code}
                </span>
              )}
            </div>
          </div>
          <span className="text-[11px] text-teal-700 dark:text-teal-400/90 font-mono font-semibold">
            {filteredSOs.length} of {salesOrders.length} orders shown
          </span>
        </div>
      )}

      {/* Filter toolbar */}
      <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] p-3 shadow-card">
        <div className="relative w-full sm:w-80">
          <IconSearch className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search SO #, customer, warehouse..."
            className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] pl-8 pr-3 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-600"
          />
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
          Total Orders: <span className="font-bold text-slate-800 dark:text-slate-200">{filteredSOs.length}</span>
          {selectedLocationId !== 'all' && (
            <span className="text-teal-600 dark:text-teal-400 ml-1.5">
              (from {selectedLocation?.name})
            </span>
          )}
        </div>
      </div>

      {/* Sales Orders List Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-card">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs table-fixed">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-[#F6F8FA] dark:bg-[#0C1017] text-slate-600 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-2.5 text-left whitespace-nowrap w-[12%]">SO Number</th>
                <th className="py-3 px-2.5 text-left whitespace-nowrap w-[13%]">Customer / Client</th>
                <th className="py-3 px-2 text-left whitespace-nowrap w-[11%]">Order Date</th>
                <th className="py-3 px-2 text-left whitespace-nowrap w-[20%]">Items Ordered</th>
                <th className="py-3 px-2 text-right whitespace-nowrap w-[10%]">
                  <div className="w-full text-right">Order Value</div>
                </th>
                <th className="py-3 px-2 text-center whitespace-nowrap w-[16%]">
                  <div className="w-full text-center">Status</div>
                </th>
                <th className="py-3 px-2.5 text-center whitespace-nowrap w-[18%]">
                  <div className="w-full text-center">Fulfillment Action</div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredSOs.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <IconFileUp className="mx-auto h-8 w-8 text-slate-500 mb-2 opacity-50" />
                    <p className="font-semibold text-sm">No sales orders found</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {selectedLocationId !== 'all'
                        ? `No sales orders recorded for ${selectedLocation?.name || 'this warehouse'}.`
                        : 'No sales orders match your search query.'}
                    </p>
                  </td>
                </tr>
              )}
              {filteredSOs.map((so, soIdx) => (
                <tr
                  key={so.id}
                  onClick={() => setSelectedOrderForDetail(so)}
                  className="relative group cursor-pointer hover:z-30 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <td className="py-2.5 px-2.5 text-left whitespace-nowrap">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedOrderForDetail(so);
                      }}
                      className="font-mono font-bold text-teal-700 dark:text-teal-400 hover:text-teal-900 dark:hover:text-teal-200 transition-colors text-left hover:underline whitespace-nowrap"
                      title="Click to view complete sales order details"
                    >
                      {so.soNumber}
                    </button>
                  </td>
                  <td className="py-2.5 px-2.5 text-left font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap truncate" title={so.customerName}>
                    {so.customerName}
                  </td>
                  <td className="py-2.5 px-2 text-left text-slate-500 dark:text-slate-400 font-mono text-[11px] whitespace-nowrap">
                    {so.orderDate}
                  </td>
                  <td className="py-2.5 px-2 text-left">
                    {so.items.length === 0 ? (
                      <span className="text-slate-400 text-[11px]">-</span>
                    ) : (
                      <div
                        className="group/items relative inline-flex items-center gap-1.5 cursor-pointer max-w-full"
                        title={so.items
                          .map((it) => `${it.orderedQty}x ${it.name} (${it.sku})`)
                          .join('\n')}
                      >
                        {/* Primary summary: First item */}
                        <span className="text-[11px] text-slate-700 dark:text-slate-300 truncate max-w-[140px]">
                          <span className="font-mono font-bold text-teal-700 dark:text-teal-400">
                            {so.items[0].orderedQty}x
                          </span>{' '}
                          <span className="truncate">{so.items[0].name}</span>
                        </span>

                        {/* More items badge if > 1 item */}
                        {so.items.length > 1 && (
                          <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold font-mono bg-slate-100 dark:bg-slate-800 text-teal-700 dark:text-teal-400 border border-slate-200 dark:border-slate-700/80 shrink-0 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors whitespace-nowrap">
                            +{so.items.length - 1} more
                          </span>
                        )}

                        {/* Hover Tooltip / Card revealing full item list */}
                        <div
                          className={`absolute left-0 ${
                            soIdx < 3 ? 'top-full mt-1.5' : 'bottom-full mb-1.5'
                          } hidden group-hover/items:flex flex-col z-50 w-72 rounded-xl bg-white dark:bg-[#0E1420] text-slate-800 dark:text-slate-100 p-3 text-xs shadow-2xl border border-slate-200 dark:border-slate-700/80 ring-1 ring-black/10 dark:ring-white/10 pointer-events-none transition-all duration-150 animate-in fade-in zoom-in-95`}
                        >
                          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2 mb-2">
                            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">
                              Items in Order ({so.items.length})
                            </span>
                            <span className="font-mono text-[10px] text-teal-600 dark:text-teal-400 font-bold">
                              {so.items.reduce((acc, it) => acc + (it.orderedQty || 0), 0)} units total
                            </span>
                          </div>

                          <div className="flex flex-col gap-2 max-h-56 overflow-y-auto pr-1">
                            {so.items.map((it, idx) => (
                              <div
                                key={idx}
                                className="flex items-start justify-between gap-2 text-[11px]"
                              >
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-1.5 truncate">
                                    <span className="font-mono font-bold text-teal-600 dark:text-teal-400 shrink-0">
                                      {it.orderedQty}x
                                    </span>
                                    <span className="font-medium text-slate-800 dark:text-slate-200 truncate">
                                      {it.name}
                                    </span>
                                  </div>
                                  <span className="font-mono text-[10px] text-slate-400 dark:text-slate-500 block pl-5">
                                    {it.sku}
                                  </span>
                                </div>
                                <span className="font-mono text-[11px] text-slate-600 dark:text-slate-400 shrink-0 text-right">
                                  {formatCurrency(it.unitPrice * it.orderedQty)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="py-2.5 px-2 text-right font-mono font-bold text-slate-900 dark:text-white whitespace-nowrap">
                    <div className="w-full text-right">{formatCurrency(so.totalAmount)}</div>
                  </td>
                  <td className="py-2.5 px-2 text-center whitespace-nowrap">
                    <div className="w-full flex items-center justify-center">
                      {so.status === 'fulfilled' ? (
                        <span className="inline-flex items-center gap-1 rounded-md font-mono text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20 px-2 py-0.5 whitespace-nowrap shrink-0">
                          <IconCheck className="h-3 w-3 shrink-0" /> Dispatched
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-md font-mono text-[10px] font-bold bg-amber-50 text-amber-900 border border-amber-200 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20 px-2 py-0.5 whitespace-nowrap shrink-0">
                          <IconClock className="h-3 w-3 shrink-0" /> Awaiting Picking
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-2.5 px-2.5 text-center whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                    {so.status === 'pending' ? (
                      <div className="flex items-center justify-center">
                        <button
                          type="button"
                          onClick={() => {
                            setFulfillError(null);
                            setFulfillingSO(so);
                          }}
                          className="rounded-lg bg-teal-700 hover:bg-teal-800 px-3 py-1 text-xs font-bold text-white shadow-subtle transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0"
                        >
                          <IconTruck className="h-3.5 w-3.5" />
                          Pick & Dispatch
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleDownloadOrderPdf(so)}
                          disabled={downloadingSoId === so.id}
                          className="flex items-center gap-1 rounded border border-teal-600/30 bg-teal-500/10 hover:bg-teal-500/20 px-2.5 py-1 text-[11px] font-semibold text-teal-700 dark:text-teal-300 transition-colors shadow-subtle whitespace-nowrap shrink-0"
                          title="Download GST Tax Invoice PDF from MinIO"
                        >
                          <IconDownload className="h-3 w-3" />
                          <span>{downloadingSoId === so.id ? 'Downloading...' : 'Tax Invoice'}</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* SALES ORDER COMPREHENSIVE DETAIL VIEW MODAL */}
      <Modal
        isOpen={Boolean(selectedOrderForDetail)}
        onClose={() => setSelectedOrderForDetail(null)}
        title={`Sales Order Details: ${selectedOrderForDetail?.soNumber}`}
        subtitle={`Placed on ${selectedOrderForDetail?.orderDate} • Status: ${
          selectedOrderForDetail?.status === 'fulfilled' ? 'Dispatched & Fulfilled' : 'Awaiting Warehouse Picking'
        }`}
        maxWidth="3xl"
      >
        {selectedOrderForDetail && (() => {
          const detailWarehouse = locations.find(
            (l) => l.id === selectedOrderForDetail.sourceLocationId || l.name === selectedOrderForDetail.sourceLocationName
          );
          const totalUnits = selectedOrderForDetail.items.reduce((acc, it) => acc + (it.orderedQty || 0), 0);

          return (
            <div className="space-y-4">
              {/* Top Highlights Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Fulfillment Warehouse Card - Prominently showing removed column */}
                <div className="rounded-xl border border-teal-500/25 bg-teal-500/10 dark:bg-teal-950/30 p-3.5 space-y-1">
                  <div className="flex items-center gap-1.5 text-teal-700 dark:text-teal-400">
                    <IconWarehouse className="h-4 w-4 shrink-0" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider">
                      Fulfillment Warehouse
                    </span>
                  </div>
                  <div className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5 pt-0.5">
                    <span>{selectedOrderForDetail.sourceLocationName}</span>
                    {detailWarehouse?.code && (
                      <span className="rounded bg-teal-500/20 px-1.5 py-0.5 text-[10px] font-mono font-bold text-teal-800 dark:text-teal-300">
                        {detailWarehouse.code}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                    {detailWarehouse?.address || detailWarehouse?.city || 'Stock source for physical dispatch & ledger OUT'}
                  </p>
                </div>

                {/* Fulfillment Status Card */}
                <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#0C1017] p-3.5 space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                    <IconClock className="h-4 w-4 shrink-0" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider">
                      Fulfillment Status
                    </span>
                  </div>
                  <div className="pt-0.5">
                    {selectedOrderForDetail.status === 'fulfilled' ? (
                      <span className="inline-flex items-center gap-1.5 rounded-md font-mono text-xs font-bold bg-emerald-500/10 px-2 py-0.5 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20">
                        <IconCheck className="h-3.5 w-3.5 shrink-0" /> Dispatched
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 rounded-md font-mono text-xs font-bold bg-amber-500/10 px-2 py-0.5 text-amber-700 dark:text-amber-400 border border-amber-500/20">
                        <IconClock className="h-3.5 w-3.5 shrink-0" /> Awaiting Picking
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                    {selectedOrderForDetail.fulfilledDate
                      ? `Dispatched on ${selectedOrderForDetail.fulfilledDate}`
                      : `Booked on ${selectedOrderForDetail.orderDate}`}
                  </p>
                </div>

                {/* Total Valuation Card */}
                <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#0C1017] p-3.5 space-y-1">
                  <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
                    <IconFileText className="h-4 w-4 shrink-0" />
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider">
                      Total Valuation
                    </span>
                  </div>
                  <div className="font-mono font-bold text-lg text-slate-900 dark:text-white pt-0.5">
                    {formatCurrency(selectedOrderForDetail.totalAmount)}
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                    {totalUnits} total units • {selectedOrderForDetail.items.length} line items
                  </p>
                </div>
              </div>

              {/* Customer & Address Details (2-Column Grid) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-[#F8FAFC] dark:bg-[#0C1017] p-4">
                {/* Bill-to Section */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-1.5">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Customer & Billing Profile
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div>
                      <span className="text-slate-400 text-[11px] block">Customer / Account:</span>
                      <span className="font-bold text-slate-900 dark:text-white text-sm">
                        {selectedOrderForDetail.customerName}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Customer GSTIN:</span>
                      <span className="font-mono text-slate-700 dark:text-slate-300 font-semibold">
                        {selectedOrderForDetail.customerGstin || 'Unregistered Consumer / Retail'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Billing Address:</span>
                      <span className="text-slate-700 dark:text-slate-300 leading-snug block">
                        {selectedOrderForDetail.billingAddress || 'Standard account billing address'}
                      </span>
                      <span className="text-[11px] font-mono text-teal-600 dark:text-teal-400 mt-0.5 block">
                        {selectedOrderForDetail.billingState || selectedOrderForDetail.state || 'Karnataka'} (State Code: {selectedOrderForDetail.billingStateCode || selectedOrderForDetail.stateCode || '29'})
                      </span>
                    </div>
                  </div>
                </div>

                {/* Ship-to Section */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-1.5">
                    <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Dispatch & Destination Profile
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs">
                    <div>
                      <span className="text-slate-400 text-[11px] block">Shipping Destination Address:</span>
                      <span className="text-slate-700 dark:text-slate-300 leading-snug block">
                        {selectedOrderForDetail.shippingAddress || selectedOrderForDetail.billingAddress || 'Same as billing address'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 text-[11px] block">Place of Supply:</span>
                      <span className="font-mono text-teal-600 dark:text-teal-400 font-semibold block">
                        {selectedOrderForDetail.shippingState || selectedOrderForDetail.billingState || 'Same as billing state'} (State Code: {selectedOrderForDetail.shippingStateCode || selectedOrderForDetail.billingStateCode || '29'})
                      </span>
                    </div>
                    {selectedOrderForDetail.invoiceId && (
                      <div>
                        <span className="text-slate-400 text-[11px] block">Sequential Tax Invoice:</span>
                        <span className="font-mono text-xs font-bold text-teal-700 dark:text-teal-300 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/20 inline-block mt-0.5">
                          {selectedOrderForDetail.invoiceId}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Line Items Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                    Ordered Line Items ({selectedOrderForDetail.items.length})
                  </span>
                  <span className="text-xs font-mono text-teal-600 dark:text-teal-400 font-bold">
                    Total Units: {totalUnits}
                  </span>
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924]">
                  <table className="w-full text-left text-xs min-w-[540px]">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] text-slate-500 dark:text-slate-400 font-semibold uppercase text-[10px]">
                        <th className="py-2.5 px-3 text-left w-10">#</th>
                        <th className="py-2.5 px-3 text-left">SKU & Item Description</th>
                        <th className="py-2.5 px-3 text-center w-24">Ordered Qty</th>
                        <th className="py-2.5 px-3 text-center w-24">Fulfilled</th>
                        <th className="py-2.5 px-3 text-right w-28">Unit Price</th>
                        <th className="py-2.5 px-3 text-right w-28">Line Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                      {selectedOrderForDetail.items.map((it, idx) => {
                        const lineTotal = it.unitPrice * it.orderedQty;
                        return (
                          <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                            <td className="py-2.5 px-3 text-slate-400 text-[11px]">{idx + 1}</td>
                            <td className="py-2.5 px-3 font-sans">
                              <div className="font-semibold text-slate-800 dark:text-slate-200">{it.name}</div>
                              <div className="font-mono text-[10px] text-teal-600 dark:text-teal-400">{it.sku}</div>
                            </td>
                            <td className="py-2.5 px-3 text-center font-bold text-slate-800 dark:text-slate-200">
                              {it.orderedQty}
                            </td>
                            <td className="py-2.5 px-3 text-center">
                              <span className={`font-semibold ${
                                selectedOrderForDetail.status === 'fulfilled' ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'
                              }`}>
                                {it.fulfilledQty ?? (selectedOrderForDetail.status === 'fulfilled' ? it.orderedQty : 0)}
                              </span>
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-600 dark:text-slate-400">
                              {formatCurrency(it.unitPrice)}
                              {it.discountPercent && it.discountPercent > 0 ? (
                                <div className="text-[10px] text-emerald-600 dark:text-emerald-400">
                                  -{it.discountPercent}%
                                </div>
                              ) : null}
                            </td>
                            <td className="py-2.5 px-3 text-right font-bold text-slate-900 dark:text-white">
                              {formatCurrency(lineTotal)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="border-t border-slate-200 dark:border-slate-800 bg-[#F8FAFC] dark:bg-[#0C1017] font-mono">
                      <tr>
                        <td colSpan={5} className="py-2.5 px-3 text-right font-sans font-bold text-slate-700 dark:text-slate-300">
                          Grand Total Valuation:
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-sm text-slate-900 dark:text-white">
                          {formatCurrency(selectedOrderForDetail.totalAmount)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>

              {/* Order Notes / Instructions */}
              {selectedOrderForDetail.notes && (
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#0C1017] p-3 text-xs">
                  <span className="font-semibold text-slate-500 dark:text-slate-400 uppercase text-[10px] tracking-wider block mb-1">
                    Order Instructions & Internal Notes:
                  </span>
                  <p className="text-slate-700 dark:text-slate-300">{selectedOrderForDetail.notes}</p>
                </div>
              )}

              {/* Modal Action: Pick & Dispatch for pending orders */}
              {selectedOrderForDetail.status === 'pending' && (
                <div className="flex items-center justify-end pt-3 border-t border-slate-100 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => {
                      const targetSo = selectedOrderForDetail;
                      setSelectedOrderForDetail(null);
                      setFulfillError(null);
                      setFulfillingSO(targetSo);
                    }}
                    className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-4 py-2 text-xs font-bold text-white shadow-subtle transition-colors"
                  >
                    <IconTruck className="h-3.5 w-3.5" />
                    <span>Pick & Dispatch</span>
                  </button>
                </div>
              )}
            </div>
          );
        })()}
      </Modal>

      {/* Fulfill Order Modal */}
      <Modal
        isOpen={Boolean(fulfillingSO)}
        onClose={() => setFulfillingSO(null)}
        title={`Fulfill Sales Order: ${fulfillingSO?.soNumber}`}
        subtitle={`Dispatch items from ${fulfillingSO?.sourceLocationName}`}
        maxWidth="lg"
      >
        {fulfillingSO && (
          <div className="space-y-4">
            {fulfillError && (
              <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-700 dark:text-rose-400 font-medium">
                <IconAlertCircle className="h-4 w-4 shrink-0" />
                <span>{fulfillError}</span>
              </div>
            )}

            <div>
              <h4 className="text-xs font-mono font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
                Order Items to Pick & Pack
              </h4>
              <div className="divide-y divide-slate-100 dark:divide-slate-800 rounded-lg border border-slate-200 dark:border-slate-800 p-2 bg-[#F4F5F8] dark:bg-[#0C1017]">
                {fulfillingSO.items.map((it, idx) => {
                  const prod = products.find((p) => p.id === it.productId);
                  const availableInLoc = prod?.locationStock[fulfillingSO.sourceLocationId] || 0;
                  const isSufficient = availableInLoc >= it.orderedQty;

                  return (
                    <div key={idx} className="flex items-center justify-between py-2 px-2 text-xs">
                      <div>
                        <div className="font-bold text-slate-800 dark:text-slate-200">{it.name}</div>
                        <div className="font-mono text-[10px] text-teal-700 dark:text-teal-400">
                          {it.sku}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-mono font-bold text-rose-700 dark:text-rose-400">
                          -{it.orderedQty} units
                        </div>
                        <div
                          className={`text-[10px] font-mono ${
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

            <div className="rounded-lg border border-amber-500/25 bg-amber-500/10 p-3 text-xs text-amber-800 dark:text-amber-300">
              Confirming dispatch will permanently decrement physical units at{' '}
              <strong className="text-slate-900 dark:text-white font-bold">
                {fulfillingSO.sourceLocationName}
              </strong>{' '}
              and post immutable OUT transactions to the movement ledger.
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setFulfillingSO(null)}
                className="rounded-lg border border-slate-200 dark:border-slate-800 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmFulfillment}
                className="rounded-lg bg-teal-700 hover:bg-teal-800 px-5 py-2 text-xs font-bold text-white shadow-subtle transition-colors"
              >
                Confirm Dispatch & Record Ledger OUT
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Create Sales Order Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Create Customer Sales Order (SO)"
        subtitle="Reserve and allocate catalog items for shipment to an account"
        maxWidth="2xl"
      >
        <form onSubmit={handleSubmitSO} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Customer / Client Name *
              </label>
              <input
                type="text"
                required
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
                placeholder="e.g. Metro Retail Corp"
                className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#131924] px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-teal-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Fulfillment Warehouse *
              </label>
              <WarehouseSelectDropdown
                locations={locations}
                selectedLocationId={sourceLocationId}
                onSelect={setSourceLocationId}
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Order Date
              </label>
              <input
                type="date"
                value={orderDate}
                onChange={(e) => setOrderDate(e.target.value)}
                className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#131924] px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-teal-600"
              />
            </div>
          </div>

          {/* Customer Tax & Dispatch Details */}
          <div className="space-y-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F8FAFC] dark:bg-[#0C1017] p-3">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Customer GSTIN (Optional)
                </label>
                <input
                  type="text"
                  maxLength={15}
                  value={customerGstin}
                  onChange={(e) => setCustomerGstin(e.target.value.toUpperCase())}
                  placeholder="e.g. 29ABCDE1234F1Z5"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] px-2.5 py-1.5 text-xs font-mono uppercase focus:outline-none focus:ring-1 focus:ring-teal-600"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Billing State *
                </label>
                <StateSelectDropdown
                  selectedCode={billingStateCode}
                  onSelect={(code, name) => {
                    setBillingStateCode(code);
                    setBillingState(name);
                  }}
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-600 dark:text-slate-400 mb-1">
                  Billing Address *
                </label>
                <input
                  type="text"
                  required
                  value={billingAddress}
                  onChange={(e) => setBillingAddress(e.target.value)}
                  placeholder="Street address, City, PIN"
                  className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-teal-600"
                />
              </div>
            </div>

            {/* Bill-to / Ship-to Toggle */}
            <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={hasSeparateShipping}
                  onChange={(e) => setHasSeparateShipping(e.target.checked)}
                  className="rounded border-slate-300 text-teal-600 focus:ring-teal-500 h-4 w-4"
                />
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Separate Shipping / Delivery Address (Bill-to / Ship-to Scenario)
                </span>
              </label>

              {hasSeparateShipping && (
                <div className="mt-2.5 grid grid-cols-1 sm:grid-cols-2 gap-3 p-2.5 rounded-lg bg-teal-500/5 border border-teal-500/20">
                  <div>
                    <label className="block text-[11px] font-semibold text-teal-900 dark:text-teal-300 mb-1">
                      Shipping / Dispatch Destination State *
                    </label>
                    <StateSelectDropdown
                      selectedCode={shippingStateCode}
                      onSelect={(code, name) => {
                        setShippingStateCode(code);
                        setShippingState(name);
                      }}
                    />
                    <span className="text-[10px] text-teal-600 dark:text-teal-400 mt-0.5 block">
                      Determines Place of Supply for GST calculation when shipping differs
                    </span>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-teal-900 dark:text-teal-300 mb-1">
                      Shipping Destination Address *
                    </label>
                    <input
                      type="text"
                      required={hasSeparateShipping}
                      value={shippingAddress}
                      onChange={(e) => setShippingAddress(e.target.value)}
                      placeholder="Delivery site / Warehouse address"
                      className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] px-2.5 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-teal-600"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Line items editor */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                  Order Line Items
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  ({lineItems.length} {lineItems.length === 1 ? 'item' : 'items'})
                </span>
              </div>
              <button
                type="button"
                onClick={handleAddLineItem}
                className="flex items-center gap-1 text-xs font-bold text-teal-700 dark:text-teal-400 hover:underline"
              >
                <IconPlus className="h-3.5 w-3.5" /> Add SKU
              </button>
            </div>

            {/* Table headers */}
            <div className="hidden sm:flex items-center gap-2 px-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              <span className="flex-1 min-w-0">Product Catalog</span>
              <span className="w-20 shrink-0 text-center">Qty</span>
              <span className="w-24 shrink-0 text-center">Unit Price</span>
              <span className="w-20 shrink-0 text-center">Disc %</span>
              <span className="w-24 shrink-0 text-right">Line Total</span>
              {lineItems.length > 1 && <span className="w-6 shrink-0"></span>}
            </div>

            <div className="space-y-2">
              {lineItems.map((item, index) => {
                const prod = products.find((p) => p.id === item.productId);
                const availableStock = sourceLocationId
                  ? (prod?.locationStock?.[sourceLocationId] ?? 0)
                  : (prod?.currentStock ?? 0);
                const remainingStock = availableStock - (item.orderedQty || 0);
                const isOutOfStock = Boolean(prod && availableStock === 0);
                const isExceedingStock = Boolean(prod && availableStock > 0 && item.orderedQty > availableStock);
                const isReorderThresholdBreached = Boolean(
                  prod &&
                  availableStock > 0 &&
                  item.orderedQty <= availableStock &&
                  prod.reorderPoint > 0 &&
                  remainingStock <= prod.reorderPoint
                );

                const lineGross = (item.orderedQty || 0) * (item.unitPrice || 0);
                const discPct = Math.max(0, Math.min(100, item.discountPercent || 0));
                const lineDisc = (lineGross * discPct) / 100;
                const lineNet = Math.max(0, lineGross - lineDisc);

                return (
                  <div
                    key={index}
                    className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] space-y-1.5"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                      <div className="w-full sm:flex-1 sm:min-w-0">
                        <ProductSearchDropdown
                          products={products}
                          selectedProductId={item.productId}
                          onSelect={(p) => handleProductSelect(index, p.id)}
                          warehouseId={sourceLocationId}
                          formatCurrency={formatCurrency}
                        />
                      </div>

                      <div className="flex items-center gap-2 w-full sm:w-auto justify-between sm:justify-start">
                        <div className="w-20 shrink-0">
                          <input
                            type="number"
                            min="1"
                            placeholder="Qty"
                            value={item.orderedQty}
                            onChange={(e) =>
                              handleUpdateItem(index, {
                                orderedQty: parseInt(e.target.value, 10) || 1,
                              })
                            }
                            className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] px-2 py-1.5 text-xs text-slate-800 dark:text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-teal-600 text-center"
                          />
                        </div>

                        <div className="w-24 shrink-0">
                          <input
                            type="number"
                            step="0.01"
                            min="0"
                            placeholder="Price"
                            value={item.unitPrice}
                            onChange={(e) =>
                              handleUpdateItem(index, {
                                unitPrice: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] px-2 py-1.5 text-xs text-slate-800 dark:text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-teal-600 text-right"
                          />
                        </div>

                        <div className="w-16 sm:w-20 shrink-0">
                          <div className="relative">
                            <input
                              type="number"
                              min="0"
                              max="100"
                              step="0.5"
                              placeholder="0"
                              value={item.discountPercent !== undefined && item.discountPercent !== null && item.discountPercent > 0 ? item.discountPercent : ''}
                              onChange={(e) => {
                                const val = e.target.value === '' ? 0 : Math.min(100, Math.max(0, parseFloat(e.target.value) || 0));
                                handleUpdateItem(index, { discountPercent: val });
                              }}
                              className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] pl-2 pr-5 py-1.5 text-xs text-slate-800 dark:text-slate-200 font-mono focus:outline-none focus:ring-1 focus:ring-teal-600 text-center"
                            />
                            <span className="absolute right-1.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-400 pointer-events-none">%</span>
                          </div>
                        </div>

                        <div className="w-20 sm:w-24 shrink-0 text-right">
                          <div className="font-mono font-bold text-xs text-slate-800 dark:text-slate-200">
                            {formatCurrency(lineNet)}
                          </div>
                          {discPct > 0 && (
                            <div className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">
                              -{discPct}% (-{formatCurrency(lineDisc)})
                            </div>
                          )}
                        </div>

                        {lineItems.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveItem(index)}
                            className="p-1 shrink-0 rounded text-slate-400 hover:text-rose-500 transition-colors"
                            title="Remove Item"
                          >
                            <IconTrash2 className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Stock & Reorder Threshold Warning Logic */}
                    {isOutOfStock && (
                      <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs font-medium">
                        <IconAlertCircle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
                        <span>
                          Out of Stock: <strong>0 units available</strong> in {currentSourceLoc?.name || 'this warehouse'}. Fulfilling this order will be blocked until restocked.
                        </span>
                      </div>
                    )}
                    {isExceedingStock && (
                      <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs font-medium">
                        <IconAlertTriangle className="h-4 w-4 shrink-0 text-rose-600 dark:text-rose-400" />
                        <span>
                          Insufficient Stock: Order quantity ({item.orderedQty}) exceeds available warehouse stock ({availableStock} {prod?.unitOfMeasure}).
                        </span>
                      </div>
                    )}
                    {!isOutOfStock && !isExceedingStock && isReorderThresholdBreached && (
                      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/25 text-amber-700 dark:text-amber-400 text-[11px] font-medium">
                        <IconAlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
                        <span>
                          Warning: Sale will reduce warehouse stock to {Math.max(0, remainingStock)} {prod?.unitOfMeasure} (at or below reorder threshold of {prod?.reorderPoint} {prod?.unitOfMeasure})
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Total Valuation & Discount Breakdown */}
          <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
            {calculateTotalDiscount() > 0 && (
              <>
                <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>Gross Subtotal</span>
                  <span className="font-mono">{formatCurrency(calculateTotalGross())}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-emerald-600 dark:text-emerald-400">
                  <span>Total Trade Discount (Deducted Pre-GST)</span>
                  <span className="font-mono font-medium">-{formatCurrency(calculateTotalDiscount())}</span>
                </div>
              </>
            )}
            <div className="flex items-center justify-between text-sm pt-1 border-t border-dashed border-slate-200 dark:border-slate-800">
              <span className="font-semibold text-slate-700 dark:text-slate-300">
                Total Valuation {calculateTotalDiscount() > 0 ? '(Net Taxable Value)' : ''}
              </span>
              <span className="font-mono font-bold text-base text-slate-900 dark:text-white">
                {formatCurrency(calculateGrandTotal())}
              </span>
            </div>
            <p className="text-[10px] text-slate-400">
              * Note: Trade discount is deducted before GST calculation as per Section 15 of CGST Act. Applicable taxes are generated upon dispatch.
            </p>
          </div>

          {/* Warehouse Stock Shortage Alert Banner */}
          {stockShortages.length > 0 && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-700 dark:text-rose-400 text-xs">
              <IconAlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
              <div className="space-y-1 flex-1">
                <div className="font-bold text-rose-800 dark:text-rose-300">
                  Warehouse Stock Alert ({currentSourceLoc?.name || 'Selected Warehouse'}):
                </div>
                <div className="text-[11px] leading-relaxed">
                  {stockShortages.map((s) => (
                    <span key={s.sku} className="inline-block mr-2 font-mono">
                      • <strong>{s.sku}</strong> ({s.name}): {s.isZero ? '0 in stock' : `only ${s.availableStock} ${s.unit} available`} (ordered {s.orderedQty} {s.unit})
                    </span>
                  ))}
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400">
                  Creating this order records it as an unfulfilled order. Dispatch & Pick will be blocked until inventory is received or transferred to {currentSourceLoc?.name || 'this warehouse'}.
                </div>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="rounded-lg border border-slate-200 dark:border-slate-800 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-teal-700 hover:bg-teal-800 px-5 py-2 text-xs font-bold text-white shadow-subtle transition-colors"
            >
              Create Sales Order
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
