"""大陸／非台灣用語清單（check_batch.py 與 check_extra.py 共用，避免兩份清單不一致）。"""
MAINLAND = ("軟件 視頻 質量 信息 網絡 程序 出租車 土豆 鼠標 屏幕 內存 公交車 酸奶 頭盔 默認 激活 文檔 硬盤 "
            "服務器 調試 登錄 短信 校服 堵塞 項目 地鐵 打印 激光 優化 數據庫 老師傅").split()
# 在特定情境下台灣也會用，附註提醒人工確認。值是附註文字。
CONTEXT_NOTES = {
    '質量': 'mass 在物理上台灣也用「質量」；指品質時才是大陸用語',
    '程序': 'program 指程式時才是大陸用語；「手術程序」等正式用法可保留',
    '地鐵': '只在指倫敦等國外地鐵時使用；台北用「捷運」',
}
# 這些詞若該字的 topics 含「科學」，視為物理／科學用法，不警告。
SCIENCE_OK = {'質量'}


def hits(texts, topics=()):
    """回傳 [(term, note)]。texts 是要掃描的字串列表；同一詞只回報一次。"""
    blob = '\n'.join(t for t in texts if t)
    out = []
    for m in MAINLAND:
        if m in blob:
            if m in SCIENCE_OK and '科學' in (topics or ()):
                continue
            out.append((m, CONTEXT_NOTES.get(m, '')))
    return out
