# Research: категория «насилие / угрозы» (Phase 9.x)

Дата: 2026-07-09. Только исследование — без реализации.

## Контекст кодовой базы

### Текущая структура `backend/data/moderation/`

| Файл | Роль |
|------|------|
| `stop_words_profanity.txt` | Мат / оскорбления (~8134) |
| `stop_words_sex.txt` | Эскорт, adult (~237) |
| `stop_words_drugs.txt` | Наркотики (~374) |
| `stop_words_translit.txt` | Латиница / obfuscation (~56) |
| `stop_words_slang_manual.txt` | Жаргон и фразы — **exact-only**, без lemma (~408) |
| `context_required.txt` | Омонимы — не блокировать слепо |
| `allow_words_alcohol.txt` | Whitelist (не block) |

Пересборка: `build_wordlists.py`. Приоритет дедупа: **sex → drugs → translit → profanity**.

### Что уже есть по насилию

- В `krugozor_stopwords.php` (уже vendored) есть блоки **суицид/убийство**, **оружие**, **экстремизм** — **намеренно не включены** в текущие словари (README § «Что исключено»).
- В `GLOBAL_EXCLUDE` / `EXCLUDE_FALSE_POSITIVES`: `смерть`, `убить`, `убивать`, `рецепт`, `донор` — исключены из всех категорий.
- `насилие` попало в `stop_words_sex.txt` через CensureBlock sex-stems — **не то же самое**, что угрозы/оружие.
- `content_moderation_service.py`: категории `profanity | sex | drugs | translit | slang` — **violence отсутствует**.

### Рекомендация по архитектуре

**Отдельная категория `stop_words_violence.txt`** — предпочтительный путь.

| Вариант | Вердикт |
|---------|---------|
| Новый `stop_words_violence.txt` | ✅ Основной |
| Расширение `profanity` | ❌ Смешивает мат и угрозы; неверный `category` в violation log |
| Только `slang_manual` | ⚠️ Частично — для **многословных фраз** (`убью тебя`, `хана тебе`), но не для лемм `уби-`, `изби-` |
| Krugozor «как есть» | ❌ Много FP для job ads (`донор`, `рецепт`, `огнестрел` в охране) |

Предлагаемый приоритет дедупа: **sex → violence → drugs → translit → profanity**.

Фразы-угрозы (2+ слова) — в `stop_words_violence.txt` **или** дублировать в `slang_manual` только если нужен exact без lemma (как сейчас для drug slang).

---

## Таблица источников (топ 10)

| # | Источник | URL | Лицензия | Язык | Размер / формат | Качество | OSS public repo | Подходит для job-ad moderation |
|---|----------|-----|----------|------|-----------------|----------|-----------------|--------------------------------|
| 1 | **Krugozor StopWords** (блоки суицид/оружие/экстремизм) | https://github.com/Vasiliy-Makogon/RussianBadWords · уже в `_sources/krugozor_stopwords.php` | Нет явной LICENSE в корне | RU | ~40–60 терминов в релевантных секциях; PHP-массив | Курируемый под РКН; практический | ⚠️ Vendoring OK, attribution в README | ⚠️ Частично — нужна жёсткая FP-фильтрация (`донор`, `рецепт`, `огнестрел`) |
| 2 | **vsecoder/ru-toxic-messages-classification** — rule-based `THREAT_*` | https://github.com/vsecoder/ru-toxic-messages-classification · `make_multilabel.py` | Проверить LICENSE в repo (типично MIT) | RU | ~25 regex-паттернов угроз | Высокое — учитывает 2-е лицо для directional threats | ✅ Да | ✅ **Лучший стартовый seed** для outstaffing (убью+тебя, зарежу, сдохни…) |
| 3 | **VK / Habr — protected identities (категория threats)** | https://vk.cc/aAS3TQ · статья https://habr.com/ru/companies/vk/articles/546186/ | Academic / research | RU | 214 слов всего, ~20–30 в «threats» | Курируемый, но про **identity-bias**, не чистое насилие | ✅ Цитирование в academic | ⚠️ Слабо — `выезжать`, `айпи` не violence |
| 4 | **HurtLex RU (категория RE — felonies/crime)** | https://github.com/valeriobasile/hurtlex/tree/master/lexica/RU | Academic resource (CC-style, см. публикацию LREC 2018) | RU | ~1.5–2k headwords всего; RE — подмножество | Академически курируемый | ✅ Да с attribution | ⚠️ Crime ≠ threat; много нейтральных юридических терминов |
| 5 | **Shlyakhov & Adler — Dictionary of Russian Slang** | Уже в `_sources/academic/txt/shlyakhov_adler_dict.txt` | Книга / fair use для research | RU+EN | Сотни idiom «threat/beat/kill» | Справочник жаргона, не machine list | ⚠️ Extract + curate | ✅ Фразы для ручной курации (`оторву башку`, `впиздячу`) |
| 6 | **TextDetox multilingual_toxic_lexicon** | https://huggingface.co/datasets/textdetox/multilingual_toxic_lexicon | openrail++ | RU+multilingual | RU: **140 517** строк | Сырой агрегат мат/токсичности | ✅ С attribution | ❌ Не violence-specific; 99% дубль profanity |
| 7 | **ContentShield** (категория VIOLENCE) | https://github.com/ZachHandley/ContentShield | Проверить repo LICENSE | RU+19 lang | RU ~215 entries total | Категории есть, RU в основном profanity-источники | ✅ | ⚠️ Слабая violence-насыщенность для RU |
| 8 | **Microsoft RTP-LX** | https://github.com/microsoft/RTP-LX | Open dataset (см. repo) | 38 языков | Prompts/completions, не wordlist | Размеченные примеры Violence | ✅ Research | ❌ Не wordlist; для ML-eval, не для exact match |
| 9 | **NVIDIA Aegis / Nemotron Content Safety** | https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-1.0 | **CC-BY-4.0** | EN (taxonomy) | 13 harm categories incl. Violence, Threat | ML training data | ✅ | ❌ Не лексикон; EN-first |
| 10 | **LDNOOBW V2** | https://github.com/LDNOOBWV2/List-of-Dirty-Naughty-Obscene-and-Otherwise-Bad-Words_V2 | Open (Shutterstock heritage) | RU: 4948 | `.txt` lowercase | Profanity, **нет** violence category | ✅ | ❌ Уже частично покрыт profanity |

### Дополнительно рассмотренные (не в топ-10)

| Источник | Почему не primary |
|----------|-------------------|
| readme-SVG/Banned-words, bars38, 4troDev/profanity.csv | Мат/оскорбления — уже в profanity |
| HateBase | Только **17** RU слов |
| mokoron / VK abusive filter | Нет публичного static wordlist; нейросеть + unofficial leak |
| Potapova/Gordeev aggression corpora | ML-датасеты, не готовый словарь |
| Grievance Dictionary | **EN-only** (20k words) |
| OWASP AISVS | Рекомендует ML/multi-layer, **не публикует** violence wordlist |
| Sightengine rule-based API | Commercial, не OSS |

---

## Свободно используемые для OSS public repo

| ✅ Рекомендуется vend + attribution | ⚠️ С оговорками | ❌ Не для прямого импорта |
|-------------------------------------|-----------------|-------------------------|
| vsecoder threat rules (extract terms) | Krugozor (нет LICENSE — только curated extract + ссылка) | TextDetox 140k RU (шум + license review) |
| HurtLex RE subset | VK list (bias-research, не violence lexicon) | Commercial APIs (Sightengine) |
| Shlyakhov academic extract | ContentShield (проверить LICENSE) | HateBase (слишком мало) |
| Manual seed + тесты проекта | LDNOOBW (дубль profanity) | |

---

## План реализации (после approve)

### Phase 1 — Download / vend

```text
_sources/violence/
  krugozor_violence_extract.txt   # парс секций suicide/weapons/extremism из PHP
  vsecoder_threat_terms.txt       # извлечь корни из THREAT_* regex
  hurtlex_ru_re.tsv               # subset RE category
  manual_seed_violence.txt        # убью, избью, зарежу, расстреляю, истреблю…
```

### Phase 2 — Extract

- Скрипт `extract_violence_candidates.py` (по аналогии с `academic/extract_terms.py`).
- Shlyakhov: regex по `threat|beat|kill|убью|избить|угроз` → `candidates_phrases.txt`.

### Phase 3 — Curate

- Убрать FP из `EXCLUDE_FALSE_POSITIVES` **только для violence bucket** (не глобально):
  - `убить` / `убивать` → **не** однословный block; только фразы или lemma+context (Phase 9.4+).
  - `смерть`, `донор`, `рецепт` — оставить в exclude.
  - Омонимы в `context_required.txt`: `автомат`, `порезать` (кулинария), `дубинка` (охранник?), `кровь` (медицина).
- Krugozor extremism (`игил`, `джихад`…) — включать осторожно (политический FP в новостных вакансиях маловероятен, но возможен).

Целевой размер после курации: **80–200** однозначных терминов + **30–50** фраз.

### Phase 4 — Integrate

1. `build_wordlists.py`: `VIOLENCE_STEMS`, `classify()` → `"violence"`, приоритет dedupe.
2. `content_moderation_service.py`: загрузка `stop_words_violence.txt`, `_category_for_term()` → `"violence"`.
3. `README.md` + attribution.
4. Тесты `test_content_moderation.py`:
   - block: «убью тебя», «зарежу вас», «сдохни», «изобью до полусмерти»
   - allow: «убью время на проекте», «отбить атаку», «смертность снизилась», «донор крови», «рецепт успеха»

---

## Предупреждения: омонимы и false positives

| Паттерн | Риск FP | Рекомендация |
|---------|---------|--------------|
| `убью` / `убить` | «убью время», «убить баг», «убить двух зайцев» | Фразы в slang; однословно — `context_required` или block только с `тебя/вас` |
| `избить` | «отбить конкурентов», спорт | context или фразовый match |
| `порезать` | кулинария, «порезать бюджет» | context_required |
| `расстрел` | фото «расстрел объектов» | осторожно; возможно только в фразах |
| `насилие` | юридический/социальный контекст («против насилия») | убрать из sex-stem; в violence только с модификаторами или не включать |
| `огнестрел`, `травмат`, `дубинка` | охранник, тира, лицензии | allow-list для профессий или context |
| `кровь` | медицина, донорство | context_required |
| Threat + 2nd person | vsecoder подход — **правильная модель** для Phase 9.4 proximity |

---

## Вывод

Готового open-source **Russian violence wordlist** уровня profanity/drugs **не существует**. Лучшая стратегия для OutstaffingBot:

1. **Seed из vsecoder threat rules** (открытый, курируемый, учитывает направленность).
2. **Выборочный extract из Krugozor** (оружие/экстремизм, без medical FP).
3. **HurtLex RE** как дополнение (с ручной фильтрацией).
4. **Shlyakhov** для разговорных фраз.
5. **Новая категория** `stop_words_violence.txt` + тесты FP — не расширять profanity.

OWASP / EU lexicons дают **таксономии и ML-датасеты**, не готовые RU stop-lists для job moderation.
