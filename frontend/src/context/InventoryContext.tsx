import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  Product,
  Location,
  StockMovement,
  PurchaseOrder,
  SalesOrder,
  StockTransfer,
  AdjustmentRecord,
  CustomFieldDefinition,
  CurrencyCode,
  AdjustmentReasonCode,
  MovementType,
} from '../types/inventory';
import {
  INITIAL_PRODUCTS,
  INITIAL_LOCATIONS,
  INITIAL_LEDGER,
  INITIAL_PURCHASE_ORDERS,
  INITIAL_SALES_ORDERS,
  INITIAL_TRANSFERS,
  INITIAL_ADJUSTMENTS,
  INITIAL_CUSTOM_FIELDS,
} from '../data/mockData';
import { useAuth } from './AuthContext';
import { api } from '../services/api';

interface InventoryContextType {
  products: Product[];
  locations: Location[];
  ledger: StockMovement[];
  purchaseOrders: PurchaseOrder[];
  salesOrders: SalesOrder[];
  transfers: StockTransfer[];
  adjustments: AdjustmentRecord[];
  customFields: CustomFieldDefinition[];
  currency: CurrencyCode;
  setCurrency: (c: CurrencyCode) => void;
  selectedLocationId: string;
  setSelectedLocationId: (locId: string) => void;
  formatCurrency: (amount: number) => string;
  
  // Actions
  addProduct: (product: Omit<Product, 'id' | 'currentStock' | 'locationStock' | 'createdAt' | 'isActive'>) => void;
  bulkAddProducts: (products: Omit<Product, 'id' | 'currentStock' | 'locationStock' | 'createdAt' | 'isActive'>[]) => Promise<number>;
  updateProduct: (id: string, product: Partial<Product>) => void;
  deleteProduct: (id: string) => void;
  createPurchaseOrder: (po: Omit<PurchaseOrder, 'id' | 'poNumber' | 'status'>) => void;
  receiveGoods: (poId: string, receivedNotes?: string) => void;
  createSalesOrder: (so: Omit<SalesOrder, 'id' | 'soNumber' | 'status'>) => void;
  fulfillSalesOrder: (soId: string) => { success: boolean; error?: string };
  createTransfer: (sourceLocationId: string, targetLocationId: string, items: { productId: string; quantity: number }[], notes?: string) => void;
  createAdjustment: (productId: string, locationId: string, newStock: number, reasonCode: AdjustmentReasonCode, notes: string) => void;
  bulkAdjustStock: (adjustmentsList: { productId: string; locationId: string; delta: number; reasonCode: AdjustmentReasonCode; notes: string }[]) => void;
  addCustomField: (field: Omit<CustomFieldDefinition, 'id'>) => void;
  addLocation: (loc: Omit<Location, 'id' | 'isActive'>) => void;
}

const InventoryContext = createContext<InventoryContextType | undefined>(undefined);

export const InventoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const currentTenantId = user?.tenantId || 'default';
  const isDemo = currentTenantId === '00000000-0000-0000-0000-000000000001' || currentTenantId === 'default';

  const [products, setProducts] = useState<Product[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [ledger, setLedger] = useState<StockMovement[]>([]);
  const [purchaseOrders, setPurchaseOrders] = useState<PurchaseOrder[]>([]);
  const [salesOrders, setSalesOrders] = useState<SalesOrder[]>([]);
  const [transfers, setTransfers] = useState<StockTransfer[]>([]);
  const [adjustments, setAdjustments] = useState<AdjustmentRecord[]>([]);
  const [customFields, setCustomFields] = useState<CustomFieldDefinition[]>([]);

  const [currency, setCurrency] = useState<CurrencyCode>('USD');
  const [selectedLocationId, setSelectedLocationId] = useState<string>('all');

  // Load tenant-isolated state
  useEffect(() => {
    const pKey = `invenza_tenant_${currentTenantId}_products`;
    const lKey = `invenza_tenant_${currentTenantId}_locations`;
    const mKey = `invenza_tenant_${currentTenantId}_ledger`;
    const poKey = `invenza_tenant_${currentTenantId}_pos`;
    const soKey = `invenza_tenant_${currentTenantId}_sos`;
    const trKey = `invenza_tenant_${currentTenantId}_transfers`;
    const adjKey = `invenza_tenant_${currentTenantId}_adjustments`;
    const cfKey = `invenza_tenant_${currentTenantId}_custom_fields`;

    const savedProds = localStorage.getItem(pKey);
    const savedLocs = localStorage.getItem(lKey);
    const savedLedger = localStorage.getItem(mKey);
    const savedPos = localStorage.getItem(poKey);
    const savedSos = localStorage.getItem(soKey);
    const savedTr = localStorage.getItem(trKey);
    const savedAdj = localStorage.getItem(adjKey);
    const savedCf = localStorage.getItem(cfKey);

    // Initial load: if demo tenant, can use demo mock items; if new company tenant, STRICT CLEAN SLATE!
    setProducts(savedProds ? JSON.parse(savedProds) : isDemo ? INITIAL_PRODUCTS : []);
    setLocations(savedLocs ? JSON.parse(savedLocs) : isDemo ? INITIAL_LOCATIONS : []);
    setLedger(savedLedger ? JSON.parse(savedLedger) : isDemo ? INITIAL_LEDGER : []);
    setPurchaseOrders(savedPos ? JSON.parse(savedPos) : isDemo ? INITIAL_PURCHASE_ORDERS : []);
    setSalesOrders(savedSos ? JSON.parse(savedSos) : isDemo ? INITIAL_SALES_ORDERS : []);
    setTransfers(savedTr ? JSON.parse(savedTr) : isDemo ? INITIAL_TRANSFERS : []);
    setAdjustments(savedAdj ? JSON.parse(savedAdj) : isDemo ? INITIAL_ADJUSTMENTS : []);
    setCustomFields(savedCf ? JSON.parse(savedCf) : isDemo ? INITIAL_CUSTOM_FIELDS : []);

    // Sync from backend
    const syncBackend = async () => {
      try {
        const backendProds = await api.getProducts();
        if (backendProds && Array.isArray(backendProds)) {
          if (backendProds.length > 0 || !isDemo) {
            const mapped: Product[] = backendProds.map((bp: any) => ({
              id: bp.id,
              sku: bp.sku,
              name: bp.name,
              category: bp.category,
              unitOfMeasure: bp.unit_of_measure,
              costPrice: bp.cost_price,
              sellPrice: bp.sell_price,
              barcode: bp.barcode || '',
              reorderPoint: bp.reorder_point,
              currentStock: bp.current_stock || 0,
              locationStock: {},
              variantAttributes: bp.variant_attributes || {},
              customFields: bp.custom_fields || {},
              isActive: bp.is_active,
              createdAt: bp.created_at,
            }));
            setProducts(mapped);
          }
        }
      } catch (err) {
        console.warn('Backend products sync fallback:', err);
      }
    };

    if (currentTenantId && currentTenantId !== 'default') {
      syncBackend();
    }
  }, [currentTenantId]);

  // Sync to tenant-scoped localStorage
  useEffect(() => {
    if (!currentTenantId) return;
    localStorage.setItem(`invenza_tenant_${currentTenantId}_products`, JSON.stringify(products));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_locations`, JSON.stringify(locations));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_ledger`, JSON.stringify(ledger));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_pos`, JSON.stringify(purchaseOrders));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_sos`, JSON.stringify(salesOrders));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_transfers`, JSON.stringify(transfers));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_adjustments`, JSON.stringify(adjustments));
    localStorage.setItem(`invenza_tenant_${currentTenantId}_custom_fields`, JSON.stringify(customFields));
  }, [products, locations, ledger, purchaseOrders, salesOrders, transfers, adjustments, customFields, currentTenantId]);

  // Currency Formatter
  const formatCurrency = (amount: number): string => {
    const symbols: Record<CurrencyCode, string> = {
      USD: '$',
      EUR: '€',
      INR: '₹',
      GBP: '£',
    };
    return `${symbols[currency]}${Number(amount || 0).toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  // Helper to re-aggregate stock for a product from the immutable ledger
  const recalculateProductStock = (currentLedger: StockMovement[], productId: string, currentProds: Product[]) => {
    const movements = currentLedger.filter(m => m.productId === productId);
    let totalStock = 0;
    const locMap: Record<string, number> = {};

    movements.forEach(m => {
      let qtyDelta = 0;
      if (m.movementType === 'IN') {
        qtyDelta = m.quantity;
      } else if (m.movementType === 'OUT') {
        qtyDelta = -m.quantity;
      } else if (m.movementType === 'ADJUST') {
        qtyDelta = m.quantity; // signed delta
      } else if (m.movementType === 'TRANSFER') {
        // From source location
        qtyDelta = -m.quantity;
      }

      totalStock += qtyDelta;
      locMap[m.locationId] = (locMap[m.locationId] || 0) + qtyDelta;

      // If transfer has a target location
      if (m.movementType === 'TRANSFER' && m.targetLocationId) {
        locMap[m.targetLocationId] = (locMap[m.targetLocationId] || 0) + m.quantity;
        totalStock += m.quantity; // Neutralized overall, but reallocated
      }
    });

    return currentProds.map(p => {
      if (p.id === productId) {
        return {
          ...p,
          currentStock: Math.max(0, totalStock),
          locationStock: locMap,
        };
      }
      return p;
    });
  };

  // Add Product
  const addProduct = async (data: Omit<Product, 'id' | 'currentStock' | 'locationStock' | 'createdAt' | 'isActive'>) => {
    const newId = `prod-${Date.now()}`;
    const newProduct: Product = {
      ...data,
      id: newId,
      currentStock: 0,
      locationStock: {},
      isActive: true,
      createdAt: new Date().toISOString(),
    };
    setProducts(prev => [newProduct, ...prev]);

    try {
      await api.createProduct({
        sku: data.sku,
        name: data.name,
        category: data.category,
        unit_of_measure: data.unitOfMeasure,
        cost_price: data.costPrice,
        sell_price: data.sellPrice,
        barcode: data.barcode,
        reorder_point: data.reorderPoint,
        variant_attributes: data.variantAttributes || {},
        custom_fields: data.customFields || {},
      });
    } catch (err) {
      console.warn('Backend product creation warning:', err);
    }
  };

  // Bulk Add Products (for CSV Import)
  const bulkAddProducts = async (
    items: Omit<Product, 'id' | 'currentStock' | 'locationStock' | 'createdAt' | 'isActive'>[]
  ): Promise<number> => {
    if (!items.length) return 0;
    const timestamp = Date.now();
    const newProds: Product[] = items.map((data, idx) => ({
      ...data,
      id: `prod-${timestamp}-${idx}-${Math.random().toString(36).substring(2, 6)}`,
      currentStock: 0,
      locationStock: {},
      isActive: true,
      createdAt: new Date().toISOString(),
    }));

    setProducts(prev => [...newProds, ...prev]);

    try {
      await api.bulkCreateProducts(
        items.map(data => ({
          sku: data.sku,
          name: data.name,
          category: data.category || 'General',
          unit_of_measure: data.unitOfMeasure || 'pcs',
          cost_price: data.costPrice || 0,
          sell_price: data.sellPrice || 0,
          barcode: data.barcode || '',
          reorder_point: data.reorderPoint || 10,
          variant_attributes: data.variantAttributes || {},
          custom_fields: data.customFields || {},
        }))
      );
    } catch (err) {
      console.warn('Backend bulk import warning:', err);
    }

    return newProds.length;
  };

  // Update Product
  const updateProduct = (id: string, data: Partial<Product>) => {
    setProducts(prev => prev.map(p => p.id === id ? { ...p, ...data } : p));
  };

  // Delete Product
  const deleteProduct = (id: string) => {
    setProducts(prev => prev.filter(p => p.id !== id));
  };

  // Create Purchase Order
  const createPurchaseOrder = (data: Omit<PurchaseOrder, 'id' | 'poNumber' | 'status'>) => {
    const count = purchaseOrders.length + 1;
    const poNumber = `PO-2026-${String(count).padStart(3, '0')}`;
    const newPO: PurchaseOrder = {
      ...data,
      id: `po-${Date.now()}`,
      poNumber,
      status: 'pending',
    };
    setPurchaseOrders(prev => [newPO, ...prev]);
  };

  // Receive Goods (GRN Flow) -> auto writes to immutable ledger!
  const receiveGoods = (poId: string, receivedNotes?: string) => {
    const po = purchaseOrders.find(p => p.id === poId);
    if (!po || po.status === 'received') return;

    const newMovements: StockMovement[] = [];
    let updatedProds = [...products];

    po.items.forEach(item => {
      const prod = updatedProds.find(p => p.id === item.productId);
      const currentLocStock = prod?.locationStock[po.targetLocationId] || 0;
      const runningBal = currentLocStock + item.orderedQty;

      const movement: StockMovement = {
        id: `mov-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        timestamp: new Date().toISOString(),
        productId: item.productId,
        sku: item.sku,
        productName: item.name,
        movementType: 'IN',
        quantity: item.orderedQty,
        locationId: po.targetLocationId,
        locationName: po.targetLocationName,
        referenceType: 'PO',
        referenceId: po.poNumber,
        performedBy: 'Sarah Connor (Admin)',
        unitCost: item.unitCost,
        runningBalance: runningBal,
      };
      newMovements.push(movement);
    });

    const updatedLedger = [...newMovements, ...ledger];
    setLedger(updatedLedger);

    // Recalculate stock for all affected products
    po.items.forEach(item => {
      updatedProds = recalculateProductStock(updatedLedger, item.productId, updatedProds);
    });
    setProducts(updatedProds);

    // Update PO status
    setPurchaseOrders(prev =>
      prev.map(p =>
        p.id === poId
          ? {
              ...p,
              status: 'received',
              receivedDate: new Date().toISOString().split('T')[0],
              items: p.items.map(it => ({ ...it, receivedQty: it.orderedQty })),
              notes: receivedNotes ? `${p.notes || ''} [Received: ${receivedNotes}]` : p.notes,
            }
          : p
      )
    );
  };

  // Create Sales Order
  const createSalesOrder = (data: Omit<SalesOrder, 'id' | 'soNumber' | 'status'>) => {
    const count = salesOrders.length + 1;
    const soNumber = `SO-2026-${String(count).padStart(3, '0')}`;
    const newSO: SalesOrder = {
      ...data,
      id: `so-${Date.now()}`,
      soNumber,
      status: 'pending',
    };
    setSalesOrders(prev => [newSO, ...prev]);
  };

  // Fulfill Sales Order -> writes OUT ledger entry!
  const fulfillSalesOrder = (soId: string): { success: boolean; error?: string } => {
    const so = salesOrders.find(s => s.id === soId);
    if (!so || so.status === 'fulfilled') return { success: false, error: 'Order not found or already fulfilled' };

    // Availability validation check
    for (const item of so.items) {
      const prod = products.find(p => p.id === item.productId);
      const available = prod?.locationStock[so.sourceLocationId] || 0;
      if (available < item.orderedQty) {
        return {
          success: false,
          error: `Insufficient stock for ${item.name} at ${so.sourceLocationName}. Available: ${available}, Required: ${item.orderedQty}`,
        };
      }
    }

    const newMovements: StockMovement[] = [];
    let updatedProds = [...products];

    so.items.forEach(item => {
      const prod = updatedProds.find(p => p.id === item.productId);
      const currentLocStock = prod?.locationStock[so.sourceLocationId] || 0;
      const runningBal = Math.max(0, currentLocStock - item.orderedQty);

      const movement: StockMovement = {
        id: `mov-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        timestamp: new Date().toISOString(),
        productId: item.productId,
        sku: item.sku,
        productName: item.name,
        movementType: 'OUT',
        quantity: item.orderedQty,
        locationId: so.sourceLocationId,
        locationName: so.sourceLocationName,
        referenceType: 'SO',
        referenceId: so.soNumber,
        performedBy: 'Fulfillment Dispatch',
        unitCost: prod?.costPrice || 0,
        runningBalance: runningBal,
      };
      newMovements.push(movement);
    });

    const updatedLedger = [...newMovements, ...ledger];
    setLedger(updatedLedger);

    // Recalculate
    so.items.forEach(item => {
      updatedProds = recalculateProductStock(updatedLedger, item.productId, updatedProds);
    });
    setProducts(updatedProds);

    setSalesOrders(prev =>
      prev.map(s =>
        s.id === soId
          ? {
              ...s,
              status: 'fulfilled',
              fulfilledDate: new Date().toISOString().split('T')[0],
              items: s.items.map(it => ({ ...it, fulfilledQty: it.orderedQty })),
            }
          : s
      )
    );

    return { success: true };
  };

  // Stock Transfer between locations
  const createTransfer = (
    sourceLocationId: string,
    targetLocationId: string,
    items: { productId: string; quantity: number }[],
    notes?: string
  ) => {
    const sourceLoc = locations.find(l => l.id === sourceLocationId);
    const targetLoc = locations.find(l => l.id === targetLocationId);
    if (!sourceLoc || !targetLoc) return;

    const count = transfers.length + 1;
    const trNumber = `TR-2026-${String(count).padStart(3, '0')}`;

    const newMovements: StockMovement[] = [];
    let updatedProds = [...products];

    const transferItems = items.map(item => {
      const prod = products.find(p => p.id === item.productId);
      const prodName = prod?.name || 'Item';
      const prodSku = prod?.sku || 'SKU';

      // Paired transfer movement record
      const movement: StockMovement = {
        id: `mov-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
        timestamp: new Date().toISOString(),
        productId: item.productId,
        sku: prodSku,
        productName: prodName,
        movementType: 'TRANSFER',
        quantity: item.quantity,
        locationId: sourceLocationId,
        locationName: sourceLoc.name,
        targetLocationId: targetLocationId,
        targetLocationName: targetLoc.name,
        referenceType: 'TRANSFER',
        referenceId: trNumber,
        performedBy: 'Inventory Logistics',
        unitCost: prod?.costPrice || 0,
        runningBalance: (prod?.locationStock[sourceLocationId] || 0) - item.quantity,
      };
      newMovements.push(movement);

      return {
        productId: item.productId,
        sku: prodSku,
        name: prodName,
        quantity: item.quantity,
      };
    });

    const updatedLedger = [...newMovements, ...ledger];
    setLedger(updatedLedger);

    items.forEach(item => {
      updatedProds = recalculateProductStock(updatedLedger, item.productId, updatedProds);
    });
    setProducts(updatedProds);

    const newTransfer: StockTransfer = {
      id: `tr-${Date.now()}`,
      transferNumber: trNumber,
      sourceLocationId,
      sourceLocationName: sourceLoc.name,
      targetLocationId,
      targetLocationName: targetLoc.name,
      status: 'completed',
      date: new Date().toISOString().split('T')[0],
      items: transferItems,
      notes,
    };

    setTransfers(prev => [newTransfer, ...prev]);
  };

  // Manual Stock Adjustment with mandatory reason code
  const createAdjustment = (
    productId: string,
    locationId: string,
    newStock: number,
    reasonCode: AdjustmentReasonCode,
    notes: string
  ) => {
    const prod = products.find(p => p.id === productId);
    const loc = locations.find(l => l.id === locationId);
    if (!prod || !loc) return;

    const previousStock = prod.locationStock[locationId] || 0;
    const delta = newStock - previousStock;
    if (delta === 0) return;

    const count = adjustments.length + 1;
    const adjNumber = `ADJ-2026-${String(count).padStart(3, '0')}`;

    const newMovement: StockMovement = {
      id: `mov-${Date.now()}`,
      timestamp: new Date().toISOString(),
      productId,
      sku: prod.sku,
      productName: prod.name,
      movementType: 'ADJUST',
      quantity: delta,
      locationId,
      locationName: loc.name,
      referenceType: 'ADJUST',
      referenceId: adjNumber,
      reasonCode,
      performedBy: 'Sarah Connor (Admin)',
      unitCost: prod.costPrice,
      runningBalance: newStock,
    };

    const updatedLedger = [newMovement, ...ledger];
    setLedger(updatedLedger);

    const updatedProds = recalculateProductStock(updatedLedger, productId, products);
    setProducts(updatedProds);

    const newAdjustmentRecord: AdjustmentRecord = {
      id: `adj-${Date.now()}`,
      adjustmentNumber: adjNumber,
      locationId,
      locationName: loc.name,
      productId,
      sku: prod.sku,
      productName: prod.name,
      previousStock,
      newStock,
      delta,
      reasonCode,
      notes,
      date: new Date().toISOString().split('T')[0],
      author: 'Sarah Connor (Admin)',
    };

    setAdjustments(prev => [newAdjustmentRecord, ...prev]);
  };

  // Bulk stock adjustment
  const bulkAdjustStock = (adjustmentsList: { productId: string; locationId: string; delta: number; reasonCode: AdjustmentReasonCode; notes: string }[]) => {
    const newMovements: StockMovement[] = [];
    const newAdjRecords: AdjustmentRecord[] = [];
    let updatedProds = [...products];

    adjustmentsList.forEach((adj, idx) => {
      const prod = updatedProds.find(p => p.id === adj.productId);
      const loc = locations.find(l => l.id === adj.locationId);
      if (!prod || !loc) return;

      const previousStock = prod.locationStock[adj.locationId] || 0;
      const newStock = Math.max(0, previousStock + adj.delta);
      const adjNumber = `ADJ-2026-${String(adjustments.length + idx + 1).padStart(3, '0')}`;

      const movement: StockMovement = {
        id: `mov-${Date.now()}-${idx}`,
        timestamp: new Date().toISOString(),
        productId: adj.productId,
        sku: prod.sku,
        productName: prod.name,
        movementType: 'ADJUST',
        quantity: adj.delta,
        locationId: adj.locationId,
        locationName: loc.name,
        referenceType: 'ADJUST',
        referenceId: adjNumber,
        reasonCode: adj.reasonCode,
        performedBy: 'Sarah Connor (Admin)',
        unitCost: prod.costPrice,
        runningBalance: newStock,
      };
      newMovements.push(movement);

      newAdjRecords.push({
        id: `adj-${Date.now()}-${idx}`,
        adjustmentNumber: adjNumber,
        locationId: adj.locationId,
        locationName: loc.name,
        productId: adj.productId,
        sku: prod.sku,
        productName: prod.name,
        previousStock,
        newStock,
        delta: adj.delta,
        reasonCode: adj.reasonCode,
        notes: adj.notes,
        date: new Date().toISOString().split('T')[0],
        author: 'Sarah Connor (Admin)',
      });
    });

    const updatedLedger = [...newMovements, ...ledger];
    setLedger(updatedLedger);
    setAdjustments(prev => [...newAdjRecords, ...prev]);

    // Recalculate unique products
    const uniqueProdIds = Array.from(new Set(adjustmentsList.map(a => a.productId)));
    uniqueProdIds.forEach(pId => {
      updatedProds = recalculateProductStock(updatedLedger, pId, updatedProds);
    });
    setProducts(updatedProds);
  };

  // Add Custom Field
  const addCustomField = (field: Omit<CustomFieldDefinition, 'id'>) => {
    const newField: CustomFieldDefinition = {
      ...field,
      id: `cf-${Date.now()}`,
    };
    setCustomFields(prev => [...prev, newField]);
  };

  // Add Location
  const addLocation = async (loc: Omit<Location, 'id' | 'isActive'>) => {
    const newLoc: Location = {
      ...loc,
      id: `loc-${Date.now()}`,
      isActive: true,
    };
    setLocations(prev => [...prev, newLoc]);

    try {
      await api.createLocation({
        name: loc.name,
        code: loc.code,
        address: loc.address,
        capacity: loc.capacity,
      });
    } catch (err) {
      console.warn('Backend location creation warning:', err);
    }
  };

  return (
    <InventoryContext.Provider
      value={{
        products,
        locations,
        ledger,
        purchaseOrders,
        salesOrders,
        transfers,
        adjustments,
        customFields,
        currency,
        setCurrency,
        selectedLocationId,
        setSelectedLocationId,
        formatCurrency,
        addProduct,
        bulkAddProducts,
        updateProduct,
        deleteProduct,
        createPurchaseOrder,
        receiveGoods,
        createSalesOrder,
        fulfillSalesOrder,
        createTransfer,
        createAdjustment,
        bulkAdjustStock,
        addCustomField,
        addLocation,
      }}
    >
      {children}
    </InventoryContext.Provider>
  );
};

export const useInventory = () => {
  const context = useContext(InventoryContext);
  if (!context) {
    throw new Error('useInventory must be used within an InventoryProvider');
  }
  return context;
};
