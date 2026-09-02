import React from 'react';
import {
  LayoutDashboard,
  Building2,
  Users,
  Package,
  Layers,
  FileDown,
  FileUp,
  ArrowLeftRight,
  SlidersHorizontal,
  Warehouse,
  BarChart3,
  Settings,
  ShieldCheck,
  X,
  LogOut,
} from 'lucide-react';
import { useInventory } from '../../context/InventoryContext';
import { useAuth } from '../../context/AuthContext';

export type TabType =
  | 'dashboard'
  | 'companies'
  | 'team'
  | 'products'
  | 'ledger'
  | 'purchase_orders'
  | 'sales_orders'
  | 'transfers'
  | 'adjustments'
  | 'warehouses'
  | 'reports'
  | 'settings';

interface SidebarProps {
  currentTab: TabType;
  onSelectTab: (tab: TabType) => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  isMobileOpen = false,
  onCloseMobile,
}) => {
  const { products, purchaseOrders, salesOrders } = useInventory();
  const { user, logout, isSuperAdmin, isCompanyAdmin } = useAuth();

  const lowStockCount = products.filter((p) => p.currentStock <= p.reorderPoint).length;
  const pendingPOCount = purchaseOrders.filter((p) => p.status === 'pending').length;
  const pendingSOCount = salesOrders.filter((s) => s.status === 'pending').length;

  const enabledModules = user?.enabledModules || [
    'products', 'locations', 'orders', 'transfers', 'adjustments', 'ledger', 'reports', 'storage'
  ];

  // Dynamic Navigation Items
  let navItems: any[] = [];

  if (isSuperAdmin) {
    navItems = [
      {
        id: 'companies' as TabType,
        label: 'Tenants & Companies',
        icon: Building2,
        highlight: true,
      },
      {
        id: 'reports' as TabType,
        label: 'Platform Reports',
        icon: BarChart3,
      },
    ];
  } else {
    navItems = [
      {
        id: 'dashboard' as TabType,
        label: 'Dashboard',
        icon: LayoutDashboard,
      },
    ];

    // Company Admin Team Tab
    if (isCompanyAdmin) {
      navItems.push({
        id: 'team' as TabType,
        label: 'Team & Roles',
        icon: Users,
        highlight: true,
      });
    }

    if (enabledModules.includes('products')) {
      navItems.push({
        id: 'products' as TabType,
        label: 'Products & SKUs',
        icon: Package,
        badge: lowStockCount > 0 ? `${lowStockCount} low` : undefined,
        badgeColor: 'amber',
      });
    }

    if (enabledModules.includes('ledger')) {
      navItems.push({
        id: 'ledger' as TabType,
        label: 'Movement Ledger',
        icon: Layers,
      });
    }

    if (enabledModules.includes('orders')) {
      navItems.push(
        {
          id: 'purchase_orders' as TabType,
          label: 'Purchase Orders',
          icon: FileDown,
          badge: pendingPOCount > 0 ? `${pendingPOCount}` : undefined,
          badgeColor: 'sky',
        },
        {
          id: 'sales_orders' as TabType,
          label: 'Sales Orders',
          icon: FileUp,
          badge: pendingSOCount > 0 ? `${pendingSOCount}` : undefined,
          badgeColor: 'emerald',
        }
      );
    }

    if (enabledModules.includes('transfers')) {
      navItems.push({
        id: 'transfers' as TabType,
        label: 'Stock Transfers',
        icon: ArrowLeftRight,
      });
    }

    if (enabledModules.includes('adjustments')) {
      navItems.push({
        id: 'adjustments' as TabType,
        label: 'Adjustments',
        icon: SlidersHorizontal,
      });
    }

    if (enabledModules.includes('locations')) {
      navItems.push({
        id: 'warehouses' as TabType,
        label: 'Warehouses',
        icon: Warehouse,
      });
    }

    if (enabledModules.includes('reports')) {
      navItems.push({
        id: 'reports' as TabType,
        label: 'Reports & Valuation',
        icon: BarChart3,
      });
    }

    navItems.push({
      id: 'settings' as TabType,
      label: 'Settings & Schema',
      icon: Settings,
    });
  }

  const handleTabClick = (tabId: TabType) => {
    onSelectTab(tabId);
    if (onCloseMobile) onCloseMobile();
  };

  const sidebarContent = (
    <aside className="flex flex-col w-64 shrink-0 border-r border-slate-200/80 dark:border-slate-800/80 bg-white/90 dark:bg-slate-950/90 backdrop-blur-xl h-screen sticky top-0 transition-colors z-40">
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-5 border-b border-slate-200/80 dark:border-slate-800/80">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 text-white shadow-glow-brand font-black text-base tracking-tight">
            {isSuperAdmin ? 'I' : (user?.companyName ? user.companyName.trim().charAt(0).toUpperCase() : 'I')}
          </div>
          <div className="flex flex-col min-w-0">
            <span className="text-sm sm:text-base font-extrabold tracking-tight text-slate-900 dark:text-white truncate drop-shadow-sm">
              {isSuperAdmin ? 'Invenza Master' : user?.companyName || 'Invenza'}
            </span>
            <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-300 tracking-wider uppercase truncate">
              {isSuperAdmin ? 'Super Admin' : user?.industry || 'Enterprise IMS'}
            </span>
          </div>
        </div>

        {/* Close button on mobile */}
        {onCloseMobile && (
          <button
            onClick={onCloseMobile}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-white"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <div className="px-3 pb-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
          {isSuperAdmin ? 'Platform Management' : 'Inventory Operations'}
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => handleTabClick(item.id)}
              className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all group ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-500/10 to-purple-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100/60 dark:hover:bg-slate-900/60 border border-transparent'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon
                  className={`w-4 h-4 transition-colors ${
                    isActive
                      ? 'text-indigo-600 dark:text-indigo-400'
                      : 'text-slate-400 dark:text-slate-500 group-hover:text-slate-700 dark:group-hover:text-slate-300'
                  }`}
                />
                <span className="truncate">{item.label}</span>
              </div>

              {item.badge && (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded-md ${
                    item.badgeColor === 'amber'
                      ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                      : item.badgeColor === 'sky'
                      ? 'bg-sky-500/15 text-sky-600 dark:text-sky-400'
                      : 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* User Profile & Logout Bottom Bar */}
      <div className="p-3 border-t border-slate-200/80 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/40">
        <div className="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-slate-950 border border-slate-200/80 dark:border-slate-800/80">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold text-xs">
              {user?.fullName?.charAt(0) || 'U'}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                {user?.fullName || 'User'}
              </span>
              <span className="text-[10px] text-slate-400 truncate">
                {user?.role?.toUpperCase()}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop Sticky Sidebar */}
      <div className="hidden md:block shrink-0">
        {sidebarContent}
      </div>

      {/* Mobile Slide-out Drawer */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex animate-in fade-in duration-200">
          <div
            className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm"
            onClick={onCloseMobile}
          />
          <div className="relative z-50 animate-in slide-in-from-left duration-200">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
