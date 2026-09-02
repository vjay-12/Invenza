import React, { useState, useEffect } from 'react';
import { InventoryProvider } from './context/InventoryContext';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar, TabType } from './components/layout/Sidebar';
import { Navbar } from './components/layout/Navbar';
import { QuickSearchModal } from './components/layout/QuickSearchModal';
import { InvenzaChatbot } from './components/chat/InvenzaChatbot';
import { Login } from './pages/Login';

import { SuperAdminConsole } from './pages/SuperAdminConsole';
import { CompanyTeam } from './pages/CompanyTeam';
import { Dashboard } from './pages/Dashboard';
import { Products } from './pages/Products';
import { Ledger } from './pages/Ledger';
import { PurchaseOrders } from './pages/PurchaseOrders';
import { SalesOrders } from './pages/SalesOrders';
import { Transfers } from './pages/Transfers';
import { Adjustments } from './pages/Adjustments';
import { Warehouses } from './pages/Warehouses';
import { Reports } from './pages/Reports';
import { Settings } from './pages/Settings';

const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading, isSuperAdmin } = useAuth();
  const [currentTab, setCurrentTab] = useState<TabType>(isSuperAdmin ? 'companies' : 'dashboard');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Sync tab with user role upon login
  useEffect(() => {
    if (isSuperAdmin) {
      setCurrentTab('companies');
    } else {
      setCurrentTab('dashboard');
    }
  }, [isSuperAdmin]);

  // Global keyboard shortcut for Command Palette (Ctrl/Cmd + K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen w-full flex items-center justify-center bg-slate-950 text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white font-black text-2xl shadow-glow-brand animate-pulse">
            I
          </div>
          <p className="text-xs font-semibold text-slate-400">Loading Invenza Enterprise Engine...</p>
        </div>
      </div>
    );
  }

  // If not logged in, render dedicated Login portal
  if (!isAuthenticated) {
    return <Login />;
  }

  const renderCurrentPage = () => {
    switch (currentTab) {
      case 'companies':
        return <SuperAdminConsole />;
      case 'team':
        return <CompanyTeam />;
      case 'dashboard':
        return <Dashboard onNavigate={(tab) => setCurrentTab(tab)} />;
      case 'products':
        return <Products />;
      case 'ledger':
        return <Ledger />;
      case 'purchase_orders':
        return <PurchaseOrders />;
      case 'sales_orders':
        return <SalesOrders />;
      case 'transfers':
        return <Transfers />;
      case 'adjustments':
        return <Adjustments />;
      case 'warehouses':
        return <Warehouses />;
      case 'reports':
        return <Reports />;
      case 'settings':
        return <Settings />;
      default:
        return isSuperAdmin ? <SuperAdminConsole /> : <Dashboard onNavigate={(tab) => setCurrentTab(tab)} />;
    }
  };

  return (
    <div className="flex h-screen w-full bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 selection:bg-indigo-500 selection:text-white transition-colors duration-200 overflow-hidden">
      {/* Sidebar (Desktop sticky & Mobile drawer) */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={(tab) => setCurrentTab(tab)}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto overflow-x-hidden">
        <Navbar
          onOpenSearch={() => setIsSearchOpen(true)}
          onOpenChat={() => setIsChatOpen(true)}
          onToggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        />

        <main className="flex-1 w-full max-w-[1600px] mx-auto p-4 sm:p-6 lg:p-8 animate-in fade-in duration-300">
          {renderCurrentPage()}
        </main>
      </div>

      {/* Modals & Overlays */}
      <QuickSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onNavigate={(tab) => setCurrentTab(tab)}
      />

      <InvenzaChatbot isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
};

export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <InventoryProvider>
          <AppContent />
        </InventoryProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
