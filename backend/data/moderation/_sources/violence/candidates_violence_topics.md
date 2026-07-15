# Violence candidates — detailed per-topic research report

Дата: 2026-07-09. **Candidates only** — не в live `stop_words_violence.txt`.

**Итого уникальных токенов:** 672 | **Фраз:** 100

---

## 1. Terrorism / extremism RU

**Токенов в секции:** 88

### WebSearch queries
- `терроризм словарь модерация русский стоп слова github`
- `экстремизм стоп слова список РКН запрещённые термины`
- `IGIL исламское государство русский жаргон термины`
- `игилизация игиловщина cyberleninka`
- `security.urfu.ru основные термины экстремизм`

### Source URLs
- https://github.com/Vasiliy-Makogon/RussianBadWords
- https://minjust.gov.ru/ru/extremist-materials/
- https://cyberleninka.ru/article/n/novaya-religiozno-politicheskaya-leksika-v-rossiyskih-smi-i-internet-diskurse-na-primere-proizvodnyh-slova-igil
- https://security.urfu.ru/ru/protivodeistvie-ehkstremizmu-i-terrorizmu/osnovnye-terminy-i-opredelenija/
- https://ru.wikipedia.org/wiki/Терроризм

### Local extracts
- `web_terrorism_urfu.txt` — 50 raw lines/terms
- `web_cyberleninka_igil.txt` — 20 raw lines/terms
- `web_islamism_terms.txt` — 37 raw lines/terms
- `krugozor_stopwords.php` — 37 raw lines/terms
- `kugimiya_banlist.yaml` — 16 raw lines/terms

**Quality notes:** MinJust публикует реестр материалов, не готовый wordlist. UrFU glossary + CyberLeninka IGIL derivatives — лучшие открытые RU термины. Islamism отделён от религии.

---

## 2. SVO / war

**Токенов в секции:** 94

### WebSearch queries
- `сво стоп слова модерация спецоперация`
- `мобилизация запрещённые фразы военная цензура слова россия`
- `спецоперация модерация дискредитация армии`
- `globalvoices российская пропаганда новояз война`
- `svoboda.org военная цензура год`

### Source URLs
- https://ru.globalvoices.org/2023/02/06/114977/
- https://ru.wikipedia.org/wiki/Цензура_в_России_во_время_вторжения_на_Украину
- https://www.svoboda.org/a/32293987.html
- https://praguesupport.com/wp-content/uploads/2025/09/war-glossary_full-version_for-printing_13092025.pdf
- https://ru.ruwiki.ru/wiki/Жаргон_участников_СВО

### Local extracts
- `web_war_glossary_ru.txt` — 83 raw lines/terms
- `web_dfrlab_rkn_tags.txt` — 8 raw lines/terms
- `kugimiya_banlist.yaml` — 16 raw lines/terms

**Quality notes:** Нет публичного RU stop-list от РКН. Prague Support war glossary (~500+ RU/UA slang pairs) + DFRLab/iStories Vepr tags — основной массив. FP: «спецоперация» медицинская.

---

## 3. Ukraine conflict

**Токенов в секции:** 94

### WebSearch queries
- `украина модерация telegram бандера сленг термины`
- `неонацизм украина термины русский словарь`
- `бандерівці wikipedia propaganda`
- `OPORA насильницька риторика telegram`
- `vk habr фильтр враждебных высказываний`

### Source URLs
- https://uk.wikipedia.org/wiki/бандерівці
- https://oporaua.org/viyna/nasil-nic-ka-ritorika-v-ukrayins-komu-segmenti-telegram-final-niy-zvit-26048
- https://habr.com/ru/companies/vk/articles/546186/
- https://github.com/hse-scila/ethnohate-project

### Local extracts
- `web_war_glossary_ru.txt` — 83 raw lines/terms
- `web_hate_speech.txt` — 67 raw lines/terms
- `vsecoder_make_multilabel.py` — 56 raw lines/terms
- `hurtlex_ru_12.tsv` — 211 raw lines/terms

**Quality notes:** Этнические слаги (хохол, ватник, колорад) — высокий FP в нейтральном контексте; только hate_speech секция. OPORA — датасет риторики, не wordlist.

---

## 4. Drones / rockets / explosions

**Токенов в секции:** 71

### WebSearch queries
- `бпла дрон террор взрывчатка сленг русский`
- `теракт терминология русский словарь модерация`
- `war glossary fpv камикадзе шахед`
- `rub-in.ru угроза бпла терроризм дронов`
- `kuban24 птичник бпла сво`

### Source URLs
- https://praguesupport.com/wp-content/uploads/2025/09/war-glossary_full-version_for-printing_13092025.pdf
- https://www.rub-in.ru/news/novye-realnosti-terrorizm-ugrozy-bpla-i-nashi-deti-pora-reshat/
- https://kuban24.tv/item/tonkosti-upravleniya-dronami-na-svo-kto-takoj-ptichnik-i-chem-razlichayutsya-bpla
- https://ukodeksrf.ru/ch-2/rzd-9/gl-24/st-205-uk-rf

### Local extracts
- `web_weapons_drones.txt` — 73 raw lines/terms
- `web_war_glossary_ru.txt` — 83 raw lines/terms
- `krugozor_stopwords.php` — 37 raw lines/terms

**Quality notes:** War glossary даёт 80+ drone/bomb tokens. ContentShield RU (404 на raw) — не извлечён. FP: дрон-доставка, космическая ракета.

---

## 5. Protests / meetings

**Токенов в секции:** 20

### WebSearch queries
- `митинг протест запрещённые слова несанкционированный митинг`
- `пикетирование модерация стоп слова россия`
- `54-ФЗ публичное мероприятие уведомление`
- `20.2 КоАП митинг демонстрация`
- `istories vepr protest moods monitoring`

### Source URLs
- https://www.consultant.ru/document/cons_doc_LAW_48103/
- https://www.consultant.ru/document/cons_doc_LAW_34661/c77bf52af28dfd8f9de192b9faf0999c023256d2/
- https://istories.media/en/stories/2023/02/08/inside-the-censorship-machine/
- https://habr.com/ru/articles/384021/

### Local extracts
- `web_protests_legal.txt` — 20 raw lines/terms
- `web_dfrlab_rkn_tags.txt` — 8 raw lines/terms
- `kugimiya_banlist.yaml` — 16 raw lines/terms

**Quality notes:** Закон не публикует banned words — только legal terms + incitement phrases. RKN мониторит «призывы к протесту» как тег.

---

## 6. Police / siloviki

**Токенов в секции:** 37

### WebSearch queries
- `мусора сленг полиция омон росгвардия жаргон`
- `силовики оскорбления словарь россия`
- `cyberleninka оскорбление представителей власти мусор мент`
- `politicwar.ru силовики политсленг`
- `molomo.ru мусор сленг`

### Source URLs
- https://www.eg.ru/culture/500105-pochemu-policeyskih-nazyvayut-musorami-i-legavymi/
- https://cyberleninka.ru/article/n/ob-uchastii-lingvista-v-sudebnyh-zasedaniyah-po-delam-ob-oskorblenii-predstaviteley-vlasti
- http://www.politicwar.ru/politika/266249.html
- https://www.molomo.ru/sleng-m/musor

### Local extracts
- `web_police_slang.txt` — 39 raw lines/terms
- `kugimiya_banlist.yaml` — 16 raw lines/terms

**Quality notes:** «мусор» — омоним с waste management (context_required). ACAB/околофутбол — protest subculture.

---

## 7. Political figures / titles

**Токенов в секции:** 44

### WebSearch queries
- `путин зеленский модерация блок оскорбления словарь`
- `istories oculus insult president photoshop dictionary`
- `unian путин зеленский риторика`
- `videocensor api insults extremism categories`
- `kugimiya banlist путин зеленск`

### Source URLs
- https://istories.media/en/stories/2023/02/08/inside-the-censorship-machine/
- https://www.unian.net/world/vladimir-putin-rezko-izmenil-ton-upominaya-zelenskogo-13377765.html
- https://videocensor.ru/developers/docs
- https://citizenlab.ca/research/an-analysis-of-in-platform-censorship-on-russias-vkontakte/

### Local extracts
- `web_political_figures.txt` — 43 raw lines/terms
- `web_dfrlab_rkn_tags.txt` — 8 raw lines/terms
- `kugimiya_banlist.yaml` — 16 raw lines/terms

**Quality notes:** RKN Oculus dictionary: insults comparing Putin to Hitler/dictator/traitor. FP: «президент компании».

---

## 8. Racism / hate speech RU

**Токенов в секции:** 215

### WebSearch queries
- `hate speech русский словарь github этнические оскорбления`
- `xenophobia lexicon russian RuEthnoHate dataset`
- `hurtlex PS category russian`
- `vsecoder IDENTITY rules github`
- `habr vk токсичность protected identities`

### Source URLs
- https://github.com/hse-scila/ethnohate-project
- https://github.com/valeriobasile/hurtlex/tree/master/lexica/RU/1.2
- https://github.com/vsecoder/ru-toxic-messages-classification
- https://habr.com/ru/companies/vk/articles/546186/
- https://scila.hse.ru/ethnohate

### Local extracts
- `web_hate_speech.txt` — 67 raw lines/terms
- `hurtlex_ru_12.tsv` — 211 raw lines/terms
- `vsecoder_make_multilabel.py` — 56 raw lines/terms

**Quality notes:** RuEthnoHate — annotated texts, не static list. Hurtlex PS + vsecoder IDENTITY дали основную массу. bars38/ContentShield — 404 при fetch.

---

## 9. Islam / religious extremism

**Токенов в секции:** 88

### WebSearch queries
- `исламизм экстремизм термины русский словарь`
- `mediascope исламизм ваххабизм экстремизм синонимы`
- `wikipedia исламизм политический ислам`
- `security.urfu ваххабиты джихадист`
- `bigenc.ru исламское государство игил`

### Source URLs
- http://www.mediascope.ru/node/2081
- https://ru.wikipedia.org/wiki/Исламизм
- https://security.urfu.ru/ru/protivodeistvie-ehkstremizmu-i-terrorizmu/osnovnye-terminy-i-opredelenija/
- https://bigenc.ru/c/islamskoe-gosudarstvo-bf9101

### Local extracts
- `web_islamism_terms.txt` — 37 raw lines/terms
- `web_terrorism_urfu.txt` — 50 raw lines/terms
- `krugozor_stopwords.php` — 37 raw lines/terms

**Quality notes:** Религия (ислам, мусульманин, коран) намеренно исключена. Mediascope: исламизм ≠ экстремизм синонимы.

---

## 10. Torture / violence

**Токенов в секции:** 96

### WebSearch queries
- `пытки термины насилие словарь угроз русский`
- `hurtlex RE category russian`
- `vsecoder THREAT rules github`
- `ukodeksrf статья 205 террористический акт`
- `law.niv.ru пытка определение`

### Source URLs
- https://github.com/valeriobasile/hurtlex/tree/master/lexica/RU/1.2
- https://github.com/vsecoder/ru-toxic-messages-classification
- https://law.niv.ru/doc/dictionary/large-legal/articles/839/pytka.htm
- https://ukodeksrf.ru/ch-2/rzd-9/gl-24/st-205-uk-rf

### Local extracts
- `web_torture_violence.txt` — 63 raw lines/terms
- `hurtlex_ru_12.tsv` — 211 raw lines/terms
- `vsecoder_make_multilabel.py` — 56 raw lines/terms

**Quality notes:** Hurtlex RE много юридических FP (Пират, шалунья) — отфильтровано is_valid_token. vsecoder threat directional требует 2-е лицо.

---

## Tokens vs regex patterns

**Токены** (`candidates_violence.txt`) — точное совпадение слов/лемм для wordlist merge.
**Regex** (`candidates_violence_regex.txt`) — фрагменты из vsecoder THREAT/IDENTITY
с классами символов (`[аеуо]`, `?`, `\s`) — только для phrase-engine, не в stop-list.
Примеры: `ватн[аеуо][^_]` (варианты «ватник»), `чурк[аиое]` (склонения),
`оторв[уе]м?\s` (угроза «оторвём»). Артефакты вроде `деhumanизация` и bidi-`пытка`
отфильтрованы; чистый токен `пытка` остаётся в torture-секции.

## Additional cross-topic sources

| Source | URL | License | Est. terms | Extracted |
|--------|-----|---------|------------|-----------|
| hurtlex RU 1.2 | https://github.com/valeriobasile/hurtlex | Academic | ~4679 | 211 RE+PS |
| vsecoder THREAT/IDENTITY | https://github.com/vsecoder/ru-toxic-messages-classification | MIT | ~40 patterns | 56 |
| Krugozor extremism | vendored PHP | No LICENSE | ~40 | 37 |
| kugimiya banlist | vendored YAML | — | ~200 roots | 16 |
| ContentShield RU | https://github.com/ZachHandley/ContentShield | Check repo | ~215 | **FAILED 404** |
| bars38 RU ban | https://github.com/bars38/Russian_ban_words | — | ~1316 | **FAILED 404** |
| LDNOOBW V2 RU | https://github.com/LDNOOBWV2/ | Open | 4948 | skipped (profanity dup) |
| TextDetox lexicon | HuggingFace | openrail++ | 140k | skipped (not violence) |
| RuEthnoHate | HSE GitHub | Research | 5.5k texts | skipped (dataset not list) |
| Citizen Lab VK | citizenlab.ca 2023/2025 | Research | LGBTIQ keywords | not violence-specific |

## Honest gaps

- Нет единого open-source **Russian violence wordlist** уровня profanity.
- ContentShield/bars38 raw fetch failed (repo paths changed).
- RKN/MinJust публикуют **материалы/теги**, не готовые stop-lists.
- War glossary сильно UA/RU mixed — курация на RU-only tokens.
