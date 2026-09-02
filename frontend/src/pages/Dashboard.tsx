import React from 'react';
import {
  DollarSign,
  Package,
  AlertTriangle,
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  TrendingUp,
  Clock,
  Layers,
  Warehouse,
  ExternalLink,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { StatCard } from '../components/common/StatCard';
import { MovementBadge } from '../components/common/Badge';
import { TabType } from '../components/layout/Sidebar';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';

interface DashboardProps {
  onNavigate: (tab: TabType) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const {
    products,
    ledger,
    locations,
    purchaseOrders,
    formatCurrency,
    selectedLocationId,
  } = useInventory();

  // Filter products if a specific warehouse is selected
  const activeProducts = products.filter((p) => {
    if (selectedLocationId === 'all') return true;
    return (p.locationStock[selectedLocationId] || 0) > 0;
  });

  // KPI Calculations
  const totalValuation = activeProducts.reduce((sum, p) => {
    const qty =
      selectedLocationId === 'all'
        ? p.currentStock
        : p.locationStock[selectedLocationId] || 0;
    return sum + qty * p.costPrice;
  }, 0);

  const lowStockItems = activeProducts.filter((p) => {
    const qty =
      selectedLocationId === 'all'
        ? p.currentStock
        : p.locationStock[selectedLocationId] || 0;
    return qty <= p.reorderPoint;
  });

  // Recent movements
  const recentMovements = ledger
    .filter((m) => {
      if (selectedLocationId === 'all') return true;
      return m.locationId === selectedLocationId || m.targetLocationId === selectedLocationId;
    })
    .slice(0, 5);

  // Mock chart data for movements
  const movementTrendData = [
    { day: 'Mon', inQty: 35, outQty: 12 },
    { day: 'Tue', inQty: 10, outQty: 24 },
    { day: 'Wed', inQty: 45, outQty: 18 },
    { day: 'Thu', inQty: 20, outQty: 32 },
    { day: 'Fri', inQty: 60, outQty: 28 },
    { day: 'Sat', inQty: 15, outQty: 8 },
    { day: 'Sun', inQty: 5, outQty: 4 },
  ];

  // Category distribution
  const categoryData = [
    { name: 'Office Furniture', value: 73 },
    { name: 'Electronics', value: 144 },
    { name: 'Accessories', value: 6 },
  ];

  return (
    <div className="space-y-6">
      {/* Top Banner & Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Operations Overview
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time movement ledger aggregation & inventory health metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('purchase_orders')}
            className="flex items-center gap-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors"
          >
            <ArrowDownRight className="h-4 w-4 text-emerald-500" />
            Receive PO
          </button>
          <button
            onClick={() => onNavigate('sales_orders')}
            className="flex items-center gap-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-colors"
          >
            <ArrowUpRight className="h-4 w-4 text-rose-500" />
            Fulfill SO
          </button>
          <button
            onClick={() => onNavigate('products')}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-colors"
          >
            <Package className="h-4 w-4" />
            Manage SKUs
          </button>
        </div>
      </div>

      {/* Critical Reorder Alert Banner if low stock exists */}
      {lowStockItems.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-900 dark:text-amber-200">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-600 dark:text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <div className="font-bold text-sm">
                {lowStockItems.length} Products at or below Reorder Threshold
              </div>
              <div className="text-xs text-amber-700 dark:text-amber-300">
                {lowStockItems.map((p) => `${p.name} (${p.currentStock} left)`).join(', ')}
              </div>
            </div>
          </div>
          <button
            onClick={() => onNavigate('purchase_orders')}
            className="shrink-0 rounded-xl bg-amber-600 hover:bg-amber-700 px-3.5 py-2 text-xs font-semibold text-white transition-colors"
          >
            Restock via PO
          </button>
        </div>
      )}

      {/* 4 Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Stock Asset Valuation"
          value={formatCurrency(totalValuation)}
          subtitle="Derived dynamically from ledger"
          icon={DollarSign}
          colorScheme="indigo"
          trend={{ value: '4.2% vs last week', isPositive: true }}
        />
        <StatCard
          title="Tracked SKUs"
          value={activeProducts.length}
          subtitle="Multi-variant master catalog"
          icon={Package}
          colorScheme="sky"
          badge="Active"
        />
        <StatCard
          title="Low Stock Warning"
          value={lowStockItems.length}
          subtitle="Needs replenishment"
          icon={AlertTriangle}
          colorScheme={lowStockItems.length > 0 ? 'amber' : 'emerald'}
          trend={{
            value: lowStockItems.length > 0 ? 'Action required' : 'Optimal',
            isPositive: lowStockItems.length === 0,
          }}
        />
        <StatCard
          title="Ledger Movements"
          value={ledger.length}
          subtitle="Immutable transactions logged"
          icon={Activity}
          colorScheme="emerald"
          badge="Audit Safe"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Movement Volume Area Chart */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Stock Movement Flow (Receipts vs Dispatches)
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Weekly velocity of items flowing through the immutable ledger
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs font-semibold">
              <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                <span className="h-2 w-2 rounded-full bg-emerald-500"></span> Stock IN
              </span>
              <span className="flex items-center gap-1.5 text-rose-600 dark:text-rose-400">
                <span className="h-2 w-2 rounded-full bg-rose-500"></span> Stock OUT
              </span>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={movementTrendData}>
                <defs>
                  <linearGradient id="colorIn" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorOut" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#f43f5e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.75rem',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="inQty"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorIn)"
                  name="Stock In"
                />
                <Area
                  type="monotone"
                  dataKey="outQty"
                  stroke="#f43f5e"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorOut)"
                  name="Stock Out"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Warehouse Distribution Cards */}
        <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Warehouse Stock Distribution
              </h3>
              <Warehouse className="h-4 w-4 text-indigo-500" />
            </div>

            <div className="space-y-4">
              {locations.map((loc) => {
                const locUnits = products.reduce(
                  (sum, p) => sum + (p.locationStock[loc.id] || 0),
                  0
                );
                const capacityPercent = Math.min(
                  100,
                  Math.round((locUnits / (loc.capacity || 10000)) * 100)
                );

                return (
                  <div key={loc.id} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-slate-800 dark:text-slate-200">{loc.name}</span>
                      <span className="font-mono text-indigo-600 dark:text-indigo-400">
                        {locUnits} units
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                        style={{ width: `${Math.max(5, capacityPercent)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] text-slate-400">
                      <span>{loc.code}</span>
                      <span>{capacityPercent}% utilized</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <button
            onClick={() => onNavigate('transfers')}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl border border-indigo-500/20 bg-indigo-500/5 hover:bg-indigo-500/10 py-2.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400 transition-colors"
          >
            <span>Initiate Inter-Warehouse Transfer</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Live Ledger Activity Feed Preview */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-indigo-500" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Live Stock Movement Stream (Ledger)
            </h3>
          </div>
          <button
            onClick={() => onNavigate('ledger')}
            className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
          >
            View Full Audit Trail →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 uppercase font-semibold text-[10px]">
                <th className="pb-3">Timestamp</th>
                <th className="pb-3">Type</th>
                <th className="pb-3">Product / SKU</th>
                <th className="pb-3">Warehouse</th>
                <th className="pb-3 text-right">Quantity Delta</th>
                <th className="pb-3">Reference</th>
                <th className="pb-3">Operator</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {recentMovements.map((m) => (
                <tr key={m.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                    {new Date(m.timestamp).toLocaleDateString()} {new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td className="py-3">
                    <MovementBadge type={m.movementType} />
                  </td>
                  <td className="py-3">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      {m.productName}
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">{m.sku}</div>
                  </td>
                  <td className="py-3 text-slate-600 dark:text-slate-300">
                    {m.locationName}
                    {m.targetLocationName && ` → ${m.targetLocationName}`}
                  </td>
                  <td className="py-3 text-right font-mono font-bold">
                    <span
                      className={
                        m.movementType === 'IN'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : m.movementType === 'OUT'
                          ? 'text-rose-600 dark:text-rose-400'
                          : 'text-amber-600 dark:text-amber-400'
                      }
                    >
                      {m.movementType === 'IN'
                        ? `+${m.quantity}`
                        : m.movementType === 'OUT'
                        ? `-${m.quantity}`
                        : m.quantity > 0
                        ? `+${m.quantity}`
                        : `${m.quantity}`}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className="rounded bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-[11px] font-mono text-slate-700 dark:text-slate-300 font-medium">
                      {m.referenceId}
                    </span>
                  </td>
                  <td className="py-3 text-slate-500 dark:text-slate-400 text-[11px]">
                    {m.performedBy}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
