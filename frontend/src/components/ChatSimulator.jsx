import React, { useState } from 'react';
import { Send, Phone, User, Sparkles, Check, CheckCheck, AlertCircle, ShoppingCart } from 'lucide-react';

export default function ChatSimulator({ onRunAgent, isProcessing, latestRun }) {
  const [inputMessage, setInputMessage] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('+919876543210');
  const [chatHistory, setChatHistory] = useState([
    {
      sender: 'system',
      text: 'KiranaOS Assistant is online. Send grocery orders in English, Hindi, or Hinglish!',
      time: '10:00 AM'
    }
  ]);

  const presetQueries = [
    {
      label: 'Happy Path Order',
      query: 'Hi bhaiya, 2 packets Aashirvaad atta, 1 Fortune oil aur 3 Maggi bhej do. Ghar pe deliver kar dena.',
      color: 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
    },
    {
      label: '5 Kilo Wala Aata (Hinglish)',
      query: 'wo 5 kilo wala aata bhej dena',
      color: 'bg-blue-950/60 text-blue-300 border-blue-800'
    },
    {
      label: 'Mera Usual Samaan (Memory)',
      query: 'bhaiya mera usual samaan bhej do',
      color: 'bg-purple-950/60 text-purple-300 border-purple-800'
    },
    {
      label: '20 Maggi (Trigger Approval)',
      query: '20 Maggi bhej do jaldi se',
      color: 'bg-amber-950/60 text-amber-300 border-amber-800'
    },
    {
      label: '50 Fortune Oil (Stock Shortage)',
      query: '50 packets Fortune oil ghar pe deliver kar do',
      color: 'bg-rose-950/60 text-rose-300 border-rose-800'
    },
    {
      label: 'Unavailable Item (Alternatives)',
      query: '2 packets Vim Bar XYZ bhej do',
      color: 'bg-slate-800 text-slate-300 border-slate-700'
    }
  ];

  const handleSend = async (msgToSend = null) => {
    const text = msgToSend || inputMessage;
    if (!text.trim() || isProcessing) return;

    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Append user message
    setChatHistory((prev) => [
      ...prev,
      { sender: 'user', text, time: currentTime }
    ]);
    setInputMessage('');

    try {
      const result = await onRunAgent({
        message: text,
        phone: phoneNumber
      });

      const replyTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setChatHistory((prev) => [
        ...prev,
        {
          sender: 'assistant',
          text: result.message,
          time: replyTime,
          status: result.status,
          order: result.order,
          options: result.clarification_options
        }
      ]);
    } catch (err) {
      setChatHistory((prev) => [
        ...prev,
        {
          sender: 'system',
          text: `Error: ${err.message}`,
          time: currentTime,
          isError: true
        }
      ]);
    }
  };

  return (
    <div className="flex flex-col h-[740px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Mobile WhatsApp Header */}
      <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-white text-sm">
              K
            </div>
            <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-400 border-2 border-slate-900 rounded-full"></span>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-semibold text-white">Kirana Store Operator</h3>
              <span className="text-[10px] px-1.5 py-0.2 bg-emerald-500/20 text-emerald-400 rounded-md">Live WhatsApp AI</span>
            </div>
            <p className="text-xs text-slate-400">Autonomous Store Bot • +91 98765 43210</p>
          </div>
        </div>

        {/* Customer Switcher */}
        <div className="flex items-center space-x-2 text-xs bg-slate-800 px-2.5 py-1.5 rounded-lg border border-slate-700">
          <User className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={phoneNumber}
            onChange={(e) => setPhoneNumber(e.target.value)}
            className="bg-transparent text-slate-200 focus:outline-none text-xs cursor-pointer"
          >
            <option value="+919876543210" className="bg-slate-800">Rahul Sharma (Regular)</option>
            <option value="+919811122233" className="bg-slate-800">Priya Verma (Milk/Snacks)</option>
            <option value="+919999988888" className="bg-slate-800">New Customer (+91 99999 88888)</option>
          </select>
        </div>
      </div>

      {/* Preset Quick Chips */}
      <div className="bg-slate-900/60 px-4 py-2 border-b border-slate-800/80 overflow-x-auto flex space-x-2 no-scrollbar">
        {presetQueries.map((preset, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(preset.query)}
            disabled={isProcessing}
            className={`whitespace-nowrap px-2.5 py-1 text-xs rounded-full border transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 ${preset.color}`}
          >
            {preset.label}
          </button>
        ))}
      </div>

      {/* Chat Messages Body */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px]">
        {chatHistory.map((item, idx) => {
          if (item.sender === 'user') {
            return (
              <div key={idx} className="flex justify-end">
                <div className="max-w-[85%] bg-emerald-700 text-white rounded-2xl rounded-tr-xs px-3.5 py-2 text-sm shadow-md">
                  <p className="whitespace-pre-wrap">{item.text}</p>
                  <div className="flex items-center justify-end space-x-1 mt-1 text-[10px] text-emerald-200">
                    <span>{item.time}</span>
                    <CheckCheck className="w-3 h-3 text-emerald-300" />
                  </div>
                </div>
              </div>
            );
          }

          if (item.sender === 'assistant') {
            const isConfirmed = item.status === 'confirmed';
            const isApproval = item.status === 'pending_approval';
            const isClarification = item.status === 'needs_clarification';

            return (
              <div key={idx} className="flex justify-start">
                <div className="max-w-[88%] bg-slate-800 text-slate-100 rounded-2xl rounded-tl-xs px-3.5 py-2.5 text-sm shadow-md border border-slate-700">
                  {/* Status Banner */}
                  <div className="flex items-center space-x-1.5 mb-1.5 pb-1.5 border-b border-slate-700 text-xs">
                    {isConfirmed && (
                      <span className="flex items-center space-x-1 text-emerald-400 font-medium">
                        <Check className="w-3.5 h-3.5" />
                        <span>Order Committed in Database</span>
                      </span>
                    )}
                    {isApproval && (
                      <span className="flex items-center space-x-1 text-amber-400 font-medium">
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>Needs Merchant Approval</span>
                      </span>
                    )}
                    {isClarification && (
                      <span className="flex items-center space-x-1 text-cyan-400 font-medium">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Clarification / Options</span>
                      </span>
                    )}
                  </div>

                  <p className="whitespace-pre-wrap font-sans text-xs leading-relaxed">{item.text}</p>

                  {/* Interactive Options if available */}
                  {item.options && item.options.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-700 space-y-1">
                      <p className="text-[11px] font-semibold text-slate-400">Select Option:</p>
                      <div className="flex flex-wrap gap-1.5">
                        {item.options.map((opt, oIdx) => (
                          <button
                            key={oIdx}
                            onClick={() => handleSend(opt.label || opt.product_id)}
                            className="px-2.5 py-1 text-xs bg-slate-700 hover:bg-emerald-600 text-slate-200 hover:text-white rounded-lg border border-slate-600 transition-colors"
                          >
                            {opt.label || opt.product_id}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-end space-x-1 mt-1 text-[10px] text-slate-400">
                    <span>{item.time}</span>
                  </div>
                </div>
              </div>
            );
          }

          return (
            <div key={idx} className="flex justify-center my-2">
              <span className="px-3 py-1 bg-slate-800/80 text-slate-400 rounded-full text-xs border border-slate-700">
                {item.text}
              </span>
            </div>
          );
        })}

        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-slate-800 text-slate-300 rounded-2xl rounded-tl-xs px-3.5 py-2 text-xs border border-slate-700 flex items-center space-x-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></div>
              <span>LangGraph executing real database tools...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input Bar */}
      <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={isProcessing}
          placeholder="Type grocery message (English, Hindi, Hinglish)..."
          className="flex-1 bg-slate-950 text-slate-100 text-sm px-4 py-2.5 rounded-xl border border-slate-700 focus:outline-none focus:border-emerald-500 placeholder-slate-500"
        />
        <button
          onClick={() => handleSend()}
          disabled={!inputMessage.trim() || isProcessing}
          className="p-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl transition-all shadow-md active:scale-95"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
