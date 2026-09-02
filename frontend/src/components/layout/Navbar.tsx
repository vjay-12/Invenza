import React, { useState, useRef, useEffect } from 'react';
import {
  Search,
  Warehouse,
  Sun,
  Moon,
  Bell,
  Sparkles,
  Command,
  ChevronDown,
  Menu,
  LogOut,
  Shield,
  Check,
} from 'lucide-react';
import { useInventory } from '../../context/InventoryContext';
import { useTheme } from '../../context/ThemeContext';
import { useAuth } from '../../context/AuthContext';
import { CurrencyCode } from '../../types/inventory';

interface NavbarProps {
  onOpenSearch: () => void;
  onOpenChat: () => void;
  onToggleMobileSidebar?: () => void;
}

const CURRENCIES: { code: CurrencyCode; symbol: string; label: string }[] = [
  { code: 'USD', symbol: '$', label: 'US Dollar' },
  { code: 'EUR', symbol: '€', label: 'Euro' },
  { code: 'INR', symbol: '₹', label: 'Indian Rupee' },
  { code: 'GBP', symbol: '£', label: 'British Pound' },
];

export const Navbar: React.FC<NavbarProps> = ({
  onOpenSearch,
  onOpenChat,
  onToggleMobileSidebar,
}) => {
  const {
    locations,
    selectedLocationId,
    setSelectedLocationId,
    currency,
    setCurrency,
    products,
  } = useInventory();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isCurrencyOpen, setIsCurrencyOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const currencyMenuRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (currencyMenuRef.current && !currencyMenuRef.current.contains(e.target as Node)) {
        setIsCurrencyOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Low stock counter for alert badge
  const lowStockCount = products.filter((p) => p.currentStock <= p.reorderPoint).length;

  const currentCurrencyInfo =
    CURRENCIES.find((c) => c.code === currency) || CURRENCIES[0];

  const initials = user?.fullName
    ? user.fullName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : 'AD';

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-200/80 dark:border-slate-800/80 bg-white/80 dark:bg-slate-950/80 px-4 sm:px-6 backdrop-blur-xl transition-colors">
      {/* Left Section: Mobile Toggle, Search & Warehouse Selector */}
      <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle menu"
          className="lg:hidden flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <Menu className="h-4 w-4" />
        </button>

        {/* Global Quick Search Pill */}
        <button
          onClick={onOpenSearch}
          className="flex h-9 w-44 sm:w-56 md:w-64 items-center justify-between rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 px-3 text-xs text-slate-400 hover:border-slate-300 dark:hover:border-slate-700 hover:text-slate-600 dark:hover:text-slate-300 transition-all shadow-sm"
        >
          <div className="flex items-center gap-2 min-w-0 truncate">
            <Search className="h-3.5 w-3.5 shrink-0 text-slate-400" />
            <span className="truncate">Search SKUs, orders...</span>
          </div>
          <kbd className="hidden sm:flex items-center gap-0.5 rounded-md bg-slate-200/70 dark:bg-slate-800 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500 dark:text-slate-400">
            <Command className="h-2.5 w-2.5" /> K
          </kbd>
        </button>

        {/* Multi-Warehouse Selector Dropdown */}
        <div className="relative hidden md:flex items-center">
          <Warehouse className="absolute left-2.5 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
          <select
            value={selectedLocationId}
            onChange={(e) => setSelectedLocationId(e.target.value)}
            className="h-9 pl-8 pr-7 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 text-slate-700 dark:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 appearance-none cursor-pointer max-w-[190px] truncate transition-colors"
          >
            <option value="all">All Warehouses</option>
            {locations.map((loc) => (
              <option key={loc.id} value={loc.id} className="bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200">
                {loc.code} — {loc.name}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
        </div>
      </div>

      {/* Right Section: Currency Dropdown, Copilot, Theme, Alerts, User Profile */}
      <div className="flex items-center gap-2 sm:gap-2.5">
        {/* Currency Dropdown Selector */}
        <div className="relative" ref={currencyMenuRef}>
          <button
            type="button"
            onClick={() => setIsCurrencyOpen(!isCurrencyOpen)}
            className="flex h-9 items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 px-2.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all shadow-sm"
            title="Select Currency"
          >
            <span className="font-bold text-indigo-600 dark:text-indigo-400">
              {currentCurrencyInfo.symbol}
            </span>
            <span className="text-xs">{currentCurrencyInfo.code}</span>
            <ChevronDown
              className={`h-3 w-3 text-slate-400 transition-transform duration-150 ${
                isCurrencyOpen ? 'rotate-180' : ''
              }`}
            />
          </button>

          {isCurrencyOpen && (
            <div className="absolute right-0 mt-1.5 w-44 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-1.5 shadow-xl backdrop-blur-xl z-50 animate-in fade-in slide-in-from-top-1 duration-150">
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                Display Currency
              </div>
              <div className="space-y-0.5 mt-0.5">
                {CURRENCIES.map((c) => {
                  const isSelected = currency === c.code;
                  return (
                    <button
                      key={c.code}
                      onClick={() => {
                        setCurrency(c.code);
                        setIsCurrencyOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                        isSelected
                          ? 'bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 font-bold'
                          : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-slate-100 dark:bg-slate-800 text-[11px] font-bold text-slate-600 dark:text-slate-300">
                          {c.symbol}
                        </span>
                        <span>{c.code}</span>
                        <span className="text-[10px] text-slate-400 font-normal">({c.label})</span>
                      </div>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400 shrink-0 ml-1" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* AI Assistant Button Trigger */}
        <button
          onClick={onOpenChat}
          className="flex h-9 items-center gap-1.5 rounded-xl bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-indigo-500/10 hover:from-indigo-500/20 hover:to-purple-500/20 border border-indigo-500/25 px-2.5 sm:px-3 text-xs font-semibold text-indigo-600 dark:text-indigo-400 transition-all shadow-sm group"
        >
          <Sparkles className="h-3.5 w-3.5 text-indigo-500 group-hover:scale-110 transition-transform" />
          <span className="hidden sm:inline">Invenza Copilot</span>
        </button>

        {/* Vertical Divider */}
        <div className="h-5 w-px bg-slate-200 dark:border-slate-800 dark:bg-slate-800 hidden sm:block mx-0.5" />

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          aria-label="Toggle Theme"
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
        >
          {theme === 'dark' ? (
            <Sun className="h-4 w-4 text-amber-400" />
          ) : (
            <Moon className="h-4 w-4 text-slate-600" />
          )}
        </button>

        {/* Notifications & Low Stock Alert */}
        <div className="relative">
          <button
            aria-label="Alerts"
            className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
          >
            <Bell className="h-4 w-4" />
            {lowStockCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[9px] font-bold text-white shadow-glow-rose ring-2 ring-white dark:ring-slate-950">
                {lowStockCount}
              </span>
            )}
          </button>
        </div>

        {/* User Profile Pill & Dropdown */}
        <div className="relative pl-1" ref={userMenuRef}>
          <button
            type="button"
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2 p-1 pr-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-900 border border-transparent hover:border-slate-200 dark:hover:border-slate-800 transition-all text-left"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 text-xs font-bold text-white shadow-md">
              {initials}
            </div>
            <div className="hidden lg:block">
              <div className="text-xs font-bold text-slate-800 dark:text-slate-200 leading-tight">
                {user?.fullName || 'Vijay B'}
              </div>
              <div className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">
                {user?.role === 'super_admin' ? 'Super Admin' : `${user?.role || 'Admin'} Role`}
              </div>
            </div>
            <ChevronDown
              className={`hidden lg:block h-3.5 w-3.5 text-slate-400 transition-transform duration-150 ${
                isUserMenuOpen ? 'rotate-180' : ''
              }`}
            />
          </button>

          {/* User Dropdown Menu */}
          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-56 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-2 shadow-2xl backdrop-blur-xl z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3 py-2 border-b border-slate-100 dark:border-slate-800">
                <p className="text-xs font-bold text-slate-900 dark:text-white">
                  {user?.fullName || 'Vijay B'}
                </p>
                <p className="text-[11px] text-slate-400 truncate">
                  {user?.email || 'admin@invenza.internal'}
                </p>
                {user?.companyName && (
                  <p className="text-[10px] text-indigo-500 font-semibold mt-0.5 truncate">
                    {user.companyName}
                  </p>
                )}
                <div className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                  <Shield className="h-3 w-3" />
                  <span className="uppercase">{user?.role || 'Admin'} Access</span>
                </div>
              </div>

              <div className="py-1">
                <button
                  onClick={() => {
                    setIsUserMenuOpen(false);
                    logout();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out of Invenza</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
