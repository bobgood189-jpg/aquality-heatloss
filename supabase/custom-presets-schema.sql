-- Мастерская: пользовательские конструкции (стены/окна/двери/полы/потолки)
-- Сайт зеркалит localStorage-ключ aq_custom_presets_v1 в профиль,
-- чтобы конструкции были доступны с любого устройства.
-- Применить в Supabase SQL Editor (проект ocrgpmlhtjghiamhbrhv).
-- Если колонку не применять — сайт продолжает работать только с localStorage.

alter table public.profiles
  add column if not exists custom_presets jsonb;

comment on column public.profiles.custom_presets is
  'Пользовательские конструкции Мастерской: {walls:[],windows:[],doors:[],floors:[],ceilings:[]}; элемент {id,name,r,desc,layers:[{name,d(мм),l(λ)}],n?,env?}';

-- Личная библиотека материалов слоёв («Мои материалы»): свои {name, λ} под свой вкус.
-- Сайт зеркалит localStorage-ключ aq_custom_mats_v1. Не применять — работает только локально.
alter table public.profiles
  add column if not exists custom_mats jsonb;

comment on column public.profiles.custom_mats is
  'Личные материалы слоёв: [{id,name,lambda,group}] — подмешиваются в автодополнение λ редактора конструкций';
