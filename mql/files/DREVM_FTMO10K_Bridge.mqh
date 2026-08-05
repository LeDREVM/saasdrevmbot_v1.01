//+------------------------------------------------------------------+
//|                                        DREVM_FTMO10K_Bridge.mqh  |
//|                     DREVM / GoldXrodgers — Negus Dja             |
//|                                                                  |
//|  Cable CDrevmBreakManip (sweep -> MSS) sur un compte FTMO 10K.   |
//|  Produit UNE decision unique : DREVM_Evaluate() -> SDrevmDecision|
//|                                                                  |
//|  ARCHITECTURE DU SCORE (conforme a l'audit quantitatif) :        |
//|   - 5 criteres de confluence, 1 point chacun (gMaxScore = 5).    |
//|   - MSS/BOS n'est PAS un point : c'est un GATE. Pas de MSS       |
//|     confirme en cloture => grade D, point final.                 |
//|   - R/R < 2 n'est PAS un point : c'est un VETO (grade D).        |
//|   - Aucun point "gratuit" (toujours vrai par construction).      |
//|   - FVG/OB comptent uniquement si le prix est confirme DANS la   |
//|     zone (prefixe in_zone).                                      |
//|                                                                  |
//|  GARDE-FOUS FTMO 10K (buffers INTERNES, plus stricts que FTMO) : |
//|   - Perte jour        : lock a 3.5%  = 350 USD  (FTMO : 5%)      |
//|   - Drawdown total    : lock a 7.0%  = 700 USD  (FTMO : 10%)     |
//|   - Objectif phase    : stop a 8.0%  = 800 USD  (FTMO : 10%)     |
//|   - Risque par trade  : 0.5% par defaut = 50 USD                 |
//|   - Freeze news +/- 4 min (pilote par FTMO_FundedNewsGuard.mqh)  |
//|                                                                  |
//|  Mode par defaut : MODE_ALERT_ONLY. Aucune execution ici.        |
//+------------------------------------------------------------------+
#ifndef __DREVM_FTMO10K_BRIDGE_MQH__
#define __DREVM_FTMO10K_BRIDGE_MQH__

#property copyright "DREVM / Negus Dja"
#property version   "1.00"

#include "DREVM_BreakManipulation.mqh"

//+------------------------------------------------------------------+
//| Enumerations                                                     |
//+------------------------------------------------------------------+
enum ENUM_DREVM_MODE
  {
   MODE_ALERT_ONLY = 0,   // alerte + journal, aucune execution
   MODE_PENDING    = 1    // ordre en attente (phase challenge uniquement)
  };

enum ENUM_DREVM_GRADE
  {
   GRADE_D = 0,
   GRADE_C = 1,
   GRADE_B = 2,
   GRADE_A = 3,
   GRADE_AP= 4
  };

//+------------------------------------------------------------------+
//| Decision retournee a l'EA                                        |
//+------------------------------------------------------------------+
struct SDrevmDecision
  {
   bool              actionable;    // true = grade >= B, tous gates passes
   ENUM_DREVM_GRADE  grade;
   int               score;         // 0..5
   int               bias;          // +1 BUY / -1 SELL / 0
   double            entry, sl, tp, rr;
   double            lot;
   bool              in_zone_fvg;
   string            veto;          // raison du blocage (vide si aucun)
   string            checklist;     // detail des 5 criteres
   string            comment;
  };

//+------------------------------------------------------------------+
//| Moteur FTMO 10K                                                  |
//+------------------------------------------------------------------+
class CDrevmFTMO10K
  {
private:
   string            m_sym;
   ENUM_TIMEFRAMES   m_tfEntry;     // M5
   ENUM_TIMEFRAMES   m_tfStruct;    // M15
   ENUM_TIMEFRAMES   m_tfBias;      // H4

   CDrevmBreakManip  m_bm;

   // risque compte
   double            m_initialBalance;
   double            m_dayStartBalance;
   datetime          m_dayAnchor;
   double            m_dailyLockPct;
   double            m_maxDDPct;
   double            m_targetPct;
   double            m_riskPct;
   int               m_maxTradesDay;
   int               m_tradesToday;
   int               m_lossStreak;
   int               m_maxLossStreak;

   // filtres
   bool              m_newsFreeze;
   int               m_sessStartHour;   // heure serveur (GMT+3 ete)
   int               m_sessEndHour;
   ENUM_DREVM_MODE   m_mode;

   // handles
   int               m_hEmaBiasFast, m_hEmaBiasSlow;

   double            EmaVal(const int handle,const int shift);
   int               BiasHTF(bool &ready);           // +1 / -1 / 0 ; ready=false si buffer H4 vide
   bool              FibSniperOK(const SDrevmSignal &s,const int bias);
   bool              InZoneFVG(const SDrevmSignal &s);
   bool              MomentumOK(const int bias);
   bool              StructureAligned(const int bias);
   void              RefreshDay(void);
   string            RiskVeto(void);
   double            LotForRisk(const double entry,const double sl);

public:
                     CDrevmFTMO10K(void);
                    ~CDrevmFTMO10K(void);

   bool              Init(const string symbol="",
                          const ENUM_TIMEFRAMES tfEntry=PERIOD_M5,
                          const ENUM_TIMEFRAMES tfStruct=PERIOD_M15,
                          const ENUM_TIMEFRAMES tfBias=PERIOD_H4,
                          const double dailyLockPct=3.5,
                          const double maxDDPct=7.0,
                          const double targetPct=8.0,
                          const double riskPct=0.5,
                          const int maxTradesDay=3,
                          const int maxLossStreak=2,
                          const int sessStartHour=15,   // 15h GMT+3 = 08h NY (ete)
                          const int sessEndHour=22,
                          const ENUM_DREVM_MODE mode=MODE_ALERT_ONLY);
   void              Deinit(void);

   void              SetNewsFreeze(const bool v) { m_newsFreeze=v; }
   void              OnTradeClosed(const double resultR);
   ENUM_DREVM_MODE   Mode(void) const { return m_mode; }

   //--- coeur : a appeler dans OnTick(), ne calcule que sur barre close
   bool              Evaluate(SDrevmDecision &out);

   string            RiskLine(void);
  };

//+------------------------------------------------------------------+
CDrevmFTMO10K::CDrevmFTMO10K(void)
  {
   m_hEmaBiasFast=INVALID_HANDLE; m_hEmaBiasSlow=INVALID_HANDLE;
   m_newsFreeze=false; m_tradesToday=0; m_lossStreak=0; m_dayAnchor=0;
  }
//+------------------------------------------------------------------+
CDrevmFTMO10K::~CDrevmFTMO10K(void) { Deinit(); }
//+------------------------------------------------------------------+
void CDrevmFTMO10K::Deinit(void)
  {
   if(m_hEmaBiasFast!=INVALID_HANDLE) { IndicatorRelease(m_hEmaBiasFast); m_hEmaBiasFast=INVALID_HANDLE; }
   if(m_hEmaBiasSlow!=INVALID_HANDLE) { IndicatorRelease(m_hEmaBiasSlow); m_hEmaBiasSlow=INVALID_HANDLE; }
   m_bm.Deinit();
  }
//+------------------------------------------------------------------+
bool CDrevmFTMO10K::Init(const string symbol,const ENUM_TIMEFRAMES tfEntry,
                         const ENUM_TIMEFRAMES tfStruct,const ENUM_TIMEFRAMES tfBias,
                         const double dailyLockPct,const double maxDDPct,
                         const double targetPct,const double riskPct,
                         const int maxTradesDay,const int maxLossStreak,
                         const int sessStartHour,const int sessEndHour,
                         const ENUM_DREVM_MODE mode)
  {
   m_sym          = (symbol=="" ? _Symbol : symbol);
   m_tfEntry      = tfEntry;
   m_tfStruct     = tfStruct;
   m_tfBias       = tfBias;
   m_dailyLockPct = dailyLockPct;
   m_maxDDPct     = maxDDPct;
   m_targetPct    = targetPct;
   m_riskPct      = riskPct;
   m_maxTradesDay = maxTradesDay;
   m_maxLossStreak= maxLossStreak;
   m_sessStartHour= sessStartHour;
   m_sessEndHour  = sessEndHour;
   m_mode         = mode;

   if(!m_bm.Init(m_sym,m_tfEntry,5,2,100,12,0.30,0.0,20,0.25,2.0,14))
      return(false);

   m_hEmaBiasFast = iMA(m_sym,m_tfBias,50,0,MODE_EMA,PRICE_CLOSE);
   m_hEmaBiasSlow = iMA(m_sym,m_tfBias,200,0,MODE_EMA,PRICE_CLOSE);
   if(m_hEmaBiasFast==INVALID_HANDLE || m_hEmaBiasSlow==INVALID_HANDLE)
     {
      Print("DREVM FTMO10K: echec handles EMA H4");
      return(false);
     }

   //--- ancrage du capital de reference (survit au restart)
   string gv = "DREVM_FTMO10K_INIT_"+IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN));
   if(GlobalVariableCheck(gv))
      m_initialBalance = GlobalVariableGet(gv);
   else
     {
      m_initialBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      GlobalVariableSet(gv,m_initialBalance);
     }
   RefreshDay();
   return(true);
  }
//+------------------------------------------------------------------+
void CDrevmFTMO10K::RefreshDay(void)
  {
   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   dt.hour=0; dt.min=0; dt.sec=0;
   datetime d0 = StructToTime(dt);
   if(d0!=m_dayAnchor)
     {
      m_dayAnchor       = d0;
      m_dayStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
      m_tradesToday     = 0;
      string gv="DREVM_FTMO10K_DAY_"+IntegerToString((int)AccountInfoInteger(ACCOUNT_LOGIN));
      GlobalVariableSet(gv,m_dayStartBalance);
     }
  }
//+------------------------------------------------------------------+
double CDrevmFTMO10K::EmaVal(const int handle,const int shift)
  {
   double b[]; ArraySetAsSeries(b,true);
   if(CopyBuffer(handle,0,shift,1,b)<=0) return(0.0);
   return(b[0]);
  }
//+------------------------------------------------------------------+
//| Biais HTF : EMA50 vs EMA200 H4 + position du prix                |
//+------------------------------------------------------------------+
int CDrevmFTMO10K::BiasHTF(bool &ready)
  {
   ready=true;
   double f=EmaVal(m_hEmaBiasFast,1), s=EmaVal(m_hEmaBiasSlow,1);
   //--- buffer H4 pas encore synchronise (frequent au 1er tick / changement de
   //--- symbole) : sans ce test, un simple defaut de donnees ferait perdre un
   //--- point de confluence en silence.
   if(f<=0.0 || s<=0.0) { ready=false; return(0); }
   double c=iClose(m_sym,m_tfBias,1);
   if(f>s && c>f) return(1);
   if(f<s && c<f) return(-1);
   return(0);
  }
//+------------------------------------------------------------------+
//| Structure M15 alignee : dernier swing majeur dans le sens        |
//+------------------------------------------------------------------+
bool CDrevmFTMO10K::StructureAligned(const int bias)
  {
   double c1=iClose(m_sym,m_tfStruct,1);
   double e50=iClose(m_sym,m_tfStruct,1); // fallback si pas d'EMA M15
   int hi=iHighest(m_sym,m_tfStruct,MODE_HIGH,20,1);
   int lo=iLowest(m_sym,m_tfStruct,MODE_LOW,20,1);
   double hh=iHigh(m_sym,m_tfStruct,hi), ll=iLow(m_sym,m_tfStruct,lo);
   double mid=0.5*(hh+ll);
   if(bias>0) return(c1>mid && lo>hi);   // dernier extreme = un high => impulsion haussiere
   if(bias<0) return(c1<mid && hi>lo);
   return(false);
  }
//+------------------------------------------------------------------+
//| Zone Fibonacci sniper : entree entre 61.8% et 95% de la jambe    |
//+------------------------------------------------------------------+
bool CDrevmFTMO10K::FibSniperOK(const SDrevmSignal &s,const int bias)
  {
   SDrevmBreak b=m_bm.Break();
   double leg=b.impulse_top-b.impulse_bottom;
   if(leg<=0.0) return(false);
   double r = (bias<0) ? (s.entry-b.impulse_bottom)/leg
                       : (b.impulse_top-s.entry)/leg;
   return(r>=0.618 && r<=0.95);
  }
//+------------------------------------------------------------------+
//| FVG confirmee ET prix deja revenu dans la zone (in_zone)         |
//+------------------------------------------------------------------+
bool CDrevmFTMO10K::InZoneFVG(const SDrevmSignal &s)
  {
   if(!s.has_fvg) return(false);
   double c1=iClose(m_sym,m_tfEntry,1);
   double tol=0.15*MathAbs(s.entry-s.sl);
   return(MathAbs(c1-s.entry)<=tol);
  }
//+------------------------------------------------------------------+
//| Momentum : la bougie de MSS cloture dans le sens, corps > 50%    |
//+------------------------------------------------------------------+
bool CDrevmFTMO10K::MomentumOK(const int bias)
  {
   double o=iOpen(m_sym,m_tfEntry,1), c=iClose(m_sym,m_tfEntry,1);
   double h=iHigh(m_sym,m_tfEntry,1), l=iLow(m_sym,m_tfEntry,1);
   double rng=h-l; if(rng<=0.0) return(false);
   double body=MathAbs(c-o)/rng;
   if(body<0.50) return(false);
   return((bias>0 && c>o) || (bias<0 && c<o));
  }
//+------------------------------------------------------------------+
//| Veto risque compte — ordre de priorite = du plus grave au moins  |
//+------------------------------------------------------------------+
string CDrevmFTMO10K::RiskVeto(void)
  {
   double eq  = AccountInfoDouble(ACCOUNT_EQUITY);
   double ddT = (m_initialBalance-eq)/m_initialBalance*100.0;
   double ddD = (m_dayStartBalance-eq)/m_dayStartBalance*100.0;
   double gain= (eq-m_initialBalance)/m_initialBalance*100.0;

   if(ddT>=m_maxDDPct)
      return(StringFormat("DRAWDOWN TOTAL %.2f%% >= %.2f%% (lock interne)",ddT,m_maxDDPct));
   if(ddD>=m_dailyLockPct)
      return(StringFormat("PERTE JOUR %.2f%% >= %.2f%% (lock interne)",ddD,m_dailyLockPct));
   if(gain>=m_targetPct)
      return(StringFormat("OBJECTIF %.2f%% atteint — arret des prises de risque",gain));
   if(m_newsFreeze)
      return("FREEZE NEWS +/- 4 min");
   if(m_tradesToday>=m_maxTradesDay)
      return(StringFormat("QUOTA JOUR atteint (%d trades)",m_tradesToday));
   if(m_lossStreak>=m_maxLossStreak)
      return(StringFormat("SERIE DE %d PERTES — pause obligatoire",m_lossStreak));

   MqlDateTime dt; TimeToStruct(TimeCurrent(),dt);
   if(dt.day_of_week==0 || dt.day_of_week==6) return("HORS SEMAINE");
   if(dt.hour<m_sessStartHour || dt.hour>=m_sessEndHour)
      return(StringFormat("HORS SESSION NY (%02d:00-%02d:00 serveur)",m_sessStartHour,m_sessEndHour));
   return("");
  }
//+------------------------------------------------------------------+
//| Lot = risque% du solde initial, borne par le budget jour restant |
//+------------------------------------------------------------------+
double CDrevmFTMO10K::LotForRisk(const double entry,const double sl)
  {
   double dist=MathAbs(entry-sl);
   if(dist<=0.0) return(0.0);

   double tickVal =SymbolInfoDouble(m_sym,SYMBOL_TRADE_TICK_VALUE);
   double tickSize=SymbolInfoDouble(m_sym,SYMBOL_TRADE_TICK_SIZE);
   if(tickVal<=0.0 || tickSize<=0.0) return(0.0);

   double riskMoney = m_initialBalance*m_riskPct/100.0;

   //--- ne jamais engager plus que ce qui reste avant le lock jour
   double eq        = AccountInfoDouble(ACCOUNT_EQUITY);
   double dayFloor  = m_dayStartBalance*(1.0-m_dailyLockPct/100.0);
   double remaining = eq-dayFloor;
   if(remaining<=0.0) return(0.0);
   riskMoney = MathMin(riskMoney,remaining*0.90);

   double lossPerLot=(dist/tickSize)*tickVal;
   if(lossPerLot<=0.0) return(0.0);

   double lot=riskMoney/lossPerLot;
   double step=SymbolInfoDouble(m_sym,SYMBOL_VOLUME_STEP);
   double vmin=SymbolInfoDouble(m_sym,SYMBOL_VOLUME_MIN);
   double vmax=SymbolInfoDouble(m_sym,SYMBOL_VOLUME_MAX);
   lot=MathFloor(lot/step)*step;
   if(lot<vmin) return(0.0);          // risque trop faible pour le lot minimum => on ne force pas
   if(lot>vmax) lot=vmax;
   return(NormalizeDouble(lot,2));
  }
//+------------------------------------------------------------------+
void CDrevmFTMO10K::OnTradeClosed(const double resultR)
  {
   m_tradesToday++;
   if(resultR<0.0) m_lossStreak++;
   else            m_lossStreak=0;
  }
//+------------------------------------------------------------------+
string CDrevmFTMO10K::RiskLine(void)
  {
   double eq=AccountInfoDouble(ACCOUNT_EQUITY);
   return(StringFormat("Equity %.2f | jour %.2f%% (lock %.1f%%) | total %.2f%% (lock %.1f%%) | trades %d/%d",
                       eq,
                       (eq-m_dayStartBalance)/m_dayStartBalance*100.0, m_dailyLockPct,
                       (eq-m_initialBalance)/m_initialBalance*100.0,   m_maxDDPct,
                       m_tradesToday,m_maxTradesDay));
  }
//+------------------------------------------------------------------+
//| EVALUATION COMPLETE                                              |
//+------------------------------------------------------------------+
bool CDrevmFTMO10K::Evaluate(SDrevmDecision &out)
  {
   ZeroMemory(out);
   out.grade=GRADE_D;

   if(!m_bm.Update()) return(false);   // invariant : une seule passe par barre close
   RefreshDay();

   //--- GATE 0 : risque compte (prioritaire sur toute analyse)
   out.veto=RiskVeto();
   if(out.veto!="") { out.comment="Aucun setup expose — "+out.veto; return(true); }

   //--- GATE 1 : MSS/BOS confirme en cloture (pas un point, un gate)
   if(m_bm.Phase()!=DREVM_BREAK)
     {
      out.comment="Pas de MSS confirme en cloture — attente.";
      return(true);
     }

   SDrevmSignal s=m_bm.Signal();
   if(!s.ready) { out.comment="Signal incomplet."; return(true); }

   int bias=s.bias;
   out.bias=bias; out.entry=s.entry; out.sl=s.sl; out.tp=s.tp; out.rr=s.rr;

   //--- GATE 2 : veto R/R (grade D, jamais un simple malus)
   if(s.veto_rr)
     {
      out.veto=StringFormat("R/R %.2f < 2.00",s.rr);
      out.comment="Grade D — veto R/R.";
      return(true);
     }

   //--- GATE 3 : contre-tendance HTF interdite
   bool htfReady=true;
   int htf=BiasHTF(htfReady);
   if(!htfReady)
     {
      out.comment="Donnees H4 indisponibles — evaluation reportee.";
      return(true);
     }
   if(htf!=0 && htf!=bias)
     {
      out.veto="Contre-tendance H4";
      out.comment="Grade D — signal oppose au biais H4.";
      return(true);
     }

   //--- 5 criteres de confluence, 1 point chacun
   bool c1=(htf==bias);                 // biais H4 aligne
   bool c2=StructureAligned(bias);      // structure M15 coherente
   bool c3=FibSniperOK(s,bias);         // zone sniper 61.8-95%
   bool c4=InZoneFVG(s);                // FVG confirmee ET prix dans la zone
   bool c5=MomentumOK(bias);            // corps de la bougie MSS

   out.score=(c1?1:0)+(c2?1:0)+(c3?1:0)+(c4?1:0)+(c5?1:0);
   out.in_zone_fvg=c4;
   out.checklist=StringFormat("H4:%s M15:%s FIB:%s in_zone_FVG:%s MOM:%s",
                              c1?"OK":"--",c2?"OK":"--",c3?"OK":"--",
                              c4?"OK":"--",c5?"OK":"--");

   if(out.score>=5)      out.grade=GRADE_AP;
   else if(out.score==4) out.grade=GRADE_A;
   else if(out.score==3) out.grade=GRADE_B;
   else if(out.score==2) out.grade=GRADE_C;
   else                  out.grade=GRADE_D;

   //--- lot uniquement si actionnable
   if(out.grade>=GRADE_B)
     {
      out.lot=LotForRisk(out.entry,out.sl);
      if(out.lot<=0.0)
        {
         out.veto="Lot calcule nul (budget jour insuffisant ou lot min inatteignable)";
         out.actionable=false;
        }
      else out.actionable=true;
     }

   string g[5]={"D","C","B","A","A+"};
   out.comment=StringFormat("%s | Grade %s (%d/5) | E %.5f SL %.5f TP %.5f | R/R %.2f | lot %.2f | %s",
                            (bias>0?"BUY":"SELL"),g[out.grade],out.score,
                            out.entry,out.sl,out.tp,out.rr,out.lot,out.checklist);
   return(true);
  }

//+------------------------------------------------------------------+
//| INTEGRATION DANS FTMO_FibRSI_Scoring_EA.mq5                      |
//|                                                                  |
//| 1) En tete du fichier, apres les autres includes :               |
//|      #include "DREVM_FTMO10K_Bridge.mqh"                         |
//|      CDrevmFTMO10K gDrevm;                                       |
//|                                                                  |
//| 2) OnInit() :                                                    |
//|      if(!gDrevm.Init(_Symbol,PERIOD_M5,PERIOD_M15,PERIOD_H4,     |
//|                      3.5, 7.0, 8.0, 0.5, 3, 2, 15, 22,           |
//|                      MODE_ALERT_ONLY)) return(INIT_FAILED);      |
//|                                                                  |
//| 3) OnDeinit() : gDrevm.Deinit();                                 |
//|                                                                  |
//| 4) OnTick() — remplacer l'ancien bloc de scoring par :           |
//|      gDrevm.SetNewsFreeze(NewsGuard_IsFrozen());                 |
//|      SDrevmDecision d;                                           |
//|      if(!gDrevm.Evaluate(d)) return;   // barre non cloturee     |
//|      Comment(gDrevm.RiskLine()+"\n"+d.comment);                  |
//|      if(!d.actionable) return;                                   |
//|      if(gDrevm.Mode()==MODE_ALERT_ONLY)                          |
//|        { SendNotification(_Symbol+" "+d.comment); return; }      |
//|      // MODE_PENDING : poser le limit a d.entry, SL d.sl, TP d.tp|
//|                                                                  |
//| 5) OnTradeTransaction() — a la fermeture d'une position :        |
//|      gDrevm.OnTradeClosed(resultat_en_R);                        |
//|                                                                  |
//| RAPPEL : la gestion de position (partiel 50% a 1R + breakeven +  |
//| trailing ATR) reste le seul module valide statistiquement.       |
//| Elle doit tourner independamment de ce moteur de signal.         |
//+------------------------------------------------------------------+
#endif // __DREVM_FTMO10K_BRIDGE_MQH__
