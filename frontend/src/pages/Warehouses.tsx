import React, { useState } from 'react';
import {
  Warehouse,
  Plus,
  MapPin,
  Package,
  Layers,
  ArrowLeftRight,
  CheckCircle2,
} from 'lucide-react';
import { useInventory } from '../context/InventoryContext';
import { Modal } from '../components/common/Modal';

export const Warehouses: React.FC = () => {
  const {
    locations,
    products,
    addLocation,
    selectedLocationId,
    setSelectedLocationId,
  } = useInventory();

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [address, setAddress] = useState('');
  const [capacity, setCapacity] = useState('10000');

  const handleAddWarehouseSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !code) return;

    addLocation({
      name,
      code: code.toUpperCase().trim(),
      address,
      capacity: parseInt(capacity, 10) || 10000,
    });

    setIsAddModalOpen(false);
    setName('');
    setCode('');
    setAddress('');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Multi-Warehouse & Storage Locations
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
            Architected for multi-location operations from day one. Track real-time distribution and
            capacity utilization.
          </p>
        </div>

        <button
          onClick={() => setIsAddModalOpen(true)}
          className="flex items-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20 transition-colors self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          Add Warehouse Location
        </button>
      </div>

      {/* Warehouse Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {locations.map((loc) => {
          // Total items in this warehouse
          const totalUnits = products.reduce(
            (sum, p) => sum + (p.locationStock[loc.id] || 0),
            0
          );
          const activeSKUsCount = products.filter(
            (p) => (p.locationStock[loc.id] || 0) > 0
          ).length;
          const capacityPercent = Math.min(
            100,
            Math.round((totalUnits / (loc.capacity || 10000)) * 100)
          );
          const isCurrentActive = selectedLocationId === loc.id;

          return (
            <div
              key={loc.id}
              className={`rounded-2xl border bg-white/70 dark:bg-slate-900/60 p-6 backdrop-blur-xl card-hover-effect flex flex-col justify-between ${
                isCurrentActive
                  ? 'border-indigo-500 ring-2 ring-indigo-500/20 shadow-glow-brand'
                  : 'border-slate-200/80 dark:border-slate-800'
              }`}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                      <Warehouse className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900 dark:text-white">{loc.name}</div>
                      <span className="font-mono text-xs font-bold text-indigo-600 dark:text-indigo-400">
                        {loc.code}
                      </span>
                    </div>
                  </div>

                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <CheckCircle2 className="h-3 w-3" /> Active
                  </span>
                </div>

                {loc.address && (
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
                    <MapPin className="h-3.5 w-3.5 shrink-0" />
                    <span>{loc.address}</span>
                  </div>
                )}

                {/* Metrics */}
                <div className="mt-6 grid grid-cols-2 gap-3 border-t border-slate-100 dark:border-slate-800/80 pt-4">
                  <div>
                    <div className="text-[10px] uppercase font-bold text-slate-400">Stored Units</div>
                    <div className="text-lg font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                      {totalUnits} pcs
                    </div>
                  </div>

                  <div>
                    <div className="text-[10px] uppercase font-bold text-slate-400">Distinct SKUs</div>
                    <div className="text-lg font-bold font-mono text-slate-900 dark:text-white mt-0.5">
                      {activeSKUsCount}
                    </div>
                  </div>
                </div>

                {/* Capacity Meter */}
                <div className="mt-4 space-y-1.5">
                  <div className="flex justify-between text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                    <span>Capacity Utilization</span>
                    <span>{capacityPercent}%</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${Math.max(5, capacityPercent)}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>0</span>
                    <span>Max {loc.capacity || 10000}</span>
                  </div>
                </div>
              </div>

              {/* Action */}
              <div className="mt-6 pt-4 border-t border-slate-100 dark:border-slate-800">
                <button
                  onClick={() =>
                    setSelectedLocationId(isCurrentActive ? 'all' : loc.id)
                  }
                  className={`w-full py-2 rounded-xl text-xs font-semibold transition-all ${
                    isCurrentActive
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                  }`}
                >
                  {isCurrentActive ? 'Active Filter Applied (Click to Clear)' : 'Filter System to this Location'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Warehouse Modal */}
      <Modal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        title="Add New Warehouse Location"
        subtitle="Expands multi-location distribution network"
        maxWidth="md"
      >
        <form onSubmit={handleAddWarehouseSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Warehouse Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. South Texas Fulfillment Center"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Facility Code *
              </label>
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. STX-04"
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono uppercase focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Storage Capacity (Units)
              </label>
              <input
                type="number"
                value={capacity}
                onChange={(e) => setCapacity(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs font-mono focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Street Address & Postal Code
            </label>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="e.g. 100 Industrial Parkway, Austin, TX"
              className="w-full rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 px-3 py-2 text-xs focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={() => setIsAddModalOpen(false)}
              className="rounded-xl border border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-xl bg-indigo-600 hover:bg-indigo-700 px-5 py-2 text-xs font-semibold text-white shadow-md shadow-indigo-600/20"
            >
              Add Warehouse
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
