//+------------------------------------------------------------------+
//|                                        DREVM_CorrelationGuard.mqh |
//|                          GoldXrodgers / DREVM — Négus Dja        |
//|                                                                  |
//|  MODULE DE CORRÉLATION OPTIMISÉ — include pour tous les EAs      |
//|                                                                  |
//|  Problème : XAUUSD, US30, USDJPY, CADJPY, USDCAD partagent des   |
//|  devises. Plusieurs trades "différents" = une seule grosse       |
//|  exposition déguisée (USD x4, JPY x2, CAD x2).                   |
//|                                                                  |
//|  Solution :                                                      |
//|   1. Exposition nette par devise (somme signée des lots pondérés)|
//|   2. Corrélation dynamique des rendements H1 (Pearson, rolling)  |
//|   3. Lot ajusté : réduit si le nouveau trade augmente une        |
//|      exposition déjà chargée ou est corrélé à une position       |
//|   4. Veto si l'exposition devise dépasserait le cap              |
//|                                                                  |
//|  Usage dans un EA :                                              |
//|    #include "DREVM_CorrelationGuard.mqh"                         |
//|    ...                                                           |
//|    double adjLot = CorrGuard_AdjustLot(_Symbol, dir, baseLot);   |
//|    if(adjLot <= 0.0) return; // veto corrélation                 |
//|    trade.Buy(adjLot, ...);                                       |
//+------------------------------------------------------------------+
#property strict

//=== PARAMÈTRES (surchargables avant l'include via #define) =========
#ifndef CORR_MAX_CURRENCY_EXPOSURE
#define CORR_MAX_CURRENCY_EXPOSURE   0.06   // lots pondérés max par devise
#endif
#ifndef CORR_HIGH_THRESHOLD
#define CORR_HIGH_THRESHOLD          0.70   // |r| au-delà = fortement corrélé
#endif
#ifndef CORR_MED_THRESHOLD
#define CORR_MED_THRESHOLD           0.40   // |r| au-delà = moyennement corrélé
#endif
#ifndef CORR_LOOKBACK_H1
#define CORR_LOOKBACK_H1             96     // barres H1 pour le calcul (4 jours)
#endif
#ifndef CORR_REDUCE_HIGH
#define CORR_REDUCE_HIGH             0.50   // réduction de lot si corrélation forte
#endif
#ifndef CORR_REDUCE_MED
#define CORR_REDUCE_MED              0.75   // réduction si corrélation moyenne
#endif
#ifndef CORR_CACHE_SECONDS
#define CORR_CACHE_SECONDS           3600   // recalcul matrice toutes les heures
#endif

//=== UNIVERS DREVM ==================================================
string CORR_SYMBOLS[5] = {"XAUUSD", "US30", "USDJPY", "CADJPY", "USDCAD"};

// Décomposition devise : base +1, cotée -1 pour un BUY (inverse pour SELL)
// XAUUSD : base=XAU(or), cotée=USD | US30 : indice USD (cotée USD)
string CORR_BASE[5]  = {"XAU", "US30I", "USD", "CAD", "USD"};
string CORR_QUOTE[5] = {"USD", "USD",   "JPY", "JPY", "CAD"};

// Poids de volatilité relative (normalise 0.01 lot or vs 0.01 lot forex)
// approximation : valeur ATR(D1) en devise du compte pour 0.01 lot, base 1.0 = forex majeur
double CORR_VOLW[5]  = {2.5, 2.0, 1.0, 1.0, 1.0};

//=== CACHE MATRICE DE CORRÉLATION ===================================
double   corrMatrix[5][5];
datetime corrLastCalc = 0;

//+------------------------------------------------------------------+
//| Index d'un symbole dans l'univers (-1 si hors univers)           |
//+------------------------------------------------------------------+
int CorrGuard_Index(const string symbol)
  {
   for(int i = 0; i < 5; i++)
      if(StringFind(symbol, CORR_SYMBOLS[i]) == 0) return i;
   return -1;
  }

//+------------------------------------------------------------------+
//| Rendements H1 log d'un symbole                                    |
//+------------------------------------------------------------------+
bool CorrGuard_Returns(const string symbol, double &rets[])
  {
   double closes[];
   int copied = CopyClose(symbol, PERIOD_H1, 1, CORR_LOOKBACK_H1 + 1, closes);
   if(copied < CORR_LOOKBACK_H1 + 1) return false;

   ArrayResize(rets, CORR_LOOKBACK_H1);
   for(int i = 0; i < CORR_LOOKBACK_H1; i++)
     {
      if(closes[i] <= 0.0) return false;
      rets[i] = MathLog(closes[i + 1] / closes[i]);
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Pearson entre deux séries                                         |
//+------------------------------------------------------------------+
double CorrGuard_Pearson(const double &a[], const double &b[])
  {
   int n = MathMin(ArraySize(a), ArraySize(b));
   if(n < 10) return 0.0;

   double sumA = 0, sumB = 0;
   for(int i = 0; i < n; i++) { sumA += a[i]; sumB += b[i]; }
   double meanA = sumA / n, meanB = sumB / n;

   double cov = 0, varA = 0, varB = 0;
   for(int i = 0; i < n; i++)
     {
      double da = a[i] - meanA, db = b[i] - meanB;
      cov  += da * db;
      varA += da * da;
      varB += db * db;
     }
   double denom = MathSqrt(varA * varB);
   if(denom <= 0.0) return 0.0;
   return cov / denom;
  }

//+------------------------------------------------------------------+
//| Recalcul (cache) de la matrice de corrélation                     |
//+------------------------------------------------------------------+
void CorrGuard_UpdateMatrix()
  {
   if(TimeCurrent() - corrLastCalc < CORR_CACHE_SECONDS) return;
   corrLastCalc = TimeCurrent();

   double rets[5][];
   bool   ok[5];
   double tmp[];
   for(int i = 0; i < 5; i++)
     {
      ok[i] = CorrGuard_Returns(CORR_SYMBOLS[i], tmp);
      if(ok[i])
        {
         ArrayResize(rets[i], ArraySize(tmp));
         ArrayCopy(rets[i], tmp);
        }
     }

   for(int i = 0; i < 5; i++)
      for(int j = 0; j < 5; j++)
        {
         if(i == j) { corrMatrix[i][j] = 1.0; continue; }
         corrMatrix[i][j] = (ok[i] && ok[j]) ? CorrGuard_Pearson(rets[i], rets[j]) : 0.0;
        }
  }

//+------------------------------------------------------------------+
//| Exposition nette actuelle par devise (lots pondérés signés)      |
//| dir de chaque position : BUY = +base/-quote, SELL inverse         |
//+------------------------------------------------------------------+
void CorrGuard_CurrencyExposure(string &currencies[], double &exposure[])
  {
   // Devises de l'univers
   string allCur[6] = {"USD", "JPY", "CAD", "XAU", "US30I", ""};
   ArrayResize(currencies, 5);
   ArrayResize(exposure, 5);
   for(int c = 0; c < 5; c++) { currencies[c] = allCur[c]; exposure[c] = 0.0; }

   for(int p = PositionsTotal() - 1; p >= 0; p--)
     {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      int idx = CorrGuard_Index(sym);
      if(idx < 0) continue;

      double vol  = PositionGetDouble(POSITION_VOLUME) * CORR_VOLW[idx];
      int    sign = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;

      for(int c = 0; c < 5; c++)
        {
         if(currencies[c] == CORR_BASE[idx])  exposure[c] += sign * vol;
         if(currencies[c] == CORR_QUOTE[idx]) exposure[c] -= sign * vol;
        }
     }
  }

//+------------------------------------------------------------------+
//| Corrélation effective max entre le candidat et les positions      |
//| Prend en compte le SENS : deux positions corrélées dans le même   |
//| sens de risque cumulent ; en sens opposé elles se hedgent.        |
//+------------------------------------------------------------------+
double CorrGuard_MaxEffectiveCorr(const string symbol, const int dir)
  {
   int idx = CorrGuard_Index(symbol);
   if(idx < 0) return 0.0;

   CorrGuard_UpdateMatrix();

   double maxEff = 0.0;
   for(int p = PositionsTotal() - 1; p >= 0; p--)
     {
      ulong ticket = PositionGetTicket(p);
      if(ticket == 0) continue;
      string psym = PositionGetString(POSITION_SYMBOL);
      int pidx = CorrGuard_Index(psym);
      if(pidx < 0 || pidx == idx) continue;

      int psign = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;

      // corrélation effective = r * sens_candidat * sens_position
      // > 0 : les deux risques s'additionnent (danger)
      // < 0 : hedge naturel (acceptable)
      double eff = corrMatrix[idx][pidx] * dir * psign;
      if(eff > maxEff) maxEff = eff;
     }
   return maxEff;
  }

//+------------------------------------------------------------------+
//| FONCTION PRINCIPALE — lot ajusté ou veto (retour <= 0)           |
//+------------------------------------------------------------------+
double CorrGuard_AdjustLot(const string symbol, const int dir, const double baseLot)
  {
   int idx = CorrGuard_Index(symbol);
   if(idx < 0) return baseLot;   // hors univers : pas de contrôle

   double lot = baseLot;

   // ── 1. Réduction par corrélation dynamique effective ──
   double eff = CorrGuard_MaxEffectiveCorr(symbol, dir);
   if(eff >= CORR_HIGH_THRESHOLD)
      lot *= CORR_REDUCE_HIGH;                 // -50%
   else if(eff >= CORR_MED_THRESHOLD)
      lot *= CORR_REDUCE_MED;                  // -25%

   // ── 2. Veto par exposition devise ──
   string currencies[]; double exposure[];
   CorrGuard_CurrencyExposure(currencies, exposure);

   double addVol = lot * CORR_VOLW[idx];
   for(int c = 0; c < 5; c++)
     {
      double delta = 0.0;
      if(currencies[c] == CORR_BASE[idx])  delta =  dir * addVol;
      if(currencies[c] == CORR_QUOTE[idx]) delta = -dir * addVol;
      if(delta == 0.0) continue;

      double newExp = MathAbs(exposure[c] + delta);
      double curExp = MathAbs(exposure[c]);

      // Veto seulement si le trade AGGRAVE une exposition déjà au cap
      if(newExp > CORR_MAX_CURRENCY_EXPOSURE && newExp > curExp)
        {
         PrintFormat("CorrGuard VETO %s %s: exposition %s passerait à %.3f (cap %.3f)",
                     symbol, dir > 0 ? "BUY" : "SELL", currencies[c],
                     newExp, CORR_MAX_CURRENCY_EXPOSURE);
         return 0.0;
        }
     }

   // ── 3. Normalisation broker ──
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   lot = MathFloor(lot / lotStep) * lotStep;
   if(lot < minLot)
     {
      // Trop réduit pour être exécutable : veto propre plutôt qu'un lot forcé
      PrintFormat("CorrGuard VETO %s: lot ajusté %.3f < min %.2f (corr eff %.2f)",
                  symbol, lot, minLot, eff);
      return 0.0;
     }

   if(lot < baseLot)
      PrintFormat("CorrGuard %s %s: lot %.2f -> %.2f (corr eff %.2f)",
                  symbol, dir > 0 ? "BUY" : "SELL", baseLot, lot, eff);

   return lot;
  }

//+------------------------------------------------------------------+
//| Rapport texte (pour Comment / Telegram / logs)                    |
//+------------------------------------------------------------------+
string CorrGuard_Report()
  {
   CorrGuard_UpdateMatrix();
   string currencies[]; double exposure[];
   CorrGuard_CurrencyExposure(currencies, exposure);

   string s = "── CorrGuard ──\n";
   for(int c = 0; c < 5; c++)
      if(MathAbs(exposure[c]) > 0.0001)
         s += StringFormat("%s: %+.3f%s\n", currencies[c], exposure[c],
              MathAbs(exposure[c]) >= CORR_MAX_CURRENCY_EXPOSURE ? " ⚠️CAP" : "");

   s += "Corr H1 (4j):\n";
   for(int i = 0; i < 5; i++)
      for(int j = i + 1; j < 5; j++)
         if(MathAbs(corrMatrix[i][j]) >= CORR_MED_THRESHOLD)
            s += StringFormat("%s/%s: %+.2f\n", CORR_SYMBOLS[i], CORR_SYMBOLS[j], corrMatrix[i][j]);
   return s;
  }
//+------------------------------------------------------------------+
