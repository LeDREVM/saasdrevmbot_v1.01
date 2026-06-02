//+------------------------------------------------------------------+
//|  NY Session · Wyckoff Scoring · FVG · Order Blocks · Fibonacci  |
//|  Compatible MT5 — indicator overlay                              |
//+------------------------------------------------------------------+
#property copyright   "DreVM Trading"
#property version     "1.00"
#property indicator_chart_window
#property indicator_plots 0

//=== Inputs ===========================================================

// --- NY Session -------------------------------------------------------
input group            "── NY Session ──"
input bool   InpShowNY        = true;
input color  InpNYColor       = C'255,93,0';          // orange fond
input int    InpNYStartHour   = 9;                    // heure NY (EST)
input int    InpNYStartMin    = 30;
input int    InpNYEndHour     = 16;
input int    InpNYEndMin      = 0;

// --- Order Blocks -----------------------------------------------------
input group            "── Order Blocks ──"
input bool   InpShowOB        = true;
input int    InpOBLookback    = 10;
input color  InpBullOBColor   = C'62,137,250';        // bleu
input color  InpBearOBColor   = C'255,49,49';         // rouge
input bool   InpShowOBLabel   = true;

// --- Fair Value Gaps --------------------------------------------------
input group            "── Fair Value Gaps ──"
input bool   InpShowFVG       = true;
input int    InpMaxFVG        = 3;                    // nb max visibles
input color  InpBullFVGColor  = C'0,230,118';         // vert
input color  InpBearFVGColor  = C'255,82,82';         // rouge

// --- Wyckoff Scoring --------------------------------------------------
input group            "── Wyckoff ──"
input bool   InpShowWyck      = true;
input int    InpWyckLookback  = 20;
input double InpVolMult       = 2.0;                  // multiplicateur volume climax
input color  InpClimaxColor   = C'255,152,0';         // orange
input color  InpSpringColor   = C'0,230,118';         // vert
input color  InpUTColor       = C'255,49,49';         // rouge

// --- Fibonacci --------------------------------------------------------
input group            "── Fibonacci ──"
input bool   InpShowFib       = true;
input bool   InpFibAutoSwing  = true;                 // swing automatique
input int    InpFibSwingLen   = 20;                   // lookback swing
input color  InpFibColor      = clrSilver;
input color  InpOTEBullColor  = C'0,230,118';
input color  InpOTEBearColor  = C'255,82,82';

// --- Score Panel ------------------------------------------------------
input group            "── Panneau Score ──"
input bool   InpShowPanel     = true;
input int    InpPanelX        = 20;
input int    InpPanelY        = 30;

//=== Globals ==========================================================
int    g_tf_sec;          // durée barre en secondes
double g_atr;             // ATR(14) courant

// Compteurs d'objets pour nettoyage
int    g_fvg_bull_count = 0;
int    g_fvg_bear_count = 0;
int    g_ob_bull_count  = 0;
int    g_ob_bear_count  = 0;

// Wyckoff score (reset chaque calcul)
int    g_wyckoff_score  = 0;

//======================================================================
int OnInit()
{
    g_tf_sec = PeriodSeconds();
    ChartSetInteger(0, CHART_EVENT_MOUSE_MOVE, true);
    return INIT_SUCCEEDED;
}

//======================================================================
void OnDeinit(const int reason)
{
    ObjectsDeleteAll(0, "DV_");
}

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
    if(rates_total < InpWyckLookback + 5) return 0;

    // Recalculer seulement si une nouvelle bougie fermée ou premier appel
    bool full_recalc = (prev_calculated == 0);
    bool new_bar     = (prev_calculated < rates_total);

    if(!full_recalc && !new_bar) return rates_total;

    // --- ATR approximation ---
    g_atr = iATR(_Symbol, _Period, 14, rates_total - 2);

    // --- Effacer les anciens objets si recalcul complet ---
    if(full_recalc) ObjectsDeleteAll(0, "DV_");

    int limit = full_recalc ? rates_total - 1 : rates_total - 2;
    int start = full_recalc ? InpWyckLookback + 3 : MathMax(InpWyckLookback + 3, prev_calculated - 1);

    // --- Boucle principale ---
    for(int i = start; i <= limit; i++)
    {
        datetime t = time[i];

        // NY Session highlight
        if(InpShowNY) DrawNYSession(t, i, time);

        // FVG
        if(InpShowFVG) DetectFVG(i, time, open, high, low, close);

        // Order Blocks
        if(InpShowOB) DetectOB(i, rates_total, time, open, high, low, close);

        // Wyckoff events
        if(InpShowWyck) DetectWyckoff(i, rates_total, time, open, high, low, close, tick_volume);
    }

    // --- Fibonacci sur dernier swing ---
    if(InpShowFib) DrawFibonacci(rates_total, time, high, low);

    // --- Score panel ---
    if(InpShowPanel) DrawScorePanel(rates_total, time, open, high, low, close, tick_volume);

    return rates_total;
}

//======================================================================
//  NY SESSION HIGHLIGHT
//======================================================================
void DrawNYSession(datetime t, int i, const datetime &time[])
{
    MqlDateTime dt;
    TimeToStruct(t, dt);
    // Convertir UTC → EST (UTC-5 hors DST, UTC-4 DST — simplifié UTC-5)
    int est_hour = (dt.hour - 5 + 24) % 24;
    int est_min  = dt.min;

    bool in_ny = false;
    int start_minutes = InpNYStartHour * 60 + InpNYStartMin;
    int end_minutes   = InpNYEndHour   * 60 + InpNYEndMin;
    int cur_minutes   = est_hour * 60 + est_min;

    if(end_minutes > start_minutes)
        in_ny = (cur_minutes >= start_minutes && cur_minutes < end_minutes);
    else
        in_ny = (cur_minutes >= start_minutes || cur_minutes < end_minutes);

    if(!in_ny) return;

    string name = "DV_NY_" + IntegerToString(i);
    if(ObjectFind(0, name) < 0)
    {
        ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                     time[i], 0,
                     time[i] + g_tf_sec, 0);
        ObjectSetInteger(0, name, OBJPROP_COLOR,    InpNYColor);
        ObjectSetInteger(0, name, OBJPROP_BGCOLOR,  InpNYColor);
        ObjectSetInteger(0, name, OBJPROP_FILL,     true);
        ObjectSetInteger(0, name, OBJPROP_BACK,     true);
        ObjectSetInteger(0, name, OBJPROP_WIDTH,    1);
        ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
        // Étirer sur toute la hauteur via prix extrêmes
        double chart_max = ChartGetDouble(0, CHART_PRICE_MAX);
        double chart_min = ChartGetDouble(0, CHART_PRICE_MIN);
        ObjectSetDouble(0, name, OBJPROP_PRICE, 0, chart_max);
        ObjectSetDouble(0, name, OBJPROP_PRICE, 1, chart_min);
    }
}

//======================================================================
//  FAIR VALUE GAPS
//======================================================================
void DetectFVG(int i, const datetime &time[],
               const double &open[], const double &high[],
               const double &low[], const double &close[])
{
    if(i < 2) return;

    // FVG bullish : gap entre high[i-2] et low[i]
    if(low[i] > high[i-2])
    {
        string name = "DV_FVG_B_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                         time[i-2], high[i-2],
                         time[i] + (datetime)(g_tf_sec * 20), low[i]);
            ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBullFVGColor);
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, ColorWithAlpha(InpBullFVGColor, 210));
            ObjectSetInteger(0, name, OBJPROP_FILL,    true);
            ObjectSetInteger(0, name, OBJPROP_BACK,    true);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            if(InpShowOBLabel)
            {
                string lname = name + "_L";
                ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-1], low[i]);
                ObjectSetString(0, lname, OBJPROP_TEXT, "FVG▲");
                ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBullFVGColor);
                ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
            }
        }
    }

    // FVG bearish : gap entre low[i-2] et high[i]
    if(high[i] < low[i-2])
    {
        string name = "DV_FVG_S_" + IntegerToString(i);
        if(ObjectFind(0, name) < 0)
        {
            ObjectCreate(0, name, OBJ_RECTANGLE, 0,
                         time[i-2], low[i-2],
                         time[i] + (datetime)(g_tf_sec * 20), high[i]);
            ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBearFVGColor);
            ObjectSetInteger(0, name, OBJPROP_BGCOLOR, ColorWithAlpha(InpBearFVGColor, 210));
            ObjectSetInteger(0, name, OBJPROP_FILL,    true);
            ObjectSetInteger(0, name, OBJPROP_BACK,    true);
            ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
            if(InpShowOBLabel)
            {
                string lname = name + "_L";
                ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-1], high[i]);
                ObjectSetString(0, lname, OBJPROP_TEXT, "FVG▼");
                ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBearFVGColor);
                ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
            }
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

    // Bullish OB : dernière bougie baissière avant un mouvement haussier
    // Détection : close[i] rompt le plus haut des lb bougies précédentes
    double prev_high = high[i - 1];
    for(int k = 2; k <= lb; k++)
        prev_high = MathMax(prev_high, high[i - k]);

    if(close[i] > prev_high)
    {
        // Chercher la dernière bougie baissière avant i
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
                                 time[i] + (datetime)(g_tf_sec * 30), ob_btm);
                    ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBullOBColor);
                    ObjectSetInteger(0, name, OBJPROP_BGCOLOR, ColorWithAlpha(InpBullOBColor, 200));
                    ObjectSetInteger(0, name, OBJPROP_FILL,    true);
                    ObjectSetInteger(0, name, OBJPROP_BACK,    true);
                    ObjectSetInteger(0, name, OBJPROP_WIDTH,   1);
                    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                    if(InpShowOBLabel)
                    {
                        string lname = name + "_L";
                        ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-k], ob_btm);
                        ObjectSetString(0, lname, OBJPROP_TEXT, "+OB");
                        ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBullOBColor);
                        ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                    }
                }
                break;
            }
        }
    }

    // Bearish OB : dernière bougie haussière avant un mouvement baissier
    double prev_low = low[i - 1];
    for(int k = 2; k <= lb; k++)
        prev_low = MathMin(prev_low, low[i - k]);

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
                                 time[i] + (datetime)(g_tf_sec * 30), ob_btm);
                    ObjectSetInteger(0, name, OBJPROP_COLOR,   InpBearOBColor);
                    ObjectSetInteger(0, name, OBJPROP_BGCOLOR, ColorWithAlpha(InpBearOBColor, 200));
                    ObjectSetInteger(0, name, OBJPROP_FILL,    true);
                    ObjectSetInteger(0, name, OBJPROP_BACK,    true);
                    ObjectSetInteger(0, name, OBJPROP_WIDTH,   1);
                    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
                    if(InpShowOBLabel)
                    {
                        string lname = name + "_L";
                        ObjectCreate(0, lname, OBJ_TEXT, 0, time[i-k], ob_top);
                        ObjectSetString(0, lname, OBJPROP_TEXT, "-OB");
                        ObjectSetInteger(0, lname, OBJPROP_COLOR,    InpBearOBColor);
                        ObjectSetInteger(0, lname, OBJPROP_FONTSIZE, 7);
                    }
                }
                break;
            }
        }
    }
}

//======================================================================
//  WYCKOFF DETECTION + SCORE
//======================================================================
void DetectWyckoff(int i, int rates_total,
                   const datetime &time[],
                   const double &open[], const double &high[],
                   const double &low[], const double &close[],
                   const long &tick_volume[])
{
    int lb = InpWyckLookback;
    if(i < lb + 1 || i >= rates_total) return;

    double vol_avg = 0;
    for(int k = 1; k <= lb; k++) vol_avg += (double)tick_volume[i-k];
    vol_avg /= lb;

    double body      = MathAbs(close[i] - open[i]);
    double mean_body = 0;
    for(int k = 1; k <= lb; k++) mean_body += MathAbs(close[i-k] - open[i-k]);
    mean_body /= lb;

    // Support / résistance sur lb bougies précédentes
    double wyck_support = low[i-1];
    double wyck_resist  = high[i-1];
    for(int k = 2; k <= lb; k++)
    {
        wyck_support = MathMin(wyck_support, low[i-k]);
        wyck_resist  = MathMax(wyck_resist,  high[i-k]);
    }

    bool is_climax = (tick_volume[i] > vol_avg * InpVolMult);
    bool big_body  = (body > mean_body * 1.5);

    // Selling Climax (SC)
    bool isSC = is_climax && (close[i] < open[i]) && (low[i] <= wyck_support * 1.001) && big_body;
    // Buying Climax (BC)
    bool isBC = is_climax && (close[i] > open[i]) && (high[i] >= wyck_resist * 0.999) && big_body;
    // Spring
    bool isSpring = (low[i] < wyck_support) && (close[i] > wyck_support) && (close[i] > open[i]) && (tick_volume[i] < vol_avg);
    // Upthrust (UT)
    bool isUT = (high[i] > wyck_resist) && (close[i] < wyck_resist) && (close[i] < open[i]) && (tick_volume[i] < vol_avg);
    // Sign of Strength (SOS)
    bool isSOS = (close[i] > open[i]) && big_body && (tick_volume[i] > vol_avg * 0.8) && (close[i] > wyck_resist);
    // Sign of Weakness (SOW)
    bool isSOW = (close[i] < open[i]) && big_body && (tick_volume[i] > vol_avg * 0.8) && (close[i] < wyck_support);

    // Draw labels
    if(isSC)    WyckLabel(i, time, low,  "SC",  InpClimaxColor, true);
    if(isBC)    WyckLabel(i, time, high, "BC",  InpClimaxColor, false);
    if(isSpring)WyckLabel(i, time, low,  "Spr", InpSpringColor, true);
    if(isUT)    WyckLabel(i, time, high, "UT",  InpUTColor,     false);
    if(isSOS)   WyckLabel(i, time, low,  "SOS", InpSpringColor, true);
    if(isSOW)   WyckLabel(i, time, high, "SOW", InpUTColor,     false);
}

void WyckLabel(int i, const datetime &time[],
               const double &price[], string txt,
               color clr, bool below)
{
    string name = "DV_WY_" + txt + "_" + IntegerToString(i);
    if(ObjectFind(0, name) >= 0) return;
    ObjectCreate(0, name, OBJ_TEXT, 0, time[i], price[i]);
    ObjectSetString (0, name, OBJPROP_TEXT,     txt);
    ObjectSetInteger(0, name, OBJPROP_COLOR,    clr);
    ObjectSetInteger(0, name, OBJPROP_FONTSIZE, 8);
    ObjectSetInteger(0, name, OBJPROP_ANCHOR,   below ? ANCHOR_TOP : ANCHOR_BOTTOM);
    ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
}

//======================================================================
//  FIBONACCI  (swing auto)
//======================================================================
void DrawFibonacci(int rates_total, const datetime &time[],
                   const double &high[], const double &low[])
{
    int lb = InpFibSwingLen;
    if(rates_total < lb * 2 + 2) return;

    // Trouver swing high et swing low sur les lb dernières bougies
    int   sh_idx = lb, sl_idx = lb;
    double sh_val = high[lb], sl_val = low[lb];
    for(int k = 1; k < lb * 2; k++)
    {
        if(high[k] > sh_val){ sh_val = high[k]; sh_idx = k; }
        if(low[k]  < sl_val){ sl_val = low[k];  sl_idx = k; }
    }

    // Déterminer direction : swing high vient avant swing low → tendance baissière
    bool bull_trend = (sh_idx > sl_idx);   // swing low récent = retracement haussier
    datetime x1, x2;
    double   y1, y2;
    if(bull_trend)
    {
        x1 = time[sh_idx]; y1 = sh_val;   // bas → haut : de swing low à swing high
        x2 = time[sl_idx]; y2 = sl_val;
    }
    else
    {
        x1 = time[sl_idx]; y1 = sl_val;
        x2 = time[sh_idx]; y2 = sh_val;
    }

    double range = y2 - y1;
    if(MathAbs(range) < _Point * 10) return;

    // Niveaux Fibonacci
    double fibs[] = {0.0, 0.236, 0.382, 0.500, 0.618, 0.710, 0.786, 0.810, 0.950, 1.000, 1.618};
    string labs[] = {"0.000","0.236","0.382","0.500","0.618","0.710","0.786","0.810","0.950","1.000","1.618"};
    color  cols[] = {clrSilver, clrOrangeRed, clrGold, clrGreen, clrGold, clrDeepSkyBlue, clrLime, clrOrchid, clrWhite, clrSilver, clrGold};

    datetime x_end = time[0] + (datetime)(g_tf_sec * 50);

    for(int f = 0; f < ArraySize(fibs); f++)
    {
        double price = y1 + range * fibs[f];
        string lname = "DV_FIB_L_" + IntegerToString(f);
        string tname = "DV_FIB_T_" + IntegerToString(f);

        if(ObjectFind(0, lname) < 0)
            ObjectCreate(0, lname, OBJ_TREND, 0, x2, price, x_end, price);
        ObjectSetInteger(0, lname, OBJPROP_COLOR,   cols[f]);
        ObjectSetInteger(0, lname, OBJPROP_WIDTH,   1);
        ObjectSetInteger(0, lname, OBJPROP_STYLE,   STYLE_DOT);
        ObjectSetInteger(0, lname, OBJPROP_RAY_RIGHT, true);
        ObjectSetDouble (0, lname, OBJPROP_PRICE, 0, price);
        ObjectSetDouble (0, lname, OBJPROP_PRICE, 1, price);
        ObjectSetInteger(0, lname, OBJPROP_TIME, 0, x2);
        ObjectSetInteger(0, lname, OBJPROP_TIME, 1, x_end);
        ObjectSetInteger(0, lname, OBJPROP_SELECTABLE, false);

        string label_txt = labs[f] + "  " + DoubleToString(price, _Digits);
        if(ObjectFind(0, tname) < 0)
            ObjectCreate(0, tname, OBJ_TEXT, 0, x_end, price);
        ObjectSetString (0, tname, OBJPROP_TEXT,     label_txt);
        ObjectSetInteger(0, tname, OBJPROP_COLOR,    cols[f]);
        ObjectSetInteger(0, tname, OBJPROP_FONTSIZE, 7);
        ObjectSetInteger(0, tname, OBJPROP_SELECTABLE, false);
    }

    // Zone OTE Bull  0.618 – 0.786
    string bull_ote = "DV_FIB_OTE_BULL";
    double ote_top  = y1 + range * (bull_trend ? 0.786 : 0.382);
    double ote_btm  = y1 + range * (bull_trend ? 0.618 : 0.236);
    if(ote_top < ote_btm){ double tmp = ote_top; ote_top = ote_btm; ote_btm = tmp; }
    if(ObjectFind(0, bull_ote) < 0)
        ObjectCreate(0, bull_ote, OBJ_RECTANGLE, 0, x2, ote_top, x_end, ote_btm);
    ObjectSetInteger(0, bull_ote, OBJPROP_COLOR,   InpOTEBullColor);
    ObjectSetInteger(0, bull_ote, OBJPROP_BGCOLOR, ColorWithAlpha(InpOTEBullColor, 220));
    ObjectSetInteger(0, bull_ote, OBJPROP_FILL,    true);
    ObjectSetInteger(0, bull_ote, OBJPROP_BACK,    true);
    ObjectSetInteger(0, bull_ote, OBJPROP_SELECTABLE, false);
}

//======================================================================
//  PANNEAU SCORE WYCKOFF + CONFLUENCE
//======================================================================
void DrawScorePanel(int rates_total,
                    const datetime &time[],
                    const double &open[], const double &high[],
                    const double &low[], const double &close[],
                    const long &tick_volume[])
{
    if(rates_total < InpWyckLookback + 5) return;

    int    lb      = InpWyckLookback;
    int    i       = rates_total - 2;   // dernière bougie fermée
    double vol_avg = 0;
    for(int k = 1; k <= lb; k++) vol_avg += (double)tick_volume[i-k];
    vol_avg /= lb;

    double body      = MathAbs(close[i] - open[i]);
    double mean_body = 0;
    for(int k = 1; k <= lb; k++) mean_body += MathAbs(close[i-k] - open[i-k]);
    mean_body /= lb;

    double wyck_support = low[i-1];
    double wyck_resist  = high[i-1];
    for(int k = 2; k <= lb; k++)
    {
        wyck_support = MathMin(wyck_support, low[i-k]);
        wyck_resist  = MathMax(wyck_resist,  high[i-k]);
    }

    bool is_climax = (tick_volume[i] > vol_avg * InpVolMult);
    bool big_body  = (body > mean_body * 1.5);

    bool isSC     = is_climax && (close[i] < open[i]) && (low[i]  <= wyck_support * 1.001) && big_body;
    bool isBC     = is_climax && (close[i] > open[i]) && (high[i] >= wyck_resist  * 0.999) && big_body;
    bool isSpring = (low[i] < wyck_support) && (close[i] > wyck_support) && (close[i] > open[i]) && (tick_volume[i] < vol_avg);
    bool isUT     = (high[i] > wyck_resist) && (close[i] < wyck_resist) && (close[i] < open[i]) && (tick_volume[i] < vol_avg);
    bool isSOS    = (close[i] > open[i]) && big_body && (tick_volume[i] > vol_avg * 0.8) && (close[i] > wyck_resist);
    bool isSOW    = (close[i] < open[i]) && big_body && (tick_volume[i] > vol_avg * 0.8) && (close[i] < wyck_support);

    // Score bull / bear  (-10 à +10)
    int score = 0;
    if(isSC)     score += 3;   // accumulation potentielle
    if(isSpring) score += 4;
    if(isSOS)    score += 3;
    if(isBC)     score -= 3;   // distribution potentielle
    if(isUT)     score -= 4;
    if(isSOW)    score -= 3;

    // Session NY en cours ?
    MqlDateTime dt; TimeToStruct(time[i], dt);
    int est_hour    = (dt.hour - 5 + 24) % 24;
    int cur_minutes = est_hour * 60 + dt.min;
    int ny_start    = InpNYStartHour * 60 + InpNYStartMin;
    int ny_end      = InpNYEndHour   * 60 + InpNYEndMin;
    bool in_ny      = (cur_minutes >= ny_start && cur_minutes < ny_end);
    if(in_ny) score += (score > 0 ? 1 : (score < 0 ? -1 : 0)); // boost si confluence NY

    // Couleur selon score
    color panel_color = (score > 0) ? InpSpringColor : (score < 0) ? InpUTColor : clrGray;
    string bias = (score >= 3) ? "BULL" : (score <= -3) ? "BEAR" : "NEUTRE";

    // Ligne Wyckoff
    string wyck_event = "";
    if(isSC)     wyck_event = "SC";
    else if(isBC)     wyck_event = "BC";
    else if(isSpring) wyck_event = "Spring";
    else if(isUT)     wyck_event = "UT";
    else if(isSOS)    wyck_event = "SOS";
    else if(isSOW)    wyck_event = "SOW";
    else              wyck_event = "—";

    // Affichage
    string lines[];
    ArrayResize(lines, 6);
    lines[0] = "══ DreVM NY+Wyckoff ══";
    lines[1] = "Session NY : " + (in_ny ? "✔ ACTIVE" : "✘ OFF");
    lines[2] = "Wyckoff    : " + wyck_event;
    lines[3] = "Score      : " + (score > 0 ? "+" : "") + IntegerToString(score) + " / 10";
    lines[4] = "Biais      : " + bias;
    lines[5] = "ATR(14)    : " + DoubleToString(g_atr, _Digits);

    for(int row = 0; row < ArraySize(lines); row++)
    {
        string oname = "DV_PNL_" + IntegerToString(row);
        if(ObjectFind(0, oname) < 0)
            ObjectCreate(0, oname, OBJ_LABEL, 0, 0, 0);
        ObjectSetInteger(0, oname, OBJPROP_CORNER,   CORNER_LEFT_UPPER);
        ObjectSetInteger(0, oname, OBJPROP_XDISTANCE, InpPanelX);
        ObjectSetInteger(0, oname, OBJPROP_YDISTANCE, InpPanelY + row * 16);
        ObjectSetString (0, oname, OBJPROP_TEXT,     lines[row]);
        ObjectSetInteger(0, oname, OBJPROP_COLOR,    row == 0 ? clrGold : (row == 4 ? panel_color : clrSilver));
        ObjectSetInteger(0, oname, OBJPROP_FONTSIZE, 9);
        ObjectSetInteger(0, oname, OBJPROP_SELECTABLE, false);
        ObjectSetInteger(0, oname, OBJPROP_HIDDEN,   true);
    }
}

//======================================================================
//  UTILITAIRES
//======================================================================

// Simule une couleur avec transparence (fond clair → mélange avec blanc)
color ColorWithAlpha(color base, uchar alpha)
{
    // alpha 0=transparent, 255=opaque  — MT5 ne supporte pas la transparence vraie
    // on renvoie juste la couleur de base légèrement éclaircie
    int r = (int)((color)(base) >> 16 & 0xFF);
    int g = (int)((color)(base) >> 8  & 0xFF);
    int b = (int)((color)(base)       & 0xFF);
    // Mélange avec blanc proportionnel
    double t = 1.0 - alpha / 255.0;
    r = (int)(r + (255 - r) * t);
    g = (int)(g + (255 - g) * t);
    b = (int)(b + (255 - b) * t);
    return (color)((r << 16) | (g << 8) | b);
}

// iATR simplifié : calcule ATR sur n bougies précédant la barre i
double iATR(string sym, ENUM_TIMEFRAMES tf, int period, int bar_idx)
{
    double sum = 0;
    for(int k = 0; k < period; k++)
    {
        double h = iHigh(sym, tf, bar_idx - k);
        double l = iLow (sym, tf, bar_idx - k);
        double c = iClose(sym, tf, bar_idx - k + 1);
        double tr = MathMax(h - l, MathMax(MathAbs(h - c), MathAbs(l - c)));
        sum += tr;
    }
    return sum / period;
}
//+------------------------------------------------------------------+
