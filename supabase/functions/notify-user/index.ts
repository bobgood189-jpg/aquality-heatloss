import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY') || '';
const FROM_EMAIL     = Deno.env.get('NOTIFY_FROM')    || 'noreply@aquality.uz';
const SITE_NAME      = 'AQuality Теплопотери';

type NotifyType =
  | 'subscription_activated'
  | 'subscription_expiry_warning'
  | 'subscription_expired';

interface NotifyPayload {
  type: NotifyType;
  user_id: string;
  plan?: string;
  amount?: number;
  days_left?: number;
  expires_at?: string;
}

const PLAN_NAMES: Record<string, string> = {
  m1:  '1 месяц',
  m6:  '6 месяцев',
  m12: '12 месяцев',
};

function planLabel(plan: string) {
  return PLAN_NAMES[plan] || plan;
}

function fmtSum(n: number) {
  return new Intl.NumberFormat('ru-RU').format(Math.round(n)) + ' сум';
}

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('ru-RU', {
    day: 'numeric', month: 'long', year: 'numeric',
  });
}

function buildEmail(payload: NotifyPayload, userEmail: string, userName: string) {
  const { type, plan, amount, days_left, expires_at } = payload;

  if (type === 'subscription_activated') {
    const planStr  = planLabel(plan || '');
    const amtStr   = amount ? fmtSum(amount) : '—';
    const expStr   = expires_at ? fmtDate(expires_at) : '—';
    return {
      subject: `✅ Подписка активирована — ${SITE_NAME}`,
      html: `
<div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
  <h2 style="color:#d97706">Подписка активирована!</h2>
  <p>Здравствуйте, <b>${userName}</b>!</p>
  <p>Ваша подписка на <b>${SITE_NAME}</b> успешно активирована.</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:8px;background:#f9f7f2;border-radius:4px 0 0 4px;font-weight:600;width:40%">Тариф</td>
        <td style="padding:8px;background:#f9f7f2">${planStr}</td></tr>
    <tr><td style="padding:8px;font-weight:600">Сумма</td>
        <td style="padding:8px">${amtStr}</td></tr>
    <tr><td style="padding:8px;background:#f9f7f2;font-weight:600">Действует до</td>
        <td style="padding:8px;background:#f9f7f2">${expStr}</td></tr>
  </table>
  <p>Теперь вам доступны все функции калькулятора теплопотерь.</p>
  <p style="color:#6b7280;font-size:12px;margin-top:24px">Это письмо отправлено автоматически — отвечать не нужно.</p>
</div>`,
    };
  }

  if (type === 'subscription_expiry_warning') {
    const dStr = days_left === 1 ? 'завтра' : `через ${days_left} дн.`;
    const expStr = expires_at ? fmtDate(expires_at) : '—';
    return {
      subject: `⚠️ Подписка истекает ${dStr} — ${SITE_NAME}`,
      html: `
<div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
  <h2 style="color:#d97706">Срок подписки заканчивается</h2>
  <p>Здравствуйте, <b>${userName}</b>!</p>
  <p>Ваша подписка на <b>${SITE_NAME}</b> истекает <b>${expStr}</b> (${dStr}).</p>
  <p>Продлите подписку заранее, чтобы не потерять доступ к расчётам.</p>
  <p style="color:#6b7280;font-size:12px;margin-top:24px">Это письмо отправлено автоматически — отвечать не нужно.</p>
</div>`,
    };
  }

  if (type === 'subscription_expired') {
    return {
      subject: `❌ Подписка истекла — ${SITE_NAME}`,
      html: `
<div style="font-family:sans-serif;max-width:560px;margin:0 auto;color:#1a1a1a">
  <h2 style="color:#dc2626">Срок подписки истёк</h2>
  <p>Здравствуйте, <b>${userName}</b>!</p>
  <p>Ваша подписка на <b>${SITE_NAME}</b> истекла. Доступ к расчётам временно ограничен.</p>
  <p>Свяжитесь с нами для продления: <a href="https://t.me/aqualityHL">@aqualityHL</a></p>
  <p style="color:#6b7280;font-size:12px;margin-top:24px">Это письмо отправлено автоматически — отвечать не нужно.</p>
</div>`,
    };
  }

  return null;
}

async function sendViaResend(to: string, subject: string, html: string) {
  const res = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${RESEND_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ from: FROM_EMAIL, to, subject, html }),
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
    const payload: NotifyPayload = await req.json();
    if (!payload.user_id || !payload.type) {
      return new Response(JSON.stringify({ error: 'Missing user_id or type' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!,
    );

    // Get user email + name from profiles
    const { data: prof } = await supabase
      .from('profiles')
      .select('full_name, email')
      .eq('id', payload.user_id)
      .maybeSingle();

    // Fallback: get email from auth.users
    let userEmail = prof?.email || '';
    let userName  = prof?.full_name || 'Пользователь';

    if (!userEmail) {
      const { data: { user } } = await supabase.auth.admin.getUserById(payload.user_id);
      userEmail = user?.email || '';
      if (!userName || userName === 'Пользователь') userName = user?.email || 'Пользователь';
    }

    if (!userEmail) {
      return new Response(JSON.stringify({ error: 'User email not found' }), {
        status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // If no Resend key — log and skip silently
    if (!RESEND_API_KEY) {
      console.warn('[notify-user] RESEND_API_KEY not set — email skipped');
      return new Response(JSON.stringify({ ok: true, skipped: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const mail = buildEmail(payload, userEmail, userName);
    if (!mail) {
      return new Response(JSON.stringify({ error: 'Unknown notification type' }), {
        status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    await sendViaResend(userEmail, mail.subject, mail.html);

    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (err) {
    console.error('[notify-user]', err);
    return new Response(JSON.stringify({ error: String(err) }), {
      status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
