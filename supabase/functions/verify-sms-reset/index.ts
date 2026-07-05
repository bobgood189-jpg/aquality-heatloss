// Проверяет 6-значный код сброса пароля, отправленный send-sms-reset по SMS
// через Eskiz.uz, и меняет пароль через Admin API. Пара с verify-tg-reset —
// тот же контракт (email, code, newPassword), только код доставляется по
// SMS, а не в Telegram-бот, и хранится хешем (sha256(phone:code)), а не
// открытым текстом.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const GENERIC_ERROR = 'Неверный или просроченный код';

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

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
      .from('sms_reset_codes')
      .select('id, phone, code_hash, attempts, max_attempts, expires_at')
      .eq('user_id', profile.id)
      .is('used_at', null)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (!rec || new Date(rec.expires_at).getTime() < Date.now()) {
      return new Response(JSON.stringify({ ok: false, reason: 'invalid_code', error: GENERIC_ERROR }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (rec.attempts >= rec.max_attempts) {
      return new Response(JSON.stringify({
        ok: false, reason: 'too_many_attempts', error: 'Слишком много попыток. Запросите новый код.',
      }), { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } });
    }

    const inputHash = await sha256Hex(`${rec.phone}:${String(code).trim()}`);
    if (inputHash !== rec.code_hash) {
      await supabase.from('sms_reset_codes').update({ attempts: rec.attempts + 1 }).eq('id', rec.id);
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

    await supabase.from('sms_reset_codes').update({ used_at: new Date().toISOString() }).eq('id', rec.id);

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[verify-sms-reset]', err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
