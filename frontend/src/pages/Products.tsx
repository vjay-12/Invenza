import React, { useState, useRef } from 'react';
import {
  Package,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  Barcode,
  SlidersHorizontal,
  Trash2,
  Edit2,
  CheckSquare,
  Square,
  AlertCircle,
  Tag,
  Check,
  X,
  FileDown,
  FileSpreadsheet,
  Info,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { Product, AdjustmentReasonCode } from '../types/inventory';
import { Modal } from '../components/common/Modal';
import { BarcodeLabelModal } from '../components/common/BarcodeLabelModal';

export const Products: React.FC = () => {
  const {
    products,
    locations,
    customFields,
    currency,
    formatCurrency,
    selectedLocationId,
    addProduct,
    bulkAddProducts,
    updateProduct,
    deleteProduct,
    createAdjustment,
    bulkAdjustStock,
  } = useInventory();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [stockStatusFilter, setStockStatusFilter] = useState<'all' | 'low' | 'in_stock'>('all');

  // Selection for bulk actions
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isBulkAdjustModalOpen, setIsBulkAdjustModalOpen] = useState(false);
  const [barcodeProduct, setBarcodeProduct] = useState<Product | null>(null);

  // CSV Import State
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [parsedProducts, setParsedProducts] = useState<any[]>([]);
  const [isImporting, setIsImporting] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [importToast, setImportToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // New Product Form State
  const [newSku, setNewSku] = useState('');
  const [newName, setNewName] = useState('');
  const [newCategory, setNewCategory] = useState('Electronics');
  const [newUom, setNewUom] = useState('pcs');
  const [newCostPrice, setNewCostPrice] = useState('25.00');
  const [newSellPrice, setNewSellPrice] = useState('60.00');
  const [newBarcode, setNewBarcode] = useState('');
  const [newReorderPoint, setNewReorderPoint] = useState('15');
  const [newVariantKey, setNewVariantKey] = useState('Color');
  const [newVariantValue, setNewVariantValue] = useState('');
  const [newCustomFieldsData, setNewCustomFieldsData] = useState<Record<string, any>>({});

  // Bulk Adjustment Form State
  const [bulkDelta, setBulkDelta] = useState<number>(0);
  const [bulkLocationId, setBulkLocationId] = useState<string>(locations[0]?.id || '');
  const [bulkReason, setBulkReason] = useState<AdjustmentReasonCode>('audit');
  const [bulkNotes, setBulkNotes] = useState('');

  // Categories list
  const categories = ['all', ...Array.from(new Set(products.map((p) => p.category)))];

  // Filtering
  const filteredProducts = products.filter((p) => {
    const q = searchQuery.toLowerCase().trim();
    const matchesQuery =
      !q ||
      p.name.toLowerCase().includes(q) ||
      p.sku.toLowerCase().includes(q) ||
      p.barcode?.includes(q);

    const matchesCategory = selectedCategory === 'all' || p.category === selectedCategory;

    const currentQty =
      selectedLocationId === 'all'
        ? p.currentStock
        : p.locationStock[selectedLocationId] || 0;

    let matchesStock = true;
    if (stockStatusFilter === 'low') {
      matchesStock = currentQty <= p.reorderPoint;
    } else if (stockStatusFilter === 'in_stock') {
      matchesStock = currentQty > p.reorderPoint;
    }

    return matchesQuery && matchesCategory && matchesStock;
  });

  // Handle Select All
  const handleSelectAll = () => {
    if (selectedProductIds.length === filteredProducts.length) {
      setSelectedProductIds([]);
    } else {
      setSelectedProductIds(filteredProducts.map((p) => p.id));
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  // Create Product Submit
  const handleCreateProduct = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSku || !newName) return;

    const variantAttrs: Record<string, string> = {};
    if (newVariantKey && newVariantValue) {
      variantAttrs[newVariantKey] = newVariantValue;
    }

    addProduct({
      sku: newSku.toUpperCase().trim(),
      name: newName.trim(),
      category: newCategory,
      unitOfMeasure: newUom,
      costPrice: parseFloat(newCostPrice) || 0,
      sellPrice: parseFloat(newSellPrice) || 0,
      barcode: newBarcode.trim() || `890${Math.floor(100000000 + Math.random() * 900000000)}`,
      reorderPoint: parseFloat(newReorderPoint) || 10,
      variantAttributes: variantAttrs,
      customFields: newCustomFieldsData,
    });

    setIsAddModalOpen(false);
    // Reset
    setNewSku('');
    setNewName('');
    setNewBarcode('');
    setNewVariantValue('');
    setNewCustomFieldsData({});
  };

  // Bulk Adjust Submit
  const handleBulkAdjustSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (bulkDelta === 0 || !bulkLocationId || selectedProductIds.length === 0) return;

    const adjustmentsList = selectedProductIds.map((pId) => ({
      productId: pId,
      locationId: bulkLocationId,
      delta: bulkDelta,
      reasonCode: bulkReason,
      notes: bulkNotes || 'Bulk stock update applied across selected SKUs',
    }));

    bulkAdjustStock(adjustmentsList);
    setIsBulkAdjustModalOpen(false);
    setSelectedProductIds([]);
    setBulkDelta(0);
    setBulkNotes('');
  };

  // Export CSV
  const handleExportCSV = () => {
    const itemsToExport =
      selectedProductIds.length > 0
        ? products.filter((p) => selectedProductIds.includes(p.id))
        : filteredProducts;

    const headers = ['SKU', 'Name', 'Category', 'Unit', 'Cost', 'SellPrice', 'Barcode', 'CurrentStock'];
    const rows = itemsToExport.map((p) => [
      p.sku,
      `"${p.name.replace(/"/g, '""')}"`,
      p.category,
      p.unitOfMeasure,
      p.costPrice,
      p.sellPrice,
      p.barcode,
      p.currentStock,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `invenza_skus_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Download CSV Template with required columns first
  const handleDownloadTemplate = () => {
    const csvContent = [
      'sku,name,category,unit_of_measure,cost_price,sell_price,reorder_point,barcode,variant_attribute',
      'SKU-KB-101,"Logitech MX Keys Wireless",Electronics,pcs,75.00,119.00,15,761198450123,Graphite',
      'SKU-CH-202,"Ergonomic Mesh Office Chair",Furniture,pcs,120.00,249.00,8,890142859012,Black',
      'SKU-CB-303,"Braided USB-C Cable 2M",Accessories,pcs,4.50,14.99,50,890582910394,Silver',
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'invenza_sku_import_template.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Robust CSV Parser
  const parseCSVText = (text: string) => {
    const lines = text.split(/\r\n|\n/).map((l) => l.trim()).filter(Boolean);
    if (lines.length < 2) return [];

    const parseRow = (line: string): string[] => {
      const result: string[] = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          if (inQuotes && line[i + 1] === '"') {
            current += '"';
            i++;
          } else {
            inQuotes = !inQuotes;
          }
        } else if (char === ',' && !inQuotes) {
          result.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      result.push(current.trim());
      return result;
    };

    const headers = parseRow(lines[0]).map((h) =>
      h.toLowerCase().replace(/[\s_-]+/g, '')
    );

    const skuIdx = headers.findIndex((h) =>
      ['sku', 'skucode', 'itemcode', 'code'].includes(h)
    );
    const nameIdx = headers.findIndex((h) =>
      ['name', 'productname', 'title', 'itemname', 'product'].includes(h)
    );
    const catIdx = headers.findIndex((h) =>
      ['category', 'cat', 'department', 'dept'].includes(h)
    );
    const uomIdx = headers.findIndex((h) =>
      ['unitofmeasure', 'uom', 'unit'].includes(h)
    );
    const costIdx = headers.findIndex((h) =>
      ['costprice', 'cost', 'buyprice', 'unitcost'].includes(h)
    );
    const sellIdx = headers.findIndex((h) =>
      ['sellprice', 'price', 'saleprice', 'sellingprice'].includes(h)
    );
    const reorderIdx = headers.findIndex((h) =>
      ['reorderpoint', 'reorder', 'minstock'].includes(h)
    );
    const barcodeIdx = headers.findIndex((h) =>
      ['barcode', 'upc', 'ean'].includes(h)
    );
    const variantIdx = headers.findIndex((h) =>
      ['variantattribute', 'variant', 'color', 'size', 'attributes'].includes(h)
    );

    const parsed: any[] = [];
    for (let i = 1; i < lines.length; i++) {
      const cols = parseRow(lines[i]);
      if (cols.length === 0 || (cols.length === 1 && !cols[0])) continue;

      const sku =
        skuIdx !== -1 && cols[skuIdx] ? cols[skuIdx].toUpperCase().trim() : '';
      const name =
        nameIdx !== -1 && cols[nameIdx] ? cols[nameIdx].trim() : '';
      const category =
        catIdx !== -1 && cols[catIdx] ? cols[catIdx].trim() : 'General';
      const uom = uomIdx !== -1 && cols[uomIdx] ? cols[uomIdx].trim() : 'pcs';
      const cost =
        costIdx !== -1 && cols[costIdx]
          ? parseFloat(cols[costIdx].replace(/[^0-9.]/g, '')) || 0
          : 0;
      const sell =
        sellIdx !== -1 && cols[sellIdx]
          ? parseFloat(cols[sellIdx].replace(/[^0-9.]/g, '')) || 0
          : 0;
      const reorder =
        reorderIdx !== -1 && cols[reorderIdx]
          ? parseFloat(cols[reorderIdx].replace(/[^0-9.]/g, '')) || 10
          : 10;
      const barcode =
        barcodeIdx !== -1 && cols[barcodeIdx]
          ? cols[barcodeIdx].trim()
          : `890${Math.floor(100000000 + Math.random() * 900000000)}`;
      const variant =
        variantIdx !== -1 && cols[variantIdx] ? cols[variantIdx].trim() : '';

      parsed.push({
        rawLine: i + 1,
        sku,
        name,
        category,
        unitOfMeasure: uom,
        costPrice: cost,
        sellPrice: sell,
        reorderPoint: reorder,
        barcode,
        variantAttributes: variant ? { Variant: variant } : {},
        customFields: {},
        isValid: Boolean(sku && name),
      });
    }
    return parsed;
  };

  const handleFileSelect = (file: File) => {
    if (!file || !file.name.toLowerCase().endsWith('.csv')) {
      alert('Please upload a valid .csv file format.');
      return;
    }
    setImportFile(file);
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (text) {
        const parsed = parseCSVText(text);
        setParsedProducts(parsed);
      }
    };
    reader.readAsText(file);
  };

  const validParsedProducts = parsedProducts.filter((p) => p.isValid);
  const invalidParsedProducts = parsedProducts.filter((p) => !p.isValid);

  const handleConfirmImport = async () => {
    if (!validParsedProducts.length) return;
    setIsImporting(true);

    try {
      const itemsToImport = validParsedProducts.map((p) => ({
        sku: p.sku,
        name: p.name,
        category: p.category,
        unitOfMeasure: p.unitOfMeasure,
        costPrice: p.costPrice,
        sellPrice: p.sellPrice,
        barcode: p.barcode,
        reorderPoint: p.reorderPoint,
        variantAttributes: p.variantAttributes,
        customFields: p.customFields,
      }));

      const count = await bulkAddProducts(itemsToImport);
      setImportToast({
        type: 'success',
        message: `Successfully imported ${count} SKUs into catalog!`,
      });
      setIsImportModalOpen(false);
      setImportFile(null);
      setParsedProducts([]);

      setTimeout(() => setImportToast(null), 5000);
    } catch (err: any) {
      setImportToast({
        type: 'error',
        message: err.message || 'Failed to import CSV products.',
      });
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast notification banner */}
      {importToast && (
        <div
          className={`flex items-center justify-between p-3.5 rounded-2xl border text-xs font-semibold animate-in fade-in slide-in-from-top-2 duration-200 ${
            importToast.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
          }`}
        >
          <div className="flex items-center gap-2">
            {importToast.type === 'success' ? (
              <Check className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{importToast.message}</span>
          </div>
          <button
            onClick={() => setImportToast(null)}
            className="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Product & SKU Catalog
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5 truncate">
            Master SKU catalog with JSONB custom fields, variant tags, and barcode printing
          </p>
        </div>

        {/* Action Buttons Toolbar (Always single row, no wrapping) */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Download CSV Template Button */}
          <button
            type="button"
            onClick={handleDownloadTemplate}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 transition-colors shadow-sm whitespace-nowrap"
            title="Download CSV template with required columns at start"
          >
            <FileDown className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
            <span>Template</span>
          </button>

          {/* Import CSV Button */}
          <button
            type="button"
            onClick={() => {
              setImportFile(null);
              setParsedProducts([]);
              setIsImportModalOpen(true);
            }}
            className="flex items-center gap-1.5 rounded-xl border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/50 dark:bg-indigo-950/40 hover:bg-indigo-100/60 dark:hover:bg-indigo-900/40 px-3 py-2 text-xs font-semibold text-indigo-600 dark:text-indigo-400 transition-colors shadow-sm whitespace-nowrap"
            title="Import products from CSV file"
          >
            <Upload className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span>Import</span>
          </button>

          {/* Export CSV Button */}
          <button
            type="button"
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 transition-colors shadow-sm whitespace-nowrap"
            title="Export catalog products to CSV"
          >
            <Download className="h-4 w-4 text-slate-400" />
            <span>Export</span>
          </button>

          {/* Add New SKU Primary Button */}
          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-600 px-3.5 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/20 transition-all whitespace-nowrap"
          >
            <Plus className="h-4 w-4" />
            <span>Add SKU</span>
          </button>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-3 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-4 backdrop-blur-xl">
        <div className="flex items-center gap-3 w-full md:w-auto flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by SKU, name, or barcode..."
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 pl-9 pr-4 py-2 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="flex items-center gap-2.5 w-full md:w-auto justify-end overflow-x-auto">
          {/* Category Dropdown */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none"
          >
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat}
              </option>
            ))}
          </select>

          {/* Stock Health Toggle */}
          <div className="flex items-center rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-1 text-xs">
            <button
              onClick={() => setStockStatusFilter('all')}
              className={`rounded-lg px-2.5 py-1 font-medium transition-all ${
                stockStatusFilter === 'all'
                  ? 'bg-white dark:bg-slate-700 text-indigo-600 dark:text-indigo-400 shadow-sm font-bold'
                  : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setStockStatusFilter('low')}
              className={`rounded-lg px-2.5 py-1 font-medium transition-all ${
                stockStatusFilter === 'low'
                  ? 'bg-amber-500 text-white shadow-sm font-bold'
                  : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
              }`}
            >
              Low Stock
            </button>
          </div>
        </div>
      </div>

      {/* Bulk Action Sticky Bar (when items selected) */}
      {selectedProductIds.length > 0 && (
        <div className="flex items-center justify-between rounded-xl bg-indigo-900/90 text-white px-5 py-3 shadow-xl backdrop-blur-md animate-in fade-in slide-in-from-top-2 border border-indigo-700">
          <div className="flex items-center gap-3 text-xs font-semibold">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-indigo-900 font-bold">
              {selectedProductIds.length}
            </span>
            <span>SKUs selected for batch action</span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsBulkAdjustModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-semibold shadow-sm transition-colors"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Batch Adjust Stock
            </button>
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 rounded-lg bg-indigo-700 hover:bg-indigo-600 px-3 py-1.5 text-xs font-semibold transition-colors"
            >
              <Download className="h-3.5 w-3.5" />
              Export Selected
            </button>
            <button
              onClick={() => setSelectedProductIds([])}
              className="rounded-lg p-1.5 hover:bg-indigo-800 text-slate-300 hover:text-white transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* SKU Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 dark:text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4 w-10">
                  <button onClick={handleSelectAll} className="flex items-center">
                    {selectedProductIds.length === filteredProducts.length &&
                    filteredProducts.length > 0 ? (
                      <CheckSquare className="h-4 w-4 text-indigo-600" />
                    ) : (
                      <Square className="h-4 w-4 text-slate-400" />
                    )}
                  </button>
                </th>
                <th className="py-3 px-3">SKU & Barcode</th>
                <th className="py-3 px-3">Product Name & Category</th>
                <th className="py-3 px-3">Variants & Attributes</th>
                <th className="py-3 px-3 text-right">Available Stock</th>
                <th className="py-3 px-3 text-right">Cost / Sell Price</th>
                <th className="py-3 px-3 text-right">Margin %</th>
                <th className="py-3 px-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {filteredProducts.map((p) => {
                const isSelected = selectedProductIds.includes(p.id);
                const currentQty =
                  selectedLocationId === 'all'
                    ? p.currentStock
                    : p.locationStock[selectedLocationId] || 0;
                const isLow = currentQty <= p.reorderPoint;
                const margin =
                  p.sellPrice > 0
                    ? Math.round(((p.sellPrice - p.costPrice) / p.sellPrice) * 100)
                    : 0;

                return (
                  <tr
                    key={p.id}
                    className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors ${
                      isSelected ? 'bg-indigo-50/40 dark:bg-indigo-950/20' : ''
                    }`}
                  >
                    <td className="py-3 px-4">
                      <button
                        onClick={() => handleToggleSelect(p.id)}
                        className="flex items-center"
                      >
                        {isSelected ? (
                          <CheckSquare className="h-4 w-4 text-indigo-600" />
                        ) : (
                          <Square className="h-4 w-4 text-slate-400" />
                        )}
                      </button>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-mono font-bold text-indigo-600 dark:text-indigo-400">
                        {p.sku}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        {p.barcode || 'No barcode'}
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-800 dark:text-slate-200">
                        {p.name}
                      </div>
                      <span className="inline-block rounded-md bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {p.category}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {Object.entries(p.variantAttributes || {}).map(([k, v]) => (
                          <span
                            key={k}
                            className="rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 px-1.5 py-0.5 text-[10px] text-slate-600 dark:text-slate-300"
                          >
                            <span className="text-slate-400">{k}:</span> {String(v)}
                          </span>
                        ))}
                        {p.customFields?.batchNumber && (
                          <span className="rounded-md border border-purple-500/20 bg-purple-500/10 px-1.5 py-0.5 text-[10px] text-purple-600 dark:text-purple-400">
                            Lot: {String(p.customFields.batchNumber)}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-1.5 font-mono font-bold">
                        <span
                          className={
                            isLow
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-slate-800 dark:text-slate-200'
                          }
                        >
                          {currentQty} {p.unitOfMeasure}
                        </span>
                        {isLow && (
                          <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse" />
                        )}
                      </div>
                      <div className="text-[10px] text-slate-400">Min: {p.reorderPoint}</div>
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      <div className="font-semibold text-slate-800 dark:text-slate-200">
                        {formatCurrency(p.sellPrice)}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        Cost: {formatCurrency(p.costPrice)}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold">
                      <span
                        className={
                          margin > 40
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : margin > 20
                            ? 'text-slate-700 dark:text-slate-300'
                            : 'text-amber-600 dark:text-amber-400'
                        }
                      >
                        {margin}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          onClick={() => setBarcodeProduct(p)}
                          title="Print Barcode Label"
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-indigo-600 transition-colors"
                        >
                          <Barcode className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteProduct(p.id)}
                          title="Delete Product"
                          className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 hover:text-rose-600 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Product Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add New SKU to Master Catalog"
        subtitle="Registers new product item with immutable ledger hooks & custom schema fields"
        maxWidth="2xl"
      >
        <form onSubmit={handleCreateProduct} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                SKU Identifier *
              </label>
              <input
                type="text"
                required
                value={newSku}
                onChange={(e) => setNewSku(e.target.value)}
                placeholder="e.g. SKU-WIR-MOU-01"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono uppercase focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Product Title *
              </label>
              <input
                type="text"
                required
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Precision Wireless Mouse"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Category
              </label>
              <input
                type="text"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Unit of Measure (UOM)
              </label>
              <select
                value={newUom}
                onChange={(e) => setNewUom(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
              >
                <option value="pcs">Pieces (pcs)</option>
                <option value="box">Box (box)</option>
                <option value="kg">Kilogram (kg)</option>
                <option value="meters">Meters (m)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Barcode Value
              </label>
              <input
                type="text"
                value={newBarcode}
                onChange={(e) => setNewBarcode(e.target.value)}
                placeholder="Auto-generated if blank"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Cost Price ({currency})
              </label>
              <input
                type="number"
                step="0.01"
                value={newCostPrice}
                onChange={(e) => setNewCostPrice(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Sell Price ({currency})
              </label>
              <input
                type="number"
                step="0.01"
                value={newSellPrice}
                onChange={(e) => setNewSellPrice(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Safety Reorder Threshold
              </label>
              <input
                type="number"
                value={newReorderPoint}
                onChange={(e) => setNewReorderPoint(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Dynamic Custom Fields Section */}
          {customFields.length > 0 && (
            <div className="border-t border-slate-100 dark:border-slate-800 pt-3">
              <span className="text-[11px] font-bold tracking-wider text-slate-400 uppercase">
                Dynamic Custom Attributes (JSONB)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                {customFields.map((cf) => (
                  <div key={cf.id}>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                      {cf.name}
                    </label>
                    {cf.type === 'select' ? (
                      <select
                        value={newCustomFieldsData[cf.key] || ''}
                        onChange={(e) =>
                          setNewCustomFieldsData((prev) => ({
                            ...prev,
                            [cf.key]: e.target.value,
                          }))
                        }
                        className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
                      >
                        <option value="">Select option...</option>
                        {cf.options?.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type={cf.type === 'number' ? 'number' : cf.type === 'date' ? 'date' : 'text'}
                        value={newCustomFieldsData[cf.key] || ''}
                        onChange={(e) =>
                          setNewCustomFieldsData((prev) => ({
                            ...prev,
                            [cf.key]: e.target.value,
                          }))
                        }
                        className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsAddModalOpen(false)}
              className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Save Product SKU
            </button>
          </div>
        </form>
      </Modal>

      {/* Bulk Stock Adjustment Modal */}
      <Modal
        isOpen={isBulkAdjustModalOpen}
        onClose={() => setIsBulkAdjustModalOpen(false)}
        title="Batch Stock Adjustment"
        subtitle={`Adjust inventory balance across ${selectedProductIds.length} selected SKUs`}
        maxWidth="lg"
      >
        <form onSubmit={handleBulkAdjustSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Target Warehouse
            </label>
            <select
              value={bulkLocationId}
              onChange={(e) => setBulkLocationId(e.target.value)}
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs"
            >
              {locations.map((loc) => (
                <option key={loc.id} value={loc.id}>
                  {loc.code} — {loc.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Quantity Delta (+ or -)
              </label>
              <input
                type="number"
                required
                value={bulkDelta}
                onChange={(e) => setBulkDelta(parseInt(e.target.value, 10) || 0)}
                placeholder="e.g. +5 or -2"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono font-bold"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Mandatory Audit Reason Code *
              </label>
              <select
                value={bulkReason}
                onChange={(e) => setBulkReason(e.target.value as AdjustmentReasonCode)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-semibold uppercase"
              >
                <option value="audit">AUDIT (Periodic stock take count)</option>
                <option value="damage">DAMAGE (Defective/broken inventory)</option>
                <option value="loss">LOSS (Unaccounted shrinkage/theft)</option>
                <option value="miscount">MISCOUNT (Previous counting error)</option>
                <option value="return">RETURN (Customer RMA restock)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Audit Justification Notes *
            </label>
            <textarea
              required
              rows={2}
              value={bulkNotes}
              onChange={(e) => setBulkNotes(e.target.value)}
              placeholder="Provide reason for adjustment to satisfy audit compliance..."
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsBulkAdjustModalOpen(false)}
              className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Commit Batch Ledger Adjustments
            </button>
          </div>
        </form>
      </Modal>

      {/* CSV Import Modal */}
      <Modal
        isOpen={isImportModalOpen}
        onClose={() => {
          setIsImportModalOpen(false);
          setImportFile(null);
          setParsedProducts([]);
        }}
        title="Import Products & SKUs from CSV"
        subtitle="Batch upload product catalog records directly into your workspace"
        maxWidth="3xl"
      >
        <div className="space-y-4">
          {/* Helpful Template Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200/60 dark:border-indigo-900/50">
            <div className="flex items-start gap-2.5 min-w-0">
              <FileSpreadsheet className="h-5 w-5 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
              <div className="text-xs text-slate-700 dark:text-slate-300 min-w-0">
                <span className="font-bold text-indigo-700 dark:text-indigo-300">
                  Pre-formatted CSV Template
                </span>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  Required columns: <code className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">sku</code> and <code className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">name</code>. Optional: category, unit, cost, price, barcode.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleDownloadTemplate}
              className="flex items-center justify-center gap-1.5 shrink-0 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800 text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-slate-800 transition-colors shadow-sm"
            >
              <FileDown className="h-3.5 w-3.5" />
              <span>Download Template</span>
            </button>
          </div>

          {/* Upload Drag & Drop Area */}
          {!importFile ? (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOver(false);
                const file = e.dataTransfer.files?.[0];
                if (file) handleFileSelect(file);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
                isDragOver
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : 'border-slate-200 dark:border-slate-800 hover:border-indigo-400/50 bg-slate-50/50 dark:bg-slate-900/40'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
              />
              <div className="flex flex-col items-center justify-center gap-2.5">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                  <Upload className="h-6 w-6" />
                </div>
                <div>
                  <span className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    Click to browse or drag & drop CSV file
                  </span>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Standard comma-delimited spreadsheet (.csv)
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-3.5">
              {/* Loaded File Info Card */}
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
                    CSV
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                      {importFile.name}
                    </div>
                    <div className="text-[10px] text-slate-400">
                      {(importFile.size / 1024).toFixed(1)} KB &bull; {parsedProducts.length} total rows detected
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setImportFile(null);
                    setParsedProducts([]);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="px-2.5 py-1 rounded-lg text-xs font-semibold text-slate-500 hover:text-rose-500 hover:bg-rose-500/10 transition-colors shrink-0"
                >
                  Change File
                </button>
              </div>

              {/* Status Pills */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
                  <Check className="h-3.5 w-3.5" />
                  {validParsedProducts.length} Ready to Import
                </span>
                {invalidParsedProducts.length > 0 && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 text-xs font-bold">
                    <AlertCircle className="h-3.5 w-3.5" />
                    {invalidParsedProducts.length} Missing SKU/Name (Will be skipped)
                  </span>
                )}
              </div>

              {/* Preview Table */}
              <div className="max-h-60 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-800">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-slate-100 dark:bg-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    <tr>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">SKU</th>
                      <th className="px-3 py-2">Product Name</th>
                      <th className="px-3 py-2">Category</th>
                      <th className="px-3 py-2 text-right">Cost</th>
                      <th className="px-3 py-2 text-right">Sell Price</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 bg-white dark:bg-slate-900">
                    {parsedProducts.map((p, idx) => (
                      <tr key={idx} className={p.isValid ? '' : 'bg-rose-500/5'}>
                        <td className="px-3 py-2">
                          {p.isValid ? (
                            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400">Ready</span>
                          ) : (
                            <span className="text-[10px] font-bold text-rose-500">Missing SKU/Name</span>
                          )}
                        </td>
                        <td className="px-3 py-2 font-mono font-bold text-slate-800 dark:text-slate-200">
                          {p.sku || <em className="text-rose-400 font-sans font-normal">empty</em>}
                        </td>
                        <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300">
                          {p.name || <em className="text-rose-400 font-sans font-normal">empty</em>}
                        </td>
                        <td className="px-3 py-2 text-slate-500">{p.category}</td>
                        <td className="px-3 py-2 text-right font-mono text-slate-600 dark:text-slate-400">
                          {formatCurrency(p.costPrice)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono font-bold text-indigo-600 dark:text-indigo-400">
                          {formatCurrency(p.sellPrice)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Modal Footer Controls */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => {
                setIsImportModalOpen(false);
                setImportFile(null);
                setParsedProducts([]);
              }}
              className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>

            <button
              type="button"
              disabled={!validParsedProducts.length || isImporting}
              onClick={handleConfirmImport}
              className="flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-bold shadow-md shadow-indigo-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {isImporting ? (
                <>
                  <span className="h-3.5 w-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  <span>Importing...</span>
                </>
              ) : (
                <>
                  <Upload className="h-3.5 w-3.5" />
                  <span>Confirm & Import ({validParsedProducts.length} Products)</span>
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>

      {/* Barcode Label Modal */}
      <BarcodeLabelModal
        product={barcodeProduct}
        isOpen={Boolean(barcodeProduct)}
        onClose={() => setBarcodeProduct(null)}
      />
    </div>
  );
};
