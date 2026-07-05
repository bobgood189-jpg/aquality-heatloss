// Отправляет 6-значный код восстановления пароля по SMS через Eskiz.uz —
// альтернативный (наряду с email-OTP и Telegram-ботом) канал сброса пароля,
// см. supabase/sms-reset-codes-schema.sql. Телефон ищется в profiles по
// email, поэтому форма «Забыли пароль» не нуждается в отдельном поле «телефон».
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { sendSms, normalizeUzPhone } from '../_shared/eskiz.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const CODE_TTL_MIN = 10;
const COOLDOWN_SEC = 30;

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

// 998901234567 → "+998 90 *** ** 67" — для подсказки на экране, не раскрывая номер целиком.
function maskPhone(mobile: string): string {
  return `+${mobile.slice(0, 3)} ${mobile.slice(3, 5)} *** ** ${mobile.slice(-2)}`;
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { email } = await req.json();
    if (!email) {
      return new Response(JSON.stringify({ ok: false, error: 'email required' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    );

    const { data: profile } = await supabase
      .from('profiles')
      .select('id, phone')
      .ilike('email', String(email).trim())
      .maybeSingle();

    if (!profile) {
      return new Response(JSON.stringify({ ok: false, reason: 'user_not_found', error: 'Email не зарегистрирован' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    let mobile: string;
    try {
      mobile = normalizeUzPhone(profile.phone || '');
    } catch {
      return new Response(JSON.stringify({ ok: false, reason: 'no_phone', error: 'У аккаунта не указан номер телефона' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const { data: last } = await supabase
      .from('sms_reset_codes')
      .select('created_at')
      .eq('user_id', profile.id)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (last && Date.now() - new Date(last.created_at).getTime() < COOLDOWN_SEC * 1000) {
      return new Response(JSON.stringify({ ok: false, reason: 'too_soon', error: 'Код уже отправлен, подождите немного' }), {
        status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await supabase.from('sms_reset_codes').delete().eq('user_id', profile.id).is('used_at', null);

    const code = String(Math.floor(100000 + Math.random() * 900000));
    const codeHash = await sha256Hex(`${mobile}:${code}`);
    const expiresAt = new Date(Date.now() + CODE_TTL_MIN * 60 * 1000).toISOString();

    const { error: insErr } = await supabase
      .from('sms_reset_codes')
      .insert({ user_id: profile.id, phone: mobile, code_hash: codeHash, expires_at: expiresAt });
    if (insErr) throw insErr;

    await sendSms(mobile, `Aquality: код для сброса пароля ${code}. Никому не сообщайте его.`);

    return new Response(JSON.stringify({ ok: true, phone: maskPhone(mobile) }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[send-sms-reset]', err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
