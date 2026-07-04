// Проверяет код, отправленный send-sms-otp. При успехе помечает запись
// used_at — дальше сайт вызывает RPC confirm_phone_verified(phone) от имени
// залогиненного пользователя, чтобы перенести факт подтверждения на profiles.
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

function normalizeUzPhone(raw: string): string {
  const digits = String(raw || '').replace(/\D/g, '');
  if (digits.length === 9) return `998${digits}`;
  if (digits.length === 12 && digits.startsWith('998')) return digits;
  throw new Error(`bad phone: ${raw}`);
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { phone, code } = await req.json();
    if (!phone || !code) {
      return new Response(JSON.stringify({ ok: false, error: 'phone and code required' }), {
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

    const { data: rec } = await supabase
      .from('sms_otp_codes')
      .select('id, code_hash, attempts, max_attempts, expires_at')
      .eq('phone', mobile)
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

    const inputHash = await sha256Hex(`${mobile}:${String(code).trim()}`);
    if (inputHash !== rec.code_hash) {
      await supabase.from('sms_otp_codes').update({ attempts: rec.attempts + 1 }).eq('id', rec.id);
      return new Response(JSON.stringify({ ok: false, reason: 'invalid_code', error: GENERIC_ERROR }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await supabase.from('sms_otp_codes').update({ used_at: new Date().toISOString() }).eq('id', rec.id);

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[verify-sms-otp]', err);
    return new Response(JSON.stringify({ ok: false, error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
