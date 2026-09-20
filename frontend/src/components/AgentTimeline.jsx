import React from 'react';
import { Clock, Terminal, Wrench, CheckCircle2, AlertTriangle, ArrowRight, ShieldCheck } from 'lucide-react';

export default function AgentTimeline({ latestRun }) {
  if (!latestRun) {
    return (
      <div className="h-[740px] bg-slate-950 rounded-2xl border border-slate-800 p-6 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-3">
          <Terminal className="w-6 h-6 text-slate-500" />
        </div>
        <h4 className="text-sm font-semibold text-slate-300">Awaiting Agent Execution</h4>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Send an order via WhatsApp Simulator or trigger a test scenario to inspect live LangGraph tool executions in real-time.
        </p>
      </div>
    );
  }

  const events = latestRun.events || [];
  const toolCalls = latestRun.tool_calls || [];
  const intent = latestRun.structured_intent || {};

  const getEventBadgeColor = (eventName) => {
    if (eventName.includes('CONFIRMATION') || eventName.includes('ORDER_CREATED') || eventName.includes('UPDATED')) {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    }
    if (eventName.includes('APPROVAL') || eventName.includes('INSUFFICIENT')) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
    if (eventName.includes('FAILED') || eventName.includes('UNRESOLVED')) {
      return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    }
    return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
  };

  return (
    <div className="h-[740px] bg-slate-950 rounded-2xl border border-slate-800 flex flex-col overflow-hidden shadow-2xl">
      {/* Header Summary */}
      <div className="bg-slate-900 px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-2">
            <h3 className="text-sm font-semibold text-white">LangGraph Execution Trace</h3>
            <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 text-slate-300 rounded border border-slate-700">
              Run ID: {latestRun.run_id}
            </span>
          </div>
          <p className="text-xs text-slate-400">Request: {latestRun.request_id} • Status: <strong className="text-emerald-400 uppercase">{latestRun.status}</strong></p>
        </div>

        <div className="flex items-center space-x-2 text-xs">
          <span className="px-2.5 py-1 bg-slate-800 text-slate-300 rounded-lg border border-slate-700">
            {events.length} Events Logged
          </span>
          <span className="px-2.5 py-1 bg-emerald-950 text-emerald-400 rounded-lg border border-emerald-800">
            {toolCalls.length} Tool Calls
          </span>
        </div>
      </div>

      {/* Structured Intent Banner */}
      {intent.intent && (
        <div className="bg-slate-900/50 px-5 py-2.5 border-b border-slate-800/80 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400">Qwen Intent:</span>
            <span className="font-semibold text-cyan-300 uppercase">{intent.intent}</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">Delivery:</span>
            <span className="font-medium text-slate-200">{intent.delivery_required ? 'Yes (Home Delivery)' : 'No (Pickup)'}</span>
          </div>
          <div className="text-slate-400">
            Items Extracted: <strong className="text-white">{(intent.items || []).length}</strong>
          </div>
        </div>
      )}

      {/* Events Timeline Stream */}
      <div className="flex-1 p-5 overflow-y-auto space-y-3 font-mono text-xs">
        {events.map((evt, idx) => {
          return (
            <div key={idx} className="relative pl-6 pb-2 border-l-2 border-slate-800 last:border-l-0">
              {/* Timeline marker node */}
              <div className="absolute -left-[9px] top-0.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-emerald-500 flex items-center justify-center">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
              </div>

              {/* Event Card */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-3 hover:border-slate-700 transition-colors">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-slate-400">{evt.timestamp}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getEventBadgeColor(evt.event)}`}>
                      {evt.event}
                    </span>
                  </div>
                  {evt.tool && (
                    <span className="flex items-center space-x-1 text-[11px] text-amber-300/90 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                      <Wrench className="w-3 h-3" />
                      <span>{evt.tool}()</span>
                    </span>
                  )}
                </div>

                {/* Event Details JSON */}
                <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 text-[11px] text-slate-300 overflow-x-auto">
                  <pre className="whitespace-pre-wrap leading-relaxed">{JSON.stringify(evt.details, null, 2)}</pre>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
