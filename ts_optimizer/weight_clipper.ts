/**
 * Neural Feature Weight Optimizer & Gradient Clipper for Multi-Timeframe Ichimoku Signals.
 * Prevents runaway weight explosion during high-volatility regime transitions.
 */

export interface FeatureWeightVector {
  tenkanKijunCross: number;
  kumoBreakout: number;
  chikouMomentum: number;
  atrRegimeFilter: number;
}

export class NeuralWeightClipper {
  private readonly maxAbsWeight: number;
  private readonly learningRate: number;

  constructor(maxAbsWeight = 1.5, learningRate = 0.01) {
    this.maxAbsWeight = maxAbsWeight;
    this.learningRate = learningRate;
  }

  public clipAndNormalize(weights: FeatureWeightVector): FeatureWeightVector {
    const raw = [
      this.clamp(weights.tenkanKijunCross),
      this.clamp(weights.kumoBreakout),
      this.clamp(weights.chikouMomentum),
      this.clamp(weights.atrRegimeFilter),
    ];

    const l1Norm = raw.reduce((acc, v) => acc + Math.abs(v), 0);
    if (l1Norm < 1e-9) {
      return { tenkanKijunCross: 0.25, kumoBreakout: 0.25, chikouMomentum: 0.25, atrRegimeFilter: 0.25 };
    }

    return {
      tenkanKijunCross: Number((raw[0] / l1Norm).toFixed(6)),
      kumoBreakout: Number((raw[1] / l1Norm).toFixed(6)),
      chikouMomentum: Number((raw[2] / l1Norm).toFixed(6)),
      atrRegimeFilter: Number((raw[3] / l1Norm).toFixed(6)),
    };
  }

  public applyGradientStep(
    current: FeatureWeightVector,
    gradients: FeatureWeightVector,
    rewardSignal: number
  ): FeatureWeightVector {
    const step = this.learningRate * Math.max(-1, Math.min(1, rewardSignal));
    return this.clipAndNormalize({
      tenkanKijunCross: current.tenkanKijunCross + step * gradients.tenkanKijunCross,
      kumoBreakout: current.kumoBreakout + step * gradients.kumoBreakout,
      chikouMomentum: current.chikouMomentum + step * gradients.chikouMomentum,
      atrRegimeFilter: current.atrRegimeFilter + step * gradients.atrRegimeFilter,
    });
  }

  private clamp(val: number): number {
    if (!Number.isFinite(val)) return 0;
    return Math.max(-this.maxAbsWeight, Math.min(this.maxAbsWeight, val));
  }
}
