"""單字資料的共用常數（19 項 topics、9 種詞性、16 種 issue 類型、path 格式）。"""
import re

TOPICS = "日常生活、飲食、家庭與人際、學校與學習、工作與商業、金融與會計、健康與身體、情緒與性格、動物、植物與自然、天氣與環境、科技與網路、交通與旅行、運動與休閒、藝術與文化、社會與法律、科學、歷史與地理、抽象概念與其他".split('、')
POS = {'n.', 'v.', 'adj.', 'adv.', 'prep.', 'conj.', 'pron.', 'det.', 'interj.'}
ISSUE_TYPES = {'pos_wrong', 'pos_missing', 'zh_wrong', 'zh_missing', 'zh_unclear', 'example_missing_word', 'example_unnatural',
               'example_style', 'example_similar', 'translation_bad', 'mainland_term', 'simplified_char', 'topics_bad',
               'emoji_bad', 'image_query_bad', 'format_bad'}
SEVERITIES = {'high', 'medium', 'low', 'uncertain'}
PATH_RE = re.compile(r'^(senses\[\d+\]\.(pos|zh)|senses\[\d+\]\.examples\[\d+\]\.(en|zh)|topics|emoji|image_query)$')


def walk(entry, path):
    """沿 path 走進單字資料，回傳 (parent, last_key)；找不到拋 KeyError／IndexError。"""
    keys = [(m.group(1) if m.group(1) else int(m.group(2))) for m in re.finditer(r'([A-Za-z_]+)|\[(\d+)\]', path)]
    o = entry
    for k in keys[:-1]:
        o = o[k]
    _ = o[keys[-1]]
    return o, keys[-1]


def flatten(entry):
    """把一筆單字資料攤平成 {path: value}。topics 整個陣列算一個值。"""
    out = {}
    def rec(o, pre):
        if isinstance(o, dict):
            for k, v in o.items(): rec(v, f'{pre}.{k}' if pre else k)
        elif isinstance(o, list) and pre != 'topics':
            for i, v in enumerate(o): rec(v, f'{pre}[{i}]')
        else:
            out[pre] = o
    rec(entry, '')
    out.pop('word', None)
    return out
