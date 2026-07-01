-- ============================================================================
-- Вход на сайт по НОМЕРУ ТЕЛЕФОНА или EMAIL.
--
-- Supabase signInWithPassword умеет только email. Эта функция превращает
-- введённый логин в email: если это email — возвращает как есть; если телефон —
-- ищет профиль по последним 9 цифрам (формат UZ-номера) в phone/phone2 и
-- возвращает его email. Если не нашли — возвращает введённое как есть (тогда
-- вход просто не пройдёт с «неверный логин»).
--
-- Вызывается ДО логина (анонимно), поэтому GRANT для anon/authenticated.
-- Компромисс приватности: по номеру можно узнать email (перебор). Это
-- осознанно — иначе вход по телефону невозможен без SMS-провайдера.
--
-- Идемпотентно. Требует schema.sql (profiles.phone/phone2/email/updated_at).
-- ============================================================================
CREATE OR REPLACE FUNCTION public.resolve_login_email(p_login TEXT)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  v_in    TEXT := TRIM(COALESCE(p_login, ''));
  v_dig   TEXT;
  v_tail  TEXT;
  v_email TEXT;
BEGIN
  IF v_in = '' THEN
    RETURN v_in;
  END IF;

  -- Похоже на email — возвращаем как есть (в нижнем регистре).
  IF position('@' IN v_in) > 0 THEN
    RETURN lower(v_in);
  END IF;

  -- Иначе трактуем как телефон: сравниваем только цифры, по последним 9.
  v_dig := regexp_replace(v_in, '\D', '', 'g');
  IF length(v_dig) < 7 THEN
    RETURN v_in;
  END IF;
  v_tail := right(v_dig, 9);

  SELECT email INTO v_email
  FROM public.profiles
  WHERE email IS NOT NULL
    AND (
      regexp_replace(COALESCE(phone,  ''), '\D', '', 'g') LIKE '%' || v_tail
      OR regexp_replace(COALESCE(phone2, ''), '\D', '', 'g') LIKE '%' || v_tail
    )
  ORDER BY updated_at DESC NULLS LAST
  LIMIT 1;

  RETURN COALESCE(v_email, v_in);
END;
$$;

GRANT EXECUTE ON FUNCTION public.resolve_login_email(TEXT) TO anon, authenticated;

-- ============================================================================
-- ГОТОВО. Применяется автоматически через Management API в этой сессии, либо
-- вручную: Supabase Dashboard → SQL Editor → выполнить этот файл.
-- ============================================================================
