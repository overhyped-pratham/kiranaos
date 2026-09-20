import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ChatSimulator from './components/ChatSimulator';
import AgentTimeline from './components/AgentTimeline';
import InventoryTable from './components/InventoryTable';
import OrdersView from './components/OrdersView';
import ApprovalsView from './components/ApprovalsView';
import JudgeSuite from './components/JudgeSuite';
import { api } from './services/api';
import { ShoppingBag, AlertTriangle, TrendingUp, Clock, CheckCircle2, RefreshCw } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [pendingOrders, setPendingOrders] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusInfo, setStatusInfo] = useState(null);

  const loadData = async () => {
    try {
      const [inv, ords, pend, status] = await Promise.all([
        api.getInventory().catch(() => []),
        api.getOrders().catch(() => []),
        api.getPendingApprovals().catch(() => []),
        api.getSystemStatus().catch(() => null)
      ]);
      setProducts(inv);
      setOrders(ords);
      setPendingOrders(pend);
      setStatusInfo(status);
    } catch (e) {
      console.error('Failed to load data:', e);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleRunAgent = async (payload) => {
    setIsProcessing(true);
    try {
      const res = await api.runAgent(payload);
      setLatestRun(res);
      await loadData();
      return res;
    } finally {
      setIsProcessing(false);
    }
  };

  const handleUpdateProduct = async (id, updates) => {
    await api.updateProduct(id, updates);
    await loadData();
  };

  const handleRestockProduct = async (payload) => {
    await api.restockProduct(payload);
    await loadData();
  };

  const handleApproveOrder = async (payload) => {
    const res = await api.approveOrder(payload);
    await loadData();
    return res;
  };

  const lowStockProducts = products.filter(p => p.stock <= p.low_stock_threshold);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-emerald-500 selection:text-white">
      {/* Top Navbar */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingCount={pendingOrders.length}
        lowStockCount={lowStockProducts.length}
      />

      {/* Metric Quick Stats Bar */}
      <div className="bg-slate-900/60 border-b border-slate-800/80 px-4 sm:px-6 lg:px-8 py-2.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-slate-400">Total Products: <strong className="text-white">{products.length}</strong></span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`w-2 h-2 rounded-full ${lowStockProducts.length > 0 ? 'bg-amber-400' : 'bg-slate-500'}`}></span>
              <span className="text-slate-400">Low Stock Items: <strong className={lowStockProducts.length > 0 ? 'text-amber-400 font-bold' : 'text-slate-300'}>{lowStockProducts.length}</strong></span>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-slate-400">Committed Orders: <strong className="text-white">{orders.length}</strong></span>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`w-2 h-2 rounded-full ${pendingOrders.length > 0 ? 'bg-rose-400 animate-ping' : 'bg-slate-500'}`}></span>
              <span className="text-slate-400">Pending Approvals: <strong className={pendingOrders.length > 0 ? 'text-rose-400 font-bold' : 'text-slate-300'}>{pendingOrders.length}</strong></span>
            </div>
          </div>

          <div className="flex items-center space-x-2 text-[11px] text-slate-400">
            <span>FastAPI: <strong className="text-emerald-400">Connected (:8000)</strong></span>
            <span>•</span>
            <button
              onClick={loadData}
              className="hover:text-white flex items-center space-x-1"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Sync</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'dashboard' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Customer WhatsApp Simulator (5 cols) */}
            <div className="lg:col-span-5">
              <ChatSimulator
                onRunAgent={handleRunAgent}
                isProcessing={isProcessing}
                latestRun={latestRun}
              />
            </div>

            {/* Right: Live Agent Execution & Tools Timeline (7 cols) */}
            <div className="lg:col-span-7">
              <AgentTimeline latestRun={latestRun} />
            </div>
          </div>
        )}

        {activeTab === 'inventory' && (
          <InventoryTable
            products={products}
            onRefresh={loadData}
            onUpdateProduct={handleUpdateProduct}
            onRestockProduct={handleRestockProduct}
          />
        )}

        {activeTab === 'orders' && (
          <OrdersView
            orders={orders}
            onRefresh={loadData}
          />
        )}

        {activeTab === 'approvals' && (
          <ApprovalsView
            pendingOrders={pendingOrders}
            onApproveOrder={handleApproveOrder}
          />
        )}

        {activeTab === 'judge' && (
          <JudgeSuite onRefreshAll={loadData} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        KiranaOS — Zero-Click Store Operator • LangGraph + Qwen2.5-3B + BGE-M3 + n8n WhatsApp • Real PostgreSQL / SQLite Backed
      </footer>
    </div>
  );
}
