import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY') || '';
const FROM_EMAIL     = Deno.env.get('NOTIFY_FROM') || 'noreply@aquality.uz';
const FROM_NAME      = 'Aquality WaterPro';

async function sendOtpEmail(to: string, otp: string) {
  const html = `
<!DOCTYPE html>
<html lang="ru">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#07090F;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#07090F;padding:40px 0">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#0D1117;border-radius:16px;border:1px solid rgba(194,112,61,.25);overflow:hidden;max-width:95%">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#1a0f00,#0D1117);padding:28px 36px;border-bottom:1px solid rgba(194,112,61,.2)">
          <table cellpadding="0" cellspacing="0"><tr>
            <td style="width:40px;height:40px;background:rgba(194,112,61,.15);border-radius:10px;text-align:center;vertical-align:middle;border:1px solid rgba(194,112,61,.3)">
              <span style="font-size:20px;line-height:40px">🔥</span>
            </td>
            <td style="padding-left:12px">
              <div style="color:#ECF0FA;font-size:16px;font-weight:700;letter-spacing:.5px">Aquality <span style="color:#C2703D">·</span> WaterPro</div>
              <div style="color:rgba(148,163,184,.5);font-size:11px;letter-spacing:1.5px;text-transform:uppercase;margin-top:2px">Расчёт теплопотерь</div>
            </td>
          </tr></table>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:36px 36px 28px">
          <p style="color:rgba(148,163,184,.7);font-size:14px;margin:0 0 24px">Ваш код подтверждения для входа:</p>

          <!-- OTP block -->
          <div style="background:rgba(194,112,61,.08);border:1px solid rgba(194,112,61,.3);border-radius:12px;padding:24px;text-align:center;margin:0 0 28px">
            <div style="letter-spacing:14px;font-size:44px;font-weight:800;color:#ECF0FA;font-variant-numeric:tabular-nums;margin-left:14px">${otp}</div>
          </div>

          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0 0 8px">⏱ Код действует <b style="color:rgba(148,163,184,.8)">10 минут</b></p>
          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0">🔒 Никому не передавайте этот код, в том числе сотрудникам Aquality</p>
        </td></tr>

        <!-- Footer -->
        <tr><td style="padding:20px 36px;border-top:1px solid rgba(140,165,210,.08)">
          <p style="color:rgba(148,163,184,.3);font-size:11px;margin:0;text-align:center">
            Если вы не запрашивали этот код — просто проигнорируйте письмо.<br>
            © Aquality WaterPro · Фергана, Узбекистан
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>`;

  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: `${FROM_NAME} <${FROM_EMAIL}>`,
      to,
      subject: `${otp} — ваш код входа в Aquality WaterPro`,
      html,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Resend error ${res.status}: ${text}`);
  }
  return res.json();
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const { email } = await req.json();
    if (!email) {
      return new Response(JSON.stringify({ error: 'email required' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    );

    // Generate OTP via Supabase Admin — extracts 6-digit email_otp
    const { data, error } = await supabase.auth.admin.generateLink({
      type: 'magiclink',
      email,
    });

    if (error) {
      const msg = /user not found/i.test(error.message)
        ? 'Пользователь с таким email не найден'
        : error.message;
      return new Response(JSON.stringify({ error: msg }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const otp = data?.properties?.email_otp;
    if (!otp) {
      return new Response(JSON.stringify({ error: 'OTP generation failed' }), {
        status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (!RESEND_API_KEY) {
      console.warn('[send-otp] RESEND_API_KEY not set — skipping email, otp:', otp);
      return new Response(JSON.stringify({ ok: true, skipped: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await sendOtpEmail(email, otp);

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[send-otp]', err);
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
