"""check_batch.py 與 check_extra.py 共用的字形工具（只用標準函式庫）。"""
import re

_TOKEN = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)*")


def inflect(w):
    """目標字的常見變化形（與舊 check_extra.forms 相同）。"""
    w = w.lower()
    s = {w, w + 's', w + 'es', w + 'ed', w + 'd', w + 'ing', w + "'s"}
    if w.endswith('e'):
        s |= {w[:-1] + 'ing', w + 'r', w + 'st'}
    if w.endswith('y'):
        s |= {w[:-1] + 'ies', w[:-1] + 'ied', w[:-1] + 'ier', w[:-1] + 'iest'}
    if len(w) > 2:
        s |= {w + w[-1] + 'ed', w + w[-1] + 'ing', w + w[-1] + 'er', w + w[-1] + 'est'}
    return s


def _plurals(seg):
    out = {seg + 's', seg + 'es'}
    if seg.endswith('y') and len(seg) > 1:
        out.add(seg[:-1] + 'ies')
    return out


def forms(w):
    """變化形集合。連字號詞額外加入「任一段變複數」（runners-up、passers-by、sons-in-law）。"""
    w = w.lower()
    s = inflect(w)
    if '-' in w:
        segs = w.split('-')
        for i, seg in enumerate(segs):
            for p in _plurals(seg):
                s.add('-'.join(segs[:i] + [p] + segs[i + 1:]))
    return s


def tokens(text):
    """小寫、彎引號轉直引號後切成詞；連字號與撇號詞保持完整（check-in、o'clock）。"""
    return _TOKEN.findall(text.lower().replace('’', "'"))


def contains_exact(text, w):
    """目標字（含變化形）是否以「完整單獨的詞」出現。連字號詞不接受只有前綴相同的詞。"""
    fs = forms(w)
    return any(t in fs for t in tokens(text))


# 字母名稱以母音音開頭 → 用 an（X-ray、M-shaped、S-curve、F-word）；其餘用 a（U-turn、T-shirt、B-side）
AN_LETTERS = set('aefhilmnorsx')


# ---- 冠詞 a／an 的發音判斷 ----
AN_EXC_AN = {'hour', 'hourly', 'honest', 'honestly', 'honor', 'honour', 'honorable', 'heir', 'heiress', 'herb'}
AN_EXC_A = {'one', 'once', 'ubiquitous', 'ufo', 'unanimous', 'unanimously', 'unicorn', 'unique', 'uniquely',
            'use', 'used', 'useful', 'useless', 'user', 'users', 'usual', 'usually', 'utensil', 'utensils',
            'utility', 'utilities', 'utopia', 'euro', 'euros', 'eucalyptus', 'european', 'eu', 'ewe', 'eulogy'}


def starts_with_vowel_sound(word):
    """英文單字（非縮寫）開頭是否為母音發音，供 a／an 判斷。"""
    w = word.lower()
    if w in AN_EXC_AN:
        return True
    if w in AN_EXC_A:
        return False
    if re.match(r'^uni(?!n|m)', w):   # uni-（唸 /juː/）：union、unit、universe、uniform；unin-/unim-（唸 /ʌn/）除外
        return False
    if re.match(r'^(use|usu|uti)', w):
        return False
    return w[:1] in 'aeiou'


def article_ok(art, nxt, hyphen_after=False, original=None):
    """回傳 True/False：art（a／an）搭配 nxt 是否正確。original 是原文大小寫，用來辨識縮寫（MBA、FBI）。"""
    art = art.lower()
    if len(nxt) == 1 and hyphen_after:                 # X-ray、e-mail、U-turn：看字母名稱
        vow = nxt.lower() in AN_LETTERS
    elif original and len(original) >= 2 and original.isupper():   # 全大寫縮寫：看第一個字母的名稱
        vow = original[0].lower() in AN_LETTERS
    else:
        vow = starts_with_vowel_sound(nxt)
    return (art == 'an') == vow
