import unittest
from quant_engine.ichimoku_core import OHLCBar, IchimokuVectorEngine
from quant_engine.risk_governor import DeterministicRiskGovernor
from quant_engine.walk_forward_validator import WalkForwardValidator


class TestQuantIchimokuEngine(unittest.TestCase):

    def _generate_trending_bars(self, count: int = 90, direction: float = 1.0):
        bars = []
        price = 100.0
        for i in range(count):
            open_p = price
            close_p = round(open_p + direction * 0.8, 4)
            high_p = round(max(open_p, close_p) + 0.5, 4)
            low_p = round(min(open_p, close_p) - 0.3, 4)
            bars.append(OHLCBar(timestamp=f"2026-01-{(i % 28) + 1:02d}T00:00:00Z", open=open_p, high=high_p, low=low_p, close=close_p))
            price = close_p
        return bars

    def test_causal_ichimoku_warmup_and_bullish_regime(self):
        engine = IchimokuVectorEngine(tenkan_period=9, kijun_period=26, senkou_b_period=52, atr_period=14)
        bars = self._generate_trending_bars(90, direction=1.0)
        snapshots = engine.evaluate_series(bars)

        self.assertEqual(len(snapshots), 90)
        self.assertEqual(snapshots[0].regime, "WARMUP")
        self.assertIsNone(snapshots[5].tenkan_sen)
        self.assertIsNotNone(snapshots[8].tenkan_sen)

        # After 52 + 26 = 78 bars, Senkou Span B projected forward is populated
        final_snap = snapshots[-1]
        self.assertEqual(final_snap.regime, "BULLISH_ABOVE_KUMO")
        self.assertGreater(final_snap.tenkan_sen, final_snap.kijun_sen)
        self.assertGreater(final_snap.atr_14, 0.0)

    def test_causal_ichimoku_bearish_regime(self):
        engine = IchimokuVectorEngine()
        bars = self._generate_trending_bars(90, direction=-1.0)
        snapshots = engine.evaluate_series(bars)
        self.assertEqual(snapshots[-1].regime, "BEARISH_BELOW_KUMO")
        self.assertLess(snapshots[-1].tenkan_sen, snapshots[-1].kijun_sen)

    def test_risk_governor_circuit_breakers_and_sizing(self):
        gov = DeterministicRiskGovernor(risk_per_trade_pct=0.005, max_daily_dd_pct=0.035, max_total_dd_pct=0.08)

        # 1. Normal approved order
        dec_ok = gov.evaluate_order(initial_equity=100000, day_start_equity=100000, current_equity=100000, atr_value=2.5)
        self.assertTrue(dec_ok.approved)
        self.assertEqual(dec_ok.stop_distance_price, 5.0)
        self.assertEqual(dec_ok.position_lots, 10.0)

        # 2. Daily drawdown circuit breaker (4% drop today > 3.5% limit)
        dec_daily = gov.evaluate_order(initial_equity=100000, day_start_equity=100000, current_equity=95500, atr_value=2.5)
        self.assertFalse(dec_daily.approved)
        self.assertEqual(dec_daily.reason, "DAILY_DRAWDOWN_CIRCUIT_BREAKER_TRIPPED")

        # 3. Total drawdown circuit breaker (9% drop overall > 8.0% limit)
        dec_total = gov.evaluate_order(initial_equity=100000, day_start_equity=92000, current_equity=90500, atr_value=2.5)
        self.assertFalse(dec_total.approved)
        self.assertEqual(dec_total.reason, "MAX_TOTAL_DRAWDOWN_BREAKER_TRIPPED")

    def test_walk_forward_validator_pass_and_fail_gates(self):
        validator = WalkForwardValidator()
        is_returns = [1.2, -0.5, 1.5, 0.8, -0.4, 1.1, 0.9, -0.3, 1.4, 0.7]
        oos_returns = [1.0, -0.4, 1.1, 0.7, -0.3, 0.9, 0.8, -0.4, 1.2, 0.6]

        res = validator.validate_split(is_returns, oos_returns)
        self.assertTrue(res["passed_stress_gate"])
        self.assertGreater(res["out_of_sample"]["profit_factor"], 1.5)
        self.assertGreater(res["oos_sharpe_retention"], 0.6)


if __name__ == "__main__":
    unittest.main()
