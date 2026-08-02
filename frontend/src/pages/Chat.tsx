/**
 * AI Chat — Multi-turn conversation with the AI investment advisor.
 *
 * Features:
 * - Persistent conversation in session
 * - Voice input support
 * - Ticker detection triggers AI analysis
 * - Typing indicator during response
 */

import { useState, useRef, useEffect } from "react";
import { VoiceInput } from "@/components/VoiceInput";
import { getStoredToken } from "@/services/auth";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const SUGGESTIONS = [
  "Analyze RELIANCE",
  "How's my portfolio doing?",
  "Should I buy TCS?",
  "What are the top opportunities?",
  "Analyze INFY",
  "Show my risk exposure",
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "Hi! I'm your AI investment advisor. Ask me about any stock (use the ticker in CAPS), portfolio analysis, or market insights.\n\nTry: \"Analyze RELIANCE\" or \"Should I buy TCS?\"",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text?: string) {
    const content = (text || input).trim();
    if (!content || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await getAIResponse(content);
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content: "Sorry, something went wrong. Please try again.", timestamp: new Date() },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  async function getAIResponse(query: string): Promise<string> {
    const token = getStoredToken();
    const headers: Record<string, string> = { Authorization: `Bearer ${token}` };

    // Check if query mentions a ticker (supports & in Indian tickers like M&M, GVT&D, L&TFH)
    const tickerMatch = query.match(/\b([A-Z][A-Z0-9&]{1,14})\b/);
    const ticker = tickerMatch ? tickerMatch[1] : null;

    // Route to appropriate endpoint based on query intent
    if (ticker && (query.toLowerCase().includes("analyze") || query.toLowerCase().includes("buy") || query.toLowerCase().includes("sell") || query.toLowerCase().includes("about"))) {
      const res = await fetch(`/api/v1/ai/analyze/${ticker}`, {
        method: "POST",
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.responses && data.responses.length > 0) {
          const agents = data.responses.map((r: any) =>
            `• **${r.agent_name}** (${r.score}/10): ${r.summary}`
          ).join("\n");
          return `📊 **Analysis for ${ticker}**\n\n${agents}\n\nOverall: ${data.responses.length} agents analyzed this stock.`;
        }
        return `📊 **${ticker}** — Analysis request sent but AI agents didn't return detailed results. This can happen outside market hours or for lesser-known tickers. Try again during NSE trading hours (9:15 AM - 3:30 PM IST).`;
      }
    }

    if (query.toLowerCase().includes("portfolio") || query.toLowerCase().includes("holdings")) {
      const res = await fetch("/api/v1/portfolios", { headers });
      if (res.ok) {
        const portfolios = await res.json();
        if (portfolios.length > 0) {
          const holdingsRes = await fetch(`/api/v1/portfolios/${portfolios[0].id}/holdings`, { headers });
          if (holdingsRes.ok) {
            const data = await holdingsRes.json();
            return `📁 **Your Portfolio: ${data.portfolio_name}**\n\n` +
              `• Holdings: ${data.total_holdings}\n` +
              `• Total Invested: ₹${data.total_invested.toLocaleString("en-IN")}\n\n` +
              `Top positions:\n${data.holdings.slice(0, 5).map((h: any) => `  • ${h.ticker}: ${h.quantity} units @ ₹${h.average_cost}`).join("\n")}`;
          }
        }
        return "You don't have a portfolio yet. Go to the Import page to upload your holdings, or add them manually on the Portfolio page.";
      }
    }

    if (query.toLowerCase().includes("opportunit")) {
      const res = await fetch("/api/v1/decisions/opportunities", { headers });
      if (res.ok) {
        const data = await res.json();
        if (data.opportunities?.length) {
          return `🎯 **Top Opportunities**\n\n${data.opportunities.slice(0, 5).map((o: any) => `• **${o.ticker}** (${o.type}): ${o.reason} — Score: ${o.score}/10`).join("\n")}`;
        }
        return "No new opportunities detected right now. Check back during market hours for fresh signals.";
      }
    }

    if (query.toLowerCase().includes("risk") || query.toLowerCase().includes("alert")) {
      const res = await fetch("/api/v1/decisions/alerts", { headers });
      if (res.ok) {
        const data = await res.json();
        if (data.alerts?.length) {
          return `⚠️ **Active Alerts**\n\n${data.alerts.slice(0, 5).map((a: any) => `• [${a.severity}] ${a.title}: ${a.message}`).join("\n")}`;
        }
        return "✅ No active risk alerts. Your portfolio looks healthy.";
      }
    }

    // If we have a ticker but no specific intent, try a full analysis
    if (ticker) {
      const res = await fetch(`/api/v1/ai/analyze/${ticker}`, {
        method: "POST",
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.responses && data.responses.length > 0) {
          const agents = data.responses.map((r: any) =>
            `• **${r.agent_name}** (${r.score}/10): ${r.summary}`
          ).join("\n");
          return `📊 **Analysis for ${ticker}**\n\n${agents}`;
        }
        // If no agent responses, show whatever data came back
        return `📊 **${ticker}** — Analysis completed but no detailed scores available. The AI agents may need market data (try during market hours).`;
      }
      return `I couldn't find data for "${ticker}". Make sure it's a valid NSE ticker symbol (e.g., RELIANCE, TCS, INFY, M&M).`;
    }

    // Generic help
    return "I can help you with:\n\n" +
      "• **Stock analysis** — \"Analyze RELIANCE\" or \"Should I buy TCS?\"\n" +
      "• **Portfolio overview** — \"How's my portfolio?\"\n" +
      "• **Opportunities** — \"Show me opportunities\"\n" +
      "• **Risk alerts** — \"Any risks to watch?\"\n\n" +
      "Just mention a stock ticker in CAPS and I'll analyze it for you!";
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-sky-500 text-white"
                  : "bg-white border border-slate-200 text-slate-800 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              <p className={`mt-1 text-xs ${msg.role === "user" ? "text-sky-200" : "text-slate-400"}`}>
                {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-white border border-slate-200 px-4 py-3 dark:bg-slate-800 dark:border-slate-700">
              <div className="flex gap-1">
                <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="h-2 w-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions (show when no messages beyond welcome) */}
      {messages.length <= 1 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-sky-300 hover:bg-sky-50 transition dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-sky-600"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2 border-t border-slate-200 pt-4 dark:border-slate-700">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask your AI advisor..."
          className="input flex-1"
          disabled={loading}
        />
        <VoiceInput
          onResult={(text) => { setInput(text); }}
          className="h-10 w-10 flex-shrink-0"
        />
        <button
          onClick={() => sendMessage()}
          disabled={!input.trim() || loading}
          className="rounded-lg bg-sky-500 px-5 py-2 text-sm font-medium text-white hover:bg-sky-600 disabled:opacity-50 transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}
