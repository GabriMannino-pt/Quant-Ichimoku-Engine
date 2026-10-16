//+------------------------------------------------------------------+
//|                                      IchimokuExecutionBridge.mq5 |
//|                        Gabriele Mannino - Quant-Ichimoku-Engine  |
//|         Low-Latency MQL5 Execution Bridge with Drawdown Breakers |
//+------------------------------------------------------------------+
#property copyright "Gabriele Mannino"
#property version   "1.80"
#property strict

input double InpRiskPerTradePct   = 0.50;   // Risk per trade (% of Equity)
input double InpMaxDailyDDPct     = 3.50;   // Max Daily Drawdown Circuit Breaker (%)
input int    InpMaxSpreadPoints   = 25;     // Max Allowed Spread (Points)
input int    InpTenkanPeriod      = 9;      // Ichimoku Tenkan-sen Period
input int    InpKijunPeriod       = 26;     // Ichimoku Kijun-sen Period
input int    InpSenkouBPeriod     = 52;     // Ichimoku Senkou Span B Period
input ulong  InpMagicNumber       = 180902; // Strategy Execution Identifier

int handleIchimoku = INVALID_HANDLE;
int handleATR      = INVALID_HANDLE;
double dayStartEquity = 0.0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   handleIchimoku = iIchimoku(_Symbol, _Period, InpTenkanPeriod, InpKijunPeriod, InpSenkouBPeriod);
   handleATR      = iATR(_Symbol, _Period, 14);

   if(handleIchimoku == INVALID_HANDLE || handleATR == INVALID_HANDLE)
   {
      Print("[CRITICAL] Failed to initialize Ichimoku or ATR indicator handles.");
      return(INIT_FAILED);
   }

   dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Check institutional spread and daily drawdown circuit breakers   |
//+------------------------------------------------------------------+
bool IsExecutionPermitted()
{
   long currentSpread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(currentSpread > InpMaxSpreadPoints)
      return(false);

   double currentEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(dayStartEquity > 0.0)
   {
      double dailyDDPct = ((dayStartEquity - currentEquity) / dayStartEquity) * 100.0;
      if(dailyDDPct >= InpMaxDailyDDPct)
      {
         PrintFormat("[CIRCUIT BREAKER] Daily Drawdown %.2f%% exceeded limit %.2f%%.", dailyDDPct, InpMaxDailyDDPct);
         return(false);
      }
   }
   return(true);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   if(!IsExecutionPermitted())
      return;

   double tenkan[], kijun[], spanA[], spanB[], atr[];
   ArraySetAsSeries(tenkan, true);
   ArraySetAsSeries(kijun, true);
   ArraySetAsSeries(spanA, true);
   ArraySetAsSeries(spanB, true);
   ArraySetAsSeries(atr, true);

   if(CopyBuffer(handleIchimoku, 0, 1, 2, tenkan) < 2) return;
   if(CopyBuffer(handleIchimoku, 1, 1, 2, kijun)  < 2) return;
   if(CopyBuffer(handleIchimoku, 2, 1, 2, spanA)  < 2) return;
   if(CopyBuffer(handleIchimoku, 3, 1, 2, spanB)  < 2) return;
   if(CopyBuffer(handleATR,      0, 1, 1, atr)    < 1) return;

   double close1 = iClose(_Symbol, _Period, 1);
   double kumoTop = MathMax(spanA[0], spanB[0]);
   double kumoBot = MathMin(spanA[0], spanB[0]);

   // Causal closed-bar validation (bar index 1)
   bool bullishBreakout = (close1 > kumoTop && tenkan[0] > kijun[0] && tenkan[1] <= kijun[1]);
   bool bearishBreakout = (close1 < kumoBot && tenkan[0] < kijun[0] && tenkan[1] >= kijun[1]);

   if(bullishBreakout || bearishBreakout)
   {
      PrintFormat("[SIGNAL VERIFIED] %s | Close=%.5f | Kumo=[%.5f, %.5f] | ATR=%.5f",
                  bullishBreakout ? "BULLISH_KUMO_TK" : "BEARISH_KUMO_TK",
                  close1, kumoBot, kumoTop, atr[0]);
   }
}
//+------------------------------------------------------------------+
