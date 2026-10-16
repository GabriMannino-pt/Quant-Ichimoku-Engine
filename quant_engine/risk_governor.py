from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    position_lots: float
    stop_distance_price: float
    reason: str


class DeterministicRiskGovernor:
    """
    Enforces institutional & prop-desk risk limits:
    - Maximum fractional risk per trade (default 0.50% of equity)
    - Maximum daily drawdown circuit breaker (default 3.50%)
    - Maximum overall drawdown circuit breaker (default 8.00%)
    """

    def __init__(
        self,
        risk_per_trade_pct: float = 0.005,
        max_daily_dd_pct: float = 0.035,
        max_total_dd_pct: float = 0.08,
        atr_stop_multiplier: float = 2.0,
    ):
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_dd_pct = max_daily_dd_pct
        self.max_total_dd_pct = max_total_dd_pct
        self.atr_stop_multiplier = atr_stop_multiplier

    def evaluate_order(
        self,
        initial_equity: float,
        day_start_equity: float,
        current_equity: float,
        atr_value: float,
        contract_value_per_point: float = 10.0,
    ) -> RiskDecision:
        if current_equity <= 0 or initial_equity <= 0 or day_start_equity <= 0:
            return RiskDecision(False, 0.0, 0.0, "INVALID_EQUITY_STATE")

        daily_dd = (day_start_equity - current_equity) / day_start_equity
        if daily_dd >= self.max_daily_dd_pct:
            return RiskDecision(False, 0.0, 0.0, "DAILY_DRAWDOWN_CIRCUIT_BREAKER_TRIPPED")

        total_dd = (initial_equity - current_equity) / initial_equity
        if total_dd >= self.max_total_dd_pct:
            return RiskDecision(False, 0.0, 0.0, "MAX_TOTAL_DRAWDOWN_BREAKER_TRIPPED")

        if atr_value <= 0:
            return RiskDecision(False, 0.0, 0.0, "INVALID_ATR_VOLATILITY")

        stop_distance = round(atr_value * self.atr_stop_multiplier, 5)
        risk_budget_currency = current_equity * self.risk_per_trade_pct
        raw_lots = risk_budget_currency / (stop_distance * contract_value_per_point)
        lots = max(0.01, round(raw_lots, 2))

        return RiskDecision(True, lots, stop_distance, "APPROVED")
