import React, { useRef } from 'react';
import { Modal } from './Modal';
import { Product } from '../../types/inventory';
import { Printer, Copy, Check } from 'lucide-react';
import { useInventory } from '../../context/InventoryContext';

interface BarcodeLabelModalProps {
  product: Product | null;
  isOpen: boolean;
  onClose: () => void;
}

export const BarcodeLabelModal: React.FC<BarcodeLabelModalProps> = ({
  product,
  isOpen,
  onClose,
}) => {
  const { formatCurrency } = useInventory();
  const [copied, setCopied] = React.useState(false);
  const printAreaRef = useRef<HTMLDivElement>(null);

  if (!product) return null;

  const handlePrint = () => {
    window.print();
  };

  const handleCopyBarcode = () => {
    navigator.clipboard.writeText(product.barcode || product.sku);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Generate SVG Code128 pattern simulation based on digits/characters
  const generateBarcodeBars = (code: string) => {
    const bars: boolean[] = [];
    const seed = code.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    for (let i = 0; i < 65; i++) {
      bars.push(((seed * (i + 1) * 31) % 7) > 2);
    }
    return bars;
  };

  const bars = generateBarcodeBars(product.barcode || product.sku);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Barcode Label Generator"
      subtitle={`Print warehouse shelf & asset tags for ${product.sku}`}
      maxWidth="md"
    >
      <div className="space-y-6">
        {/* Printable Label Card Preview */}
        <div
          ref={printAreaRef}
          className="mx-auto w-full max-w-xs rounded-xl border-2 border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800/90 p-5 text-center shadow-lg"
        >
          <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700 pb-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
            <span>INVENZA ASSET TAG</span>
            <span>{product.unitOfMeasure.toUpperCase()}</span>
          </div>

          <div className="my-3 text-left">
            <h4 className="font-bold text-slate-900 dark:text-white line-clamp-1">{product.name}</h4>
            <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mt-1">
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">{product.sku}</span>
              <span className="font-bold text-slate-800 dark:text-slate-200">{formatCurrency(product.sellPrice)}</span>
            </div>
          </div>

          {/* SVG Barcode Bars */}
          <div className="flex h-16 items-center justify-center gap-[2px] bg-white p-2 rounded border border-slate-200 dark:border-slate-600">
            {bars.map((isBar, idx) => (
              <div
                key={idx}
                className={`h-full ${isBar ? 'w-[3px] bg-black' : 'w-[2px] bg-transparent'}`}
              />
            ))}
          </div>

          {/* Numeric barcode string */}
          <div className="mt-2 font-mono text-xs tracking-widest text-slate-700 dark:text-slate-300 font-semibold">
            {product.barcode || 'NO-BARCODE-DEFINED'}
          </div>

          {/* Batch / Storage Zone if present */}
          {(product.customFields?.batchNumber || product.customFields?.storageZone) && (
            <div className="mt-3 flex items-center justify-between border-t border-slate-200 dark:border-slate-700 pt-2 text-[10px] text-slate-400">
              <span>Lot: {product.customFields.batchNumber || 'N/A'}</span>
              <span>Zone: {product.customFields.storageZone || 'Standard'}</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center justify-between gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
          <button
            type="button"
            onClick={handleCopyBarcode}
            className="flex items-center gap-2 rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2.5 text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied Barcode' : 'Copy Barcode'}
          </button>

          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/25 transition-all"
          >
            <Printer className="h-4 w-4" />
            Print Label
          </button>
        </div>
      </div>
    </Modal>
  );
};
