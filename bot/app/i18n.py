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
        "ru": "🔥 <b>Aquality | WaterPro</b> — калькулятор теплопотерь\n\nРассчитаю теплопотери дома по нормам КМК 2.01.04-18, подберу мощность котла и количество секций радиаторов. Бесплатно и за пару минут.\n\nВыберите действие:",
        "uz": "🔥 <b>Aquality | WaterPro</b> — issiqlik yo'qotishlari kalkulyatori\n\nUyning issiqlik yo'qotishlarini KMK 2.01.04-18 bo'yicha hisoblab, qozon quvvati va radiator seksiyalari sonini tanlab beraman. Bepul va bir necha daqiqada.\n\nAmalni tanlang:",
        "en": "🔥 <b>Aquality | WaterPro</b> — heat-loss calculator\n\nI'll compute your building's heat loss per KMK 2.01.04-18, size the boiler and the number of radiator sections. Free, in a couple of minutes.\n\nChoose an action:"},
    "menu_calc": {"ru": "🧮 Рассчитать теплопотери", "uz": "🧮 Issiqlik yo'qotishini hisoblash", "en": "🧮 Calculate heat loss"},
    "menu_demo": {"ru": "🏡 Демо-расчёт (пример дома)", "uz": "🏡 Demo-hisob (uy namunasi)", "en": "🏡 Demo (example house)"},
    "menu_materials": {"ru": "📚 Справочник материалов", "uz": "📚 Materiallar ma'lumotnomasi", "en": "📚 Materials library"},
    "menu_contact": {"ru": "📞 Контакты", "uz": "📞 Aloqa", "en": "📞 Contacts"},
    "menu_faq": {"ru": "❓ Как считается?", "uz": "❓ Qanday hisoblanadi?", "en": "❓ How it works"},
    "menu_lang": {"ru": "🌐 Язык", "uz": "🌐 Til", "en": "🌐 Language"},
    "menu_lead": {"ru": "✍️ Оставить заявку", "uz": "✍️ Ariza qoldirish", "en": "✍️ Request a consult"},
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
