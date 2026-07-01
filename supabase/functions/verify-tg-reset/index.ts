// Проверяет 6-значный код восстановления пароля, отправленный в Telegram-бот
// (см. supabase/tg-reset-codes-schema.sql), и меняет пароль через Admin API.
//
// Логика живёт в Edge Function, а не в RPC, потому что смена пароля требует
// supabase.auth.admin.updateUserById — это Admin API, недоступный из plpgsql.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const MAX_ATTEMPTS = 5;
const GENERIC_ERROR = 'Неверный или просроченный код';

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { email, code, newPassword } = await req.json();
    if (!email || !code || !newPassword) {
      return new Response(JSON.stringify({ ok: false, error: 'email, code and newPassword required' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }
    if (String(newPassword).length < 6) {
      return new Response(JSON.stringify({ ok: false, error: 'password too short' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    );

    const { data: profile } = await supabase
      .from('profiles')
      .select('id')
      .ilike('email', String(email).trim())
      .maybeSingle();

    if (!profile) {
      return new Response(JSON.stringify({ ok: false, reason: 'invalid_code', error: GENERIC_ERROR }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const { data: rec } = await supabase
      .from('tg_reset_codes')
      .select('id, code, attempts, expires_at')
      .eq('user_id', profile.id)
      .eq('used', false)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (!rec || new Date(rec.expires_at).getTime() < Date.now()) {
      return new Response(JSON.stringify({ ok: false, reason: 'invalid_code', error: GENERIC_ERROR }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (rec.attempts >= MAX_ATTEMPTS) {
      return new Response(JSON.stringify({
        ok: false, reason: 'too_many_attempts',
        error: 'Слишком много попыток. Запросите новый код.',
      }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    if (String(rec.code) !== String(code).trim()) {
      await supabase.from('tg_reset_codes').update({ attempts: rec.attempts + 1 }).eq('id', rec.id);
      return new Response(JSON.stringify({ ok: false, reason: 'invalid_code', error: GENERIC_ERROR }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const { error: updErr } = await supabase.auth.admin.updateUserById(profile.id, { password: newPassword });
    if (updErr) {
      return new Response(JSON.stringify({ ok: false, error: updErr.message }), {
        status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await supabase.from('tg_reset_codes').update({ used: true }).eq('id', rec.id);

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[verify-tg-reset]', err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
