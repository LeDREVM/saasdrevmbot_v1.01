//+------------------------------------------------------------------+
//|  DreVM_Bridge.mq5                                                |
//|  Envoie les signaux MT5 → n8n Webhook → Supabase                |
//|                                                                  |
//|  SETUP MT5 :                                                     |
//|  Outils → Options → Expert Advisors → Autoriser les requêtes    |
//|  web vers : http://2.24.14.85:5678  (VPS Hostinger — n8n Docker) |
//|  URL surchargée par l'input InpWebhookURL si besoin.            |
//+------------------------------------------------------------------+
#property copyright "DreVM Trading"
#property version   "1.00"
#property strict

//=== INPUTS ===========================================================
input group  "── Connexion n8n ──"
input string InpWebhookURL  = "http://2.24.14.85:5678/webhook/drevm"; // URL webhook n8n (VPS Hostinger)
input string InpApiKey      = "drevm-secret-key";                     // clé partagée MT5↔n8n
input int    InpTimeoutMs   = 5000;                                   // timeout HTTP ms

input group  "── Filtres Signal ──"
input int    InpMinScore    = 3;    // score minimum pour envoyer
input bool   InpSendOnBar   = true; // envoyer à chaque nouvelle bougie
input bool   InpSendEvents  = true; // envoyer événements Wyckoff/FVG

input group  "── Wyckoff params ──"
input int    InpWyckLookback = 20;
input double InpVolMult      = 2.0;

input group  "── RSI ──"
input int    InpRSILen  = 14;
input double InpRSIOB   = 70.0;
input double InpRSIOS   = 30.0;

//=== GLOBALS ==========================================================
datetime g_last_bar   = 0;
string   g_last_event = "";

//======================================================================
int OnInit()
{
    EventSetTimer(10);  // check toutes les 10s
    Print("DreVM Bridge initialisé — Webhook : ", InpWebhookURL);
    return INIT_SUCCEEDED;
}

void OnDeinit(const int reason) { EventKillTimer(); }

//======================================================================
void OnTimer()
{
    datetime current_bar = iTime(_Symbol, _Period, 0);
    if(!InpSendOnBar) return;
    if(current_bar == g_last_bar) return;
    g_last_bar = current_bar;

    SendSignal();
}

void OnTick()
{
    // Événements intra-bar si activé
    if(InpSendEvents) CheckAndSendEvents();
}

//======================================================================
//  CALCUL DU SCORE + PAYLOAD
//======================================================================
void SendSignal()
{
    int    rates_total = iBars(_Symbol, _Period);
    if(rates_total < InpWyckLookback + 5) return;

    // --- Données de prix ---
    double o  = iOpen (_Symbol, _Period, 1);
    double h  = iHigh (_Symbol, _Period, 1);
    double l  = iLow  (_Symbol, _Period, 1);
    double c  = iClose(_Symbol, _Period, 1);
    datetime t = iTime(_Symbol, _Period, 1);

    // --- Wyckoff ---
    string wyck_event = DetectWyckoffEvent();

    // --- RSI ---
    double rsi = iRSI(_Symbol, _Period, InpRSILen, PRICE_CLOSE, 1);

    // --- Score ---
    int score = CalcScore(wyck_event, rsi, c, o);
    if(MathAbs(score) < InpMinScore) return;

    string bias = (score >= 4) ? "BULL_FORT" : (score >= 2) ? "BULL" :
                  (score <= -4) ? "BEAR_FORT" : (score <= -2) ? "BEAR" : "NEUTRE";

    // --- Session ---
    MqlDateTime dt; TimeToStruct(t, dt);
    int est_h = (dt.hour - 5 + 24) % 24;
    int cur_m = est_h * 60 + dt.min;
    string session = "AUTRE";
    if(cur_m >= 570 && cur_m < 960)  session = "NY";
    else if(dt.hour >= 8 && dt.hour < 11) session = "LDN_OPEN";
    else if(dt.hour >= 15 && dt.hour < 17) session = "LDN_CLOSE";
    else if(dt.hour >= 0 && dt.hour < 4)  session = "ASIAN";

    // --- Niveaux Fibonacci ---
    double fib_618 = CalcFibLevel(rates_total, 0.618);
    double fib_786 = CalcFibLevel(rates_total, 0.786);

    // --- JSON payload ---
    string payload = BuildJSON(
        _Symbol, EnumToString(_Period),
        TimeToString(t, TIME_DATE|TIME_MINUTES),
        o, h, l, c,
        rsi, wyck_event, score, bias, session,
        fib_618, fib_786,
        (double)iVolume(_Symbol, _Period, 1)
    );

    PostToWebhook(payload, "signal");
}

//======================================================================
//  ÉVÉNEMENTS INTRA-BAR (FVG, OB cassé, etc.)
//======================================================================
void CheckAndSendEvents()
{
    // FVG bullish : low[0] > high[2]
    double h2 = iHigh(_Symbol, _Period, 2);
    double l0 = iLow (_Symbol, _Period, 0);
    double l2 = iLow (_Symbol, _Period, 2);
    double h0 = iHigh(_Symbol, _Period, 0);

    string event_tag = "";
    if(l0 > h2) event_tag = "FVG_BULL";
    else if(h0 < l2) event_tag = "FVG_BEAR";

    if(event_tag != "" && event_tag != g_last_event)
    {
        g_last_event = event_tag;
        double c = iClose(_Symbol, _Period, 0);
        string payload = "{\"type\":\"event\",\"event\":\"" + event_tag + "\","
                       + "\"symbol\":\"" + _Symbol + "\","
                       + "\"price\":" + DoubleToString(c, _Digits) + ","
                       + "\"time\":\"" + TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES) + "\","
                       + "\"api_key\":\"" + InpApiKey + "\"}";
        PostToWebhook(payload, "event");
    }
}

//======================================================================
//  WYCKOFF EVENT DETECTION
//======================================================================
string DetectWyckoffEvent()
{
    int lb = InpWyckLookback;
    double vol_avg = 0, mean_body = 0;
    for(int k = 1; k <= lb; k++)
    {
        vol_avg   += (double)iVolume(_Symbol, _Period, k);
        mean_body += MathAbs(iClose(_Symbol, _Period, k) - iOpen(_Symbol, _Period, k));
    }
    vol_avg /= lb; mean_body /= lb;

    double o = iOpen (_Symbol, _Period, 1);
    double h = iHigh (_Symbol, _Period, 1);
    double l = iLow  (_Symbol, _Period, 1);
    double c = iClose(_Symbol, _Period, 1);
    double body = MathAbs(c - o);
    double vol  = (double)iVolume(_Symbol, _Period, 1);

    double ws = iLow(_Symbol, _Period, 2), wr = iHigh(_Symbol, _Period, 2);
    for(int k = 2; k <= lb; k++)
    {
        ws = MathMin(ws, iLow (_Symbol, _Period, k));
        wr = MathMax(wr, iHigh(_Symbol, _Period, k));
    }

    bool is_climax = (vol > vol_avg * InpVolMult);
    bool big_body  = (body > mean_body * 1.5);

    if(is_climax && c < o && l <= ws * 1.001 && big_body) return "SC";
    if(is_climax && c > o && h >= wr * 0.999 && big_body) return "BC";
    if(l < ws && c > ws && c > o && vol < vol_avg)        return "Spring";
    if(h > wr && c < wr && c < o && vol < vol_avg)        return "UT";
    if(c > o && big_body && vol > vol_avg * 0.8 && c > wr) return "SOS";
    if(c < o && big_body && vol > vol_avg * 0.8 && c < ws) return "SOW";
    return "NONE";
}

//======================================================================
//  SCORE
//======================================================================
int CalcScore(string wyck, double rsi, double c, double o)
{
    int score = 0;
    if(wyck == "SC" || wyck == "Spring") score += 3;
    if(wyck == "SOS")                    score += 3;
    if(wyck == "BC" || wyck == "UT")     score -= 3;
    if(wyck == "SOW")                    score -= 3;
    if(rsi <= InpRSIOS) score += 2;
    if(rsi >= InpRSIOB) score -= 2;
    if(c > o) score += 1; else if(c < o) score -= 1;
    return score;
}

//======================================================================
//  FIBONACCI LEVEL
//======================================================================
double CalcFibLevel(int rates_total, double ratio)
{
    int lb = 20;
    if(rates_total < lb * 2) return 0;
    double sh = iHigh(_Symbol, _Period, 1), sl = iLow(_Symbol, _Period, 1);
    int shi = 1, sli = 1;
    for(int k = 2; k < lb * 2; k++)
    {
        double h = iHigh(_Symbol, _Period, k);
        double l = iLow (_Symbol, _Period, k);
        if(h > sh){ sh = h; shi = k; }
        if(l < sl){ sl = l; sli = k; }
    }
    bool bull = (shi > sli);
    double y1 = bull ? sh : sl;
    double y2 = bull ? sl : sh;
    return y1 + (y2 - y1) * ratio;
}

//======================================================================
//  CONSTRUCTION JSON
//======================================================================
string BuildJSON(string symbol, string tf, string bar_time,
                 double o, double h, double l, double c,
                 double rsi, string wyck, int score, string bias,
                 string session, double fib618, double fib786, double vol)
{
    string j = "{";
    j += "\"type\":\"signal\",";
    j += "\"api_key\":\"" + InpApiKey + "\",";
    j += "\"symbol\":\"" + symbol + "\",";
    j += "\"timeframe\":\"" + tf + "\",";
    j += "\"time\":\"" + bar_time + "\",";
    j += "\"open\":"  + DoubleToString(o, _Digits) + ",";
    j += "\"high\":"  + DoubleToString(h, _Digits) + ",";
    j += "\"low\":"   + DoubleToString(l, _Digits) + ",";
    j += "\"close\":" + DoubleToString(c, _Digits) + ",";
    j += "\"volume\":" + DoubleToString(vol, 0) + ",";
    j += "\"rsi\":"   + DoubleToString(rsi, 2) + ",";
    j += "\"wyckoff_event\":\"" + wyck + "\",";
    j += "\"score\":" + IntegerToString(score) + ",";
    j += "\"bias\":\"" + bias + "\",";
    j += "\"session\":\"" + session + "\",";
    j += "\"fib_618\":" + DoubleToString(fib618, _Digits) + ",";
    j += "\"fib_786\":" + DoubleToString(fib786, _Digits) + ",";
    j += "\"spread\":" + IntegerToString((int)SymbolInfoInteger(symbol, SYMBOL_SPREAD));
    j += "}";
    return j;
}

//======================================================================
//  HTTP POST vers n8n
//======================================================================
void PostToWebhook(string payload, string log_tag)
{
    uchar post_data[];
    uchar result[];
    string result_headers;

    StringToCharArray(payload, post_data, 0, StringLen(payload));

    string headers = "Content-Type: application/json\r\n"
                   + "X-API-Key: " + InpApiKey + "\r\n";

    int res = WebRequest("POST", InpWebhookURL, headers, InpTimeoutMs,
                         post_data, result, result_headers);

    if(res == -1)
        Print("❌ Webhook error [", log_tag, "] : ", GetLastError(), " — vérifier URL et permissions MT5");
    else
        Print("✅ Webhook [", log_tag, "] HTTP ", res, " | ", CharArrayToString(result));
}
//+------------------------------------------------------------------+
