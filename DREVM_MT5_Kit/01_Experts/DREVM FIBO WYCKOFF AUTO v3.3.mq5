//+------------------------------------------------------------------+
//|             DREVM FIBO WYCKOFF AUTO v3.3 CORE                   |
//|                                                                  |
//| H4  = Biais institutionnel                         40 pts        |
//| M15 = Zone Fibonacci 61.8-71 / 88.6-95             30 pts        |
//| M5  = Spring / UTAD + BOS + rejection              30 pts        |
//|                                                                  |
//| EXECUTION >= 75/100                                               |
//| SL = 120 points                                                   |
//| TP = 200 points                                                   |
//+------------------------------------------------------------------+

#include <Trade/Trade.mqh>
CTrade trade;

//=============================================================
// AUTO TRADING
//=============================================================

input group "=== DREVM v3.3 AUTO EXECUTION ==="

input bool   AutoTradingEnabled   = true;
input long   MagicNumber          = 330026;

input int    StopLossPoints       = 120;
input int    TakeProfitPoints     = 200;

input double RiskPercent          = 0.50;
input double FixedLot             = 0.01;
input bool   UseRiskPercent       = true;

input int    MinimumSetupScore    = 75;
input int    MaxTradesPerDay      = 3;
input int    CooldownM5Bars       = 3;

input double MaxSpreadPoints      = 30;
input double MaxDailyLossPercent  = 2.0;

//=============================================================
// TIMEFRAMES
//=============================================================

input group "=== MULTI TIMEFRAME ==="

input ENUM_TIMEFRAMES BiasTF      = PERIOD_H4;
input ENUM_TIMEFRAMES ZoneTF      = PERIOD_M15;
input ENUM_TIMEFRAMES TriggerTF   = PERIOD_M5;

//=============================================================
// H4
//=============================================================

input group "=== H4 BIAS ==="

input int H4SwingBars             = 40;
input int H4EMAFast               = 50;
input int H4EMASlow               = 200;

//=============================================================
// M15 FIBONACCI
//=============================================================

input group "=== M15 FIBONACCI ==="

input int M15SwingBars            = 40;

input bool UsePremiumZone         = true;
input bool UseDeepZone            = true;

//=============================================================
// M5 WYCKOFF
//=============================================================

input group "=== M5 WYCKOFF ==="

input int LiquidityLookback       = 10;
input int BOSLookback             = 3;

input double MinRejectionRatio    = 0.50;

input bool RequireLiquiditySweep  = true;
input bool RequireBOS             = true;

//=============================================================
// NEWS
//=============================================================

input group "=== NEWS ==="

input bool BlockTradingOnNews = true;

input string InpNewsTimes =
"2026.08.13 15:00-16:00";

//=============================================================
// STATE
//=============================================================

int h4EMA50  = INVALID_HANDLE;
int h4EMA200 = INVALID_HANDLE;

datetime lastM5Bar       = 0;
datetime lastTradeM5Bar  = 0;

datetime newsStart[];
datetime newsEnd[];

int newsCount = 0;


//+------------------------------------------------------------------+
//| STRUCTURES                                                       |
//+------------------------------------------------------------------+

struct SwingData
{
   bool valid;

   bool bullish;

   double high;
   double low;

   datetime highTime;
   datetime lowTime;
};


struct SetupResult
{
   bool buy;
   bool sell;

   int score;

   bool h4Bull;
   bool h4Bear;

   bool m15Premium;
   bool m15Deep;

   bool spring;
   bool utad;

   bool bullBOS;
   bool bearBOS;

   double fib618;
   double fib71;
   double fib886;
   double fib95;

   string reason;
};


//+------------------------------------------------------------------+
//| NORMALIZE PRICE                                                  |
//+------------------------------------------------------------------+

double NP(double price)
{
   return NormalizeDouble(price,_Digits);
}


//+------------------------------------------------------------------+
//| PRICE INSIDE ZONE                                                |
//+------------------------------------------------------------------+

bool InZone(double price,double p1,double p2)
{
   double hi = MathMax(p1,p2);
   double lo = MathMin(p1,p2);

   return(
      price >= lo &&
      price <= hi
   );
}


//+------------------------------------------------------------------+
//| GET SWING                                                        |
//| Uses CLOSED candles only                                         |
//+------------------------------------------------------------------+

SwingData GetSwing(
   ENUM_TIMEFRAMES tf,
   int bars
)
{
   SwingData s;

   s.valid   = false;
   s.bullish = false;

   s.high = 0;
   s.low  = 0;

   s.highTime = 0;
   s.lowTime  = 0;

   MqlRates r[];

   ArraySetAsSeries(r,true);

   // shift 1 = no active candle
   int copied =
      CopyRates(
         _Symbol,
         tf,
         1,
         bars,
         r
      );

   if(copied < bars)
      return s;

   double highest = r[0].high;
   double lowest  = r[0].low;

   int hiIndex = 0;
   int loIndex = 0;

   for(int i=1;i<bars;i++)
   {
      if(r[i].high > highest)
      {
         highest = r[i].high;
         hiIndex = i;
      }

      if(r[i].low < lowest)
      {
         lowest = r[i].low;
         loIndex = i;
      }
   }

   s.high = highest;
   s.low  = lowest;

   s.highTime = r[hiIndex].time;
   s.lowTime  = r[loIndex].time;

   // Because ArraySetAsSeries:
   // smaller index = more recent.
   //
   // Low older than high =
   // low index greater than high index =
   // bullish impulse.

   s.bullish =
      loIndex > hiIndex;

   s.valid =
      (highest > lowest);

   return s;
}


//+------------------------------------------------------------------+
//| FIBONACCI PRICE                                                  |
//+------------------------------------------------------------------+

double FibPrice(
   SwingData &s,
   double level
)
{
   double range =
      s.high-s.low;

   if(s.bullish)
   {
      // Retracement from High downward
      return
         s.high -
         range*level;
   }

   // Retracement from Low upward
   return
      s.low +
      range*level;
}


//+------------------------------------------------------------------+
//| EMA H4                                                           |
//+------------------------------------------------------------------+

bool ReadH4EMA(
   double &fast,
   double &slow
)
{
   double a[];
   double b[];

   ArraySetAsSeries(a,true);
   ArraySetAsSeries(b,true);

   // closed candle = shift 1

   if(CopyBuffer(
      h4EMA50,
      0,
      1,
      1,
      a) != 1)
      return false;

   if(CopyBuffer(
      h4EMA200,
      0,
      1,
      1,
      b) != 1)
      return false;

   fast = a[0];
   slow = b[0];

   return true;
}


//+------------------------------------------------------------------+
//| H4 BIAS                                                          |
//+------------------------------------------------------------------+

int GetH4Bias(
   bool &bull,
   bool &bear
)
{
   bull = false;
   bear = false;

   SwingData h4 =
      GetSwing(
         BiasTF,
         H4SwingBars
      );

   if(!h4.valid)
      return 0;

   double ema50;
   double ema200;

   if(!ReadH4EMA(
      ema50,
      ema200))
      return 0;

   MqlRates bar[];

   ArraySetAsSeries(bar,true);

   if(CopyRates(
      _Symbol,
      BiasTF,
      1,
      1,
      bar) != 1)
      return 0;

   double close =
      bar[0].close;

   //---------------------------
   // BULL
   //---------------------------

   if(
      h4.bullish &&
      ema50 > ema200 &&
      close > ema50
   )
   {
      bull = true;

      return 40;
   }

   //---------------------------
   // BEAR
   //---------------------------

   if(
      !h4.bullish &&
      ema50 < ema200 &&
      close < ema50
   )
   {
      bear = true;

      return 40;
   }

   return 0;
}


//+------------------------------------------------------------------+
//| M15 FIBO                                                        |
//+------------------------------------------------------------------+

int GetM15Zone(
   bool h4Bull,
   bool h4Bear,
   bool &premium,
   bool &deep,
   double &fib618,
   double &fib71,
   double &fib886,
   double &fib95
)
{
   premium = false;
   deep    = false;

   SwingData s =
      GetSwing(
         ZoneTF,
         M15SwingBars
      );

   if(!s.valid)
      return 0;

   // Direction M15 must agree with H4

   if(h4Bull && !s.bullish)
      return 0;

   if(h4Bear && s.bullish)
      return 0;

   fib618 =
      FibPrice(
         s,
         0.618
      );

   fib71 =
      FibPrice(
         s,
         0.71
      );

   fib886 =
      FibPrice(
         s,
         0.886
      );

   fib95 =
      FibPrice(
         s,
         0.95
      );

   MqlRates bar[];

   ArraySetAsSeries(bar,true);

   if(CopyRates(
      _Symbol,
      ZoneTF,
      1,
      1,
      bar) != 1)
      return 0;

   /*
      Important:

      We evaluate full M15 candle excursion,
      not only closing price.

      That allows a candle to sweep the Fib
      and close back outside the zone.
   */

   double candleHigh =
      bar[0].high;

   double candleLow =
      bar[0].low;

   //--------------------------------
   // PREMIUM 61.8 → 71
   //--------------------------------

   double premiumHigh =
      MathMax(
         fib618,
         fib71
      );

   double premiumLow =
      MathMin(
         fib618,
         fib71
      );

   premium =
      (
         candleHigh >= premiumLow &&
         candleLow  <= premiumHigh
      );

   //--------------------------------
   // DEEP 88.6 → 95
   //--------------------------------

   double deepHigh =
      MathMax(
         fib886,
         fib95
      );

   double deepLow =
      MathMin(
         fib886,
         fib95
      );

   deep =
      (
         candleHigh >= deepLow &&
         candleLow  <= deepHigh
      );

   if(
      (UsePremiumZone && premium)
      ||
      (UseDeepZone && deep)
   )
      return 30;

   return 0;
}


//+------------------------------------------------------------------+
//| LOWEST PREVIOUS LOW                                              |
//+------------------------------------------------------------------+

double PreviousLowestLow(
   MqlRates &r[],
   int start,
   int count
)
{
   double lowest =
      r[start].low;

   int end =
      MathMin(
         ArraySize(r),
         start+count
      );

   for(int i=start+1;
       i<end;
       i++)
   {
      if(r[i].low < lowest)
         lowest = r[i].low;
   }

   return lowest;
}


//+------------------------------------------------------------------+
//| HIGHEST PREVIOUS HIGH                                            |
//+------------------------------------------------------------------+

double PreviousHighestHigh(
   MqlRates &r[],
   int start,
   int count
)
{
   double highest =
      r[start].high;

   int end =
      MathMin(
         ArraySize(r),
         start+count
      );

   for(int i=start+1;
       i<end;
       i++)
   {
      if(r[i].high > highest)
         highest = r[i].high;
   }

   return highest;
}


//+------------------------------------------------------------------+
//| BULLISH REJECTION                                                |
//+------------------------------------------------------------------+

bool BullishRejection(
   MqlRates &bar
)
{
   if(bar.close <= bar.open)
      return false;

   double body =
      MathAbs(
         bar.close -
         bar.open
      );

   if(body < _Point)
      body = _Point;

   double wick =
      MathMin(
         bar.open,
         bar.close
      )
      -
      bar.low;

   return(
      wick >=
      body*MinRejectionRatio
   );
}


//+------------------------------------------------------------------+
//| BEARISH REJECTION                                                |
//+------------------------------------------------------------------+

bool BearishRejection(
   MqlRates &bar
)
{
   if(bar.close >= bar.open)
      return false;

   double body =
      MathAbs(
         bar.close -
         bar.open
      );

   if(body < _Point)
      body = _Point;

   double wick =
      bar.high
      -
      MathMax(
         bar.open,
         bar.close
      );

   return(
      wick >=
      body*MinRejectionRatio
   );
}


//+------------------------------------------------------------------+
//| M5 WYCKOFF TRIGGER                                               |
//+------------------------------------------------------------------+

int GetM5Trigger(
   bool h4Bull,
   bool h4Bear,
   bool &spring,
   bool &utad,
   bool &bullBOS,
   bool &bearBOS
)
{
   spring  = false;
   utad    = false;

   bullBOS = false;
   bearBOS = false;

   int requiredBars =
      MathMax(
         LiquidityLookback,
         BOSLookback
      ) + 5;

   MqlRates r[];

   ArraySetAsSeries(r,true);

   if(CopyRates(
      _Symbol,
      TriggerTF,
      1,
      requiredBars,
      r) < requiredBars)
      return 0;

   /*
      r[0] = last CLOSED M5 candle
      r[1+] = historical closed candles
   */

   MqlRates signal =
      r[0];

   //----------------------------------------------------
   // PREVIOUS LIQUIDITY
   //----------------------------------------------------

   double previousLow =
      PreviousLowestLow(
         r,
         1,
         LiquidityLookback
      );

   double previousHigh =
      PreviousHighestHigh(
         r,
         1,
         LiquidityLookback
      );

   //----------------------------------------------------
   // SPRING
   //
   // wick below previous liquidity
   // close back above liquidity
   //----------------------------------------------------

   spring =
      (
         signal.low <
         previousLow
         &&
         signal.close >
         previousLow
         &&
         BullishRejection(
            signal
         )
      );

   //----------------------------------------------------
   // UTAD
   //----------------------------------------------------

   utad =
      (
         signal.high >
         previousHigh
         &&
         signal.close <
         previousHigh
         &&
         BearishRejection(
            signal
         )
      );

   //----------------------------------------------------
   // BOS REFERENCES
   //----------------------------------------------------

   double bosHigh =
      PreviousHighestHigh(
         r,
         1,
         BOSLookback
      );

   double bosLow =
      PreviousLowestLow(
         r,
         1,
         BOSLookback
      );

   bullBOS =
      signal.close >
      bosHigh;

   bearBOS =
      signal.close <
      bosLow;

   //----------------------------------------------------
   // BUY TRIGGER
   //----------------------------------------------------

   bool buyTrigger =
      h4Bull;

   if(RequireLiquiditySweep)
      buyTrigger =
         buyTrigger &&
         spring;

   if(RequireBOS)
      buyTrigger =
         buyTrigger &&
         bullBOS;

   //----------------------------------------------------
   // SELL TRIGGER
   //----------------------------------------------------

   bool sellTrigger =
      h4Bear;

   if(RequireLiquiditySweep)
      sellTrigger =
         sellTrigger &&
         utad;

   if(RequireBOS)
      sellTrigger =
         sellTrigger &&
         bearBOS;

   if(
      buyTrigger ||
      sellTrigger
   )
      return 30;

   return 0;
}


//+------------------------------------------------------------------+
//| SETUP ENGINE                                                     |
//+------------------------------------------------------------------+

SetupResult AnalyzeSetup()
{
   SetupResult s;

   ZeroMemory(s);

   //--------------------------------
   // H4 = 40
   //--------------------------------

   int h4Score =
      GetH4Bias(
         s.h4Bull,
         s.h4Bear
      );

   //--------------------------------
   // M15 = 30
   //--------------------------------

   int m15Score = 0;

   if(h4Score > 0)
   {
      m15Score =
         GetM15Zone(
            s.h4Bull,
            s.h4Bear,
            s.m15Premium,
            s.m15Deep,
            s.fib618,
            s.fib71,
            s.fib886,
            s.fib95
         );
   }

   //--------------------------------
   // M5 = 30
   //--------------------------------

   int m5Score = 0;

   if(
      h4Score > 0 &&
      m15Score > 0
   )
   {
      m5Score =
         GetM5Trigger(
            s.h4Bull,
            s.h4Bear,
            s.spring,
            s.utad,
            s.bullBOS,
            s.bearBOS
         );
   }

   //--------------------------------
   // TOTAL
   //--------------------------------

   s.score =
      h4Score +
      m15Score +
      m5Score;

   //--------------------------------
   // FINAL BUY
   //--------------------------------

   s.buy =
      (
         s.score >= MinimumSetupScore
         &&
         s.h4Bull
         &&
         (
            s.m15Premium ||
            s.m15Deep
         )
         &&
         s.spring
         &&
         s.bullBOS
      );

   //--------------------------------
   // FINAL SELL
   //--------------------------------

   s.sell =
      (
         s.score >= MinimumSetupScore
         &&
         s.h4Bear
         &&
         (
            s.m15Premium ||
            s.m15Deep
         )
         &&
         s.utad
         &&
         s.bearBOS
      );

   //--------------------------------
   // REASON
   //--------------------------------

   if(s.buy)
   {
      s.reason =
         "A+ BUY | H4 Bull + M15 Fibo + M5 Spring/BOS";
   }
   else
   if(s.sell)
   {
      s.reason =
         "A+ SELL | H4 Bear + M15 Fibo + M5 UTAD/BOS";
   }
   else
   {
      s.reason =
         "WAIT";
   }

   return s;
}


//+------------------------------------------------------------------+
//| NEWS PARSER                                                      |
//+------------------------------------------------------------------+

void ParseNewsTimes()
{
   newsCount = 0;

   ArrayResize(newsStart,0);
   ArrayResize(newsEnd,0);

   string raw =
      InpNewsTimes;

   StringTrimLeft(raw);
   StringTrimRight(raw);

   if(StringLen(raw)==0)
      return;

   string tokens[];

   int total =
      StringSplit(
         raw,
         ';',
         tokens
      );

   for(int i=0;i<total;i++)
   {
      string token =
         tokens[i];

      StringTrimLeft(token);
      StringTrimRight(token);

      int space =
         StringFind(
            token,
            " "
         );

      if(space < 0)
         continue;

      string datePart =
         StringSubstr(
            token,
            0,
            space
         );

      string timePart =
         StringSubstr(
            token,
            space+1
         );

      string times[];

      if(StringSplit(
         timePart,
         '-',
         times) != 2)
         continue;

      datetime start =
         StringToTime(
            datePart+
            " "+
            times[0]
         );

      datetime end =
         StringToTime(
            datePart+
            " "+
            times[1]
         );

      if(start==0 ||
         end==0)
         continue;

      if(end <= start)
         end += 86400;

      ArrayResize(
         newsStart,
         newsCount+1
      );

      ArrayResize(
         newsEnd,
         newsCount+1
      );

      newsStart[newsCount] =
         start;

      newsEnd[newsCount] =
         end;

      newsCount++;
   }
}


//+------------------------------------------------------------------+
//| NEWS BLACKOUT                                                    |
//+------------------------------------------------------------------+

bool IsNewsBlackout()
{
   datetime now =
      TimeCurrent();

   for(int i=0;
       i<newsCount;
       i++)
   {
      if(
         now >= newsStart[i] &&
         now <= newsEnd[i]
      )
         return true;
   }

   return false;
}


//+------------------------------------------------------------------+
//| NY DST                                                           |
//+------------------------------------------------------------------+

int NthWeekday(
   int year,
   int month,
   int weekday,
   int nth
)
{
   MqlDateTime d;

   ZeroMemory(d);

   d.year = year;
   d.mon  = month;
   d.day  = 1;

   datetime first =
      StructToTime(d);

   MqlDateTime f;

   TimeToStruct(
      first,
      f
   );

   int delta =
      weekday -
      f.day_of_week;

   if(delta < 0)
      delta += 7;

   return(
      1 +
      delta +
      (nth-1)*7
   );
}


datetime DateUTC(
   int y,
   int m,
   int d,
   int h
)
{
   MqlDateTime x;

   ZeroMemory(x);

   x.year = y;
   x.mon  = m;
   x.day  = d;
   x.hour = h;

   return StructToTime(x);
}


bool IsNYDST(
   datetime gmt
)
{
   MqlDateTime x;

   TimeToStruct(
      gmt,
      x
   );

   int y =
      x.year;

   int march =
      NthWeekday(
         y,
         3,
         0,
         2
      );

   int november =
      NthWeekday(
         y,
         11,
         0,
         1
      );

   datetime start =
      DateUTC(
         y,
         3,
         march,
         7
      );

   datetime end =
      DateUTC(
         y,
         11,
         november,
         6
      );

   return(
      gmt >= start &&
      gmt < end
   );
}


//+------------------------------------------------------------------+
//| NY SESSION                                                       |
//+------------------------------------------------------------------+

bool NYSession()
{
   datetime gmt =
      TimeGMT();

   int offset =
      IsNYDST(gmt)
      ? -4
      : -5;

   datetime ny =
      gmt +
      offset*3600;

   MqlDateTime t;

   TimeToStruct(
      ny,
      t
   );

   int minutes =
      t.hour*60 +
      t.min;

   return(
      minutes >= 570 && // 09:30
      minutes < 960     // 16:00
   );
}


//+------------------------------------------------------------------+
//| POSITION EXISTS                                                  |
//+------------------------------------------------------------------+

bool HasPosition()
{
   for(int i=PositionsTotal()-1;
       i>=0;
       i--)
   {
      ulong ticket =
         PositionGetTicket(i);

      if(ticket==0)
         continue;

      if(!PositionSelectByTicket(
         ticket))
         continue;

      if(
         PositionGetString(
            POSITION_SYMBOL
         ) == _Symbol
         &&
         PositionGetInteger(
            POSITION_MAGIC
         ) == MagicNumber
      )
         return true;
   }

   return false;
}


//+------------------------------------------------------------------+
//| SPREAD                                                           |
//+------------------------------------------------------------------+

double SpreadPoints()
{
   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );

   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );

   return(
      (ask-bid) /
      _Point
   );
}


//+------------------------------------------------------------------+
//| VOLUME                                                           |
//+------------------------------------------------------------------+

double NormalizeLot(
   double volume
)
{
   double minimum =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_VOLUME_MIN
      );

   double maximum =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_VOLUME_MAX
      );

   double step =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_VOLUME_STEP
      );

   if(step <= 0)
      step = 0.01;

   volume =
      MathMax(
         minimum,
         volume
      );

   volume =
      MathMin(
         maximum,
         volume
      );

   volume =
      MathFloor(
         volume/step
      )*step;

   int digits = 2;

   if(step >= 1)
      digits = 0;

   else if(step >= 0.1)
      digits = 1;

   else if(step >= 0.01)
      digits = 2;

   else
      digits = 3;

   return
      NormalizeDouble(
         volume,
         digits
      );
}


//+------------------------------------------------------------------+
//| RISK LOT                                                         |
//+------------------------------------------------------------------+

double CalculateLot(
   ENUM_ORDER_TYPE type,
   double entry,
   double stop
)
{
   if(!UseRiskPercent)
      return NormalizeLot(
         FixedLot
      );

   double balance =
      AccountInfoDouble(
         ACCOUNT_BALANCE
      );

   double riskMoney =
      balance*
      RiskPercent/
      100.0;

   double oneLotLoss = 0;

   if(!OrderCalcProfit(
      type,
      _Symbol,
      1.0,
      entry,
      stop,
      oneLotLoss))
   {
      return NormalizeLot(
         FixedLot
      );
   }

   oneLotLoss =
      MathAbs(
         oneLotLoss
      );

   if(oneLotLoss <= 0)
      return NormalizeLot(
         FixedLot
      );

   return NormalizeLot(
      riskMoney /
      oneLotLoss
   );
}


//+------------------------------------------------------------------+
//| EXECUTION BUY                                                    |
//+------------------------------------------------------------------+

bool OpenBuy(
   int score
)
{
   double ask =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_ASK
      );

   double sl =
      NP(
         ask -
         StopLossPoints*
         _Point
      );

   double tp =
      NP(
         ask +
         TakeProfitPoints*
         _Point
      );

   double lot =
      CalculateLot(
         ORDER_TYPE_BUY,
         ask,
         sl
      );

   trade.SetExpertMagicNumber(
      MagicNumber
   );

   trade.SetTypeFillingBySymbol(
      _Symbol
   );

   bool sent =
      trade.Buy(
         lot,
         _Symbol,
         0,
         sl,
         tp,
         "DREVM v3.3 A+ BUY "+IntegerToString(score)
      );

   if(!sent)
   {
      Print(
         "❌ BUY request failure | ",
         trade.ResultRetcode(),
         " | ",
         trade.ResultRetcodeDescription()
      );

      return false;
   }

   uint rc =
      trade.ResultRetcode();

   if(
      rc != TRADE_RETCODE_DONE &&
      rc != TRADE_RETCODE_PLACED &&
      rc != TRADE_RETCODE_DONE_PARTIAL
   )
   {
      Print(
         "❌ BUY rejected | ",
         rc,
         " | ",
         trade.ResultRetcodeDescription()
      );

      return false;
   }

   Print(
      "✅ DREVM BUY | SCORE ",
      score,
      "/100 | LOT ",
      lot,
      " | SL ",
      sl,
      " | TP ",
      tp
   );

   return true;
}


//+------------------------------------------------------------------+
//| EXECUTION SELL                                                   |
//+------------------------------------------------------------------+

bool OpenSell(
   int score
)
{
   double bid =
      SymbolInfoDouble(
         _Symbol,
         SYMBOL_BID
      );

   double sl =
      NP(
         bid +
         StopLossPoints*
         _Point
      );

   double tp =
      NP(
         bid -
         TakeProfitPoints*
         _Point
      );

   double lot =
      CalculateLot(
         ORDER_TYPE_SELL,
         bid,
         sl
      );

   trade.SetExpertMagicNumber(
      MagicNumber
   );

   trade.SetTypeFillingBySymbol(
      _Symbol
   );

   bool sent =
      trade.Sell(
         lot,
         _Symbol,
         0,
         sl,
         tp,
         "DREVM v3.3 A+ SELL "+IntegerToString(score)
      );

   if(!sent)
   {
      Print(
         "❌ SELL request failure | ",
         trade.ResultRetcode(),
         " | ",
         trade.ResultRetcodeDescription()
      );

      return false;
   }

   uint rc =
      trade.ResultRetcode();

   if(
      rc != TRADE_RETCODE_DONE &&
      rc != TRADE_RETCODE_PLACED &&
      rc != TRADE_RETCODE_DONE_PARTIAL
   )
   {
      Print(
         "❌ SELL rejected | ",
         rc,
         " | ",
         trade.ResultRetcodeDescription()
      );

      return false;
   }

   Print(
      "✅ DREVM SELL | SCORE ",
      score,
      "/100 | LOT ",
      lot,
      " | SL ",
      sl,
      " | TP ",
      tp
   );

   return true;
}


//+------------------------------------------------------------------+
//| INIT                                                             |
//+------------------------------------------------------------------+

int OnInit()
{
   h4EMA50 =
      iMA(
         _Symbol,
         BiasTF,
         H4EMAFast,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );

   h4EMA200 =
      iMA(
         _Symbol,
         BiasTF,
         H4EMASlow,
         0,
         MODE_EMA,
         PRICE_CLOSE
      );

   if(
      h4EMA50 ==
      INVALID_HANDLE
      ||
      h4EMA200 ==
      INVALID_HANDLE
   )
   {
      Print(
         "❌ H4 EMA initialization failed"
      );

      return INIT_FAILED;
   }

   trade.SetExpertMagicNumber(
      MagicNumber
   );

   trade.SetTypeFillingBySymbol(
      _Symbol
   );

   ParseNewsTimes();

   Print(
      "================================="
   );

   Print(
      "✅ DREVM FIBO WYCKOFF AUTO v3.3"
   );

   Print(
      "H4  = BIAS 40"
   );

   Print(
      "M15 = FIBO 30"
   );

   Print(
      "M5  = SPRING/UTAD/BOS 30"
   );

   Print(
      "MIN SCORE = ",
      MinimumSetupScore
   );

   Print(
      "SL = ",
      StopLossPoints,
      " | TP = ",
      TakeProfitPoints
   );

   Print(
      "================================="
   );

   return INIT_SUCCEEDED;
}


//+------------------------------------------------------------------+
//| DEINIT                                                           |
//+------------------------------------------------------------------+

void OnDeinit(
   const int reason
)
{
   if(
      h4EMA50 !=
      INVALID_HANDLE
   )
      IndicatorRelease(
         h4EMA50
      );

   if(
      h4EMA200 !=
      INVALID_HANDLE
   )
      IndicatorRelease(
         h4EMA200
      );

   Comment("");
}


//+------------------------------------------------------------------+
//| ON TICK                                                          |
//+------------------------------------------------------------------+

void OnTick()
{
   //---------------------------------------------------------------
   // EA works from M5 clock,
   // regardless of chart timeframe
   //---------------------------------------------------------------

   datetime currentM5 =
      iTime(
         _Symbol,
         TriggerTF,
         0
      );

   if(currentM5 == 0)
      return;

   if(currentM5 ==
      lastM5Bar)
      return;

   lastM5Bar =
      currentM5;

   //---------------------------------------------------------------
   // ANALYSIS
   //---------------------------------------------------------------

   SetupResult setup =
      AnalyzeSetup();

   //---------------------------------------------------------------
   // PANEL
   //---------------------------------------------------------------

   string bias =
      "NEUTRAL";

   if(setup.h4Bull)
      bias =
         "📈 BULL";

   if(setup.h4Bear)
      bias =
         "📉 BEAR";

   string zone =
      "NO ZONE";

   if(setup.m15Premium)
      zone =
         "🔥 61.8-71";

   if(setup.m15Deep)
      zone =
         "💎 88.6-95";

   string wyckoff =
      "NONE";

   if(setup.spring)
      wyckoff =
         "🟢 SPRING";

   if(setup.utad)
      wyckoff =
         "🔴 UTAD";

   string structure =
      "NO BOS";

   if(setup.bullBOS)
      structure =
         "⬆ BULL BOS";

   if(setup.bearBOS)
      structure =
         "⬇ BEAR BOS";

   string action =
      "WAIT";

   if(setup.buy)
      action =
         "✅ BUY A+";

   if(setup.sell)
      action =
         "✅ SELL A+";

   string panel =
      "══ DREVM v3.3 ══\n"
      +
      "H4: "+bias+"\n"
      +
      "M15: "+zone+"\n"
      +
      "M5: "+wyckoff+"\n"
      +
      "Structure: "+structure+"\n"
      +
      "────────────────\n"
      +
      "61.8: "+
      DoubleToString(
         setup.fib618,
         _Digits
      )+"\n"
      +
      "71: "+
      DoubleToString(
         setup.fib71,
         _Digits
      )+"\n"
      +
      "88.6: "+
      DoubleToString(
         setup.fib886,
         _Digits
      )+"\n"
      +
      "95: "+
      DoubleToString(
         setup.fib95,
         _Digits
      )+"\n"
      +
      "────────────────\n"
      +
      "SCORE: "+
      IntegerToString(
         setup.score
      )+
      "/100\n"
      +
      "MIN: "+
      IntegerToString(
         MinimumSetupScore
      )+
      "\n"
      +
      "SL: "+
      IntegerToString(
         StopLossPoints
      )+
      " pts\n"
      +
      "TP: "+
      IntegerToString(
         TakeProfitPoints
      )+
      " pts\n"
      +
      "Spread: "+
      DoubleToString(
         SpreadPoints(),
         1
      )+
      "\n"
      +
      "NY: "+
      (
         NYSession()
         ?
         "🗽 ACTIVE"
         :
         "OFF"
      )+
      "\n"
      +
      "News: "+
      (
         IsNewsBlackout()
         ?
         "⛔ BLACKOUT"
         :
         "✅ OK"
      )+
      "\n"
      +
      "────────────────\n"
      +
      "ACTION: "+
      action;

   Comment(panel);

   //---------------------------------------------------------------
   // NO SIGNAL
   //---------------------------------------------------------------

   if(
      !setup.buy &&
      !setup.sell
   )
      return;

   //---------------------------------------------------------------
   // AUTO OFF
   //---------------------------------------------------------------

   if(!AutoTradingEnabled)
   {
      Print(
         "⚠ A+ détecté mais AUTO OFF"
      );

      return;
   }

   //---------------------------------------------------------------
   // NY ONLY
   //---------------------------------------------------------------

   if(!NYSession())
   {
      Print(
         "⏸ A+ refusé : hors NY"
      );

      return;
   }

   //---------------------------------------------------------------
   // NEWS
   //---------------------------------------------------------------

   if(
      BlockTradingOnNews &&
      IsNewsBlackout()
   )
   {
      Print(
         "⛔ A+ refusé : NEWS BLACKOUT"
      );

      return;
   }

   //---------------------------------------------------------------
   // SPREAD
   //---------------------------------------------------------------

   if(
      SpreadPoints() >
      MaxSpreadPoints
   )
   {
      Print(
         "⛔ A+ refusé : Spread = ",
         SpreadPoints()
      );

      return;
   }

   //---------------------------------------------------------------
   // EXISTING POSITION
   //---------------------------------------------------------------

   if(HasPosition())
   {
      Print(
         "⏸ Position DREVM déjà active"
      );

      return;
   }

   //---------------------------------------------------------------
   // SAME BAR PROTECTION
   //---------------------------------------------------------------

   if(
      lastTradeM5Bar ==
      currentM5
   )
      return;

   //---------------------------------------------------------------
   // EXECUTION
   //---------------------------------------------------------------

   bool opened = false;

   if(setup.buy)
      opened =
         OpenBuy(
            setup.score
         );

   else
   if(setup.sell)
      opened =
         OpenSell(
            setup.score
         );

   if(opened)
      lastTradeM5Bar =
         currentM5;
}
//+------------------------------------------------------------------+