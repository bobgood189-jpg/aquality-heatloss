"""RU / UZ / EN strings for the bot. Mirrors the website's _i18n approach: a flat
key→translations dict plus t(key, lang). Default language is Russian (the shop's
primary audience in Fergana)."""

LANGS = ["ru", "uz", "en"]
LANG_NAMES = {"ru": "🇷🇺 Русский", "uz": "🇺🇿 O'zbekcha", "en": "🇬🇧 English"}
DEFAULT_LANG = "ru"

STR = {
    # ── generic ──
    "back": {"ru": "◀️ Назад", "uz": "◀️ Orqaga", "en": "◀️ Back"},
    "cancel": {"ru": "✖️ Отмена", "uz": "✖️ Bekor qilish", "en": "✖️ Cancel"},
    "skip": {"ru": "Пропустить ▶️", "uz": "O'tkazib yuborish ▶️", "en": "Skip ▶️"},
    "done": {"ru": "✅ Готово", "uz": "✅ Tayyor", "en": "✅ Done"},
    "yes": {"ru": "Да", "uz": "Ha", "en": "Yes"},
    "no": {"ru": "Нет", "uz": "Yo'q", "en": "No"},
    "menu": {"ru": "🏠 Меню", "uz": "🏠 Menyu", "en": "🏠 Menu"},
    "invalid_number": {"ru": "⚠️ Введите число (например 4.5).",
                       "uz": "⚠️ Raqam kiriting (masalan 4.5).",
                       "en": "⚠️ Enter a number (e.g. 4.5)."},
    # ── welcome / menu ──
    "choose_lang": {"ru": "Выберите язык / Tilni tanlang / Choose language:",
                    "uz": "Tilni tanlang / Выберите язык / Choose language:",
                    "en": "Choose language / Выберите язык / Tilni tanlang:"},
    "welcome": {
        "ru": "🔥 <b>Aquality | WaterPro</b>\n\nКалькулятор теплопотерь, инженерные инструменты (котёл, радиаторы, топливо, утеплитель) и подписка — всё в одном боте.\n\nВыберите действие:",
        "uz": "🔥 <b>Aquality | WaterPro</b>\n\nIssiqlik yo'qotish kalkulyatori, muhandislik vositalari (qozon, radiator, yoqilg'i, uteplitel) va obuna — hammasi bitta botda.\n\nAmalni tanlang:",
        "en": "🔥 <b>Aquality | WaterPro</b>\n\nHeat-loss calculator, engineering tools (boiler, radiators, fuel, insulation) and subscription — all in one bot.\n\nChoose an action:"},
    "menu_materials": {"ru": "📚 Справочник материалов", "uz": "📚 Materiallar ma'lumotnomasi", "en": "📚 Materials library"},
    "menu_contact": {"ru": "📞 Контакты", "uz": "📞 Aloqa", "en": "📞 Contacts"},
    "menu_faq": {"ru": "❓ Как считается?", "uz": "❓ Qanday hisoblanadi?", "en": "❓ How it works"},
    "menu_lang": {"ru": "🌐 Язык", "uz": "🌐 Til", "en": "🌐 Language"},
    "menu_lead": {"ru": "✍️ Оставить заявку", "uz": "✍️ Ariza qoldirish", "en": "✍️ Request a consult"},
    # ── подписка / оплата ──
    "menu_tariffs": {"ru": "💳 Подписка / Тарифы", "uz": "💳 Obuna / Tariflar", "en": "💳 Subscription / Plans"},
    "plan_m1": {"ru": "1 месяц", "uz": "1 oy", "en": "1 month"},
    "plan_m6": {"ru": "6 месяцев", "uz": "6 oy", "en": "6 months"},
    "plan_m12": {"ru": "12 месяцев", "uz": "12 oy", "en": "12 months"},
    "tariffs_title": {
        "ru": "💳 <b>Доступ к расчёту</b>\n\nДемо открыто всем. Полный расчёт своего объекта — по подписке.{status}\n\n<b>Тарифы:</b>{plans}\n\n🎁 Есть промокод? Отправьте: <code>/promo КОД</code>{total}",
        "uz": "💳 <b>Hisobga kirish</b>\n\nDemo hammaga ochiq. O'z obyektingizni to'liq hisoblash — obuna orqali.{status}\n\n<b>Tariflar:</b>{plans}\n\n🎁 Promokod bormi? Yuboring: <code>/promo KOD</code>{total}",
        "en": "💳 <b>Calculation access</b>\n\nDemo is open to all. Full calculation of your own object requires a subscription.{status}\n\n<b>Plans:</b>{plans}\n\n🎁 Have a promo code? Send: <code>/promo CODE</code>{total}"},
    "tariffs_pay": {"ru": "💬 Оплатить через Telegram", "uz": "💬 Telegram orqali to'lash", "en": "💬 Pay via Telegram"},
    "sub_active": {"ru": "\n\n✅ Подписка активна до <b>{date}</b>.", "uz": "\n\n✅ Obuna <b>{date}</b> gacha faol.", "en": "\n\n✅ Subscription active until <b>{date}</b>."},
    "sub_none": {"ru": "", "uz": "", "en": ""},
    "sub_days_left": {"ru": "осталось {n} дн.", "uz": "{n} kun qoldi", "en": "{n} days left"},
    "sub_expires_in": {"ru": "истекает через {n} дн.!", "uz": "{n} kunda tugaydi!", "en": "expires in {n} days!"},
    "sub_expires_tomorrow": {"ru": "истекает завтра!", "uz": "ertaga tugaydi!", "en": "expires tomorrow!"},
    "sub_expiry_warn": {
        "ru": "⚠️ <b>Ваша подписка истекает через {n} дн.</b> (до {date}).\n\nПродлите заранее, чтобы не потерять доступ к расчётам.",
        "uz": "⚠️ <b>Obunangiz {n} kunda tugaydi</b> ({date} gacha).\n\nHisob-kitoblarga kirishni yo'qotmaslik uchun muddatdan oldin yangilang.",
        "en": "⚠️ <b>Your subscription expires in {n} days</b> (until {date}).\n\nRenew early to keep access to calculations.",
    },
    "sub_expiry_tomorrow": {
        "ru": "⚠️ <b>Ваша подписка истекает завтра!</b> (до {date}).\n\nПродлите сейчас, чтобы не потерять доступ.",
        "uz": "⚠️ <b>Obunangiz ertaga tugaydi!</b> ({date} gacha).\n\nKirishni yo'qotmaslik uchun hozir yangilang.",
        "en": "⚠️ <b>Your subscription expires tomorrow!</b> (until {date}).\n\nRenew now to keep access.",
    },
    "sub_expired_warn": {
        "ru": "❌ <b>Ваша подписка истекла.</b>\n\nДоступ к полному расчёту ограничен. Свяжитесь с нами для продления.",
        "uz": "❌ <b>Obunangiz tugadi.</b>\n\nTo'liq hisob-kitobga kirish cheklangan. Yangilash uchun biz bilan bog'laning.",
        "en": "❌ <b>Your subscription has expired.</b>\n\nFull calculation access is restricted. Contact us to renew.",
    },
    "sub_none_user": {
        "ru": "У вас нет активной подписки. Используйте /tariffs для просмотра тарифов.",
        "uz": "Sizda faol obuna yo'q. Tariflarni ko'rish uchun /tariffs foydalaning.",
        "en": "You have no active subscription. Use /tariffs to view plans.",
    },
    "promo_applied": {"ru": "🎁 Промокод <b>{code}</b> применён: скидка −{disc}%. К оплате за {plan}: <b>{price}</b>.",
                      "uz": "🎁 <b>{code}</b> promokod qo'llandi: −{disc}% chegirma. {plan} uchun: <b>{price}</b>.",
                      "en": "🎁 Promo <b>{code}</b> applied: −{disc}% off. {plan} total: <b>{price}</b>."},
    "promo_bad": {"ru": "⚠️ Код недействителен.", "uz": "⚠️ Kod yaroqsiz.", "en": "⚠️ Invalid code."},
    "promo_exhausted": {"ru": "⚠️ Лимит кода исчерпан.", "uz": "⚠️ Kod limiti tugagan.", "en": "⚠️ Code limit reached."},
    "promo_used": {"ru": "⚠️ Вы уже применяли этот код.", "uz": "⚠️ Bu kodni allaqachon ishlatgansiz.", "en": "⚠️ You already used this code."},
    "promo_usage": {"ru": "Использование: <code>/promo КОД</code>", "uz": "Foydalanish: <code>/promo KOD</code>", "en": "Usage: <code>/promo CODE</code>"},
    "pay_locked": {
        "ru": "🔒 <b>Полный расчёт — по подписке.</b>\n\nДемо доступно в меню бесплатно. Чтобы рассчитать свой объект, оформите подписку.",
        "uz": "🔒 <b>To'liq hisob — obuna orqali.</b>\n\nDemo menyuda bepul. O'z obyektingizni hisoblash uchun obuna bo'ling.",
        "en": "🔒 <b>Full calculation requires a subscription.</b>\n\nThe demo is free in the menu. To calculate your own object, subscribe."},
    "pay_order": {
        "ru": "Здравствуйте! Хочу оформить подписку Aquality: {plan} — {price}.{promo} Мой id: {uid}.",
        "uz": "Salom! Aquality obunasini rasmiylashtirmoqchiman: {plan} — {price}.{promo} Mening id: {uid}.",
        "en": "Hello! I'd like an Aquality subscription: {plan} — {price}.{promo} My id: {uid}."},
    "pay_howto": {
        "ru": "\n\n👉 Нажмите кнопку ниже, напишите менеджеру это сообщение (скопируйте текст выше). После оплаты доступ откроют в течение рабочего дня.",
        "uz": "\n\n👉 Quyidagi tugmani bosing va menejerga yuqoridagi xabarni yuboring. To'lovdan so'ng kirish ish kuni davomida ochiladi.",
        "en": "\n\n👉 Tap the button below and send the manager the message above. Access is granted within a business day after payment."},
    # ── city ──
    "ask_city": {"ru": "🏙 Выберите город (для расчётной зимней температуры, параметр Б):",
                 "uz": "🏙 Shaharni tanlang (qishki hisobiy harorat uchun, parametr B):",
                 "en": "🏙 Choose your city (for the design winter temperature, parameter B):"},
    "city_set": {"ru": "Город: <b>{city}</b>, расчётная температура <b>{t}°C</b>.",
                 "uz": "Shahar: <b>{city}</b>, hisobiy harorat <b>{t}°C</b>.",
                 "en": "City: <b>{city}</b>, design temperature <b>{t}°C</b>."},
    # ── object params ──
    "ask_floors": {"ru": "🏢 Сколько <b>этажей</b> в объекте?", "uz": "🏢 Obyektda nechta <b>qavat</b>?", "en": "🏢 How many <b>floors</b>?"},
    "ask_height": {"ru": "📏 Высота потолка, м (например 3.0):", "uz": "📏 Shift balandligi, m (masalan 3.0):", "en": "📏 Ceiling height, m (e.g. 3.0):"},
    "ask_attic": {"ru": "🏠 Тип чердака / кровли (верхний этаж):", "uz": "🏠 Cherdak / tom turi (yuqori qavat):", "en": "🏠 Attic / roof type (top floor):"},
    "ask_airtight": {"ru": "💨 Герметичность здания (инфильтрация):", "uz": "💨 Bino germetikligi (infiltratsiya):", "en": "💨 Building airtightness (infiltration):"},
    "ask_regime": {"ru": "♨️ Температурный режим системы отопления:", "uz": "♨️ Isitish tizimi harorat rejimi:", "en": "♨️ Heating system temperature mode:"},
    "ask_lambda": {"ru": "💧 Влажностный режим λ (условия эксплуатации):", "uz": "💧 Namlik rejimi λ (ekspluatatsiya sharoiti):", "en": "💧 Moisture mode λ (operating conditions):"},
    "lambda_a": {"ru": "А — сухой (Фергана, по умолч.)", "uz": "A — quruq (Farg'ona, default)", "en": "A — dry (Fergana, default)"},
    "lambda_b": {"ru": "Б — влажный (+λ)", "uz": "B — nam (+λ)", "en": "B — humid (+λ)"},
    # ── materials ──
    "mat_intro": {"ru": "🧱 Теперь материалы конструкций. Выбирайте по очереди:",
                  "uz": "🧱 Endi konstruksiya materiallari. Navbat bilan tanlang:",
                  "en": "🧱 Now the construction materials. Pick them one by one:"},
    "mat_walls": {"ru": "Стены", "uz": "Devorlar", "en": "Walls"},
    "mat_windows": {"ru": "Окна", "uz": "Derazalar", "en": "Windows"},
    "mat_doors": {"ru": "Двери", "uz": "Eshiklar", "en": "Doors"},
    "mat_floors": {"ru": "Пол", "uz": "Pol", "en": "Floor"},
    "mat_ceilings": {"ru": "Потолок / кровля", "uz": "Shift / tom", "en": "Ceiling / roof"},
    "ask_mat": {"ru": "Выберите материал: <b>{cat}</b>", "uz": "Materialni tanlang: <b>{cat}</b>", "en": "Choose material: <b>{cat}</b>"},
    "pick_group": {"ru": "Выберите группу: <b>{cat}</b>", "uz": "Guruhni tanlang: <b>{cat}</b>", "en": "Choose a group: <b>{cat}</b>"},
    "mat_set": {"ru": "✅ {cat}: <b>{name}</b> (R={r})", "uz": "✅ {cat}: <b>{name}</b> (R={r})", "en": "✅ {cat}: <b>{name}</b> (R={r})"},
    "popular": {"ru": "⭐ Популярные", "uz": "⭐ Ommabop", "en": "⭐ Popular"},
    "all_groups": {"ru": "📂 Все группы", "uz": "📂 Barcha guruhlar", "en": "📂 All groups"},
    # ── rooms ──
    "rooms_intro": {"ru": "🚪 Добавьте помещения этажа <b>{floor}</b>. После добавления всех — нажмите «Посчитать».",
                    "uz": "🚪 <b>{floor}</b> qavat xonalarini qo'shing. Hammasini qo'shgach «Hisoblash» ni bosing.",
                    "en": "🚪 Add rooms for floor <b>{floor}</b>. When done, press “Calculate”."},
    "add_room": {"ru": "➕ Добавить помещение", "uz": "➕ Xona qo'shish", "en": "➕ Add room"},
    "next_floor": {"ru": "⬆️ Следующий этаж", "uz": "⬆️ Keyingi qavat", "en": "⬆️ Next floor"},
    "calc_now": {"ru": "🧮 Посчитать", "uz": "🧮 Hisoblash", "en": "🧮 Calculate"},
    "ask_room_type": {"ru": "Тип помещения:", "uz": "Xona turi:", "en": "Room type:"},
    "ask_room_len": {"ru": "Длина помещения, м (например 5):", "uz": "Xona uzunligi, m (masalan 5):", "en": "Room length, m (e.g. 5):"},
    "ask_room_wid": {"ru": "Ширина помещения, м (например 4):", "uz": "Xona kengligi, m (masalan 4):", "en": "Room width, m (e.g. 4):"},
    "ask_ext_walls": {"ru": "🧭 Какие стены <b>наружные</b>? Отметьте стороны света (минимум одна), затем «Готово».\nС/В/СВ +10%, З/ЮВ +5%, Ю/ЮЗ 0%. Угловая (2+ стен) +5%.",
                      "uz": "🧭 Qaysi devorlar <b>tashqi</b>? Tomonlarni belgilang (kamida bittasi), keyin «Tayyor».",
                      "en": "🧭 Which walls are <b>external</b>? Tag the compass sides (at least one), then “Done”."},
    "dir_N": {"ru": "С (север)", "uz": "Sh (shimol)", "en": "N (north)"},
    "dir_E": {"ru": "В (восток)", "uz": "Sharq", "en": "E (east)"},
    "dir_S": {"ru": "Ю (юг)", "uz": "J (janub)", "en": "S (south)"},
    "dir_W": {"ru": "З (запад)", "uz": "G' (g'arb)", "en": "W (west)"},
    "ext_walls_set": {"ru": "Наружные стены: <b>{dirs}</b>", "uz": "Tashqi devorlar: <b>{dirs}</b>", "en": "External walls: <b>{dirs}</b>"},
    "need_one_wall": {"ru": "⚠️ Отметьте хотя бы одну наружную стену.", "uz": "⚠️ Kamida bitta tashqi devorni belgilang.", "en": "⚠️ Tag at least one external wall."},
    "ask_windows": {"ru": "🪟 Сколько окон в помещении? (0 если нет)", "uz": "🪟 Xonada nechta deraza? (yo'q bo'lsa 0)", "en": "🪟 How many windows? (0 if none)"},
    "ask_win_size": {"ru": "Размер окна Ш×В в метрах через × (например 1.5×1.4):", "uz": "Deraza o'lchami E×B metrda × bilan (masalan 1.5×1.4):", "en": "Window size W×H in metres with × (e.g. 1.5×1.4):"},
    "ask_win_dir": {"ru": "На какой наружной стене окна?", "uz": "Derazalar qaysi tashqi devorda?", "en": "Which external wall are the windows on?"},
    "ask_doors": {"ru": "🚪 Сколько наружных дверей? (0 если нет)", "uz": "🚪 Nechta tashqi eshik? (yo'q bo'lsa 0)", "en": "🚪 How many external doors? (0 if none)"},
    "ask_door_size": {"ru": "Размер двери Ш×В в метрах (например 1.0×2.1):", "uz": "Eshik o'lchami E×B metrda (masalan 1.0×2.1):", "en": "Door size W×H in metres (e.g. 1.0×2.1):"},
    "ask_door_dir": {"ru": "На какой наружной стене дверь?", "uz": "Eshik qaysi tashqi devorda?", "en": "Which external wall is the door on?"},
    "ask_door_beta": {"ru": "Тип открывания двери (надбавка на приток холода):", "uz": "Eshik ochilish turi (sovuq oqimi qo'shimchasi):", "en": "Door opening type (cold-air surcharge):"},
    "room_added": {"ru": "✅ Добавлено: <b>{name}</b> {l}×{w} м. Всего помещений: {n}.",
                   "uz": "✅ Qo'shildi: <b>{name}</b> {l}×{w} m. Jami xonalar: {n}.",
                   "en": "✅ Added: <b>{name}</b> {l}×{w} m. Rooms total: {n}."},
    "no_rooms": {"ru": "⚠️ Сначала добавьте хотя бы одно помещение.", "uz": "⚠️ Avval kamida bitta xona qo'shing.", "en": "⚠️ Add at least one room first."},
    # ── results ──
    "result_title": {"ru": "📊 <b>Результат расчёта теплопотерь</b>", "uz": "📊 <b>Issiqlik yo'qotishi hisobi</b>", "en": "📊 <b>Heat-loss result</b>"},
    "res_totalkw": {"ru": "🔥 Теплопотери: <b>{kw} кВт</b>", "uz": "🔥 Issiqlik yo'qotishi: <b>{kw} kVt</b>", "en": "🔥 Heat loss: <b>{kw} kW</b>"},
    "res_boiler": {"ru": "⚙️ Котёл с запасом 25%: <b>{kw} кВт</b>", "uz": "⚙️ Qozon 25% zaxira bilan: <b>{kw} kVt</b>", "en": "⚙️ Boiler (+25% margin): <b>{kw} kW</b>"},
    "res_area": {"ru": "📐 Площадь: {area} м² · {rooms} помещ. · {floors} эт.", "uz": "📐 Maydon: {area} m² · {rooms} xona · {floors} qavat", "en": "📐 Area: {area} m² · {rooms} rooms · {floors} floors"},
    "res_persqm": {"ru": "📈 Удельные потери: {v} Вт/м²", "uz": "📈 Solishtirma yo'qotish: {v} Vt/m²", "en": "📈 Specific loss: {v} W/m²"},
    "res_breakdown": {"ru": "<b>Структура потерь:</b>", "uz": "<b>Yo'qotish tarkibi:</b>", "en": "<b>Loss breakdown:</b>"},
    "res_sections": {"ru": "🔧 Радиаторы: ≈ <b>{n} секций</b> ({model})", "uz": "🔧 Radiatorlar: ≈ <b>{n} seksiya</b> ({model})", "en": "🔧 Radiators: ≈ <b>{n} sections</b> ({model})"},
    "res_pipe": {"ru": "🟦 Магистраль: труба Ø {pipe} мм", "uz": "🟦 Magistral: quvur Ø {pipe} mm", "en": "🟦 Main line: pipe Ø {pipe} mm"},
    "res_boiler_model": {"ru": "🔩 Рекомендуемый котёл: <b>{model}</b>\n   <i>{type}</i>", "uz": "🔩 Tavsiya etilgan qozon: <b>{model}</b>\n   <i>{type}</i>", "en": "🔩 Recommended boiler: <b>{model}</b>\n   <i>{type}</i>"},
    "res_fuel": {"ru": "💰 <b>Стоимость отопления / мес.</b> (≈, тарифы UZ):", "uz": "💰 <b>Isitish narxi / oy</b> (≈, UZ tariflari):", "en": "💰 <b>Heating cost / month</b> (≈, UZ tariffs):"},
    "res_disclaimer": {"ru": "<i>Расчёт по КМК 2.01.04-18, ориентировочный. Для точного проекта — оставьте заявку, специалист уточнит детали бесплатно.</i>",
                       "uz": "<i>Hisob KMK 2.01.04-18 bo'yicha, taxminiy. Aniq loyiha uchun ariza qoldiring — mutaxassis bepul aniqlaydi.</i>",
                       "en": "<i>Per KMK 2.01.04-18, approximate. For an exact project leave a request — a specialist will refine it free.</i>"},
    "comp_wall": {"ru": "Стены", "uz": "Devorlar", "en": "Walls"},
    "comp_window": {"ru": "Окна", "uz": "Derazalar", "en": "Windows"},
    "comp_door": {"ru": "Двери", "uz": "Eshiklar", "en": "Doors"},
    "comp_floor": {"ru": "Пол", "uz": "Pol", "en": "Floor"},
    "comp_ceiling": {"ru": "Потолок", "uz": "Shift", "en": "Ceiling"},
    "comp_infil": {"ru": "Инфильтрация", "uz": "Infiltratsiya", "en": "Infiltration"},
    # ── lead ──
    "lead_start": {"ru": "✍️ Оставьте заявку — специалист свяжется и бесплатно уточнит проект.\n\nКак вас зовут?",
                   "uz": "✍️ Ariza qoldiring — mutaxassis bog'lanib, loyihani bepul aniqlaydi.\n\nIsmingiz?",
                   "en": "✍️ Leave a request — a specialist will contact you and refine the project for free.\n\nYour name?"},
    "lead_phone": {"ru": "📱 Ваш номер телефона (например +998 90 123-45-67):", "uz": "📱 Telefon raqamingiz (masalan +998 90 123-45-67):", "en": "📱 Your phone number (e.g. +998 90 123-45-67):"},
    "lead_sent": {"ru": "✅ Спасибо, <b>{name}</b>! Заявка отправлена. Мы скоро свяжемся с вами по номеру {phone}.",
                  "uz": "✅ Rahmat, <b>{name}</b>! Ariza yuborildi. Tez orada {phone} raqami orqali bog'lanamiz.",
                  "en": "✅ Thanks, <b>{name}</b>! Request sent. We'll contact you at {phone} soon."},
    "lead_share_phone": {"ru": "📱 Отправить мой номер", "uz": "📱 Raqamimni yuborish", "en": "📱 Share my number"},
    # ── contact / faq ──
    "contact_text": {
        "ru": "📞 <b>Aquality | WaterPro</b>\nОтопление, водоснабжение, котлы и радиаторы — Фергана.\n\n☎️ {phone}\n☎️ {phone2}\n💬 WhatsApp: wa.me/{wa}\n📍 {addr}",
        "uz": "📞 <b>Aquality | WaterPro</b>\nIsitish, suv ta'minoti, qozon va radiatorlar — Farg'ona.\n\n☎️ {phone}\n☎️ {phone2}\n💬 WhatsApp: wa.me/{wa}\n📍 {addr}",
        "en": "📞 <b>Aquality | WaterPro</b>\nHeating, plumbing, boilers & radiators — Fergana.\n\n☎️ {phone}\n☎️ {phone2}\n💬 WhatsApp: wa.me/{wa}\n📍 {addr}"},
    "faq_text": {
        "ru": "❓ <b>Как считается?</b>\n\nИнженерный расчёт по КМК 2.01.04-18 и КМК 2.01.01-94 (параметр Б):\n\n<b>Q = (Δt / R) · S · n · (1 + Σβ)</b> для каждого ограждения (стены, окна, двери, пол, потолок) + инфильтрация Q = 0.28·1.005·V·ρ·Δt·ACH.\n\n• R — сопротивление теплопередаче конструкции\n• Δt — разница внутр./наружной температуры\n• β — надбавки на ориентацию и угловые комнаты\n• Пол на грунте — зональный метод (Староверов)\n\nКотёл берём с запасом 25%. Результат ориентировочный; точный проект уточнит специалист бесплатно.",
        "uz": "❓ <b>Qanday hisoblanadi?</b>\n\nKMK 2.01.04-18 va KMK 2.01.01-94 (parametr B) bo'yicha muhandislik hisobi:\n\n<b>Q = (Δt / R) · S · n · (1 + Σβ)</b> har bir to'siq uchun + infiltratsiya.\n\nQozon 25% zaxira bilan olinadi. Natija taxminiy; aniq loyihani mutaxassis bepul aniqlaydi.",
        "en": "❓ <b>How it works</b>\n\nEngineering calc per KMK 2.01.04-18 & KMK 2.01.01-94 (parameter B):\n\n<b>Q = (Δt / R) · S · n · (1 + Σβ)</b> for each enclosure + infiltration.\n\nBoiler sized with a 25% margin. Result is approximate; a specialist refines the exact project for free."},
    "restart_hint": {"ru": "Расчёт сброшен. /start — начать заново.", "uz": "Hisob tozalandi. /start — qaytadan.", "en": "Calculation reset. /start to begin again."},
    # ── registration flow ──
    "reg_prompt": {
        "ru": "📧 Введите email вашего аккаунта на сайте (или новый email для создания аккаунта):",
        "uz": "📧 Saytdagi akkauntingiz emailini kiriting (yoki yangi akkaunt uchun yangi email):",
        "en": "📧 Enter your site account email (or a new email to create an account):"},
    "reg_invalid_email": {
        "ru": "⚠️ Некорректный email. Попробуйте ещё раз:",
        "uz": "⚠️ Noto'g'ri email. Qayta urinib ko'ring:",
        "en": "⚠️ Invalid email. Please try again:"},
    "reg_account_found": {
        "ru": "✅ Аккаунт найден. Telegram привязан!",
        "uz": "✅ Akkaunt topildi. Telegram bog'landi!",
        "en": "✅ Account found. Telegram linked!"},
    "reg_created": {
        "ru": "✅ Аккаунт создан и Telegram привязан!",
        "uz": "✅ Akkaunt yaratildi va Telegram bog'landi!",
        "en": "✅ Account created and Telegram linked!"},
    "reg_ask_password": {
        "ru": "🔑 Придумайте пароль для входа на сайт (минимум 6 символов).\n\nС этим паролём и вашим email вы сможете войти на сайте.",
        "uz": "🔑 Saytga kirish uchun parol o'ylab toping (kamida 6 belgi).\n\nShu parol va emailingiz bilan saytga kirasiz.",
        "en": "🔑 Choose a password to log in on the site (at least 6 characters).\n\nUse it with your email to sign in on the site."},
    "reg_pass_short": {
        "ru": "⚠️ Пароль слишком короткий. Минимум 6 символов. Попробуйте ещё раз:",
        "uz": "⚠️ Parol juda qisqa. Kamida 6 belgi. Qayta urinib ko'ring:",
        "en": "⚠️ Password too short. At least 6 characters. Try again:"},
    "reg_pass_ok": {
        "ru": "✅ Пароль сохранён. Теперь можно войти на сайте: email + этот пароль.",
        "uz": "✅ Parol saqlandi. Endi saytga kirishingiz mumkin: email + shu parol.",
        "en": "✅ Password saved. You can now log in on the site: email + this password."},
    "reg_pass_error": {
        "ru": "⚠️ Пароль пока не удалось сохранить. Продолжим регистрацию — задать пароль можно позже через /resetpass.",
        "uz": "⚠️ Parolni saqlab bo'lmadi. Ro'yxatdan o'tishni davom ettiramiz — parolni keyinroq /resetpass orqali o'rnatishingiz mumkin.",
        "en": "⚠️ Couldn't save the password yet. Let's continue — you can set it later via /resetpass."},
    "reg_ask_name": {
        "ru": "Как вас зовут? (или /skip)",
        "uz": "Ismingiz nima? (yoki /skip)",
        "en": "What's your name? (or /skip)"},
    "reg_ask_phone": {
        "ru": "📱 Ваш номер телефона? (или /skip)",
        "uz": "📱 Telefon raqamingiz? (yoki /skip)",
        "en": "📱 Your phone number? (or /skip)"},
    "reg_done": {
        "ru": "🎉 Готово! Добро пожаловать.",
        "uz": "🎉 Tayyor! Xush kelibsiz.",
        "en": "🎉 Done! Welcome."},
    "reg_email_error": {
        "ru": "⚠️ Не удалось обработать email. Попробуйте другой адрес:",
        "uz": "⚠️ Emailni qayta ishlashda xatolik. Boshqa manzil kiriting:",
        "en": "⚠️ Could not process email. Try a different address:"},
    "reg_error": {
        "ru": "⚠️ Ошибка привязки. Попробуйте позже.",
        "uz": "⚠️ Bog'lashda xatolik. Keyinroq urinib ko'ring.",
        "en": "⚠️ Linking error. Please try again later."},
    # ── password reset (email-free, via bot) ──
    "reset_not_linked": {
        "ru": "🔒 Чтобы сбросить пароль, сначала привяжите аккаунт: отправьте /link и укажите email вашего аккаунта на сайте.",
        "uz": "🔒 Parolni tiklash uchun avval akkauntni bog'lang: /link yuboring va saytdagi akkaunt emailini kiriting.",
        "en": "🔒 To reset your password, link your account first: send /link and enter your site account email."},
    "reset_prompt": {
        "ru": "🔑 Придумайте новый пароль (минимум 6 символов) и отправьте его сообщением.\n\nОтмена — /cancel",
        "uz": "🔑 Yangi parol o'ylab toping (kamida 6 belgi) va xabar sifatida yuboring.\n\nBekor qilish — /cancel",
        "en": "🔑 Enter a new password (at least 6 characters) and send it as a message.\n\nCancel — /cancel"},
    "reset_too_short": {
        "ru": "⚠️ Пароль слишком короткий. Минимум 6 символов. Попробуйте ещё раз:",
        "uz": "⚠️ Parol juda qisqa. Kamida 6 belgi. Qayta urinib ko'ring:",
        "en": "⚠️ Password too short. At least 6 characters. Try again:"},
    "reset_done": {
        "ru": "✅ Пароль изменён!\n\nВойдите на сайте: email <b>{email}</b> + новый пароль.\n\n🔒 Для безопасности удалите сообщение с паролём.",
        "uz": "✅ Parol o'zgartirildi!\n\nSaytga kiring: email <b>{email}</b> + yangi parol.\n\n🔒 Xavfsizlik uchun parol yozilgan xabarni o'chiring.",
        "en": "✅ Password changed!\n\nLog in on the site: email <b>{email}</b> + new password.\n\n🔒 For safety, delete the message with your password."},
    "reset_error": {
        "ru": "⚠️ Не удалось сменить пароль. Попробуйте позже или напишите менеджеру.",
        "uz": "⚠️ Parolni o'zgartirib bo'lmadi. Keyinroq urinib ko'ring yoki menejerga yozing.",
        "en": "⚠️ Could not change the password. Try again later or contact the manager."},
    # ── telegram account linking ──
    "link_usage": {
        "ru": "ℹ️ Чтобы привязать Telegram к аккаунту на сайте:\n\n1. Откройте профиль на {site}\n2. Вкладка «Аккаунт» → «Привязать Telegram»\n3. Нажмите «Получить код» и отправьте:\n\n<code>/link КОД</code>",
        "uz": "ℹ️ Telegram-ni saytdagi profilingizga bog'lash uchun:\n\n1. {site} saytida profilni oching\n2. «Akkaunt» → «Telegram bog'lash»\n3. «Kod olish» tugmasini bosib yuboring:\n\n<code>/link KOD</code>",
        "en": "ℹ️ To link Telegram to your site account:\n\n1. Open your profile at {site}\n2. Account tab → 'Link Telegram'\n3. Click 'Get code' and send:\n\n<code>/link CODE</code>",
    },
    "link_success": {
        "ru": "✅ Telegram успешно привязан к вашему аккаунту!",
        "uz": "✅ Telegram muvaffaqiyatli bog'landi!",
        "en": "✅ Telegram successfully linked to your account!",
    },
    "link_bad_token": {
        "ru": "❌ Код недействителен или истёк (15 мин.). Получите новый код в профиле на сайте.",
        "uz": "❌ Kod noto'g'ri yoki muddati o'tgan (15 daq.). Saytdagi profildan yangi kod oling.",
        "en": "❌ Code is invalid or expired (15 min.). Get a new code from your site profile.",
    },
    "link_already": {
        "ru": "⚠️ Этот Telegram уже привязан к другому аккаунту.",
        "uz": "⚠️ Bu Telegram allaqachon boshqa akkauntga bog'langan.",
        "en": "⚠️ This Telegram is already linked to another account.",
    },
    "link_error": {
        "ru": "⚠️ Привязка временно недоступна. Попробуйте позже.",
        "uz": "⚠️ Bog'lash vaqtincha mavjud emas. Keyinroq urinib ko'ring.",
        "en": "⚠️ Linking is temporarily unavailable. Please try again later.",
    },
    "reg_no_sb": {
        "ru": "⚠️ Функция недоступна (нет подключения к базе).",
        "uz": "⚠️ Funksiya mavjud emas (bazaga ulanish yo'q).",
        "en": "⚠️ Feature unavailable (no database connection).",
    },
    # ── password reset code delivered via Telegram (site-initiated) ──
    "reset_code_message": {
        "ru": "🔑 Код для сброса пароля на сайте: <b>{code}</b>\n\n⏱ Действителен 10 минут. Никому не сообщайте этот код.",
        "uz": "🔑 Saytda parolni tiklash kodi: <b>{code}</b>\n\n⏱ 10 daqiqa amal qiladi. Bu kodni hech kimga aytmang.",
        "en": "🔑 Your site password reset code: <b>{code}</b>\n\n⏱ Valid for 10 minutes. Do not share this code with anyone.",
    },
    # ── "Мой аккаунт" screen ──
    "menu_account": {"ru": "👤 Мой аккаунт", "uz": "👤 Mening akkauntim", "en": "👤 My account"},
    "account_not_linked": {
        "ru": "👤 <b>Мой аккаунт</b>\n\nTelegram ещё не привязан к аккаунту на сайте.\n\nℹ️ Как привязать:\n1. Откройте профиль на {site}\n2. «Аккаунт» → «Привязать Telegram»\n3. Отправьте сюда: <code>/link КОД</code>",
        "uz": "👤 <b>Mening akkauntim</b>\n\nTelegram hali saytdagi akkauntga bog'lanmagan.\n\nℹ️ Qanday bog'lash:\n1. {site} saytida profilni oching\n2. «Akkaunt» → «Telegram bog'lash»\n3. Bu yerga yuboring: <code>/link KOD</code>",
        "en": "👤 <b>My account</b>\n\nTelegram isn't linked to a site account yet.\n\nℹ️ How to link:\n1. Open your profile at {site}\n2. 'Account' → 'Link Telegram'\n3. Send here: <code>/link CODE</code>",
    },
    "account_info": {
        "ru": "👤 <b>Мой аккаунт</b>\n\n📧 Email: <b>{email}</b>\n🙍 Имя: {name}\n📱 Телефон: {phone}{sub}",
        "uz": "👤 <b>Mening akkauntim</b>\n\n📧 Email: <b>{email}</b>\n🙍 Ism: {name}\n📱 Telefon: {phone}{sub}",
        "en": "👤 <b>My account</b>\n\n📧 Email: <b>{email}</b>\n🙍 Name: {name}\n📱 Phone: {phone}{sub}",
    },
    "account_sub_active": {
        "ru": "\n💳 Подписка: <b>{plan}</b> до {date}",
        "uz": "\n💳 Obuna: <b>{plan}</b> {date} gacha",
        "en": "\n💳 Subscription: <b>{plan}</b> until {date}",
    },
    "account_sub_none": {
        "ru": "\n💳 Подписка не активна",
        "uz": "\n💳 Obuna faol emas",
        "en": "\n💳 No active subscription",
    },
    "account_btn_resetpass": {"ru": "🔑 Сменить пароль", "uz": "🔑 Parolni o'zgartirish", "en": "🔑 Change password"},
    "account_btn_unlink": {"ru": "🔌 Отвязать Telegram", "uz": "🔌 Telegramni uzish", "en": "🔌 Unlink Telegram"},
    "account_btn_site": {"ru": "🌐 Открыть на сайте", "uz": "🌐 Saytda ochish", "en": "🌐 Open on site"},
    "account_unlink_confirm": {
        "ru": "⚠️ Точно отвязать Telegram от аккаунта? Вы потеряете доступ к /resetpass и статусу подписки в боте.",
        "uz": "⚠️ Telegramni akkauntdan uzasizmi? /resetpass va obuna holatiga botda kirish imkoniyatini yo'qotasiz.",
        "en": "⚠️ Really unlink Telegram from your account? You'll lose access to /resetpass and subscription status in the bot.",
    },
    "account_unlink_yes": {"ru": "✅ Да, отвязать", "uz": "✅ Ha, uzish", "en": "✅ Yes, unlink"},
    "account_unlink_no": {"ru": "✖️ Отмена", "uz": "✖️ Bekor qilish", "en": "✖️ Cancel"},
    "account_unlinked": {
        "ru": "✅ Telegram отвязан от аккаунта.",
        "uz": "✅ Telegram akkauntdan uzildi.",
        "en": "✅ Telegram unlinked from your account.",
    },
    "account_unlink_error": {
        "ru": "⚠️ Не удалось отвязать. Попробуйте позже.",
        "uz": "⚠️ Uzib bo'lmadi. Keyinroq urinib ko'ring.",
        "en": "⚠️ Could not unlink. Please try again later.",
    },
    # ── menu labels (extended menu) ──
    "menu_quick": {"ru": "🧮 Быстрая оценка", "uz": "🧮 Tez baholash", "en": "🧮 Quick estimate"},
    "menu_demo": {"ru": "🏠 Демо-расчёт", "uz": "🏠 Demo hisob", "en": "🏠 Demo estimate"},
    "menu_calc": {"ru": "📐 Полный расчёт", "uz": "📐 To'liq hisob", "en": "📐 Full calculation"},
    "menu_calc_new": {"ru": "🔁 Новый расчёт", "uz": "🔁 Yangi hisob", "en": "🔁 New calculation"},
    "menu_tools": {"ru": "🧰 Инженерные инструменты", "uz": "🧰 Muhandislik vositalari", "en": "🧰 Engineering tools"},
    "menu_mysub": {"ru": "💳 Моя подписка", "uz": "💳 Mening obunam", "en": "💳 My subscription"},
    "menu_status": {"ru": "📋 Мой заказ", "uz": "📋 Buyurtmam", "en": "📋 My order"},
    "menu_promo": {"ru": "🎁 Промокод", "uz": "🎁 Promokod", "en": "🎁 Promo code"},
    "menu_site": {"ru": "🌐 Открыть сайт", "uz": "🌐 Saytni ochish", "en": "🌐 Open site"},
    "menu_buy": {"ru": "🛒 Купить подписку", "uz": "🛒 Obuna sotib olish", "en": "🛒 Buy subscription"},
    "menu_admin": {"ru": "👑 Админ-панель", "uz": "👑 Admin panel", "en": "👑 Admin panel"},
    # ── tools submenu ──
    "tools_title": {
        "ru": "🧰 <b>Инженерные инструменты</b>\n\nБыстрые расчёты без визарда — выберите инструмент:",
        "uz": "🧰 <b>Muhandislik vositalari</b>\n\nSehrgarsiz tez hisoblar — vositani tanlang:",
        "en": "🧰 <b>Engineering tools</b>\n\nQuick calculators, no wizard — pick a tool:"},
    "tool_boiler": {"ru": "⚙️ Подбор котла", "uz": "⚙️ Qozon tanlash", "en": "⚙️ Boiler selector"},
    "tool_rad": {"ru": "🔧 Расчёт радиаторов", "uz": "🔧 Radiator hisobi", "en": "🔧 Radiator sizing"},
    "tool_fuel": {"ru": "💰 Стоимость отопления", "uz": "💰 Isitish narxi", "en": "💰 Heating cost"},
    "tool_insul": {"ru": "❄️ Толщина утеплителя", "uz": "❄️ Uteplitel qalinligi", "en": "❄️ Insulation thickness"},
    "tool_conv": {"ru": "📏 Конвертер мощности", "uz": "📏 Quvvat konverteri", "en": "📏 Power converter"},
    "tool_cities": {"ru": "🌡 Города и температуры", "uz": "🌡 Shaharlar va harorat", "en": "🌡 Cities & temps"},
    "back_tools": {"ru": "◀️ К инструментам", "uz": "◀️ Vositalarga", "en": "◀️ To tools"},
    # ── quick estimate ──
    "quick_ask_area": {
        "ru": "🧮 <b>Быстрая оценка теплопотерь</b>\n\nВведите отапливаемую площадь объекта в м² (например 120):",
        "uz": "🧮 <b>Tez baholash</b>\n\nIsitiladigan maydonni m² da kiriting (masalan 120):",
        "en": "🧮 <b>Quick heat-loss estimate</b>\n\nEnter the heated area in m² (e.g. 120):"},
    "quick_ask_quality": {
        "ru": "🏗 Площадь: <b>{area} м²</b>.\n\nКакое утепление у здания?",
        "uz": "🏗 Maydon: <b>{area} m²</b>.\n\nBino qanday uteplangan?",
        "en": "🏗 Area: <b>{area} m²</b>.\n\nHow well is the building insulated?"},
    "quick_q_good": {"ru": "🟢 Хорошее (новое, утеплён)", "uz": "🟢 Yaxshi (yangi, uteplangan)", "en": "🟢 Good (new, insulated)"},
    "quick_q_avg": {"ru": "🟡 Среднее (кирпич/блок)", "uz": "🟡 O'rtacha (g'isht/blok)", "en": "🟡 Average (brick/block)"},
    "quick_q_poor": {"ru": "🔴 Слабое (старое, щели)", "uz": "🔴 Zaif (eski, g'ovak)", "en": "🔴 Poor (old, drafty)"},
    "quick_result": {
        "ru": "🧮 <b>Быстрая оценка</b>\n\n📐 Площадь: <b>{area} м²</b> · {qlabel}\n🔥 Теплопотери: <b>≈ {kw} кВт</b> ({wm2} Вт/м²)\n⚙️ Котёл с запасом: <b>{boiler} кВт</b>\n🔧 Радиаторы: <b>≈ {sections} секц.</b> (80/60)\n💰 Газ: ≈ <b>{gas} сум/мес</b>\n\n<i>Ориентировочно. Точный расчёт — «📐 Полный расчёт» или заявка специалисту.</i>",
        "uz": "🧮 <b>Tez baholash</b>\n\n📐 Maydon: <b>{area} m²</b> · {qlabel}\n🔥 Issiqlik yo'qotishi: <b>≈ {kw} kVt</b> ({wm2} Vt/m²)\n⚙️ Qozon zaxira bilan: <b>{boiler} kVt</b>\n🔧 Radiatorlar: <b>≈ {sections} seksiya</b> (80/60)\n💰 Gaz: ≈ <b>{gas} so'm/oy</b>\n\n<i>Taxminiy. Aniq hisob — «📐 To'liq hisob» yoki mutaxassisga ariza.</i>",
        "en": "🧮 <b>Quick estimate</b>\n\n📐 Area: <b>{area} m²</b> · {qlabel}\n🔥 Heat loss: <b>≈ {kw} kW</b> ({wm2} W/m²)\n⚙️ Boiler with margin: <b>{boiler} kW</b>\n🔧 Radiators: <b>≈ {sections} sec.</b> (80/60)\n💰 Gas: ≈ <b>{gas} sum/mo</b>\n\n<i>Approximate. For an exact figure use “📐 Full calculation” or request a specialist.</i>"},
    # ── boiler selector ──
    "boiler_ask_kw": {
        "ru": "⚙️ <b>Подбор котла</b>\n\nВведите теплопотери объекта в кВт (например 12.5).\nНе знаете? Сначала сделайте «🧮 Быструю оценку».",
        "uz": "⚙️ <b>Qozon tanlash</b>\n\nIssiqlik yo'qotishini kVt da kiriting (masalan 12.5).",
        "en": "⚙️ <b>Boiler selector</b>\n\nEnter the object's heat loss in kW (e.g. 12.5)."},
    "boiler_result": {
        "ru": "⚙️ <b>Подбор котла</b>\n\n🔥 Теплопотери: <b>{kw} кВт</b>\n➕ С запасом 25%: <b>{margin} кВт</b>\n📦 Типоразмер котла: <b>{size} кВт</b>\n🔩 Модель: <b>{model}</b>\n   <i>{type}</i>\n🟦 Магистраль: труба Ø <b>{pipe} мм</b>",
        "uz": "⚙️ <b>Qozon tanlash</b>\n\n🔥 Issiqlik yo'qotishi: <b>{kw} kVt</b>\n➕ 25% zaxira bilan: <b>{margin} kVt</b>\n📦 Qozon o'lchami: <b>{size} kVt</b>\n🔩 Model: <b>{model}</b>\n   <i>{type}</i>\n🟦 Magistral: quvur Ø <b>{pipe} mm</b>",
        "en": "⚙️ <b>Boiler selector</b>\n\n🔥 Heat loss: <b>{kw} kW</b>\n➕ +25% margin: <b>{margin} kW</b>\n📦 Boiler size: <b>{size} kW</b>\n🔩 Model: <b>{model}</b>\n   <i>{type}</i>\n🟦 Main line: pipe Ø <b>{pipe} mm</b>"},
    # ── radiator sizing ──
    "rad_ask_kw": {
        "ru": "🔧 <b>Расчёт радиаторов</b>\n\nВведите теплопотери <b>помещения</b> в кВт (например 1.6):",
        "uz": "🔧 <b>Radiator hisobi</b>\n\n<b>Xona</b> issiqlik yo'qotishini kVt da kiriting (masalan 1.6):",
        "en": "🔧 <b>Radiator sizing</b>\n\nEnter the <b>room</b> heat loss in kW (e.g. 1.6):"},
    "rad_result": {
        "ru": "🔧 <b>Секции радиатора</b> (t возд. 20°C, +15% запас)\n\n🔥 Нагрузка: <b>{kw} кВт</b>\n\n♨️ 90/70: <b>{s9070} секц.</b>\n♨️ 80/60: <b>{s8060} секц.</b>\n♨️ 75/65: <b>{s7565} секц.</b>\n\n🔩 Модель: <b>{model}</b>\n<i>{spec}</i>",
        "uz": "🔧 <b>Radiator seksiyalari</b> (havo 20°C, +15% zaxira)\n\n🔥 Yuklama: <b>{kw} kVt</b>\n\n♨️ 90/70: <b>{s9070} sek.</b>\n♨️ 80/60: <b>{s8060} sek.</b>\n♨️ 75/65: <b>{s7565} sek.</b>\n\n🔩 Model: <b>{model}</b>\n<i>{spec}</i>",
        "en": "🔧 <b>Radiator sections</b> (air 20°C, +15% margin)\n\n🔥 Load: <b>{kw} kW</b>\n\n♨️ 90/70: <b>{s9070} sec.</b>\n♨️ 80/60: <b>{s8060} sec.</b>\n♨️ 75/65: <b>{s7565} sec.</b>\n\n🔩 Model: <b>{model}</b>\n<i>{spec}</i>"},
    # ── heating cost ──
    "fuel_ask_kw": {
        "ru": "💰 <b>Стоимость отопления</b>\n\nВведите теплопотери объекта в кВт (например 12.5):",
        "uz": "💰 <b>Isitish narxi</b>\n\nIssiqlik yo'qotishini kVt da kiriting (masalan 12.5):",
        "en": "💰 <b>Heating cost</b>\n\nEnter the object's heat loss in kW (e.g. 12.5):"},
    "fuel_result": {
        "ru": "💰 <b>Стоимость отопления</b> (тарифы UZ, нагрузка {load}%)\n\n🔥 Мощность: <b>{kw} кВт</b>\n📊 Расход: ~{kwh} кВт·ч/мес\n\n{lines}\n\n<i>За сезон (~4 мес) — примерно ×4. Оценочно.</i>",
        "uz": "💰 <b>Isitish narxi</b> (UZ tariflari, yuklama {load}%)\n\n🔥 Quvvat: <b>{kw} kVt</b>\n📊 Sarf: ~{kwh} kVt·s/oy\n\n{lines}\n\n<i>Mavsumga (~4 oy) — taxminan ×4.</i>",
        "en": "💰 <b>Heating cost</b> (UZ tariffs, load {load}%)\n\n🔥 Power: <b>{kw} kW</b>\n📊 Use: ~{kwh} kWh/mo\n\n{lines}\n\n<i>Per season (~4 mo) ≈ ×4. Approximate.</i>"},
    # ── insulation thickness ──
    "insul_ask_current": {
        "ru": "❄️ <b>Толщина утеплителя</b>\n\nШаг 1/2. Текущее сопротивление стены R, м²·°C/Вт (например 0.75 для кирпича 380).\n\nПодсказка: R стены есть в «📚 Справочнике материалов».",
        "uz": "❄️ <b>Uteplitel qalinligi</b>\n\n1/2-qadam. Devorning joriy R qarshiligi (masalan 0.75):",
        "en": "❄️ <b>Insulation thickness</b>\n\nStep 1/2. Current wall R, m²·°C/W (e.g. 0.75 for 380 brick):"},
    "insul_ask_target": {
        "ru": "🎯 Шаг 2/2. Целевое R, м²·°C/Вт.\n\nНорма для стен в UZ ≈ <b>2.5–3.0</b>. Введите, например 2.8:",
        "uz": "🎯 2/2-qadam. Maqsadli R.\n\nUZ devorlar normasi ≈ <b>2.5–3.0</b>. Masalan 2.8:",
        "en": "🎯 Step 2/2. Target R.\n\nUZ wall norm ≈ <b>2.5–3.0</b>. Enter e.g. 2.8:"},
    "insul_result": {
        "ru": "❄️ <b>Нужная толщина утеплителя</b>\n\nR: <b>{cur}</b> → <b>{tgt}</b> (ΔR = {dr})\n\n{lines}\n\n<i>Толщина ≈ ΔR · λ. Берите ближайшую большую плиту.</i>",
        "uz": "❄️ <b>Kerakli uteplitel qalinligi</b>\n\nR: <b>{cur}</b> → <b>{tgt}</b> (ΔR = {dr})\n\n{lines}\n\n<i>Qalinlik ≈ ΔR · λ.</i>",
        "en": "❄️ <b>Required insulation thickness</b>\n\nR: <b>{cur}</b> → <b>{tgt}</b> (ΔR = {dr})\n\n{lines}\n\n<i>Thickness ≈ ΔR · λ. Round up to the next board.</i>"},
    "insul_already": {
        "ru": "✅ Текущее R уже не меньше целевого — дополнительный утеплитель не нужен.",
        "uz": "✅ Joriy R maqsaddan kam emas — qo'shimcha uteplitel kerak emas.",
        "en": "✅ Current R already meets the target — no extra insulation needed."},
    # ── power converter ──
    "conv_ask_kw": {
        "ru": "📏 <b>Конвертер мощности</b>\n\nВведите мощность в кВт (например 12.5):",
        "uz": "📏 <b>Quvvat konverteri</b>\n\nQuvvatni kVt da kiriting (masalan 12.5):",
        "en": "📏 <b>Power converter</b>\n\nEnter power in kW (e.g. 12.5):"},
    "conv_result": {
        "ru": "📏 <b>{kw} кВт</b> =\n\n• <b>{kcal}</b> ккал/ч\n• <b>{btu}</b> BTU/ч\n• <b>{hp}</b> л.с.\n• <b>{w}</b> Вт",
        "uz": "📏 <b>{kw} kVt</b> =\n\n• <b>{kcal}</b> kkal/s\n• <b>{btu}</b> BTU/s\n• <b>{hp}</b> o.k.\n• <b>{w}</b> Vt",
        "en": "📏 <b>{kw} kW</b> =\n\n• <b>{kcal}</b> kcal/h\n• <b>{btu}</b> BTU/h\n• <b>{hp}</b> hp\n• <b>{w}</b> W"},
    # ── cities & design temps ──
    "cities_title": {
        "ru": "🌡 <b>Расчётные зимние температуры (параметр Б)</b>\nпо КМК 2.01.01-94:\n",
        "uz": "🌡 <b>Hisobiy qishki haroratlar (parametr B)</b>\nKMK 2.01.01-94 bo'yicha:\n",
        "en": "🌡 <b>Design winter temperatures (parameter B)</b>\nper KMK 2.01.01-94:\n"},
    # ── promo checker ──
    "promo_ask": {
        "ru": "🎁 <b>Проверка промокода</b>\n\nОтправьте промокод одним сообщением:",
        "uz": "🎁 <b>Promokodni tekshirish</b>\n\nPromokodni bitta xabar bilan yuboring:",
        "en": "🎁 <b>Check a promo code</b>\n\nSend the promo code in one message:"},
    "promo_ok": {
        "ru": "✅ Промокод <b>{code}</b> действует: скидка <b>−{disc}%</b>.\nПрименится при оформлении в «🛒 Купить подписку».",
        "uz": "✅ <b>{code}</b> promokod amal qiladi: <b>−{disc}%</b> chegirma.\n«🛒 Obuna sotib olish» da qo'llanadi.",
        "en": "✅ Promo <b>{code}</b> is valid: <b>−{disc}%</b> off.\nApplies at checkout in “🛒 Buy subscription”."},
}


def t(key, lang=DEFAULT_LANG, **fmt):
    entry = STR.get(key)
    if not entry:
        return key
    s = entry.get(lang) or entry.get(DEFAULT_LANG) or key
    if fmt:
        try:
            s = s.format(**fmt)
        except (KeyError, IndexError):
            pass
    return s


def loc_name(item, lang):
    """Localized display name for a preset / room-type dict."""
    if lang == "uz":
        return item.get("nameUz") or item.get("name")
    if lang == "en":
        return item.get("nameEn") or item.get("name")
    return item.get("name")
