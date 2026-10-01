import { supabase } from './supabase.js';
import { requestJSON } from './api-client.js';
export async function authRequest(url, options = {}) {
  const { data } = await supabase.auth.getSession();
  if (!data.session) throw new Error('Connecte-toi depuis le journal pour accéder aux alertes.');
  return requestJSON(url, { ...options, headers: { ...options.headers, Authorization: `Bearer ${data.session.access_token}` } });
}
