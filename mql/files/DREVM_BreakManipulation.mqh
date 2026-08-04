//+------------------------------------------------------------------+
//|                                     DREVM_BreakManipulation.mqh  |
//|                     DREVM / GoldXrodgers — Negus Dja             |
//|                                                                  |
//|  Sequence ICT/Wyckoff : MANIPULATION (sweep de liquidite)        |
//|                      -> BREAK (MSS/BOS confirme a la cloture)    |
//|                      -> zone d'entree (FVG ou fib sniper)        |
//|                                                                  |
//|  INVARIANTS DREVM (ne pas modifier) :                            |
//|   - Evaluation UNIQUEMENT sur barre cloturee (no-repaint).       |
//|     Aucune lecture du shift 0 (bougie en formation).             |
//|   - Aucun lookahead : un swing fractal k n'est considere connu   |
//|     qu'a partir de k barres apres sa formation (shift >= k+2).   |
//|   - R/R < MinRR => veto (grade D), pas un simple malus.          |
//|   - Une entree contre-tendance sans MSS confirme n'est jamais    |
//|     validee par ce module.                                       |
//|   - Aucune metrique de performance / winrate produite ici.       |
//+------------------------------------------------------------------+
#ifndef __DREVM_BREAK_MANIPULATION_MQH__
#define __DREVM_BREAK_MANIPULATION_MQH__

#property copyright "DREVM / Negus Dja"
#property version   "1.00"

//+------------------------------------------------------------------+
//| Enumerations                                                     |
//+------------------------------------------------------------------+
enum ENUM_DREVM_PHASE
  {
   DREVM_IDLE          = 0,   // rien en cours, on scanne les sweeps
   DREVM_MANIPULATION  = 1,   // sweep valide, on attend le break
   DREVM_BREAK         = 2,   // MSS/BOS confirme -> signal disponible
   DREVM_INVALIDATED   = 3    // sweep invalide ou expire
  };

//+------------------------------------------------------------------+
//| Structures                                                       |
//+------------------------------------------------------------------+
struct SDrevmSwing
  {
   bool              valid;
   double            price;
   int               shift;      // shift au moment de la detection
   datetime          time;
  };

struct SDrevmManipulation
  {
   bool              active;
   int               bias;         // +1 = sweep des lows (biais BUY) / -1 = sweep des highs (biais SELL)
   double            extreme;      // high du sweep (SELL) ou low du sweep (BUY)
   double            swept_level;  // niveau du swing balaye
   double            close_px;     // cloture de la bougie de sweep
   datetime          time;
   double            wick_atr;     // amplitude de la meche / ATR
   double            vol_ratio;    // volume du sweep / mediane des N precedents
   int               shift;        // shift courant de la bougie de sweep (s'incremente)
  };

struct SDrevmBreak
  {
   bool              confirmed;
   int               bias;
   double            level;        // niveau structurel casse a la cloture
   datetime          time;
   double            impulse_top;
   double            impulse_bottom;
  };

struct SDrevmSignal
  {
   bool              ready;
   int               bias;         // +1 BUY / -1 SELL
   double            entry;
   double            sl;
   double            tp;
   double            rr;
   bool              veto_rr;      // true => grade D, ne pas executer
   bool              has_fvg;      // entree adossee a une FVG confirmee
   string            comment;
  };

//+------------------------------------------------------------------+
//| Classe principale                                                |
//+------------------------------------------------------------------+
class CDrevmBreakManip
  {
private:
   string            m_sym;
   ENUM_TIMEFRAMES   m_tf;

   // parametres
   int               m_k;            // fractal majeur (swing de liquidite)
   int               m_mk;           // fractal mineur (structure interne pour le MSS)
   int               m_lookback;     // fenetre max de recherche du swing balaye
   int               m_maxBars;      // barres max entre manipulation et break
   double            m_minWickATR;   // rejet minimal de la meche en ATR
   double            m_minVolRatio;  // 0 = filtre volume desactive
   int               m_volRef;       // barres de reference pour la mediane de volume
   double            m_slBufATR;     // buffer SL au-dela de l'extreme, en ATR
   double            m_minRR;        // seuil de veto R/R (DREVM = 2.0)
   int               m_atrPeriod;

   // etat
   int               m_hATR;
   datetime          m_lastBar;
   ENUM_DREVM_PHASE  m_phase;
   SDrevmManipulation m_manip;
   SDrevmBreak       m_break;
   SDrevmSignal      m_signal;

   //--- utilitaires
   double            ATR(const int shift);
   bool              FindSwingHigh(const int startShift,const int maxShift,const int k,double &price,int &shiftOut);
   bool              FindSwingLow(const int startShift,const int maxShift,const int k,double &price,int &shiftOut);
   double            VolRatio(const int shift);
   bool              DetectManipulation(void);
   bool              DetectBreak(void);
   void              BuildSignal(void);
   void              Reset(const ENUM_DREVM_PHASE ph);

public:
                     CDrevmBreakManip(void);
                    ~CDrevmBreakManip(void);

   bool              Init(const string symbol,const ENUM_TIMEFRAMES tf,
                          const int swingK=5,const int minorK=2,
                          const int lookbackSwing=100,const int maxBarsToBreak=12,
                          const double minWickATR=0.30,const double minVolRatio=0.0,
                          const int volRefBars=20,const double slBufferATR=0.25,
                          const double minRR=2.0,const int atrPeriod=14);
   void              Deinit(void);

   //--- a appeler dans OnTick() : ne traite QUE les nouvelles barres cloturees
   bool              Update(void);

   //--- accesseurs
   ENUM_DREVM_PHASE  Phase(void)      const { return m_phase;  }
   SDrevmManipulation Manipulation(void) const { return m_manip;  }
   SDrevmBreak       Break(void)      const { return m_break;   }
   SDrevmSignal      Signal(void)     const { return m_signal;  }
   string            PhaseText(void)  const;
   string            Describe(void)   const;
  };

//+------------------------------------------------------------------+
CDrevmBreakManip::CDrevmBreakManip(void)
  {
   m_sym=""; m_tf=PERIOD_CURRENT; m_hATR=INVALID_HANDLE;
   m_lastBar=0; m_phase=DREVM_IDLE;
   ZeroMemory(m_manip); ZeroMemory(m_break); ZeroMemory(m_signal);
  }
//+------------------------------------------------------------------+
CDrevmBreakManip::~CDrevmBreakManip(void) { Deinit(); }
//+------------------------------------------------------------------+
void CDrevmBreakManip::Deinit(void)
  {
   if(m_hATR!=INVALID_HANDLE) { IndicatorRelease(m_hATR); m_hATR=INVALID_HANDLE; }
  }
//+------------------------------------------------------------------+
bool CDrevmBreakManip::Init(const string symbol,const ENUM_TIMEFRAMES tf,
                            const int swingK,const int minorK,
                            const int lookbackSwing,const int maxBarsToBreak,
                            const double minWickATR,const double minVolRatio,
                            const int volRefBars,const double slBufferATR,
                            const double minRR,const int atrPeriod)
  {
   m_sym        = (symbol=="" ? _Symbol : symbol);
   m_tf         = (tf==PERIOD_CURRENT ? (ENUM_TIMEFRAMES)Period() : tf);
   m_k          = MathMax(2,swingK);
   m_mk         = MathMax(1,minorK);
   m_lookback   = MathMax(20,lookbackSwing);
   m_maxBars    = MathMax(3,maxBarsToBreak);
   m_minWickATR = MathMax(0.0,minWickATR);
   m_minVolRatio= MathMax(0.0,minVolRatio);
   m_volRef     = MathMax(5,volRefBars);
   m_slBufATR   = MathMax(0.0,slBufferATR);
   m_minRR      = MathMax(1.0,minRR);
   m_atrPeriod  = MathMax(2,atrPeriod);

   m_hATR = iATR(m_sym,m_tf,m_atrPeriod);
   if(m_hATR==INVALID_HANDLE)
     {
      Print("DREVM_BreakManip: echec handle ATR sur ",m_sym);
      return(false);
     }
   m_lastBar = 0;
   Reset(DREVM_IDLE);
   return(true);
  }
//+------------------------------------------------------------------+
void CDrevmBreakManip::Reset(const ENUM_DREVM_PHASE ph)
  {
   ZeroMemory(m_manip); ZeroMemory(m_break); ZeroMemory(m_signal);
   m_phase = ph;
  }
//+------------------------------------------------------------------+
double CDrevmBreakManip::ATR(const int shift)
  {
   double buf[];
   ArraySetAsSeries(buf,true);
   if(CopyBuffer(m_hATR,0,shift,1,buf)<=0) return(0.0);
   return(buf[0]);
  }
//+------------------------------------------------------------------+
//| Swing high fractal CONFIRME. startShift doit valoir au moins     |
//| k+2 pour garantir que le swing etait connu avant la barre 1.     |
//+------------------------------------------------------------------+
bool CDrevmBreakManip::FindSwingHigh(const int startShift,const int maxShift,const int k,
                                     double &price,int &shiftOut)
  {
   int total = Bars(m_sym,m_tf);
   int last  = MathMin(maxShift,total-k-2);
   for(int s=MathMax(startShift,k+2); s<=last; s++)
     {
      double hp = iHigh(m_sym,m_tf,s);
      bool ok = true;
      for(int j=1; j<=k; j++)
        {
         if(iHigh(m_sym,m_tf,s-j) >= hp || iHigh(m_sym,m_tf,s+j) > hp) { ok=false; break; }
        }
      if(ok) { price=hp; shiftOut=s; return(true); }
     }
   return(false);
  }
//+------------------------------------------------------------------+
bool CDrevmBreakManip::FindSwingLow(const int startShift,const int maxShift,const int k,
                                    double &price,int &shiftOut)
  {
   int total = Bars(m_sym,m_tf);
   int last  = MathMin(maxShift,total-k-2);
   for(int s=MathMax(startShift,k+2); s<=last; s++)
     {
      double lp = iLow(m_sym,m_tf,s);
      bool ok = true;
      for(int j=1; j<=k; j++)
        {
         if(iLow(m_sym,m_tf,s-j) <= lp || iLow(m_sym,m_tf,s+j) < lp) { ok=false; break; }
        }
      if(ok) { price=lp; shiftOut=s; return(true); }
     }
   return(false);
  }
//+------------------------------------------------------------------+
//| Volume relatif : tick volume(shift) / mediane des m_volRef       |
//| bougies PRECEDENTES (mesure locale, insensible a la session).    |
//+------------------------------------------------------------------+
double CDrevmBreakManip::VolRatio(const int shift)
  {
   double v[];
   ArrayResize(v,m_volRef);
   for(int i=0;i<m_volRef;i++) v[i]=(double)iVolume(m_sym,m_tf,shift+1+i);
   ArraySort(v);
   double med = (m_volRef%2==1) ? v[m_volRef/2]
                                : 0.5*(v[m_volRef/2-1]+v[m_volRef/2]);
   if(med<=0.0) return(0.0);
   return((double)iVolume(m_sym,m_tf,shift)/med);
  }
//+------------------------------------------------------------------+
//| MANIPULATION : la barre 1 depasse un swing confirme mais CLOTURE |
//| a l'interieur. La liquidite a ete prise puis rejetee.            |
//+------------------------------------------------------------------+
bool CDrevmBreakManip::DetectManipulation(void)
  {
   double atr = ATR(1);
   if(atr<=0.0) return(false);

   double h1=iHigh(m_sym,m_tf,1), l1=iLow(m_sym,m_tf,1), c1=iClose(m_sym,m_tf,1);
   double px; int sh;

   //--- sweep des highs -> biais SELL
   if(FindSwingHigh(m_k+2,m_lookback,m_k,px,sh))
     {
      if(h1>px && c1<px)
        {
         double wick=(h1-c1)/atr;
         if(wick>=m_minWickATR)
           {
            double vr=VolRatio(1);
            if(m_minVolRatio<=0.0 || vr>=m_minVolRatio)
              {
               m_manip.active      = true;
               m_manip.bias        = -1;
               m_manip.extreme     = h1;
               m_manip.swept_level = px;
               m_manip.close_px    = c1;
               m_manip.time        = iTime(m_sym,m_tf,1);
               m_manip.wick_atr    = wick;
               m_manip.vol_ratio   = vr;
               m_manip.shift       = 1;
               return(true);
              }
           }
        }
     }

   //--- sweep des lows -> biais BUY
   if(FindSwingLow(m_k+2,m_lookback,m_k,px,sh))
     {
      if(l1<px && c1>px)
        {
         double wick=(c1-l1)/atr;
         if(wick>=m_minWickATR)
           {
            double vr=VolRatio(1);
            if(m_minVolRatio<=0.0 || vr>=m_minVolRatio)
              {
               m_manip.active      = true;
               m_manip.bias        = 1;
               m_manip.extreme     = l1;
               m_manip.swept_level = px;
               m_manip.close_px    = c1;
               m_manip.time        = iTime(m_sym,m_tf,1);
               m_manip.wick_atr    = wick;
               m_manip.vol_ratio   = vr;
               m_manip.shift       = 1;
               return(true);
              }
           }
        }
     }
   return(false);
  }
//+------------------------------------------------------------------+
//| BREAK (MSS/BOS) : cloture au-dela du dernier swing mineur        |
//| forme APRES la manipulation, dans le sens du biais.              |
//+------------------------------------------------------------------+
bool CDrevmBreakManip::DetectBreak(void)
  {
   if(!m_manip.active) return(false);
   int limit = m_manip.shift-1;             // structure interne posterieure au sweep
   if(limit < m_mk+2) return(false);        // pas encore assez de barres

   double c1 = iClose(m_sym,m_tf,1);
   double px; int sh;

   if(m_manip.bias==-1)
     {
      // SELL : casser le dernier swing LOW mineur forme depuis le sweep
      if(!FindSwingLow(m_mk+2,limit,m_mk,px,sh)) return(false);
      if(c1 >= px) return(false);
      m_break.confirmed      = true;
      m_break.bias           = -1;
      m_break.level          = px;
      m_break.time           = iTime(m_sym,m_tf,1);
      m_break.impulse_top    = m_manip.extreme;
      m_break.impulse_bottom = iLow(m_sym,m_tf,iLowest(m_sym,m_tf,MODE_LOW,m_manip.shift,1));
      return(true);
     }
   else
     {
      // BUY : casser le dernier swing HIGH mineur forme depuis le sweep
      if(!FindSwingHigh(m_mk+2,limit,m_mk,px,sh)) return(false);
      if(c1 <= px) return(false);
      m_break.confirmed      = true;
      m_break.bias           = 1;
      m_break.level          = px;
      m_break.time           = iTime(m_sym,m_tf,1);
      m_break.impulse_bottom = m_manip.extreme;
      m_break.impulse_top    = iHigh(m_sym,m_tf,iHighest(m_sym,m_tf,MODE_HIGH,m_manip.shift,1));
      return(true);
     }
  }
//+------------------------------------------------------------------+
//| Signal : entree FVG (prioritaire) ou fib 0.705 de la jambe       |
//| d'impulsion. SL au-dela de l'extreme du sweep + buffer ATR.      |
//| TP = liquidite opposee. R/R < MinRR => veto (grade D).           |
//+------------------------------------------------------------------+
void CDrevmBreakManip::BuildSignal(void)
  {
   ZeroMemory(m_signal);
   if(!m_break.confirmed) return;

   double atr = ATR(1);
   int    dg  = (int)SymbolInfoInteger(m_sym,SYMBOL_DIGITS);
   double top = m_break.impulse_top;
   double bot = m_break.impulse_bottom;
   double leg = top-bot;
   if(leg<=0.0) return;

   double entry=0.0; bool hasFvg=false;

   //--- recherche d'une FVG dans la jambe d'impulsion (gap 3 bougies)
   for(int i=1; i<=m_manip.shift-2; i++)
     {
      if(m_break.bias==-1)
        {
         // FVG baissiere : low[i+2] > high[i]
         double lo=iLow(m_sym,m_tf,i+2), hi=iHigh(m_sym,m_tf,i);
         if(lo>hi) { entry=0.5*(lo+hi); hasFvg=true; break; }
        }
      else
        {
         // FVG haussiere : high[i+2] < low[i]
         double hi=iHigh(m_sym,m_tf,i+2), lo=iLow(m_sym,m_tf,i);
         if(hi<lo) { entry=0.5*(hi+lo); hasFvg=true; break; }
        }
     }

   //--- repli : niveau sniper 70.5% de la jambe (zone 61.8-71 DREVM)
   if(!hasFvg)
      entry = (m_break.bias==-1) ? bot+0.705*leg : top-0.705*leg;

   //--- SL au-dela de l'extreme du sweep
   double sl = (m_break.bias==-1) ? m_manip.extreme+m_slBufATR*atr
                                  : m_manip.extreme-m_slBufATR*atr;
   double risk = MathAbs(entry-sl);
   if(risk<=0.0) return;

   //--- TP = liquidite opposee (swing confirme majeur), sinon MinRR
   double liq; int lsh; double tp;
   if(m_break.bias==-1)
     {
      tp = FindSwingLow(m_k+2,m_lookback,m_k,liq,lsh) ? liq : entry-m_minRR*risk;
      if(tp>=entry) tp = entry-m_minRR*risk;
     }
   else
     {
      tp = FindSwingHigh(m_k+2,m_lookback,m_k,liq,lsh) ? liq : entry+m_minRR*risk;
      if(tp<=entry) tp = entry+m_minRR*risk;
     }

   double rr = MathAbs(tp-entry)/risk;

   m_signal.ready   = true;
   m_signal.bias    = m_break.bias;
   m_signal.entry   = NormalizeDouble(entry,dg);
   m_signal.sl      = NormalizeDouble(sl,dg);
   m_signal.tp      = NormalizeDouble(tp,dg);
   m_signal.rr      = rr;
   m_signal.has_fvg = hasFvg;
   m_signal.veto_rr = (rr < m_minRR);
   m_signal.comment = StringFormat("%s | sweep %s | MSS close | entree %s | R/R %.2f%s",
                                   (m_break.bias==1?"BUY":"SELL"),
                                   (m_manip.bias==1?"lows":"highs"),
                                   (hasFvg?"FVG":"fib 70.5"),
                                   rr,
                                   (m_signal.veto_rr?" | VETO R/R (grade D)":""));
  }
//+------------------------------------------------------------------+
//| Machine a etats — une seule execution par barre cloturee         |
//+------------------------------------------------------------------+
bool CDrevmBreakManip::Update(void)
  {
   datetime t = iTime(m_sym,m_tf,0);
   if(t==0 || t==m_lastBar) return(false);       // invariant no-repaint
   m_lastBar = t;

   if(Bars(m_sym,m_tf) < m_lookback+m_k+m_volRef+10) return(false);

   //--- vieillissement de la manipulation en cours
   if(m_manip.active) m_manip.shift++;

   switch(m_phase)
     {
      case DREVM_IDLE:
      case DREVM_INVALIDATED:
        {
         Reset(DREVM_IDLE);
         if(DetectManipulation()) m_phase = DREVM_MANIPULATION;
         break;
        }

      case DREVM_MANIPULATION:
        {
         double c1=iClose(m_sym,m_tf,1);

         // invalidation : cloture au-dela de l'extreme du sweep
         bool killed = (m_manip.bias==-1) ? (c1>m_manip.extreme) : (c1<m_manip.extreme);
         if(killed || m_manip.shift>m_maxBars)
           {
            Reset(DREVM_INVALIDATED);
            // une nouvelle manipulation peut naitre sur la meme barre
            if(DetectManipulation()) m_phase = DREVM_MANIPULATION;
            break;
           }

         if(DetectBreak())
           {
            BuildSignal();
            m_phase = DREVM_BREAK;
           }
         break;
        }

      case DREVM_BREAK:
        {
         // signal consomme : on repart en scan
         Reset(DREVM_IDLE);
         if(DetectManipulation()) m_phase = DREVM_MANIPULATION;
         break;
        }
     }
   return(true);
  }
//+------------------------------------------------------------------+
string CDrevmBreakManip::PhaseText(void) const
  {
   switch(m_phase)
     {
      case DREVM_MANIPULATION: return("MANIPULATION");
      case DREVM_BREAK:        return("BREAK");
      case DREVM_INVALIDATED:  return("INVALIDE");
     }
   return("IDLE");
  }
//+------------------------------------------------------------------+
string CDrevmBreakManip::Describe(void) const
  {
   if(m_phase==DREVM_MANIPULATION)
      return(StringFormat("[%s] %s sweep %s @ %.5f | meche %.2f ATR | vol x%.2f | %d/%d barres",
                          m_sym,PhaseText(),(m_manip.bias==1?"lows":"highs"),
                          m_manip.extreme,m_manip.wick_atr,m_manip.vol_ratio,
                          m_manip.shift,m_maxBars));
   if(m_phase==DREVM_BREAK)
      return(StringFormat("[%s] BREAK confirme @ %.5f | %s",m_sym,m_break.level,m_signal.comment));
   return(StringFormat("[%s] %s",m_sym,PhaseText()));
  }

//+------------------------------------------------------------------+
//| EXEMPLE D'INTEGRATION (a copier dans l'EA)                       |
//|                                                                  |
//|  #include <DREVM/DREVM_BreakManipulation.mqh>                    |
//|  CDrevmBreakManip gBM;                                           |
//|                                                                  |
//|  int OnInit()                                                    |
//|    {                                                             |
//|     if(!gBM.Init(_Symbol,PERIOD_M5,5,2,100,12,0.30,0.0,20,       |
//|                  0.25,2.0,14)) return(INIT_FAILED);              |
//|     return(INIT_SUCCEEDED);                                      |
//|    }                                                             |
//|                                                                  |
//|  void OnDeinit(const int r) { gBM.Deinit(); }                    |
//|                                                                  |
//|  void OnTick()                                                   |
//|    {                                                             |
//|     if(!gBM.Update()) return;   // rien tant que barre non close |
//|     if(gBM.Phase()!=DREVM_BREAK) return;                         |
//|     SDrevmSignal s = gBM.Signal();                               |
//|     if(!s.ready || s.veto_rr) return;      // veto R/R = grade D |
//|     // -> alimenter le moteur de confluence / MODE_ALERT_ONLY    |
//|     Print(gBM.Describe());                                       |
//|    }                                                             |
//+------------------------------------------------------------------+
#endif // __DREVM_BREAK_MANIPULATION_MQH__
