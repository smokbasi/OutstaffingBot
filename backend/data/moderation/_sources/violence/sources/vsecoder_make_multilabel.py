"""
Weak-supervision разметка labeled.csv → labeled_multi.csv с категориями:
- profanity       : есть мат
- insult          : направленное оскорбление человеку (insult-word + 2-е лицо ИЛИ есть угроза)
- identity_attack : атака на группу (нац/гендер/идентичность)
- threat          : угроза вреда
- is_directed     : токсичность направлена на адресата (2-е лицо)
- severity        : 0 (нет) / 1 (мат) / 2 (insult|identity) / 3 (threat)

Применяется та же нормализация, что и в обучающем пайплайне, поэтому
обфускация типа "д*бил" / "пuдор" ловится.

Это noisy labels — годны как старт для multi-label обучения и как
референс для последующей чистки/LLM-разметки.
"""
import re
import pandas as pd

HOMOGLYPHS = str.maketrans({
    'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с',
    'x': 'х', 'y': 'у', 'k': 'к', 'h': 'н', 'm': 'м',
    'b': 'в', 't': 'т', 'r': 'г', 'n': 'п', 'u': 'и',
    '0': 'о', '3': 'з', '4': 'ч', '6': 'б', '7': 'т',
})
REPEAT_RE = re.compile(r'(.)\1{2,}')
NON_TEXT_RE = re.compile(r'[^a-zа-яё\s-]')
WS_RE = re.compile(r'\s+')


def normalize(text: str) -> str:
    text = str(text).lower().translate(HOMOGLYPHS)
    text = REPEAT_RE.sub(r'\1\1', text)
    text = NON_TEXT_RE.sub(' ', text)
    return WS_RE.sub(' ', text).strip()


# Маты (корни/префиксы). Используем \b, нормализация уже выровняла регистр и обфускацию.
PROFANITY = [
    r'\bхуй', r'\bхуё', r'\bхуе[вгдтнс]', r'\bхуя\b',
    r'\bхуесос', r'\bхуёсос',
    r'\bохуе', r'\bнахуй', r'\bпохуй', r'\bдохуя',
    r'\bбля\b', r'\bбляд',  # бляд / блядь / бляди / блядей / блядский / блядство
    r'\bпизд', r'\bпизж',
    r'\bпиздобол', r'\bпиздабол',
    r'\bебан', r'\bёбан', r'\bебат', r'\bёбат', r'\bебут', r'\bёбут',
    r'\bебал', r'\bёбал', r'\bебуч', r'\bёбуч', r'\bебись',
    r'\bёб\b', r'\bеб\b', r'\bебля', r'\bёбля',
    r'\bуёб', r'\bуеб', r'\bзаеб', r'\bзаёб', r'\bотъеб', r'\bотъёб',
    r'\bподъеб', r'\bподъёб', r'\bвыеб', r'\bвыёб',
    r'\bсук[аиу]\b', r'\bсучк[аи]', r'\bсучонок',
    r'\bхер[аеу]\b', r'\bхерн', r'\bхрен[аоеу]\b', r'\bнихер',
    r'\bговн', r'\bдерьм',
    r'\bмудак', r'\bмудил', r'\bмудач',
    r'\bгондон',
    r'\bпиздец', r'\bохуен', r'\bохуит',
    r'\bдрочи', r'\bдроч[аеуи]',
    r'\bшлюх',  # шлюха / шлюхи / шлюхой
]

# Insult-слова (без фильтра направленности — фильтр ниже)
INSULT_WORDS = [
    r'\bдебил', r'\bдибил',
    r'\bидиот', r'\bкретин', r'\bимбецил',
    r'\bтупой\b', r'\bтупая\b', r'\bтупое\b', r'\bтупые\b', r'\bтуп(?:ого|ому|ым|ом)\b',
    r'\bтупиц', r'\bтупорыл', r'\bтупоголов', r'\bтупиц',
    r'\bлошара', r'\bлох\b', r'\bлохи\b', r'\bлоху\b',
    r'\bдурак\b', r'\bдура\b', r'\bдурач', r'\bдуры\b',
    r'\bпридурок', r'\bпридурк',
    r'\bчмо\b', r'\bчмош',
    r'\bублюд',
    r'\bкозел\b', r'\bкозёл\b', r'\bкозлы\b', r'\bкозла\b', r'\bкозлу\b',
    r'\bбаран\b', r'\bбараны\b',
    r'\bхуйло', r'\bхуесос', r'\bхуёсос',
    r'\bничтожн', r'\bжалк',
    r'\bмразь', r'\bмразот',
    r'\bхамл',
    r'\bдолбоё', r'\bдолбое', r'\bдолбаё', r'\bдолбае',
    r'\bурод\b', r'\bуроды\b', r'\bуродц',
    r'\bподонок', r'\bподонк',
    r'\bсволоч',
    r'\bимпотент',
    r'\bпетух\b', r'\bпетухи\b',  # тюремный жаргон
]

# Атаки на группы. Будь осторожен: жид/жидк фильтруем строгим словом.
IDENTITY = [
    r'\bхохол\b', r'\bхохлы\b', r'\bхохла\b', r'\bхохлам\b', r'\bхохлов\b',
    r'\bкацап', r'\bмоскал',
    r'\bчурк[аиое]\b', r'\bчуркест', r'\bчурбан\b',
    r'\bчёрнож', r'\bчернож',
    r'\bчерномаз', r'\bчёрномаз',
    r'\bузкоглаз', r'\bраскос',
    r'\bжид\b', r'\bжиды\b', r'\bжидов', r'\bжиде\b', r'\bжидам\b', r'\bжидами\b',
    r'\bпидорас', r'\bпидрюга',
    r'\bниггер', r'\bнигер\b',
    r'\bхач\b', r'\bхачи\b', r'\bхачик',
    r'\bбандеров',
    r'\bукропы\b',
    r'\bватник', r'\bватн[аеуо][^_]', r'\bколорад\b',
    r'\bпиндос',
    r'\bпедик', r'\bпидик', r'\bпидор', r'\bпедераст',
    r'\bкаклы\b',
    r'\bдаун\b', r'\bдауны\b',  # часто в значении ID-attack
]

# Угрозы-императивы (всегда направлены — это сама форма)
THREAT_IMPERATIVE = [
    r'\bсдохн', r'\bудавись', r'\bповесись', r'\bудавитьс',
]

# Угрозы-действия (нужен 2-е лицо или прямой адресат, иначе нарратив/самоадрес)
THREAT_DIRECTIONAL = [
    r'\bубью\b', r'\bубил\s+бы', r'\bпришью\b', r'\bпришил\s+бы',
    r'\bпридушу', r'\bпорешу', r'\bгрохну\b',
    r'\bзарежу', r'\bзастрелю', r'\bрасстрел',
    r'\bтрахну\b', r'\bизнасилую',
    r'\bнайду\s+тебя', r'\bнайду\s+вас',
    r'\bхана\s+тебе', r'\bкрышка\s+тебе', r'\bконец\s+тебе',
    r'\bоторв[уё]м?\s', r'\bпроломлю',
    r'\bголову\s+оторв', r'\bбашку\s+оторв',
    r'\bвпиздячу', r'\bвпизжу',
]

# Агрессивные императивы (для is_directed: они и без местоимения направлены)
IMPERATIVES_DIRECTED = [
    r'\bсдохн', r'\bудавись', r'\bповесись',
    r'\bпошёл\s+(на|в)', r'\bпошел\s+(на|в)',
    r'\bзаткнись', r'\bзаткнитесь',
    r'\bсвали\b', r'\bвали\s+(отсюда|нахуй|на\s+хуй)',
    r'\bотъебись', r'\bотъебитесь', r'\bотвали\b',
    r'\bхуй\s+тебе', r'\bхуй\s+вам',
    r'\bна\s+хуй\b', r'\bнахуй\b',
    r'\bхватит\s+(пиздеть|нести|гнать)',
]

SECOND_PERSON = re.compile(
    r'\b(ты|тебя|тебе|тобой|тобою|твой|твоя|твоё|твои|тво(?:его|ему|ей|их|им|ими|ём|ем)'
    r'|вы|вам|вас|вами|ваш|ваша|ваше|ваши|ваш(?:его|ему|ей|их|им|ими))\b'
)


def any_match(patterns, text):
    return any(re.search(p, text) for p in patterns)


def label(text: str):
    norm = normalize(text)

    profanity = any_match(PROFANITY, norm)
    insult_word = any_match(INSULT_WORDS, norm)
    identity = any_match(IDENTITY, norm)

    second_person = bool(SECOND_PERSON.search(norm))
    imperative_directed = any_match(IMPERATIVES_DIRECTED, norm)
    directed = second_person or imperative_directed

    # threat: либо императив-угроза (всегда срабатывает), либо угроза-действие + 2-е лицо
    threat_imp = any_match(THREAT_IMPERATIVE, norm)
    threat_dir = any_match(THREAT_DIRECTIONAL, norm) and second_person
    threat = threat_imp or threat_dir

    insult = (insult_word and directed) or threat

    if threat:
        severity = 3
    elif insult or identity:
        severity = 2
    elif profanity:
        severity = 1
    else:
        severity = 0

    return int(profanity), int(insult), int(identity), int(threat), int(directed), severity


def main():
    df = pd.read_csv('labeled.csv')
    df['toxic'] = df['toxic'].astype(int)

    rows = df['comment'].map(label).tolist()
    df['profanity']       = [r[0] for r in rows]
    df['insult']          = [r[1] for r in rows]
    df['identity_attack'] = [r[2] for r in rows]
    df['threat']          = [r[3] for r in rows]
    df['is_directed']     = [r[4] for r in rows]
    df['severity']        = [r[5] for r in rows]

    df.to_csv('labeled_multi.csv', index=False, encoding='utf-8')

    print(f'rows total: {len(df)}')
    print(f'\n=== Распределение бинарных категорий ===')
    for col in ['profanity', 'insult', 'identity_attack', 'threat', 'is_directed']:
        n = df[col].sum()
        print(f'  {col:18s}: {n:5d}  ({n/len(df):.2%})')

    print(f'\n=== severity ===')
    print(df['severity'].value_counts().sort_index().to_string())

    any_rule = (df[['profanity','insult','identity_attack','threat']].max(axis=1) == 1)
    tp = ((df['toxic']==1) & any_rule).sum()
    fn = ((df['toxic']==1) & ~any_rule).sum()
    fp = ((df['toxic']==0) & any_rule).sum()
    tn = ((df['toxic']==0) & ~any_rule).sum()
    n_tox = (df['toxic']==1).sum()
    n_neu = (df['toxic']==0).sum()
    print(f'\n=== Согласие правил с оригинальной меткой toxic ===')
    print(f'  toxic=1, правило сработало:    {tp:5d} / {n_tox} ({tp/n_tox:.2%})  (recall правил)')
    print(f'  toxic=1, правило не сработало: {fn:5d} / {n_tox} ({fn/n_tox:.2%})')
    print(f'  toxic=0, правило не сработало: {tn:5d} / {n_neu} ({tn/n_neu:.2%})  (specificity)')
    print(f'  toxic=0, правило сработало:    {fp:5d} / {n_neu} ({fp/n_neu:.2%})  (FP правил)')

    print(f'\nsaved -> labeled_multi.csv')


if __name__ == '__main__':
    main()
