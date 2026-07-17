//+------------------------------------------------------------------+
//|                                   DREVM_FiboSniper_Indicator.mq5 |
//|                          GoldXrodgers / DREVM — Négus Dja        |
//|                                                                  |
//|  INDICATEUR (aucune exécution) — même moteur que l'EA :          |
//|  • Swing high/low fractal (H1 par défaut)                        |
//|  • Zones range HIGH / LOW + zone SNIPER 61.8→95%                 |
//|  • Lignes Fibonacci 61.8 / 71 / 81 / 88.6 / 95                   |
//|  • Biais EMA50/200 (H1)                                          |
//|  • Détection sweep liquidité + BOS sur close M5 (no-repaint)     |
//|  • Score de confluence /6 + grade A+/A/B/C/D                     |
//|  • Panneau sobre + alertes popup / push / Telegram               |
//|                                                                  |
//|  À poser sur n'importe quel TF — la logique interne reste        |
//|  multi-timeframe (swing H1, trigger M5), comme l'EA.             |
//+------------------------------------------------------------------+
#property copyright "DREVM / GoldXrodgers"
#property version   "1.00"
#property strict
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

//=== ENUMS ==========================================================
enum ENUM_GRADE
  {
   GRADE_D  = 0,
   GRADE_C  = 1,
   GRADE_B  = 2,
   GRADE_A  = 3,
   GRADE_AP = 4
  };

//=== INPUTS =========================================================
input group "=== BIAIS HTF (EMA) ==="
input ENUM_TIMEFRAMES InpBiasTF         = PERIOD_H1;       // TF du biais EMA
input int            InpEmaFast         = 50;              // EMA rapide
input int            InpEmaSlow         = 200;             // EMA lente

input group "=== FIBONACCI SNIPER ==="
input ENUM_TIMEFRAMES InpSwingTF        = PERIOD_H1;       // TF détection swing
input int            InpSwingLookback   = 120;             // Barres lookback
input int            InpSwingStrength   = 3;               // Force fractale
input double         InpFibEntryMin     = 61.8;            // Zone sniper min (%)
input double         InpFibEntryMax     = 95.0;            // Zone sniper max (%)
input double         InpFibInvalid      = 100.0;           // Invalidation (%)

input group "=== TRIGGER M5 (SWEEP + BOS) ==="
input int            InpSweepLookback   = 20;              // Barres M5 liquidité
input int            InpBosLookback     = 10;              // Barres M5 structure
input int            InpTriggerExpiry   = 12;              // Validité sweep (bougies M5)

input group "=== SIGNAL ==="
input ENUM_GRADE     InpMinGrade        = GRADE_B;         // Grade minimum pour alerter
input double         InpRRTarget        = 1.5;             // R/R pour le calcul E/SL/TP

input group "=== AFFICHAGE ==="
input bool           InpDisplaySober    = true;            // Panneau sobre
input bool           InpDrawZones       = true;            // Dessiner zones + Fibo
input bool           InpDrawSignalArrow = true;            // Flèche sur signal validé
input color          InpColorHigh       = C'239,68,68';    // Zone high (#ef4444)
input color          InpColorLow        = C'16,185,129';   // Zone low (#10b981)
input color          InpColorSniper     = C'234,179,8';    // Zone sniper (#eab308)
input color          InpColorFibLines   = clrDimGray;      // Lignes Fibo
input color          InpColorBuyArrow   = C'34,197,94';    // Flèche BUY (#22c55e)
input color          InpColorSellArrow  = C'239,68,68';    // Flèche SELL (#ef4444)

input group "=== ALERTES ==="
input bool           InpPopupAlert      = true;            // Popup + son
input bool           InpPushNotif       = true;            // Push mobile MT5

input group "=== TELEGRAM ==="
input bool           InpTelegramEnable  = false;           // Alertes Telegram
input string         InpTelegramToken   = "";              // Bot token
input string         InpTelegramChatId  = "";              // Chat ID

//=== ETAT GLOBAL ====================================================
int      hEmaFast = INVALID_HANDLE;
int      hEmaSlow = INVALID_HANDLE;

datetime lastM5BarTime = 0;

double   swingHigh = 0.0, swingLow = 0.0;
datetime swingHighTime = 0, swingLowTime = 0;
int      trendFibo = 0;

bool     sweepDetected  = false;
int      sweepDirection = 0;
datetime sweepTime      = 0;

datetime lastSignalBar  = 0;   // anti-spam : 1 alerte max par bougie M5

#define ZONE_PREFIX "DREVMI_"

//+------------------------------------------------------------------+
int OnInit()
  {
   hEmaFast = iMA(_Symbol, InpBiasTF, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, InpBiasTF, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   if(hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE)
      return INIT_FAILED;

   Print("DREVM FiboSniper Indicator initialisé sur ", _Symbol);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(hEmaFast != INVALID_HANDLE) IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE) IndicatorRelease(hEmaSlow);
   ObjectsDeleteAll(0, ZONE_PREFIX);
   Comment("");
   ChartRedraw();
  }

//+------------------------------------------------------------------+
//| OnCalculate — pipeline sur close M5 (no-repaint)                 |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   datetime m5Time = iTime(_Symbol, PERIOD_M5, 0);
   if(m5Time == lastM5BarTime) return rates_total;
   lastM5BarTime = m5Time;

   DetectSwings();
   if(swingHigh <= 0.0 || swingLow <= 0.0 || swingHigh <= swingLow)
      return rates_total;

   DrawZones();

   int emaBias = GetEmaBias();
   DetectSweep();
   int bosDir  = DetectBos();

   EvaluateSetup(emaBias, bosDir);
   return rates_total;
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

   // Niveaux théoriques E/SL/TP (info seulement — pas d'exécution)
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
   UpdateDisplay(emaBias, fibPct, score, gradeStr);

   // Signal complet : sweep + BOS + grade suffisant
   if(!cSweep || !cBos) return;
   if(grade < InpMinGrade) return;

   // Anti-spam : une alerte max par bougie M5
   datetime sigBar = iTime(_Symbol, PERIOD_M5, 1);
   if(sigBar == lastSignalBar) return;
   lastSignalBar = sigBar;

   string msg = StringFormat("DREVM-I %s SIGNAL %s [%s %d/6] Fib %.1f%% | E:%s SL:%s TP:%s",
               _Symbol, dir > 0 ? "BUY" : "SELL", gradeStr, score, fibPct,
               DoubleToString(entry, _Digits), DoubleToString(sl, _Digits),
               DoubleToString(tp, _Digits));

   Notify(msg);

   if(InpDrawSignalArrow)
      DrawSignalArrow(dir, sigBar, grade);

   sweepDetected = false; // consommer le trigger
  }

//+------------------------------------------------------------------+
void BuildTradeLevels(const int dir, double &entry, double &sl, double &tp)
  {
   entry = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK)
                     : SymbolInfoDouble(_Symbol, SYMBOL_BID);

   double range   = swingHigh - swingLow;
   double invalid = (dir > 0)
                    ? swingHigh - range * (InpFibInvalid / 100.0)
                    : swingLow  + range * (InpFibInvalid / 100.0);

   double pad = 10 * _Point;
   sl = (dir > 0) ? invalid - pad : invalid + pad;

   double risk = MathAbs(entry - sl);
   tp = (dir > 0) ? entry + risk * InpRRTarget : entry - risk * InpRRTarget;

   entry = NormalizeDouble(entry, _Digits);
   sl    = NormalizeDouble(sl, _Digits);
   tp    = NormalizeDouble(tp, _Digits);
  }

//+------------------------------------------------------------------+
//| Dessin des zones + Fibonacci                                      |
//+------------------------------------------------------------------+
void DrawZones()
  {
   if(!InpDrawZones) return;

   double   range  = swingHigh - swingLow;
   datetime tStart = MathMin(swingHighTime, swingLowTime);
   datetime tEnd   = TimeCurrent() + PeriodSeconds(PERIOD_H1) * 12;
   double   band   = range * 0.10;

   DrawRect("rangeHigh", tStart, swingHigh, tEnd, swingHigh - band, InpColorHigh);
   DrawHLine("lineHigh", swingHigh, InpColorHigh, STYLE_SOLID, 2,
             StringFormat("HIGH %s", DoubleToString(swingHigh, _Digits)));

   DrawRect("rangeLow", tStart, swingLow + band, tEnd, swingLow, InpColorLow);
   DrawHLine("lineLow", swingLow, InpColorLow, STYLE_SOLID, 2,
             StringFormat("LOW %s", DoubleToString(swingLow, _Digits)));

   double snipTop, snipBot;
   if(trendFibo == 1)
     {
      snipTop = swingHigh - range * (InpFibEntryMin / 100.0);
      snipBot = swingHigh - range * (InpFibEntryMax / 100.0);
     }
   else
     {
      snipBot = swingLow + range * (InpFibEntryMin / 100.0);
      snipTop = swingLow + range * (InpFibEntryMax / 100.0);
     }
   DrawRect("sniperZone", tStart, MathMax(snipTop, snipBot), tEnd,
            MathMin(snipTop, snipBot), InpColorSniper);

   double fibLevels[5] = {61.8, 71.0, 81.0, 88.6, 95.0};
   for(int i = 0; i < 5; i++)
     {
      double px = (trendFibo == 1)
                  ? swingHigh - range * (fibLevels[i] / 100.0)
                  : swingLow  + range * (fibLevels[i] / 100.0);
      DrawHLine(StringFormat("fib%d", i), px, InpColorFibLines, STYLE_DOT, 1,
                StringFormat("%.1f%%  %s", fibLevels[i], DoubleToString(px, _Digits)));
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

//+------------------------------------------------------------------+
//| Flèche de signal (historique conservé sur le chart)              |
//+------------------------------------------------------------------+
void DrawSignalArrow(const int dir, const datetime barTime, const ENUM_GRADE grade)
  {
   string name = ZONE_PREFIX + "sig_" + IntegerToString((long)barTime);
   if(ObjectFind(0, name) >= 0) return;

   double px = (dir > 0) ? iLow(_Symbol, PERIOD_M5, 1) : iHigh(_Symbol, PERIOD_M5, 1);
   double offset = 10 * _Point;

   ObjectCreate(0, name, OBJ_ARROW, 0, barTime, (dir > 0) ? px - offset : px + offset);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, (dir > 0) ? 233 : 234); // ▲ / ▼
   ObjectSetInteger(0, name, OBJPROP_COLOR, (dir > 0) ? InpColorBuyArrow : InpColorSellArrow);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
   ObjectSetString(0, name, OBJPROP_TOOLTIP,
                   StringFormat("DREVM %s %s", dir > 0 ? "BUY" : "SELL", GradeToString(grade)));
  }

//+------------------------------------------------------------------+
//| Panneau — sobre ou détaillé                                       |
//+------------------------------------------------------------------+
void UpdateDisplay(const int emaBias, const double fibPct,
                   const int score, const string gradeStr)
  {
   string biasStr = emaBias > 0 ? "BULL" : (emaBias < 0 ? "BEAR" : "—");

   if(InpDisplaySober)
     {
      Comment("DREVM-I  ", _Symbol, "\n",
              StringFormat("Fib %.1f%%   %d/6 %s", fibPct, score, gradeStr), "\n",
              "Biais EMA ", biasStr, "   Trend ", trendFibo > 0 ? "▲" : "▼");
     }
   else
     {
      Comment(StringFormat("DREVM-I %s | Fib %.1f%% | Score %d/6 %s | EMA %s | Trend %s | Sweep %s",
              _Symbol, fibPct, score, gradeStr, biasStr,
              trendFibo > 0 ? "UP" : "DOWN", sweepDetected ? "actif" : "—"));
     }
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
//| Telegram via WebRequest (autoriser https://api.telegram.org)     |
//+------------------------------------------------------------------+
void SendTelegram(const string msg)
  {
   if(StringLen(InpTelegramToken) == 0 || StringLen(InpTelegramChatId) == 0)
      return;

   string url = "https://api.telegram.org/bot" + InpTelegramToken + "/sendMessage";

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
   if(len > 0) ArrayResize(data, len - 1);

   ResetLastError();
   int status = WebRequest("POST", url,
                           "Content-Type: application/x-www-form-urlencoded\r\n",
                           5000, data, result, resultHeaders);

   if(status == -1)
      PrintFormat("DREVM-I Telegram: WebRequest bloqué (err %d).", GetLastError());
   else if(status != 200)
      PrintFormat("DREVM-I Telegram: HTTP %d — vérifier token/chat_id.", status);
  }
//+------------------------------------------------------------------+
