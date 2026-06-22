# Moderation wordlists (Phase 9.1)

Категоризированные словари для content moderation pipeline OutstaffingBot.
Один термин — одна строка, lowercase, дедупликация между файлами (приоритет: **sex → drugs → translit → profanity**).

## Файлы

| Файл | Назначение | Терминов (≈) |
|------|------------|--------------|
| `stop_words_profanity.txt` | Мат / ненормативная лексика (RU) | **8348** |
| `stop_words_sex.txt` | Эскорт, prostitution, adult services | **313** |
| `stop_words_drugs.txt` | Наркотики, slang, darknet-площадки | **358** |
| `stop_words_translit.txt` | Латиница / obfuscation (GOVNO, PIDOR, mephedrone…) | **50** |
| `allow_words_alcohol.txt` | Whitelist-справочник для Phase 9.5 (не блок-лист) | **62** |

Пересборка: `python build_wordlists.py` (исходники в `_sources/`).

## Источники и лицензии

### Profanity / mat

| Источник | URL | Лицензия | Как использован |
|----------|-----|----------|-----------------|
| **badwords-py** (FlacSy/BadWords) | https://github.com/FlacSy/BadWords · PyPI `badwords-py` | MIT | Экспорт RU-слов через `ProfanityFilter.init(languages=['ru'])` → **3571** термин |
| **readme-SVG/Banned-words** | https://github.com/readme-SVG/Banned-words/blob/main/Banned-words-list/ru.txt | **Apache-2.0** | Vendored: `_sources/ru_banned_readme_svg.txt` → **4241** термин |
| **Krugozor ProfanityWordsValidator** | https://github.com/Vasiliy-Makogon/RussianBadWords | (repo, без явной LICENSE в корне) | Парсинг `_sources/krugozor_profanity.php` → **1849** термин |

### Sex / escort

| Источник | Как использован |
|----------|-----------------|
| **Krugozor StopWordsValidator** (sex block) | Блок `'мжм'` … `'мочеиспускание'` → **105** термин |
| **CensureBlock ex-ussr** | Regex-roots из `0.42-ex-ussr.txt` (ri-sh/censureblock) → **45** корней |
| **kugimiya «Банлист Алисы»** | https://gist.github.com/kugimiya/5ddf7dfb80c5e57081e54a1513c0a4bc — фильтр по sex-stems → **68** |
| **hacking-buds bad_terms** | https://github.com/jbfeldman/hacking-buds — только Reason «prostitution/trafficking» → **74** фраз/слова |
| **Custom (manual)** | досуг, массаж 18+, vip девушки, intim uslugi, escort service… → **72** |

### Drugs

| Источник | Как использован |
|----------|-----------------|
| **Krugozor StopWordsValidator** (drug blocks) | Секции «Наркоманский жаргон», препараты, площадки → **362** |
| **kugimiya banlist** | Фильтр по drug-stems → **17** |
| **Custom (manual)** | закладка, zakladka, клад, кладмен, mephedrone variants… → **61** |

### Transliteration

| Источник | Как использован |
|----------|-----------------|
| **Manual seed** | GOVNO, PIDOR, HUY, BLYAT, Mephedron, zakladka… → **55** |
| **badwords-py / profanity lists** | Латинские токены с profanity/drug/sex stems → merged |

## Что исключено (false positives для outstaffing)

- **Алкоголь** — термины в `allow_words_alcohol.txt`; удалены из block-листов (бар, коктейли, сомелье, вино…).
- **hacking-buds** — не включены ethnicity/transitive фразы (Asian, New in town…).
- **kugimiya** — только паттерны, совпадающие с sex/drug stems (не политика/протесты).
- **Krugozor** — VPN, кредиты, гадания, оружие и пр. **не** попали в эти 4 словаря.
- **EXCLUDE_FALSE_POSITIVES** в `build_wordlists.py` — омонимы жаргона и business-слова, не возвращаются при пересборке.

### False positives removed

Список в `EXCLUDE_FALSE_POSITIVES` (`build_wordlists.py`). Удалены при пересборке **2025-06-23**.

**stop_words_drugs.txt** (−54, 412 → 358) — омонимы Krugozor «наркоманский жаргон» и EN marketplace-токены:

| RU (быт / работа) | EN (business / быт) |
|-------------------|---------------------|
| план, взбодриться, агрегат, болтанка, болтушка, варево, доза, канюля, карбид, кикер, кокс, крис, кристалл, кристалы, крисы, кроссвордный, кумар, миксы, натур, оттянуться, пинки, пласт, подзаправиться, расколбаситься, стимульнуться, треснуться, ужалиться, ускоритель, **фен** (фен для волос; префикс «фен*» в названиях препаратов остаётся), мача, мулька, шала, жмых, брахман, гарик, марго, вторяк, духарь, калики, килики | asap, onion, ramp, mega, versus, empire, evolution, monopoly, incognito, omg |

Также исправлен парсер Krugozor: заголовок секции «наркоманский жаргон…» больше не попадает в словарь.

**stop_words_sex.txt** (−9, 322 → 313) — hacking-buds vs вакансии:

`teen`, `teens`, `young`, `youngs`, `branding`, `finesse`, `quota`, `purchaser`, `seasoning`

**stop_words_profanity.txt** — без изменений (8348).  
**stop_words_translit.txt** — без изменений (50).

**Не удаляли** (намеренно): `соль` (не было в списках), `шмаль`, `косяк`, `закладка`, `феназепам`/`фентанил` и др. однозначный drug/sex/profanity контент; `asap-market`, `megadarknet` и составные darknet-имена.

## Attribution

```
# readme-SVG/Banned-words (Apache-2.0)
Copyright readme-SVG contributors
https://github.com/readme-SVG/Banned-words

# badwords-py (MIT)
Copyright FlacSy / BadWords contributors
https://github.com/FlacSy/BadWords

# CensureBlock ex-ussr subscription
Vasiliy Temnikov — censureblock@gmail.com
https://github.com/ri-sh/censureblock

# Krugozor RussianBadWords
https://github.com/Vasiliy-Makogon/RussianBadWords

# hacking-buds / Poirot bad_terms
https://github.com/jbfeldman/hacking-buds

# kugimiya «Банлист Алисы»
https://gist.github.com/kugimiya/5ddf7dfb80c5e57081e54a1513c0a4bc
```

## Интеграция (Phase 9.1)

```python
# Загрузка (пример)
from pathlib import Path

MOD_DIR = Path(__file__).resolve().parent / "data" / "moderation"

def load_terms(name: str) -> frozenset[str]:
    path = MOD_DIR / name
    return frozenset(
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )

PROFANITY = load_terms("stop_words_profanity.txt")
SEX = load_terms("stop_words_sex.txt")
DRUGS = load_terms("stop_words_drugs.txt")
TRANSLIT = load_terms("stop_words_translit.txt")
ALCOHOL_ALLOW = load_terms("allow_words_alcohol.txt")
```

См. также: [docs/TASKS.md § Phase 9.1](../../../docs/TASKS.md#91-content-moderation--базовый-pipeline-p0), [docs/PLAN.md § 10.1](../../../docs/PLAN.md#101-content-moderation--compliance).
