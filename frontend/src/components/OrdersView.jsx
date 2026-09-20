import React from 'react';
import { ShoppingCart, Truck, CheckCircle2, Clock, XCircle, ShieldCheck } from 'lucide-react';

export default function OrdersView({ orders, onRefresh }) {
  return (
    <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-5 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <ShoppingCart className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-semibold text-white">Committed Orders Ledger</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Orders created via atomic database transactions with deterministic price calculation.
          </p>
        </div>

        <span className="text-xs px-2.5 py-1 bg-slate-800 text-slate-300 rounded-lg border border-slate-700">
          {orders.length} Total Orders
        </span>
      </div>

      {/* Orders List */}
      <div className="divide-y divide-slate-800">
        {orders.length === 0 ? (
          <div className="p-8 text-center text-slate-500 text-xs">
            No orders committed yet. Use the WhatsApp simulator to create one!
          </div>
        ) : (
          orders.map((ord) => {
            const isConfirmed = ord.status === 'confirmed';
            const isPending = ord.status === 'pending_approval';
            const isDelivered = ord.status === 'delivered';

            return (
              <div key={ord.id} className="p-5 hover:bg-slate-900/40 transition-colors">
                {/* Order Top Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono font-bold text-sm text-white tracking-wide">{ord.id}</span>
                    <span className="text-xs text-slate-400 font-mono">Cust: {ord.customer_id}</span>
                    {ord.idempotency_key && (
                      <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 text-slate-400 rounded border border-slate-700">
                        Key: {ord.idempotency_key}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-3">
                    {/* Status Badge */}
                    {isConfirmed && (
                      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Confirmed</span>
                      </span>
                    )}
                    {isPending && (
                      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        <Clock className="w-3.5 h-3.5" />
                        <span>Pending Merchant Approval</span>
                      </span>
                    )}
                    {isDelivered && (
                      <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        <Truck className="w-3.5 h-3.5" />
                        <span>Delivered</span>
                      </span>
                    )}

                    <span className="text-xs text-slate-400 font-mono">
                      {ord.created_at ? new Date(ord.created_at).toLocaleTimeString() : ''}
                    </span>
                  </div>
                </div>

                {/* Items & Pricing Breakdown */}
                <div className="bg-slate-900/70 rounded-xl p-3 border border-slate-800/80 mb-3">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="text-slate-400 border-b border-slate-800 pb-1 text-[11px]">
                        <th className="py-1">Item Description</th>
                        <th className="py-1 text-center">Qty</th>
                        <th className="py-1 text-right">Unit Price</th>
                        <th className="py-1 text-right">Line Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {(ord.items || []).map((item, idx) => (
                        <tr key={idx}>
                          <td className="py-1.5 font-medium text-slate-200">{item.product_name}</td>
                          <td className="py-1.5 text-center font-mono text-slate-300">{item.quantity}</td>
                          <td className="py-1.5 text-right font-mono text-slate-400">₹{item.unit_price.toFixed(2)}</td>
                          <td className="py-1.5 text-right font-mono font-semibold text-slate-200">₹{item.line_total.toFixed(2)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Bottom Financials & Delivery Info */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between text-xs pt-1 border-t border-slate-800/60 text-slate-400">
                  <div className="flex items-center space-x-2">
                    <Truck className="w-4 h-4 text-emerald-400" />
                    <span>Deliver to: <strong className="text-slate-200">{ord.delivery_address || 'Customer Default Address'}</strong></span>
                  </div>

                  <div className="flex items-center space-x-4 mt-2 sm:mt-0">
                    <span>Subtotal: ₹{ord.subtotal.toFixed(2)}</span>
                    <span>Delivery: {ord.delivery_charge === 0 ? <strong className="text-emerald-400">FREE</strong> : `₹${ord.delivery_charge.toFixed(2)}`}</span>
                    <span className="text-sm font-bold text-white bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700">
                      Total: ₹{ord.total.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
