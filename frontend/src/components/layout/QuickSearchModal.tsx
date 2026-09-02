import React, { useState, useEffect } from 'react';
import { Modal } from '../common/Modal';
import { Search, Package, FileDown, FileUp, ArrowRight } from 'lucide-react';
import { useInventory } from '../../context/InventoryContext';
import { TabType } from './Sidebar';

interface QuickSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: TabType) => void;
}

export const QuickSearchModal: React.FC<QuickSearchModalProps> = ({
  isOpen,
  onClose,
  onNavigate,
}) => {
  const { products, purchaseOrders, salesOrders, formatCurrency } = useInventory();
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (isOpen) {
      setQuery('');
    }
  }, [isOpen]);

  const q = query.toLowerCase().trim();

  const filteredProducts = q
    ? products.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.sku.toLowerCase().includes(q) ||
          p.barcode?.includes(q) ||
          p.category.toLowerCase().includes(q)
      )
    : products.slice(0, 4);

  const filteredPOs = q
    ? purchaseOrders.filter(
        (p) =>
          p.poNumber.toLowerCase().includes(q) ||
          p.supplierName.toLowerCase().includes(q)
      )
    : purchaseOrders.slice(0, 2);

  const filteredSOs = q
    ? salesOrders.filter(
        (s) =>
          s.soNumber.toLowerCase().includes(q) ||
          s.customerName.toLowerCase().includes(q)
      )
    : salesOrders.slice(0, 2);

  const handleSelect = (tab: TabType) => {
    onNavigate(tab);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Quick Command Palette" maxWidth="xl">
      <div className="space-y-4">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type SKU, product title, PO number, or customer..."
            className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/90 pl-10 pr-4 py-3 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto space-y-4 pr-1">
          {/* Products Group */}
          <div>
            <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-2">
              <Package className="h-3 w-3" /> Products ({filteredProducts.length})
            </div>
            <div className="space-y-1">
              {filteredProducts.map((p) => (
                <div
                  key={p.id}
                  onClick={() => handleSelect('products')}
                  className="flex items-center justify-between rounded-xl p-2.5 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 font-mono text-xs font-bold">
                      SKU
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200 group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                        {p.name}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        {p.sku} • Stock: {p.currentStock} {p.unitOfMeasure}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      {formatCurrency(p.sellPrice)}
                    </span>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* POs Group */}
          {filteredPOs.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-2">
                <FileDown className="h-3 w-3" /> Purchase Orders
              </div>
              <div className="space-y-1">
                {filteredPOs.map((po) => (
                  <div
                    key={po.id}
                    onClick={() => handleSelect('purchase_orders')}
                    className="flex items-center justify-between rounded-xl p-2.5 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors group"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        {po.poNumber} — {po.supplierName}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Status: <span className="capitalize">{po.status}</span> • {formatCurrency(po.totalAmount)}
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SOs Group */}
          {filteredSOs.length > 0 && (
            <div>
              <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-2">
                <FileUp className="h-3 w-3" /> Sales Orders
              </div>
              <div className="space-y-1">
                {filteredSOs.map((so) => (
                  <div
                    key={so.id}
                    onClick={() => handleSelect('sales_orders')}
                    className="flex items-center justify-between rounded-xl p-2.5 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer transition-colors group"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        {so.soNumber} — {so.customerName}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        Status: <span className="capitalize">{so.status}</span> • {formatCurrency(so.totalAmount)}
                      </div>
                    </div>
                    <ArrowRight className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};
