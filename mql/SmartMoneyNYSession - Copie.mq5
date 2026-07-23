//+------------------------------------------------------------------+
//|                   SmartMoneyNYSession.mq5                        |
//|            saasDrevmBot v1.01 — Expert Advisor MQL5             |
//|                                                                  |
//|  Stratégie : Smart Money Trading System                         |
//|    H4 biais  →  M15 zone liquidité  →  M5 trigger               |
//|    + Wyckoff Spring/UTAD + RSI divergence + Kijun filtre        |
//|    Grade A+/A/B/C · SL ATR · break-even · DD journalier         |
//|    Session New York 09h30–16h00 (heure NY, DST-aware)           |
//|                                                                  |
//|  Magic : 770077  — Symboles : US30 + USDJPY (configurables)     |
//+------------------------------------------------------------------+
#property copyright "saasDrevmBot v1.01"
#property version   "1.01"
#property description "Smart Money Trading System — Session New York"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>



// EA simplifié pour webhook


string webhook_url = "http://127.0.0.1:5678/webhook/mt5-signals";

void OnTick() {
   static datetime last_poll = 0;
   if(TimeCurrent() - last_poll >= 5) {
      PollSignals();
      last_poll = TimeCurrent();
   }
}

void PollSignals() {
   char result[];
   string headers;
   int res = WebRequest("GET", webhook_url, NULL, NULL, 5000, result, headers);
   // Traitement de la réponse JSON et exécution des trades
}





//==========================================================================
//  CONSTANTES
//==========================================================================
#define MAGIC         770077
#define BARS_H4       150
#define BARS_M15      150
#define BARS_M5       150
#define WYCK_LOOKBACK  20
#define DIV_LOOKBACK   10   // barres pour la divergence RSI (iloc[-10])

//==========================================================================
//  INPUTS
//==========================================================================

input group "── Profil ──────────────────────────────────────────────────"
input string InpProfile      = "SCALPING";
// Profils disponibles : SCALPING | BALANCED | CONSERVATIVE | AGGRESSIVE

input group "── Session New York (heure NY) ─────────────────────────────"
input int    InpSessStartH   = 9;    // Heure début
input int    InpSessStartM   = 30;   // Minute début
input int    InpSessEndH     = 16;   // Heure fin
input int    InpSessEndM     = 0;    // Minute fin
input bool   InpCloseAtEnd   = true; // Fermer tout en fin de session

input group "── Symboles ────────────────────────────────────────────────"
input string InpSym1         = "US30";    // Symbole 1
input string InpSym2         = "USDJPY";  // Symbole 2
input int    InpSpread1      = 50;   // Spread max Sym1 (points)
input int    InpSpread2      = 20;   // Spread max Sym2 (points)

input group "── Indicateurs ─────────────────────────────────────────────"
input int    InpEMA21        = 21;   // EMA courte
input int    InpEMA50        = 50;   // EMA longue
input int    InpRSIPeriod    = 14;   // RSI
input int    InpATRPeriod    = 14;   // ATR
input int    InpKijunPeriod  = 26;   // Kijun
input int    InpWyckLookback = 20;   // Wyckoff : lookback (bougies)
input double InpWyckVolMult  = 1.5;  // Wyckoff : seuil volume faible (< InpWyckVolMult * avg)

input group "── Alertes ─────────────────────────────────────────────────"
input bool   InpAlerts       = true;  // Alertes MetaTrader
input bool   InpPush         = false; // Notifications push mobile

//==========================================================================
//  STRUCTURES
//==========================================================================

struct ProfileCfg
{
   double risk_pct;       // % du solde risqué par trade
   double rr_target;      // Risk:Reward cible
   int    max_trades;     // Max trades/jour par symbole
   double max_dd_pct;     // DD journalier max (%)
   double be_at_r;        // Déplacer SL au BE à N*R de profit
   double sl_atr_mult;    // Multiplicateur ATR pour la distance SL
   int    min_grade;      // Grade minimum : 0=C 1=B 2=A 3=A+
};

struct SymbolCfg
{
   string name;
   int    max_spread;
   int    trades_today;
   datetime last_bar_m5;  // anti-doublon : dernier bar M5 scanné
};

struct MarketCtx
{
   string h4_bias;        // "BULLISH" | "BEARISH"
   bool   m15_zone;       // prix sur extrême du range 30-bar M15
   string m5_trigger;     // "BUY" | "SELL" | ""
   string rsi_div;        // "BULLISH" | "BEARISH" | ""
   string wyckoff;        // "SPRING" | "UTAD" | ""
   bool   above_kijun;    // prix > Kijun M5
};

struct SetupResult
{
   bool   valid;
   int    grade;          // 0=C 1=B 2=A 3=A+
   string direction;      // "up" | "down" | ""
   string setup_type;     // "continuation" | "reversal" | "none"
   int    score;          // 6 + nb confluences (0..3)
};

struct DayState
{
   string day;
   double eq_start;
   double bal_start;
   bool   halted;
};

//==========================================================================
//  VARIABLES GLOBALES
//==========================================================================

CTrade       g_trade;
ProfileCfg   g_prof;
SymbolCfg    g_syms[2];
DayState     g_day;
bool         g_sess_was_open = false;

//==========================================================================
//  UTILITAIRES TEMPS (fuseau New York, DST US inclus)
//==========================================================================

// Algorithme de Tomohiko Sakamoto : jour de la semaine (0=Dim, 1=Lun…)
int DayOfWeekFor(int year, int month, int day)
{
   static int t[12] = {0,3,2,5,0,3,5,1,4,6,2,4};
   if(month < 3) year--;
   return (year + year/4 - year/100 + year/400 + t[month-1] + day) % 7;
}

// Offset UTC→NY en heures (-4 EDT, -5 EST)
int NyOffset(int year, int month, int day)
{
   // Printemps : 2e dimanche de mars à 2h00
   // Automne   : 1er dimanche de novembre à 2h00
   int offset = -5;
   if(month > 3 && month < 11) return -4;
   if(month == 3)
   {
      int dow_m1 = DayOfWeekFor(year, 3, 1);
      int first  = 1 + (7 - dow_m1) % 7;   // 1er dimanche de mars
      int second = first + 7;               // 2e dimanche
      if(day >= second) offset = -4;
   }
   else if(month == 11)
   {
      int dow_n1 = DayOfWeekFor(year, 11, 1);
      int first  = 1 + (7 - dow_n1) % 7;   // 1er dimanche de novembre
      if(day < first) offset = -4;
   }
   return offset;
}

// Convertit un timestamp UTC en heure NY
datetime ToNY(datetime utc)
{
   MqlDateTime d; TimeToStruct(utc, d);
   return utc + (datetime)(NyOffset(d.year, d.mon, d.day) * 3600);
}

string GetNYDate()
{
   MqlDateTime d; TimeToStruct(ToNY(TimeGMT()), d);
   return StringFormat("%04d-%02d-%02d", d.year, d.mon, d.day);
}

bool InNYSession()
{
   datetime ny = ToNY(TimeGMT());
   MqlDateTime d; TimeToStruct(ny, d);
   if(d.day_of_week == 0 || d.day_of_week == 6) return false;
   int now   = d.hour * 60 + d.min;
   int start = InpSessStartH * 60 + InpSessStartM;
   int end_  = InpSessEndH   * 60 + InpSessEndM;
   return now >= start && now <= end_;
}

//==========================================================================
//  PROFILS
//==========================================================================

bool LoadProfile(const string name, ProfileCfg &cfg)
{
   cfg.sl_atr_mult = 1.5;
   if(name == "SCALPING")
   {
      cfg.risk_pct=0.5; cfg.rr_target=2.0; cfg.max_trades=3;
      cfg.max_dd_pct=3.0; cfg.be_at_r=1.0; cfg.min_grade=2;
      return true;
   }
   if(name == "BALANCED")
   {
      cfg.risk_pct=1.0; cfg.rr_target=2.5; cfg.max_trades=2;
      cfg.max_dd_pct=4.0; cfg.be_at_r=1.0; cfg.min_grade=2;
      return true;
   }
   if(name == "CONSERVATIVE")
   {
      cfg.risk_pct=0.5; cfg.rr_target=3.0; cfg.max_trades=1;
      cfg.max_dd_pct=2.0; cfg.be_at_r=1.0; cfg.min_grade=3;
      return true;
   }
   if(name == "AGGRESSIVE")
   {
      cfg.risk_pct=1.5; cfg.rr_target=2.0; cfg.max_trades=4;
      cfg.max_dd_pct=5.0; cfg.be_at_r=1.0; cfg.min_grade=1;
      return true;
   }
   return false;
}

string GradeStr(int g)
{
   switch(g){ case 3:return "A+"; case 2:return "A"; case 1:return "B"; default:return "C"; }
}

//==========================================================================
//  CALCULS D'INDICATEURS (tableaux 0=plus ancien, n-1=plus récent)
//==========================================================================

// EMA via la méthode EWM : alpha = 2/(period+1)
double EMAFull(const double &close[], int period, int idx)
{
   if(idx < 0 || idx >= ArraySize(close)) return close[MathMax(0,idx)];
   double k   = 2.0 / (period + 1.0);
   double ema = close[0];
   for(int i = 1; i <= idx; i++)
      ema = close[i] * k + ema * (1.0 - k);
   return ema;
}

// ATR (Wilder True Range) sur les `period` dernières barres
double CalcATR(const double &h[], const double &l[], const double &c[],
               int period, int n)
{
   if(n < period + 1) return 0;
   double sum = 0;
   for(int i = n - period; i < n; i++)
   {
      double tr = MathMax(h[i]-l[i],
                  MathMax(MathAbs(h[i]-c[i-1]),
                          MathAbs(l[i]-c[i-1])));
      sum += tr;
   }
   return sum / period;
}

// RSI de Wilder (lissage 1/period) — remplit rsi[] de la taille n
void CalcRSI(const double &close[], int period, int n, double &rsi[])
{
   ArrayResize(rsi, n);
   ArrayInitialize(rsi, 50.0);
   if(n < period + 1) return;

   double ag = 0, al = 0;
   for(int i = 1; i <= period; i++)
   {
      double d = close[i] - close[i-1];
      if(d > 0) ag += d; else al -= d;
   }
   ag /= period; al /= period;
   rsi[period] = (al < 1e-10) ? 100.0 : 100.0 - 100.0/(1.0 + ag/al);

   for(int i = period + 1; i < n; i++)
   {
      double d    = close[i] - close[i-1];
      double gain = (d > 0) ? d : 0;
      double loss = (d < 0) ? -d : 0;
      ag = (ag * (period-1) + gain) / period;
      al = (al * (period-1) + loss) / period;
      rsi[i] = (al < 1e-10) ? 100.0 : 100.0 - 100.0/(1.0 + ag/al);
   }
}

// Moyenne mobile simple sur volume (les n dernières barres)
double SMA_Vol(const long &vol[], int period, int n)
{
   if(n < period) return 0;
   double sum = 0;
   for(int i = n - period; i < n; i++) sum += (double)vol[i];
   return sum / period;
}

//==========================================================================
//  DÉTECTEURS TECHNIQUES
//==========================================================================

// Biais H4 : close actuel vs close 20 bougies avant
string DetectH4Bias(const double &c[], int n)
{
   if(n < 21) return "BULLISH";
   return (c[n-1] > c[n-21]) ? "BULLISH" : "BEARISH";
}

// Zone M15 touchée : prix près d'un extrême du range 30 bougies
bool DetectM15Zone(const double &h[], const double &l[], const double &c[],
                   int n)
{
   if(n < 30) return false;
   double hi = h[n-30], lo = l[n-30];
   for(int i = n-29; i < n; i++) { if(h[i]>hi) hi=h[i]; if(l[i]<lo) lo=l[i]; }
   double atr = CalcATR(h, l, c, InpATRPeriod, n);
   double px  = c[n-1];
   return (MathAbs(px-hi) <= atr || MathAbs(px-lo) <= atr);
}

// Trigger M5 : bougie haussière/baissière sur la dernière clôture
string DetectM5Trigger(const double &c[], int n)
{
   if(n < 2) return "";
   if(c[n-1] > c[n-2]) return "BUY";
   if(c[n-1] < c[n-2]) return "SELL";
   return "";
}

// Divergence RSI sur DIV_LOOKBACK bougies (comparaison prix vs RSI)
string DetectDivergence(const double &c[], int n)
{
   if(n < DIV_LOOKBACK + InpRSIPeriod + 2) return "";
   double rsi[];
   CalcRSI(c, InpRSIPeriod, n, rsi);
   double p_now  = c[n-1],             p_ago  = c[n-1-DIV_LOOKBACK];
   double r_now  = rsi[n-1],           r_ago  = rsi[n-1-DIV_LOOKBACK];
   if(p_now < p_ago && r_now > r_ago) return "BULLISH";
   if(p_now > p_ago && r_now < r_ago) return "BEARISH";
   return "";
}

// Wyckoff Spring / UTAD
// Spring : mèche sous prior_low + clôture au-dessus + volume faible
// UTAD   : mèche au-dessus prior_high + clôture en dessous + volume faible
string DetectWyckoff(const double &h[], const double &l[], const double &c[],
                     const long &vol[], int n)
{
   int lb = InpWyckLookback;
   if(n < lb + 2) return "";

   double phi = h[n-lb-1], plo = l[n-lb-1];
   for(int i = n-lb; i < n-1; i++) { if(h[i]>phi) phi=h[i]; if(l[i]<plo) plo=l[i]; }

   double lh = h[n-1], ll = l[n-1], lc = c[n-1];
   double avg_vol = SMA_Vol(vol, lb, n-1);  // moyenne sans la bougie courante
   bool   lo_vol  = (avg_vol > 0 && (double)vol[n-1] < avg_vol * InpWyckVolMult);

   if(ll < plo && lc > plo && lc > c[n-2] && lo_vol) return "SPRING";
   if(lh > phi && lc < phi && lc < c[n-2] && lo_vol) return "UTAD";
   return "";
}

// Filtre Ichimoku Kijun : prix > Kijun = true
bool PriceAboveKijun(const double &h[], const double &l[], const double &c[],
                     int n)
{
   int p = InpKijunPeriod;
   if(n < p) return false;
   double kh = h[n-p], kl = l[n-p];
   for(int i = n-p+1; i < n; i++) { if(h[i]>kh) kh=h[i]; if(l[i]<kl) kl=l[i]; }
   return c[n-1] > (kh + kl) / 2.0;
}

//==========================================================================
//  CONSTRUCTION DU CONTEXTE MARCHÉ
//==========================================================================

bool BuildContext(const string &sym, MarketCtx &ctx, double &atr_out)
{
   // ── H4 ────────────────────────────────────────────────────────────────
   MqlRates h4[]; int nh4 = CopyRates(sym, PERIOD_H4, 0, BARS_H4, h4);
   if(nh4 < 25) { PrintFormat("[%s] H4 : données insuffisantes (%d)", sym, nh4); return false; }

   double h4c[]; ArrayResize(h4c, nh4);
   for(int i=0;i<nh4;i++) h4c[i]=h4[i].close;
   ctx.h4_bias = DetectH4Bias(h4c, nh4);

   // ── M15 ───────────────────────────────────────────────────────────────
   MqlRates m15[]; int nm15 = CopyRates(sym, PERIOD_M15, 0, BARS_M15, m15);
   if(nm15 < 35) { PrintFormat("[%s] M15 : données insuffisantes (%d)", sym, nm15); return false; }

   double m15h[], m15l[], m15c[];
   ArrayResize(m15h, nm15); ArrayResize(m15l, nm15); ArrayResize(m15c, nm15);
   for(int i=0;i<nm15;i++) { m15h[i]=m15[i].high; m15l[i]=m15[i].low; m15c[i]=m15[i].close; }
   ctx.m15_zone = DetectM15Zone(m15h, m15l, m15c, nm15);

   // ── M5 ────────────────────────────────────────────────────────────────
   MqlRates m5[]; int nm5 = CopyRates(sym, PERIOD_M5, 0, BARS_M5, m5);
   if(nm5 < InpWyckLookback + 5)
   { PrintFormat("[%s] M5 : données insuffisantes (%d)", sym, nm5); return false; }

   double m5h[], m5l[], m5c[]; long m5v[];
   ArrayResize(m5h, nm5); ArrayResize(m5l, nm5); ArrayResize(m5c, nm5); ArrayResize(m5v, nm5);
   for(int i=0;i<nm5;i++)
   {
      m5h[i]=m5[i].high; m5l[i]=m5[i].low; m5c[i]=m5[i].close;
      m5v[i]=(long)m5[i].tick_volume;
   }

   ctx.m5_trigger  = DetectM5Trigger(m5c, nm5);
   ctx.rsi_div     = DetectDivergence(m5c, nm5);
   ctx.wyckoff     = DetectWyckoff(m5h, m5l, m5c, m5v, nm5);
   ctx.above_kijun = PriceAboveKijun(m5h, m5l, m5c, nm5);

   atr_out = CalcATR(m5h, m5l, m5c, InpATRPeriod, nm5);
   return true;
}

//==========================================================================
//  SIGNAL SMART MONEY + SCORING (section 6 & 11 de la Bible)
//==========================================================================

SetupResult ClassifySetup(const MarketCtx &ctx)
{
   SetupResult res;
   res.valid=false; res.grade=0; res.direction=""; res.setup_type="none"; res.score=0;

   // 1) SMART SIGNAL : divergence RSI + Wyckoff + filtre Kijun
   string dir = "";
   if(ctx.rsi_div=="BULLISH" && ctx.wyckoff=="SPRING" && ctx.above_kijun)  dir = "up";
   if(ctx.rsi_div=="BEARISH" && ctx.wyckoff=="UTAD"   && !ctx.above_kijun) dir = "down";
   if(dir == "") return res;

   // 2) LOGIQUE FINALE : confluence H4 / M15 / M5
   bool bias_ok = (dir=="up"   && ctx.h4_bias=="BULLISH") ||
                  (dir=="down" && ctx.h4_bias=="BEARISH");
   bool zone_ok = ctx.m15_zone;
   bool trig_ok = (dir=="up"   && ctx.m5_trigger=="BUY") ||
                  (dir=="down" && ctx.m5_trigger=="SELL");

   int extras = (bias_ok?1:0) + (zone_ok?1:0) + (trig_ok?1:0);

   // 3) Grade (0=C, 1=B, 2=A, 3=A+)
   int grade;
   if(extras==3) grade=3; else if(extras==2) grade=2;
   else if(extras==1) grade=1; else grade=0;

   res.valid      = true;
   res.grade      = grade;
   res.direction  = dir;
   res.setup_type = bias_ok ? "continuation" : "reversal";
   res.score      = 6 + extras;
   return res;
}

//==========================================================================
//  GESTION DES POSITIONS
//==========================================================================

int CountPositions(const string &sym)
{
   int cnt = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(PositionSelectByTicket(t) &&
         PositionGetString(POSITION_SYMBOL) == sym &&
         PositionGetInteger(POSITION_MAGIC) == MAGIC)
         cnt++;
   }
   return cnt;
}

void CloseAllByMagic(const string &reason)
{
   int closed = 0;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(PositionSelectByTicket(t) && PositionGetInteger(POSITION_MAGIC) == MAGIC)
      {
         g_trade.PositionClose(t, 20);
         closed++;
      }
   }
   if(closed > 0) PrintFormat("Fermeture session (%s) : %d position(s).", reason, closed);
}

void ManageBreakeven()
{
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(!PositionSelectByTicket(t)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MAGIC) continue;

      double open_px = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl      = PositionGetDouble(POSITION_SL);
      double tp      = PositionGetDouble(POSITION_TP);
      long   ptype   = PositionGetInteger(POSITION_TYPE);
      string psym    = PositionGetString(POSITION_SYMBOL);
      int    digits  = (int)SymbolInfoInteger(psym, SYMBOL_DIGITS);
      double r_dist  = MathAbs(open_px - sl);
      if(r_dist <= 0) continue;

      if(ptype == POSITION_TYPE_BUY)
      {
         double px = SymbolInfoDouble(psym, SYMBOL_BID);
         if((px-open_px)/r_dist >= g_prof.be_at_r && sl < open_px)
         {
            g_trade.PositionModify(t, NormalizeDouble(open_px, digits), tp);
            PrintFormat("[%s] ✅ SL → break-even BUY (ticket %d)", psym, (int)t);
         }
      }
      else
      {
         double px = SymbolInfoDouble(psym, SYMBOL_ASK);
         if((open_px-px)/r_dist >= g_prof.be_at_r && sl > open_px)
         {
            g_trade.PositionModify(t, NormalizeDouble(open_px, digits), tp);
            PrintFormat("[%s] ✅ SL → break-even SELL (ticket %d)", psym, (int)t);
         }
      }
   }
}

//==========================================================================
//  DRAWDOWN JOURNALIER
//==========================================================================

bool DailyDDBreached()
{
   if(g_day.eq_start <= 0) return false;
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double pct = (g_day.eq_start - eq) / g_day.eq_start * 100.0;
   return pct >= g_prof.max_dd_pct;
}

//==========================================================================
//  CALCUL DU LOT (risque % du solde)
//==========================================================================

double CalcLot(const string &sym, double sl_dist)
{
   double balance   = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_money= balance * g_prof.risk_pct / 100.0;
   double tick_sz   = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double tick_val  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double vol_min   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double vol_max   = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double vol_step  = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(tick_sz <= 0 || tick_val <= 0 || sl_dist <= 0) return 0;
   double loss_per_lot = (sl_dist / tick_sz) * tick_val;
   if(loss_per_lot <= 0) return 0;
   double lots = risk_money / loss_per_lot;
   lots = MathFloor(lots / vol_step) * vol_step;
   lots = MathMax(vol_min, MathMin(vol_max, lots));
   return NormalizeDouble(lots, 2);
}

//==========================================================================
//  OUVERTURE D'UN TRADE
//==========================================================================

bool OpenTrade(const string &sym, const string &dir, double atr, const SetupResult &setup)
{
   int    digits  = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double sl_dist = atr * g_prof.sl_atr_mult;
   double entry, sl, tp;
   bool   is_buy = (dir == "up");

   if(is_buy)
   {
      entry = SymbolInfoDouble(sym, SYMBOL_ASK);
      sl    = entry - sl_dist;
      tp    = entry + sl_dist * g_prof.rr_target;
   }
   else
   {
      entry = SymbolInfoDouble(sym, SYMBOL_BID);
      sl    = entry + sl_dist;
      tp    = entry - sl_dist * g_prof.rr_target;
   }
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);

   double lots = CalcLot(sym, sl_dist);
   if(lots <= 0)
   { PrintFormat("[%s] Lot calculé = 0 — ordre annulé.", sym); return false; }

   string grade  = GradeStr(setup.grade);
   string comment= StringFormat("NYBot_%s_%s", grade, setup.setup_type);

   PrintFormat("[%s] SIGNAL %s | grade=%s | setup=%s | div=%s | wyck=%s",
               sym, is_buy?"BUY":"SELL", grade, setup.setup_type, "", "");
   PrintFormat("[%s] entry=%.5f SL=%.5f TP=%.5f lots=%.2f R:R=%.1f score=%d",
               sym, entry, sl, tp, lots, g_prof.rr_target, setup.score);

   bool ok = is_buy ? g_trade.Buy (lots, sym, entry, sl, tp, comment)
                    : g_trade.Sell(lots, sym, entry, sl, tp, comment);
   if(ok)
   {
      PrintFormat("[%s] ✅ Ordre exécuté — ticket=%d retcode=%d",
                  sym, (int)g_trade.ResultOrder(), (int)g_trade.ResultRetcode());
      string msg = StringFormat("[%s] %s %s | %.5f SL %.5f TP %.5f | %.2f lots",
                                sym, is_buy?"🟢 BUY":"🔴 SELL", grade, entry, sl, tp, lots);
      if(InpAlerts) Alert(msg);
      if(InpPush)   SendNotification(msg);
   }
   else
      PrintFormat("[%s] ❌ Ordre refusé — retcode=%d | %s",
                  sym, (int)g_trade.ResultRetcode(), g_trade.ResultRetcodeDescription());
   return ok;
}

//==========================================================================
//  SCAN D'UN SYMBOLE
//==========================================================================

void ScanSymbol(SymbolCfg &cfg)
{
   const string sym = cfg.name;

   // Une seule position active par symbole
   if(CountPositions(sym) > 0) return;

   // Max trades journalier
   if(cfg.trades_today >= g_prof.max_trades) return;

   // Spread
   if((int)SymbolInfoInteger(sym, SYMBOL_SPREAD) > cfg.max_spread)
   {
      PrintFormat("[%s] Spread %d > %d — skip", sym,
                  (int)SymbolInfoInteger(sym, SYMBOL_SPREAD), cfg.max_spread);
      return;
   }

   // Anti-doublon : attendre une nouvelle bougie M5
   datetime bar_time = (datetime)SeriesInfoInteger(sym, PERIOD_M5, SERIES_LASTBAR_DATE);
   if(bar_time == cfg.last_bar_m5) return;

   // Construire le contexte
   MarketCtx ctx;
   double atr_val;
   if(!BuildContext(sym, ctx, atr_val)) return;

   // Classer le setup
   SetupResult setup = ClassifySetup(ctx);
   if(!setup.valid) return;
   if(setup.grade < g_prof.min_grade)
   {
      PrintFormat("[%s] Grade %s < %s requis — skip.", sym,
                  GradeStr(setup.grade), GradeStr(g_prof.min_grade));
      return;
   }

   // Ouvrir le trade
   if(OpenTrade(sym, setup.direction, atr_val, setup))
   {
      cfg.trades_today++;
      cfg.last_bar_m5 = bar_time;
   }
}

//==========================================================================
//  INIT / DEINIT
//==========================================================================

int OnInit()
{
   if(!LoadProfile(InpProfile, g_prof))
   {
      Alert("Profil inconnu : '", InpProfile, "' — SCALPING chargé par défaut.");
      LoadProfile("SCALPING", g_prof);
   }

   g_syms[0].name = InpSym1; g_syms[0].max_spread = InpSpread1;
   g_syms[0].trades_today = 0; g_syms[0].last_bar_m5 = 0;

   g_syms[1].name = InpSym2; g_syms[1].max_spread = InpSpread2;
   g_syms[1].trades_today = 0; g_syms[1].last_bar_m5 = 0;

   // Sélectionner les symboles dans MarketWatch
   SymbolSelect(InpSym1, true);
   SymbolSelect(InpSym2, true);

   g_trade.SetExpertMagicNumber(MAGIC);
   g_trade.SetDeviationInPoints(20);
   g_trade.SetTypeFilling(ORDER_FILLING_IOC);
   g_trade.SetAsyncMode(false);

   g_day.day = ""; g_day.eq_start = 0; g_day.halted = false;
   g_sess_was_open = false;

   EventSetTimer(15);   // polling toutes les 15 s (= Python POLL_SECONDS)

   PrintFormat("SmartMoney NY Session EA démarré | profil=%s | R:R=%.1f | risque=%.1f%% | grade_min=%s",
               InpProfile, g_prof.rr_target, g_prof.risk_pct, GradeStr(g_prof.min_grade));
   PrintFormat("Symboles : %s (spread_max=%d) + %s (spread_max=%d)",
               InpSym1, InpSpread1, InpSym2, InpSpread2);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

//==========================================================================
//  ONTIMER — boucle principale (polling 15 s)
//==========================================================================

void OnTimer()
{
   // ── Réinitialisation journalière ────────────────────────────────────
   string today = GetNYDate();
   if(today != g_day.day)
   {
      g_day.day      = today;
      g_day.eq_start = AccountInfoDouble(ACCOUNT_EQUITY);
      g_day.bal_start= AccountInfoDouble(ACCOUNT_BALANCE);
      g_day.halted   = false;
      for(int i=0;i<2;i++) g_syms[i].trades_today = 0;
      PrintFormat("🌅 Nouveau jour NY %s | équité départ=%.2f %s",
                  today, g_day.eq_start, AccountInfoString(ACCOUNT_CURRENCY));
   }

   // ── Session NY ───────────────────────────────────────────────────────
   bool sess = InNYSession();
   if(g_sess_was_open && !sess && InpCloseAtEnd)
      CloseAllByMagic("fin_session_NY");
   g_sess_was_open = sess;
   if(!sess) return;

   // ── Gestion break-even en continu ────────────────────────────────────
   ManageBreakeven();

   // ── Drawdown journalier ───────────────────────────────────────────────
   if(DailyDDBreached())
   {
      if(!g_day.halted)
      {
         double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
         double pct = (g_day.eq_start>0) ? (g_day.eq_start-eq)/g_day.eq_start*100 : 0;
         PrintFormat("🛑 DD journalier %.2f%% ≥ %.2f%% — entrées arrêtées.", pct, g_prof.max_dd_pct);
         if(InpAlerts) Alert(StringFormat("NY BOT — DD journalier %.2f%% atteint. Entrées bloquées.", pct));
         g_day.halted = true;
      }
      return;
   }

   // ── Scan des symboles ─────────────────────────────────────────────────
   for(int i = 0; i < 2; i++)
      ScanSymbol(g_syms[i]);
}

//==========================================================================
//  ONTICK — break-even en temps réel
//==========================================================================

void OnTick()
{
   ManageBreakeven();
}

//+------------------------------------------------------------------+
//  FIN DE FICHIER
//+------------------------------------------------------------------+
