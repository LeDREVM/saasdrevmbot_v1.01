//+------------------------------------------------------------------+
//| AISignalReceiver.mq5 — Reçoit les signaux du VPS via socket     |
//| Se connecte au signal_server.py sur le VPS Hostinger            |
//+------------------------------------------------------------------+
#property copyright "saasdrevmbot"
#property version   "1.00"
#property strict

input string   VPS_IP         = "YOUR_VPS_IP";   // IP VPS Hostinger
input int      BRIDGE_PORT    = 5001;             // Port bridge Python
input int      POLL_SECONDS   = 5;               // Fréquence poll (sec)
input double   DEFAULT_LOT    = 0.01;            // Lot par défaut
input int      SLIPPAGE       = 10;
input int      MAGIC          = 20260602;

int      timerCounter = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   EventSetTimer(1);
   Print("[AISignal] EA démarré — VPS: ", VPS_IP, ":", BRIDGE_PORT);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   EventKillTimer();
}

//+------------------------------------------------------------------+
void OnTimer()
{
   timerCounter++;
   if (timerCounter < POLL_SECONDS) return;
   timerCounter = 0;
   PollSignal();
}

//+------------------------------------------------------------------+
void PollSignal()
{
   int socket = SocketCreate();
   if (socket == INVALID_HANDLE)
   {
      Print("[AISignal] Socket create failed: ", GetLastError());
      return;
   }

   if (!SocketConnect(socket, VPS_IP, BRIDGE_PORT, 3000))
   {
      SocketClose(socket);
      return;
   }

   // Lire la réponse
   string response = "";
   uchar buf[];
   uint  timeout_ms = 3000;
   uint  start = GetTickCount();

   while (GetTickCount() - start < timeout_ms)
   {
      uint available = SocketIsReadable(socket);
      if (available > 0)
      {
         int read = SocketRead(socket, buf, available, 1000);
         if (read > 0)
            response += CharArrayToString(buf, 0, read);
      }
      if (StringFind(response, "\n") >= 0) break;
      Sleep(50);
   }

   SocketClose(socket);
   response = StringTrimRight(StringTrimLeft(response));

   if (response == "" || response == "NONE")
      return;

   ProcessSignal(response, socket);
}

//+------------------------------------------------------------------+
void ProcessSignal(string jsonStr, int sock)
{
   Print("[AISignal] Signal reçu: ", jsonStr);

   string symbol    = JsonGet(jsonStr, "symbol");
   string direction = JsonGet(jsonStr, "direction");
   string sigId     = JsonGet(jsonStr, "signal_id");
   double entry     = StringToDouble(JsonGet(jsonStr, "entry_price"));
   double sl        = StringToDouble(JsonGet(jsonStr, "stop_loss"));
   double tp1       = StringToDouble(JsonGet(jsonStr, "take_profit"));
   double lotSize   = StringToDouble(JsonGet(jsonStr, "lot_size"));
   double score     = StringToDouble(JsonGet(jsonStr, "score"));
   int    magic     = (int)StringToInteger(JsonGet(jsonStr, "magic_number"));
   string comment   = JsonGet(jsonStr, "comment");

   if (symbol == "") symbol = _Symbol;
   if (lotSize <= 0) lotSize = DEFAULT_LOT;
   if (magic == 0)   magic   = MAGIC;

   ENUM_ORDER_TYPE orderType = (direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;

   MqlTradeRequest req  = {};
   MqlTradeResult  res  = {};

   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = symbol;
   req.volume    = lotSize;
   req.type      = orderType;
   req.price     = (direction == "BUY") ? SymbolInfoDouble(symbol, SYMBOL_ASK)
                                        : SymbolInfoDouble(symbol, SYMBOL_BID);
   req.sl        = sl;
   req.tp        = tp1;
   req.deviation = SLIPPAGE;
   req.magic     = magic;
   req.comment   = comment + " S=" + DoubleToString(score, 1);

   bool sent = OrderSend(req, res);

   string ack;
   if (sent && res.retcode == TRADE_RETCODE_DONE)
   {
      ack = "ACK:" + IntegerToString(res.order);
      Print("[AISignal] ✅ Ordre ouvert ticket=", res.order, " ", symbol, " ", direction,
            " lot=", lotSize, " score=", score);
   }
   else
   {
      ack = "ERR:" + IntegerToString(res.retcode);
      Print("[AISignal] ❌ Erreur ordre retcode=", res.retcode, " ", res.comment);
   }

   // Renvoie l'ack au serveur Python
   int sockAck = SocketCreate();
   if (sockAck != INVALID_HANDLE && SocketConnect(sockAck, VPS_IP, BRIDGE_PORT, 2000))
   {
      uchar ackBuf[];
      StringToCharArray(ack + "\n", ackBuf);
      SocketSend(sockAck, ackBuf, ArraySize(ackBuf) - 1);
      SocketClose(sockAck);
   }
}

//+------------------------------------------------------------------+
// Extraction JSON minimale (pas de lib externe requise)
string JsonGet(string json, string key)
{
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if (pos < 0) return "";

   pos += StringLen(search);
   // Saute espace et ':'
   while (pos < StringLen(json) && (StringSubstr(json, pos, 1) == " " || StringSubstr(json, pos, 1) == ":"))
      pos++;

   if (pos >= StringLen(json)) return "";

   string ch = StringSubstr(json, pos, 1);

   if (ch == "\"")
   {
      pos++;
      int end = StringFind(json, "\"", pos);
      if (end < 0) return "";
      return StringSubstr(json, pos, end - pos);
   }
   else
   {
      // Valeur numérique ou booléenne
      string result = "";
      while (pos < StringLen(json))
      {
         ch = StringSubstr(json, pos, 1);
         if (ch == "," || ch == "}" || ch == "\n") break;
         result += ch;
         pos++;
      }
      return StringTrimRight(StringTrimLeft(result));
   }
}

//+------------------------------------------------------------------+
void OnTick() {}
//+------------------------------------------------------------------+
