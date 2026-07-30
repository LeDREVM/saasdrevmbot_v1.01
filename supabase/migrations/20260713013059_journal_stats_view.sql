-- ============================================================================
--  Vue statistiques du journal (par utilisateur). security_invoker=true →
--  exécute avec les droits de l'appelant, donc la RLS de journal_trades
--  s'applique : chaque user ne voit que ses propres stats.
-- ============================================================================

CREATE OR REPLACE VIEW public.journal_stats
WITH (security_invoker = true) AS
SELECT
    user_id,
    COUNT(*)                                             AS trades,
    COUNT(*) FILTER (WHERE result = 'win')               AS wins,
    COUNT(*) FILTER (WHERE result = 'loss')              AS losses,
    COUNT(*) FILTER (WHERE result = 'breakeven')         AS breakeven,
    COUNT(*) FILTER (WHERE result = 'running')           AS running,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE result = 'win')
        / NULLIF(COUNT(*) FILTER (WHERE result IN ('win', 'loss')), 0), 1
    )                                                    AS winrate_pct,
    ROUND(COALESCE(SUM(r_multiple), 0), 2)               AS total_r,
    ROUND(AVG(r_multiple) FILTER (
        WHERE result IN ('win', 'loss', 'breakeven')), 2) AS avg_r,
    ROUND(
        COALESCE(SUM(r_multiple) FILTER (WHERE r_multiple > 0), 0)
        / NULLIF(ABS(SUM(r_multiple) FILTER (WHERE r_multiple < 0)), 0), 2
    )                                                    AS profit_factor,
    ROUND(MAX(r_multiple), 2)                            AS best_r,
    ROUND(MIN(r_multiple), 2)                            AS worst_r
FROM public.journal_trades
GROUP BY user_id;
