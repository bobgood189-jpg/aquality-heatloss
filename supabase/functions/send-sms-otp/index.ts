// Отправляет 6-значный код подтверждения телефона по SMS через Eskiz.uz.
// Код хранится только хешем (sha256(phone:code)) в public.sms_otp_codes —
// см. supabase/otp-sms-schema.sql. Проверка — verify-sms-otp.
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { sendSms, normalizeUzPhone } from '../_shared/eskiz.ts';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const CODE_TTL_MIN = 5;
const COOLDOWN_SEC = 30;

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { phone } = await req.json();
    if (!phone) {
      return new Response(JSON.stringify({ ok: false, error: 'phone required' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    let mobile: string;
    try {
      mobile = normalizeUzPhone(phone);
    } catch {
      return new Response(JSON.stringify({ ok: false, reason: 'bad_phone', error: 'Некорректный номер телефона' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    );

    const { data: last } = await supabase
      .from('sms_otp_codes')
      .select('created_at')
      .eq('phone', mobile)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (last && Date.now() - new Date(last.created_at).getTime() < COOLDOWN_SEC * 1000) {
      return new Response(JSON.stringify({ ok: false, reason: 'too_soon', error: 'Код уже отправлен, подождите немного' }), {
        status: 429, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await supabase.from('sms_otp_codes').delete().eq('phone', mobile).is('used_at', null);

    const code = String(Math.floor(100000 + Math.random() * 900000));
    const codeHash = await sha256Hex(`${mobile}:${code}`);
    const expiresAt = new Date(Date.now() + CODE_TTL_MIN * 60 * 1000).toISOString();

    const { error: insErr } = await supabase
      .from('sms_otp_codes')
      .insert({ phone: mobile, code_hash: codeHash, expires_at: expiresAt });
    if (insErr) throw insErr;

    await sendSms(mobile, `Aquality: код подтверждения ${code}. Никому не сообщайте его.`);

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[send-sms-otp]', err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
