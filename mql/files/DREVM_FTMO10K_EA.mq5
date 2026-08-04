//+------------------------------------------------------------------+
//|                                        DREVM_FTMO10K_EA.mq5      |
//|                     DREVM / GoldXrodgers — Negus Dja             |
//|                                                                  |
//|  Compte cible : FTMO 10 000 USD (challenge ou funded)            |
//|  Broker       : Fusion Markets MT5 — serveur GMT+3 (ete)         |
//|  Timeframe    : attacher en M5 (entree). Structure M15, biais H4.|
//|                                                                  |
//|  EMPLACEMENT (les 3 fichiers dans le MEME dossier) :             |
//|    MQL5\Experts\drevmbot\DREVM_BreakManipulation.mqh             |
//|    MQL5\Experts\drevmbot\DREVM_FTMO10K_Bridge.mqh                |
//|    MQL5\Experts\drevmbot\DREVM_FTMO10K_EA.mq5   <- compiler      |
//|  Les includes sont relatifs (guillemets), pas <Include/>.        |
//|                                                                  |
//|  INVARIANTS                                                      |
//|   - Signal evalue UNIQUEMENT sur cloture de barre M5.            |
//|   - MSS/BOS = gate. R/R < 2 = veto. Contre-tendance H4 = veto.   |
//|   - Grade < B => aucun prix expose, aucune action.               |
//|   - MODE_ALERT_ONLY par defaut : l'EA n'entre pas seul.          |
//|   - La gestion de position (50% a 1R + BE + trailing ATR) est le |
//|     seul module valide statistiquement : elle tourne toujours,   |
//|     y compris sur les positions ouvertes a la main.              |
//|   - Aucune statistique de performance affichee ou promise.       |
//+------------------------------------------------------------------+
#property copyright "DREVM / Negus Dja"
#property link      "https://github.com/LeDREVM/saasdrevmbot_v1.01"
#property version   "1.00"
#property strict

#include <Trade/Trade.mqh>
#include "DREVM_FTMO10K_Bridge.mqh"

//+------------------------------------------------------------------+
//| Parametres                                                       |
//+------------------------------------------------------------------+
enum ENUM_TRAIL_MODE
  {
   TRAIL_ATR   = 0,   // Distance = multiplicateur x ATR (s'adapte a la volatilite)
   TRAIL_FIXED = 1    // Distance fixe en points (a recalibrer par symbole)
  };

input group "=== Mode ==="
input ENUM_DREVM_MODE InpMode              = MODE_ALERT_ONLY; // Mode d'execution
input long            InpMagic             = 100010;          // Magic number (FTMO 10K)
input bool            InpManageManualTrades= true;            // Gerer aussi les trades manuels

input group "=== Risque compte FTMO 10K ==="
input double InpDailyLockPct   = 3.5;    // Lock perte jour %      (FTMO: 5%)
input double InpMaxDDPct       = 7.0;    // Lock drawdown total %  (FTMO: 10%)
input double InpTargetPct      = 8.0;    // Objectif phase %       (FTMO: 10%)
input double InpRiskPct        = 0.5;    // Risque par trade %
input int    InpMaxTradesDay   = 3;      // Trades max par jour
input int    InpMaxLossStreak  = 2;      // Pertes consecutives max

input group "=== Session (heures serveur GMT+3) ==="
input int    InpSessStartHour  = 15;     // Debut (15 = 08h NY ete)
input int    InpSessEndHour    = 22;     // Fin
input double InpMaxSpreadPts   = 35;     // Spread max en points

input group "=== Blackout news (sortie de ff_to_newstimes.py) ==="
input string InpNewsTimes      = "";     // "2026.08.05 15:30,2026.08.06 14:00"
input int    InpNewsFreezeMin  = 4;      // Freeze +/- minutes
input bool   InpNewsFlatBefore = true;   // Fermer les positions avant l'event

input group "=== Gestion de position (module valide) ==="
input bool   InpUsePartial     = true;   // Partiel 50% a 1R
input bool   InpUseBreakeven   = true;   // SL au BE apres le partiel
input double InpBeOffsetPts    = 20;     // Offset BE en points
input bool   InpUseTrail       = true;   // Activer le trailing
input ENUM_TRAIL_MODE InpTrailMode = TRAIL_ATR; // Type de trailing
input double InpTrailFixedPts  = 90;     // Distance fixe (points) si TRAIL_FIXED
input double InpAtrTrailMult   = 1.5;    // Multiplicateur ATR si TRAIL_ATR
input int    InpAtrPeriod      = 14;     // Periode ATR
input double InpTrailStepPts   = 15;     // Pas minimal du trailing (points)

input group "=== Ordres en attente (MODE_PENDING) ==="
input int    InpPendingExpiryMin = 45;   // Expiration du limit (minutes)

input group "=== Notifications & journal ==="
input bool   InpPushNotify     = true;   // Notification push MT5
input bool   InpJournalCSV     = true;   // Journal CSV dans MQL5/Files
input string InpJournalFile    = "DREVM_FTMO10K_journal.csv";

//+------------------------------------------------------------------+
//| Globales                                                         |
//+------------------------------------------------------------------+
CTrade          gTrade;
CDrevmFTMO10K   gDrevm;
int             gAtrHandle = INVALID_HANDLE;
datetime        gNews[];
double          gRiskMoney = 0.0;
datetime        gLastSignalBar = 0;

struct SPosState
  {
   ulong    ticket;
   double   entry;
   double   origSL;
   double   risk;      // distance entree-SL initial
   int      dir;       // +1 buy / -1 sell
   bool     partialDone;
   bool     bePlaced;
  };
SPosState gPos[];

//+------------------------------------------------------------------+
//| Utilitaires                                                      |
//+------------------------------------------------------------------+
double Pt(void) { return(SymbolInfoDouble(_Symbol,SYMBOL_POINT)); }

double AtrNow(void)
  {
   double b[]; ArraySetAsSeries(b,true);
   if(gAtrHandle==INVALID_HANDLE) return(0.0);
   if(CopyBuffer(gAtrHandle,0,1,1,b)<=0) return(0.0);
   return(b[0]);
  }

double SpreadPoints(void)
  {
   return((SymbolInfoDouble(_Symbol,SYMBOL_ASK)-SymbolInfoDouble(_Symbol,SYMBOL_BID))/Pt());
  }

void Notify(const string msg)
  {
   Print(msg);
   if(InpPushNotify) SendNotification(StringSubstr(_Symbol+" | "+msg,0,250));
  }

//+------------------------------------------------------------------+
//| News : parsing de InpNewsTimes                                   |
//+------------------------------------------------------------------+
void ParseNewsTimes(void)
  {
   ArrayFree(gNews);
   if(StringLen(InpNewsTimes)<10) return;

   string src=InpNewsTimes;
   StringReplace(src,";",",");
   StringReplace(src,"|",",");
   string parts[];
   int n=StringSplit(src,',',parts);
   for(int i=0;i<n;i++)
     {
      string s=parts[i];
      StringTrimLeft(s); StringTrimRight(s);
      if(StringLen(s)<10) continue;
      datetime t=StringToTime(s);
      if(t>0)
        {
         int k=ArraySize(gNews);
         ArrayResize(gNews,k+1);
         gNews[k]=t;
        }
     }
   ArraySort(gNews);
   PrintFormat("DREVM: %d evenements news charges (heure serveur).",ArraySize(gNews));
  }

// -1 = hors fenetre, sinon secondes restantes avant l'event (peut etre negatif si passe)
bool IsNewsFrozen(bool &beforeEvent)
  {
   beforeEvent=false;
   datetime now=TimeCurrent();
   int w=InpNewsFreezeMin*60;
   for(int i=0;i<ArraySize(gNews);i++)
     {
      long d=(long)gNews[i]-(long)now;
      if(MathAbs((double)d)<=w) { beforeEvent=(d>0); return(true); }
     }
   return(false);
  }

//+------------------------------------------------------------------+
//| Suivi d'etat des positions                                       |
//+------------------------------------------------------------------+
int FindPos(const ulong ticket)
  {
   for(int i=0;i<ArraySize(gPos);i++) if(gPos[i].ticket==ticket) return(i);
   return(-1);
  }

void RegisterPos(const ulong ticket)
  {
   if(!PositionSelectByTicket(ticket)) return;
   int i=FindPos(ticket);
   if(i<0)
     {
      i=ArraySize(gPos);
      ArrayResize(gPos,i+1);
      gPos[i].ticket      = ticket;
      gPos[i].entry       = PositionGetDouble(POSITION_PRICE_OPEN);
      gPos[i].origSL      = PositionGetDouble(POSITION_SL);
      gPos[i].dir         = (PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY)?1:-1;
      gPos[i].risk        = MathAbs(gPos[i].entry-gPos[i].origSL);
      gPos[i].partialDone = false;
      gPos[i].bePlaced    = false;
     }
  }

void PurgeClosedPos(void)
  {
   for(int i=ArraySize(gPos)-1;i>=0;i--)
      if(!PositionSelectByTicket(gPos[i].ticket))
        {
         for(int j=i;j<ArraySize(gPos)-1;j++) gPos[j]=gPos[j+1];
         ArrayResize(gPos,ArraySize(gPos)-1);
        }
  }

bool IsOurs(void)
  {
   if(PositionGetString(POSITION_SYMBOL)!=_Symbol) return(false);
   if(PositionGetInteger(POSITION_MAGIC)==InpMagic) return(true);
   return(InpManageManualTrades && PositionGetInteger(POSITION_MAGIC)==0);
  }

//+------------------------------------------------------------------+
//| GESTION DE POSITION — partiel 1R, breakeven, trailing ATR        |
//+------------------------------------------------------------------+
void ManagePositions(void)
  {
   PurgeClosedPos();
   double atr=AtrNow();
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   double stopLevel=(double)SymbolInfoInteger(_Symbol,SYMBOL_TRADE_STOPS_LEVEL)*Pt();

   for(int p=PositionsTotal()-1;p>=0;p--)
     {
      ulong ticket=PositionGetTicket(p);
      if(ticket==0 || !PositionSelectByTicket(ticket)) continue;
      if(!IsOurs()) continue;

      RegisterPos(ticket);
      int idx=FindPos(ticket);
      if(idx<0 || gPos[idx].risk<=0.0) continue;

      int    dir  = gPos[idx].dir;
      double entry= gPos[idx].entry;
      double risk = gPos[idx].risk;
      double vol  = PositionGetDouble(POSITION_VOLUME);
      double sl   = PositionGetDouble(POSITION_SL);
      double tp   = PositionGetDouble(POSITION_TP);
      double px   = (dir>0)?SymbolInfoDouble(_Symbol,SYMBOL_BID)
                           :SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      double gain = (px-entry)*dir;

      //--- 1) partiel 50% a 1R
      if(InpUsePartial && !gPos[idx].partialDone && gain>=risk)
        {
         double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);
         double vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
         double half=MathFloor((vol/2.0)/step)*step;
         if(half>=vmin && (vol-half)>=vmin)
           {
            if(gTrade.PositionClosePartial(ticket,half))
              {
               gPos[idx].partialDone=true;
               Notify(StringFormat("Partiel 50%% a 1R execute (%.2f lots) ticket %I64u",half,ticket));
              }
           }
         else gPos[idx].partialDone=true; // volume trop petit pour scinder
        }

      //--- 2) breakeven apres le partiel
      if(InpUseBreakeven && gPos[idx].partialDone && !gPos[idx].bePlaced)
        {
         double be=entry+dir*InpBeOffsetPts*Pt();
         bool better=(dir>0)?(be>sl):(be<sl||sl==0.0);
         if(better && MathAbs(px-be)>stopLevel)
            if(gTrade.PositionModify(ticket,NormalizeDouble(be,dg),tp))
              {
               gPos[idx].bePlaced=true;
               Notify(StringFormat("SL au breakeven ticket %I64u",ticket));
              }
        }

      //--- 3) trailing (uniquement apres BE, jamais en sens defavorable)
      if(InpUseTrail && gPos[idx].bePlaced)
        {
         double dist=(InpTrailMode==TRAIL_FIXED) ? InpTrailFixedPts*Pt()
                                                 : InpAtrTrailMult*atr;
         if(dist>0.0)
           {
            double newSl=(dir>0)?px-dist:px+dist;
            newSl=NormalizeDouble(newSl,dg);
            //--- pas minimal : sans ce garde-fou le trailing envoie un ordre
            //--- de modification a CHAQUE tick (flood serveur + rejets broker)
            double stepPx=InpTrailStepPts*Pt();
            bool better=(dir>0)?(newSl>sl+stepPx):(newSl<sl-stepPx);
            if(better && MathAbs(px-newSl)>stopLevel)
               gTrade.PositionModify(ticket,newSl,tp);
           }
        }
     }
  }

//+------------------------------------------------------------------+
//| Fermetures d'urgence (news)                                      |
//+------------------------------------------------------------------+
void CancelPendings(void)
  {
   for(int i=OrdersTotal()-1;i>=0;i--)
     {
      ulong t=OrderGetTicket(i);
      if(t==0) continue;
      if(OrderGetString(ORDER_SYMBOL)!=_Symbol) continue;
      if(OrderGetInteger(ORDER_MAGIC)!=InpMagic) continue;
      gTrade.OrderDelete(t);
     }
  }

void CloseAllPositions(const string reason)
  {
   for(int p=PositionsTotal()-1;p>=0;p--)
     {
      ulong t=PositionGetTicket(p);
      if(t==0 || !PositionSelectByTicket(t)) continue;
      if(!IsOurs()) continue;
      if(gTrade.PositionClose(t))
         Notify("Fermeture ticket "+IntegerToString((int)t)+" — "+reason);
     }
  }

//+------------------------------------------------------------------+
//| Journal CSV                                                      |
//+------------------------------------------------------------------+
void JournalWrite(const SDrevmDecision &d)
  {
   if(!InpJournalCSV) return;
   string g[5]={"D","C","B","A","A+"};
   int h=FileOpen(InpJournalFile,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI,';');
   if(h==INVALID_HANDLE) return;
   if(FileSize(h)==0)
      FileWrite(h,"datetime","symbole","sens","grade","score","entree","sl","tp","rr","lot","checklist","veto");
   FileSeek(h,0,SEEK_END);
   FileWrite(h,TimeToString(TimeCurrent(),TIME_DATE|TIME_MINUTES),_Symbol,
             (d.bias>0?"BUY":(d.bias<0?"SELL":"-")),g[d.grade],d.score,
             DoubleToString(d.entry,_Digits),DoubleToString(d.sl,_Digits),
             DoubleToString(d.tp,_Digits),DoubleToString(d.rr,2),
             DoubleToString(d.lot,2),d.checklist,d.veto);
   FileClose(h);
  }

//+------------------------------------------------------------------+
//| Placement de l'ordre (MODE_PENDING uniquement)                   |
//+------------------------------------------------------------------+
void PlacePending(const SDrevmDecision &d)
  {
   if(SpreadPoints()>InpMaxSpreadPts)
     {
      Notify(StringFormat("Ordre annule — spread %.0f pts > %.0f",SpreadPoints(),InpMaxSpreadPts));
      return;
     }
   datetime exp=TimeCurrent()+InpPendingExpiryMin*60;
   bool ok=false;
   if(d.bias>0)
      ok=gTrade.BuyLimit(d.lot,d.entry,_Symbol,d.sl,d.tp,ORDER_TIME_SPECIFIED,exp,"DREVM_FTMO10K");
   else
      ok=gTrade.SellLimit(d.lot,d.entry,_Symbol,d.sl,d.tp,ORDER_TIME_SPECIFIED,exp,"DREVM_FTMO10K");

   if(ok) Notify("Ordre en attente pose — "+d.comment);
   else   Notify(StringFormat("Echec ordre (%d) %s",gTrade.ResultRetcode(),gTrade.ResultRetcodeDescription()));
  }

//+------------------------------------------------------------------+
//| Panneau                                                          |
//+------------------------------------------------------------------+
void Panel(const string line)
  {
   string mode=(InpMode==MODE_ALERT_ONLY)?"ALERT_ONLY":"PENDING";
   Comment(StringFormat("DREVM FTMO 10K | %s | %s\n%s\n%s\nSpread %.0f pts | News chargees: %d",
                        _Symbol,mode,gDrevm.RiskLine(),line,SpreadPoints(),ArraySize(gNews)));
  }

//+------------------------------------------------------------------+
//| OnInit                                                           |
//+------------------------------------------------------------------+
int OnInit(void)
  {
   if(Period()!=PERIOD_M5)
      Print("DREVM: attention — EA concu pour un graphique M5. TF actuel: ",EnumToString((ENUM_TIMEFRAMES)Period()));

   gTrade.SetExpertMagicNumber(InpMagic);
   gTrade.SetDeviationInPoints(20);
   gTrade.SetTypeFillingBySymbol(_Symbol);

   if(!gDrevm.Init(_Symbol,PERIOD_M5,PERIOD_M15,PERIOD_H4,
                   InpDailyLockPct,InpMaxDDPct,InpTargetPct,InpRiskPct,
                   InpMaxTradesDay,InpMaxLossStreak,
                   InpSessStartHour,InpSessEndHour,InpMode))
     {
      Print("DREVM: echec init du moteur.");
      return(INIT_FAILED);
     }

   gAtrHandle=iATR(_Symbol,PERIOD_M5,InpAtrPeriod);
   if(gAtrHandle==INVALID_HANDLE) return(INIT_FAILED);

   gRiskMoney=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPct/100.0;
   ParseNewsTimes();
   ArrayFree(gPos);

   PrintFormat("DREVM FTMO 10K initialise | risque/trade %.2f (%.2f%%) | lock jour %.1f%% | lock total %.1f%%",
               gRiskMoney,InpRiskPct,InpDailyLockPct,InpMaxDDPct);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   if(gAtrHandle!=INVALID_HANDLE) IndicatorRelease(gAtrHandle);
   gDrevm.Deinit();
   Comment("");
  }

//+------------------------------------------------------------------+
//| OnTick                                                           |
//+------------------------------------------------------------------+
void OnTick(void)
  {
   //--- 1) gestion de position : a chaque tick, toujours prioritaire
   ManagePositions();

   //--- 2) blackout news
   bool before=false;
   bool frozen=IsNewsFrozen(before);
   gDrevm.SetNewsFreeze(frozen);
   if(frozen)
     {
      CancelPendings();
      if(before && InpNewsFlatBefore) CloseAllPositions("blackout news");
      Panel("FREEZE NEWS +/- "+IntegerToString(InpNewsFreezeMin)+" min — aucune action.");
      return;
     }

   //--- 3) evaluation du signal (uniquement sur cloture M5)
   SDrevmDecision d;
   if(!gDrevm.Evaluate(d)) return;

   Panel(d.comment);

   if(d.veto!="")   { JournalWrite(d); return; }
   if(!d.actionable){ JournalWrite(d); return; }

   //--- anti-doublon : un signal max par barre
   datetime bar=iTime(_Symbol,PERIOD_M5,0);
   if(bar==gLastSignalBar) return;
   gLastSignalBar=bar;

   JournalWrite(d);
   Notify("SETUP "+d.comment);

   if(InpMode==MODE_PENDING) PlacePending(d);
  }

//+------------------------------------------------------------------+
//| OnTradeTransaction — comptage des trades et de la serie          |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   if(trans.type!=TRADE_TRANSACTION_DEAL_ADD) return;
   if(!HistoryDealSelect(trans.deal)) return;
   if(HistoryDealGetString(trans.deal,DEAL_SYMBOL)!=_Symbol) return;
   if(HistoryDealGetInteger(trans.deal,DEAL_ENTRY)!=DEAL_ENTRY_OUT) return;

   ulong posId=(ulong)HistoryDealGetInteger(trans.deal,DEAL_POSITION_ID);
   if(PositionSelectByTicket(posId)) return;   // fermeture partielle : on ignore

   //--- agregation du P&L de la position par DEAL_POSITION_ID
   double pnl=0.0;
   if(HistorySelectByPosition(posId))
      for(int i=HistoryDealsTotal()-1;i>=0;i--)
        {
         ulong dt=HistoryDealGetTicket(i);
         if(dt==0) continue;
         pnl+=HistoryDealGetDouble(dt,DEAL_PROFIT)
             +HistoryDealGetDouble(dt,DEAL_SWAP)
             +HistoryDealGetDouble(dt,DEAL_COMMISSION);
        }

   double r=(gRiskMoney>0.0)?pnl/gRiskMoney:0.0;
   gDrevm.OnTradeClosed(r);
   Notify(StringFormat("Position %I64u fermee | %.2f USD | %.2fR",posId,pnl,r));
  }
//+------------------------------------------------------------------+
