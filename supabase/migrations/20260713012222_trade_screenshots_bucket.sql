-- ============================================================================
--  Storage : bucket privé "trade-screenshots" pour les captures du journal.
--  Convention de chemin : {user_id}/<fichier>  → chaque user isolé par RLS.
--  Idempotent. Bucket privé (accès via URLs signées).
-- ============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'trade-screenshots', 'trade-screenshots', false,
    5242880,  -- 5 Mo / fichier
    ARRAY['image/png', 'image/jpeg', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Policies sur storage.objects, restreintes au bucket + au dossier {user_id}.
DROP POLICY IF EXISTS "trade_screenshots_select" ON storage.objects;
CREATE POLICY "trade_screenshots_select" ON storage.objects
    FOR SELECT TO authenticated
    USING (bucket_id = 'trade-screenshots'
           AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "trade_screenshots_insert" ON storage.objects;
CREATE POLICY "trade_screenshots_insert" ON storage.objects
    FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'trade-screenshots'
                AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "trade_screenshots_update" ON storage.objects;
CREATE POLICY "trade_screenshots_update" ON storage.objects
    FOR UPDATE TO authenticated
    USING (bucket_id = 'trade-screenshots'
           AND auth.uid()::text = (storage.foldername(name))[1])
    WITH CHECK (bucket_id = 'trade-screenshots'
                AND auth.uid()::text = (storage.foldername(name))[1]);

DROP POLICY IF EXISTS "trade_screenshots_delete" ON storage.objects;
CREATE POLICY "trade_screenshots_delete" ON storage.objects
    FOR DELETE TO authenticated
    USING (bucket_id = 'trade-screenshots'
           AND auth.uid()::text = (storage.foldername(name))[1]);
