export type MovementType = 'IN' | 'OUT' | 'ADJUST' | 'TRANSFER';

export type AdjustmentReasonCode = 'damage' | 'loss' | 'miscount' | 'return' | 'audit';

export interface Location {
  id: string;
  name: string;
  code: string;
  address?: string;
  capacity?: number;
  isActive: boolean;
}

export interface CustomFieldDefinition {
  id: string;
  name: string;
  key: string;
  type: 'text' | 'number' | 'date' | 'select';
  options?: string[];
  required: boolean;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  unitOfMeasure: string;
  costPrice: number;
  sellPrice: number;
  barcode: string;
  reorderPoint: number;
  variantAttributes: Record<string, string>; // e.g. { Color: "Midnight Blue", Size: "XL" }
  customFields: Record<string, any>;         // e.g. { batchNumber: "B-2026-X", expiryDate: "2027-12-31" }
  currentStock: number;                      // Aggregated from ledger
  locationStock: Record<string, number>;     // Aggregated per location { locationId: count }
  isActive: boolean;
  createdAt: string;
}

export interface StockMovement {
  id: string;
  timestamp: string;
  productId: string;
  sku: string;
  productName: string;
  movementType: MovementType;
  quantity: number;                          // Positive number; movementType dictates sign
  locationId: string;
  locationName: string;
  targetLocationId?: string;                 // For transfers
  targetLocationName?: string;
  referenceType: 'PO' | 'SO' | 'ADJUST' | 'TRANSFER' | 'INITIAL';
  referenceId: string;
  reasonCode?: AdjustmentReasonCode | string;
  performedBy: string;
  unitCost: number;
  runningBalance: number;
}

export interface POLineItem {
  productId: string;
  sku: string;
  name: string;
  orderedQty: number;
  receivedQty: number;
  unitCost: number;
}

export interface PurchaseOrder {
  id: string;
  poNumber: string;
  supplierName: string;
  status: 'draft' | 'pending' | 'received' | 'cancelled';
  targetLocationId: string;
  targetLocationName: string;
  orderDate: string;
  receivedDate?: string;
  items: POLineItem[];
  totalAmount: number;
  notes?: string;
}

export interface SOLineItem {
  productId: string;
  sku: string;
  name: string;
  orderedQty: number;
  fulfilledQty: number;
  unitPrice: number;
}

export interface SalesOrder {
  id: string;
  soNumber: string;
  customerName: string;
  status: 'pending' | 'fulfilled' | 'cancelled';
  sourceLocationId: string;
  sourceLocationName: string;
  orderDate: string;
  fulfilledDate?: string;
  items: SOLineItem[];
  totalAmount: number;
  notes?: string;
}

export interface StockTransfer {
  id: string;
  transferNumber: string;
  sourceLocationId: string;
  sourceLocationName: string;
  targetLocationId: string;
  targetLocationName: string;
  status: 'completed' | 'in_transit';
  date: string;
  items: {
    productId: string;
    sku: string;
    name: string;
    quantity: number;
  }[];
  notes?: string;
}

export interface AdjustmentRecord {
  id: string;
  adjustmentNumber: string;
  locationId: string;
  locationName: string;
  productId: string;
  sku: string;
  productName: string;
  previousStock: number;
  newStock: number;
  delta: number;
  reasonCode: AdjustmentReasonCode;
  notes: string;
  date: string;
  author: string;
}

export interface WebhookConfig {
  id: string;
  url: string;
  events: ('stock.low' | 'stock.movement' | 'po.received' | 'so.fulfilled')[];
  isActive: boolean;
  secret: string;
}

export type CurrencyCode = 'USD' | 'EUR' | 'INR' | 'GBP';
