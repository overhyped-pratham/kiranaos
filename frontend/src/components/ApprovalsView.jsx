import React, { useState } from 'react';
import { AlertCircle, CheckCircle, XCircle, ShieldAlert, Clock, User, DollarSign } from 'lucide-react';

export default function ApprovalsView({ pendingOrders, onApproveOrder }) {
  const [processingId, setProcessingId] = useState(null);

  const handleAction = async (orderId, action) => {
    setProcessingId(orderId);
    try {
      await onApproveOrder({
        order_id: orderId,
        action: action,
        reason: action === 'reject' ? 'Rejected by store operator via dashboard.' : null,
      });
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div className="bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Header */}
      <div className="p-5 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-semibold text-white">Merchant Human-in-the-Loop Approvals</h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Autonomous guardrail: LangGraph halts state and persists execution for bulk orders or high-value requests.
          </p>
        </div>

        <span className="text-xs px-2.5 py-1 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20 font-semibold">
          {pendingOrders.length} Pending
        </span>
      </div>

      {/* Approvals List */}
      <div className="p-5 space-y-4">
        {pendingOrders.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            No orders currently pending approval. Everything running fully automated!
          </div>
        ) : (
          pendingOrders.map((ord) => {
            const isProcessing = processingId === ord.id;

            return (
              <div
                key={ord.id}
                className="bg-slate-900 border-2 border-amber-500/30 rounded-2xl p-5 shadow-lg relative overflow-hidden"
              >
                {/* Warning Banner */}
                <div className="flex items-center justify-between mb-3 pb-3 border-b border-slate-800">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-white text-sm">{ord.id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                      Approval Required
                    </span>
                  </div>
                  <div className="text-xs font-mono text-slate-400">
                    Customer: {ord.customer_id}
                  </div>
                </div>

                {/* Reason */}
                <div className="bg-amber-950/40 border border-amber-800/60 rounded-xl p-3 mb-4 text-xs text-amber-200 flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold block">Trigger Reason:</span>
                    <span>{ord.approval_reason || 'Order exceeds standard quantity or value thresholds.'}</span>
                  </div>
                </div>

                {/* Line Items */}
                <div className="bg-slate-950 rounded-xl p-3 border border-slate-800 mb-4 text-xs">
                  <div className="text-slate-400 font-semibold mb-2">Requested Items:</div>
                  <div className="space-y-1.5">
                    {(ord.items || []).map((item, idx) => (
                      <div key={idx} className="flex justify-between items-center text-slate-200">
                        <span>• {item.quantity} × {item.product_name}</span>
                        <span className="font-mono font-semibold">₹{item.line_total.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="mt-3 pt-2 border-t border-slate-800 flex justify-between items-center font-bold text-sm text-white">
                    <span>Grand Total:</span>
                    <span className="text-emerald-400">₹{ord.total.toFixed(2)}</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end space-x-3">
                  <button
                    onClick={() => handleAction(ord.id, 'reject')}
                    disabled={isProcessing}
                    className="px-4 py-2 bg-rose-950 hover:bg-rose-900 text-rose-300 font-medium rounded-xl text-xs border border-rose-800 transition-colors disabled:opacity-50"
                  >
                    Reject Order
                  </button>
                  <button
                    onClick={() => handleAction(ord.id, 'approve')}
                    disabled={isProcessing}
                    className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-xs shadow-md transition-all active:scale-95 disabled:opacity-50 flex items-center space-x-1.5"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>{isProcessing ? 'Committing...' : 'Approve & Deduct Inventory'}</span>
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
