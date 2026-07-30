/**
 * Client Supabase (front). Utilise la clé ANON (publique) + RLS : chaque
 * utilisateur ne voit que ses lignes de journal. NE JAMAIS mettre la clé
 * service_role ici.
 */
import { createClient } from '@supabase/supabase-js';

const url = import.meta.env.VITE_SUPABASE_URL;
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabaseEnabled = Boolean(url && anon);
export const supabase = supabaseEnabled ? createClient(url, anon) : null;
export const SCREENSHOT_BUCKET = 'trade-screenshots';
