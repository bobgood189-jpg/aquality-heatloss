import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-bot-secret',
};

const BOT_SYNC_SECRET = Deno.env.get('BOT_SYNC_SECRET') || '';

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders });

  // Authenticate the bot via shared secret
  const secret = req.headers.get('x-bot-secret');
  if (!BOT_SYNC_SECRET || secret !== BOT_SYNC_SECRET) {
    return json({ error: 'Unauthorized' }, 401);
  }

  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
  );

  try {
    const body = await req.json();
    const { action, tg_user_id, tg_username, token, plan, days, amount, promo } = body;

    if (!tg_user_id) return json({ error: 'tg_user_id required' }, 400);

    // ── Link Telegram account to a website profile ──
    if (action === 'link') {
      if (!token) return json({ error: 'token required' }, 400);
      const { data, error } = await supabase.rpc('link_tg_account', {
        p_token:        (token as string).trim().toUpperCase(),
        p_tg_user_id:   tg_user_id,
        p_tg_username:  tg_username || '',
      });
      if (error) {
        console.error('[telegram-webhook] link_tg_account:', error);
        return json({ error: error.message }, 500);
      }
      return json(data);
    }

    // ── Activate subscription for the linked profile ──
    if (action === 'activate_sub') {
      if (!plan || !days) return json({ error: 'plan and days required' }, 400);
      const { data, error } = await supabase.rpc('activate_sub_by_tg', {
        p_tg_user_id: tg_user_id,
        p_plan:       plan,
        p_days:       days,
        p_amount:     amount ?? null,
        p_promo:      promo  ?? null,
      });
      if (error) {
        console.error('[telegram-webhook] activate_sub_by_tg:', error);
        return json({ error: error.message }, 500);
      }
      return json(data);
    }

    return json({ error: 'unknown action' }, 400);
  } catch (err) {
    console.error('[telegram-webhook]', err);
    return json({ error: String(err) }, 500);
  }
});
