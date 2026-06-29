#!/usr/bin/env node
/*
 * encrypt.js — StatiCrypt-подход для Aquality.
 *
 * Берёт открытый index.html и шифрует его целиком (AES-256-GCM,
 * ключ выводится из пароля через PBKDF2-SHA256). На выходе —
 * index.protected.html: самодостаточная страница, которая без
 * правильного пароля показывает только заставку, а весь реальный
 * контент держит зашифрованным прямо в файле.
 *
 * Расшифровка происходит в браузере на штатном Web Crypto API —
 * никаких внешних библиотек.
 *
 * Использование:
 *   SITE_PASSWORD='ваш-пароль' node scripts/encrypt.js
 *   node scripts/encrypt.js 'ваш-пароль'
 *
 * Пароль НИКОГДА не попадает в выходной файл и в git — он нужен
 * только в момент сборки, чтобы вывести ключ шифрования.
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SRC = path.join(ROOT, 'index.html');
const OUT = path.join(ROOT, 'index.protected.html');

// Параметры KDF/шифра. Должны совпадать с расшифровщиком в браузере.
const ITERATIONS = 250000; // PBKDF2-SHA256
const KEY_LEN = 32;        // 256 бит для AES-256-GCM

// ── Подкоманда owner-hash: вывести PBKDF2-запись для пароля владельца ──
// Использование:  node scripts/encrypt.js owner-hash 'НовыйПароль'
// Скопируйте JSON в index.html → const OWNER_CRED = {...}; (пароль в код не попадает).
if (process.argv[2] === 'owner-hash') {
  const pw = process.argv[3] || process.env.OWNER_PASSWORD;
  if (!pw) { console.error("\n  ✗ Укажите пароль: node scripts/encrypt.js owner-hash 'НовыйПароль'\n"); process.exit(1); }
  const salt = crypto.randomBytes(16);
  const iter = 150000; // должно совпадать с AQSec.PBKDF2_ITER в index.html
  const hash = crypto.pbkdf2Sync(pw, salt, iter, 32, 'sha256');
  const rec = { v: 1, alg: 'PBKDF2-SHA256', iter, salt: salt.toString('base64'), hash: hash.toString('base64') };
  console.log('\n  Вставьте в index.html вместо текущего OWNER_CRED:\n');
  console.log('  const OWNER_CRED = ' + JSON.stringify(rec) + ';\n');
  process.exit(0);
}

const password = process.env.SITE_PASSWORD || process.argv[2];
if (!password) {
  console.error('\n  ✗ Не задан пароль.\n');
  console.error("    SITE_PASSWORD='ваш-пароль' node scripts/encrypt.js");
  console.error("    node scripts/encrypt.js 'ваш-пароль'\n");
  process.exit(1);
}
if (!fs.existsSync(SRC)) {
  console.error(`\n  ✗ Не найден исходник: ${SRC}\n`);
  process.exit(1);
}

const plaintext = fs.readFileSync(SRC); // Buffer (UTF-8 HTML)

// --- Шифрование -----------------------------------------------------------
const salt = crypto.randomBytes(16);
const iv = crypto.randomBytes(12); // 96-бит nonce — стандарт для GCM
const key = crypto.pbkdf2Sync(password, salt, ITERATIONS, KEY_LEN, 'sha256');

const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
const authTag = cipher.getAuthTag(); // 16 байт

// Web Crypto ждёт auth-tag в конце шифротекста — приклеиваем.
const blob = Buffer.concat([ciphertext, authTag]);

const PAYLOAD = blob.toString('base64');
const SALT_B64 = salt.toString('base64');
const IV_B64 = iv.toString('base64');

// --- Самопроверка round-trip ---------------------------------------------
// Расшифровываем тем же ключом, чтобы гарантировать корректность параметров.
(function selfTest() {
  const ct = blob.subarray(0, blob.length - 16);
  const tag = blob.subarray(blob.length - 16);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(tag);
  const out = Buffer.concat([decipher.update(ct), decipher.final()]);
  if (!out.equals(plaintext)) {
    console.error('\n  ✗ Self-test провалился: расшифровка не совпала с оригиналом.\n');
    process.exit(1);
  }
})();

// --- Сборка страницы-замка ------------------------------------------------
// _t — function declaration ниже (всплывает), поэтому извлекаем шаблон здесь.
const _src = _t.toString();
const GATE_TEMPLATE = _src.slice(_src.indexOf('/*') + 2, _src.lastIndexOf('*/'));

const html = GATE_TEMPLATE.split('__ITERATIONS__').join(String(ITERATIONS))
  .split('__SALT__').join(SALT_B64)
  .split('__IV__').join(IV_B64)
  .replace('__PAYLOAD__', () => PAYLOAD); // функция-replacer ⇒ '$' в base64 не интерпретируется

fs.writeFileSync(OUT, html);

const kb = (n) => (n / 1024).toFixed(0) + ' КБ';
console.log('\n  ✓ Зашифровано.');
console.log(`    Исходник : index.html            (${kb(plaintext.length)})`);
console.log(`    Результат: index.protected.html   (${kb(Buffer.byteLength(html))})`);
console.log(`    Алгоритм : AES-256-GCM + PBKDF2-SHA256 ×${ITERATIONS}`);
console.log('\n    Заливай на хостинг index.protected.html (можно переименовать в index.html).');
console.log('    Пароль в файл НЕ записан — без него контент не открыть.\n');

// ==========================================================================
//  Шаблон страницы-замка. __PLACEHOLDER__ заменяются выше.
//  Внутри — расшифровщик на Web Crypto API.
// ==========================================================================
function _t() {/*
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Aquality — закрытый доступ</title>
<meta name="robots" content="noindex, nofollow">
<style>
  :root{
    --bg:#0a1018; --bg2:#0f1a26; --card:#111c2b; --line:rgba(120,170,220,.14);
    --txt:#dce8f4; --muted:#7e93ab; --amber:#ffb547; --amber2:#ff8a3d;
    --err:#ff6b6b; --ok:#3ddc97;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    color:var(--txt); background:radial-gradient(1200px 700px at 50% -10%, #16273a 0%, var(--bg2) 45%, var(--bg) 100%);
    display:flex; align-items:center; justify-content:center; padding:24px;
    -webkit-font-smoothing:antialiased;
  }
  .thermal{position:fixed; inset:0; z-index:0; overflow:hidden; pointer-events:none}
  .thermal::before,.thermal::after{
    content:""; position:absolute; border-radius:50%; filter:blur(70px); opacity:.5;
    animation:float 14s ease-in-out infinite;
  }
  .thermal::before{width:380px;height:380px;background:radial-gradient(circle,#1d72c4,transparent 70%);top:-90px;left:-60px}
  .thermal::after{width:320px;height:320px;background:radial-gradient(circle,var(--amber2),transparent 70%);bottom:-80px;right:-40px;animation-delay:-6s;opacity:.32}
  @keyframes float{0%,100%{transform:translate(0,0)}50%{transform:translate(30px,28px)}}
  .card{
    position:relative; z-index:1; width:100%; max-width:400px;
    background:linear-gradient(180deg, rgba(20,33,50,.92), rgba(13,22,34,.92));
    border:1px solid var(--line); border-radius:20px; padding:36px 30px 30px;
    box-shadow:0 30px 80px -30px rgba(0,0,0,.8), inset 0 1px 0 rgba(255,255,255,.04);
    backdrop-filter:blur(8px);
  }
  .lock{
    width:62px;height:62px;margin:0 auto 18px;border-radius:16px;
    display:flex;align-items:center;justify-content:center;font-size:30px;
    background:linear-gradient(135deg, rgba(255,181,71,.18), rgba(255,138,61,.08));
    border:1px solid rgba(255,181,71,.32);
  }
  h1{margin:0 0 6px;text-align:center;font-size:19px;font-weight:700;letter-spacing:.2px}
  .sub{margin:0 0 24px;text-align:center;font-size:13px;color:var(--muted);line-height:1.5}
  form{display:flex;flex-direction:column;gap:12px}
  .field{position:relative}
  input[type=password],input[type=text]{
    width:100%;padding:14px 44px 14px 15px;font-size:15px;color:var(--txt);
    background:#0c1622;border:1px solid var(--line);border-radius:12px;outline:none;
    transition:border-color .15s, box-shadow .15s;
  }
  input:focus{border-color:rgba(255,181,71,.55);box-shadow:0 0 0 3px rgba(255,181,71,.12)}
  .toggle{
    position:absolute;right:8px;top:50%;transform:translateY(-50%);
    background:none;border:none;color:var(--muted);cursor:pointer;font-size:16px;padding:6px;line-height:1;
  }
  .row{display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--muted);user-select:none}
  .row input{accent-color:var(--amber)}
  button.go{
    margin-top:4px;padding:14px;font-size:15px;font-weight:700;color:#1a0f00;cursor:pointer;
    background:linear-gradient(135deg,var(--amber),var(--amber2));border:none;border-radius:12px;
    transition:transform .12s, filter .15s, opacity .15s;
  }
  button.go:hover{filter:brightness(1.06)}
  button.go:active{transform:translateY(1px)}
  button.go:disabled{opacity:.6;cursor:default;filter:saturate(.6)}
  .msg{min-height:18px;text-align:center;font-size:12.5px;margin-top:2px}
  .msg.err{color:var(--err)}
  .msg.ok{color:var(--ok)}
  .spinner{
    display:inline-block;width:14px;height:14px;border:2px solid rgba(26,15,0,.35);
    border-top-color:#1a0f00;border-radius:50%;animation:spin .7s linear infinite;vertical-align:-2px;margin-right:6px;
  }
  @keyframes spin{to{transform:rotate(360deg)}}
  .foot{margin-top:18px;text-align:center;font-size:11px;color:#5a6e85}
  noscript{display:block;text-align:center;color:var(--err);font-size:13px;margin-top:14px}
</style>
</head>
<body>
  <div class="thermal"></div>
  <div class="card">
    <div class="lock">🔒</div>
    <h1>Закрытый доступ</h1>
    <p class="sub">Эта страница защищена паролем.<br>Введите пароль, чтобы продолжить.</p>
    <form id="f" autocomplete="off">
      <div class="field">
        <input id="pw" type="password" placeholder="Пароль" autocomplete="current-password" autofocus>
        <button type="button" class="toggle" id="tg" aria-label="Показать пароль">👁</button>
      </div>
      <label class="row"><input type="checkbox" id="remember" checked> Запомнить на эту сессию</label>
      <button class="go" id="go" type="submit">Открыть</button>
      <div class="msg" id="msg"></div>
    </form>
    <div class="foot">Aquality · AES-256 защита</div>
    <noscript>Для входа нужно включить JavaScript.</noscript>
  </div>

<script>
(function(){
  "use strict";
  var ITER = __ITERATIONS__;
  var SALT = bytes("__SALT__");
  var IV   = bytes("__IV__");
  var PAYLOAD = "__PAYLOAD__";

  function bytes(b64){ var s=atob(b64), u=new Uint8Array(s.length); for(var i=0;i<s.length;i++)u[i]=s.charCodeAt(i); return u; }

  var $ = function(id){ return document.getElementById(id); };
  var pw=$("pw"), go=$("go"), msg=$("msg"), form=$("f"), remember=$("remember");

  // Расшифровать payload данным паролем. Бросает исключение при неверном пароле.
  function decrypt(password){
    var enc = new TextEncoder();
    return crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveKey"])
      .then(function(km){
        return crypto.subtle.deriveKey(
          {name:"PBKDF2", salt:SALT, iterations:ITER, hash:"SHA-256"},
          km, {name:"AES-GCM", length:256}, false, ["decrypt"]);
      })
      .then(function(key){
        return crypto.subtle.decrypt({name:"AES-GCM", iv:IV}, key, bytes(PAYLOAD));
      })
      .then(function(buf){ return new TextDecoder().decode(buf); });
  }

  function render(htmlText){
    // Полная замена документа — инлайновые скрипты исходника выполнятся.
    document.open();
    document.write(htmlText);
    document.close();
  }

  var busy=false;
  function unlock(password, fromMemory){
    if(busy) return;
    busy=true; go.disabled=true;
    msg.className="msg";
    msg.innerHTML='<span class="spinner"></span>Расшифровка…';
    decrypt(password).then(function(html){
      if(remember.checked) try{ sessionStorage.setItem("aq_pw", password); }catch(e){}
      msg.className="msg ok"; msg.textContent="Доступ открыт";
      setTimeout(function(){ render(html); }, 120);
    }).catch(function(){
      busy=false; go.disabled=false;
      if(fromMemory){ try{ sessionStorage.removeItem("aq_pw"); }catch(e){} msg.className="msg"; msg.textContent=""; pw.focus(); return; }
      msg.className="msg err"; msg.textContent="Неверный пароль";
      pw.value=""; pw.focus();
    });
  }

  form.addEventListener("submit", function(e){ e.preventDefault(); var v=pw.value; if(v) unlock(v,false); });

  $("tg").addEventListener("click", function(){
    pw.type = pw.type==="password" ? "text" : "password"; pw.focus();
  });

  // Авто-вход, если пароль уже сохранён в этой сессии.
  try{
    var saved = sessionStorage.getItem("aq_pw");
    if(saved) unlock(saved, true);
  }catch(e){}
})();
</script>
</body>
</html>
*/}
