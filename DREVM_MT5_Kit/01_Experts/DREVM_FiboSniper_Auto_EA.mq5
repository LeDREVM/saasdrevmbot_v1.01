//+------------------------------------------------------------------+
//|                                     DREVM_FiboSniper_Auto_EA.mq5 |
//|                          GoldXrodgers / DREVM — Négus Dja        |
//|  Automatisation du protocole DREVM :                             |
//|  Fibo sniper (61.8/71/81/88.6/95) + Biais EMA50/200              |
//|  + Sweep liquidité + BOS M5 + Scoring confluence (grade A+..D)   |
//|  + Guardrails prop firm (buffers internes 3.5% / 7% / 8%)        |
//|  + News blackout (InpNewsTimes) + Gestion position complète      |
//|                                                                  |
//|  Évaluation UNIQUEMENT sur clôture M5 (no-repaint).              |
//|  Défaut : MODE_ALERT_ONLY (confirmation manuelle).               |
//+------------------------------------------------------------------+
#property copyright "DREVM / GoldXrodgers"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
CTrade trade;

//=== ENUMS ==========================================================
enum ENUM_EXEC_MODE
  {
   MODE_ALERT_ONLY = 0,   // Alertes seulement (défaut DREVM)
   MODE_MARKET     = 1    // Exécution automatique
  };

enum ENUM_GRADE
  {
   GRADE_D  = 0,
   GRADE_C  = 1,
   GRADE_B  = 2,
   GRADE_A  = 3,
   GRADE_AP = 4           // A+
  };

//=== INPUTS =========================================================
input group "=== EXECUTION ==="
input ENUM_EXEC_MODE InpExecMode        = MODE_ALERT_ONLY; // Mode d'exécution
input long           InpMagic           = 20260717;        // Magic number
input double         InpRiskPercent     = 0.5;             // Risque % par trade
input double         InpMaxLot          = 0.10;            // Lot maximum (cap sécurité)
input ENUM_GRADE     InpMinGrade        = GRADE_B;         // Grade minimum pour agir

input group "=== BIAIS HTF (EMA) ==="
input ENUM_TIMEFRAMES InpBiasTF         = PERIOD_H1;       // TF du biais EMA
input int            InpEmaFast         = 50;              // EMA rapide
input int            InpEmaSlow         = 200;             // EMA lente

input group "=== FIBONACCI SNIPER ==="
input ENUM_TIMEFRAMES InpSwingTF        = PERIOD_H1;       // TF détection swing
input int            InpSwingLookback   = 120;             // Barres lookback swing
input int            InpSwingStrength   = 3;               // Force fractale (barres de chaque côté)
input double         InpFibEntryMin     = 61.8;            // Zone sniper min (%)
input double         InpFibEntryMax     = 95.0;            // Zone sniper max (%)
input double         InpFibInvalid      = 100.0;           // Invalidation (%)

input group "=== TRIGGER M5 (SWEEP + BOS) ==="
input int            InpSweepLookback   = 20;              // Barres M5 pour high/low de liquidité
input int            InpBosLookback     = 10;              // Barres M5 pour structure BOS
input int            InpTriggerExpiry   = 12;              // Barres M5 validité du sweep

input group "=== GESTION POSITION ==="
input double         InpRRTarget        = 2.0;             // R/R minimal (TP final)
input double         InpPartialAtR      = 1.0;             // Partial close à X R
input double         InpPartialPercent  = 50.0;            // % clôturé au partial
input bool           InpBreakevenAfterPartial = true;      // BE après partial
input double         InpBePlusPoints    = 20;              // BE + x points
input bool           InpUseAtrTrailing  = true;            // Trailing ATR actif
input int            InpAtrPeriod       = 14;              // Période ATR
input double         InpAtrMult         = 2.0;             // Multiplicateur ATR trailing

input group "=== GUARDRAILS PROP FIRM (buffers internes) ==="
input double         InpDailyLockPct    = 3.5;             // Lock drawdown jour % (buffer interne)
input double         InpTotalLockPct    = 7.0;             // Lock drawdown total % (buffer interne)
input double         InpPhaseTargetPct  = 8.0;             // Cible de phase %

input group "=== NEWS BLACKOUT ==="
input string         InpNewsTimes       = "";              // "YYYY.MM.DD HH:MM-HH:MM;..." (heure serveur)
input int            InpNewsBufferMin   = 2;               // Marge additionnelle (minutes)

input group "=== ALERTES ==="
input bool           InpPushNotif       = true;            // Notifications push
input bool           InpPopupAlert      = true;            // Alertes popup

//=== ETAT GLOBAL ====================================================
int      hEmaFast = INVALID_HANDLE;
int      hEmaSlow = INVALID_HANDLE;
int      hAtrM5   = INVALID_HANDLE;

datetime lastM5BarTime   = 0;

// Swing / Fibo
double   swingHigh = 0.0, swingLow = 0.0;
datetime swingHighTime = 0, swingLowTime = 0;
int      trendFibo = 0;          // +1 haussier (fib tracé low->high), -1 baissier

// Trigger state
bool     sweepDetected   = false;
int      sweepDirection  = 0;    // +1 sweep du low (setup BUY), -1 sweep du high (setup SELL)
datetime sweepTime       = 0;

// Position state (persistant via GlobalVariables)
string   gvPrefix = "";

// Guardrails
double   dayStartEquity  = 0.0;
datetime dayStartStamp   = 0;
double   refBalance      = 0.0;  // balance de référence de phase
bool     tradingLocked   = false;
string   lockReason      = "";

//+------------------------------------------------------------------+
//| Helpers GlobalVariables (persistance restart)                     |
//+------------------------------------------------------------------+
string GV(const string key) { return gvPrefix + key; }

double GVGet(const string key, double defVal)
  {
   if(GlobalVariableCheck(GV(key))) return GlobalVariableGet(GV(key));
   return defVal;
  }
void GVSet(const string key, double val) { GlobalVariableSet(GV(key), val); }

//+------------------------------------------------------------------+
//| OnInit                                                            |
//+------------------------------------------------------------------+
int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);

   gvPrefix = "DREVM_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_" +
              IntegerToString(InpMagic) + "_" + _Symbol + "_";

   hEmaFast = iMA(_Symbol, InpBiasTF, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, InpBiasTF, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hAtrM5   = iATR(_Symbol, PERIOD_M5, InpAtrPeriod);

   if(hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE || hAtrM5 == INVALID_HANDLE)
     {
      Print("DREVM: échec création handles indicateurs");
      return INIT_FAILED;
     }

   // Balance de référence de phase (persistante)
   refBalance = GVGet("refBalance", 0.0);
   if(refBalance <= 0.0)
     {
      refBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      GVSet("refBalance", refBalance);
     }

   ResetDailyAnchor();
   PrintFormat("DREVM FiboSniper Auto initialisé | Mode=%s | RefBalance=%.2f",
               InpExecMode == MODE_ALERT_ONLY ? "ALERT_ONLY" : "MARKET", refBalance);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(hEmaFast != INVALID_HANDLE) IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE) IndicatorRelease(hEmaSlow);
   if(hAtrM5   != INVALID_HANDLE) IndicatorRelease(hAtrM5);
  }

//+------------------------------------------------------------------+
//| OnTick — logique sur clôture M5 uniquement (no-repaint)          |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Gestion de position à chaque tick (BE / trailing / partial)
   ManageOpenPositions();

   // Nouvelle bougie M5 clôturée ?
   datetime m5Time = iTime(_Symbol, PERIOD_M5, 0);
   if(m5Time == lastM5BarTime) return;
   lastM5BarTime = m5Time;

   // ---- pipeline sur close M5 ----
   UpdateDailyAnchor();
   UpdateGuardrails();
   if(tradingLocked)
     {
      Comment("DREVM ⛔ LOCK: ", lockReason);
      return;
     }
   if(IsNewsBlackout())
     {
      Comment("DREVM 📰 NEWS BLACKOUT actif — aucun signal");
      return;
     }

   DetectSwings();
   if(swingHigh <= 0.0 || swingLow <= 0.0 || swingHigh <= swingLow) return;

   int emaBias = GetEmaBias();          // +1 bullish, -1 bearish, 0 neutre
   DetectSweep();
   int bosDir  = DetectBos();           // +1 BOS haussier, -1 baissier, 0 aucun

   EvaluateSetup(emaBias, bosDir);
  }

//+------------------------------------------------------------------+
//| Biais EMA (HTF)                                                   |
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
//| Détection swing high/low fractal sur InpSwingTF                  |
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
      // Trend Fibo : si le high est plus récent -> jambe haussière (fib low->high) etc.
      trendFibo = (swingHighTime > swingLowTime) ? 1 : -1;
     }
  }

//+------------------------------------------------------------------+
//| Niveau de retracement courant (%) dans la jambe active           |
//+------------------------------------------------------------------+
double CurrentFibPercent()
  {
   double range = swingHigh - swingLow;
   if(range <= 0.0) return -1.0;
   double px = iClose(_Symbol, PERIOD_M5, 1);

   if(trendFibo == 1)   // jambe haussière : retracement depuis le high vers le bas
      return (swingHigh - px) / range * 100.0;
   else                 // jambe baissière : retracement depuis le low vers le haut
      return (px - swingLow) / range * 100.0;
  }

//+------------------------------------------------------------------+
//| Sweep de liquidité sur M5 (mèche au-delà d'un extrême récent)    |
//+------------------------------------------------------------------+
void DetectSweep()
  {
   // Expiration du sweep précédent
   if(sweepDetected)
     {
      int barsSince = iBarShift(_Symbol, PERIOD_M5, sweepTime);
      if(barsSince > InpTriggerExpiry) { sweepDetected = false; sweepDirection = 0; }
     }

   int start = 2; // on regarde la bougie clôturée (index 1) vs les précédentes
   double refHigh = -DBL_MAX, refLow = DBL_MAX;
   for(int i = start; i < start + InpSweepLookback; i++)
     {
      refHigh = MathMax(refHigh, iHigh(_Symbol, PERIOD_M5, i));
      refLow  = MathMin(refLow,  iLow(_Symbol, PERIOD_M5, i));
     }

   double h1 = iHigh(_Symbol, PERIOD_M5, 1);
   double l1 = iLow(_Symbol, PERIOD_M5, 1);
   double c1 = iClose(_Symbol, PERIOD_M5, 1);

   // Sweep du high : mèche au-dessus du ref high mais close en-dessous -> setup SELL
   if(h1 > refHigh && c1 < refHigh)
     {
      sweepDetected  = true;
      sweepDirection = -1;
      sweepTime      = iTime(_Symbol, PERIOD_M5, 1);
     }
   // Sweep du low : mèche sous le ref low mais close au-dessus -> setup BUY
   else if(l1 < refLow && c1 > refLow)
     {
      sweepDetected  = true;
      sweepDirection = 1;
      sweepTime      = iTime(_Symbol, PERIOD_M5, 1);
     }
  }

//+------------------------------------------------------------------+
//| BOS M5 : close au-delà du dernier extrême de structure           |
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
//| Scoring de confluence + décision                                  |
//+------------------------------------------------------------------+
void EvaluateSetup(const int emaBias, const int bosDir)
  {
   double fibPct = CurrentFibPercent();

   // Direction candidate = continuation de la jambe (trendFibo)
   int dir = trendFibo; // +1 BUY continuation, -1 SELL continuation

   // --- 6 confluences DREVM ---
   bool cBias    = (emaBias == dir);                                        // 1. biais EMA aligné
   bool cFib     = (fibPct >= InpFibEntryMin && fibPct <= InpFibEntryMax);  // 2. zone sniper
   bool cSweep   = (sweepDetected && sweepDirection == dir);                // 3. sweep bon côté
   bool cBos     = (bosDir == dir);                                         // 4. BOS M5 dans le sens
   bool cValid   = (fibPct < InpFibInvalid && fibPct >= 0.0);               // 5. pas invalidé (100%)

   // 6. R/R estimé
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

   string gradeStr = GradeToString(grade);
   Comment(StringFormat("DREVM %s | Fib %.1f%% | Biais EMA %s | Sweep %s | BOS %s | Score %d/6 -> %s",
           _Symbol, fibPct,
           emaBias > 0 ? "BULL" : (emaBias < 0 ? "BEAR" : "—"),
           cSweep ? "OK" : "—", cBos ? "OK" : "—", score, gradeStr));

   // Décision : trigger complet requis (sweep + BOS) + grade suffisant
   if(!cSweep || !cBos) return;
   if(grade < InpMinGrade) return;
   if(HasOpenPosition()) return;

   string msg = StringFormat("DREVM %s SETUP %s [%s %d/6] Fib %.1f%% | E:%.2f SL:%.2f TP:%.2f",
               _Symbol, dir > 0 ? "BUY" : "SELL", gradeStr, score, fibPct, entry, sl, tp);

   if(InpExecMode == MODE_ALERT_ONLY)
     {
      Notify(msg);
      // Consommer le trigger pour éviter le spam
      sweepDetected = false;
      return;
     }

   // MODE_MARKET : exécution
   double lots = CalcLots(risk);
   if(lots <= 0.0) return;

   bool ok = (dir > 0)
             ? trade.Buy(lots, _Symbol, 0.0, sl, tp, "DREVM_" + gradeStr)
             : trade.Sell(lots, _Symbol, 0.0, sl, tp, "DREVM_" + gradeStr);

   if(ok)
     {
      Notify(msg + StringFormat(" | EXEC %.2f lots", lots));
      GVSet("partialDone", 0.0);
      sweepDetected = false;
     }
   else
      PrintFormat("DREVM: échec ordre (%d) %s", trade.ResultRetcode(), trade.ResultComment());
  }

//+------------------------------------------------------------------+
//| Construction des niveaux entrée / SL / TP                        |
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
                    ? swingHigh - range * (InpFibInvalid / 100.0)   // sous le 100% de la jambe haussière
                    : swingLow  + range * (InpFibInvalid / 100.0);  // au-dessus du 100% de la jambe baissière

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
//| Calcul de lot selon risque % (pas de $ dans les identifiants)    |
//+------------------------------------------------------------------+
double CalcLots(const double slDistance)
  {
   if(slDistance <= 0.0) return 0.0;

   double riskAmount = AccountInfoDouble(ACCOUNT_EQUITY) * InpRiskPercent / 100.0;
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickValue <= 0.0 || tickSize <= 0.0) return 0.0;

   double lossPerLot = slDistance / tickSize * tickValue;
   if(lossPerLot <= 0.0) return 0.0;

   double lots = riskAmount / lossPerLot;

   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lots = MathFloor(lots / lotStep) * lotStep;
   lots = MathMax(minLot, MathMin(lots, MathMin(maxLot, InpMaxLot)));
   return lots;
  }

//+------------------------------------------------------------------+
//| Gestion des positions ouvertes (partial / BE / trailing ATR)     |
//+------------------------------------------------------------------+
void ManageOpenPositions()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;

      long   type   = PositionGetInteger(POSITION_TYPE);
      double open   = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl     = PositionGetDouble(POSITION_SL);
      double vol    = PositionGetDouble(POSITION_VOLUME);
      double px     = (type == POSITION_TYPE_BUY)
                      ? SymbolInfoDouble(_Symbol, SYMBOL_BID)
                      : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

      double risk = MathAbs(open - sl);
      if(risk <= 0.0) continue;

      double progressR = (type == POSITION_TYPE_BUY)
                         ? (px - open) / risk
                         : (open - px) / risk;

      // --- Partial close à 1R ---
      bool partialDone = (GVGet("partialDone", 0.0) > 0.5);
      if(!partialDone && progressR >= InpPartialAtR)
        {
         double closeVol = NormalizeVolume(vol * InpPartialPercent / 100.0);
         if(closeVol > 0.0 && closeVol < vol)
           {
            if(trade.PositionClosePartial(ticket, closeVol))
              {
               GVSet("partialDone", 1.0);
               Notify(StringFormat("DREVM %s: partial %.0f%% à %.1fR", _Symbol, InpPartialPercent, InpPartialAtR));
              }
           }
         // --- Breakeven après partial ---
         if(InpBreakevenAfterPartial)
           {
            double bePad = InpBePlusPoints * _Point;
            double newSl = (type == POSITION_TYPE_BUY) ? open + bePad : open - bePad;
            bool improve = (type == POSITION_TYPE_BUY) ? (newSl > sl) : (newSl < sl);
            if(improve) trade.PositionModify(ticket, NormalizePrice(newSl), PositionGetDouble(POSITION_TP));
           }
        }

      // --- Trailing ATR (seulement après partial/BE) ---
      if(InpUseAtrTrailing && GVGet("partialDone", 0.0) > 0.5)
        {
         double atr[1];
         if(CopyBuffer(hAtrM5, 0, 1, 1, atr) == 1 && atr[0] > 0.0)
           {
            double trailSl = (type == POSITION_TYPE_BUY) ? px - atr[0] * InpAtrMult
                                                         : px + atr[0] * InpAtrMult;
            double curSl = PositionGetDouble(POSITION_SL);
            bool improve = (type == POSITION_TYPE_BUY) ? (trailSl > curSl) : (trailSl < curSl);
            if(improve) trade.PositionModify(ticket, NormalizePrice(trailSl), PositionGetDouble(POSITION_TP));
           }
        }
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

double NormalizeVolume(double v)
  {
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   v = MathFloor(v / lotStep) * lotStep;
   if(v < minLot) return 0.0;
   return v;
  }

double NormalizePrice(double p)
  {
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   return NormalizeDouble(p, digits);
  }

//+------------------------------------------------------------------+
//| Guardrails prop firm (buffers internes DREVM)                    |
//+------------------------------------------------------------------+
void ResetDailyAnchor()
  {
   dayStartEquity = AccountInfoDouble(ACCOUNT_EQUITY);
   MqlDateTime dt; TimeToStruct(TimeCurrent(), dt);
   dt.hour = 0; dt.min = 0; dt.sec = 0;
   dayStartStamp = StructToTime(dt);
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
      ResetDailyAnchor();          // nouveau jour serveur
   else
      dayStartEquity = GVGet("dayStartEquity", AccountInfoDouble(ACCOUNT_EQUITY));
  }

void UpdateGuardrails()
  {
   tradingLocked = false;
   lockReason = "";

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);

   // Lock jour (buffer 3.5%)
   double dayDDPct = (dayStartEquity - equity) / dayStartEquity * 100.0;
   if(dayDDPct >= InpDailyLockPct)
     {
      tradingLocked = true;
      lockReason = StringFormat("DD jour %.2f%% >= %.1f%%", dayDDPct, InpDailyLockPct);
     }

   // Lock total (buffer 7%)
   double totDDPct = (refBalance - equity) / refBalance * 100.0;
   if(totDDPct >= InpTotalLockPct)
     {
      tradingLocked = true;
      lockReason = StringFormat("DD total %.2f%% >= %.1f%%", totDDPct, InpTotalLockPct);
     }

   // Cible de phase atteinte (8%) : lock protecteur
   double gainPct = (equity - refBalance) / refBalance * 100.0;
   if(gainPct >= InpPhaseTargetPct)
     {
      tradingLocked = true;
      lockReason = StringFormat("🎯 Cible phase atteinte +%.2f%% — protéger les gains", gainPct);
     }

   if(tradingLocked)
      Notify("DREVM ⛔ " + _Symbol + " LOCK: " + lockReason);
  }

//+------------------------------------------------------------------+
//| News blackout — InpNewsTimes "YYYY.MM.DD HH:MM-HH:MM;..."        |
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

      // Format: "YYYY.MM.DD HH:MM-HH:MM"
      int dashPos = StringFind(w, "-", 11);
      if(dashPos < 0) continue;

      string startStr = StringSubstr(w, 0, dashPos);            // "YYYY.MM.DD HH:MM"
      string dateStr  = StringSubstr(w, 0, 10);                 // "YYYY.MM.DD"
      string endStr   = dateStr + " " + StringSubstr(w, dashPos + 1); // même jour

      datetime tStart = StringToTime(startStr) - InpNewsBufferMin * 60;
      datetime tEnd   = StringToTime(endStr)   + InpNewsBufferMin * 60;

      if(now >= tStart && now <= tEnd) return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
//| Utilitaires                                                       |
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
  }
//+------------------------------------------------------------------+
