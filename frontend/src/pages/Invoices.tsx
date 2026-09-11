import React, { useState, useEffect } from 'react';
import {
  IconFileText,
  IconDownload,
  IconSearch,
  IconIndianRupee,
  IconLayers,
  IconAlertTriangle,
  IconCheck,
  IconPrinter,
  IconEye,
  IconTrash2,
  IconBuilding,
  IconRefreshCw,
} from '../components/icons';
import { useInventory } from '../context/InventoryContext';
import { Invoice, InvoiceStatus } from '../types/inventory';
import { api } from '../services/api';
import { PageMeta } from '../components/common/PageMeta';
import { StatCard } from '../components/common/StatCard';
import { Modal } from '../components/common/Modal';

export const Invoices: React.FC = () => {
  const { formatCurrency, currency } = useInventory();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [voidModalInvoice, setVoidModalInvoice] = useState<Invoice | null>(null);
  const [isVoiding, setIsVoiding] = useState(false);

  const fetchInvoices = async () => {
    setIsLoading(true);
    try {
      const data = await api.getInvoices({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        search: searchQuery || undefined,
      });
      if (Array.isArray(data)) {
        // Map backend snake_case to frontend camelCase
        const mapped: Invoice[] = data.map((inv: any) => ({
          id: inv.id,
          tenantId: inv.tenant_id,
          invoiceNumber: inv.invoice_number,
          salesOrderId: inv.sales_order_id,
          invoiceDate: inv.invoice_date,
          dueDate: inv.due_date,
          placeOfSupply: inv.place_of_supply,
          status: inv.status,
          sellerLegalName: inv.seller_legal_name,
          sellerGstin: inv.seller_gstin,
          sellerPan: inv.seller_pan,
          sellerAddress: inv.seller_address,
          sellerState: inv.seller_state,
          sellerStateCode: inv.seller_state_code,
          customerName: inv.customer_name,
          customerGstin: inv.customer_gstin,
          customerBillingAddress: inv.customer_billing_address,
          customerShippingAddress: inv.customer_shipping_address,
          customerState: inv.customer_state,
          customerStateCode: inv.customer_state_code,
          isInterState: inv.is_inter_state,
          totalTaxableValue: Number(inv.total_taxable_value || 0),
          totalCgst: Number(inv.total_cgst || 0),
          totalSgst: Number(inv.total_sgst || 0),
          totalIgst: Number(inv.total_igst || 0),
          roundOff: Number(inv.round_off || 0),
          grandTotal: Number(inv.grand_total || 0),
          grandTotalWords: inv.grand_total_words || '',
          pdfUrl: inv.pdf_url,
          items: (inv.items || []).map((it: any) => ({
            id: it.id,
            productId: it.product_id,
            itemDescription: it.item_description,
            hsnCode: it.hsn_code,
            quantity: Number(it.quantity || 0),
            unitOfMeasure: it.unit_of_measure || 'pcs',
            unitPrice: Number(it.unit_price || 0),
            discount: Number(it.discount || 0),
            taxableValue: Number(it.taxable_value || 0),
            gstRate: Number(it.gst_rate || 0),
            cgstRate: Number(it.cgst_rate || 0),
            cgstAmount: Number(it.cgst_amount || 0),
            sgstRate: Number(it.sgst_rate || 0),
            sgstAmount: Number(it.sgst_amount || 0),
            igstRate: Number(it.igst_rate || 0),
            igstAmount: Number(it.igst_amount || 0),
            total: Number(it.total || 0),
          })),
        }));
        setInvoices(mapped);
      }
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [statusFilter]);

  const [downloadingInvId, setDownloadingInvId] = useState<string | null>(null);

  const handleDownloadPdf = async (inv: Invoice) => {
    setDownloadingInvId(inv.id);
    try {
      await api.downloadInvoicePdf(inv.id, inv.invoiceNumber);
    } catch (err) {
      console.error('Failed to download invoice PDF:', err);
      // Fallback in case of network issue
      window.open(api.getInvoicePdfUrl(inv.id), '_blank');
    } finally {
      setDownloadingInvId(null);
    }
  };

  const handleConfirmVoid = async () => {
    if (!voidModalInvoice) return;
    setIsVoiding(true);
    try {
      await api.voidInvoice(voidModalInvoice.id);
      await fetchInvoices();
      setVoidModalInvoice(null);
    } catch (err) {
      console.error('Void invoice error:', err);
    } finally {
      setIsVoiding(false);
    }
  };

  // KPIs
  const totalTaxable = invoices.reduce((sum, inv) => sum + (inv.status !== 'void' ? inv.totalTaxableValue : 0), 0);
  const totalTaxCollected = invoices.reduce(
    (sum, inv) => sum + (inv.status !== 'void' ? inv.totalCgst + inv.totalSgst + inv.totalIgst : 0),
    0
  );
  const totalInvoiced = invoices.reduce((sum, inv) => sum + (inv.status !== 'void' ? inv.grandTotal : 0), 0);
  const voidCount = invoices.filter((i) => i.status === 'void').length;

  const filteredInvoices = invoices.filter((inv) => {
    const q = searchQuery.toLowerCase();
    return (
      inv.invoiceNumber.toLowerCase().includes(q) ||
      inv.customerName.toLowerCase().includes(q) ||
      (inv.customerGstin && inv.customerGstin.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      <PageMeta
        title="GST Tax Invoices & Billing | Invenza Enterprise Inventory"
        description="Indian GST-compliant tax invoicing engine. Auto-generated from Sales Order fulfillments with CGST, SGST, IGST tax breakdown and PDF generation."
        canonicalPath="/invoices"
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            GST Tax Invoices
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Sequential, unbroken tax invoices automatically generated upon Sales Order fulfillment with HSN & GST splits.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchInvoices}
          className="flex items-center gap-2 rounded-lg bg-white dark:bg-[#131924] border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors shadow-subtle self-start sm:self-auto"
        >
          <IconRefreshCw className={`h-3.5 w-3.5 text-teal-600 dark:text-teal-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Sync Invoices</span>
        </button>
      </div>

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Invoices Issued"
          value={invoices.filter((i) => i.status !== 'void').length}
          subtitle="Sequential unbroken register"
          icon={IconFileText}
          colorScheme="teal"
          badge="GST Compliant"
        />
        <StatCard
          title="Total Tax Collected"
          value={formatCurrency(totalTaxCollected)}
          subtitle="CGST + SGST + IGST"
          icon={IconIndianRupee}
          colorScheme="emerald"
        />
        <StatCard
          title="Taxable Turnover"
          value={formatCurrency(totalTaxable)}
          subtitle="Net goods value dispatched"
          icon={IconLayers}
          colorScheme="slate"
        />
        <StatCard
          title="Void Register"
          value={voidCount}
          subtitle="Preserved audit numbers"
          icon={IconAlertTriangle}
          colorScheme={voidCount > 0 ? 'amber' : 'slate'}
          badge={voidCount > 0 ? 'Audit Logged' : 'Zero Voids'}
        />
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] p-4 shadow-card">
        <div className="relative w-full sm:w-80">
          <IconSearch className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search by Invoice #, Customer, GSTIN..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#0B111A] pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-500"
          />
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1 self-start sm:self-auto text-xs font-semibold">
          {['all', 'issued', 'paid', 'void'].map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`rounded-lg px-3 py-1.5 capitalize transition-colors ${
                statusFilter === st
                  ? 'bg-teal-700 text-white font-bold shadow-subtle'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Invoices Table */}
      <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-card">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-600 dark:text-slate-300">
            <thead className="border-b border-slate-200 dark:border-slate-800 bg-[#F6F8FA] dark:bg-[#0B111A] text-[11px] font-mono uppercase tracking-wider text-slate-600 dark:text-slate-400">
              <tr>
                <th className="px-4 py-3 font-semibold">Invoice No</th>
                <th className="px-4 py-3 font-semibold">Date</th>
                <th className="px-4 py-3 font-semibold">Customer & GSTIN</th>
                <th className="px-4 py-3 font-semibold">Place of Supply</th>
                <th className="px-4 py-3 font-semibold text-right">Taxable Val</th>
                <th className="px-4 py-3 font-semibold text-right">GST Total</th>
                <th className="px-4 py-3 font-semibold text-right">Grand Total</th>
                <th className="px-4 py-3 font-semibold text-center">Status</th>
                <th className="px-4 py-3 font-semibold text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-sans">
              {filteredInvoices.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <IconFileText className="mx-auto h-8 w-8 text-slate-300 dark:text-slate-600 mb-2" />
                    <p className="font-semibold text-sm text-slate-600 dark:text-slate-300">
                      No Tax Invoices Found
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Invoices are automatically generated when Sales Orders are fulfilled.
                    </p>
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => (
                  <tr
                    key={inv.id}
                    className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors ${
                      inv.status === 'void' ? 'opacity-60 bg-rose-500/5' : ''
                    }`}
                  >
                    <td className="px-4 py-3.5 font-mono font-bold text-teal-700 dark:text-teal-400">
                      {inv.invoiceNumber}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-500">
                      {inv.invoiceDate ? inv.invoiceDate.split('T')[0] : 'N/A'}
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-slate-900 dark:text-white">
                        {inv.customerName}
                      </div>
                      <div className="text-[10px] font-mono text-slate-400">
                        {inv.customerGstin || 'B2C / Unregistered'}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 font-mono">
                      <span className="text-[11px] font-semibold text-slate-800 dark:text-slate-200">
                        {inv.placeOfSupply}
                      </span>
                      <div className="text-[10px] text-slate-400">
                        {inv.isInterState ? 'Inter-State (IGST)' : 'Intra-State (CGST+SGST)'}
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono font-medium">
                      {formatCurrency(inv.totalTaxableValue)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono font-medium text-emerald-700 dark:text-emerald-400">
                      {formatCurrency(inv.totalCgst + inv.totalSgst + inv.totalIgst)}
                    </td>
                    <td className="px-4 py-3.5 text-right font-mono font-bold text-slate-900 dark:text-white">
                      {formatCurrency(inv.grandTotal)}
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider border ${
                          inv.status === 'issued'
                            ? 'bg-teal-50 text-teal-800 border-teal-200 dark:bg-teal-500/15 dark:text-teal-300 dark:border-transparent'
                            : inv.status === 'paid'
                            ? 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-transparent'
                            : 'bg-rose-50 text-rose-800 border-rose-200 dark:bg-rose-500/15 dark:text-rose-300 dark:border-transparent line-through'
                        }`}
                      >
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <div className="flex items-center justify-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleDownloadPdf(inv)}
                          disabled={downloadingInvId === inv.id}
                          className="flex items-center gap-1 rounded border border-teal-600/30 bg-teal-500/10 hover:bg-teal-500/20 px-2 py-1 text-[11px] font-semibold text-teal-700 dark:text-teal-300 transition-colors"
                          title="Download Tax Invoice PDF"
                        >
                          <IconDownload className="h-3 w-3" />
                          <span>{downloadingInvId === inv.id ? '...' : 'PDF'}</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => setSelectedInvoice(inv)}
                          className="p-1 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                          title="View Invoice Details"
                        >
                          <IconEye className="h-3.5 w-3.5" />
                        </button>

                        {inv.status !== 'void' && (
                          <button
                            type="button"
                            onClick={() => setVoidModalInvoice(inv)}
                            className="p-1 rounded text-rose-400 hover:text-rose-600"
                            title="Void Invoice"
                          >
                            <IconTrash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Invoice Detail Modal */}
      {selectedInvoice && (
        <Modal
          isOpen={!!selectedInvoice}
          onClose={() => setSelectedInvoice(null)}
          title={`Tax Invoice ${selectedInvoice.invoiceNumber}`}
          maxWidth="xl"
        >
          <div className="space-y-5 text-xs text-slate-700 dark:text-slate-300">
            {/* Header info */}
            <div className="grid grid-cols-2 gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
              <div>
                <div className="font-bold text-sm text-slate-900 dark:text-white">
                  {selectedInvoice.sellerLegalName}
                </div>
                <div className="text-slate-500 mt-0.5">{selectedInvoice.sellerAddress}</div>
                <div className="font-mono text-slate-400 mt-1">
                  GSTIN: {selectedInvoice.sellerGstin} | PAN: {selectedInvoice.sellerPan}
                </div>
              </div>
              <div className="text-right">
                <div className="font-mono font-bold text-teal-600 dark:text-teal-400 text-sm">
                  {selectedInvoice.invoiceNumber}
                </div>
                <div className="text-slate-500 mt-0.5">
                  Date: {selectedInvoice.invoiceDate ? selectedInvoice.invoiceDate.split('T')[0] : 'N/A'}
                </div>
                <div className="font-mono text-slate-400 mt-1">
                  Place of Supply: {selectedInvoice.placeOfSupply}
                </div>
              </div>
            </div>

            {/* Bill To / Ship To */}
            <div className="grid grid-cols-2 gap-4 rounded-lg bg-slate-50 dark:bg-[#0B111A] p-3 border border-slate-200 dark:border-slate-800">
              <div>
                <div className="font-mono font-bold text-[10px] uppercase text-teal-600 tracking-wider">
                  Bill To
                </div>
                <div className="font-semibold text-slate-900 dark:text-white mt-1">
                  {selectedInvoice.customerName}
                </div>
                <div className="text-slate-500 mt-0.5">{selectedInvoice.customerBillingAddress}</div>
                <div className="font-mono text-slate-400 mt-0.5">
                  GSTIN: {selectedInvoice.customerGstin || 'Unregistered'}
                </div>
              </div>
              <div>
                <div className="font-mono font-bold text-[10px] uppercase text-teal-600 tracking-wider">
                  Ship To
                </div>
                <div className="font-semibold text-slate-900 dark:text-white mt-1">
                  {selectedInvoice.customerName}
                </div>
                <div className="text-slate-500 mt-0.5">{selectedInvoice.customerShippingAddress}</div>
                <div className="font-mono text-slate-400 mt-0.5">
                  Tax Regime: {selectedInvoice.isInterState ? 'Inter-State (IGST)' : 'Intra-State (CGST + SGST)'}
                </div>
              </div>
            </div>

            {/* Line Items */}
            <div>
              <div className="font-bold text-slate-900 dark:text-white mb-2">Line Items</div>
              <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left font-sans">
                  <thead className="bg-slate-100 dark:bg-slate-800 font-mono text-[10px] uppercase text-slate-400">
                    <tr>
                      <th className="px-3 py-2">Item</th>
                      <th className="px-3 py-2">HSN</th>
                      <th className="px-3 py-2 text-right">Qty</th>
                      <th className="px-3 py-2 text-right">Rate</th>
                      <th className="px-3 py-2 text-right">Taxable</th>
                      {selectedInvoice.isInterState ? (
                        <th className="px-3 py-2 text-right">IGST</th>
                      ) : (
                        <>
                          <th className="px-3 py-2 text-right">CGST</th>
                          <th className="px-3 py-2 text-right">SGST</th>
                        </>
                      )}
                      <th className="px-3 py-2 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-[11px]">
                    {selectedInvoice.items.map((it, idx) => (
                      <tr key={idx}>
                        <td className="px-3 py-2 font-medium">{it.itemDescription}</td>
                        <td className="px-3 py-2 font-mono text-slate-400">{it.hsnCode}</td>
                        <td className="px-3 py-2 text-right font-mono">{it.quantity}</td>
                        <td className="px-3 py-2 text-right font-mono">{formatCurrency(it.unitPrice)}</td>
                        <td className="px-3 py-2 text-right font-mono">{formatCurrency(it.taxableValue)}</td>
                        {selectedInvoice.isInterState ? (
                          <td className="px-3 py-2 text-right font-mono text-teal-600">
                            {formatCurrency(it.igstAmount)} ({it.igstRate}%)
                          </td>
                        ) : (
                          <>
                            <td className="px-3 py-2 text-right font-mono text-teal-600">
                              {formatCurrency(it.cgstAmount)} ({it.cgstRate}%)
                            </td>
                            <td className="px-3 py-2 text-right font-mono text-teal-600">
                              {formatCurrency(it.sgstAmount)} ({it.sgstRate}%)
                            </td>
                          </>
                        )}
                        <td className="px-3 py-2 text-right font-mono font-bold text-slate-900 dark:text-white">
                          {formatCurrency(it.total)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Totals & Number to Words */}
            <div className="flex flex-col sm:flex-row justify-between items-start gap-4 border-t border-slate-200 dark:border-slate-800 pt-3">
              <div className="text-slate-500 max-w-sm">
                <div className="text-[10px] font-mono uppercase text-slate-400">Total in Words:</div>
                <div className="font-semibold text-slate-900 dark:text-white text-xs mt-0.5">
                  {selectedInvoice.grandTotalWords}
                </div>
              </div>
              <div className="text-right space-y-1 font-mono text-xs">
                <div className="flex justify-between gap-8 text-slate-500">
                  <span>Taxable Subtotal:</span>
                  <span>{formatCurrency(selectedInvoice.totalTaxableValue)}</span>
                </div>
                {selectedInvoice.isInterState ? (
                  <div className="flex justify-between gap-8 text-teal-600">
                    <span>Total IGST:</span>
                    <span>{formatCurrency(selectedInvoice.totalIgst)}</span>
                  </div>
                ) : (
                  <>
                    <div className="flex justify-between gap-8 text-teal-600">
                      <span>Total CGST:</span>
                      <span>{formatCurrency(selectedInvoice.totalCgst)}</span>
                    </div>
                    <div className="flex justify-between gap-8 text-teal-600">
                      <span>Total SGST:</span>
                      <span>{formatCurrency(selectedInvoice.totalSgst)}</span>
                    </div>
                  </>
                )}
                {selectedInvoice.roundOff !== 0 && (
                  <div className="flex justify-between gap-8 text-slate-500">
                    <span>Round Off:</span>
                    <span>{selectedInvoice.roundOff > 0 ? `+${selectedInvoice.roundOff}` : selectedInvoice.roundOff}</span>
                  </div>
                )}
                <div className="flex justify-between gap-8 border-t border-slate-200 dark:border-slate-800 pt-1 font-bold text-sm text-slate-900 dark:text-white">
                  <span>Grand Total:</span>
                  <span className="text-teal-600 dark:text-teal-400">{formatCurrency(selectedInvoice.grandTotal)}</span>
                </div>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="flex justify-end gap-2 border-t border-slate-200 dark:border-slate-800 pt-3">
              <button
                type="button"
                onClick={() => setSelectedInvoice(null)}
                className="rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => handleDownloadPdf(selectedInvoice)}
                className="flex items-center gap-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 px-3 py-1.5 text-xs font-bold text-white shadow-subtle"
              >
                <IconDownload className="h-3.5 w-3.5" />
                <span>Download PDF</span>
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Void Invoice Confirmation Modal */}
      {voidModalInvoice && (
        <Modal
          isOpen={!!voidModalInvoice}
          onClose={() => setVoidModalInvoice(null)}
          title="Void Tax Invoice"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs text-slate-600 dark:text-slate-300">
            <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 text-rose-800 dark:text-rose-200">
              <p className="font-bold">Are you sure you want to void this invoice?</p>
              <p className="mt-1 font-mono text-[11px]">
                Invoice #{voidModalInvoice.invoiceNumber}
              </p>
            </div>

            <p>
              Per Indian GST regulations, voided invoices permanently retain their sequential number to prevent gaps in the audit register. The regenerated PDF will clearly display a prominent <b>VOID INVOICE</b> watermark.
            </p>

            <div className="flex justify-end gap-2 border-t border-slate-200 dark:border-slate-800 pt-3">
              <button
                type="button"
                onClick={() => setVoidModalInvoice(null)}
                className="rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isVoiding}
                onClick={handleConfirmVoid}
                className="rounded-lg bg-rose-600 hover:bg-rose-700 px-3 py-1.5 text-xs font-bold text-white shadow-subtle"
              >
                {isVoiding ? 'Voiding...' : 'Confirm Void'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
