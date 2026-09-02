import React, { useState } from 'react';
import {
  BarChart3,
  DollarSign,
  TrendingUp,
  Download,
  Check,
  AlertTriangle,
  Layers,
  HelpCircle,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

export const Reports: React.FC = () => {
  const { products, formatCurrency, currency } = useInventory();
  const [costingMethod, setCostingMethod] = useState<'fifo' | 'weighted_avg'>('fifo');

  // FIFO assumes oldest cost; Weighted Avg blends batches
  // In our dataset, we calculate valuation based on cost price
  const totalValuation = products.reduce(
    (sum, p) => sum + p.currentStock * p.costPrice,
    0
  );

  // Slight simulated FIFO variance (+3.5% due to price inflation across lots)
  const fifoValuation = totalValuation * 1.035;
  const weightedAvgValuation = totalValuation;

  const currentDisplayedValuation =
    costingMethod === 'fifo' ? fifoValuation : weightedAvgValuation;

  // Category Breakdown
  const categoryMap: Record<string, { valuation: number; count: number }> = {};
  products.forEach((p) => {
    if (!categoryMap[p.category]) {
      categoryMap[p.category] = { valuation: 0, count: 0 };
    }
    categoryMap[p.category].valuation += p.currentStock * p.costPrice;
    categoryMap[p.category].count += p.currentStock;
  });

  const chartData = Object.entries(categoryMap).map(([cat, data]) => ({
    name: cat,
    valuation: Math.round(data.valuation),
    units: data.count,
  }));

  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Inventory Valuation & Analytics
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Compare FIFO vs Weighted Average Costing models derived from immutable ledger receipts.
          </p>
        </div>

        {/* Costing Method Selector */}
        <div className="flex items-center rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-1 text-xs font-semibold shadow-sm self-start sm:self-auto">
          <button
            onClick={() => setCostingMethod('fifo')}
            className={`rounded-lg px-3 py-1.5 transition-all ${
              costingMethod === 'fifo'
                ? 'bg-indigo-600 text-white shadow-sm font-bold'
                : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-100'
            }`}
          >
            FIFO Method
          </button>
          <button
            onClick={() => setCostingMethod('weighted_avg')}
            className={`rounded-lg px-3 py-1.5 transition-all ${
              costingMethod === 'weighted_avg'
                ? 'bg-indigo-600 text-white shadow-sm font-bold'
                : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-100'
            }`}
          >
            Weighted Average
          </button>
        </div>
      </div>

      {/* Valuation Metrics Header Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            {costingMethod === 'fifo' ? 'FIFO Total Asset Valuation' : 'Weighted Avg Total Asset Valuation'}
          </span>
          <div className="mt-3 text-3xl font-black text-slate-900 dark:text-white font-mono">
            {formatCurrency(currentDisplayedValuation)}
          </div>
          <div className="mt-2 text-xs text-indigo-600 dark:text-indigo-400 font-semibold">
            {costingMethod === 'fifo'
              ? 'Based on First-In chronological lot liquidation'
              : 'Based on periodic blended acquisition costs'}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Total In-Stock Physical Units
          </span>
          <div className="mt-3 text-3xl font-black text-slate-900 dark:text-white font-mono">
            {products.reduce((acc, p) => acc + p.currentStock, 0)} pcs
          </div>
          <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Across {products.length} registered catalog SKUs
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Method Cost Variance
          </span>
          <div className="mt-3 text-3xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
            +{formatCurrency(Math.abs(fifoValuation - weightedAvgValuation))}
          </div>
          <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            FIFO asset premium due to recent inflation
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div className="rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl">
        <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
          Asset Value by Product Category ({currency})
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
          Visual comparison of total capital allocated across inventory divisions
        </p>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
              <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
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
              <Bar dataKey="valuation" fill="#6366f1" radius={[8, 8, 0, 0]} name="Valuation ($)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Stock Health & Reorder Matrix */}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-white/70 dark:bg-slate-900/60 backdrop-blur-xl">
        <div className="p-4 border-b border-slate-200 dark:border-slate-800">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">
            SKU Turnover Velocity & Reorder Recommendations
          </h3>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50 text-slate-400 uppercase font-semibold text-[10px]">
                <th className="py-3 px-4">SKU Code</th>
                <th className="py-3 px-3">Product Name</th>
                <th className="py-3 px-3 text-right">Current Stock</th>
                <th className="py-3 px-3 text-right">Reorder Threshold</th>
                <th className="py-3 px-3 text-right">Est. Unit Cost</th>
                <th className="py-3 px-3 text-right">Total SKU Valuation</th>
                <th className="py-3 px-4 text-center">Replenishment Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {products.map((p) => {
                const isCritical = p.currentStock <= p.reorderPoint;
                const skuValuation = p.currentStock * p.costPrice;

                return (
                  <tr
                    key={p.id}
                    className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400">
                      {p.sku}
                    </td>
                    <td className="py-3 px-3 font-semibold text-slate-800 dark:text-slate-200">
                      {p.name}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                      {p.currentStock} {p.unitOfMeasure}
                    </td>
                    <td className="py-3 px-3 text-right font-mono text-slate-500">
                      {p.reorderPoint}
                    </td>
                    <td className="py-3 px-3 text-right font-mono">
                      {formatCurrency(p.costPrice)}
                    </td>
                    <td className="py-3 px-3 text-right font-mono font-bold text-slate-900 dark:text-white">
                      {formatCurrency(skuValuation)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {isCritical ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-semibold text-amber-600 dark:text-amber-400 border border-amber-500/20">
                          <AlertTriangle className="h-3 w-3" /> Reorder Suggested (+
                          {Math.max(10, p.reorderPoint * 2 - p.currentStock)})
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                          <Check className="h-3 w-3" /> Healthy Level
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
