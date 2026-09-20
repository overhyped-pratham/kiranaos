import React from 'react';
import { ShoppingBag, Database, Cpu, Activity, Bell, CheckCircle2, Sparkles } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, pendingCount, lowStockCount }) {
  return (
    <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Brand Logo & Tagline */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-900/30">
              <ShoppingBag className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-tight text-white">Kirana<span className="text-emerald-400">OS</span></span>
                <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                  Zero-Click Operator
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous Store AI • Real Database & Inventory</p>
            </div>
          </div>

          {/* Live System Engine Badges */}
          <div className="hidden lg:flex items-center space-x-2 text-xs">
            <span className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              <span>LLM: <strong>Qwen2.5-3B</strong></span>
            </span>
            <span className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>Retrieval: <strong>BGE-M3 + Rerank</strong></span>
            </span>
            <span className="flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700">
              <Database className="w-3.5 h-3.5 text-blue-400" />
              <span>DB: <strong>Postgres / SQLite (Live)</strong></span>
            </span>
            <span className="flex items-center space-x-1.5 px-2.5 py-1 bg-emerald-500/10 text-emerald-400 rounded-md border border-emerald-500/20">
              <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>LangGraph Active</span>
            </span>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1 sm:space-x-2">
            {[
              { id: 'dashboard', label: 'Operator Hub' },
              { id: 'inventory', label: 'Live Inventory', badge: lowStockCount > 0 ? `${lowStockCount} Low` : null, badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
              { id: 'orders', label: 'Committed Orders' },
              { id: 'approvals', label: 'Approvals', badge: pendingCount > 0 ? pendingCount : null, badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30' },
              { id: 'judge', label: 'Judge Verification', special: true },
            ].map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`relative px-3 py-1.5 rounded-lg text-xs sm:text-sm font-medium transition-all flex items-center space-x-1.5 ${
                    tab.special
                      ? isActive
                        ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white font-semibold shadow-md shadow-orange-900/30'
                        : 'bg-amber-500/10 text-amber-300 border border-amber-500/30 hover:bg-amber-500/20'
                      : isActive
                      ? 'bg-emerald-600 text-white shadow-md shadow-emerald-900/30'
                      : 'text-slate-300 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  <span>{tab.label}</span>
                  {tab.badge && (
                    <span className={`px-1.5 py-0.2 text-[10px] font-bold rounded-full border ${tab.badgeColor || 'bg-slate-700 text-slate-200'}`}>
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

        </div>
      </div>
    </header>
  );
}
