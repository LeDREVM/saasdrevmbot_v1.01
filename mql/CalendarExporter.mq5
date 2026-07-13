//+------------------------------------------------------------------+
//| CalendarExporter.mq5                                             |
//| Exporte le calendrier économique MT5 (CalendarValueHistory) en   |
//| JSON, consommable par le pipeline Python (ny_session_interface/  |
//| news.py, NEWS_SOURCE=mt5).                                        |
//|                                                                  |
//| Le paquet Python MetaTrader5 n'expose PAS le calendrier ; cet    |
//| EA fait le pont : il écrit MQL5/Files/<OutFile> à intervalle     |
//| régulier. Pointer MT5_CALENDAR_FILE (côté console) sur ce fichier.|
//|                                                                  |
//| ⚠️ Le terminal doit avoir le calendrier activé et une connexion. |
//+------------------------------------------------------------------+
#property copyright "DREVM"
#property version   "1.00"
#property strict

input int    HoursAhead   = 24;                    // fenêtre à venir (heures)
input int    RefreshSec   = 300;                   // rafraîchissement (secondes)
input string OutFile      = "calendar_export.json";// dans MQL5/Files/
input bool   HighOnly     = false;                 // n'exporter que le high-impact

//+------------------------------------------------------------------+
int OnInit()
  {
   EventSetTimer(RefreshSec);
   ExportCalendar();
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
  }
//+------------------------------------------------------------------+
void OnTimer()
  {
   ExportCalendar();
  }
//+------------------------------------------------------------------+
string ImportanceToStr(const ENUM_CALENDAR_EVENT_IMPORTANCE imp)
  {
   switch(imp)
     {
      case CALENDAR_IMPORTANCE_HIGH:     return("high");
      case CALENDAR_IMPORTANCE_MODERATE: return("medium");
      case CALENDAR_IMPORTANCE_LOW:      return("low");
      default:                           return("none");
     }
  }
//+------------------------------------------------------------------+
string JsonEscape(string s)
  {
   StringReplace(s, "\\", "\\\\");
   StringReplace(s, "\"", "\\\"");
   return(s);
  }
//+------------------------------------------------------------------+
void ExportCalendar()
  {
   datetime from = TimeCurrent();
   datetime to   = from + (datetime)HoursAhead * 3600;

   MqlCalendarValue values[];
   int n = CalendarValueHistory(values, from, to, NULL, NULL);
   if(n < 0)
     {
      PrintFormat("CalendarExporter: CalendarValueHistory a échoué (err=%d)", GetLastError());
      return;
     }

   string json = "[";
   bool   first = true;

   for(int i = 0; i < n; i++)
     {
      MqlCalendarEvent event;
      if(!CalendarEventById(values[i].event_id, event))
         continue;

      string imp = ImportanceToStr(event.importance);
      if(imp == "none")
         continue;
      if(HighOnly && imp != "high")
         continue;

      MqlCalendarCountry country;
      string curr = "";
      if(CalendarCountryById(event.country_id, country))
         curr = country.currency;

      // Date "YYYY.MM.DD" -> "YYYY-MM-DD" ; heure "HH:MM".
      string date = TimeToString(values[i].time, TIME_DATE);
      StringReplace(date, ".", "-");
      string tm = TimeToString(values[i].time, TIME_MINUTES);

      if(!first)
         json += ",";
      first = false;
      json += StringFormat("{\"date\":\"%s\",\"time\":\"%s\",\"currency\":\"%s\",\"event\":\"%s\",\"impact\":\"%s\"}",
                           date, tm, curr, JsonEscape(event.name), imp);
     }
   json += "]";

   int h = FileOpen(OutFile, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      PrintFormat("CalendarExporter: FileOpen('%s') a échoué (err=%d)", OutFile, GetLastError());
      return;
     }
   FileWriteString(h, json);
   FileClose(h);
   PrintFormat("CalendarExporter: %d événements exportés -> %s", n, OutFile);
  }
//+------------------------------------------------------------------+
