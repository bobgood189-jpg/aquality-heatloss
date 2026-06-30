import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY') || '';
const FROM_EMAIL     = Deno.env.get('NOTIFY_FROM') || 'noreply@aquality.uz';
const FROM_NAME      = 'Aquality WaterPro';
const SITE_URL       = Deno.env.get('SITE_URL') || 'https://aquality-hl.netlify.app';

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json' },
  });
}

function emailHeader() {
  return `
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
    </td></tr>`;
}

function emailFooter() {
  return `
    <tr><td style="padding:20px 36px;border-top:1px solid rgba(140,165,210,.08)">
      <p style="color:rgba(148,163,184,.3);font-size:11px;margin:0;text-align:center">
        Если вы не запрашивали это письмо — просто проигнорируйте его.<br>
        © Aquality WaterPro · Фергана, Узбекистан
      </p>
    </td></tr>`;
}

async function sendEmail(to: string, subject: string, html: string) {
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ from: `${FROM_NAME} <${FROM_EMAIL}>`, to, subject, html }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Resend error ${res.status}: ${text}`);
  }
  return res.json();
}

async function sendInviteEmail(to: string) {
  const html = `
<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#07090F;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#07090F;padding:40px 0">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#0D1117;border-radius:16px;border:1px solid rgba(194,112,61,.25);overflow:hidden;max-width:95%">
        ${emailHeader()}
        <tr><td style="padding:36px 36px 28px">
          <p style="color:rgba(148,163,184,.7);font-size:14px;margin:0 0 16px">Этот адрес электронной почты не зарегистрирован в системе <b style="color:#ECF0FA">Aquality WaterPro</b>.</p>
          <p style="color:rgba(148,163,184,.7);font-size:14px;margin:0 0 28px">Чтобы воспользоваться профессиональным расчётом теплопотерь, создайте бесплатный аккаунт по кнопке ниже:</p>
          <div style="text-align:center;margin:0 0 28px">
            <a href="${SITE_URL}" style="display:inline-block;background:linear-gradient(135deg,#C2703D,#F59E0B);color:#0D1117;font-size:15px;font-weight:700;padding:14px 36px;border-radius:12px;text-decoration:none;letter-spacing:.3px">Зарегистрироваться →</a>
          </div>
          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0">🔒 Если вы не запрашивали этот email — просто проигнорируйте письмо.</p>
        </td></tr>
        ${emailFooter()}
      </table>
    </td></tr>
  </table>
</body></html>`;
  await sendEmail(to, 'Приглашение зарегистрироваться в Aquality WaterPro', html);
}

async function sendOtpEmail(to: string, otp: string) {
  const html = `
<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#07090F;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#07090F;padding:40px 0">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#0D1117;border-radius:16px;border:1px solid rgba(194,112,61,.25);overflow:hidden;max-width:95%">
        ${emailHeader()}
        <tr><td style="padding:36px 36px 28px">
          <p style="color:rgba(148,163,184,.7);font-size:14px;margin:0 0 24px">Ваш код подтверждения для входа:</p>
          <div style="background:rgba(194,112,61,.08);border:1px solid rgba(194,112,61,.3);border-radius:12px;padding:24px;text-align:center;margin:0 0 28px">
            <div style="letter-spacing:14px;font-size:44px;font-weight:800;color:#ECF0FA;font-variant-numeric:tabular-nums;margin-left:14px">${otp}</div>
          </div>
          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0 0 8px">⏱ Код действует <b style="color:rgba(148,163,184,.8)">10 минут</b></p>
          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0">🔒 Никому не передавайте этот код, в том числе сотрудникам Aquality</p>
        </td></tr>
        ${emailFooter()}
      </table>
    </td></tr>
  </table>
</body></html>`;
  await sendEmail(to, `${otp} — ваш код входа в Aquality WaterPro`, html);
}

async function sendPasswordResetEmail(to: string, code: string) {
  const html = `
<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#07090F;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#07090F;padding:40px 0">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#0D1117;border-radius:16px;border:1px solid rgba(194,112,61,.25);overflow:hidden;max-width:95%">
        ${emailHeader()}
        <tr><td style="padding:36px 36px 28px">
          <p style="color:rgba(148,163,184,.7);font-size:14px;margin:0 0 8px">Вы запросили сброс пароля для аккаунта <b style="color:#ECF0FA">${to}</b>.</p>
          <p style="color:rgba(148,163,184,.7);font-size:14px;margin:0 0 24px">Введите этот код на сайте, чтобы установить новый пароль:</p>
          <div style="background:rgba(194,112,61,.08);border:1px solid rgba(194,112,61,.3);border-radius:12px;padding:24px;text-align:center;margin:0 0 28px">
            <div style="letter-spacing:14px;font-size:44px;font-weight:800;color:#ECF0FA;font-variant-numeric:tabular-nums;margin-left:14px">${code}</div>
          </div>
          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0 0 8px">⏱ Код действует <b style="color:rgba(148,163,184,.8)">10 минут</b></p>
          <p style="color:rgba(148,163,184,.5);font-size:13px;margin:0">🔒 Никому не передавайте этот код. Если вы не запрашивали сброс — ваш пароль в безопасности.</p>
        </td></tr>
        ${emailFooter()}
      </table>
    </td></tr>
  </table>
</body></html>`;
  await sendEmail(to, `${code} — код подтверждения для сброса пароля Aquality WaterPro`, html);
}

Deno.serve(async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders });
  }

  try {
    const body = await req.json();
    const { email, action, type, code: inputCode, newPassword } = body;

    if (!email) return json({ error: 'email required' }, 400);

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    );

    // ── Existing: invite email for unregistered users ──
    if (action === 'invite') {
      if (RESEND_API_KEY) await sendInviteEmail(email);
      else console.warn('[send-otp] RESEND_API_KEY not set — invite email skipped:', email);
      return json({ ok: true });
    }

    // ── New: send 6-digit password reset code ──
    if (type === 'password_reset') {
      // Use generateLink to check user existence and obtain their ID
      const { data: linkData, error: linkErr } = await supabase.auth.admin.generateLink({
        type: 'magiclink',
        email,
      });

      if (linkErr || !linkData?.user?.id) {
        // User not found → send invite email (neutral response to caller)
        if (RESEND_API_KEY) await sendInviteEmail(email);
        else console.warn('[send-otp] unregistered:', email);
        return json({ ok: true });
      }

      const userId = linkData.user.id;
      const code = String(Math.floor(100000 + Math.random() * 900000));
      const expiresAt = new Date(Date.now() + 10 * 60 * 1000).toISOString();

      // Remove old unused codes for this email
      await supabase.from('otp_codes')
        .delete()
        .eq('email', email)
        .eq('type', 'password_reset')
        .eq('used', false);

      // Store new code
      const { error: insertErr } = await supabase.from('otp_codes').insert({
        email,
        user_id: userId,
        code,
        type: 'password_reset',
        expires_at: expiresAt,
      });
      if (insertErr) {
        console.error('[send-otp] insert otp_codes:', insertErr);
        return json({ error: 'Внутренняя ошибка сервера' }, 500);
      }

      if (RESEND_API_KEY) await sendPasswordResetEmail(email, code);
      else console.warn('[send-otp] RESEND_API_KEY not set — reset code:', code);

      return json({ ok: true });
    }

    // ── New: verify code + update password ──
    if (type === 'verify_reset') {
      if (!inputCode || !newPassword) return json({ error: 'code and newPassword required' }, 400);
      if (newPassword.length < 6) return json({ error: 'Пароль должен быть не менее 6 символов' }, 400);

      const { data: row, error: rowErr } = await supabase.from('otp_codes')
        .select('id, user_id')
        .eq('email', email)
        .eq('code', String(inputCode))
        .eq('type', 'password_reset')
        .eq('used', false)
        .gte('expires_at', new Date().toISOString())
        .single();

      if (rowErr || !row) return json({ error: 'Неверный или просроченный код' }, 400);

      // Mark as used before updating password (prevents replay attacks)
      await supabase.from('otp_codes').update({ used: true }).eq('id', row.id);

      const { error: updateErr } = await supabase.auth.admin.updateUserById(
        row.user_id,
        { password: newPassword },
      );
      if (updateErr) return json({ error: updateErr.message }, 400);

      return json({ ok: true });
    }

    // ── Existing: login OTP via Supabase magic link ──
    const { data, error } = await supabase.auth.admin.generateLink({
      type: 'magiclink',
      email,
    });

    if (error) {
      const msg = /user not found/i.test(error.message)
        ? 'Пользователь с таким email не найден'
        : error.message;
      return json({ error: msg }, 400);
    }

    const otp = data?.properties?.email_otp;
    if (!otp) return json({ error: 'OTP generation failed' }, 500);

    if (!RESEND_API_KEY) {
      console.warn('[send-otp] RESEND_API_KEY not set — skipping email, otp:', otp);
      return json({ ok: true, skipped: true });
    }

    await sendOtpEmail(email, otp);
    return json({ ok: true });

  } catch (err) {
    console.error('[send-otp]', err);
    return json({ error: String(err) }, 500);
  }
});
