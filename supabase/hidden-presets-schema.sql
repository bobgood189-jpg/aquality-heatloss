-- Скрытые встроенные пресеты каталога (стены/окна/двери/полы/потолки).
-- Пользователь прячет ненужные встроенные материалы из списка; сайт зеркалит
-- localStorage-ключ aq_hidden_presets_v1 в профиль, чтобы скрытие переносилось
-- между устройствами.
-- Применить в Supabase SQL Editor (проект ocrgpmlhtjghiamhbrhv).
-- Если колонку не применять — сайт продолжает работать только с localStorage.

alter table public.profiles
  add column if not exists hidden_presets jsonb;

comment on column public.profiles.hidden_presets is
  'Скрытые встроенные пресеты каталога: {walls:[id...],windows:[],doors:[],floors:[],ceilings:[]} — только id встроенных BASE_PRESETS; свои конструкции удаляются, а не скрываются';
