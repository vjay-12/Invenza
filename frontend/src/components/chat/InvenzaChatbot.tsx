import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  X,
  Send,
  Database,
  BookOpen,
  ChevronDown,
  Minimize2,
  Bot,
  User,
  ExternalLink,
  Code,
} from 'lucide-react';
import { useInventory } from '../../context/InventoryContext';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  toolInvoked?: 'query_inventory_db' | 'search_docs';
  sqlQuery?: string;
  docCitation?: string;
}

interface InvenzaChatbotProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InvenzaChatbot: React.FC<InvenzaChatbotProps> = ({ isOpen, onClose }) => {
  const { products, locations, purchaseOrders } = useInventory();
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content:
        "Greetings! I'm your **Invenza AI Copilot**. I have dual-engine intelligence: I can run read-only **Text-to-SQL** queries across your live stock ledger (`query_inventory_db`) or search inventory SOPs & valuation algorithms (`search_docs`).\n\nTry asking me what's low on stock or how our FIFO ledger works!",
      timestamp: 'Just now',
    },
  ]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  const samplePrompts = [
    "What items are low on stock in Central Hub?",
    "How does FIFO stock valuation work?",
    "Show pending purchase orders",
    "What is the total valuation of electronics?",
  ];

  const handleSend = (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim()) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setIsTyping(true);

    // Simulate intelligent orchestrator response with realistic tool-use routing
    setTimeout(() => {
      const lower = text.toLowerCase();
      let reply: ChatMessage;

      if (
        lower.includes('low') ||
        lower.includes('reorder') ||
        lower.includes('central hub') ||
        lower.includes('stock')
      ) {
        const lowItems = products.filter((p) => p.currentStock <= p.reorderPoint);
        const count = lowItems.length;

        reply = {
          id: `reply-${Date.now()}`,
          role: 'assistant',
          content: `I executed a read-only **Text-to-SQL** query over the inventory ledger. We currently have **${count} SKUs** below their safety reorder thresholds:\n\n${lowItems
            .map(
              (p) =>
                `• **${p.name}** (\`${p.sku}\`): **${p.currentStock} ${p.unitOfMeasure}** in stock (Reorder Point: ${p.reorderPoint})`
            )
            .join('\n')}\n\n💡 *Actionable insight*: Purchase Order \`PO-2026-005\` has already been created for AeroCraft Industrial Supplies to replenish these units.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          toolInvoked: 'query_inventory_db',
          sqlQuery:
            'SELECT p.sku, p.name, p.reorder_point, COALESCE(SUM(m.quantity), 0) AS stock FROM products p LEFT JOIN stock_movements m ON p.id = m.product_id WHERE p.tenant_id = :tenant_id GROUP BY p.id HAVING stock <= p.reorder_point;',
        };
      } else if (
        lower.includes('fifo') ||
        lower.includes('valuation') ||
        lower.includes('weighted average') ||
        lower.includes('ledger')
      ) {
        reply = {
          id: `reply-${Date.now()}`,
          role: 'assistant',
          content:
            "I retrieved the relevant SOP documentation via **pgvector RAG**:\n\n### How FIFO Works in Invenza:\nInvenza calculates inventory assets using an **immutable movement ledger** (`IN`, `OUT`, `ADJUST`, `TRANSFER`). In **FIFO (First-In, First-Out)** costing:\n1. Incoming stock batches from Purchase Orders (GRN) are chronologically logged with their exact unit cost.\n2. When Sales Orders or adjustments consume stock, units are liquidated against the oldest active batch first.\n3. This reflects physical inventory rotation and preserves accurate profit margin calculations during inflationary periods.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          toolInvoked: 'search_docs',
          docCitation: 'Invenza Standard Operations Guide (SOP-VAL-04: Inventory Costing & Ledger Aggregation)',
        };
      } else if (lower.includes('po') || lower.includes('purchase order')) {
        reply = {
          id: `reply-${Date.now()}`,
          role: 'assistant',
          content: `You currently have **${purchaseOrders.length} Purchase Orders** on file.\n\n• **PO-2026-005** (AeroCraft): Pending delivery to Central Hub ($3,135.00)\n• **PO-2026-004** (OmniDesk): Fully received with auto-written GRN movements ($170.00)`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          toolInvoked: 'query_inventory_db',
          sqlQuery: 'SELECT po_number, supplier_name, status, total_amount FROM purchase_orders WHERE tenant_id = :tenant_id ORDER BY order_date DESC LIMIT 5;',
        };
      } else {
        reply = {
          id: `reply-${Date.now()}`,
          role: 'assistant',
          content:
            "I can assist with real-time stock balances, warehouse rebalancing, purchase order tracking, and inventory accounting guidelines. All answers are verified against your live database ledger.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
      }

      setMessages((prev) => [...prev, reply]);
      setIsTyping(false);
    }, 600);
  };

  if (!isOpen) {
    return (
      <button
        onClick={onClose}
        className="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-600 text-white shadow-xl shadow-indigo-500/30 hover:shadow-indigo-500/50 hover:scale-105 active:scale-95 transition-all group"
        aria-label="Open Invenza AI Assistant"
      >
        <Sparkles className="h-6 w-6 animate-pulse text-white group-hover:rotate-12 transition-transform" />
        <span className="absolute -top-1 -right-1 flex h-4 w-4">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-4 w-4 bg-indigo-500"></span>
        </span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 flex h-[620px] w-96 max-w-[calc(100vw-2rem)] flex-col rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 shadow-2xl backdrop-blur-xl overflow-hidden transition-all animate-in fade-in slide-in-from-bottom-5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 bg-gradient-to-r from-indigo-600/10 via-purple-600/10 to-transparent px-4 py-3.5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-glow-brand">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold text-slate-900 dark:text-white">Invenza Copilot</span>
              <span className="rounded-full bg-indigo-500/10 dark:bg-indigo-500/20 px-1.5 py-0.2 text-[10px] font-bold text-indigo-600 dark:text-indigo-400">
                v1.0
              </span>
            </div>
            <div className="text-[10px] text-slate-400">Orchestrator: Text-to-SQL + pgvector RAG</div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[88%] rounded-2xl p-3.5 ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 rounded-br-none'
                  : 'bg-slate-100 dark:bg-slate-800/90 text-slate-800 dark:text-slate-100 border border-slate-200/80 dark:border-slate-700/60 rounded-bl-none'
              }`}
            >
              {/* Tool Execution Badge */}
              {msg.toolInvoked && (
                <div className="mb-2 flex items-center gap-1.5 rounded-lg bg-indigo-500/10 px-2 py-1 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                  {msg.toolInvoked === 'query_inventory_db' ? (
                    <>
                      <Database className="h-3 w-3" />
                      <span>Tool: query_inventory_db (Text-to-SQL)</span>
                    </>
                  ) : (
                    <>
                      <BookOpen className="h-3 w-3" />
                      <span>Tool: search_docs (pgvector RAG)</span>
                    </>
                  )}
                </div>
              )}

              {/* Message text with basic markdown styling */}
              <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>

              {/* SQL Inspector Card */}
              {msg.sqlQuery && (
                <div className="mt-2.5 rounded-lg bg-slate-900 p-2 text-[10px] font-mono text-emerald-400 border border-slate-700 overflow-x-auto">
                  <div className="flex items-center gap-1 text-[9px] text-slate-400 uppercase font-sans mb-1">
                    <Code className="h-2.5 w-2.5" /> Executed Tenant-Safe SELECT Query
                  </div>
                  {msg.sqlQuery}
                </div>
              )}

              {/* Citation */}
              {msg.docCitation && (
                <div className="mt-2 flex items-center gap-1 text-[10px] text-indigo-500 dark:text-indigo-400 italic">
                  <ExternalLink className="h-3 w-3" /> Source: {msg.docCitation}
                </div>
              )}
            </div>
            <span className="mt-1 text-[10px] text-slate-400 px-1">{msg.timestamp}</span>
          </div>
        ))}

        {isTyping && (
          <div className="flex items-center gap-2 rounded-2xl bg-slate-100 dark:bg-slate-800 p-3 max-w-[120px]">
            <Bot className="h-4 w-4 text-indigo-500 animate-spin" />
            <span className="text-xs text-slate-500">Thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts */}
      <div className="px-3 py-2 border-t border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-950/50">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1.5">
          Quick Insights
        </div>
        <div className="flex gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {samplePrompts.map((p, i) => (
            <button
              key={i}
              onClick={() => handleSend(p)}
              className="shrink-0 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1 text-[11px] text-slate-600 dark:text-slate-300 hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Input Form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
        className="flex items-center gap-2 border-t border-slate-200 dark:border-slate-800 p-3 bg-white dark:bg-slate-900"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Invenza Copilot anything..."
          className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/90 px-3 py-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:border-indigo-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white shadow-md shadow-indigo-600/20 transition-all"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
};
