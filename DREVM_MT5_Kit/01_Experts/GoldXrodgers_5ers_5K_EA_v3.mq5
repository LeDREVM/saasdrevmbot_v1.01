//+------------------------------------------------------------------+
//|                              GoldXrodgers_5ers_5K_EA.mq5          |
//|              Stratégie Négus Dja — optimisée The5ers 5K HighStakes|
//|  Confluence v3 : Fibo(jambe) + Kijun + RSI + FVG-zone + OB-zone   |
//|  v3 : FVG/OB doivent CONTENIR l'entree ; R/R et Wyckoff = filtres |
//|       et non plus des points ; gMaxScore 7 -> 5.                  |
//|  Garde-fous prop : DD journalier 5% / DD total 10% / cible phase  |
//|  Filtre news : blocage exécution + suppression pending (±buffer)  |
//+------------------------------------------------------------------+
#property copyright "Negus Dja"
#property version   "3.00"
#property strict
#property description "EA confluence optimise The5ers 5K High Stakes."
#property description "FVG + Order Block + Wyckoff + RSI score, garde-fous DD, filtre news."

#include <Trade\Trade.mqh>
CTrade trade;

//==================================================================//
//                            ENTRÉES                               //
//==================================================================//
input group "=== Général ==="
input long    InpMagic            = 250602;        // Magic number
input string  InpComment          = "GX-5ers";     // Commentaire ordres
input int     InpMaxSpreadPoints  = 40;            // Spread max (points)
input int     InpSlippagePoints   = 20;            // Slippage (points)

enum ENUM_EXEC_MODE { MODE_ALERT_ONLY=0, MODE_PENDING=1, MODE_MARKET=2 };
input group "=== Mode d'exécution ==="
input ENUM_EXEC_MODE InpExecMode  = MODE_ALERT_ONLY; // 0 alerte / 1 limit / 2 marché
input bool    InpSendPush         = true;          // Notification push mobile
input bool    InpSendAlert        = true;          // Popup terminal

//--- GARDE-FOUS PROP FIRM (The5ers 5K High Stakes)
input group "=== Garde-fous The5ers ==="
input double  InpAccountSize      = 5000.0;        // Solde initial du compte
input double  InpDailyDDLimitPct  = 5.0;           // Limite DD journalier The5ers (%)
input double  InpMaxDDLimitPct    = 10.0;          // Limite DD total The5ers (%)
input double  InpDailyBufferPct   = 3.5;           // Verrou interne journalier (< 5%)
input double  InpMaxBufferPct     = 7.0;           // Verrou interne total (< 10%)
input double  InpPhaseTargetPct   = 8.0;           // Cible phase (8% P1 / 5% P2)
input bool    InpLockOnTarget     = true;          // Stop trades quand cible atteinte
input int     InpServerDayRollover= 0;             // Heure rollover journalier (serveur)

//--- Risque par trade
input group "=== Risque ==="
input double  InpRiskPercent      = 0.5;           // Risque par trade (% du solde)
input double  InpMaxLotCap        = 0.0;           // Plafond de lot (0 = off, sécurité prop)
input double  InpMinRR            = 2.0;           // R/R minimum
input double  InpTpRR             = 2.5;           // R/R cible TP
input int     InpMaxOpenTrades    = 1;             // Trades simultanés max
input bool    InpForceStopLoss    = true;          // SL obligatoire (règle The5ers)

//--- Gestion de position (méthodo DREVM)
input group "=== Gestion de position ==="
input bool    InpUsePartial       = true;          // TP1 a 1R : cloture partielle
input double  InpPartialAtR        = 1.0;          // Declenche le partiel a X R
input double  InpPartialPercent    = 50.0;         // % du lot ferme en TP1
input bool    InpMoveBreakeven     = true;         // SL au breakeven apres TP1
input double  InpBeBufferPoints    = 20;           // Tampon BE (points au-dela entree)
input bool    InpUseTrailing       = true;         // Trailing ATR sur le runner
input double  InpTrailAtrMult       = 1.5;         // Distance trailing (x ATR)

//--- Sessions (heure serveur)
input group "=== Sessions ==="
input bool    InpUseSession       = true;          // Activer filtre session
input int     InpLondonStart      = 8;
input int     InpLondonEnd        = 12;
input int     InpNYStart          = 13;
input int     InpNYEnd            = 21;

//--- FILTRE NEWS (The5ers : interdit ±2 min, on prend une marge)
input group "=== Filtre News ==="
input bool    InpUseNewsFilter    = true;          // Activer filtre news
input int     InpNewsBufferMin    = 5;             // Marge avant/après (min) > 2 exigé
input string  InpNewsTimes        = "";            // Liste serveur "YYYY.MM.DD HH:MM;..."

//--- Tendance / Ichimoku
input group "=== Tendance ==="
input int     InpEmaFast          = 50;
input int     InpEmaSlow          = 100;
input int     InpTenkan           = 9;
input int     InpKijun            = 26;
input int     InpSenkou           = 52;

//--- Wyckoff (détection range/phase)
input group "=== Wyckoff ==="
input int     InpRangeLookback    = 40;            // Barres pour détecter range
input double  InpRangeMaxAtrMult  = 2.5;           // Range serré si amplitude < x*ATR

//--- RSI score
input group "=== RSI score ==="
input int     InpRsiPeriod        = 14;
input double  InpRsiBullMin       = 45.0;          // RSI mini pour biais haussier
input double  InpRsiBearMax       = 55.0;          // RSI maxi pour biais baissier

//--- FVG / Order Block
input group "=== FVG & Order Block ==="
input bool    InpUseFVG           = true;          // Confluence FVG
input bool    InpUseOB            = true;          // Confluence Order Block
input int     InpImbLookback      = 20;            // Barres pour chercher FVG/OB
input double  InpMinFvgAtrMult     = 0.30;         // Taille FVG mini (x ATR)
input bool    InpRequireEntryInZone = true;        // v3: l'entree doit etre DANS la zone FVG/OB
input double  InpZoneTolAtr        = 0.15;         // v3: tolerance autour de la zone (x ATR)
input double  InpMinLimitGapAtr    = 0.10;         // v3: ecart mini entre prix et ordre limite (x ATR)

//--- Fibonacci
input group "=== Fibonacci ==="
input int     InpSwingLookback    = 60;
input double  InpFibZoneMin       = 0.50;
input double  InpFibZoneMax       = 0.886;
input double  InpFibEntry         = 0.618;
input double  InpFibStopBufATR    = 0.5;           // Tampon SL au-delà du swing (x ATR)
// v3 : le facteur Fibo est structurellement bride par l'entree limite fixe.
//  ZONE_ATTEINTE  : point si le retracement ACTUEL est dans [Min,Max].
//                   Mais un BuyLimit a 61.8% exige que le prix soit AU-DESSUS
//                   de 61.8%, donc seule la fenetre [Min, InpFibEntry] survit
//                   -> facteur rare (~3-6% des signaux).
//  RETRAC_ENGAGE  : point si le retracement a demarre (>= InpFibProgressMin)
//                   sans avoir atteint le niveau d'entree. Le pullback est
//                   reel et l'ordre a une chance d'etre rempli "frais".
enum ENUM_FIB_MODE { FIB_ZONE_ATTEINTE=0, FIB_RETRAC_ENGAGE=1 };
input ENUM_FIB_MODE InpFibMode      = FIB_RETRAC_ENGAGE; // v3: mode du facteur Fibo
input double  InpFibProgressMin     = 0.236;       // v3: retracement mini (mode ENGAGE)

//--- Qualité
input group "=== Qualité du setup ==="
enum ENUM_MIN_GRADE { GRADE_B=0, GRADE_A=1, GRADE_APLUS=2 };
input ENUM_MIN_GRADE InpMinGrade  = GRADE_A;       // Note mini (A conseillé en prop)

//==================================================================//
//                          GLOBALS                                 //
//==================================================================//
int hEmaFast,hEmaSlow,hIchimoku,hRsi,hAtr;
datetime lastBarTime=0, lastAlertBar=0;
datetime gNewsTimes[];
int      gNewsCount=0;

double   gDayBaseline=0;      // equity/balance de référence du jour
int      gCurDay=-1;
bool     gLockedTotal=false;  // verrou DD total atteint
bool     gLockedTarget=false; // verrou cible atteinte

//--- Sortie d'analyse
int    gDir=0, gScore=0, gMaxScore=5;   // v3 : 5 facteurs REELS
double gFibPos=0;                       // retracement mesure sur la jambe
double gLegHigh=0, gLegLow=0;           // jambe d'impulsion en cours
double gEntry=0,gSL=0,gTP=0;
string gNotes="";
string gPhase="";

//==================================================================//
//                            INIT                                  //
//==================================================================//
int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(InpSlippagePoints);
   trade.SetTypeFillingBySymbol(_Symbol);

   hEmaFast = iMA(_Symbol,_Period,InpEmaFast,0,MODE_EMA,PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol,_Period,InpEmaSlow,0,MODE_EMA,PRICE_CLOSE);
   hIchimoku= iIchimoku(_Symbol,_Period,InpTenkan,InpKijun,InpSenkou);
   hRsi     = iRSI(_Symbol,_Period,InpRsiPeriod,PRICE_CLOSE);
   hAtr     = iATR(_Symbol,_Period,14);
   if(hEmaFast==INVALID_HANDLE||hEmaSlow==INVALID_HANDLE||hIchimoku==INVALID_HANDLE||
      hRsi==INVALID_HANDLE||hAtr==INVALID_HANDLE)
     { Print("Erreur indicateurs."); return(INIT_FAILED); }

   ParseNews();
   // v3 : Wyckoff et R/R sont devenus des FILTRES (rejet) et ne comptent
   //      plus de point. Facteurs reels : Fibo(jambe) + Kijun + RSI (+FVG)(+OB).
   gMaxScore = 3 + (InpUseFVG?1:0) + (InpUseOB?1:0);
   PrintFormat("GX 5ers EA | %s %s | cible %.1f%% | risk %.2f%% | mode %d",
               _Symbol,EnumToString((ENUM_TIMEFRAMES)_Period),InpPhaseTargetPct,InpRiskPercent,InpExecMode);
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   IndicatorRelease(hEmaFast); IndicatorRelease(hEmaSlow);
   IndicatorRelease(hIchimoku);IndicatorRelease(hRsi); IndicatorRelease(hAtr);
  }

//==================================================================//
//                       OUTILS DE BASE                             //
//==================================================================//
bool IsNewBar()
  {
   datetime t=(datetime)SeriesInfoInteger(_Symbol,_Period,SERIES_LASTBAR_DATE);
   if(t!=lastBarTime){ lastBarTime=t; return true; }
   return false;
  }
double Buf(int h,int b,int s){ double v[]; if(CopyBuffer(h,b,s,1,v)!=1) return 0.0; return v[0]; }

bool InSession()
  {
   if(!InpUseSession) return true;
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt); int h=dt.hour;
   return((h>=InpLondonStart && h<InpLondonEnd) || (h>=InpNYStart && h<InpNYEnd));
  }

//==================================================================//
//                          NEWS                                    //
//==================================================================//
void ParseNews()
  {
   gNewsCount=0; ArrayResize(gNewsTimes,0);
   if(StringLen(InpNewsTimes)==0) return;
   string parts[]; int n=StringSplit(InpNewsTimes,';',parts);
   for(int i=0;i<n;i++)
     {
      string s=parts[i]; StringTrimLeft(s); StringTrimRight(s);
      if(StringLen(s)==0) continue;
      datetime t=StringToTime(s);
      if(t>0){ ArrayResize(gNewsTimes,gNewsCount+1); gNewsTimes[gNewsCount]=t; gNewsCount++; }
     }
   PrintFormat("News chargées : %d événement(s).",gNewsCount);
  }

bool InNewsBlackout()
  {
   if(!InpUseNewsFilter || gNewsCount==0) return false;
   datetime now=TimeCurrent();
   int buf=InpNewsBufferMin*60;
   for(int i=0;i<gNewsCount;i++)
      if(now>=gNewsTimes[i]-buf && now<=gNewsTimes[i]+buf) return true;
   return false;
  }

// Supprime mes pending qui pourraient se déclencher pendant la fenêtre news
void CancelMyPendings()
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong tk=OrderGetTicket(i);
      if(OrderSelect(tk))
         if(OrderGetInteger(ORDER_MAGIC)==InpMagic && OrderGetString(ORDER_SYMBOL)==_Symbol)
            trade.OrderDelete(tk);
     }
  }

//==================================================================//
//                    GARDE-FOUS PROP FIRM                          //
//==================================================================//
void UpdateDayBaseline()
  {
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   int dayId=dt.day_of_year;
   // rollover quand on passe l'heure définie sur un nouveau jour
   if(dayId!=gCurDay && dt.hour>=InpServerDayRollover)
     {
      double bal=AccountInfoDouble(ACCOUNT_BALANCE);
      double eq =AccountInfoDouble(ACCOUNT_EQUITY);
      gDayBaseline=MathMax(bal,eq);   // The5ers : le plus haut des deux
      gCurDay=dayId;
     }
   if(gDayBaseline<=0) gDayBaseline=MathMax(AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY));
  }

// true = autorisé à ouvrir un nouveau trade
bool RiskGuardOK()
  {
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);

   // 1) DD total (verrou interne sous la limite The5ers)
   double maxFloor=InpAccountSize*(1.0-InpMaxBufferPct/100.0);
   if(eq<=maxFloor){ if(!gLockedTotal){ Print("⛔ Verrou DD TOTAL atteint."); gLockedTotal=true; } }
   if(gLockedTotal) return false;

   // 2) DD journalier (verrou interne sous 5%)
   double dailyFloor=gDayBaseline*(1.0-InpDailyBufferPct/100.0);
   if(eq<=dailyFloor){ Print("⛔ Verrou DD JOURNALIER atteint — pause jusqu'au rollover."); return false; }

   // 3) Cible de phase atteinte
   if(InpLockOnTarget)
     {
      double targetEq=InpAccountSize*(1.0+InpPhaseTargetPct/100.0);
      if(eq>=targetEq){ if(!gLockedTarget){ Print("🎯 Cible phase atteinte — stop nouveaux trades."); gLockedTarget=true; } }
      if(gLockedTarget) return false;
     }
   return true;
  }

int CountMyTrades()
  {
   int n=0;
   for(int i=PositionsTotal()-1;i>=0;i--)
     { ulong tk=PositionGetTicket(i);
       if(PositionSelectByTicket(tk))
          if(PositionGetInteger(POSITION_MAGIC)==InpMagic && PositionGetString(POSITION_SYMBOL)==_Symbol) n++; }
   for(int i=OrdersTotal()-1;i>=0;i--)
     { ulong tk=OrderGetTicket(i);
       if(OrderSelect(tk))
          if(OrderGetInteger(ORDER_MAGIC)==InpMagic && OrderGetString(ORDER_SYMBOL)==_Symbol) n++; }
   return n;
  }

//==================================================================//
//                     STRUCTURE / SMC                              //
//==================================================================//
void GetSwing(double &swH,double &swL)
  {
   swH=-DBL_MAX; swL=DBL_MAX;
   for(int i=1;i<=InpSwingLookback;i++)
     { double hi=iHigh(_Symbol,_Period,i), lo=iLow(_Symbol,_Period,i);
       if(hi>swH) swH=hi; if(lo<swL) swL=lo; }
  }

//--- v3 : jambe d'IMPULSION en cours (et non le range brut sur N barres).
//    Le retracement Fibonacci n'a de sens que mesure sur la derniere jambe
//    directionnelle. Ancien bug : (swH-close)/range mesurait la position dans
//    un range de 60 barres, incompatible avec la condition trendUp qui exige
//    justement un prix haut -> le point Fibo ne tombait que dans 6% des cas.
//    dir=+1 : jambe haussiere = plus bas AVANT le plus haut recent.
//    dir=-1 : jambe baissiere = plus haut AVANT le plus bas recent.
bool GetImpulseLeg(int dir,double &legH,double &legL)
  {
   int idxExt=1;
   if(dir>0)
     {
      double best=-DBL_MAX;
      for(int i=1;i<=InpSwingLookback;i++)
        { double hi=iHigh(_Symbol,_Period,i); if(hi>best){ best=hi; idxExt=i; } }
      legH=best;
      double lo=DBL_MAX;
      for(int i=idxExt;i<=InpSwingLookback;i++)   // strictement AVANT le sommet
        { double v=iLow(_Symbol,_Period,i); if(v<lo) lo=v; }
      legL=lo;
     }
   else
     {
      double worst=DBL_MAX;
      for(int i=1;i<=InpSwingLookback;i++)
        { double lo=iLow(_Symbol,_Period,i); if(lo<worst){ worst=lo; idxExt=i; } }
      legL=worst;
      double hi=-DBL_MAX;
      for(int i=idxExt;i<=InpSwingLookback;i++)
        { double v=iHigh(_Symbol,_Period,i); if(v>hi) hi=v; }
      legH=hi;
     }
   return (legH>legL);
  }

// FVG haussier : gap entre high(i+2) et low(i) -> price doit pouvoir y revenir
bool BullishFVG(double atr,double &zLo,double &zHi)
  {
   for(int i=1;i<=InpImbLookback;i++)
     { double lowI=iLow(_Symbol,_Period,i), highI2=iHigh(_Symbol,_Period,i+2);
       if(lowI>highI2 && (lowI-highI2)>=atr*InpMinFvgAtrMult){ zLo=highI2; zHi=lowI; return true; } }
   return false;
  }
bool BearishFVG(double atr,double &zLo,double &zHi)
  {
   for(int i=1;i<=InpImbLookback;i++)
     { double highI=iHigh(_Symbol,_Period,i), lowI2=iLow(_Symbol,_Period,i+2);
       if(lowI2>highI && (lowI2-highI)>=atr*InpMinFvgAtrMult){ zLo=highI; zHi=lowI2; return true; } }
   return false;
  }

// Order Block haussier : dernière bougie baissière avant déplacement haussier
bool BullishOB(double &zLo,double &zHi)
  {
   for(int i=2;i<=InpImbLookback;i++)
     { bool down=iClose(_Symbol,_Period,i)<iOpen(_Symbol,_Period,i);
       bool disp=iClose(_Symbol,_Period,i-1)>iHigh(_Symbol,_Period,i);
       if(down && disp){ zLo=iLow(_Symbol,_Period,i); zHi=iHigh(_Symbol,_Period,i); return true; } }
   return false;
  }
bool BearishOB(double &zLo,double &zHi)
  {
   for(int i=2;i<=InpImbLookback;i++)
     { bool up=iClose(_Symbol,_Period,i)>iOpen(_Symbol,_Period,i);
       bool disp=iClose(_Symbol,_Period,i-1)<iLow(_Symbol,_Period,i);
       if(up && disp){ zLo=iLow(_Symbol,_Period,i); zHi=iHigh(_Symbol,_Period,i); return true; } }
   return false;
  }

//--- v3 : evaluation du facteur Fibonacci selon le mode choisi.
bool FibFactorOK(double fibPos)
  {
   if(InpFibMode==FIB_ZONE_ATTEINTE)
      return (fibPos>=MathMin(InpFibZoneMin,InpFibZoneMax) &&
              fibPos<=MathMax(InpFibZoneMin,InpFibZoneMax));
   // FIB_RETRAC_ENGAGE : le repli a demarre mais n'a pas encore atteint l'entree
   return (fibPos>=InpFibProgressMin && fibPos<InpFibEntry);
  }

//--- v3 : l'entree projetee tombe-t-elle dans la zone [zLo,zHi] ?
//    Tolerance en ATR pour absorber le bruit d'un tick.
bool EntryInZone(double entry,double zLo,double zHi,double atr)
  {
   if(!InpRequireEntryInZone) return true;
   if(entry<=0 || zHi<=zLo)   return false;
   double tol=atr*InpZoneTolAtr;
   return (entry>=zLo-tol && entry<=zHi+tol);
  }

//==================================================================//
//                    SCORING DE CONFLUENCE                         //
//==================================================================//
string GradeFromScore(int s)
  {
   double r=(gMaxScore>0)?(double)s/gMaxScore:0;
   if(r>=0.85) return "A+";
   if(r>=0.70) return "A";
   if(r>=0.55) return "B";
   return "C";
  }
int MinScore(ENUM_MIN_GRADE g)
  {
   if(g==GRADE_APLUS) return (int)MathCeil(gMaxScore*0.85);
   if(g==GRADE_A)     return (int)MathCeil(gMaxScore*0.70);
   return (int)MathCeil(gMaxScore*0.55);
  }

void Analyze()
  {
   gScore=0; gDir=0; gEntry=0; gSL=0; gTP=0; gNotes=""; gPhase=""; gFibPos=0; gLegHigh=0; gLegLow=0;

   double emaF=Buf(hEmaFast,0,1), emaS=Buf(hEmaSlow,0,1);
   double kijun=Buf(hIchimoku,1,1);
   double spanA=Buf(hIchimoku,2,1), spanB=Buf(hIchimoku,3,1);
   double rsi1=Buf(hRsi,0,1), rsi3=Buf(hRsi,0,3);
   double atr=Buf(hAtr,0,1);
   double close1=iClose(_Symbol,_Period,1);
   double kumoTop=MathMax(spanA,spanB), kumoBot=MathMin(spanA,spanB);

   double swH,swL; GetSwing(swH,swL);
   double range=swH-swL; if(range<=0||atr<=0){ gNotes="Range/ATR invalide."; return; }

   //--- Wyckoff phase (simplifié)
   bool tight=(range < atr*InpRangeMaxAtrMult);
   bool trendUp=(emaF>emaS) && (close1>kumoTop);
   bool trendDown=(emaF<emaS) && (close1<kumoBot);
   if(trendUp)        gPhase="MARKUP";
   else if(trendDown) gPhase="MARKDOWN";
   else if(tight && close1<= (swL+range*0.4)) gPhase="ACCUMULATION";
   else if(tight && close1>= (swH-range*0.4)) gPhase="DISTRIBUTION";
   else gPhase="RANGE";

   double zLo,zHi;

   //========================= BUY ===========================//
   if(trendUp)
     {
      gDir=1; gNotes+="Wyckoff MARKUP (filtre). ";   // v3 : plus de point ici

      // --- jambe d'impulsion + entree AVANT tout scoring de zone
      if(!GetImpulseLeg(1,gLegHigh,gLegLow)){ gDir=0; gNotes="Jambe invalide."; return; }
      double legRange=gLegHigh-gLegLow;
      if(legRange<=0){ gDir=0; gNotes="Jambe nulle."; return; }

      gEntry=gLegHigh-legRange*InpFibEntry;
      gSL   =gLegLow-atr*InpFibStopBufATR;
      double risk=gEntry-gSL;
      // --- v3 : R/R = FILTRE de rejet, plus un point de score
      if(risk<=0){ gDir=0; gNotes="Risque invalide."; return; }
      gTP=gEntry+risk*InpTpRR;
      if((gTP-gEntry)/risk < InpMinRR){ gDir=0; gNotes="R/R sous le minimum."; return; }

      // --- v3 : coherence de l'ordre limite. Un BuyLimit doit etre SOUS le
      //     marche. Si le prix a deja retrace au-dela de InpFibEntry, l'ordre
      //     serait du mauvais cote et rejete par le broker (erreur 130).
      if(InpExecMode==MODE_PENDING && gEntry >= close1-atr*InpMinLimitGapAtr)
        { gDir=0; gNotes="Entree limite au-dessus du marche (retracement deja depasse)."; return; }

      // --- (1) Fibonacci mesure sur la JAMBE
      gFibPos=(gLegHigh-close1)/legRange;
      if(FibFactorOK(gFibPos))
        { gScore++; gNotes+=StringFormat("Fibo %.0f%% (jambe). ",gFibPos*100); }
      // --- (2) Kijun
      if(close1>kijun){ gScore++; gNotes+="> Kijun. "; }
      // --- (3) RSI
      if(rsi1>=InpRsiBullMin && rsi1>rsi3){ gScore++; gNotes+="RSI haussier. "; }
      // v3 : le point n'est accorde que si l'ENTREE tombe dans la zone.
      //      Avant, zLo/zHi etaient calcules puis jamais relus : le point
      //      signifiait "un FVG existe quelque part dans les 20 dernieres
      //      bougies" -> vrai dans ~80% des cas, donc non discriminant.
      if(InpUseFVG && BullishFVG(atr,zLo,zHi) && EntryInZone(gEntry,zLo,zHi,atr))
        { gScore++; gNotes+="FVG bull (entree dans zone). "; }
      if(InpUseOB && BullishOB(zLo,zHi) && EntryInZone(gEntry,zLo,zHi,atr))
        { gScore++; gNotes+="OB bull (entree dans zone). "; }

      gNotes+=StringFormat("R/R %.1f. ",InpTpRR);
     }
   //========================= SELL ==========================//
   else if(trendDown)
     {
      gDir=-1; gNotes+="Wyckoff MARKDOWN (filtre). ";

      if(!GetImpulseLeg(-1,gLegHigh,gLegLow)){ gDir=0; gNotes="Jambe invalide."; return; }
      double legRange=gLegHigh-gLegLow;
      if(legRange<=0){ gDir=0; gNotes="Jambe nulle."; return; }

      gEntry=gLegLow+legRange*InpFibEntry;
      gSL   =gLegHigh+atr*InpFibStopBufATR;
      double risk=gSL-gEntry;
      if(risk<=0){ gDir=0; gNotes="Risque invalide."; return; }
      gTP=gEntry-risk*InpTpRR;
      if((gEntry-gTP)/risk < InpMinRR){ gDir=0; gNotes="R/R sous le minimum."; return; }

      if(InpExecMode==MODE_PENDING && gEntry <= close1+atr*InpMinLimitGapAtr)
        { gDir=0; gNotes="Entree limite sous le marche (retracement deja depasse)."; return; }

      gFibPos=(close1-gLegLow)/legRange;
      if(FibFactorOK(gFibPos))
        { gScore++; gNotes+=StringFormat("Fibo %.0f%% (jambe). ",gFibPos*100); }
      if(close1<kijun){ gScore++; gNotes+="< Kijun. "; }
      if(rsi1<=InpRsiBearMax && rsi1<rsi3){ gScore++; gNotes+="RSI baissier. "; }
      if(InpUseFVG && BearishFVG(atr,zLo,zHi) && EntryInZone(gEntry,zLo,zHi,atr))
        { gScore++; gNotes+="FVG bear (entree dans zone). "; }
      if(InpUseOB && BearishOB(zLo,zHi) && EntryInZone(gEntry,zLo,zHi,atr))
        { gScore++; gNotes+="OB bear (entree dans zone). "; }

      gNotes+=StringFormat("R/R %.1f. ",InpTpRR);
     }
   else gNotes="Pas de biais (phase "+gPhase+"). Attente.";
  }

//==================================================================//
//                    LOT / EXÉCUTION                               //
//==================================================================//
double NormalizeLot(double lot)
  {
   double mn=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double mx=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
   double st=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   if(InpMaxLotCap>0) mx=MathMin(mx,InpMaxLotCap);   // plafond sécurité prop
   lot=MathFloor(lot/st)*st; return MathMax(mn,MathMin(mx,lot));
  }
double CalcLot(double entry,double sl)
  {
   double riskAmount=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0;
   double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE);
   double ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
   double dist=MathAbs(entry-sl);
   if(dist<=0||tv<=0||ts<=0) return NormalizeLot(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));
   double lossPerLot=(dist/ts)*tv; if(lossPerLot<=0) return NormalizeLot(SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN));
   return NormalizeLot(riskAmount/lossPerLot);
  }

void FireSignal(string grade)
  {
   if(InpForceStopLoss && gSL<=0) return; // SL obligatoire (règle The5ers)
   double lot=CalcLot(gEntry,gSL);
   string side=(gDir==1)?"BUY":"SELL";
   string msg=StringFormat("%s %s | %s [%s] %d/%d\nEntry %.3f SL %.3f TP %.3f Lot %.2f\n%s",
                           side,_Symbol,grade,gPhase,gScore,gMaxScore,gEntry,gSL,gTP,lot,gNotes);
   if(InpSendAlert) Alert(msg);
   if(InpSendPush)  SendNotification(msg);
   Print(msg);

   if(InpExecMode==MODE_ALERT_ONLY) return;
   if(InpExecMode==MODE_PENDING)
     {
      if(gDir==1) trade.BuyLimit(lot,gEntry,_Symbol,gSL,gTP,ORDER_TIME_GTC,0,InpComment+" "+grade);
      else        trade.SellLimit(lot,gEntry,_Symbol,gSL,gTP,ORDER_TIME_GTC,0,InpComment+" "+grade);
      return;
     }
   if(InpExecMode==MODE_MARKET)
     {
      double ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK), bid=SymbolInfoDouble(_Symbol,SYMBOL_BID);
      if(gDir==1) trade.Buy(lot,_Symbol,ask,gSL,gTP,InpComment+" "+grade);
      else        trade.Sell(lot,_Symbol,bid,gSL,gTP,InpComment+" "+grade);
     }
  }

//==================================================================//
//             GESTION DE POSITION (partiel/BE/trailing)            //
//==================================================================//
ulong  gTrackTicket[];
double gTrackInitRisk[];
bool   gTrackPartial[];

int TrackIndex(ulong tk)
  {
   for(int i=0;i<ArraySize(gTrackTicket);i++) if(gTrackTicket[i]==tk) return i;
   return -1;
  }
void TrackAdd(ulong tk,double initRisk)
  {
   int n=ArraySize(gTrackTicket);
   ArrayResize(gTrackTicket,n+1); ArrayResize(gTrackInitRisk,n+1); ArrayResize(gTrackPartial,n+1);
   gTrackTicket[n]=tk; gTrackInitRisk[n]=initRisk; gTrackPartial[n]=false;
  }

void ManagePositions()
  {
   double atr=Buf(hAtr,0,1);
   double pt =SymbolInfoDouble(_Symbol,SYMBOL_POINT);
   double stepLot=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
   double minLot =SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);

   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);
      if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol)  continue;

      long   type =PositionGetInteger(POSITION_TYPE);
      double open =PositionGetDouble(POSITION_PRICE_OPEN);
      double sl   =PositionGetDouble(POSITION_SL);
      double tp   =PositionGetDouble(POSITION_TP);
      double vol  =PositionGetDouble(POSITION_VOLUME);
      double price=(type==POSITION_TYPE_BUY)?SymbolInfoDouble(_Symbol,SYMBOL_BID)
                                            :SymbolInfoDouble(_Symbol,SYMBOL_ASK);

      //--- enregistrement (R initial = |open - SL d'origine|)
      int idx=TrackIndex(tk);
      if(idx<0)
        { double r=MathAbs(open-sl); if(r<=0) r=atr; TrackAdd(tk,r); idx=TrackIndex(tk); }
      double R=gTrackInitRisk[idx];
      if(R<=0) continue;

      double profitR=(type==POSITION_TYPE_BUY)?(price-open)/R:(open-price)/R;

      //--- 1) TP1 partiel à X R + breakeven
      if(InpUsePartial && !gTrackPartial[idx] && profitR>=InpPartialAtR)
        {
         double closeVol=NormalizeLot(vol*InpPartialPercent/100.0);
         double remain  =vol-closeVol;
         if(closeVol>=minLot && remain>=minLot)
           {
            if(trade.PositionClosePartial(tk,closeVol))
              {
               gTrackPartial[idx]=true;
               if(InpMoveBreakeven)
                 {
                  double be=(type==POSITION_TYPE_BUY)?open+InpBeBufferPoints*pt
                                                     :open-InpBeBufferPoints*pt;
                  trade.PositionModify(tk,be,tp);
                 }
              }
           }
        }

      //--- 2) Trailing ATR sur le runner (après partiel)
      if(InpUseTrailing && gTrackPartial[idx] && atr>0)
        {
         double newSL;
         if(type==POSITION_TYPE_BUY)
           { newSL=price-atr*InpTrailAtrMult; if(newSL>sl && newSL>open) trade.PositionModify(tk,newSL,tp); }
         else
           { newSL=price+atr*InpTrailAtrMult; if((newSL<sl||sl==0) && newSL<open) trade.PositionModify(tk,newSL,tp); }
        }
     }
  }

//==================================================================//
//                            TICK                                  //
//==================================================================//
void OnTick()
  {
   UpdateDayBaseline();

   //--- Gestion des positions ouvertes : À CHAQUE TICK
   ManagePositions();

   //--- Filtre news : prioritaire, supprime mes pending dans la fenêtre
   if(InNewsBlackout())
     { CancelMyPendings(); return; }

   if(!IsNewBar()) return;
   if(!InSession()) return;
   if(!RiskGuardOK()) return;
   if(CountMyTrades()>=InpMaxOpenTrades) return;
   if(SymbolInfoInteger(_Symbol,SYMBOL_SPREAD)>InpMaxSpreadPoints) return;

   Analyze();
   if(gDir==0) return;
   string grade=GradeFromScore(gScore);
   if(gScore<MinScore(InpMinGrade)) return;
   if(gEntry<=0||gSL<=0||gTP<=0) return;

   if(lastAlertBar==lastBarTime) return;
   lastAlertBar=lastBarTime;
   FireSignal(grade);
  }

//==================================================================//
//        CRITÈRE D'OPTIMISATION ORIENTÉ CHALLENGE THE5ERS          //
//  Maximise un score "prop-passable" et DISQUALIFIE tout réglage   //
//  qui violerait le DD total, manque de trades, ou n'atteint pas   //
//  la cible de phase. À choisir : Tester > "Custom max" comme      //
//  critère d'optimisation.                                         //
//==================================================================//
double OnTester()
  {
   double profit  = TesterStatistics(STAT_PROFIT);
   double pf      = TesterStatistics(STAT_PROFIT_FACTOR);
   int    trades  = (int)TesterStatistics(STAT_TRADES);
   double winRate = (trades>0) ? TesterStatistics(STAT_PROFIT_TRADES)/trades*100.0 : 0.0;

   // Pire drawdown equity en % (on prend le plus défavorable des deux mesures)
   double ddA = TesterStatistics(STAT_EQUITYDD_PERCENT);
   double ddB = TesterStatistics(STAT_EQUITY_DDREL_PERCENT);
   double ddPct = MathMax(ddA,ddB);

   // --- DISQUALIFICATIONS (renvoie 0 = réglage rejeté) ---
   if(ddPct >= InpMaxDDLimitPct)      return 0.0;  // aurait cassé le DD total
   if(trades < 30)                    return 0.0;  // pas assez de trades = non fiable
   if(profit <= 0.0)                  return 0.0;  // perdant
   if(profit < InpAccountSize*InpPhaseTargetPct/100.0) return 0.0; // n'atteint pas la cible

   // --- Score prop-aware : récompense le profit & PF, pénalise le DD ---
   double score = (profit * pf * (winRate/100.0)) / (ddPct + 1.0);
   return score;
  }
//+------------------------------------------------------------------+
