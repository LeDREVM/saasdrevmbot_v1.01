//+------------------------------------------------------------------+
//|  NY Session · Wyckoff Scoring · FVG · OB · Fibonacci            |
//|  + Market Structure · Displacement · Volume Imbalance            |
//|  + Liquidity · NWOG/NDOG · Killzones · RSI Divergences          |
//|  Compatible MT5 — indicator overlay                              |
//+------------------------------------------------------------------+
#property copyright   "DreVM Trading"
#property version     "2.00"
#property indicator_chart_window
#property indicator_plots 0

//=== INPUTS ===========================================================

// --- Killzones --------------------------------------------------------
input group            "── Killzones ──"
input bool   InpShowNY        = true;
input color  InpNYColor       = C'255,93,0';
input int    InpNYStartHour   = 9;    // EST (UTC-5)
input int    InpNYStartMin    = 30;
input int    InpNYEndHour     = 16;
input int    InpNYEndMin      = 0;
input bool   InpShowLdnOpen   = true;
input color  InpLdnOpenColor  = C'0,188,212';
input bool   InpShowLdnClose  = true;
input color  InpLdnCloseColor = C'33,87,243';
input bool   InpShowAsian     = true;
input color  InpAsianColor    = C'233,30,99';

// --- Market Structure -------------------------------------------------
input group            "── Market Structure ──"
input bool   InpShowMS        = true;
input int    InpMSLen         = 5;
input color  InpMSSBullColor  = C'0,230,161';
input color  InpMSSBearColor  = C'230,4,0';
input bool   InpShowBOS       = true;

// --- Displacement -----------------------------------------------------
input group            "── Displacement ──"
input bool   InpShowDispl     = false;
input color  InpDisplUpColor  = clrLime;
input color  InpDisplDnColor  = clrRed;

// --- Volume Imbalance -------------------------------------------------
input group            "── Volume Imbalance ──"
input bool   InpShowVI        = true;
input int    InpMaxVI         = 3;
input color  InpVIColor       = C'6,178,208';

// --- Order Blocks -----------------------------------------------------
input group            "── Order Blocks ──"
input bool   InpShowOB        = true;
input int    InpOBLookback    = 10;
input color  InpBullOBColor   = C'62,137,250';
input color  InpBearOBColor   = C'255,49,49';
input bool   InpShowOBLabel   = true;

// --- Fair Value Gaps --------------------------------------------------
input group            "── Fair Value Gaps ──"
input bool   InpShowFVG       = true;
input int    InpMaxFVG        = 3;
input color  InpBullFVGColor  = C'0,230,118';
input color  InpBearFVGColor  = C'255,82,82';

// --- Liquidity --------------------------------------------------------
input group            "── Liquidity ──"
input bool   InpShowLiq       = true;
input int    InpLiqMargin     = 4;   // diviseur ATR
input color  InpLiqBuyColor   = C'250,69,28';
input color  InpLiqSellColor  = C'28,228,250';

// --- NWOG / NDOG ------------------------------------------------------
input group            "── NWOG / NDOG ──"
input bool   InpShowNWOG      = true;
input color  InpNWOGColor     = C'255,82,82';
input bool   InpShowNDOG      = false;
input color  InpNDOGColor     = C'255,152,0';

// --- Fibonacci --------------------------------------------------------
input group            "── Fibonacci ──"
input bool   InpShowFib       = true;
input int    InpFibSwingLen   = 20;
input color  InpOTEBullColor  = C'0,230,118';
input color  InpOTEBearColor  = C'255,82,82';

// --- Wyckoff ----------------------------------------------------------
input group            "── Wyckoff ──"
input bool   InpShowWyck      = true;
input int    InpWyckLookback  = 20;
input double InpVolMult       = 2.0;
input color  InpClimaxColor   = C'255,152,0';
input color  InpSpringColor   = C'0,230,118';
input color  InpUTColor       = C'255,49,49';

// --- RSI + Divergences ------------------------------------------------
input group            "── RSI ──"
input bool   InpShowRSI       = true;
input int    InpRSILen        = 14;
input double InpRSIOB         = 70.0;
input double InpRSIOS         = 30.0;
input bool   InpShowDiv       = true;
input int    InpDivLen        = 5;
input color  InpRSIOBColor    = C'255,82,82';
input color  InpRSIOSColor    = C'0,230,118';

// --- Score Panel ------------------------------------------------------
input group            "── Panneau Score ──"
input bool   InpShowPanel     = true;
input int    InpPanelX        = 20;
input int    InpPanelY        = 30;

//=== GLOBALS ==========================================================
int    g_tf_sec;
double g_atr;

// RSI buffers (calculés une fois)
double g_rsi[];

// Swing tracking pour Market Structure
struct SwingPoint { datetime t; double price; int dir; };
SwingPoint g_swings[];
int g_swing_dir = 0;

//======================================================================
int OnInit()
{
    g_tf_sec = PeriodSeconds();
    ArraySetAsSeries(g_rsi, true);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { ObjectsDeleteAll(0, "DV_"); }

//======================================================================
int OnCalculate(const int       rates_total,
                const int       prev_calculated,
                const datetime &time[],
                const double   &open[],
                const double   &high[],
                const double   &low[],
                const double   &close[],
                const long     &tick_volume[],
                const long     &volume[],
                const int      &spread[])
{
    if(rates_total < InpWyckLookback + 10) return 0;

    bool full_recalc = (prev_calculated == 0);
    bool new_bar     = (prev_calculated < rates_total);
    if(!full_recalc && !new_bar) return rates_total;

    // ATR approximation
    g_atr = CalcATR(14, rates_total - 2);

    if(full_recalc) ObjectsDeleteAll(0, "DV_");

    // --- RSI array ---
    CalcRSI(rates_total, close);

    int start = full_recalc ? InpWyckLookback + 3 : MathMax(InpWyckLookback + 3, prev_calculated - 2);
    int limit  = rates_total - 2;

    // --- Boucle principale ---
    for(int i = start; i <= limit; i++)
    {
        // Killzones
        DrawKillzones(i, time);

        // NWOG / NDOG
        if(InpShowNWOG || InpShowNDOG) DrawGaps(i, time, open, close);

        // Displacement
        if(InpShowDispl) DrawDisplacement(i, time, open, high, low, close);

        // Volume Imbalance
        if(InpShowVI) DrawVolumeImbalance(i, time, open, high, low, close);

        // FVG
        if(InpShowFVG) DetectFVG(i, time, high, low);

        // Order Blocks
        if(InpShowOB) DetectOB(i, rates_total, time, open, high, low, close);

        // Wyckoff
        if(InpShowWyck) DetectWyckoff(i, rates_total, time, open, high, low, close, tick_volume);

        // RSI signals
        if(InpShowRSI) DrawRSISignals(i, time, high, low);

        // RSI divergences
        if(InpShowRSI && InpShowDiv) DrawDivergences(i, rates_total, time, high, low);
    }

    // Market Structure (zigzag global)
    if(InpShowMS) DrawMarketStructure(rates_total, time, high, low, close);

    // Liquidity
    if(InpShowLiq) DrawLiquidity(rates_total, time, high, low);

    // Fibonacci
    if(InpShowFib) DrawFibonacci(rates_total, time, high, low);

    // Score panel
    if(InpShowPanel) DrawScorePanel(rates_total, time, open, high, low, close, tick_volume);

    return rates_total;
}

//======================================================================
//  KILLZONES
//======================================================================
void DrawKillzones(int i, const datetime &time[])
{
    MqlDateTime dt; TimeToStruct(time[i], dt);

    // NY : UTC-5
    int est_h   = (dt.hour - 5 + 24) % 24;
    int est_min = est_h * 60 + dt.min;
    bool in_ny  = InpShowNY && est_min >= InpNYStartHour*60+InpNYStartMin && est_min < InpNYEndHour*60+InpNYEndMin;

    // London Open : 08:00–11:00 UTC
    int utc_min  = dt.hour * 60 + dt.min;
    bool in_ldo  = InpShowLdnOpen  && utc_min >= 480  && utc_min < 660;
    // London Close: 15:00–17:00 UTC
    bool in_ldc  = InpShowLdnClose && utc_min >= 900  && utc_min < 1020;
    // Asian       : 00:00–04:00 UTC
    bool in_asia = InpShowAsian    && utc_min >= 0    && utc_min < 240;

    color kz_color = 0;
    if(in_ny)   kz_color = InpNYColor;
    else if(in_ldo)  kz_color = InpLdnOpenColor;
    else if(in_ldc)  kz_color = InpLdnCloseColor;
    else if(in_asia) kz_color = InpAsianColor;
    else return;

    string name = "DV_KZ_" + IntegerToString(i);
    if(ObjectFind(0, name) >= 0) return;

    double chart_max = ChartGetDouble(0, CHART_PRICE_MAX);
    double chart_min = ChartGetDouble(0, CHART_PRICE_MIN);
    ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                 time[i], chart_max,
                 time[i] + (datetime)g_tf_sec, chart_min);
    ObjectSetInteger(0, name, OBJPROP_COLOR,   kz_color);
    ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(kz_color, 230));
    ObjectSetInteger(0, name, OBJPROP_FILL,    true);
    ObjectSetInteger(0, name, OBJPROP_BACK,    true);
    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//======================================================================
//  NWOG / NDOG  (New Week/Day Opening Gap)
//======================================================================
void DrawGaps(int i, const datetime &time[],
              const double &open[], const double &close[])
{
    MqlDateTime dt; TimeToStruct(time[i], dt);
    MqlDateTime dt_prev; TimeToStruct(time[i-1], dt_prev);

    // NDOG : premier bar du jour (changement de jour)
    if(InpShowNDOG && dt.day != dt_prev.day && dt.hour < 4)
    {
        double gap_top = MathMax(open[i], close[i-1]);
        double gap_btm = MathMin(open[i], close[i-1]);
        if(MathAbs(gap_top - gap_btm) > _Point * 5)
        {
            string name = "DV_NDOG_" + IntegerToString(i);
            if(ObjectFind(0, name) < 0)
            {
                datetime x_end = time[i] + (datetime)(g_tf_sec * 200);
                ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                             time[i-1], gap_top, x_end, gap_btm);
                ObjectSetInteger(0, name, OBJPROP_COLOR,   InpNDOGColor);
                ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpNDOGColor, 220));
                ObjectSetInteger(0, name, OBJPROP_FILL,    true);
                ObjectSetInteger(0, name, OBJPROP_BACK,    true);
                ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                string mid_name = name + "_M";
                ObjectCreate(0, mid_name, OBJ_TREND, 0,
                             time[i-1], (gap_top+gap_btm)/2.0,
                             x_end, (gap_top+gap_btm)/2.0);
                ObjectSetInteger(0, mid_name, OBJPROP_COLOR,    InpNDOGColor);
                ObjectSetInteger(0, mid_name, OBJPROP_STYLE,    STYLE_DOT);
                ObjectSetInteger(0, mid_name, OBJPROP_RAY_RIGHT, true);
                ObjectSetInteger(0, mid_name, OBJPROP_SELECTABLE, false);
            }
        }
    }

    // NWOG : lundi = dayofweek 1 (MT5 lundi=1)
    if(InpShowNWOG && dt.day_of_week == 1 && dt_prev.day_of_week == 5)
    {
        double gap_top = MathMax(open[i], close[i-1]);
        double gap_btm = MathMin(open[i], close[i-1]);
        if(MathAbs(gap_top - gap_btm) > _Point * 5)
        {
            string name = "DV_NWOG_" + IntegerToString(i);
            if(ObjectFind(0, name) < 0)
            {
                datetime x_end = time[i] + (datetime)(g_tf_sec * 1000);
                ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                             time[i-1], gap_top, x_end, gap_btm);
                ObjectSetInteger(0, name, OBJPROP_COLOR,   InpNWOGColor);
                ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpNWOGColor, 235));
                ObjectSetInteger(0, name, OBJPROP_FILL,    true);
                ObjectSetInteger(0, name, OBJPROP_BACK,    true);
                ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                string mid_name = name + "_M";
                ObjectCreate(0, mid_name, OBJ_TREND, 0,
                             time[i-1], (gap_top+gap_btm)/2.0,
                             x_end, (gap_top+gap_btm)/2.0);
                ObjectSetInteger(0, mid_name, OBJPROP_COLOR,    InpNWOGColor);
                ObjectSetInteger(0, mid_name, OBJPROP_STYLE,    STYLE_DOT);
                ObjectSetInteger(0, mid_name, OBJPROP_RAY_RIGHT, true);
                ObjectSetInteger(0, mid_name, OBJPROP_SELECTABLE, false);
                // Label "NWOG"
                string lname = name + "_L";
                ObjectCreate(0, lname, OBJ_TEXT, 0, time[i], gap_top);
                ObjectSetString (0, lname, OBJPROP_TEXT,     "NWOG");
                ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpNWOGColor);
                ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
            }
        }
    }
}

//======================================================================
//  DISPLACEMENT  (grande bougie à corps fort, peu de mèches)
//======================================================================
void DrawDisplacement(int i, const datetime &time[],
                      const double &open[], const double &high[],
                      const double &low[], const double &close[])
{
    if(i < 5) return;
    double body     = MathAbs(close[i] - open[i]);
    double mean_b   = 0;
    for(int k=1;k<=5;k++) mean_b += MathAbs(close[i-k]-open[i-k]);
    mean_b /= 5;
    if(body < mean_b) return;

    double mx = MathMax(close[i], open[i]);
    double mn = MathMin(close[i], open[i]);
    double wick_top = high[i] - mx;
    double wick_btm = mn - low[i];
    double threshold = body * 0.36;

    bool is_displ_up = (close[i] > open[i]) && (wick_top < threshold) && (wick_btm < threshold);
    bool is_displ_dn = (close[i] < open[i]) && (wick_top < threshold) && (wick_btm < threshold);

    if(is_displ_up)
    {
        string name = "DV_DISP_U_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_ARROW, 0, time[i], low[i]);
            ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 233);
            ObjectSetInteger(0, name, OBJPROP_COLOR,     InpDisplUpColor);
            ObjectSetInteger(0, name, OBJPROP_WIDTH,     2);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        }
    }
    if(is_displ_dn)
    {
        string name = "DV_DISP_D_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_ARROW, 0, time[i], high[i]);
            ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 234);
            ObjectSetInteger(0, name, OBJPROP_COLOR,     InpDisplDnColor);
            ObjectSetInteger(0, name, OBJPROP_WIDTH,     2);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        }
    }
}

//======================================================================
//  VOLUME IMBALANCE
//======================================================================
void DrawVolumeImbalance(int i, const datetime &time[],
                          const double &open[], const double &high[],
                          const double &low[], const double &close[])
{
    if(i < 1) return;
    double mx  = MathMax(close[i],   open[i]);
    double mn  = MathMin(close[i],   open[i]);
    double mx1 = MathMax(close[i-1], open[i-1]);
    double mn1 = MathMin(close[i-1], open[i-1]);

    // VI haussière : open[i] > close[i-1] (gap haussier entre corps)
    bool vi_bull = (open[i] > close[i-1]) && (high[i-1] > low[i]) &&
                   (close[i] > close[i-1]) && (open[i] > open[i-1]) && (high[i-1] < mn);
    // VI baissière : open[i] < close[i-1]
    bool vi_bear = (open[i] < close[i-1]) && (low[i-1] < high[i]) &&
                   (close[i] < close[i-1]) && (open[i] < open[i-1]) && (low[i-1] > mx);

    if(vi_bull)
    {
        string name = "DV_VI_B_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            // Zone entre mx[i-1] et mn[i]
            double top = mn, btm = mx1;
            if(top < btm){ double tmp=top; top=btm; btm=tmp; }
            ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                         time[i-1], top,
                         time[i] + (datetime)(g_tf_sec * 15), btm);
            ObjectSetInteger(0, name, OBJPROP_COLOR,   InpVIColor);
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpVIColor, 210));
            ObjectSetInteger(0, name, OBJPROP_FILL,    true);
            ObjectSetInteger(0, name, OBJPROP_BACK,    true);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            string lname = name + "_L";
            ObjectCreate(0, lname, OBJ_TEXT, 0, time[i], (top+btm)/2.0);
            ObjectSetString (0, lname, OBJPROP_TEXT, "VI");
            ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpVIColor);
            ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
            ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
        }
    }
    if(vi_bear)
    {
        string name = "DV_VI_S_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            double top = mn1, btm = mx;
            if(top < btm){ double tmp=top; top=btm; btm=tmp; }
            ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                         time[i-1], top,
                         time[i] + (datetime)(g_tf_sec * 15), btm);
            ObjectSetInteger(0, name, OBJPROP_COLOR,   InpVIColor);
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpVIColor, 210));
            ObjectSetInteger(0, name, OBJPROP_FILL,    true);
            ObjectSetInteger(0, name, OBJPROP_BACK,    true);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            string lname = name + "_L";
            ObjectCreate(0, lname, OBJ_TEXT, 0, time[i], (top+btm)/2.0);
            ObjectSetString (0, lname, OBJPROP_TEXT, "VI");
            ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpVIColor);
            ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
            ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
        }
    }
}

//======================================================================
//  FAIR VALUE GAPS
//======================================================================
void DetectFVG(int i, const datetime &time[],
               const double &high[], const double &low[])
{
    if(i < 2) return;

    if(low[i] > high[i-2])
    {
        string name = "DV_FVG_B_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                         time[i-2], high[i-2],
                         time[i] + (datetime)(g_tf_sec * 25), low[i]);
            ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBullFVGColor);
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpBullFVGColor, 220));
            ObjectSetInteger(0, name, OBJPROP_FILL,    true);
            ObjectSetInteger(0, name, OBJPROP_BACK,    true);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            string lname = name + "_L";
            ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-1], low[i]);
            ObjectSetString (0, lname, OBJPROP_TEXT, "FVG▲");
            ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBullFVGColor);
            ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
            ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
        }
    }

    if(high[i] < low[i-2])
    {
        string name = "DV_FVG_S_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                         time[i-2], low[i-2],
                         time[i] + (datetime)(g_tf_sec * 25), high[i]);
            ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBearFVGColor);
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpBearFVGColor, 220));
            ObjectSetInteger(0, name, OBJPROP_FILL,    true);
            ObjectSetInteger(0, name, OBJPROP_BACK,    true);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            string lname = name + "_L";
            ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-1], high[i]);
            ObjectSetString (0, lname, OBJPROP_TEXT, "FVG▼");
            ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBearFVGColor);
            ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
            ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
        }
    }
}

//======================================================================
//  ORDER BLOCKS
//======================================================================
void DetectOB(int i, int rates_total,
              const datetime &time[],
              const double &open[], const double &high[],
              const double &low[], const double &close[])
{
    int lb = InpOBLookback;
    if(i < lb + 1 || i >= rates_total - 1) return;

    double prev_high = high[i-1];
    for(int k = 2; k <= lb; k++) prev_high = MathMax(prev_high, high[i-k]);

    if(close[i] > prev_high)
    {
        for(int k = 1; k <= lb; k++)
        {
            if(close[i-k] < open[i-k])
            {
                string name = "DV_OB_B_" + IntegerToString(i);
                if(ObjectFind(0, name) < 0)
                {
                    double ob_top = MathMax(open[i-k], close[i-k]);
                    double ob_btm = MathMin(open[i-k], close[i-k]);
                    ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                                 time[i-k], ob_top,
                                 time[i] + (datetime)(g_tf_sec * 35), ob_btm);
                    ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBullOBColor);
                    ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpBullOBColor, 205));
                    ObjectSetInteger(0, name, OBJPROP_FILL,    true);
                    ObjectSetInteger(0, name, OBJPROP_BACK,    true);
                    ObjectSetInteger(0, name, OBJPROP_WIDTH,   1);
                    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                    if(InpShowOBLabel)
                    {
                        string lname = name + "_L";
                        ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-k], ob_btm);
                        ObjectSetString (0, lname, OBJPROP_TEXT, "+OB");
                        ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBullOBColor);
                        ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                        ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
                    }
                }
                break;
            }
        }
    }

    double prev_low = low[i-1];
    for(int k = 2; k <= lb; k++) prev_low = MathMin(prev_low, low[i-k]);

    if(close[i] < prev_low)
    {
        for(int k = 1; k <= lb; k++)
        {
            if(close[i-k] > open[i-k])
            {
                string name = "DV_OB_S_" + IntegerToString(i);
                if(ObjectFind(0, name) < 0)
                {
                    double ob_top = MathMax(open[i-k], close[i-k]);
                    double ob_btm = MathMin(open[i-k], close[i-k]);
                    ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                                 time[i-k], ob_top,
                                 time[i] + (datetime)(g_tf_sec * 35), ob_btm);
                    ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBearOBColor);
                    ObjectSetInteger(0, name, OBJPROP_BGCOLOR, BlendWithWhite(InpBearOBColor, 205));
                    ObjectSetInteger(0, name, OBJPROP_FILL,    true);
                    ObjectSetInteger(0, name, OBJPROP_BACK,    true);
                    ObjectSetInteger(0, name, OBJPROP_WIDTH,   1);
                    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                    if(InpShowOBLabel)
                    {
                        string lname = name + "_L";
                        ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-k], ob_top);
                        ObjectSetString (0, lname, OBJPROP_TEXT, "-OB");
                        ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBearOBColor);
                        ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                        ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
                    }
                }
                break;
            }
        }
    }
}

//======================================================================
//  LIQUIDITY  (Buyside / Sellside)
//======================================================================
void DrawLiquidity(int rates_total, const datetime &time[],
                   const double &high[], const double &low[])
{
    int lb = 30;
    if(rates_total < lb + 5) return;

    double margin = g_atr / InpLiqMargin;

    // Buyside : cluster de hauts proches
    for(int i = lb; i <= rates_total - 3; i++)
    {
        int count = 0;
        double ref = high[i];
        int    ref_bar = i;
        double min_h = ref, max_h = ref;
        for(int k = 1; k <= lb; k++)
        {
            if(MathAbs(high[i-k] - ref) < margin)
            {
                count++;
                min_h = MathMin(min_h, high[i-k]);
                max_h = MathMax(max_h, high[i-k]);
                ref_bar = i - k;
            }
        }
        if(count >= 2)
        {
            string name = "DV_LIQ_B_" + IntegerToString(i);
            if(ObjectFind(0, name) < 0)
            {
                double mid = (min_h + max_h) / 2.0;
                ObjectCreate(0, name, OBJ_TREND, 0,
                             time[ref_bar], mid,
                             time[0] + (datetime)(g_tf_sec * 10), mid);
                ObjectSetInteger(0, name, OBJPROP_COLOR,    InpLiqBuyColor);
                ObjectSetInteger(0, name, OBJPROP_STYLE,    STYLE_DOT);
                ObjectSetInteger(0, name, OBJPROP_WIDTH,    1);
                ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
                ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                string lname = name + "_L";
                ObjectCreate(0, lname, OBJ_TEXT, 0, time[i], max_h + margin);
                ObjectSetString (0, lname, OBJPROP_TEXT, "BSL");
                ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpLiqBuyColor);
                ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
            }
            break; // un seul cluster par direction pour éviter le bruit
        }
    }

    // Sellside : cluster de bas proches
    for(int i = lb; i <= rates_total - 3; i++)
    {
        int count = 0;
        double ref = low[i];
        int    ref_bar = i;
        double min_l = ref, max_l = ref;
        for(int k = 1; k <= lb; k++)
        {
            if(MathAbs(low[i-k] - ref) < margin)
            {
                count++;
                min_l = MathMin(min_l, low[i-k]);
                max_l = MathMax(max_l, low[i-k]);
                ref_bar = i - k;
            }
        }
        if(count >= 2)
        {
            string name = "DV_LIQ_S_" + IntegerToString(i);
            if(ObjectFind(0, name) < 0)
            {
                double mid = (min_l + max_l) / 2.0;
                ObjectCreate(0, name, OBJ_TREND, 0,
                             time[ref_bar], mid,
                             time[0] + (datetime)(g_tf_sec * 10), mid);
                ObjectSetInteger(0, name, OBJPROP_COLOR,    InpLiqSellColor);
                ObjectSetInteger(0, name, OBJPROP_STYLE,    STYLE_DOT);
                ObjectSetInteger(0, name, OBJPROP_WIDTH,    1);
                ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, true);
                ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                string lname = name + "_L";
                ObjectCreate(0, lname, OBJ_TEXT, 0, time[i], min_l - margin);
                ObjectSetString (0, lname, OBJPROP_TEXT, "SSL");
                ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpLiqSellColor);
                ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
            }
            break;
        }
    }
}

//======================================================================
//  MARKET STRUCTURE  MSS / BOS
//======================================================================
void DrawMarketStructure(int rates_total, const datetime &time[],
                          const double &high[], const double &low[],
                          const double &close[])
{
    int lb = InpMSLen;
    if(rates_total < lb * 3) return;

    int limit = rates_total - 2;

    for(int i = lb * 2; i <= limit; i++)
    {
        // Pivot high : plus haut des lb bougies de chaque côté
        bool is_ph = true, is_pl = true;
        for(int k = 1; k <= lb; k++)
        {
            if(high[i-k] >= high[i] || high[i+k] > high[i]) { is_ph = false; break; }
        }
        for(int k = 1; k <= lb; k++)
        {
            if(low[i-k] <= low[i] || low[i+k] < low[i]) { is_pl = false; break; }
        }

        if(is_ph)
        {
            // Vérifier MSS/BOS : close actuel dépasse ce pivot
            for(int j = i + 1; j <= limit; j++)
            {
                if(close[j] > high[i])
                {
                    string tag  = (g_swing_dir < 1) ? "MSS" : (InpShowBOS ? "BOS" : "");
                    if(tag == "") break;
                    string name = "DV_MS_BL_" + IntegerToString(i) + "_" + IntegerToString(j);
                    if(ObjectFind(0, name) < 0)
                    {
                        ObjectCreate(0, name, OBJ_TREND, 0,
                                     time[i], high[i], time[j], high[i]);
                        ObjectSetInteger(0, name, OBJPROP_COLOR,   InpMSSBullColor);
                        ObjectSetInteger(0, name, OBJPROP_STYLE,   STYLE_DOT);
                        ObjectSetInteger(0, name, OBJPROP_WIDTH,   1);
                        ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
                        ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                        string lname = name + "_L";
                        int mid_bar = (i + j) / 2;
                        ObjectCreate(0, lname, OBJ_TEXT, 0, time[mid_bar], high[i]);
                        ObjectSetString (0, lname, OBJPROP_TEXT, tag);
                        ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpMSSBullColor);
                        ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                        ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
                        g_swing_dir = 1;
                    }
                    break;
                }
            }
        }

        if(is_pl)
        {
            for(int j = i + 1; j <= limit; j++)
            {
                if(close[j] < low[i])
                {
                    string tag  = (g_swing_dir > -1) ? "MSS" : (InpShowBOS ? "BOS" : "");
                    if(tag == "") break;
                    string name = "DV_MS_BR_" + IntegerToString(i) + "_" + IntegerToString(j);
                    if(ObjectFind(0, name) < 0)
                    {
                        ObjectCreate(0, name, OBJ_TREND, 0,
                                     time[i], low[i], time[j], low[i]);
                        ObjectSetInteger(0, name, OBJPROP_COLOR,   InpMSSBearColor);
                        ObjectSetInteger(0, name, OBJPROP_STYLE,   STYLE_DOT);
                        ObjectSetInteger(0, name, OBJPROP_WIDTH,   1);
                        ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
                        ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                        string lname = name + "_L";
                        int mid_bar = (i + j) / 2;
                        ObjectCreate(0, lname, OBJ_TEXT, 0, time[mid_bar], low[i]);
                        ObjectSetString (0, lname, OBJPROP_TEXT, tag);
                        ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpMSSBearColor);
                        ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                        ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);
                        g_swing_dir = -1;
                    }
                    break;
                }
            }
        }
    }
}

//======================================================================
//  WYCKOFF  (SC, BC, Spring, UT, SOS, SOW, LPS, LPSY, AR)
//======================================================================
void DetectWyckoff(int i, int rates_total,
                   const datetime &time[],
                   const double &open[], const double &high[],
                   const double &low[], const double &close[],
                   const long &tick_volume[])
{
    int lb = InpWyckLookback;
    if(i < lb + 2 || i >= rates_total) return;

    double vol_avg = 0, mean_body = 0;
    for(int k = 1; k <= lb; k++)
    {
        vol_avg   += (double)tick_volume[i-k];
        mean_body += MathAbs(close[i-k] - open[i-k]);
    }
    vol_avg   /= lb;
    mean_body /= lb;

    double body  = MathAbs(close[i] - open[i]);
    double ws    = low[i-1],  wr = high[i-1];
    for(int k = 2; k <= lb; k++) { ws = MathMin(ws, low[i-k]); wr = MathMax(wr, high[i-k]); }

    bool is_climax = (tick_volume[i] > vol_avg * InpVolMult);
    bool big_body  = (body > mean_body * 1.5);
    bool small_body= (body < mean_body * 0.6);
    bool low_vol   = (tick_volume[i] < vol_avg * 0.7);

    bool isSC  = is_climax && (close[i]<open[i]) && (low[i]<=ws*1.001) && big_body;
    bool isBC  = is_climax && (close[i]>open[i]) && (high[i]>=wr*0.999) && big_body;
    bool isSpr = (low[i]<ws) && (close[i]>ws) && (close[i]>open[i]) && (tick_volume[i]<vol_avg);
    bool isUT  = (high[i]>wr) && (close[i]<wr) && (close[i]<open[i]) && (tick_volume[i]<vol_avg);
    bool isSOS = (close[i]>open[i]) && big_body && (tick_volume[i]>vol_avg*0.8) && (close[i]>wr);
    bool isSOW = (close[i]<open[i]) && big_body && (tick_volume[i]>vol_avg*0.8) && (close[i]<ws);

    // LPS / LPSY : nécessite connaissance des événements précédents
    bool prevSOS = false, prevSOW = false;
    for(int k = 1; k <= lb*2 && i-k >= 0; k++)
    {
        double bk  = MathAbs(close[i-k] - open[i-k]);
        double wsa = low[i-k-1], wra = high[i-k-1];
        for(int j=2;j<=lb && i-k-j>=0;j++) { wsa=MathMin(wsa,low[i-k-j]); wra=MathMax(wra,high[i-k-j]); }
        double va = 0;
        for(int j=1;j<=lb && i-k-j>=0;j++) va += (double)tick_volume[i-k-j];
        va /= lb;
        double mba = 0;
        for(int j=1;j<=lb && i-k-j>=0;j++) mba += MathAbs(close[i-k-j]-open[i-k-j]);
        mba /= lb;
        if((close[i-k]>open[i-k]) && (bk>mba*1.5) && ((double)tick_volume[i-k]>va*0.8) && (close[i-k]>wra)) { prevSOS=true; break; }
        if((close[i-k]<open[i-k]) && (bk>mba*1.5) && ((double)tick_volume[i-k]>va*0.8) && (close[i-k]<wsa)) { prevSOW=true; break; }
    }
    bool isLPS  = prevSOS && (close[i]>open[i]) && small_body && low_vol;
    bool isLPSY = prevSOW && (close[i]<open[i]) && small_body && low_vol;

    // AR (Automatic Rally après SC / Reaction après BC)
    bool afterSC = false, afterBC = false;
    for(int k=1;k<=lb && i-k>=0;k++)
    {
        double bk=MathAbs(close[i-k]-open[i-k]);
        double wsa=low[i-k-1], wra=high[i-k-1];
        for(int j=2;j<=lb && i-k-j>=0;j++){ wsa=MathMin(wsa,low[i-k-j]); wra=MathMax(wra,high[i-k-j]); }
        double va=0;
        for(int j=1;j<=lb && i-k-j>=0;j++) va+=(double)tick_volume[i-k-j];
        va/=lb;
        double mba=0;
        for(int j=1;j<=lb && i-k-j>=0;j++) mba+=MathAbs(close[i-k-j]-open[i-k-j]);
        mba/=lb;
        bool sc_k = ((double)tick_volume[i-k]>va*InpVolMult) && (close[i-k]<open[i-k]) && (low[i-k]<=wsa*1.001) && (bk>mba*1.5);
        bool bc_k = ((double)tick_volume[i-k]>va*InpVolMult) && (close[i-k]>open[i-k]) && (high[i-k]>=wra*0.999) && (bk>mba*1.5);
        if(sc_k){ afterSC=true; break; }
        if(bc_k){ afterBC=true; break; }
    }
    bool isAR_bull = afterSC && (close[i]>open[i]) && (body>mean_body) && (close[i-1]<=open[i-1]);
    bool isAR_bear = afterBC && (close[i]<open[i]) && (body>mean_body) && (close[i-1]>=open[i-1]);

    if(isSC)     WyckLabel(i, time[i], low[i],  "SC",    InpClimaxColor, true);
    if(isBC)     WyckLabel(i, time[i], high[i], "BC",    InpClimaxColor, false);
    if(isSpr)    WyckLabel(i, time[i], low[i],  "Spr",   InpSpringColor, true);
    if(isUT)     WyckLabel(i, time[i], high[i], "UT",    InpUTColor,     false);
    if(isSOS)    WyckLabel(i, time[i], low[i],  "SOS",   InpSpringColor, true);
    if(isSOW)    WyckLabel(i, time[i], high[i], "SOW",   InpUTColor,     false);
    if(isLPS)    WyckLabel(i, time[i], low[i],  "LPS",   InpSpringColor, true);
    if(isLPSY)   WyckLabel(i, time[i], high[i], "LPSY",  InpUTColor,     false);
    if(isAR_bull)WyckLabel(i, time[i], high[i], "AR",    InpSpringColor, false);
    if(isAR_bear)WyckLabel(i, time[i], low[i],  "AR",    InpUTColor,     true);
}

void WyckLabel(int idx, datetime t, double price, string txt, color clr, bool below)
{
    string name = "DV_WY_" + txt + "_" + IntegerToString(idx);
    if(ObjectFind(0, name) >= 0) return;
    ObjectCreate(0, name, OBJ_TEXT, 0, t, price);
    ObjectSetString (0, name, OBJPROP_TEXT,     txt);
    ObjectSetInteger(0, name, OBJPROP_COLOR,    clr);
    ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
    ObjectSetInteger(0, name, OBJPROP_ANCHOR,   below ? ANCHOR_TOP : ANCHOR_BOTTOM);
    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//======================================================================
//  RSI CALC + SIGNALS + DIVERGENCES
//======================================================================
void CalcRSI(int rates_total, const double &close[])
{
    ArrayResize(g_rsi, rates_total);
    ArraySetAsSeries(g_rsi, false);
    int len = InpRSILen;
    if(rates_total < len + 2) return;

    double gain = 0, loss = 0;
    for(int k = 1; k <= len; k++)
    {
        double d = close[k] - close[k-1];
        if(d > 0) gain += d; else loss -= d;
    }
    gain /= len; loss /= len;
    g_rsi[len] = (loss == 0) ? 100.0 : 100.0 - 100.0 / (1.0 + gain / loss);

    for(int i = len + 1; i < rates_total; i++)
    {
        double d = close[i] - close[i-1];
        double g = (d > 0) ? d : 0.0;
        double l = (d < 0) ? -d : 0.0;
        gain = (gain * (len - 1) + g) / len;
        loss = (loss * (len - 1) + l) / len;
        g_rsi[i] = (loss == 0) ? 100.0 : 100.0 - 100.0 / (1.0 + gain / loss);
    }
}

void DrawRSISignals(int i, const datetime &time[],
                    const double &high[], const double &low[])
{
    if(i < InpRSILen + 1) return;
    bool is_ob   = g_rsi[i] >= InpRSIOB;
    bool was_ob  = g_rsi[i-1] >= InpRSIOB;
    bool is_os   = g_rsi[i] <= InpRSIOS;
    bool was_os  = g_rsi[i-1] <= InpRSIOS;

    // Entrée en zone OB
    if(is_ob && !was_ob)
    {
        string name = "DV_RSI_OB_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_ARROW, 0, time[i], high[i]);
            ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 234);
            ObjectSetInteger(0, name, OBJPROP_COLOR,     InpRSIOBColor);
            ObjectSetInteger(0, name, OBJPROP_WIDTH,     1);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        }
    }
    // Entrée en zone OS
    if(is_os && !was_os)
    {
        string name = "DV_RSI_OS_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_ARROW, 0, time[i], low[i]);
            ObjectSetInteger(0, name, OBJPROP_ARROWCODE, 233);
            ObjectSetInteger(0, name, OBJPROP_COLOR,     InpRSIOSColor);
            ObjectSetInteger(0, name, OBJPROP_WIDTH,     1);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        }
    }
}

void DrawDivergences(int i, int rates_total,
                     const datetime &time[],
                     const double &high[], const double &low[])
{
    int dlen = InpDivLen;
    if(i < dlen * 2 + 2 || i >= rates_total - dlen) return;

    // Pivot high RSI et prix
    bool rsi_ph = true, prc_ph = true;
    bool rsi_pl = true, prc_pl = true;
    for(int k = 1; k <= dlen; k++)
    {
        if(g_rsi[i-k] >= g_rsi[i] || g_rsi[i+k] > g_rsi[i]) { rsi_ph = false; }
        if(g_rsi[i-k] <= g_rsi[i] || g_rsi[i+k] < g_rsi[i]) { rsi_pl = false; }
        if(high[i-k]  >= high[i]  || high[i+k]  > high[i])   { prc_ph = false; }
        if(low[i-k]   <= low[i]   || low[i+k]   < low[i])    { prc_pl = false; }
    }

    // Bearish divergence : prix higher high, RSI lower high
    if(rsi_ph && prc_ph)
    {
        // Chercher pivot précédent
        for(int j = i - dlen - 1; j >= dlen; j--)
        {
            bool ph2 = true;
            for(int k = 1; k <= dlen; k++)
                if(g_rsi[j-k] >= g_rsi[j] || g_rsi[j+k] > g_rsi[j]) { ph2 = false; break; }
            if(!ph2) continue;

            if(high[i] > high[j] && g_rsi[i] < g_rsi[j])
            {
                string name = "DV_DIV_BR_" + IntegerToString(i);
                if(ObjectFind(0, name) < 0)
                {
                    ObjectCreate(0, name, OBJ_TEXT, 0, time[i], high[i]);
                    ObjectSetString (0, name, OBJPROP_TEXT,     "D▼");
                    ObjectSetInteger(0, name, OBJPROP_COLOR,    InpRSIOBColor);
                    ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
                    ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_BOTTOM);
                    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                }
            }
            break;
        }
    }

    // Bullish divergence : prix lower low, RSI higher low
    if(rsi_pl && prc_pl)
    {
        for(int j = i - dlen - 1; j >= dlen; j--)
        {
            bool pl2 = true;
            for(int k = 1; k <= dlen; k++)
                if(g_rsi[j-k] <= g_rsi[j] || g_rsi[j+k] < g_rsi[j]) { pl2 = false; break; }
            if(!pl2) continue;

            if(low[i] < low[j] && g_rsi[i] > g_rsi[j])
            {
                string name = "DV_DIV_BL_" + IntegerToString(i);
                if(ObjectFind(0, name) < 0)
                {
                    ObjectCreate(0, name, OBJ_TEXT, 0, time[i], low[i]);
                    ObjectSetString (0, name, OBJPROP_TEXT,     "D▲");
                    ObjectSetInteger(0, name, OBJPROP_COLOR,    InpRSIOSColor);
                    ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
                    ObjectSetInteger(0, name, OBJPROP_ANCHOR,   ANCHOR_TOP);
                    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                }
            }
            break;
        }
    }
}

//======================================================================
//  FIBONACCI  (swing auto)
//======================================================================
void DrawFibonacci(int rates_total, const datetime &time[],
                   const double &high[], const double &low[])
{
    int lb = InpFibSwingLen;
    if(rates_total < lb * 2 + 2) return;

    int   sh_idx = lb; double sh_val = high[lb];
    int   sl_idx = lb; double sl_val = low[lb];
    for(int k = 1; k < lb * 2; k++)
    {
        if(high[k] > sh_val){ sh_val = high[k]; sh_idx = k; }
        if(low[k]  < sl_val){ sl_val = low[k];  sl_idx = k; }
    }

    bool bull_trend = (sh_idx > sl_idx);
    datetime x1 = bull_trend ? time[sh_idx] : time[sl_idx];
    double   y1 = bull_trend ? sh_val : sl_val;
    datetime x2 = bull_trend ? time[sl_idx] : time[sh_idx];
    double   y2 = bull_trend ? sl_val : sh_val;
    double range = y2 - y1;
    if(MathAbs(range) < _Point * 10) return;

    double fibs[] = {0.0,0.236,0.382,0.500,0.618,0.710,0.786,0.810,0.950,1.000,1.618};
    string labs[] = {"0.000","0.236","0.382","0.500","0.618","0.710","0.786","0.810","0.950","1.000","1.618"};
    color  cols[] = {clrSilver,clrOrangeRed,clrGold,clrGreen,clrGold,clrDeepSkyBlue,clrLime,clrOrchid,clrWhite,clrSilver,clrGold};

    datetime x_end = time[0] + (datetime)(g_tf_sec * 50);

    for(int f = 0; f < ArraySize(fibs); f++)
    {
        double price = y1 + range * fibs[f];
        string lname = "DV_FIB_L_" + IntegerToString(f);
        string tname = "DV_FIB_T_" + IntegerToString(f);

        if(ObjectFind(0, lname) < 0) ObjectCreate(0, lname, OBJ_TREND, 0, x2, price, x_end, price);
        ObjectSetDouble (0, lname, OBJPROP_PRICE, 0, price);
        ObjectSetDouble (0, lname, OBJPROP_PRICE, 1, price);
        ObjectSetInteger(0, lname, OBJPROP_TIME,  0, x2);
        ObjectSetInteger(0, lname, OBJPROP_TIME,  1, x_end);
        ObjectSetInteger(0, lname, OBJPROP_COLOR,      cols[f]);
        ObjectSetInteger(0, lname, OBJPROP_STYLE,      STYLE_DOT);
        ObjectSetInteger(0, lname, OBJPROP_RAY_RIGHT,  true);
        ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);

        if(ObjectFind(0, tname) < 0) ObjectCreate(0, tname, OBJ_TEXT, 0, x_end, price);
        ObjectSetString (0, tname, OBJPROP_TEXT,     labs[f] + "  " + DoubleToString(price, _Digits));
        ObjectSetInteger(0, tname, OBJPROP_COLOR,    cols[f]);
        ObjectSetInteger(0, tname, OBJPROP_FONTSIZE, 7);
        ObjectSetInteger(0, tname, OBJPROP_SELECTABLE, false);
    }

    // Zone OTE
    double ote_top = y1 + range * (bull_trend ? 0.786 : 0.382);
    double ote_btm = y1 + range * (bull_trend ? 0.618 : 0.236);
    if(ote_top < ote_btm){ double tmp=ote_top; ote_top=ote_btm; ote_btm=tmp; }
    color ote_clr  = bull_trend ? InpOTEBullColor : InpOTEBearColor;
    string bull_ote = "DV_FIB_OTE";
    if(ObjectFind(0, bull_ote) < 0)
        ObjectCreate(0, bull_ote, OBJ_RECTANGLE, 0, x2, ote_top, x_end, ote_btm);
    ObjectSetDouble (0, bull_ote, OBJPROP_PRICE, 0, ote_top);
    ObjectSetDouble (0, bull_ote, OBJPROP_PRICE, 1, ote_btm);
    ObjectSetInteger(0, bull_ote, OBJPROP_TIME,  0, x2);
    ObjectSetInteger(0, bull_ote, OBJPROP_TIME,  1, x_end);
    ObjectSetInteger(0, bull_ote, OBJPROP_COLOR,   ote_clr);
    ObjectSetInteger(0, bull_ote, OBJPROP_BGCOLOR, BlendWithWhite(ote_clr, 215));
    ObjectSetInteger(0, bull_ote, OBJPROP_FILL,    true);
    ObjectSetInteger(0, bull_ote, OBJPROP_BACK,    true);
    ObjectSetInteger(0, bull_ote, OBJPROP_SELECTABLE, false);
}

//======================================================================
//  PANNEAU SCORE COMPLET
//======================================================================
void DrawScorePanel(int rates_total,
                    const datetime &time[],
                    const double &open[], const double &high[],
                    const double &low[], const double &close[],
                    const long &tick_volume[])
{
    if(rates_total < InpWyckLookback + 5) return;
    int lb = InpWyckLookback, i = rates_total - 2;

    double vol_avg = 0, mean_body = 0;
    for(int k=1;k<=lb;k++) { vol_avg+=tick_volume[i-k]; mean_body+=MathAbs(close[i-k]-open[i-k]); }
    vol_avg /= lb; mean_body /= lb;

    double body = MathAbs(close[i]-open[i]);
    double ws = low[i-1], wr = high[i-1];
    for(int k=2;k<=lb;k++) { ws=MathMin(ws,low[i-k]); wr=MathMax(wr,high[i-k]); }

    bool is_climax = (tick_volume[i] > vol_avg * InpVolMult);
    bool big_body  = (body > mean_body * 1.5);
    bool isSC  = is_climax && (close[i]<open[i]) && (low[i]<=ws*1.001) && big_body;
    bool isBC  = is_climax && (close[i]>open[i]) && (high[i]>=wr*0.999) && big_body;
    bool isSpr = (low[i]<ws) && (close[i]>ws) && (close[i]>open[i]) && (tick_volume[i]<vol_avg);
    bool isUT  = (high[i]>wr) && (close[i]<wr) && (close[i]<open[i]) && (tick_volume[i]<vol_avg);
    bool isSOS = (close[i]>open[i]) && big_body && (tick_volume[i]>vol_avg*0.8) && (close[i]>wr);
    bool isSOW = (close[i]<open[i]) && big_body && (tick_volume[i]>vol_avg*0.8) && (close[i]<ws);

    int score = 0;
    if(isSC)  score += 3; if(isSpr) score += 4; if(isSOS) score += 3;
    if(isBC)  score -= 3; if(isUT)  score -= 4; if(isSOW) score -= 3;

    // Confluence FVG : FVG bullish présent sous le prix ?
    bool fvg_bull_near = ObjectFind(0, "DV_FVG_B_" + IntegerToString(i))   >= 0 ||
                         ObjectFind(0, "DV_FVG_B_" + IntegerToString(i-1)) >= 0;
    bool fvg_bear_near = ObjectFind(0, "DV_FVG_S_" + IntegerToString(i))   >= 0 ||
                         ObjectFind(0, "DV_FVG_S_" + IntegerToString(i-1)) >= 0;
    if(fvg_bull_near) score++;
    if(fvg_bear_near) score--;

    // Confluence RSI
    double rsi_cur = (ArraySize(g_rsi) > i) ? g_rsi[i] : 50.0;
    if(rsi_cur <= InpRSIOS) score += 2;
    if(rsi_cur >= InpRSIOB) score -= 2;

    // Session NY ?
    MqlDateTime dt; TimeToStruct(time[i], dt);
    int est_h = (dt.hour-5+24)%24;
    int cur_m = est_h*60+dt.min;
    bool in_ny = (cur_m >= InpNYStartHour*60+InpNYStartMin && cur_m < InpNYEndHour*60+InpNYEndMin);
    if(in_ny && score != 0) score += (score>0 ? 1 : -1);

    // NWOG actif ?
    bool nwog_active = false;
    for(int k=0; k<10; k++)
        if(ObjectFind(0, "DV_NWOG_" + IntegerToString(i-k)) >= 0) { nwog_active = true; break; }
    if(nwog_active) score += (score>=0 ? 1 : -1);

    // Bias
    string bias = (score >= 4) ? "BULL FORT" : (score >= 2) ? "BULL" :
                  (score <= -4) ? "BEAR FORT" : (score <= -2) ? "BEAR" : "NEUTRE";
    color panel_color = (score > 0) ? InpSpringColor : (score < 0) ? InpUTColor : clrGray;

    string wyck_event = isSC ? "SC" : isBC ? "BC" : isSpr ? "Spring" :
                        isUT ? "UT" : isSOS ? "SOS" : isSOW ? "SOW" : "—";

    // RSI label
    string rsi_str = "RSI " + DoubleToString(rsi_cur, 1) +
                     (rsi_cur >= InpRSIOB ? " [OB]" : rsi_cur <= InpRSIOS ? " [OS]" : "");

    string lines[];
    ArrayResize(lines, 10);
    lines[0] = "══ DreVM v2.0 ════════";
    lines[1] = "Session NY  : " + (in_ny ? "✔ ACTIVE" : "✘ OFF");
    lines[2] = "NWOG actif  : " + (nwog_active ? "OUI" : "NON");
    lines[3] = "Wyckoff     : " + wyck_event;
    lines[4] = rsi_str;
    lines[5] = "FVG bull    : " + (fvg_bull_near ? "PRESENT" : "—");
    lines[6] = "FVG bear    : " + (fvg_bear_near ? "PRESENT" : "—");
    lines[7] = "Score       : " + (score>0 ? "+" : "") + IntegerToString(score);
    lines[8] = "Biais       : " + bias;
    lines[9] = "ATR(14)     : " + DoubleToString(g_atr, _Digits);

    for(int row = 0; row < ArraySize(lines); row++)
    {
        string oname = "DV_PNL_" + IntegerToString(row);
        if(ObjectFind(0, oname) < 0) ObjectCreate(0, oname, OBJ_LABEL, 0, 0, 0);
        ObjectSetInteger(0, oname, OBJPROP_CORNER,    CORNER_LEFT_UPPER);
        ObjectSetInteger(0, oname, OBJPROP_XDISTANCE, InpPanelX);
        ObjectSetInteger(0, oname, OBJPROP_YDISTANCE, InpPanelY + row * 17);
        ObjectSetString (0, oname, OBJPROP_TEXT,      lines[row]);
        color txt_col = (row == 0) ? clrGold :
                        (row == 8) ? panel_color :
                        (row == 4) ? (rsi_cur>=InpRSIOB ? InpRSIOBColor : rsi_cur<=InpRSIOS ? InpRSIOSColor : clrSilver) :
                        clrSilver;
        ObjectSetInteger(0, oname, OBJPROP_COLOR,    txt_col);
        ObjectSetInteger(0, oname, OBJPROP_FONTSIZE, 9);
        ObjectSetInteger(0, oname, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, oname, OBJPROP_HIDDEN,   true);
    }
}

//======================================================================
//  UTILITAIRES
//======================================================================
color BlendWithWhite(color base, uchar alpha)
{
    int r = (int)(base >> 16 & 0xFF);
    int g = (int)(base >> 8  & 0xFF);
    int b = (int)(base       & 0xFF);
    double t = 1.0 - alpha / 255.0;
    r = (int)(r + (255-r)*t); g = (int)(g + (255-g)*t); b = (int)(b + (255-b)*t);
    return (color)((r << 16)|(g << 8)|b);
}

double CalcATR(int period, int bar_idx)
{
    double sum = 0;
    for(int k = 0; k < period; k++)
    {
        double h = iHigh(_Symbol, _Period, bar_idx - k);
        double l = iLow (_Symbol, _Period, bar_idx - k);
        double c = iClose(_Symbol, _Period, bar_idx - k + 1);
        sum += MathMax(h-l, MathMax(MathAbs(h-c), MathAbs(l-c)));
    }
    return sum / period;
}
//+------------------------------------------------------------------+
