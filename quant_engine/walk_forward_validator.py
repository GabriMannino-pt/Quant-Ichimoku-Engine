import math
from typing import List, Dict, Any


class WalkForwardValidator:
    """
    Evaluates strategy trade returns across In-Sample (IS) and Out-of-Sample (OOS) splits
    to prevent curve-fitting and measure OOS retention efficiency.
    """

    @staticmethod
    def compute_metrics(trade_returns: List[float]) -> Dict[str, float]:
        if not trade_returns:
            return {
                "trade_count": 0,
                "net_return": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
            }

        gross_profit = sum(r for r in trade_returns if r > 0)
        gross_loss = abs(sum(r for r in trade_returns if r < 0))
        profit_factor = round(gross_profit / gross_loss, 4) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        mean_ret = sum(trade_returns) / len(trade_returns)
        variance = sum((r - mean_ret) ** 2 for r in trade_returns) / max(1, len(trade_returns) - 1)
        std_dev = math.sqrt(variance)
        sharpe = round((mean_ret / std_dev) * math.sqrt(252), 4) if std_dev > 1e-9 else 0.0

        # Cumulative equity curve & max drawdown
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in trade_returns:
            cum += r
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd

        wins = sum(1 for r in trade_returns if r > 0)
        return {
            "trade_count": len(trade_returns),
            "net_return": round(sum(trade_returns), 4),
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown": round(max_dd, 4),
            "win_rate": round(wins / len(trade_returns), 4),
        }

    def validate_split(self, in_sample_returns: List[float], out_of_sample_returns: List[float]) -> Dict[str, Any]:
        is_metrics = self.compute_metrics(in_sample_returns)
        oos_metrics = self.compute_metrics(out_of_sample_returns)

        oos_retention = 0.0
        if is_metrics["sharpe_ratio"] > 0:
            oos_retention = round(oos_metrics["sharpe_ratio"] / is_metrics["sharpe_ratio"], 4)

        passed = (
            oos_metrics["profit_factor"] >= 1.15
            and oos_metrics["sharpe_ratio"] >= 0.8
            and oos_retention >= 0.50
        )

        return {
            "in_sample": is_metrics,
            "out_of_sample": oos_metrics,
            "oos_sharpe_retention": oos_retention,
            "passed_stress_gate": passed,
        }
