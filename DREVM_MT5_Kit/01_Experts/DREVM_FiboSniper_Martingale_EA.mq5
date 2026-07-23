//+------------------------------------------------------------------+
//|                                DREVM_FiboSniper_Martingale_EA.mq5 |
//|                          GoldXrodgers / DREVM — Négus Dja        |
//|                                                                  |
//|  ⚠️  VERSION COMPTE PERSONNEL (~200$) — MARTINGALE CONTRÔLÉE     |
//|                                                                  |
//|  Même moteur de signal que DREVM_FiboSniper_Auto_EA :            |
//|  Fibo sniper + biais EMA + sweep + BOS M5 + grade confluence.    |
//|                                                                  |
//|  Money management : multiplicateur après perte, reset après      |
//|  gain — MAIS avec disjoncteurs stricts :                         |
//|   • Cap de niveaux martingale (défaut 3 doublements max)         |
//|   • Cap de lot absolu (défaut 0.08)                              |
//|   • Stop-out équity : arrêt définitif si equity < seuil          |
//|   • Cooldown après reset forcé                                   |
//|                                                                  |
//|  AVERTISSEMENT : la martingale augmente exponentiellement le     |
//|  risque de ruine. Sur 200$, une série de pertes normale peut     |
//|  détruire le compte. N'utiliser qu'avec de l'argent qu'on        |
//|  accepte de perdre ENTIÈREMENT.                                  |
//+------------------------------------------------------------------+
#property copyright "DREVM / GoldXrodgers"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "DREVM_CorrelationGuard.mqh"
CTrade trade;

//=== ENUMS ==========================================================
enum ENUM_EXEC_MODE
  {
   MODE_ALERT_ONLY = 0,   // Alertes seulement
   MODE_MARKET     = 1    // Exécution automatique
  };

enum ENUM_GRADE
  {
   GRADE_D  = 0,
   GRADE_C  = 1,
   GRADE_B  = 2,
   GRADE_A  = 3,
   GRADE_AP = 4
  };

//=== INPUTS =========================================================
input group "=== EXECUTION ==="
input ENUM_EXEC_MODE InpExecMode        = MODE_ALERT_ONLY; // Mode d'exécution
input long           InpMagic           = 20260718;        // Magic number
input ENUM_GRADE     InpMinGrade        = GRADE_B;         // Grade minimum

input group "=== MARTINGALE CONTRÔLÉE (compte ~200$) ==="
input double         InpBaseLot         = 0.01;            // Lot de base (niveau 0)
input double         InpMultiplier      = 2.0;             // Multiplicateur après perte
input int            InpMaxSteps        = 3;               // Niveaux max APRÈS le lot de base (0.01->0.02->0.04->0.08)
input double         InpAbsMaxLot       = 0.08;            // Cap de lot ABSOLU (jamais dépassé)
input int            InpCooldownBars    = 24;              // Bougies M5 de pause après reset forcé

input group "=== DISJONCTEURS (non négociables) ==="
input double         InpEquityStopOut   = 140.0;           // Arrêt DÉFINITIF si equity < (devise du compte)
input double         InpDailyLossStop   = 30.0;            // Arrêt du jour si perte jour > (devise)
input int            InpMaxTradesPerDay = 4;               // Nombre max de trades par jour
input double         InpMaxSpreadPoints = 50;              // Spread max pour trader (points)

input group "=== BIAIS HTF (EMA) ==="
input ENUM_TIMEFRAMES InpBiasTF         = PERIOD_H1;
input int            InpEmaFast         = 50;
input int            InpEmaSlow         = 200;

input group "=== FIBONACCI SNIPER ==="
input ENUM_TIMEFRAMES InpSwingTF        = PERIOD_H1;
input int            InpSwingLookback   = 120;
input int            InpSwingStrength   = 3;
input double         InpFibEntryMin     = 61.8;
input double         InpFibEntryMax     = 95.0;
input double         InpFibInvalid      = 100.0;

input group "=== TRIGGER M5 (SWEEP + BOS) ==="
input int            InpSweepLookback   = 20;
input int            InpBosLookback     = 10;
input int            InpTriggerExpiry   = 12;

input group "=== SORTIES ==="
input double         InpRRTarget        = 1.5;             // R/R cible (plus court en martingale)
input bool           InpUseAtrTrailing  = true;
input int            InpAtrPeriod       = 14;
input double         InpAtrMult         = 2.0;

input group "=== NEWS BLACKOUT ==="
input string         InpNewsTimes       = "";              // "YYYY.MM.DD HH:MM-HH:MM;..."
input int            InpNewsBufferMin   = 2;

input group "=== ALERTES ==="
input bool           InpPushNotif       = true;
input bool           InpPopupAlert      = true;

input group "=== TELEGRAM ==="
input bool           InpTelegramEnable  = true;            // Activer alertes Telegram
input string         InpTelegramToken   = "";              // Bot token (BotFather)
input string         InpTelegramChatId  = "";              // Chat ID (ex: 123456789)

input group "=== AFFICHAGE ==="
input bool           InpDisplaySober    = true;            // Affichage sobre (minimal)
input bool           InpDrawZones       = true;            // Dessiner range high/low + Fibo
input color          InpColorHigh       = C'239,68,68';    // Zone high (rouge #ef4444)
input color          InpColorLow        = C'16,185,129';   // Zone low (vert #10b981)
input color          InpColorSniper     = C'234,179,8';    // Zone sniper 61.8-95 (jaune #eab308)
input color          InpColorFibLines   = clrDimGray;      // Lignes Fibo intermédiaires

//=== ETAT GLOBAL ====================================================
int      hEmaFast = INVALID_HANDLE;
int      hEmaSlow = INVALID_HANDLE;
int      hAtrM5   = INVALID_HANDLE;

datetime lastM5BarTime = 0;

double   swingHigh = 0.0, swingLow = 0.0;
datetime swingHighTime = 0, swingLowTime = 0;
int      trendFibo = 0;

bool     sweepDetected  = false;
int      sweepDirection = 0;
datetime sweepTime      = 0;

string   gvPrefix = "";

// Martingale state (persistant)
int      martiStep     = 0;      // niveau courant (0 = lot de base)
int      cooldownLeft  = 0;      // bougies M5 restantes de pause
bool     hardStopped   = false;  // stop-out équity déclenché (définitif)

double   dayStartEquity = 0.0;
datetime dayStartStamp  = 0;
bool     dayStopped     = false;
int      tradesToday    = 0;     // compteur de trades ouverts aujourd'hui

//+------------------------------------------------------------------+
string GV(const string key) { return gvPrefix + key; }
double GVGet(const string key, double defVal)
  {
   if(GlobalVariableCheck(GV(key))) return GlobalVariableGet(GV(key));
   return defVal;
  }
void GVSet(const string key, double val) { GlobalVariableSet(GV(key), val); }

//+------------------------------------------------------------------+
int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);

   gvPrefix = "DREVMM_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_" +
              IntegerToString(InpMagic) + "_" + _Symbol + "_";

   hEmaFast = iMA(_Symbol, InpBiasTF, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, InpBiasTF, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hAtrM5   = iATR(_Symbol, PERIOD_M5, InpAtrPeriod);
   if(hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE || hAtrM5 == INVALID_HANDLE)
      return INIT_FAILED;

   // Restaurer l'état martingale après restart
   martiStep    = (int)GVGet("martiStep", 0.0);
   cooldownLeft = (int)GVGet("cooldownLeft", 0.0);
   hardStopped  = (GVGet("hardStopped", 0.0) > 0.5);

   ResetDailyAnchor();

   // Vérification cohérence : la séquence max doit rester sous le cap absolu
   double worstLot = InpBaseLot * MathPow(InpMultiplier, InpMaxSteps);
   if(worstLot > InpAbsMaxLot)
      PrintFormat("DREVM-M ⚠️ Séquence max %.2f lots > cap %.2f — le cap tronquera la martingale.",
                  worstLot, InpAbsMaxLot);

   PrintFormat("DREVM-M init | Mode=%s | Base=%.2f x%.1f max %d étapes | StopOut equity < %.2f",
               InpExecMode == MODE_ALERT_ONLY ? "ALERT_ONLY" : "MARKET",
               InpBaseLot, InpMultiplier, InpMaxSteps, InpEquityStopOut);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(hEmaFast != INVALID_HANDLE) IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE) IndicatorRelease(hEmaSlow);
   if(hAtrM5   != INVALID_HANDLE) IndicatorRelease(hAtrM5);
   DeleteZones();
   Comment("");
  }

//+------------------------------------------------------------------+
//| OnTrade — détecter la clôture d'une position pour la séquence    |
//+------------------------------------------------------------------+
void OnTrade()
  {
   // Balayer l'historique récent des deals de cet EA
   datetime from = TimeCurrent() - 7 * 24 * 3600;
   if(!HistorySelect(from, TimeCurrent())) return;

   int total = HistoryDealsTotal();
   if(total <= 0) return;

   // Dernier deal de sortie de notre magic/symbole
   for(int i = total - 1; i >= 0; i--)
     {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(dealTicket == 0) continue;
      if(HistoryDealGetString(dealTicket, DEAL_SYMBOL) != _Symbol) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetInteger(dealTicket, DEAL_ENTRY) != DEAL_ENTRY_OUT) continue;

      // Déjà traité ?
      double lastProcessed = GVGet("lastDeal", 0.0);
      if((double)dealTicket <= lastProcessed) return;
      GVSet("lastDeal", (double)dealTicket);

      double profit = HistoryDealGetDouble(dealTicket, DEAL_PROFIT)
                    + HistoryDealGetDouble(dealTicket, DEAL_SWAP)
                    + HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);

      if(profit >= 0.0)
        {
         // GAIN -> reset séquence
         if(martiStep > 0)
            Notify(StringFormat("DREVM-M %s ✅ gain %.2f — séquence reset (était niveau %d)",
                   _Symbol, profit, martiStep));
         martiStep = 0;
        }
      else
        {
         // PERTE -> niveau suivant, sauf si cap atteint
         martiStep++;
         if(martiStep > InpMaxSteps)
           {
            martiStep    = 0;
            cooldownLeft = InpCooldownBars;
            Notify(StringFormat("DREVM-M %s 🛑 CAP martingale atteint après perte %.2f — RESET FORCÉ + cooldown %d bougies M5",
                   _Symbol, profit, InpCooldownBars));
           }
         else
            Notify(StringFormat("DREVM-M %s ❌ perte %.2f — niveau martingale %d/%d (prochain lot %.2f)",
                   _Symbol, profit, martiStep, InpMaxSteps, NextLot()));
        }

      GVSet("martiStep", (double)martiStep);
      GVSet("cooldownLeft", (double)cooldownLeft);
      return;
     }
  }

//+------------------------------------------------------------------+
double NextLot()
  {
   double lot = InpBaseLot * MathPow(InpMultiplier, martiStep);

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lot = MathFloor(lot / lotStep) * lotStep;
   lot = MathMax(minLot, MathMin(lot, MathMin(maxLot, InpAbsMaxLot))); // CAP ABSOLU
   return lot;
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   ManageOpenPositions();

   datetime m5Time = iTime(_Symbol, PERIOD_M5, 0);
   if(m5Time == lastM5BarTime) return;
   lastM5BarTime = m5Time;

   // ---- close M5 pipeline ----
   UpdateDailyAnchor();
   UpdateCircuitBreakers();

   if(hardStopped)
     {
      UpdateDisplay("⛔ HARD STOP — retirer l'EA");
      return;
     }
   if(dayStopped)
     {
      UpdateDisplay(StringFormat("⛔ Stop jour (-%.0f)", InpDailyLossStop));
      return;
     }
   if(tradesToday >= InpMaxTradesPerDay)
     {
      UpdateDisplay("⛔ Limite trades — demain");
      return;
     }
   if(cooldownLeft > 0)
     {
      cooldownLeft--;
      GVSet("cooldownLeft", (double)cooldownLeft);
      UpdateDisplay(StringFormat("⏸ Cooldown %d bougies", cooldownLeft));
      return;
     }
   if(IsNewsBlackout())
     {
      UpdateDisplay("📰 News blackout");
      return;
     }

   // Spread check (compte 200$ : le spread pèse lourd)
   double spread = (double)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(spread > InpMaxSpreadPoints)
     {
      UpdateDisplay(StringFormat("Spread large (%.0f pts)", spread));
      return;
     }

   DetectSwings();
   if(swingHigh <= 0.0 || swingLow <= 0.0 || swingHigh <= swingLow) return;
   DrawZones();

   int emaBias = GetEmaBias();
   DetectSweep();
   int bosDir  = DetectBos();

   EvaluateSetup(emaBias, bosDir);
  }

//+------------------------------------------------------------------+
int GetEmaBias()
  {
   double fast[1], slow[1];
   if(CopyBuffer(hEmaFast, 0, 1, 1, fast) != 1) return 0;
   if(CopyBuffer(hEmaSlow, 0, 1, 1, slow) != 1) return 0;
   if(fast[0] > slow[0]) return  1;
   if(fast[0] < slow[0]) return -1;
   return 0;
  }

//+------------------------------------------------------------------+
void DetectSwings()
  {
   int bars = MathMin(InpSwingLookback, iBars(_Symbol, InpSwingTF) - InpSwingStrength - 1);
   if(bars < InpSwingStrength * 2 + 1) return;

   double bestHigh = 0.0, bestLow = DBL_MAX;
   datetime bestHighT = 0, bestLowT = 0;

   for(int i = InpSwingStrength + 1; i <= bars; i++)
     {
      double hi = iHigh(_Symbol, InpSwingTF, i);
      double lo = iLow(_Symbol, InpSwingTF, i);

      bool isFracHigh = true, isFracLow = true;
      for(int k = 1; k <= InpSwingStrength; k++)
        {
         if(iHigh(_Symbol, InpSwingTF, i - k) >= hi || iHigh(_Symbol, InpSwingTF, i + k) > hi)
            isFracHigh = false;
         if(iLow(_Symbol, InpSwingTF, i - k) <= lo || iLow(_Symbol, InpSwingTF, i + k) < lo)
            isFracLow = false;
         if(!isFracHigh && !isFracLow) break;
        }

      if(isFracHigh && hi > bestHigh) { bestHigh = hi; bestHighT = iTime(_Symbol, InpSwingTF, i); }
      if(isFracLow  && lo < bestLow)  { bestLow  = lo; bestLowT  = iTime(_Symbol, InpSwingTF, i); }
     }

   if(bestHigh > 0.0 && bestLow < DBL_MAX)
     {
      swingHigh = bestHigh;  swingHighTime = bestHighT;
      swingLow  = bestLow;   swingLowTime  = bestLowT;
      trendFibo = (swingHighTime > swingLowTime) ? 1 : -1;
     }
  }

//+------------------------------------------------------------------+
double CurrentFibPercent()
  {
   double range = swingHigh - swingLow;
   if(range <= 0.0) return -1.0;
   double px = iClose(_Symbol, PERIOD_M5, 1);
   if(trendFibo == 1) return (swingHigh - px) / range * 100.0;
   return (px - swingLow) / range * 100.0;
  }

//+------------------------------------------------------------------+
void DetectSweep()
  {
   if(sweepDetected)
     {
      int barsSince = iBarShift(_Symbol, PERIOD_M5, sweepTime);
      if(barsSince > InpTriggerExpiry) { sweepDetected = false; sweepDirection = 0; }
     }

   int start = 2;
   double refHigh = -DBL_MAX, refLow = DBL_MAX;
   for(int i = start; i < start + InpSweepLookback; i++)
     {
      refHigh = MathMax(refHigh, iHigh(_Symbol, PERIOD_M5, i));
      refLow  = MathMin(refLow,  iLow(_Symbol, PERIOD_M5, i));
     }

   double h1 = iHigh(_Symbol, PERIOD_M5, 1);
   double l1 = iLow(_Symbol, PERIOD_M5, 1);
   double c1 = iClose(_Symbol, PERIOD_M5, 1);

   if(h1 > refHigh && c1 < refHigh)
     { sweepDetected = true; sweepDirection = -1; sweepTime = iTime(_Symbol, PERIOD_M5, 1); }
   else if(l1 < refLow && c1 > refLow)
     { sweepDetected = true; sweepDirection = 1; sweepTime = iTime(_Symbol, PERIOD_M5, 1); }
  }

//+------------------------------------------------------------------+
int DetectBos()
  {
   double structHigh = -DBL_MAX, structLow = DBL_MAX;
   for(int i = 2; i < 2 + InpBosLookback; i++)
     {
      structHigh = MathMax(structHigh, iHigh(_Symbol, PERIOD_M5, i));
      structLow  = MathMin(structLow,  iLow(_Symbol, PERIOD_M5, i));
     }
   double c1 = iClose(_Symbol, PERIOD_M5, 1);
   if(c1 > structHigh) return  1;
   if(c1 < structLow)  return -1;
   return 0;
  }

//+------------------------------------------------------------------+
void EvaluateSetup(const int emaBias, const int bosDir)
  {
   double fibPct = CurrentFibPercent();
   int dir = trendFibo;

   bool cBias  = (emaBias == dir);
   bool cFib   = (fibPct >= InpFibEntryMin && fibPct <= InpFibEntryMax);
   bool cSweep = (sweepDetected && sweepDirection == dir);
   bool cBos   = (bosDir == dir);
   bool cValid = (fibPct < InpFibInvalid && fibPct >= 0.0);

   double entry, sl, tp;
   BuildTradeLevels(dir, entry, sl, tp);
   double risk   = MathAbs(entry - sl);
   double reward = MathAbs(tp - entry);
   bool cRR      = (risk > 0.0 && reward / risk >= InpRRTarget);

   int score = (int)cBias + (int)cFib + (int)cSweep + (int)cBos + (int)cValid + (int)cRR;

   ENUM_GRADE grade;
   if(score >= 6)      grade = GRADE_AP;
   else if(score == 5) grade = GRADE_A;
   else if(score == 4) grade = GRADE_B;
   else if(score == 3) grade = GRADE_C;
   else                grade = GRADE_D;

   double nextLot = NextLot();

   UpdateDisplay("Scan", fibPct, score, GradeToString(grade));

   if(!cSweep || !cBos) return;
   if(grade < InpMinGrade) return;
   if(HasOpenPosition()) return;

   string msg = StringFormat("DREVM-M %s SETUP %s [%s %d/6] Marti niv %d lot %.2f | E:%.2f SL:%.2f TP:%.2f",
               _Symbol, dir > 0 ? "BUY" : "SELL", GradeToString(grade), score,
               martiStep, nextLot, entry, sl, tp);

   if(InpExecMode == MODE_ALERT_ONLY)
     {
      Notify(msg);
      sweepDetected = false;
      return;
     }

   // ── Filtre corrélation : lot ajusté ou veto ──
   double execLot = CorrGuard_AdjustLot(_Symbol, dir, nextLot);
   if(execLot <= 0.0)
     {
      Notify(StringFormat("DREVM-M %s: signal %s [%s] bloqué par CorrGuard (exposition corrélée)",
             _Symbol, dir > 0 ? "BUY" : "SELL", GradeToString(grade)));
      sweepDetected = false;
      return;
     }

   bool ok = (dir > 0)
             ? trade.Buy(execLot, _Symbol, 0.0, sl, tp, "DREVMM_" + GradeToString(grade))
             : trade.Sell(execLot, _Symbol, 0.0, sl, tp, "DREVMM_" + GradeToString(grade));

   if(ok)
     {
      tradesToday++;
      GVSet("tradesToday", (double)tradesToday);
      Notify(msg + StringFormat(" | EXEC ✅ (trade %d/%d du jour)", tradesToday, InpMaxTradesPerDay));
      sweepDetected = false;
     }
   else
      PrintFormat("DREVM-M: échec ordre (%d) %s", trade.ResultRetcode(), trade.ResultComment());
  }

//+------------------------------------------------------------------+
void BuildTradeLevels(const int dir, double &entry, double &sl, double &tp)
  {
   double atr[1];
   double atrVal = 0.0;
   if(CopyBuffer(hAtrM5, 0, 1, 1, atr) == 1) atrVal = atr[0];

   entry = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                     : SymbolInfoDouble(_Symbol, SYMBOL_BID);

   double range   = swingHigh - swingLow;
   double invalid = (dir > 0)
                    ? swingHigh - range * (InpFibInvalid / 100.0)
                    : swingLow  + range * (InpFibInvalid / 100.0);

   double pad = MathMax(atrVal * 0.5, 10 * _Point);
   sl = (dir > 0) ? invalid - pad : invalid + pad;

   double risk = MathAbs(entry - sl);
   tp = (dir > 0) ? entry + risk * InpRRTarget : entry - risk * InpRRTarget;

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   entry = NormalizeDouble(entry, digits);
   sl    = NormalizeDouble(sl, digits);
   tp    = NormalizeDouble(tp, digits);
  }

//+------------------------------------------------------------------+
void ManageOpenPositions()
  {
   if(!InpUseAtrTrailing) return;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      long   type = PositionGetInteger(POSITION_TYPE);
      double open = PositionGetDouble(POSITION_PRICE_OPEN);
      double px   = (type == POSITION_TYPE_BUY)
                    ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                    : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      // Trailing seulement une fois la position en profit > 0.5 x risque initial
      double sl   = PositionGetDouble(POSITION_SL);
      double risk = MathAbs(open - sl);
      if(risk <= 0.0) continue;

      double progressR = (type == POSITION_TYPE_BUY) ? (px - open) / risk : (open - px) / risk;
      if(progressR < 0.5) continue;

      double atr[1];
      if(CopyBuffer(hAtrM5, 0, 1, 1, atr) != 1 || atr[0] <= 0.0) continue;

      double trailSl = (type == POSITION_TYPE_BUY) ? px - atr[0] * InpAtrMult
                                                   : px + atr[0] * InpAtrMult;
      bool improve = (type == POSITION_TYPE_BUY) ? (trailSl > sl) : (trailSl < sl);
      if(improve) trade.PositionModify(ticket, NormalizePrice(trailSl), PositionGetDouble(POSITION_TP));
     }
  }

bool HasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic) return true;
     }
   return false;
  }

double NormalizePrice(double p)
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return NormalizeDouble(p, digits);
  }

//+------------------------------------------------------------------+
//| Disjoncteurs                                                      |
//+------------------------------------------------------------------+
void ResetDailyAnchor()
  {
   dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   dayStartStamp = StructToTime(dt);
   dayStopped = false;
   tradesToday = 0;
   GVSet("tradesToday", 0.0);
   GVSet("dayStartEquity", dayStartEquity);
   GVSet("dayStartStamp", (double)dayStartStamp);
  }

void UpdateDailyAnchor()
  {
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   datetime todayStart = StructToTime(dt);

   datetime savedStamp = (datetime)GVGet("dayStartStamp", 0.0);
   if(savedStamp < todayStart)
      ResetDailyAnchor();
   else
     {
      dayStartEquity = GVGet("dayStartEquity", AccountInfoDouble(ACCOUNT_EQUITY));
      tradesToday    = (int)GVGet("tradesToday", 0.0);
     }
  }

void UpdateCircuitBreakers()
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   // HARD STOP : equity sous le seuil -> arrêt définitif (persistant)
   if(!hardStopped && equity < InpEquityStopOut)
     {
      hardStopped = true;
      GVSet("hardStopped", 1.0);
      Notify(StringFormat("DREVM-M 🚨 HARD STOP-OUT: equity %.2f < %.2f. EA arrêté DÉFINITIVEMENT sur %s.",
             equity, InpEquityStopOut, _Symbol));
     }

   // Stop du jour
   double dayLoss = dayStartEquity - equity;
   if(!dayStopped && dayLoss >= InpDailyLossStop)
     {
      dayStopped = true;
      Notify(StringFormat("DREVM-M ⛔ STOP JOUR: perte %.2f >= %.2f sur %s", dayLoss, InpDailyLossStop, _Symbol));
     }
  }

//+------------------------------------------------------------------+
bool IsNewsBlackout()
  {
   if(StringLen(InpNewsTimes) == 0) return false;

   string windows[];
   int n = StringSplit(InpNewsTimes, ';', windows);
   datetime now = TimeCurrent();

   for(int i = 0; i < n; i++)
     {
      string w = windows[i];
      StringTrimLeft(w); StringTrimRight(w);
      if(StringLen(w) < 16) continue;

      int dashPos = StringFind(w, "-", 11);
      if(dashPos < 0) continue;

      string startStr = StringSubstr(w, 0, dashPos);
      string dateStr  = StringSubstr(w, 0, 10);
      string endStr   = dateStr + " " + StringSubstr(w, dashPos + 1);

      datetime tStart = StringToTime(startStr) - InpNewsBufferMin * 60;
      datetime tEnd   = StringToTime(endStr)   + InpNewsBufferMin * 60;

      if(now >= tStart && now <= tEnd) return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
string GradeToString(const ENUM_GRADE g)
  {
   switch(g)
     {
      case GRADE_AP: return "A+";
      case GRADE_A:  return "A";
      case GRADE_B:  return "B";
      case GRADE_C:  return "C";
      default:       return "D";
     }
  }

void Notify(const string msg)
  {
   Print(msg);
   if(InpPopupAlert) Alert(msg);
   if(InpPushNotif)  SendNotification(msg);
   if(InpTelegramEnable) SendTelegram(msg);
  }

//+------------------------------------------------------------------+
//| Dessin des zones range high/low + niveaux Fibonacci sniper       |
//+------------------------------------------------------------------+
#define ZONE_PREFIX "DREVMZ_"

void DrawZones()
  {
   if(!InpDrawZones) return;
   if(swingHigh <= 0.0 || swingLow <= 0.0 || swingHigh <= swingLow) return;

   double   range   = swingHigh - swingLow;
   datetime tStart  = MathMin(swingHighTime, swingLowTime);
   datetime tEnd    = TimeCurrent() + PeriodSeconds(PERIOD_H1) * 12; // projection à droite

   // Épaisseur des bandes high/low : 10% du range
   double band = range * 0.10;

   // ── Zone RANGE HIGH (liquidité haute) ──
   DrawRect("rangeHigh", tStart, swingHigh, tEnd, swingHigh - band, InpColorHigh);
   DrawHLine("lineHigh", swingHigh, InpColorHigh, STYLE_SOLID, 2,
             StringFormat("HIGH %.2f", swingHigh));

   // ── Zone RANGE LOW (liquidité basse) ──
   DrawRect("rangeLow", tStart, swingLow + band, tEnd, swingLow, InpColorLow);
   DrawHLine("lineLow", swingLow, InpColorLow, STYLE_SOLID, 2,
             StringFormat("LOW %.2f", swingLow));

   // ── Zone SNIPER (61.8 -> 95 selon la jambe) ──
   double snipTop, snipBot;
   if(trendFibo == 1)   // jambe haussière : retracement mesuré depuis le high
     {
      snipTop = swingHigh - range * (InpFibEntryMin / 100.0);
      snipBot = swingHigh - range * (InpFibEntryMax / 100.0);
     }
   else                 // jambe baissière : retracement mesuré depuis le low
     {
      snipBot = swingLow + range * (InpFibEntryMin / 100.0);
      snipTop = swingLow + range * (InpFibEntryMax / 100.0);
     }
   DrawRect("sniperZone", tStart, MathMax(snipTop, snipBot), tEnd,
            MathMin(snipTop, snipBot), InpColorSniper);

   // ── Lignes Fibonacci clés ──
   double fibLevels[5] = {61.8, 71.0, 81.0, 88.6, 95.0};
   for(int i = 0; i < 5; i++)
     {
      double px = (trendFibo == 1)
                  ? swingHigh - range * (fibLevels[i] / 100.0)
                  : swingLow  + range * (fibLevels[i] / 100.0);
      DrawHLine(StringFormat("fib%d", i), px, InpColorFibLines, STYLE_DOT, 1,
                StringFormat("%.1f%%  %.2f", fibLevels[i], px));
     }

   ChartRedraw();
  }

void DrawRect(const string id, datetime t1, double p1, datetime t2, double p2, color clr)
  {
   string name = ZONE_PREFIX + id;
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectMove(0, name, 0, t1, p1);
   ObjectMove(0, name, 1, t2, p2);
  }

void DrawHLine(const string id, double price, color clr, ENUM_LINE_STYLE style,
               int width, const string label)
  {
   string name = ZONE_PREFIX + id;
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
   ObjectSetInteger(0, name, OBJPROP_STYLE, style);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetString(0, name, OBJPROP_TEXT, label);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
  }

void DeleteZones()
  {
   ObjectsDeleteAll(0, ZONE_PREFIX);
   ChartRedraw();
  }


void UpdateDisplay(const string status, const double fibPct = -1.0,
                   const int score = -1, const string gradeStr = "")
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   if(InpDisplaySober)
     {
      // ── Version sobre : 4 lignes max, l'essentiel ──
      string line1 = "DREVM-M  " + _Symbol;
      string line2 = status;
      string line3 = StringFormat("Marti %d/%d   Trades %d/%d",
                     martiStep, InpMaxSteps, tradesToday, InpMaxTradesPerDay);
      string line4 = StringFormat("Equity %.2f", equity);

      if(fibPct >= 0.0 && score >= 0)
         line2 = StringFormat("Fib %.1f%%   %d/6 %s", fibPct, score, gradeStr);

      Comment(line1, "\n", line2, "\n", line3, "\n", line4);
     }
   else
     {
      // ── Version détaillée ──
      Comment(StringFormat("DREVM-M %s | %s | Fib %.1f%% | Score %d/6 %s | Marti %d/%d | Trades %d/%d | Equity %.2f",
              _Symbol, status, fibPct, score, gradeStr,
              martiStep, InpMaxSteps, tradesToday, InpMaxTradesPerDay, equity));
     }
  }

//+------------------------------------------------------------------+
//| Envoi Telegram via WebRequest                                     |
//| Prérequis MT5 : Outils > Options > Expert Advisors >             |
//| "Autoriser WebRequest pour les URL listées" +                     |
//| ajouter https://api.telegram.org                                  |
//+------------------------------------------------------------------+
void SendTelegram(const string msg)
  {
   if(StringLen(InpTelegramToken) == 0 || StringLen(InpTelegramChatId) == 0)
      return;

   string url = "https://api.telegram.org/bot" + InpTelegramToken + "/sendMessage";

   // Encodage URL minimal du message
   string text = msg;
   StringReplace(text, "%", "%25");
   StringReplace(text, "&", "%26");
   StringReplace(text, "+", "%2B");
   StringReplace(text, "#", "%23");
   StringReplace(text, "\n", "%0A");

   string payload = "chat_id=" + InpTelegramChatId + "&text=" + text;

   char data[];
   char result[];
   string resultHeaders;
   int len = StringToCharArray(payload, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(len > 0) ArrayResize(data, len - 1); // retirer le \0 final

   ResetLastError();
   int status = WebRequest("POST", url,
                           "Content-Type: application/x-www-form-urlencoded\r\n",
                           5000, data, result, resultHeaders);

   if(status == -1)
      PrintFormat("DREVM-M Telegram: WebRequest bloqué (err %d). "
                  "Ajouter https://api.telegram.org dans Outils>Options>Expert Advisors.",
                  GetLastError());
   else if(status != 200)
      PrintFormat("DREVM-M Telegram: HTTP %d — vérifier token/chat_id.", status);
  }
//+------------------------------------------------------------------+
