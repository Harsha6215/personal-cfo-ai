"""
Technical Analysis Agent — Story 4.4

Role: Technical Trader — analyzes price patterns, trend, momentum.
Input: Historical Prices (OHLCV).
Output: Trend, RSI, MACD, Support/Resistance levels.

Uses computation FIRST (RSI, MACD, MAs), then LLM to interpret.
"""

from datetime import date, timedelta

from ai_services.agents.base import AgentContext, AgentResponse, BaseAgent
from ai_services.agents.llm import LLMProvider


def _compute_rsi(prices: list[float], period: int = 14) -> float:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return 50.0  # neutral if not enough data

    gains, losses = [], []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _compute_macd(prices: list[float]) -> dict:
    """Calculate MACD (12, 26, 9)."""
    if len(prices) < 26:
        return {"macd": 0, "signal": 0, "histogram": 0}

    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * k + result[-1] * (1 - k))
        return result

    ema12 = ema(prices, 12)
    ema26 = ema(prices, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = ema(macd_line[-9:], 9) if len(macd_line) >= 9 else [0]

    macd_val = macd_line[-1]
    signal_val = signal_line[-1]
    return {
        "macd": round(macd_val, 2),
        "signal": round(signal_val, 2),
        "histogram": round(macd_val - signal_val, 2),
    }


def _compute_moving_averages(prices: list[float]) -> dict:
    """Calculate key moving averages."""
    result = {}
    current = prices[-1] if prices else 0
    for period in [20, 50, 200]:
        if len(prices) >= period:
            ma = sum(prices[-period:]) / period
            result[f"sma_{period}"] = round(ma, 2)
            result[f"above_sma_{period}"] = current > ma
    return result


def _find_support_resistance(prices: list[float]) -> dict:
    """Simple support/resistance from recent highs/lows."""
    if len(prices) < 20:
        return {}
    recent = prices[-60:] if len(prices) >= 60 else prices
    return {
        "support": round(min(recent[-20:]), 2),
        "resistance": round(max(recent[-20:]), 2),
        "recent_low": round(min(recent), 2),
        "recent_high": round(max(recent), 2),
    }


class TechnicalAnalystAgent(BaseAgent):
    name = "technical_analyst"
    role = "Technical Trader — Price Patterns, Trend & Momentum Analysis"
    required_data = ["price_history", "quote"]

    @property
    def system_prompt(self) -> str:
        return """You are a professional Technical Analyst / Chartist.
You analyze price data and technical indicators to determine trend and momentum.

STRICT RULES:
- Base your analysis on the computed indicators provided (RSI, MACD, MAs, Support/Resistance)
- Determine overall trend: Bullish, Bearish, or Sideways
- Identify key levels and signals
- Do NOT look at fundamentals — only price action
- Score from 0 to 10 (10 = extremely bullish technical setup)

RESPOND ONLY IN THIS JSON FORMAT:
{
    "score": 6.5,
    "sentiment": "neutral",
    "confidence": 68,
    "analysis": "Stock is trading above 50 SMA but below 200 SMA with RSI at 58, suggesting neutral to mildly bullish momentum.",
    "evidence": [
        "RSI at 58 — neutral zone",
        "MACD histogram positive — momentum improving",
        "Price above 50-day MA (₹3,450) — short-term bullish",
        "Support at ₹3,200, Resistance at ₹3,680"
    ],
    "metrics": {
        "trend": "sideways_to_bullish",
        "rsi": 58,
        "macd_signal": "bullish_crossover",
        "support": 3200,
        "resistance": 3680
    }
}"""

    def build_prompt(self, context: AgentContext) -> str:
        parts = [f"Technical analysis for {context.ticker}.\n"]

        # Current price
        if context.quote:
            parts.append(f"Current Price: ₹{context.quote.get('price', 0):.2f}")
            parts.append(f"Day Change: {context.quote.get('change_pct', 0):.2f}%")
            if context.quote.get('high_52w'):
                parts.append(f"52W High: ₹{context.quote['high_52w']:.0f}")
            if context.quote.get('low_52w'):
                parts.append(f"52W Low: ₹{context.quote['low_52w']:.0f}")

        # Compute indicators from price_history
        prices = []
        if context.price_history:
            prices = [bar.get("close", bar) if isinstance(bar, dict) else bar for bar in context.price_history]

        if prices:
            # RSI
            rsi = _compute_rsi(prices)
            parts.append(f"\n--- COMPUTED INDICATORS ---")
            parts.append(f"RSI (14): {rsi}")

            # MACD
            macd = _compute_macd(prices)
            parts.append(f"MACD: {macd['macd']}, Signal: {macd['signal']}, Histogram: {macd['histogram']}")

            # Moving averages
            mas = _compute_moving_averages(prices)
            for key, val in mas.items():
                parts.append(f"{key.upper()}: {val}")

            # Support / Resistance
            levels = _find_support_resistance(prices)
            if levels:
                parts.append(f"Support: ₹{levels.get('support', 0)}")
                parts.append(f"Resistance: ₹{levels.get('resistance', 0)}")

            parts.append(f"\nPrice data points: {len(prices)} days")
            parts.append(f"Latest 5 closes: {[round(p, 1) for p in prices[-5:]]}")
        else:
            parts.append("\nNo price history available for technical analysis.")

        return "\n".join(parts)

    async def execute(self, context: AgentContext, llm: LLMProvider) -> AgentResponse:
        # Fetch price history if not in context
        if not context.price_history:
            try:
                import sys, os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
                from backend.services.market_data import MarketDataService, YahooFinanceProvider
                market = MarketDataService(provider=YahooFinanceProvider())
                end = date.today()
                start = end - timedelta(days=200)
                bars = await market.get_history(context.ticker, start, end)
                context.price_history = [{"close": b.close} for b in bars]
            except Exception:
                pass

        prompt = self.build_prompt(context)
        result = await llm.generate_json(self.system_prompt, prompt)

        return AgentResponse(
            agent_name=self.name,
            agent_role=self.role,
            ticker=context.ticker,
            analysis=result.get("analysis", "Technical analysis unavailable."),
            score=result.get("score"),
            sentiment=result.get("sentiment"),
            confidence=result.get("confidence", 0),
            evidence=result.get("evidence", []),
            metrics=result.get("metrics", {}),
            recommendation=None,
        )
