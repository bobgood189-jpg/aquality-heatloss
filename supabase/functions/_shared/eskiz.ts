// Клиент Eskiz.uz SMS API (https://documenter.getpostman.com/view/663428/RzfmES4z).
// Используется Edge Functions send-sms-otp / verify-sms-otp.
//
// Секреты (проект ocrgpmlhtjghiamhbrhv), НЕ коммитить:
//   supabase secrets set ESKIZ_EMAIL=bobgood189@gmail.com
//   supabase secrets set ESKIZ_PASSWORD=...
//   supabase secrets set ESKIZ_FROM=4546   (ник отправителя — до модерации Eskiz
//                                            принимает только текст "Bu Eskiz dan test")
//
// ESKIZ_TOKEN сознательно НЕ хранится как секрет: токен получается через
// /auth/login и живёт в памяти процесса Edge Function, с релогином при 401
// и явным /auth/refresh раз в сутки (сам токен у Eskiz живёт 30 дней).
// Инстансы Edge Functions недолговечны, поэтому кэш — это оптимизация для
// тёплых повторных вызовов, а не единственная линия защиты: релогин при 401
// всегда подстрахует холодный старт.

const ESKIZ_BASE = 'https://notify.eskiz.uz/api';
const EMAIL    = Deno.env.get('ESKIZ_EMAIL') || '';
const PASSWORD = Deno.env.get('ESKIZ_PASSWORD') || '';
const FROM     = Deno.env.get('ESKIZ_FROM') || '4546';

let _token: string | null = null;
let _tokenAt = 0;

const TOKEN_REFRESH_AFTER_MS = 24 * 60 * 60 * 1000;

async function login(): Promise<string> {
  if (!EMAIL || !PASSWORD) {
    throw new Error('ESKIZ_EMAIL / ESKIZ_PASSWORD не заданы (supabase secrets set ...)');
  }
  const body = new URLSearchParams({ email: EMAIL, password: PASSWORD });
  const res = await fetch(`${ESKIZ_BASE}/auth/login`, { method: 'POST', body });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Eskiz login ${res.status}: ${text}`);
  }
  const data = await res.json();
  const token = data?.data?.token;
  if (!token) throw new Error(`Eskiz login: токен не получен (${JSON.stringify(data)})`);
  _token = token;
  _tokenAt = Date.now();
  return token;
}

async function refresh(): Promise<string> {
  if (!_token) return login();
  const res = await fetch(`${ESKIZ_BASE}/auth/refresh`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${_token}` },
  });
  if (!res.ok) return login();
  const data = await res.json();
  const token = data?.data?.token;
  if (!token) return login();
  _token = token;
  _tokenAt = Date.now();
  return token;
}

export async function getEskizToken(forceNew = false): Promise<string> {
  if (forceNew) return login();
  if (!_token) return login();
  if (Date.now() - _tokenAt > TOKEN_REFRESH_AFTER_MS) return refresh();
  return _token;
}

// 998XXXXXXXXX — формат, который принимает Eskiz. Понимает и «+998 90 000-00-00»,
// и «901234567» (9 цифр без кода страны).
export function normalizeUzPhone(raw: string): string {
  const digits = String(raw || '').replace(/\D/g, '');
  if (digits.length === 9) return `998${digits}`;
  if (digits.length === 12 && digits.startsWith('998')) return digits;
  throw new Error(`Некорректный номер телефона: ${raw}`);
}

export async function sendSms(phone: string, message: string): Promise<{ id?: string }> {
  const mobile = normalizeUzPhone(phone);
  let token = await getEskizToken();

  const doSend = (tok: string) => {
    const body = new URLSearchParams({ mobile_phone: mobile, message, from: FROM });
    return fetch(`${ESKIZ_BASE}/message/sms/send`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${tok}` },
      body,
    });
  };

  let res = await doSend(token);
  if (res.status === 401) {
    token = await getEskizToken(true);
    res = await doSend(token);
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Eskiz sendSms ${res.status}: ${text}`);
  }
  const data = await res.json();
  if (data?.status && !['waiting', 'success'].includes(data.status)) {
    throw new Error(`Eskiz sendSms: ${JSON.stringify(data)}`);
  }
  return { id: data?.id };
}
