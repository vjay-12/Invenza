import React, { useState, useEffect } from 'react';
import {
  IconDashboard,
  IconBuilding,
  IconUsers,
  IconPackage,
  IconLayers,
  IconFileDown,
  IconFileUp,
  IconArrowLeftRight,
  IconSlidersHorizontal,
  IconWarehouse,
  IconBarChart3,
  IconSettings,
  IconFileText,
  IconX,
  IconShieldCheck,
  IconIndianRupee,
  IconMessageCircle,
} from '../icons';
import { useInventory } from '../../context/InventoryContext';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../services/api';

export type TabType =
  | 'home'
  | 'dashboard'
  | 'companies'
  | 'leads'
  | 'safeguards'
  | 'roles'
  | 'billing'
  | 'team'
  | 'products'
  | 'ledger'
  | 'purchase_orders'
  | 'sales_orders'
  | 'invoices'
  | 'transfers'
  | 'adjustments'
  | 'warehouses'
  | 'reports'
  | 'settings'
  | 'terms'
  | 'privacy'
  | 'profile';

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
  const { products, purchaseOrders, salesOrders, taxConfig } = useInventory();
  const { user, isSuperAdmin, isCompanyAdmin } = useAuth();

  const [newLeadsCount, setNewLeadsCount] = useState<number>(0);
  const [pendingSafeguardsCount, setPendingSafeguardsCount] = useState<number>(0);

  useEffect(() => {
    if (isSuperAdmin) {
      const fetchBadges = async () => {
        try {
          const [leads, reqs] = await Promise.all([
            api.getLeads('new'),
            api.getSecurityRequests('pending'),
          ]);
          if (Array.isArray(leads)) {
            setNewLeadsCount(leads.length);
          }
          if (Array.isArray(reqs)) {
            setPendingSafeguardsCount(reqs.length);
          }
        } catch {
          // ignore error
        }
      };
      fetchBadges();
      const handleRefresh = () => fetchBadges();
      window.addEventListener('invenza_notifications_refresh', handleRefresh);
      window.addEventListener('focus', handleRefresh);
      const interval = setInterval(fetchBadges, 15000);
      return () => {
        window.removeEventListener('invenza_notifications_refresh', handleRefresh);
        window.removeEventListener('focus', handleRefresh);
        clearInterval(interval);
      };
    }
  }, [isSuperAdmin]);

  const lowStockCount = products.filter((p) => p.currentStock <= p.reorderPoint && p.currentStock > 0).length;
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
        icon: IconBuilding,
      },
      {
        id: 'leads' as TabType,
        label: 'Leads & Quotes',
        icon: IconMessageCircle,
        badge: newLeadsCount > 0 ? `${newLeadsCount} New` : undefined,
      },
      {
        id: 'safeguards' as TabType,
        label: 'Security Safeguards',
        icon: IconShieldCheck,
        badge: pendingSafeguardsCount > 0 ? `${pendingSafeguardsCount} Pending` : undefined,
      },
      {
        id: 'roles' as TabType,
        label: 'Role Management',
        icon: IconUsers,
      },
      {
        id: 'billing' as TabType,
        label: 'Billing',
        icon: IconIndianRupee,
      },
      {
        id: 'reports' as TabType,
        label: 'Platform Reports',
        icon: IconBarChart3,
      },
    ];
  } else {
    navItems = [
      {
        id: 'dashboard' as TabType,
        label: 'Dashboard',
        icon: IconDashboard,
      },
    ];

    if (isCompanyAdmin) {
      navItems.push({
        id: 'team' as TabType,
        label: 'Team & Roles',
        icon: IconUsers,
      });
    }

    if (enabledModules.includes('products')) {
      navItems.push({
        id: 'products' as TabType,
        label: 'Products & SKUs',
        icon: IconPackage,
        badge: lowStockCount > 0 ? `${lowStockCount} low` : undefined,
      });
    }

    if (enabledModules.includes('ledger')) {
      navItems.push({
        id: 'ledger' as TabType,
        label: 'Movement Ledger',
        icon: IconLayers,
      });
    }

    if (enabledModules.includes('orders')) {
      navItems.push(
        {
          id: 'purchase_orders' as TabType,
          label: 'Purchase Orders',
          icon: IconFileDown,
          badge: pendingPOCount > 0 ? `${pendingPOCount}` : undefined,
        },
        {
          id: 'sales_orders' as TabType,
          label: 'Sales Orders',
          icon: IconFileUp,
          badge: pendingSOCount > 0 ? `${pendingSOCount}` : undefined,
        },
        {
          id: 'invoices' as TabType,
          label: 'Invoices',
          icon: IconFileText,
        }
      );
    }

    if (enabledModules.includes('transfers')) {
      navItems.push({
        id: 'transfers' as TabType,
        label: 'Stock Transfers',
        icon: IconArrowLeftRight,
      });
    }

    if (enabledModules.includes('adjustments')) {
      navItems.push({
        id: 'adjustments' as TabType,
        label: 'Adjustments',
        icon: IconSlidersHorizontal,
      });
    }

    if (enabledModules.includes('locations')) {
      navItems.push({
        id: 'warehouses' as TabType,
        label: 'Warehouses',
        icon: IconWarehouse,
      });
    }

    if (enabledModules.includes('reports')) {
      navItems.push({
        id: 'reports' as TabType,
        label: 'Reports & Valuation',
        icon: IconBarChart3,
      });
    }

    navItems.push({
      id: 'settings' as TabType,
      label: 'Settings & Schema',
      icon: IconSettings,
    });
  }

  const handleTabClick = (tabId: TabType) => {
    onSelectTab(tabId);
    if (onCloseMobile) onCloseMobile();
  };

  const sidebarContent = (
    <aside className="flex flex-col w-[268px] shrink-0 border-r border-slate-200 dark:border-[#16202E] bg-[#E8ECF2] dark:bg-[#090E17] text-slate-900 dark:text-slate-100 h-full transition-colors z-40 select-none">
      {/* Bold Wordmark Logo - Aligned to Header Height */}
      <div className="h-16 sm:h-18 pt-2.5 sm:pt-3 pb-1 flex items-center justify-between px-5 sm:px-6">
        <button
          type="button"
          onClick={() => handleTabClick(isSuperAdmin ? 'companies' : 'dashboard')}
          className="text-left group focus:outline-none"
        >
          <div className="flex items-center gap-1.5">
            <span className="text-xl font-black tracking-tight text-slate-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors font-sans">
              Invenza
            </span>
            <span className="h-2 w-2 rounded-full bg-teal-500 dark:bg-teal-400 mt-0.5 shrink-0 shadow-[0_0_8px_rgba(45,212,191,0.6)]" />
          </div>
          <div className="text-[9px] font-mono tracking-widest text-slate-500 uppercase truncate">
            {isSuperAdmin ? 'Master Platform' : user?.companyName || 'Multi-Warehouse IMS'}
          </div>
        </button>

        {/* Close button on mobile */}
        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="md:hidden p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
            aria-label="Close sidebar"
          >
            <IconX className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation Links — Typography-Led with Balanced Spacing */}
      <div className="flex-1 overflow-y-auto px-5 sm:px-6 py-3.5 space-y-3.5">
        <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 dark:text-slate-600 mb-2">
          {isSuperAdmin ? 'Platform Management' : 'Inventory Operations'}
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleTabClick(item.id)}
              className={`w-full text-left py-1.5 px-2.5 -mx-2.5 rounded-lg flex items-center justify-between group transition-colors focus:outline-none ${
                isActive
                  ? 'bg-teal-500/10 dark:bg-teal-500/10'
                  : 'hover:bg-slate-200/60 dark:hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <Icon
                  className={`w-3.5 h-3.5 shrink-0 transition-colors ${
                    isActive
                      ? 'text-teal-600 dark:text-teal-400'
                      : 'text-slate-400 dark:text-slate-600 group-hover:text-slate-600 dark:group-hover:text-slate-400'
                  }`}
                />
                <span
                  className={`text-sm tracking-tight transition-colors truncate ${
                    isActive
                      ? 'text-teal-700 dark:text-teal-400 font-bold'
                      : 'text-slate-600 dark:text-slate-400 font-medium group-hover:text-slate-900 dark:group-hover:text-slate-200'
                  }`}
                >
                  {item.label}
                </span>
              </div>

              <div className="flex items-center gap-2 shrink-0 ml-2">
                {item.badge && (
                  <span className="text-[11px] font-mono font-semibold px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-800 dark:text-amber-400/90 border border-amber-500/25">
                    {item.badge}
                  </span>
                )}
              </div>
            </button>
          );
        })}

      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop Sticky Sidebar */}
      <div className="hidden md:block shrink-0 h-full">
        {sidebarContent}
      </div>

      {/* Mobile Slide-out Drawer */}
      {isMobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex animate-in fade-in duration-200">
          <div
            className="fixed inset-0 bg-slate-950/70"
            onClick={onCloseMobile}
          />
          <div className="relative z-50 animate-in slide-in-from-left duration-200 h-full">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
};
