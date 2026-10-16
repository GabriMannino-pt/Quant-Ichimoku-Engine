from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass(frozen=True)
class OHLCBar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class IchimokuSnapshot:
    timestamp: str
    close: float
    tenkan_sen: Optional[float]
    kijun_sen: Optional[float]
    senkou_span_a: Optional[float]
    senkou_span_b: Optional[float]
    atr_14: Optional[float]
    regime: str  # "BULLISH_ABOVE_KUMO" | "BEARISH_BELOW_KUMO" | "NEUTRAL_INSIDE_KUMO" | "WARMUP"


class IchimokuVectorEngine:
    """
    Causal (Zero Look-Ahead) Ichimoku Kinko Hyo & ATR calculator.
    """

    def __init__(self, tenkan_period: int = 9, kijun_period: int = 26, senkou_b_period: int = 52, atr_period: int = 14):
        self.tenkan_period = tenkan_period
        self.kijun_period = kijun_period
        self.senkou_b_period = senkou_b_period
        self.atr_period = atr_period

    @staticmethod
    def _donchian_mid(bars: List[OHLCBar], end_idx: int, period: int) -> Optional[float]:
        if end_idx + 1 < period:
            return None
        window = bars[end_idx + 1 - period : end_idx + 1]
        highest = max(b.high for b in window)
        lowest = min(b.low for b in window)
        return round((highest + lowest) / 2.0, 6)

    def _compute_atr(self, bars: List[OHLCBar], end_idx: int) -> Optional[float]:
        if end_idx < self.atr_period:
            return None
        trs: List[float] = []
        for i in range(end_idx - self.atr_period + 1, end_idx + 1):
            cur = bars[i]
            prev_close = bars[i - 1].close
            tr = max(cur.high - cur.low, abs(cur.high - prev_close), abs(cur.low - prev_close))
            trs.append(tr)
        return round(sum(trs) / len(trs), 6)

    def evaluate_series(self, bars: List[OHLCBar]) -> List[IchimokuSnapshot]:
        snapshots: List[IchimokuSnapshot] = []
        raw_tenkan: List[Optional[float]] = []
        raw_kijun: List[Optional[float]] = []
        raw_span_b: List[Optional[float]] = []

        for idx, bar in enumerate(bars):
            t_val = self._donchian_mid(bars, idx, self.tenkan_period)
            k_val = self._donchian_mid(bars, idx, self.kijun_period)
            sb_val = self._donchian_mid(bars, idx, self.senkou_b_period)
            raw_tenkan.append(t_val)
            raw_kijun.append(k_val)
            raw_span_b.append(sb_val)

            # Causal Kumo at current bar is projected from (idx - kijun_period)
            proj_idx = idx - self.kijun_period
            span_a: Optional[float] = None
            span_b: Optional[float] = None
            if proj_idx >= 0 and raw_tenkan[proj_idx] is not None and raw_kijun[proj_idx] is not None:
                span_a = round((raw_tenkan[proj_idx] + raw_kijun[proj_idx]) / 2.0, 6)
                span_b = raw_span_b[proj_idx]

            atr_val = self._compute_atr(bars, idx)

            if span_a is None or span_b is None or t_val is None or k_val is None:
                regime = "WARMUP"
            else:
                kumo_top = max(span_a, span_b)
                kumo_bottom = min(span_a, span_b)
                if bar.close > kumo_top and t_val > k_val:
                    regime = "BULLISH_ABOVE_KUMO"
                elif bar.close < kumo_bottom and t_val < k_val:
                    regime = "BEARISH_BELOW_KUMO"
                else:
                    regime = "NEUTRAL_INSIDE_KUMO"

            snapshots.append(
                IchimokuSnapshot(
                    timestamp=bar.timestamp,
                    close=bar.close,
                    tenkan_sen=t_val,
                    kijun_sen=k_val,
                    senkou_span_a=span_a,
                    senkou_span_b=span_b,
                    atr_14=atr_val,
                    regime=regime,
                )
            )
        return snapshots
