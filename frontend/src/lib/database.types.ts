export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      chart_snapshots: {
        Row: {
          created_at: string | null
          id: string
          raw_payload: Json | null
          screenshot_url: string | null
          source_url: string | null
          symbol: string
          timeframe: string
        }
        Insert: {
          created_at?: string | null
          id?: string
          raw_payload?: Json | null
          screenshot_url?: string | null
          source_url?: string | null
          symbol: string
          timeframe: string
        }
        Update: {
          created_at?: string | null
          id?: string
          raw_payload?: Json | null
          screenshot_url?: string | null
          source_url?: string | null
          symbol?: string
          timeframe?: string
        }
        Relationships: []
      }
      journal_alerts: {
        Row: {
          alert_time: string
          created_at: string
          currency: string | null
          event: string
          id: string
          impact: Database["public"]["Enums"]["event_impact"]
          note: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          alert_time: string
          created_at?: string
          currency?: string | null
          event: string
          id?: string
          impact?: Database["public"]["Enums"]["event_impact"]
          note?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          alert_time?: string
          created_at?: string
          currency?: string | null
          event?: string
          id?: string
          impact?: Database["public"]["Enums"]["event_impact"]
          note?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      journal_rules: {
        Row: {
          created_at: string
          drawdown_lock_pct: number
          drawdown_locked: boolean
          id: string
          max_trades_per_day: number
          risk_per_day_pct: number
          risk_per_trade_pct: number
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          drawdown_lock_pct?: number
          drawdown_locked?: boolean
          id?: string
          max_trades_per_day?: number
          risk_per_day_pct?: number
          risk_per_trade_pct?: number
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          drawdown_lock_pct?: number
          drawdown_locked?: boolean
          id?: string
          max_trades_per_day?: number
          risk_per_day_pct?: number
          risk_per_trade_pct?: number
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      journal_sessions: {
        Row: {
          bias: string | null
          comment: string | null
          created_at: string
          id: string
          news: string | null
          session_date: string
          updated_at: string
          user_id: string
        }
        Insert: {
          bias?: string | null
          comment?: string | null
          created_at?: string
          id?: string
          news?: string | null
          session_date?: string
          updated_at?: string
          user_id: string
        }
        Update: {
          bias?: string | null
          comment?: string | null
          created_at?: string
          id?: string
          news?: string | null
          session_date?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      journal_trades: {
        Row: {
          created_at: string
          direction: Database["public"]["Enums"]["trade_direction"]
          entry: number | null
          id: string
          notes: string | null
          r_multiple: number | null
          result: Database["public"]["Enums"]["trade_result"]
          screenshots: string[]
          sl: number | null
          symbol: string
          tp: number | null
          trade_date: string
          updated_at: string
          user_id: string
        }
        Insert: {
          created_at?: string
          direction: Database["public"]["Enums"]["trade_direction"]
          entry?: number | null
          id?: string
          notes?: string | null
          r_multiple?: number | null
          result?: Database["public"]["Enums"]["trade_result"]
          screenshots?: string[]
          sl?: number | null
          symbol: string
          tp?: number | null
          trade_date?: string
          updated_at?: string
          user_id: string
        }
        Update: {
          created_at?: string
          direction?: Database["public"]["Enums"]["trade_direction"]
          entry?: number | null
          id?: string
          notes?: string | null
          r_multiple?: number | null
          result?: Database["public"]["Enums"]["trade_result"]
          screenshots?: string[]
          sl?: number | null
          symbol?: string
          tp?: number | null
          trade_date?: string
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      mt5_logs: {
        Row: {
          action: string | null
          created_at: string | null
          id: string
          payload: Json | null
          response: Json | null
          signal_id: string | null
        }
        Insert: {
          action?: string | null
          created_at?: string | null
          id?: string
          payload?: Json | null
          response?: Json | null
          signal_id?: string | null
        }
        Update: {
          action?: string | null
          created_at?: string | null
          id?: string
          payload?: Json | null
          response?: Json | null
          signal_id?: string | null
        }
        Relationships: []
      }
      session_id: {
        Row: {
          created_at: string
          id: string
          session_id: string
          user_id: string | null
        }
        Insert: {
          created_at?: string
          id?: string
          session_id: string
          user_id?: string | null
        }
        Update: {
          created_at?: string
          id?: string
          session_id?: string
          user_id?: string | null
        }
        Relationships: []
      }
      trade_signals: {
        Row: {
          ai_analysis: string | null
          ai_model: string | null
          confidence: number | null
          created_at: string | null
          direction: string | null
          entry_price: number | null
          id: string
          mt5_ticket: number | null
          risk_reward: number | null
          score: number | null
          sent_at: string | null
          snapshot_id: string | null
          status: string | null
          stop_loss: number | null
          symbol: string
          take_profit_1: number | null
          take_profit_2: number | null
          timeframe: string
        }
        Insert: {
          ai_analysis?: string | null
          ai_model?: string | null
          confidence?: number | null
          created_at?: string | null
          direction?: string | null
          entry_price?: number | null
          id?: string
          mt5_ticket?: number | null
          risk_reward?: number | null
          score?: number | null
          sent_at?: string | null
          snapshot_id?: string | null
          status?: string | null
          stop_loss?: number | null
          symbol: string
          take_profit_1?: number | null
          take_profit_2?: number | null
          timeframe: string
        }
        Update: {
          ai_analysis?: string | null
          ai_model?: string | null
          confidence?: number | null
          created_at?: string | null
          direction?: string | null
          entry_price?: number | null
          id?: string
          mt5_ticket?: number | null
          risk_reward?: number | null
          score?: number | null
          sent_at?: string | null
          snapshot_id?: string | null
          status?: string | null
          stop_loss?: number | null
          symbol?: string
          take_profit_1?: number | null
          take_profit_2?: number | null
          timeframe?: string
        }
        Relationships: [
          {
            foreignKeyName: "trade_signals_snapshot_id_fkey"
            columns: ["snapshot_id"]
            isOneToOne: false
            referencedRelation: "chart_snapshots"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      journal_stats: {
        Row: {
          avg_r: number | null
          best_r: number | null
          breakeven: number | null
          losses: number | null
          profit_factor: number | null
          running: number | null
          total_r: number | null
          trades: number | null
          user_id: string | null
          winrate_pct: number | null
          wins: number | null
          worst_r: number | null
        }
        Relationships: []
      }
    }
    Functions: {
      session_id: {
        Args: { p_session_id: string; p_user_id?: string }
        Returns: string
      }
    }
    Enums: {
      event_impact: "low" | "medium" | "high"
      trade_direction: "buy" | "sell"
      trade_result: "win" | "loss" | "breakeven" | "running"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      event_impact: ["low", "medium", "high"],
      trade_direction: ["buy", "sell"],
      trade_result: ["win", "loss", "breakeven", "running"],
    },
  },
} as const
