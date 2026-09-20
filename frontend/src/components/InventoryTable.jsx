import React, { useState } from 'react';
import { Package, Edit3, Plus, RefreshCw, AlertTriangle, CheckCircle, Search, TrendingDown } from 'lucide-react';

export default function InventoryTable({ products, onRefresh, onUpdateProduct, onRestockProduct }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [editingProduct, setEditingProduct] = useState(null);
  const [editPrice, setEditPrice] = useState('');
  const [editStock, setEditStock] = useState('');
  const [restockAmount, setRestockAmount] = useState(10);
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  const filtered = (products || []).filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.brand.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          p.category.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = selectedCategory === 'ALL' || p.category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const categories = ['ALL', ...new Set((products || []).map((p) => p.category))];

  const handleOpenEdit = (p) => {
    setEditingProduct(p);
    setEditPrice(p.price);
    setEditStock(p.stock);
  };

  const handleSaveEdit = async () => {
    if (!editingProduct) return;
    await onUpdateProduct(editingProduct.id, {
      price: parseFloat(editPrice),
      stock: parseInt(editStock, 10),
    });
    setEditingProduct(null);
  };

  const handleQuickRestock = async (product_id, qty) => {
    await onRestockProduct({
      product_id,
      quantity: qty,
      reason: 'manual_merchant_restock'
    });
  };

  return (
    <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Header & Controls */}
      <div className="p-5 bg-slate-900 border-b border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Package className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-semibold text-white">Live Store Inventory (Database)</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Strict source of truth. Mutate stock (e.g. Maggi 50 → 0) or price (₹240 → ₹260) to verify dynamic agent adaptation.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Search bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter products..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-950 text-slate-200 text-xs pl-9 pr-3 py-2 rounded-lg border border-slate-700 focus:outline-none focus:border-emerald-500 w-48"
            />
          </div>

          <button
            onClick={onRefresh}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
            title="Refresh database records"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Category Pills */}
      <div className="px-5 py-2.5 bg-slate-900/40 border-b border-slate-800/80 flex items-center space-x-2 overflow-x-auto no-scrollbar text-xs">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1 rounded-lg font-medium transition-all ${
              selectedCategory === cat
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-900/80 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <th className="px-5 py-3">Product Name & Size</th>
              <th className="px-4 py-3">Category</th>
              <th className="px-4 py-3">Unit Price</th>
              <th className="px-4 py-3">Live Stock</th>
              <th className="px-4 py-3">Threshold</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 text-xs">
            {filtered.map((p) => {
              const isOutOfStock = p.stock === 0;
              const isLowStock = p.stock > 0 && p.stock <= p.low_stock_threshold;

              return (
                <tr key={p.id} className="hover:bg-slate-900/50 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="font-semibold text-slate-100">{p.name}</div>
                    <div className="text-[11px] text-slate-400 flex items-center space-x-2 mt-0.5">
                      <span className="font-mono text-[10px] text-slate-500">{p.id}</span>
                      <span>•</span>
                      <span>{p.size} ({p.unit})</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-slate-300">{p.category}</td>
                  <td className="px-4 py-3.5 font-semibold text-white">₹{p.price.toFixed(2)}</td>
                  <td className="px-4 py-3.5 font-bold font-mono">
                    <span className={isOutOfStock ? 'text-rose-400' : isLowStock ? 'text-amber-400' : 'text-emerald-400'}>
                      {p.stock}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-slate-400 font-mono">{p.low_stock_threshold}</td>
                  <td className="px-4 py-3.5">
                    {isOutOfStock ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                        <AlertTriangle className="w-3 h-3" />
                        <span>Out of Stock</span>
                      </span>
                    ) : isLowStock ? (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        <TrendingDown className="w-3 h-3" />
                        <span>Low Stock</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle className="w-3 h-3" />
                        <span>In Stock</span>
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-right space-x-2">
                    <button
                      onClick={() => handleOpenEdit(p)}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 text-[11px] font-medium transition-colors"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleQuickRestock(p.id, 10)}
                      className="px-2.5 py-1 bg-emerald-950 hover:bg-emerald-900 text-emerald-300 rounded border border-emerald-800 text-[11px] font-medium transition-colors"
                    >
                      +10 Restock
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Edit Modal */}
      {editingProduct && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h4 className="text-base font-bold text-white mb-1">Edit Product: {editingProduct.name}</h4>
            <p className="text-xs text-slate-400 mb-4">Mutate database values to test autonomous reaction.</p>

            <div className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 mb-1 font-medium">Live Stock Units:</label>
                <input
                  type="number"
                  value={editStock}
                  onChange={(e) => setEditStock(e.target.value)}
                  className="w-full bg-slate-950 text-white px-3 py-2 rounded-lg border border-slate-700 focus:outline-none focus:border-emerald-500 text-sm font-mono"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">Tip: Set Maggi stock to 0 to test out-of-stock alternative recommendation.</span>
              </div>

              <div>
                <label className="block text-slate-300 mb-1 font-medium">Authoritative Unit Price (₹):</label>
                <input
                  type="number"
                  step="0.5"
                  value={editPrice}
                  onChange={(e) => setEditPrice(e.target.value)}
                  className="w-full bg-slate-950 text-white px-3 py-2 rounded-lg border border-slate-700 focus:outline-none focus:border-emerald-500 text-sm font-mono"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">Tip: Change Aashirvaad price from ₹240 to ₹260 to test dynamic recalculation.</span>
              </div>
            </div>

            <div className="mt-6 flex justify-end space-x-2">
              <button
                onClick={() => setEditingProduct(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-xs shadow-md"
              >
                Save Changes to DB
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
