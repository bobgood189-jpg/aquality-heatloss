/** Tailwind config — перенесён 1:1 из inline `tailwind.config` в index.html
 *  (Шаг 1 перф-оптимизации: CDN JIT → статическая сборка).
 *  Сборка: npm run build:css  →  assets/tailwind.css
 *  content сканирует и index.html, и вынесенные JS-файлы (классы в
 *  JS-шаблонах собираются из полных литеральных строк — сканер их видит).
 */
module.exports = {
  content: ['./index.html', './assets/*.js', './nano-fx.js'],
  theme: {
    extend: {
      colors: {
        'w950':'#07090F','w900':'#0B0F1A','w850':'#111827','w800':'#1C2438',
        'amber':'#f59e0b','ember':'#EF4444','copper':'#F97316',
        'cream':'#ECF0FA','sand':'#8FA3C0','muted':'#4E6080','gold':'#FCD34D'
      },
      fontFamily: {
        sans: ['Manrope','system-ui','sans-serif'],
        mono: ['JetBrains Mono','monospace']
      }
    }
  },
  // Классы, которые могли бы собираться динамически, в этом проекте всегда
  // присутствуют полными строками в сканируемых файлах — safelist пуст.
  safelist: []
};
