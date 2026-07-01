# Email-шаблоны Supabase — 6-значный код вместо ссылки

Сайт подтверждает почту **6-значным кодом**, который пользователь вводит в приложении
(`supabase.auth.verifyOtp`). Чтобы письма приходили с кодом, а не со ссылкой, надо
один раз заменить стандартные шаблоны Supabase на эти.

## Как применить (2 минуты, один раз)

Supabase Dashboard → проект `ocrgpmlhtjghiamhbrhv` → **Authentication → Emails → Templates**:

| Шаблон Supabase   | Файл                | Subject (тема письма)                                          |
|-------------------|---------------------|---------------------------------------------------------------|
| **Confirm signup**| `confirmation.html` | `Код подтверждения: {{ .Token }} — Aquality WaterPro`         |
| **Reset Password**| `recovery.html`     | `Код для смены пароля: {{ .Token }} — Aquality WaterPro`      |
| **Magic Link**    | `magic_link.html`   | `Код входа: {{ .Token }} — Aquality WaterPro`                 |

Для каждого шаблона: вставьте содержимое соответствующего `.html` в поле *Message body*,
пропишите Subject, нажмите **Save**.

Ключевой момент: в теле письма стоит `{{ .Token }}` (6 цифр), а **не** `{{ .ConfirmationURL }}`.
Именно `{{ .ConfirmationURL }}` давал ссылку, которая выдавала ошибку при клике.

## Проверки в настройках Auth (должно быть так)

- **Authentication → Providers → Email → Confirm email** = ON (иначе почта не проверяется).
- **Authentication → URL Configuration → Site URL** — на боевой домен сайта.
- Лимит писем на встроенном мейлере Supabase небольшой (несколько в час). Для боевого
  потока клиентов подключите SMTP (Resend): **Authentication → Emails → SMTP Settings**
  → host `smtp.resend.com`, port `465`, user `resend`, password = `RESEND_API_KEY`,
  sender `noreply@aquality.uz` (домен должен быть верифицирован в Resend).
  Тогда те же письма с кодом уходят через Resend без лимитов.

## Почему так, а не через edge-функции

Раньше код слался кастомной функцией `register`/`send-signup-otp` через Resend. Это работало
только при заданном `RESEND_API_KEY` и верифицированном домене; `send-otp` (сброс пароля)
вообще не был задеплоен. Нативный путь Supabase надёжнее: письмо шлёт сам Supabase по этим
шаблонам, профиль создаётся триггером `handle_new_user`, отдельные функции и ключи не нужны.
Edge-функции можно оставить как есть — фронт их больше не вызывает.
