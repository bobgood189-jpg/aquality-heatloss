# PERF_BASELINE — до оптимизации (03.07.2026)

Условия замера: Playwright Chromium headless, CPU throttling ×6 (CDP), сеть Fast 3G
(1.6 Мбит/с down / 750 Кбит/с up / RTT 150 мс), viewport 390×844, локальный сервер.

## Метрики (baseline)

| Метрика | Значение |
|---|---|
| First Paint | **6.82 с** |
| First Contentful Paint | **7.30 с** |
| Заголовок hero виден (poll) | ~8.5 с |
| Формы/JS интерактивны (openSettings готов) | **9.85 с** |
| DOMContentLoaded | 9.63 с |
| load | 10.02 с |
| Передано (главный документ) | 1 503 542 Б (~1.47 МБ, без gzip на локальном сервере) |

До FCP пользователь видит чёрный экран ~7 секунд: браузер качает и парсит весь
1.5 МБ HTML (внутри — мегабайт JS), затем Tailwind CDN JIT-компилирует стили по
всему DOM, и только потом появляется первый кадр.

## Состав index.html (1338.6 КБ, 20 389 строк)

| Блок | Строки | Размер |
|---|---|---|
| inline script: тема (анти-FOUC) | 5–12 | 0.3 КБ |
| inline script: tailwind.config | 44–55 | 0.4 КБ |
| inline script: PerfManager | 62–313 | 9.6 КБ |
| style #1 (лоадер) | 314–348 | 2.2 КБ |
| inline script: AQ_CONFIG | 357–378 | 1.2 КБ |
| style #2 — основной CSS | 381–1897 | 129.3 КБ |
| HTML-разметка body | 1899–2699 | 59.3 КБ |
| **inline script: главный JS приложения** | **2700–19645** | **1084.9 КБ** |
| inline script: hviz-canvas и пр. | 19646–19981 | 19.7 КБ |
| style #3 (SX workspace) | 19988–20050 | 5.1 КБ |
| inline script: SX workspace | 20066–20386 | 21.1 КБ |

## `<script>` / `<link>` в `<head>` (до оптимизации)

| Ресурс | Тип | Режим |
|---|---|---|
| inline тема (строка 5) | script | синхронный (нужен до рендера — анти-FOUC) |
| inline tailwind.config (строка 44) | script | синхронный |
| `https://cdn.tailwindcss.com` | script | **синхронный, блокирует рендер** (JIT-компилятор ~350 КБ + компиляция на CPU) |
| `gsap.min.js` (cdnjs) | script | **синхронный, блокирует рендер** (26 КБ) |
| `ScrollTrigger.min.js` (cdnjs) | script | **синхронный, блокирует рендер** (16 КБ) |
| `lenis.min.js` (jsdelivr) | script | **синхронный, блокирует рендер** (4 КБ) |
| `three.min.js` r128 (cdnjs) | script | **синхронный, блокирует рендер** (121 КБ) |
| `OrbitControls.js` (jsdelivr) | script | **синхронный, блокирует рендер** (6 КБ) |
| inline PerfManager (строка 62) | script | синхронный |
| inline AQ_CONFIG (строка 357) | script | синхронный |
| Google Fonts css2 (Manrope + JetBrains Mono) | link stylesheet | **блокирует рендер** |
| preconnect fonts.googleapis.com / fonts.gstatic.com | link | ок |
| Supabase JS (umd) | script | уже лениво — динамическая вставка из JS |

## Ошибки консоли (baseline)

- `404 shop.jpg` — файла нет в репозитории; у `<img id="bg-img">` есть `onerror`,
  который прячет элемент → не критично, инициализацию не роняет.
- Предупреждение `cdn.tailwindcss.com should not be used in production` — уйдёт в Шаге 1.
- `pageerror` (фатальных ранних JS-ошибок): **нет**. «Вечный чёрный экран» на слабых
  устройствах объясняется не ошибкой, а стоимостью загрузки/парсинга/JIT до первой отрисовки.

## Примечание к скриншотам

Headless-скриншоты Playwright сами форсируют кадр рендера и под троттлингом
завершаются позже запрошенной отметки времени, поэтому для критерия «контент ≤ 3 с»
используются in-page paint-метрики (`performance.getEntriesByType('paint')`) — они
совпадают с расчётным временем передачи 1.5 МБ по Fast 3G (~7.3 с).

Скриншоты baseline: `docs/perf/base_{1,3,5,10}s.png` (доступ снаружи закрыт через `_redirects`).
Итоги оптимизации: см. `PERF_REPORT.md`.
