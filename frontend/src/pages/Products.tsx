import React, { useState, useEffect, useRef, useMemo } from 'react';
import {
  IconPackage as Package,
  IconPlus as Plus,
  IconSearch as Search,
  IconFilter as Filter,
  IconDownload as Download,
  IconUpload as Upload,
  IconBarcode as Barcode,
  IconSlidersHorizontal as SlidersHorizontal,
  IconTrash2 as Trash2,
  IconEdit as Edit2,
  IconCheckSquare as CheckSquare,
  IconSquare as Square,
  IconAlertCircle as AlertCircle,
  IconTag as Tag,
  IconCheck as Check,
  IconX as X,
  IconFileDown as FileDown,
  IconFileSpreadsheet as FileSpreadsheet,
  IconInfo as Info,
  IconWarehouse as Warehouse,
  IconMoreVertical as MoreVertical,
  IconEye as Eye,
  IconCopy as Copy,
  IconPower as Power,
  IconChevronLeft as ChevronLeft,
  IconChevronRight as ChevronRight,
  IconChevronsLeft as ChevronsLeft,
  IconChevronsRight as ChevronsRight,
  IconArrowUpDown as ArrowUpDown,
} from '../components/icons';
import { useInventory } from '../context/InventoryContext';
import { Product, AdjustmentReasonCode, CurrencyCode } from '../types/inventory';
import { Modal } from '../components/common/Modal';
import { BarcodeLabelModal } from '../components/common/BarcodeLabelModal';
import { PageMeta } from '../components/common/PageMeta';
import { SortSelectDropdown, ProductSortKey } from '../components/common/SortSelectDropdown';
import { CategorySelectDropdown } from '../components/common/CategorySelectDropdown';
import { SimpleSelectDropdown, DropdownOption } from '../components/common/SimpleSelectDropdown';
import { WarehouseSelectDropdown } from '../components/common/WarehouseSelectDropdown';

const UOM_OPTIONS: DropdownOption[] = [
  { value: 'pcs', label: 'Pieces (pcs)' },
  { value: 'box', label: 'Box (box)' },
  { value: 'kg', label: 'Kilogram (kg)' },
  { value: 'meters', label: 'Meters (m)' },
];

const GST_RATE_OPTIONS: DropdownOption[] = [
  { value: '0', label: '0% — GST Exempt Goods' },
  { value: '5', label: '5% — Essential Commodities' },
  { value: '18', label: '18% — Standard Goods & Services' },
  { value: '40', label: '40% — Demerit / Sin Goods (GST 2.0)' },
];

const ADJUSTMENT_REASONS: DropdownOption[] = [
  { value: 'audit', label: 'AUDIT (Periodic stock take count)' },
  { value: 'damage', label: 'DAMAGE (Defective/broken inventory)' },
  { value: 'loss', label: 'LOSS (Unaccounted shrinkage/theft)' },
  { value: 'miscount', label: 'MISCOUNT (Previous counting error)' },
  { value: 'return', label: 'RETURN (Customer RMA restock)' },
];

const PAGE_SIZE_OPTIONS: DropdownOption[] = [
  { value: '10', label: '10' },
  { value: '20', label: '20' },
  { value: '50', label: '50' },
  { value: '100', label: '100' },
];

export const Products: React.FC = () => {
  const {
    products,
    locations,
    customFields,
    currency,
    formatCurrency,
    selectedLocationId,
    setSelectedLocationId,
    addProduct,
    bulkAddProducts,
    updateProduct,
    toggleProductActive,
    deleteProduct,
    deleteProducts,
    createAdjustment,
    bulkAdjustStock,
  } = useInventory();

  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState<ProductSortKey>('name_asc');
  const [stockStatusFilter, setStockStatusFilter] = useState<'all' | 'in_stock' | 'low' | 'out_of_stock' | 'disabled'>('all');

  // Selection for bulk actions
  const [selectedProductIds, setSelectedProductIds] = useState<string[]>([]);

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isBulkAdjustModalOpen, setIsBulkAdjustModalOpen] = useState(false);
  const [barcodeProduct, setBarcodeProduct] = useState<Product | null>(null);
  const [productToDelete, setProductToDelete] = useState<Product | null>(null);
  const [isBulkDeleteModalOpen, setIsBulkDeleteModalOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [activeMenuProductId, setActiveMenuProductId] = useState<string | null>(null);
  const [detailProduct, setDetailProduct] = useState<Product | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

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
  const [newMaxStock, setNewMaxStock] = useState('100');
  const [newHsnCode, setNewHsnCode] = useState('8471');
  const [newGstRate, setNewGstRate] = useState('18');
  const [addModalError, setAddModalError] = useState<string | null>(null);
  const [newVariantKey, setNewVariantKey] = useState('Color');
  const [newVariantValue, setNewVariantValue] = useState('');
  const [newCustomFieldsData, setNewCustomFieldsData] = useState<Record<string, any>>({});

  // Edit Product Form State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [editSku, setEditSku] = useState('');
  const [editName, setEditName] = useState('');
  const [editCategory, setEditCategory] = useState('');
  const [editUom, setEditUom] = useState('pcs');
  const [editCostPrice, setEditCostPrice] = useState('0');
  const [editSellPrice, setEditSellPrice] = useState('0');
  const [editBarcode, setEditBarcode] = useState('');
  const [editReorderPoint, setEditReorderPoint] = useState('10');
  const [editMaxStock, setEditMaxStock] = useState('100');
  const [editHsnCode, setEditHsnCode] = useState('');
  const [editGstRate, setEditGstRate] = useState('18');
  const [editModalError, setEditModalError] = useState<string | null>(null);

  // Bulk Adjustment Form State
  const [bulkDelta, setBulkDelta] = useState<number>(0);
  const [bulkLocationId, setBulkLocationId] = useState<string>(locations[0]?.id || '');
  const [bulkReason, setBulkReason] = useState<AdjustmentReasonCode>('audit');
  const [bulkNotes, setBulkNotes] = useState('');

  // Categories list & counts
  const categories = useMemo(() => {
    return ['all', ...Array.from(new Set(products.map((p) => p.category)))];
  }, [products]);

  const categoryCounts = useMemo(() => {
    return products.reduce((acc, p) => {
      acc[p.category] = (acc[p.category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
  }, [products]);

  // Active warehouse metadata & metrics
  const selectedLoc = locations.find((l) => l.id === selectedLocationId);
  const selectedLocName = selectedLoc ? `${selectedLoc.code} : ${selectedLoc.name}` : 'All Warehouses';

  // Stock counts according to strict operational criteria:
  // In Stock: strictly greater than min reorder threshold (> min)
  // Low Stock: at or below min reorder threshold and greater than 0 (0 < qty <= min)
  // Out of Stock: depleted stock (=== 0)
  const inStockCount = products.filter((p) => {
    const qty = selectedLocationId === 'all' ? p.currentStock : p.locationStock[selectedLocationId] || 0;
    return qty > p.reorderPoint;
  }).length;

  const lowStockCount = products.filter((p) => {
    const qty = selectedLocationId === 'all' ? p.currentStock : p.locationStock[selectedLocationId] || 0;
    return qty <= p.reorderPoint && qty > 0;
  }).length;

  const outOfStockCount = products.filter((p) => {
    const qty = selectedLocationId === 'all' ? p.currentStock : p.locationStock[selectedLocationId] || 0;
    return qty === 0;
  }).length;

  const disabledCount = products.filter((p) => p.isActive === false).length;

  const warehouseStockedCount = products.filter((p) => {
    const qty = selectedLocationId === 'all' ? p.currentStock : p.locationStock[selectedLocationId] || 0;
    return qty > 0;
  }).length;

  // Filtering & Sorting
  const filteredProducts = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    const list = products.filter((p) => {
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
      if (stockStatusFilter === 'in_stock') {
        matchesStock = currentQty > p.reorderPoint;
      } else if (stockStatusFilter === 'low') {
        matchesStock = currentQty <= p.reorderPoint && currentQty > 0;
      } else if (stockStatusFilter === 'out_of_stock') {
        matchesStock = currentQty === 0;
      } else if (stockStatusFilter === 'disabled') {
        matchesStock = p.isActive === false;
      }

      return matchesQuery && matchesCategory && matchesStock;
    });

    return list.sort((a, b) => {
      const qtyA = selectedLocationId === 'all' ? a.currentStock : a.locationStock[selectedLocationId] || 0;
      const qtyB = selectedLocationId === 'all' ? b.currentStock : b.locationStock[selectedLocationId] || 0;

      switch (sortBy) {
        case 'name_asc':
          return a.name.localeCompare(b.name);
        case 'name_desc':
          return b.name.localeCompare(a.name);
        case 'category':
        case 'category_asc':
          return a.category.localeCompare(b.category) || a.name.localeCompare(b.name);
        case 'category_desc':
          return b.category.localeCompare(a.category) || a.name.localeCompare(b.name);
        case 'price_asc':
          return (a.sellPrice || 0) - (b.sellPrice || 0);
        case 'price_desc':
          return (b.sellPrice || 0) - (a.sellPrice || 0);
        case 'stock_asc':
          return qtyA - qtyB;
        case 'stock_desc':
          return qtyB - qtyA;
        default:
          return 0;
      }
    });
  }, [products, searchQuery, selectedCategory, stockStatusFilter, selectedLocationId, sortBy]);

  // Pagination State
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Reset to first page on filter, sort, or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedCategory, stockStatusFilter, selectedLocationId, sortBy]);

  const totalPages = Math.max(1, Math.ceil(filteredProducts.length / pageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, filteredProducts.length);
  const paginatedProducts = filteredProducts.slice(startIndex, endIndex);

  // Handle Select All on Current Page
  const handleSelectAll = () => {
    const pageIds = paginatedProducts.map((p) => p.id);
    const isAllPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedProductIds.includes(id));
    if (isAllPageSelected) {
      setSelectedProductIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedProductIds((prev) => Array.from(new Set([...prev, ...pageIds])));
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
    setAddModalError(null);
    if (!newSku.trim() || !newName.trim()) {
      setAddModalError('SKU and Product Title are required.');
      return;
    }
    if (!newHsnCode || !newHsnCode.trim()) {
      setAddModalError('HSN/SAC classification code is required for GST compliance.');
      return;
    }
    const rateNum = Number(newGstRate);
    if (![0, 5, 18, 40].includes(rateNum)) {
      setAddModalError('GST Rate must be one of the allowed slab values (0%, 5%, 18%, 40%).');
      return;
    }

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
      maxStock: parseFloat(newMaxStock) || undefined,
      hsnCode: newHsnCode.trim(),
      gstRate: rateNum,
      variantAttributes: variantAttrs,
      customFields: newCustomFieldsData,
    });

    setIsAddModalOpen(false);
    // Reset
    setNewSku('');
    setNewName('');
    setNewBarcode('');
    setNewReorderPoint('15');
    setNewMaxStock('100');
    setNewHsnCode('8471');
    setNewGstRate('18');
    setNewVariantValue('');
    setNewCustomFieldsData({});
    setAddModalError(null);
  };

  const handleOpenEditModal = (p: Product) => {
    setEditingProduct(p);
    setEditSku(p.sku);
    setEditName(p.name);
    setEditCategory(p.category);
    setEditUom(p.unitOfMeasure);
    setEditCostPrice(String(p.costPrice));
    setEditSellPrice(String(p.sellPrice));
    setEditBarcode(p.barcode || '');
    setEditReorderPoint(String(p.reorderPoint));
    setEditMaxStock(String(p.maxStock !== undefined ? p.maxStock : (p.reorderPoint ? p.reorderPoint * 5 : 100)));
    setEditHsnCode(p.hsnCode || '');
    setEditGstRate(String(p.gstRate !== undefined ? p.gstRate : 18));
    setEditModalError(null);
    setIsEditModalOpen(true);
  };

  const handleUpdateProduct = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProduct) return;
    setEditModalError(null);

    if (!editName.trim()) {
      setEditModalError('Product Title is required.');
      return;
    }
    if (!editHsnCode || !editHsnCode.trim()) {
      setEditModalError('HSN/SAC classification code is required before saving.');
      return;
    }
    const rateNum = Number(editGstRate);
    if (![0, 5, 18, 40].includes(rateNum)) {
      setEditModalError('GST Rate must be one of the allowed slab values (0%, 5%, 18%, 40%).');
      return;
    }

    updateProduct(editingProduct.id, {
      name: editName.trim(),
      category: editCategory,
      unitOfMeasure: editUom,
      costPrice: parseFloat(editCostPrice) || 0,
      sellPrice: parseFloat(editSellPrice) || 0,
      barcode: editBarcode.trim(),
      reorderPoint: parseFloat(editReorderPoint) || 10,
      maxStock: parseFloat(editMaxStock) || undefined,
      hsnCode: editHsnCode.trim(),
      gstRate: rateNum,
    });

    setIsEditModalOpen(false);
    setEditingProduct(null);
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

    const headers = ['SKU', 'Name', 'Category', 'Unit', 'Cost', 'SellPrice', 'GST_Rate', 'HSN_Code', 'Barcode', 'CurrentStock', 'Reorder_Point', 'Max_Stock'];
    const rows = itemsToExport.map((p) => [
      p.sku,
      `"${p.name.replace(/"/g, '""')}"`,
      p.category,
      p.unitOfMeasure,
      p.costPrice,
      p.sellPrice,
      p.gstRate !== undefined ? `${p.gstRate}%` : '18%',
      p.hsnCode || '8471',
      p.barcode,
      p.currentStock,
      p.reorderPoint,
      p.maxStock !== undefined ? p.maxStock : (p.reorderPoint ? p.reorderPoint * 5 : 100),
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
      'sku,name,category,hsn_code,gst_rate,available_stock,unit_of_measure,cost_price,sell_price,currency,reorder_point,max_stock,barcode,variant_attribute',
      'SKU-EL-101,"Logitech MX Master 3S Mouse",Electronics,8471,18,15,pcs,6500.00,9999.00,INR,20,100,890786579303,Graphite',
      'SKU-EL-102,"Dell 24-inch FHD Monitor",Electronics,8528,18,109,pcs,8500.00,12999.00,INR,10,200,890362950628,Black',
      'SKU-CH-202,"Ergonomic Mesh Office Chair",Furniture,9401,18,20,pcs,9500.00,18999.00,INR,8,50,890142859012,Black',
      'SKU-CB-303,"Braided USB-C Cable 2M",Accessories,8544,5,150,pcs,350.00,799.00,INR,50,300,890582910394,Silver',
      'SKU-BK-404,"Enterprise User Manual",Documentation,4901,0,200,pcs,150.00,350.00,INR,50,500,890981234567,Paperback',
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

    const hsnIdx = headers.findIndex((h) =>
      ['hsncode', 'hsn', 'sac', 'hsnsac', 'hsnsaccode'].includes(h)
    );
    const gstIdx = headers.findIndex((h) =>
      ['gstrate', 'gst', 'gstpct', 'gstpercentage', 'taxrate'].includes(h)
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
    const stockIdx = headers.findIndex((h) =>
      ['availablestock', 'stock', 'initialstock', 'quantity', 'qty', 'currentstock', 'openingstock'].includes(h)
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
    const currencyIdx = headers.findIndex((h) =>
      ['currency', 'curr', 'cur', 'currencycode'].includes(h)
    );
    const reorderIdx = headers.findIndex((h) =>
      ['reorderpoint', 'reorder', 'minstock'].includes(h)
    );
    const maxStockIdx = headers.findIndex((h) =>
      ['maxstock', 'max_stock', 'maximumstock', 'maxlimit', 'capacity'].includes(h)
    );
    const barcodeIdx = headers.findIndex((h) =>
      ['barcode', 'upc', 'ean'].includes(h)
    );
    const variantIdx = headers.findIndex((h) =>
      ['variantattribute', 'variant', 'color', 'size', 'attributes'].includes(h)
    );

    const VALID_GST_SLABS = [0, 5, 18, 40];
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
      const stock =
        stockIdx !== -1 && cols[stockIdx]
          ? parseFloat(cols[stockIdx].replace(/[^0-9.]/g, '')) || 0
          : 0;
      const uom = uomIdx !== -1 && cols[uomIdx] ? cols[uomIdx].trim() : 'pcs';
      const cost =
        costIdx !== -1 && cols[costIdx]
          ? parseFloat(cols[costIdx].replace(/[^0-9.]/g, '')) || 0
          : 0;
      const sell =
        sellIdx !== -1 && cols[sellIdx]
          ? parseFloat(cols[sellIdx].replace(/[^0-9.]/g, '')) || 0
          : 0;
      const rawCur =
        currencyIdx !== -1 && cols[currencyIdx]
          ? cols[currencyIdx].trim().toUpperCase()
          : '';
      const prodCurrency: CurrencyCode = rawCur === 'INR' ? 'INR' : currency;
      const reorder =
        reorderIdx !== -1 && cols[reorderIdx]
          ? parseFloat(cols[reorderIdx].replace(/[^0-9.]/g, '')) || 10
          : 10;
      const maxStockVal =
        maxStockIdx !== -1 && cols[maxStockIdx]
          ? parseFloat(cols[maxStockIdx].replace(/[^0-9.]/g, '')) || undefined
          : undefined;
      const barcode =
        barcodeIdx !== -1 && cols[barcodeIdx]
          ? cols[barcodeIdx].trim()
          : `890${Math.floor(100000000 + Math.random() * 900000000)}`;
      const variant =
        variantIdx !== -1 && cols[variantIdx] ? cols[variantIdx].trim() : '';

      const hsnCode =
        hsnIdx !== -1 && cols[hsnIdx] ? cols[hsnIdx].trim() : '';
      const rawGstStr =
        gstIdx !== -1 && cols[gstIdx] ? cols[gstIdx].replace(/[^0-9.]/g, '') : '';
      const rawGst = rawGstStr !== '' ? parseFloat(rawGstStr) : NaN;

      // Validate required GST classification and allowed slab
      const rowErrors: string[] = [];
      if (!sku) rowErrors.push('Missing SKU');
      if (!name) rowErrors.push('Missing Product Name');
      if (!hsnCode) rowErrors.push('Missing HSN code');
      if (isNaN(rawGst)) {
        rowErrors.push('Missing GST rate');
      } else if (!VALID_GST_SLABS.includes(rawGst)) {
        rowErrors.push(`Invalid GST rate (${rawGst}%). Valid slabs: 0%, 5%, 18%, 40%`);
      }

      const isValid = rowErrors.length === 0;

      parsed.push({
        rawLine: i + 1,
        sku,
        name,
        category,
        initialStock: stock,
        unitOfMeasure: uom,
        costPrice: cost,
        sellPrice: sell,
        currency: prodCurrency,
        reorderPoint: reorder,
        maxStock: maxStockVal,
        barcode,
        hsnCode,
        gstRate: isNaN(rawGst) ? 18 : rawGst,
        variantAttributes: variant ? { Variant: variant } : {},
        customFields: {},
        isValid,
        errorReason: rowErrors.join('; '),
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
        initialStock: p.initialStock || 0,
        currency: p.currency || currency,
        unitOfMeasure: p.unitOfMeasure,
        costPrice: p.costPrice,
        sellPrice: p.sellPrice,
        barcode: p.barcode,
        reorderPoint: p.reorderPoint,
        maxStock: p.maxStock,
        hsnCode: p.hsnCode || '8471',
        gstRate: p.gstRate !== undefined ? p.gstRate : 18,
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
      <PageMeta
        title="Product & SKU Catalog | Invenza Enterprise Inventory"
        description="Search, filter, and manage items, custom attributes, reorder thresholds, and active warehouse allocations."
        canonicalPath="/products"
      />

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
            className="flex items-center gap-1.5 rounded-lg bg-white dark:bg-[#161b26] border border-slate-200 dark:border-[#262c3a] hover:bg-slate-50 dark:hover:bg-[#1f2636] px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-[#a8abb4] hover:text-slate-900 dark:hover:text-white transition-colors shadow-subtle whitespace-nowrap"
            title="Download CSV template with required columns at start"
          >
            <FileDown className="h-3.5 w-3.5 text-teal-600 dark:text-[#5dcaa5]" />
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
            className="flex items-center gap-1.5 rounded-lg bg-white dark:bg-[#161b26] border border-slate-200 dark:border-[#262c3a] hover:bg-slate-50 dark:hover:bg-[#1f2636] px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-[#a8abb4] hover:text-slate-900 dark:hover:text-white transition-colors shadow-subtle whitespace-nowrap"
            title="Import products from CSV file"
          >
            <Upload className="h-3.5 w-3.5 text-emerald-600 dark:text-[#5dcaa5]" />
            <span>Import</span>
          </button>

          {/* Export CSV Button */}
          <button
            type="button"
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 rounded-lg bg-white dark:bg-[#161b26] border border-slate-200 dark:border-[#262c3a] hover:bg-slate-50 dark:hover:bg-[#1f2636] px-3 py-1.5 text-xs font-medium text-slate-700 dark:text-[#a8abb4] hover:text-slate-900 dark:hover:text-white transition-colors shadow-subtle whitespace-nowrap"
            title="Export catalog products to CSV"
          >
            <Download className="h-3.5 w-3.5 text-slate-500 dark:text-[#a8abb4]" />
            <span>Export</span>
          </button>

          {/* Add New SKU Primary Button */}
          <button
            type="button"
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 dark:bg-[#5dcaa5] dark:hover:bg-[#4eb995] px-3.5 py-1.5 text-xs font-semibold text-white dark:text-[#04342c] transition-colors shadow-subtle whitespace-nowrap"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add SKU</span>
          </button>
        </div>
      </div>

      {/* Filters & Search Toolbar */}
      <div className="relative z-30 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-2 sm:p-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-card">
        {/* Left Section: Search Input + Category Dropdown + Sort Dropdown */}
        <div className="flex items-center gap-2 min-w-0 flex-1 flex-wrap sm:flex-nowrap">
          {/* Search Box */}
          <div className="relative flex-1 sm:w-48 md:w-56 lg:w-64 max-w-xs shrink min-w-[130px]">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search SKU, name, category..."
              className="h-9 w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] pl-8 pr-7 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-teal-600 focus:border-teal-600 transition-colors"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
                title="Clear search"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>

          {/* Category Dropdown */}
          <CategorySelectDropdown
            categories={categories}
            selectedCategory={selectedCategory}
            onSelect={(cat) => setSelectedCategory(cat)}
            categoryCounts={categoryCounts}
            totalCount={products.length}
            className="shrink-0"
          />

          {/* Sort By Dropdown */}
          <SortSelectDropdown
            sortBy={sortBy}
            onSelect={(newSort) => setSortBy(newSort)}
            className="shrink-0"
          />
        </div>

        {/* Right Section: Status Filter Tabs (All / In Stock / Low Stock / Out of Stock / Disabled) */}
        <div className="flex items-center overflow-x-auto scrollbar-none pb-0.5 max-w-full">
          <div className="flex items-center h-9 rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] p-0.5 text-xs gap-0.5 shrink-0">
            <button
              onClick={() => setStockStatusFilter('all')}
              className={`h-7.5 flex items-center rounded-md px-2.5 font-medium transition-all whitespace-nowrap text-xs shrink-0 ${
                stockStatusFilter === 'all'
                  ? 'bg-teal-600 hover:bg-teal-500 dark:bg-[#5dcaa5] dark:hover:bg-[#4eb995] text-white dark:text-[#04342c] shadow-subtle font-bold'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
              }`}
            >
              All ({products.length})
            </button>
            <button
              onClick={() => setStockStatusFilter('in_stock')}
              className={`h-7.5 flex items-center rounded-md px-2 sm:px-2.5 font-medium transition-all whitespace-nowrap text-xs shrink-0 ${
                stockStatusFilter === 'in_stock'
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-subtle font-bold'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
              }`}
              title="Show items with stock greater than min reorder point (> min)"
            >
              In Stock ({inStockCount})
            </button>
            <button
              onClick={() => setStockStatusFilter('low')}
              className={`h-7.5 flex items-center rounded-md px-2 sm:px-2.5 font-medium transition-all whitespace-nowrap text-xs shrink-0 ${
                stockStatusFilter === 'low'
                  ? 'bg-amber-500 hover:bg-amber-600 text-white shadow-subtle font-bold'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
              }`}
              title="Show items at or below min reorder point (≤ min, > 0)"
            >
              Low Stock ({lowStockCount})
            </button>
            <button
              onClick={() => setStockStatusFilter('out_of_stock')}
              className={`h-7.5 flex items-center rounded-md px-2 sm:px-2.5 font-medium transition-all whitespace-nowrap text-xs shrink-0 ${
                stockStatusFilter === 'out_of_stock'
                  ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-subtle font-bold'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
              }`}
              title="Show items with zero stock (0)"
            >
              Out of Stock ({outOfStockCount})
            </button>
            <button
              onClick={() => setStockStatusFilter('disabled')}
              className={`h-7.5 flex items-center rounded-md px-2 sm:px-2.5 font-medium transition-all whitespace-nowrap text-xs shrink-0 ${
                stockStatusFilter === 'disabled'
                  ? 'bg-slate-600 hover:bg-slate-500 text-white shadow-subtle font-bold'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800/60'
              }`}
              title="Show disabled / deactivated products"
            >
              Disabled ({disabledCount})
            </button>
          </div>
        </div>
      </div>

      {/* Warehouse Focus Alert Banner (Shown when a warehouse is selected) */}
      {selectedLocationId !== 'all' && (
        <div className="!mt-2.5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-teal-200 bg-teal-50/90 dark:border-teal-500/25 dark:bg-teal-500/10 px-4 py-3 text-xs text-teal-900 dark:text-teal-300 shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400 shrink-0">
              <Warehouse className="h-4 w-4" />
            </div>
            <div>
              <span className="text-slate-600 dark:text-slate-400">Warehouse Filter: </span>
              <strong className="text-slate-900 dark:text-white font-bold">{selectedLocName}</strong>
              <span className="ml-2 rounded px-2 py-0.5 text-[11px] font-mono font-medium bg-teal-100/80 dark:bg-teal-500/10 text-teal-800 dark:text-teal-400 border border-teal-300 dark:border-teal-500/20">
                {warehouseStockedCount} of {products.length} SKUs stocked here
              </span>
            </div>
          </div>

          {stockStatusFilter !== 'all' ? (
            <button
              type="button"
              onClick={() => setStockStatusFilter('all')}
              className="flex items-center gap-1 text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 transition-colors underline"
            >
              Show all SKUs ({products.length}) →
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setStockStatusFilter('in_stock')}
              className="flex items-center gap-1 text-xs font-bold text-teal-700 dark:text-teal-400 hover:text-teal-800 dark:hover:text-teal-200 transition-colors underline"
            >
              Show only in-stock SKUs ({inStockCount}) →
            </button>
          )}
        </div>
      )}

      {/* Bulk Action Sticky Bar (when items selected) */}
      {selectedProductIds.length > 0 && (
        <div className="!mt-2.5 flex items-center justify-between rounded-xl bg-slate-900/95 dark:bg-[#131924] text-white px-5 py-3 shadow-xl backdrop-blur-md animate-in fade-in slide-in-from-top-2 border border-teal-500/40">
          <div className="flex items-center gap-3 text-xs font-semibold">
            <span className="flex h-5 w-5 items-center justify-center rounded bg-teal-500 text-slate-950 font-bold font-mono text-xs">
              {selectedProductIds.length}
            </span>
            <span>SKUs selected for batch action</span>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setIsBulkAdjustModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 px-3 py-1.5 text-xs font-semibold shadow-sm transition-colors text-white"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Batch Adjust Stock
            </button>
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 rounded-lg bg-white/10 hover:bg-white/15 border border-white/10 px-3 py-1.5 text-xs font-semibold transition-colors text-white"
            >
              <Download className="h-3.5 w-3.5" />
              Export Selected
            </button>
            <button
              onClick={() => setIsBulkDeleteModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 px-3 py-1.5 text-xs font-semibold transition-colors text-white"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete Selected
            </button>
            <button
              onClick={() => setSelectedProductIds([])}
              className="rounded-lg p-1.5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* SKU Table */}
      <div className="relative z-10 !mt-2.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#131924] shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs table-fixed min-w-[760px]">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-[#F6F8FA] dark:bg-[#0C1017] text-slate-600 dark:text-slate-400 uppercase font-semibold text-[10px] tracking-wider">
                <th className="py-3.5 px-4 w-12 text-left">
                  <button onClick={handleSelectAll} className="flex items-center" aria-label="Select all on current page">
                    {paginatedProducts.length > 0 &&
                    paginatedProducts.every((p) => selectedProductIds.includes(p.id)) ? (
                      <CheckSquare className="h-4 w-4 text-teal-600 dark:text-teal-400" />
                    ) : (
                      <Square className="h-4 w-4 text-slate-400" />
                    )}
                  </button>
                </th>
                <th className="py-3.5 px-4 w-36 text-left">
                  <div className="w-full flex items-center justify-start">
                    <span>SKU</span>
                  </div>
                </th>
                <th className="py-3.5 px-4 text-left">Product Name & Category</th>
                <th className="py-3.5 px-4 w-36 text-center">
                  <div className="w-full flex items-center justify-center">
                    <span>Available Stock</span>
                  </div>
                </th>
                <th className="py-3.5 px-4 w-36 text-center">
                  <div className="w-full flex items-center justify-center gap-1.5">
                    <span>Sell Price</span>
                    <span className="font-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20">
                      {currency}
                    </span>
                  </div>
                </th>
                <th className="py-3.5 px-4 w-36 text-center">
                  <div className="w-full flex items-center justify-center">
                    <span>GST Rate</span>
                  </div>
                </th>
                <th className="py-3.5 px-4 w-36 text-center">
                  <div className="w-full flex items-center justify-center">
                    <span>Actions</span>
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {paginatedProducts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400 text-xs">
                    <Package className="h-8 w-8 mx-auto mb-2 opacity-40 text-slate-500" />
                    No products found matching the selected filters.
                  </td>
                </tr>
              ) : (
                paginatedProducts.map((p, pIdx) => {
                  const isSelected = selectedProductIds.includes(p.id);
                  const currentQty =
                    selectedLocationId === 'all'
                      ? p.currentStock
                      : p.locationStock[selectedLocationId] || 0;
                  const isOutOfStock = currentQty === 0;
                  const isLow = currentQty > 0 && currentQty <= p.reorderPoint;
                  const margin =
                    p.sellPrice > 0
                      ? Math.round(((p.sellPrice - p.costPrice) / p.sellPrice) * 100)
                      : 0;
                  const defaultLoc =
                    locations.find((l) => l.id === p.warehouseId || l.code === p.warehouseId) || locations[0];
                  const warehouseIdentifier = p.warehouseId || defaultLoc?.id || 'WH-001';
                  const warehouseName = defaultLoc?.name || 'Central Distribution Hub';
                  const maxStockVal = p.maxStock !== undefined && p.maxStock !== null ? p.maxStock : (p.reorderPoint ? p.reorderPoint * 5 : 100);
                  const variantEntries = Object.entries(p.variantAttributes || {}).filter(
                    ([_, v]) => Boolean(v && String(v).trim())
                  );
                  const hasVariants = variantEntries.length > 0;
                  const openDownward = pIdx === 0 && paginatedProducts.length > 1;
                  const tooltipPlacement = openDownward ? 'top-full mt-1.5' : 'bottom-full mb-1.5';

                  return (
                    <tr
                      key={p.id}
                      className={`relative hover:z-30 transition-colors ${
                        p.isActive === false
                          ? 'bg-slate-100/40 dark:bg-slate-900/60 hover:bg-slate-100/60 dark:hover:bg-slate-900/80'
                          : 'hover:bg-slate-50/80 dark:hover:bg-slate-800/50'
                      } ${isSelected ? 'bg-teal-50/30 dark:bg-teal-950/20' : ''}`}
                    >
                      <td className="py-3.5 px-4 w-12 text-left">
                        <button
                          onClick={() => handleToggleSelect(p.id)}
                          className="flex items-center"
                        >
                          {isSelected ? (
                            <CheckSquare className="h-4 w-4 text-teal-600 dark:text-teal-400" />
                          ) : (
                            <Square className="h-4 w-4 text-slate-400" />
                          )}
                        </button>
                      </td>
                      <td className="py-3.5 px-4 w-36 text-left">
                        <div
                          className="relative group/sku hover:z-50 w-full flex flex-col items-start justify-center cursor-pointer"
                          onClick={() => setDetailProduct(p)}
                        >
                          <div className={`flex flex-col items-start ${p.isActive === false ? 'opacity-50' : ''}`}>
                            <span className="font-mono font-bold text-teal-600 dark:text-teal-400 group-hover/sku:underline whitespace-nowrap truncate max-w-full">
                              {p.sku}
                            </span>
                            {p.isActive === false && (
                              <div className="mt-0.5">
                                <span className="inline-block rounded-md bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 px-1.5 py-0.5 text-[10px] font-medium tracking-wide">
                                  Disabled
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Hover Tooltip revealing default location */}
                          <div className={`absolute left-0 ${tooltipPlacement} hidden group-hover/sku:flex flex-col z-50 whitespace-nowrap rounded-xl bg-slate-900 dark:bg-slate-950 text-white px-3 py-2 text-[11px] shadow-2xl border border-slate-700 ring-1 ring-white/10 pointer-events-none transition-all`}>
                            <div className="flex items-center gap-1.5 text-teal-300 font-semibold">
                              <Warehouse className="h-3.5 w-3.5 text-teal-400" />
                              <span>Default Warehouse Location</span>
                            </div>
                            <div className="mt-1 text-slate-200 text-[11px]">
                              <span className="font-medium text-white">{warehouseName}</span>
                              <span className="text-slate-400 font-mono ml-1">({defaultLoc?.code || warehouseIdentifier})</span>
                              {defaultLoc?.city ? <span className="text-slate-400"> • {defaultLoc.city}</span> : ''}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td
                        className="py-3.5 px-4 text-left cursor-pointer"
                        onClick={() => setDetailProduct(p)}
                      >
                        <div className="group/name relative hover:z-50 inline-flex flex-col max-w-full">
                          <div className={`flex flex-col max-w-full ${p.isActive === false ? 'opacity-50' : ''}`}>
                            <div className="font-semibold text-slate-800 dark:text-slate-200 group-hover/name:text-teal-600 dark:group-hover/name:text-teal-400 transition-colors truncate">
                              {p.name}
                            </div>
                            <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                              <span className="inline-block rounded-md bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-500 dark:text-slate-400 max-w-[160px] truncate">
                                {p.category}
                              </span>
                              {hasVariants && (
                                <div className="inline-flex flex-wrap items-center gap-1">
                                  {variantEntries.map(([attrKey, attrVal]) => (
                                    <span
                                      key={attrKey}
                                      title={`${attrKey}: ${attrVal}`}
                                      className="inline-flex items-center rounded-md bg-teal-50 dark:bg-teal-950/50 text-teal-700 dark:text-teal-300 border border-teal-200/70 dark:border-teal-800/60 px-1.5 py-0.5 text-[9px] font-semibold max-w-[120px] truncate"
                                    >
                                      {attrVal}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>

                          {/* Hover Tooltip: 1. Product Name, 2. | Variant : ... |, 3. | Category : ... | */}
                          <div className={`absolute left-0 ${tooltipPlacement} hidden group-hover/name:flex flex-col z-50 min-w-[200px] max-w-sm rounded-xl bg-slate-900 dark:bg-slate-950 text-white p-3 text-xs shadow-2xl border border-slate-700 ring-1 ring-white/10 pointer-events-none transition-all gap-1.5`}>
                            {/* 1. Product name */}
                            <div className="font-semibold text-white text-xs leading-snug">
                              {p.name}
                            </div>

                            {/* Badges for Variant and Category */}
                            <div className="flex flex-wrap items-center gap-1.5 pt-1.5 border-t border-slate-800/80">
                              {/* 2. | Variant : ... | */}
                              {hasVariants ? (
                                variantEntries.map(([attrKey, attrVal]) => (
                                  <span
                                    key={attrKey}
                                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-teal-950/80 text-teal-300 border border-teal-700/60 font-mono text-[10px]"
                                  >
                                    <span className="text-teal-400 font-medium">
                                      {attrKey.toLowerCase() === 'variant' ? 'Variant' : attrKey} :
                                    </span>
                                    <span className="font-bold text-white">{attrVal}</span>
                                  </span>
                                ))
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/90 text-slate-300 border border-slate-700 font-mono text-[10px]">
                                  <span className="text-slate-400 font-medium">Variant :</span>
                                  <span className="text-slate-400 italic">None</span>
                                </span>
                              )}

                              {/* 3. | Category : ... | */}
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/90 text-slate-300 border border-slate-700 font-mono text-[10px]">
                                <span className="text-slate-400 font-medium">Category :</span>
                                <span className="font-semibold text-white">{p.category}</span>
                              </span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 w-36 text-center font-mono tabular-nums">
                        <div className="group/stock relative hover:z-50 w-full flex items-center justify-center cursor-default">
                          <div className={`inline-flex items-center gap-1.5 ${p.isActive === false ? 'opacity-50' : ''}`}>
                            {isOutOfStock ? (
                              <span className="flex h-2 w-2 rounded-full bg-rose-500 shrink-0" title="Out of stock (0)" />
                            ) : isLow ? (
                              <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse shrink-0" title="Low stock threshold (≤ min, > 0)" />
                            ) : (
                              <span className="flex h-2 w-2 rounded-full bg-emerald-500/80 shrink-0" title="Healthy stock (> min)" />
                            )}
                            <span
                              className={`font-bold tabular-nums ${
                                isOutOfStock
                                  ? 'text-rose-500 dark:text-rose-400'
                                  : isLow
                                  ? 'text-amber-600 dark:text-amber-400'
                                  : 'text-slate-800 dark:text-slate-200'
                              }`}
                            >
                              {currentQty.toLocaleString()}
                            </span>
                            <span className="text-[11px] font-normal text-slate-400 dark:text-slate-500 shrink-0">
                              {p.unitOfMeasure}
                            </span>
                          </div>

                          {/* Hover Tooltip revealing Min and Max stock thresholds */}
                          <div className={`absolute left-1/2 -translate-x-1/2 ${tooltipPlacement} hidden group-hover/stock:flex flex-col z-50 whitespace-nowrap rounded-lg bg-slate-900 dark:bg-slate-950 text-white px-2.5 py-1.5 text-[10px] shadow-2xl border border-slate-700 ring-1 ring-white/10 pointer-events-none transition-all gap-0.5`}>
                            <div className="flex items-center gap-1 text-teal-300 font-semibold pb-0.5 border-b border-slate-800/80">
                              <Package className="h-3 w-3 text-teal-400" />
                              <span>Stock Thresholds</span>
                            </div>
                            <div className="flex items-center justify-between gap-3 text-slate-300 pt-0.5">
                              <span className="text-slate-400">Min Order:</span>
                              <strong className="font-mono text-amber-400">{p.reorderPoint} {p.unitOfMeasure}</strong>
                            </div>
                            <div className="flex items-center justify-between gap-3 text-slate-300">
                              <span className="text-slate-400">Max Order:</span>
                              <strong className="font-mono text-emerald-400">{maxStockVal} {p.unitOfMeasure}</strong>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 w-36 text-center font-mono tabular-nums">
                        <div className="group/price relative hover:z-50 w-full flex items-center justify-center cursor-default">
                          <span className={`font-bold tabular-nums text-slate-900 dark:text-white ${p.isActive === false ? 'opacity-50' : ''}`}>
                            {formatCurrency(p.sellPrice, p.currency || currency)}
                          </span>

                          {/* Hover Tooltip revealing Cost Price, Margin % & Profit */}
                          <div className={`absolute left-1/2 -translate-x-1/2 ${tooltipPlacement} hidden group-hover/price:flex flex-col z-50 whitespace-nowrap rounded-xl bg-slate-900 dark:bg-slate-950 text-white px-3 py-2 text-[11px] shadow-2xl border border-slate-700 ring-1 ring-white/10 pointer-events-none transition-all`}>
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-slate-400">Gross Margin:</span>
                              <span
                                className={`font-mono font-bold ${
                                  margin > 40
                                    ? 'text-emerald-400'
                                    : margin > 20
                                    ? 'text-teal-300'
                                    : 'text-amber-400'
                                }`}
                              >
                                {margin}%
                              </span>
                            </div>
                            <div className="text-[10px] text-slate-300 mt-0.5">
                              Cost Price: <span className="font-mono font-semibold text-slate-200">{formatCurrency(p.costPrice, p.currency || currency)}</span>
                            </div>
                            <div className="text-[10px] text-slate-300 mt-0.5">
                              Unit Spread: <span className="font-mono font-semibold text-emerald-400">+{formatCurrency(p.sellPrice - p.costPrice, p.currency || currency)}</span>
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 w-36 text-center font-mono tabular-nums">
                        <div className="group/gst relative hover:z-50 w-full flex items-center justify-center cursor-default">
                          <span className={`font-mono font-bold tabular-nums text-slate-800 dark:text-slate-200 ${p.isActive === false ? 'opacity-50' : ''}`}>
                            {p.gstRate !== undefined ? `${p.gstRate}%` : '18%'}
                          </span>

                          {/* Hover Tooltip revealing HSN code & slab */}
                          <div className={`absolute left-1/2 -translate-x-1/2 ${tooltipPlacement} hidden group-hover/gst:flex flex-col z-50 whitespace-nowrap rounded-lg bg-slate-900 dark:bg-slate-950 text-white px-2.5 py-1.5 text-[11px] shadow-2xl border border-slate-700 ring-1 ring-white/10 pointer-events-none transition-all`}>
                            <div className="font-medium text-teal-300">HSN Code: <span className="text-white font-mono font-bold">{p.hsnCode || 'N/A'}</span></div>
                            <div className="text-[10px] text-slate-300">GST Slab: {p.gstRate !== undefined ? `${p.gstRate}%` : '18%'}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-4 w-36 text-center">
                        <div className={`w-full flex items-center justify-center gap-1.5 ${p.isActive === false ? 'opacity-60' : ''}`}>
                          {/* Edit Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenEditModal(p);
                            }}
                            title="Edit SKU & Tax Data"
                            aria-label="Edit SKU"
                            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>

                          {/* Soft Delete (is_active) Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleProductActive(p.id);
                            }}
                            title={
                              p.isActive !== false
                                ? 'Soft Delete: Disable Product (keeps stock & history)'
                                : 'Enable Product (Re-activate)'
                            }
                            aria-label={p.isActive !== false ? 'Disable Product' : 'Enable Product'}
                            className={`rounded-lg p-1.5 transition-colors ${
                              p.isActive !== false
                                ? 'text-slate-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950/40'
                                : 'text-amber-600 bg-amber-50 dark:bg-amber-950/50 hover:bg-amber-100 dark:hover:bg-amber-900/60'
                            }`}
                          >
                            <Power className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3.5 border-t border-slate-200/80 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-xs text-slate-500 dark:text-slate-400 rounded-b-2xl">
          <div className="flex flex-wrap items-center gap-3 sm:gap-4">
            <span>
              Showing{' '}
              <strong className="font-semibold text-slate-900 dark:text-white">
                {filteredProducts.length === 0 ? 0 : startIndex + 1}
              </strong>{' '}
              to{' '}
              <strong className="font-semibold text-slate-900 dark:text-white">
                {endIndex}
              </strong>{' '}
              of{' '}
              <strong className="font-semibold text-slate-900 dark:text-white">
                {filteredProducts.length}
              </strong>{' '}
              products
            </span>

            <div className="flex items-center gap-1.5 pl-3 border-l border-slate-200 dark:border-slate-700">
              <span className="text-[11px] text-slate-500 dark:text-slate-400">Rows per page:</span>
              <div className="w-20">
                <SimpleSelectDropdown
                  options={PAGE_SIZE_OPTIONS}
                  value={String(pageSize)}
                  onChange={(val) => {
                    setPageSize(Number(val));
                    setCurrentPage(1);
                  }}
                  buttonClassName="py-1 px-2.5 h-[28px] rounded-lg text-xs font-semibold"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center gap-1 self-end sm:self-auto">
            {/* First Page */}
            <button
              type="button"
              disabled={safeCurrentPage <= 1}
              onClick={() => setCurrentPage(1)}
              title="First Page"
              className={`p-1.5 rounded-lg border transition-colors ${
                safeCurrentPage <= 1
                  ? 'border-slate-200 dark:border-slate-800 text-slate-300 dark:text-slate-700 cursor-not-allowed'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              <ChevronsLeft className="h-4 w-4" />
            </button>

            {/* Previous Page */}
            <button
              type="button"
              disabled={safeCurrentPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              title="Previous Page"
              className={`p-1.5 rounded-lg border transition-colors ${
                safeCurrentPage <= 1
                  ? 'border-slate-200 dark:border-slate-800 text-slate-300 dark:text-slate-700 cursor-not-allowed'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            {/* Page number buttons */}
            <div className="flex items-center gap-1 px-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter((p) => {
                  if (totalPages <= 7) return true;
                  if (p === 1 || p === totalPages) return true;
                  return Math.abs(p - safeCurrentPage) <= 1;
                })
                .map((pageNum, idx, arr) => {
                  const prev = arr[idx - 1];
                  const showEllipsis = prev && pageNum - prev > 1;
                  return (
                    <React.Fragment key={pageNum}>
                      {showEllipsis && <span className="px-1 text-slate-400">…</span>}
                      <button
                        type="button"
                        onClick={() => setCurrentPage(pageNum)}
                        className={`min-w-[28px] h-7 px-2 rounded-lg text-xs font-bold transition-all ${
                          safeCurrentPage === pageNum
                            ? 'bg-teal-600 dark:bg-[#5dcaa5] text-white dark:text-[#04342c] shadow-subtle'
                            : 'border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
                        }`}
                      >
                        {pageNum}
                      </button>
                    </React.Fragment>
                  );
                })}
            </div>

            {/* Next Page */}
            <button
              type="button"
              disabled={safeCurrentPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              title="Next Page"
              className={`p-1.5 rounded-lg border transition-colors ${
                safeCurrentPage >= totalPages
                  ? 'border-slate-200 dark:border-slate-800 text-slate-300 dark:text-slate-700 cursor-not-allowed'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              <ChevronRight className="h-4 w-4" />
            </button>

            {/* Last Page */}
            <button
              type="button"
              disabled={safeCurrentPage >= totalPages}
              onClick={() => setCurrentPage(totalPages)}
              title="Last Page"
              className={`p-1.5 rounded-lg border transition-colors ${
                safeCurrentPage >= totalPages
                  ? 'border-slate-200 dark:border-slate-800 text-slate-300 dark:text-slate-700 cursor-not-allowed'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'
              }`}
            >
              <ChevronsRight className="h-4 w-4" />
            </button>
          </div>
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
          {addModalError && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-semibold">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{addModalError}</span>
            </div>
          )}
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
              <SimpleSelectDropdown
                options={UOM_OPTIONS}
                value={newUom}
                onChange={setNewUom}
              />
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

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
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
                Min Reorder Level
              </label>
              <input
                type="number"
                value={newReorderPoint}
                onChange={(e) => setNewReorderPoint(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Max Stock Level
              </label>
              <input
                type="number"
                value={newMaxStock}
                onChange={(e) => setNewMaxStock(e.target.value)}
                placeholder="e.g. 100"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          {/* GST Classification Section */}
          <div className="rounded-xl border border-teal-500/20 bg-teal-500/10 p-3.5 space-y-2.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-teal-800 dark:text-teal-300">
              <Tag className="h-3.5 w-3.5" />
              GST 2.0 Statutory Classification
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  HSN / SAC Code *
                </label>
                <input
                  type="text"
                  required
                  value={newHsnCode}
                  onChange={(e) => setNewHsnCode(e.target.value.trim())}
                  placeholder="e.g. 8471"
                  className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">Harmonized System Nomenclature code printed on invoices</span>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  GST Rate Slab *
                </label>
                <SimpleSelectDropdown
                  options={GST_RATE_OPTIONS}
                  value={newGstRate}
                  onChange={setNewGstRate}
                  buttonClassName="font-mono font-bold text-teal-700 dark:text-teal-300"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">Valid GST 2.0 standard rates</span>
              </div>
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
                      <SimpleSelectDropdown
                        options={(cf.options || []).map((opt) => ({ value: opt, label: opt }))}
                        value={newCustomFieldsData[cf.key] || ''}
                        onChange={(val) =>
                          setNewCustomFieldsData((prev) => ({
                            ...prev,
                            [cf.key]: val,
                          }))
                        }
                        placeholder="Select option..."
                      />
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
              className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-teal-600 hover:bg-teal-500 dark:bg-[#5dcaa5] dark:hover:bg-[#4eb995] px-5 py-2 text-xs font-semibold text-white dark:text-[#04342c] shadow-subtle transition-colors"
            >
              Save Product SKU
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Product Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => {
          setIsEditModalOpen(false);
          setEditingProduct(null);
        }}
        title="Edit SKU & Tax Classification"
        subtitle="Update product pricing, inventory thresholds, and GST 2.0 classification"
        maxWidth="2xl"
      >
        <form onSubmit={handleUpdateProduct} className="space-y-4">
          {editModalError && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs font-semibold">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{editModalError}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                SKU Identifier
              </label>
              <input
                type="text"
                disabled
                value={editSku}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800/50 px-3 py-2 text-xs font-mono text-slate-500 cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Product Title *
              </label>
              <input
                type="text"
                required
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
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
                value={editCategory}
                onChange={(e) => setEditCategory(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Unit of Measure (UOM)
              </label>
              <SimpleSelectDropdown
                options={UOM_OPTIONS}
                value={editUom}
                onChange={setEditUom}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Barcode Value
              </label>
              <input
                type="text"
                value={editBarcode}
                onChange={(e) => setEditBarcode(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Cost Price ({currency})
              </label>
              <input
                type="number"
                step="0.01"
                value={editCostPrice}
                onChange={(e) => setEditCostPrice(e.target.value)}
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
                value={editSellPrice}
                onChange={(e) => setEditSellPrice(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Min Reorder Level
              </label>
              <input
                type="number"
                value={editReorderPoint}
                onChange={(e) => setEditReorderPoint(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Max Stock Level
              </label>
              <input
                type="number"
                value={editMaxStock}
                onChange={(e) => setEditMaxStock(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          {/* GST Classification Section */}
          <div className="rounded-xl border border-teal-500/20 bg-teal-500/10 p-3.5 space-y-2.5">
            <div className="flex items-center gap-1.5 text-xs font-bold text-teal-800 dark:text-teal-300">
              <Tag className="h-3.5 w-3.5" />
              GST 2.0 Statutory Classification
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  HSN / SAC Code *
                </label>
                <input
                  type="text"
                  required
                  value={editHsnCode}
                  onChange={(e) => setEditHsnCode(e.target.value.trim())}
                  placeholder="e.g. 8471"
                  className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:border-teal-500 focus:ring-1 focus:ring-teal-500 focus:outline-none"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">Harmonized System Nomenclature classification code</span>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  GST Rate Slab *
                </label>
                <SimpleSelectDropdown
                  options={GST_RATE_OPTIONS}
                  value={editGstRate}
                  onChange={setEditGstRate}
                  buttonClassName="font-mono font-bold text-teal-700 dark:text-teal-300"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">Valid GST 2.0 standard rates</span>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => {
                setIsEditModalOpen(false);
                setEditingProduct(null);
              }}
              className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-teal-600 hover:bg-teal-500 dark:bg-[#5dcaa5] dark:hover:bg-[#4eb995] px-5 py-2 text-xs font-semibold text-white dark:text-[#04342c] shadow-subtle transition-colors"
            >
              Save Changes
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
            <WarehouseSelectDropdown
              locations={locations}
              selectedLocationId={bulkLocationId}
              onSelect={(id) => setBulkLocationId(id)}
            />
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
              <SimpleSelectDropdown
                options={ADJUSTMENT_REASONS}
                value={bulkReason}
                onChange={(val) => setBulkReason(val as AdjustmentReasonCode)}
              />
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
              className="rounded-lg border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-teal-600 hover:bg-teal-500 dark:bg-[#5dcaa5] dark:hover:bg-[#4eb995] px-5 py-2 text-xs font-semibold text-white dark:text-[#04342c] shadow-subtle transition-colors"
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
        footer={
          <div className="flex items-center justify-between w-full">
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
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-teal-600 hover:bg-teal-500 dark:bg-[#5dcaa5] dark:hover:bg-[#4eb995] text-white dark:text-[#04342c] text-xs font-bold shadow-subtle disabled:opacity-50 disabled:cursor-not-allowed transition-all"
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
        }
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
                  Required columns: <code className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">sku</code> and <code className="text-indigo-600 dark:text-indigo-400 font-mono font-bold">name</code>. Optional: <span className="font-semibold text-indigo-500 dark:text-indigo-400">available_stock</span>, <span className="font-semibold text-indigo-500 dark:text-indigo-400">currency</span> (INR), category, unit, cost, price, barcode.
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
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 text-xs font-bold">
                    <AlertCircle className="h-3.5 w-3.5" />
                    {invalidParsedProducts.length} Rejected (Missing HSN or Invalid GST Rate)
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
                      <th className="px-3 py-2">HSN Code</th>
                      <th className="px-3 py-2 text-right">GST Rate</th>
                      <th className="px-3 py-2 text-right">Stock</th>
                      <th className="px-3 py-2 text-right">Max Stock</th>
                      <th className="px-3 py-2 text-center">Cur</th>
                      <th className="px-3 py-2 text-right">Cost</th>
                      <th className="px-3 py-2 text-right">Sell Price</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 bg-white dark:bg-slate-900">
                    {parsedProducts.map((p, idx) => (
                      <tr key={idx} className={p.isValid ? '' : 'bg-rose-500/10 dark:bg-rose-950/20'}>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {p.isValid ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded">
                              <Check className="h-3 w-3" /> Ready
                            </span>
                          ) : (
                            <span
                              title={p.errorReason}
                              className="inline-flex items-center gap-1 text-[10px] font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-950/40 px-1.5 py-0.5 rounded"
                            >
                              <AlertCircle className="h-3 w-3 shrink-0" />
                              <span className="max-w-[140px] truncate">{p.errorReason || 'Invalid'}</span>
                            </span>
                          )}
                        </td>
                        <td className="px-3 py-2 font-mono font-bold text-slate-800 dark:text-slate-200">
                          {p.sku || <em className="text-rose-400 font-sans font-normal">empty</em>}
                        </td>
                        <td className="px-3 py-2 font-medium text-slate-700 dark:text-slate-300">
                          {p.name || <em className="text-rose-400 font-sans font-normal">empty</em>}
                        </td>
                        <td className="px-3 py-2 font-mono text-xs text-slate-600 dark:text-slate-400">
                          {p.hsnCode || <span className="text-rose-500 font-bold">Missing</span>}
                        </td>
                        <td className="px-3 py-2 text-right font-mono font-bold text-slate-700 dark:text-slate-300">
                          {p.gstRate !== undefined && !isNaN(p.gstRate) ? (
                            <span className={[0, 5, 18, 40].includes(p.gstRate) ? 'text-indigo-600 dark:text-indigo-400' : 'text-rose-500'}>
                              {p.gstRate}%
                            </span>
                          ) : (
                            <span className="text-rose-500">Invalid</span>
                          )}
                        </td>
                        <td className="px-3 py-2 text-right font-mono font-bold text-emerald-600 dark:text-emerald-400">
                          {p.initialStock} {p.unitOfMeasure}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-slate-600 dark:text-slate-400">
                          {p.maxStock !== undefined ? p.maxStock : '—'}
                        </td>
                        <td className="px-3 py-2 text-center font-mono font-bold text-indigo-600 dark:text-indigo-400">
                          {p.currency}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-slate-600 dark:text-slate-400">
                          {formatCurrency(p.costPrice, p.currency)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono font-bold text-indigo-600 dark:text-indigo-400">
                          {formatCurrency(p.sellPrice, p.currency)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Expanded Product Detail View Modal */}
      {detailProduct && (
        <Modal
          isOpen={Boolean(detailProduct)}
          onClose={() => setDetailProduct(null)}
          title={`Product Specifications: ${detailProduct.sku}`}
          subtitle={`${detailProduct.name} • ${detailProduct.category}`}
          maxWidth="3xl"
        >
          <div className="space-y-5 text-xs text-slate-600 dark:text-slate-300">
            {/* Top Status & Core Identification Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                  <Package className="h-6 w-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-base text-slate-900 dark:text-white">
                      {detailProduct.name}
                    </h3>
                    <span className="rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 text-[10px] font-mono font-medium text-slate-700 dark:text-slate-300">
                      {detailProduct.category}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                    <span>SKU: <strong className="text-slate-800 dark:text-slate-200">{detailProduct.sku}</strong></span>
                    <span>•</span>
                    <span>UOM: <strong className="text-slate-800 dark:text-slate-200">{detailProduct.unitOfMeasure}</strong></span>
                    <span>•</span>
                    <span>Status: <strong className="text-emerald-600 dark:text-emerald-400">Active Catalog Item</strong></span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {detailProduct.currentStock === 0 ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                    <span className="h-1.5 w-1.5 rounded-sm bg-rose-500" />
                    CRITICAL: OUT OF STOCK
                  </span>
                ) : detailProduct.currentStock <= detailProduct.reorderPoint ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                    <span className="h-1.5 w-1.5 rounded-sm bg-amber-500" />
                    LOW STOCK ALERT (≤ {detailProduct.reorderPoint} {detailProduct.unitOfMeasure})
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <span className="h-1.5 w-1.5 rounded-sm bg-emerald-500" />
                    OPTIMAL STOCK LEVEL
                  </span>
                )}
              </div>
            </div>

            {/* 4 Metric KPI Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-3 shadow-sm flex flex-col justify-between">
                <div>
                  <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Total Stock</div>
                  <div className="text-lg font-bold font-mono text-slate-900 dark:text-white mt-1">
                    {detailProduct.currentStock.toLocaleString()} <span className="text-xs font-normal text-slate-400">{detailProduct.unitOfMeasure}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                    Min: {detailProduct.reorderPoint} • Max: {detailProduct.maxStock !== undefined ? detailProduct.maxStock : (detailProduct.reorderPoint ? detailProduct.reorderPoint * 5 : 100)}
                  </div>
                </div>
                
                {/* Stock Health Status & Comment */}
                <div className="mt-2.5 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] font-bold">
                    {detailProduct.currentStock === 0 ? (
                      <span className="text-rose-600 dark:text-rose-400">Status: Out of Stock</span>
                    ) : detailProduct.currentStock <= detailProduct.reorderPoint ? (
                      <span className="text-amber-600 dark:text-amber-400">Status: Low Stock Threshold</span>
                    ) : (
                      <span className="text-emerald-600 dark:text-emerald-400">Status: Optimal Parameters</span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 leading-tight">
                    {detailProduct.currentStock === 0
                      ? '⚠️ Depleted stock. Replenishment PO required.'
                      : detailProduct.currentStock <= detailProduct.reorderPoint
                      ? '⚠️ Below min reorder threshold.'
                      : '✅ Stock is within optimal parameters.'}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-3 shadow-sm">
                <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Selling Price</div>
                <div className="text-lg font-bold font-mono text-indigo-600 dark:text-indigo-400 mt-1">
                  {formatCurrency(detailProduct.sellPrice, detailProduct.currency || currency)}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">
                  Cost: {formatCurrency(detailProduct.costPrice, detailProduct.currency || currency)}
                </div>
              </div>

              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-3 shadow-sm">
                <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Gross Margin</div>
                {(() => {
                  const m = detailProduct.sellPrice > 0 ? Math.round(((detailProduct.sellPrice - detailProduct.costPrice) / detailProduct.sellPrice) * 100) : 0;
                  const profit = detailProduct.sellPrice - detailProduct.costPrice;
                  return (
                    <>
                      <div className={`text-lg font-bold font-mono mt-1 ${m >= 40 ? 'text-emerald-600 dark:text-emerald-400' : m >= 20 ? 'text-slate-800 dark:text-slate-200' : 'text-amber-600 dark:text-amber-400'}`}>
                        {m}%
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        +{formatCurrency(profit, detailProduct.currency || currency)} / unit
                      </div>
                    </>
                  );
                })()}
              </div>

              <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 p-3 shadow-sm">
                <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">GST Slab & HSN</div>
                <div className="text-lg font-bold font-mono text-teal-600 dark:text-teal-400 mt-1">
                  {detailProduct.gstRate !== undefined ? `${detailProduct.gstRate}%` : '18%'}
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
                  HSN: {detailProduct.hsnCode || 'Unassigned'}
                </div>
              </div>
            </div>

            {/* GST 2.0 Statutory Tax Classification Section */}
            <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3.5 bg-slate-50/50 dark:bg-slate-800/30 space-y-2.5">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <span className="flex h-2 w-2 rounded-full bg-teal-500" />
                  GST 2.0 Statutory Tax Classification
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-teal-500/10 text-teal-700 dark:text-teal-300 font-mono font-semibold">
                  HSN: {detailProduct.hsnCode || 'N/A'} • Slab: {detailProduct.gstRate !== undefined ? `${detailProduct.gstRate}%` : '18%'}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-2.5 space-y-1.5 font-mono text-[11px]">
                  <div className="font-sans font-bold text-slate-700 dark:text-slate-300 text-xs flex items-center gap-1">
                    <span>Intra-State Supply (Same State)</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">CGST + SGST</span>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>CGST ({(Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 2).toFixed(1)}%):</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {formatCurrency(detailProduct.sellPrice * (Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 200), detailProduct.currency || currency)}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>SGST ({(Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 2).toFixed(1)}%):</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {formatCurrency(detailProduct.sellPrice * (Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 200), detailProduct.currency || currency)}
                    </span>
                  </div>
                  <div className="border-t border-slate-100 dark:border-slate-800 pt-1 flex justify-between font-bold text-slate-800 dark:text-slate-200">
                    <span>Total Incl. GST:</span>
                    <span className="text-teal-600 dark:text-teal-400">
                      {formatCurrency(detailProduct.sellPrice * (1 + Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 100), detailProduct.currency || currency)}
                    </span>
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/70 p-2.5 space-y-1.5 font-mono text-[11px]">
                  <div className="font-sans font-bold text-slate-700 dark:text-slate-300 text-xs flex items-center gap-1">
                    <span>Inter-State Supply (Out of State)</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-slate-100 dark:bg-slate-800 text-slate-500">IGST Only</span>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>IGST ({Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18)}%):</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200">
                      {formatCurrency(detailProduct.sellPrice * (Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 100), detailProduct.currency || currency)}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-500">
                    <span>Place of Supply Rule:</span>
                    <span className="text-slate-700 dark:text-slate-300 font-sans text-[10px]">Shipping Destination State</span>
                  </div>
                  <div className="border-t border-slate-100 dark:border-slate-800 pt-1 flex justify-between font-bold text-slate-800 dark:text-slate-200">
                    <span>Total Incl. GST:</span>
                    <span className="text-teal-600 dark:text-teal-400">
                      {formatCurrency(detailProduct.sellPrice * (1 + Number(detailProduct.gstRate !== undefined ? detailProduct.gstRate : 18) / 100), detailProduct.currency || currency)}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Warehouse Stock Breakdown */}
            <div className="space-y-2">
              <h4 className="font-bold text-slate-900 dark:text-white flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Warehouse className="h-4 w-4 text-indigo-500" />
                  Multi-Warehouse Stock Distribution
                </span>
                <span className="text-[11px] font-normal text-slate-400 font-mono">
                  {locations.length} Registered Locations
                </span>
              </h4>

              <div className="rounded-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-800/60 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-semibold text-[10px] uppercase">
                    <tr>
                      <th className="py-2.5 px-3">Warehouse Name</th>
                      <th className="py-2.5 px-3">Code</th>
                      <th className="py-2.5 px-3">Address</th>
                      <th className="py-2.5 px-3 text-right">Available Stock</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60 font-mono">
                    {locations.map(loc => {
                      const qty = detailProduct.locationStock?.[loc.id] || 0;
                      return (
                        <tr key={loc.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30">
                          <td className="py-2.5 px-3 font-sans font-medium text-slate-800 dark:text-slate-200">
                            {loc.name}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">
                            {loc.code}
                          </td>
                          <td className="py-2.5 px-3 font-sans text-slate-400 truncate max-w-[200px]">
                            {loc.address || 'Standard Warehouse'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold">
                            <span className={qty > 0 ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400'}>
                              {qty} {detailProduct.unitOfMeasure}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Specifications, Variants & Barcode */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {/* Variant Attributes & Lot Card */}
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3 space-y-2 bg-white dark:bg-slate-900/60">
                <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <Tag className="h-4 w-4 text-indigo-500" />
                  Variant Attributes & Lots
                </div>
                <div className="space-y-1.5">
                  {Object.keys(detailProduct.variantAttributes || {}).length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(detailProduct.variantAttributes || {}).map(([k, v]) => (
                        <div
                          key={k}
                          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-2 py-1 text-xs"
                        >
                          <span className="text-slate-400">{k}:</span>{' '}
                          <span className="font-bold text-slate-700 dark:text-slate-200">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-400 italic">No variant attributes specified</div>
                  )}

                  {detailProduct.customFields?.batchNumber && (
                    <div className="mt-2 flex items-center justify-between rounded-lg border border-purple-500/20 bg-purple-500/10 px-2.5 py-1.5 text-xs text-purple-700 dark:text-purple-300">
                      <span>Batch / Lot Number:</span>
                      <strong className="font-mono">{detailProduct.customFields.batchNumber}</strong>
                    </div>
                  )}
                </div>
              </div>

              {/* Barcode & Identifiers */}
              <div className="rounded-xl border border-slate-200 dark:border-slate-800 p-3 space-y-2 bg-white dark:bg-slate-900/60">
                <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                  <Barcode className="h-4 w-4 text-indigo-500" />
                  Identification Barcode
                </div>
                <div className="rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 p-3 flex flex-col items-center justify-center text-center">
                  <div className="font-mono text-base font-bold text-slate-800 dark:text-slate-200 tracking-wider">
                    {detailProduct.barcode || 'NO BARCODE'}
                  </div>
                  <div className="text-[10px] text-slate-400 mt-1">Code 128 / UPC-A Compatible</div>
                  {detailProduct.barcode && (
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard?.writeText(detailProduct.barcode);
                        setCopiedField('barcode');
                        setTimeout(() => setCopiedField(null), 2000);
                      }}
                      className="mt-2 inline-flex items-center gap-1 text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline"
                    >
                      <Copy className="h-3 w-3" />
                      <span>{copiedField === 'barcode' ? 'Copied to clipboard!' : 'Copy Barcode'}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Action Footer */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-200 dark:border-slate-800 pt-4">
              <button
                type="button"
                onClick={() => {
                  const p = detailProduct;
                  setDetailProduct(null);
                  setProductToDelete(p);
                }}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete Product (Permanently)</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const p = detailProduct;
                    setDetailProduct(null);
                    setBarcodeProduct(p);
                  }}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-200 dark:border-slate-700 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  <Barcode className="h-3.5 w-3.5" />
                  <span>Print Barcode</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    const p = detailProduct;
                    setDetailProduct(null);
                    handleOpenEditModal(p);
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 px-3.5 py-1.5 text-xs font-bold text-white shadow-subtle transition-colors"
                >
                  <Edit2 className="h-3.5 w-3.5" />
                  <span>Edit SKU & Tax Data</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDetailProduct(null)}
                  className="rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Barcode Label Modal */}
      <BarcodeLabelModal
        product={barcodeProduct}
        isOpen={Boolean(barcodeProduct)}
        onClose={() => setBarcodeProduct(null)}
      />

      {/* Delete Product Confirmation Modal */}
      {productToDelete && (
        <Modal
          isOpen={!!productToDelete}
          onClose={() => {
            if (!isDeleting) setProductToDelete(null);
          }}
          title="Delete Product from Catalog"
          subtitle="Confirm SKU removal & audit trail logging"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs text-slate-600 dark:text-slate-300">
            <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3.5 text-rose-800 dark:text-rose-200">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="h-5 w-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold text-sm">
                    Are you sure you want to delete this product?
                  </p>
                  <p className="mt-1 font-mono text-[11px] text-slate-700 dark:text-slate-300">
                    <span className="font-semibold text-rose-700 dark:text-rose-300">{productToDelete.name}</span> (SKU: {productToDelete.sku})
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-[#F4F5F8] dark:bg-[#0C1017] p-3 space-y-1.5 font-mono text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Available Stock:</span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {productToDelete.currentStock} {productToDelete.unitOfMeasure}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Category:</span>
                <span className="text-slate-700 dark:text-slate-300">{productToDelete.category}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Audit Action:</span>
                <span className="font-bold text-teal-700 dark:text-teal-400">PRODUCT REMOVED</span>
              </div>
            </div>

            <p className="text-slate-500 dark:text-slate-400 leading-relaxed">
              This product will be removed from active inventory. An immutable <b>audit trail record (product removed)</b> will be recorded into the Movement Ledger preserving historical ledger compliance.
            </p>

            <div className="flex justify-end gap-2 border-t border-slate-200 dark:border-slate-800 pt-3">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setProductToDelete(null)}
                className="rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={async () => {
                  if (productToDelete) {
                    setIsDeleting(true);
                    try {
                      await deleteProduct(productToDelete.id);
                      setImportToast({
                        type: 'success',
                        message: `Product "${productToDelete.name}" (${productToDelete.sku}) removed. Audit trail record logged.`,
                      });
                      setProductToDelete(null);
                    } finally {
                      setIsDeleting(false);
                    }
                  }
                }}
                className="rounded-lg bg-rose-600 hover:bg-rose-700 px-4 py-1.5 text-xs font-bold text-white shadow-subtle transition-colors flex items-center gap-1.5"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>{isDeleting ? 'Deleting...' : 'Confirm Delete & Log Audit'}</span>
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Bulk Delete Products Confirmation Modal */}
      {isBulkDeleteModalOpen && (
        <Modal
          isOpen={isBulkDeleteModalOpen}
          onClose={() => {
            if (!isDeleting) setIsBulkDeleteModalOpen(false);
          }}
          title="Delete Selected Products"
          subtitle="Confirm bulk SKU removal & audit trail logging"
          maxWidth="md"
        >
          <div className="space-y-4 text-xs text-slate-600 dark:text-slate-300">
            <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3.5 text-rose-800 dark:text-rose-200">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="h-5 w-5 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <p className="font-bold text-sm">
                    Are you sure you want to delete {selectedProductIds.length} selected products?
                  </p>
                  <p className="mt-1 text-slate-700 dark:text-slate-300">
                    This will remove all selected items from active catalog and record audit trail entries in the Movement Ledger.
                  </p>
                </div>
              </div>
            </div>

            <p className="text-slate-500 dark:text-slate-400 leading-relaxed">
              An immutable audit trail record (<span className="font-semibold text-rose-600 dark:text-rose-400">product removed</span>) will be stored for each item in the Movement Ledger.
            </p>

            <div className="flex justify-end gap-2 border-t border-slate-200 dark:border-slate-800 pt-3">
              <button
                type="button"
                disabled={isDeleting}
                onClick={() => setIsBulkDeleteModalOpen(false)}
                className="rounded-lg border border-slate-200 dark:border-slate-800 px-3 py-1.5 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={async () => {
                  setIsDeleting(true);
                  try {
                    await deleteProducts(selectedProductIds);
                    setImportToast({
                      type: 'success',
                      message: `Deleted ${selectedProductIds.length} products. Audit trail records logged.`,
                    });
                    setSelectedProductIds([]);
                    setIsBulkDeleteModalOpen(false);
                  } finally {
                    setIsDeleting(false);
                  }
                }}
                className="rounded-lg bg-rose-600 hover:bg-rose-700 px-4 py-1.5 text-xs font-bold text-white shadow-subtle transition-colors flex items-center gap-1.5"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>{isDeleting ? 'Deleting...' : `Confirm Delete (${selectedProductIds.length})`}</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
