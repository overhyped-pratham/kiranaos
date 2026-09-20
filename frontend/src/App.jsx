import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import ChatSimulator from './components/ChatSimulator';
import AgentTimeline from './components/AgentTimeline';
import InventoryTable from './components/InventoryTable';
import OrdersView from './components/OrdersView';
import ApprovalsView from './components/ApprovalsView';
import JudgeSuite from './components/JudgeSuite';
import { api } from './services/api';
import { subscribeToRealtimeChanges } from './services/supabase';
import { ShoppingBag, AlertTriangle, TrendingUp, Clock, CheckCircle2, RefreshCw, Zap } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [pendingOrders, setPendingOrders] = useState([]);
  const [latestRun, setLatestRun] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusInfo, setStatusInfo] = useState(null);
  const [realtimeEvents, setRealtimeEvents] = useState([]);
  const [realtimeStatus, setRealtimeStatus] = useState('connecting');

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
    // Initial data hydration
    loadData();

    // Supabase Realtime WebSockets: instant PostgreSQL state propagation without page refresh
    const unsubscribe = subscribeToRealtimeChanges({
      onProductChange: (payload) => {
        console.log('[Supabase Realtime] Product event received:', payload);
        if (payload.eventType === 'UPDATE' && payload.new) {
          setProducts((prev) =>
            prev.map((p) => (p.id === payload.new.id ? { ...p, ...payload.new } : p))
          );
        } else if (payload.eventType === 'INSERT' && payload.new) {
          setProducts((prev) => [payload.new, ...prev]);
        } else if (payload.eventType === 'DELETE' && payload.old) {
          setProducts((prev) => prev.filter((p) => p.id !== payload.old.id));
        }
      },
      onOrderChange: (payload) => {
        console.log('[Supabase Realtime] Order event received:', payload);
        if (payload.eventType === 'INSERT' && payload.new) {
          setOrders((prev) => [payload.new, ...prev]);
          if (payload.new.status === 'pending_approval') {
            setPendingOrders((prev) => [payload.new, ...prev]);
          }
        } else if (payload.eventType === 'UPDATE' && payload.new) {
          setOrders((prev) =>
            prev.map((o) => (o.id === payload.new.id ? { ...o, ...payload.new } : o))
          );
          if (payload.new.status === 'pending_approval') {
            setPendingOrders((prev) => {
              const exists = prev.some((o) => o.id === payload.new.id);
              return exists ? prev.map((o) => (o.id === payload.new.id ? payload.new : o)) : [payload.new, ...prev];
            });
          } else {
            setPendingOrders((prev) => prev.filter((o) => o.id !== payload.new.id));
          }
        }
      },
      onAgentRunChange: (payload) => {
        console.log('[Supabase Realtime] Agent run event received:', payload);
        if (payload.new) {
          setLatestRun(payload.new);
        }
      },
      onLowStockChange: (payload) => {
        console.log('[Supabase Realtime] Low stock event received:', payload);
      },
      onDeliveryChange: (payload) => {
        console.log('[Supabase Realtime] Delivery request event received:', payload);
      },
      onEventLog: (event) => {
        setRealtimeStatus('active');
        setRealtimeEvents((prev) => [event, ...prev].slice(0, 30));
      }
    });

    setRealtimeStatus('connected');

    // Heartbeat fallback sync every 30s (non-intrusive)
    const interval = setInterval(loadData, 30000);
    return () => {
      unsubscribe();
      clearInterval(interval);
    };
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

          <div className="flex items-center space-x-3 text-[11px] text-slate-400">
            <div className="flex items-center space-x-1.5 bg-slate-800/80 px-2.5 py-1 rounded-full border border-slate-700/60">
              <Zap className={`w-3 h-3 ${realtimeStatus === 'active' || realtimeStatus === 'connected' ? 'text-emerald-400 fill-emerald-400 animate-pulse' : 'text-amber-400'}`} />
              <span className="text-slate-300 font-medium">Supabase Realtime:</span>
              <strong className={realtimeStatus === 'active' || realtimeStatus === 'connected' ? 'text-emerald-400' : 'text-amber-400'}>
                {realtimeStatus === 'active' ? 'LIVE (Streaming)' : realtimeStatus === 'connected' ? 'Connected' : 'Connecting...'}
              </strong>
            </div>
            <span>•</span>
            <span>API: <strong className={statusInfo ? "text-emerald-400" : "text-amber-400"}>{statusInfo ? "Connected" : "Connecting..."}</strong></span>
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

      {/* Realtime Live Event Ticker (when events arrive) */}
      {realtimeEvents.length > 0 && (
        <div className="bg-emerald-950/40 border-b border-emerald-900/40 px-4 py-1 text-[11px] text-emerald-300 flex items-center space-x-3 overflow-x-auto">
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 uppercase tracking-wider">
            Realtime Event
          </span>
          <span className="font-mono text-slate-400">{realtimeEvents[0].timestamp}</span>
          <span className="text-slate-200">Table: <strong className="text-emerald-400">{realtimeEvents[0].table}</strong></span>
          <span className="text-slate-400">({realtimeEvents[0].eventType})</span>
          <span className="text-slate-400 truncate max-w-xl">
            {JSON.stringify(realtimeEvents[0].record)}
          </span>
        </div>
      )}

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
          <JudgeSuite onRefreshAll={loadData} realtimeEvents={realtimeEvents} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        KiranaOS — Zero-Click Store Operator • LangGraph + Qwen2.5-3B + BGE-M3 + n8n WhatsApp • Real PostgreSQL / SQLite Backed
      </footer>
    </div>
  );
}
