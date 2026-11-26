# 《糟糕島物語》內容建置：地圖 + 劇情腳本 → game.json（含自動驗證）
# 用法：python build_content.py ../KomicaRPG/wwwroot/data/game.json
import json
import random
import sys
from collections import deque

from content_db import ACTORS, SKILLS, ITEMS, ENEMIES, TROOPS, SHOPS, QUESTS, STATUSES, ELEMENTS, GAUGE, COMBOS
from content_extra import BOARDS, BOARD_PLACES, SKITS, TRAVEL, NO_TRAVEL_MAPS, CH

OUT = sys.argv[1] if len(sys.argv) > 1 else "game.json"

TILES = {
    ".": ["grass", 1], ",": ["flower", 1], "=": ["path", 1], "T": ["tree", 0], "~": ["water", 0],
    "^": ["roof", 0], "v": ["roof_blue", 0], "H": ["wall", 0], "O": ["window", 0], "D": ["door", 0],
    "P": ["poster", 0], "S": ["stone", 0], "_": ["floor", 1], "X": ["towerdoor", 1], "E": ["stairs", 1],
    "s": ["sand", 1], "b": ["bridge", 1], "w": ["wreck", 0], "R": ["rock", 0], "f": ["fence", 0],
    "K": ["tree_dark", 0], "m": ["mist", 1], "k": ["dock", 1], "B": ["barrel", 0], "c": ["carpet", 1],
    "M": ["marble", 1], "F": ["frame", 0], "Q": ["frame404", 0], "I": ["pillar", 0], "G": ["metal", 1],
    "W": ["metal_wall", 0], "N": ["banner", 0], "Z": ["circuit", 1], "V": ["void", 0], "Y": ["datawall", 0],
    "C": ["core", 1], "L": ["lava", 0], "J": ["rock_sand", 0], "h": ["shelf", 0], "u": ["counter", 0],
}


# ---------------------------------------------------------------- 地圖工具
class Canvas:
    def __init__(s, w, h, fill="."):
        s.W, s.H = w, h
        s.g = [[fill] * w for _ in range(h)]

    def set(s, x, y, c):
        s.g[y][x] = c

    def get(s, x, y):
        return s.g[y][x]

    def rect(s, x0, y0, x1, y1, c):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                s.g[y][x] = c

    def border(s, c):
        s.rect(0, 0, s.W - 1, 0, c)
        s.rect(0, s.H - 1, s.W - 1, s.H - 1, c)
        s.rect(0, 0, 0, s.H - 1, c)
        s.rect(s.W - 1, 0, s.W - 1, s.H - 1, c)

    def h(s, x0, x1, y, c="="):
        s.rect(x0, y, x1, y, c)

    def v(s, x, y0, y1, c="="):
        s.rect(x, y0, x, y1, c)

    def house(s, x, y, w, h=3, roof="^", door=None, win=()):
        s.rect(x, y, x + w - 1, y, roof)
        s.rect(x, y + 1, x + w - 1, y + h - 1, "H")
        for o in win:
            s.set(x + o, y + 1, "O")
        if door is not None:
            s.set(x + door, y + h - 1, "D")

    def carve(s, pts, c):
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            s.rect(x0, y0, x1, y1, c)

    def dots(s, c, pts, only="."):
        for x, y in pts:
            if s.g[y][x] in only:
                s.g[y][x] = c

    def scatter(s, c, n, seed, box=None, only=".", avoid=()):
        r = random.Random(seed)
        x0, y0, x1, y1 = box or (1, 1, s.W - 2, s.H - 2)
        placed = tries = 0
        while placed < n and tries < n * 80:
            tries += 1
            x, y = r.randint(x0, x1), r.randint(y0, y1)
            if s.g[y][x] in only and (x, y) not in avoid:
                s.g[y][x] = c
                placed += 1

    def rows(s):
        return ["".join(r) for r in s.g]


# ---------------------------------------------------------------- 腳本工具
def say(sp, *t): return ["say", sp] + list(t)
def nar(*t): return ["say", ""] + list(t)
def IF(c, a, b=None): return ["if", c, a] + ([b] if b is not None else [])
def F(f): return ["flag", f]
def give(i, n=1): return ["give", i, n]
def take(i, n=1): return ["take", i, n]
def gold(n): return ["gold", n]
def goal(t): return ["goal", t]
def quest(q, st): return ["quest", q, st]
def karma(n): return ["karma", n]
def battle(t, **o): return ["battle", t, o]
def choice(*opts): return ["choice"] + [[label, cmds] for label, cmds in opts]
def join(a): return ["join", a]
def warp(m, x, y, d): return ["warp", m, x, y, d]
def shop(s): return ["shop", s]
def inn(p): return ["inn", p]
def ending(e): return ["ending", e]


CRYSTAL = [["heal"], nar("精華結晶溫柔地發著光……全隊的 HP 與 MP 都回復了。"), ["save"]]


def ent(id, sprite, x, y, script, show=None, mark=None):
    """mark：條件成立時，人物頭上會出現跳動的「！」，提示玩家現在該找他說話。"""
    d = {"id": id, "sprite": sprite, "x": x, "y": y, "script": script}
    if show:
        d["show"] = show
    if mark:
        d["mark"] = mark
    return d


def chest(id, x, y, item=None, n=1, gold_=None, show=None):
    d = {"id": id, "sprite": "chest", "x": x, "y": y, "chest": {"item": item, "n": n} if item else {"gold": gold_}}
    if show:
        d["show"] = show
    return d


def crystal(id, x, y):
    return ent(id, "crystal", x, y, CRYSTAL)


def sign(id, x, y, *text):
    return ent(id, "sign", x, y, [nar(*text)])


# =====================================================================
# 島上的武將與知名人物
# 以島上流傳的梗為靈感的虛構角色：只用公開的口頭禪與行為梗，劇情與台詞皆為創作。
# =====================================================================

# ---- 生日哥（綜合村）：被拿來洗版的生日照，最後變成真正的祝福 ----
def bday_party():
    return [
        nar("生日哥把四張祝福卡排在桌上。", "綜合村的島民，一個、兩個……慢慢地聚了過來。"),
        take("card", 9),  # 多收到的祝福卡也一起交給他
        say("綜合伯", "生日快樂。今天的泡麵加蛋，算我的。"),
        IF("flag:untag1", [say("肥宅大叔", "生日快樂！肥宅是一種態度！")],
           [nar("身上還貼著名牌的肥宅大叔說不出話，只能用力地揮手。")]),
        IF("flag:untag2", [say("www 哥", "生日快樂wwwwwwwwww")],
           [nar("www 哥張了張嘴，最後用手比了一個「w」。")]),
        say("新手", "生日快樂！……祝福乙！"),
        say("生日哥", "……", "今天……真的是我生日ㄛ。"),
        nar("那天晚上，綜合版上多了一個串。", "標題只有四個字：「生日快樂」。", "回應一路推到了第十頁。"),
        say("生日哥", "這頂派對帽給你。", "戴上它，就不會一個人在角落潛水了。"),
        give("acc_party"), give("cake", 2), karma(1), quest("bday", "done"), F("bdayDone"),
    ]


bday_script = [
    IF("flag:bdayDone", [
        IF("flag:forgaveSnow", [
            say("生日哥", "我聽說雪見的事了。", "我也被匿名的人傷害過。可是每天跟我說生日快樂的，也是匿名的人。",
                "……希望她也能收到很多很多的祝福。"),
        ], [
            say("生日哥", "今天我生日ㄛ！", "……開玩笑的。不過那天的派對，我會記一輩子。"),
        ]),
    ], [IF("flag:q_bday", [
        IF("item:card>=4", bday_party(), [
            say("生日哥", "祝福卡現在有 {item:card} 張，要 4 張才夠。",
                "新番鎮的智障神和放矢哥、到處擺攤的照燒貓、釣魚港的西瓜哥、美術館的塗鴉廚……",
                "他們都是島上的『名人』。拜託你去問問看。"),
        ]),
    ], [IF("flag:raidDone", [
        say("生日哥", "……無名氏，你也被名牌兵盯上了嗎？", "他們說『生日哥』這個名號太有名，要第一個登記。",
            "可是……那根本不是我的名字啊。"),
        say("生日哥", "跟你說個祕密。", "以前有人把我的自拍照拿到綜合版洗版。每一頁都是我，配上一句『今天我生日ㄛ』。",
            "那時候，我好想就這樣消失。"),
        say("生日哥", "可是後來……每天都有人跟我說生日快樂。", "不認識的人。沒有名字的人。一天、兩天、一年……到現在都還有。"),
        say("無名氏", "……"),
        say("生日哥", "所以我想，至少辦一次真正的生日派對。", "可以幫我收集祝福卡嗎？請島上的名人寫一句話就好。4 張就夠了。"),
        F("q_bday"), quest("bday", "open"),
    ], [
        say("生日哥", "今天我生日ㄛ！"),
        choice(("生日快樂！", [
            say("生日哥", "謝謝！明天也是我生日ㄛ！"),
            IF("!flag:bdayCake", [say("生日哥", "這個給你，生日蛋糕！反正每天都有。"), give("cake"), F("bdayCake")]),
        ]), ("無視", [say("生日哥", "……嗯。習慣了。")])),
    ])])]),
]

# ---- 照燒貓：跟著熱門串到處擺攤的上古武將 ----
def teri_script(*lore):
    return [
        IF("!flag:metTeri", [
            say("照燒貓", "喲，新面孔……不對，是無名氏啊。", "我是照燒貓。上古時代就在島上擺攤了，現在是流浪的照燒屋。",
                "以前綜合版流行『武將』，我也算是其中一個吧。", "被記住，有時候是好事，有時候不是。"),
            F("metTeri"),
        ]),
        say("照燒貓", *lore),
        IF("!flag:teriDone", [IF("item:sauce>=3", [
            say("照燒貓", "這、這是……沉船灘的海鹽、捏他之森的香菇、惡搞谷的辣椒！", "祕傳醬汁終於可以重現了！"),
            take("sauce", 3), give("acc_apron"), quest("teriyaki", "done"), F("teriDone"),
            say("照燒貓", "這件圍裙送你。穿著它，炎上也燒不到你。", "以後我的攤子也賣『照燒全家餐』了。"),
        ], [IF("flag:q_teri", [
            say("照燒貓", "祕方材料找到 {item:sauce} 個了。沉船灘、捏他之森、惡搞谷的寶箱裡，總共 3 個。"),
        ], [
            say("照燒貓", "對了，我的祕傳醬汁少了三樣材料。", "年輕時我把它們藏在沉船灘、捏他之森、惡搞谷的寶箱裡……現在腰不好，走不動了。",
                "幫我找回來的話，有謝禮喔。"),
            F("q_teri"), quest("teriyaki", "open"),
        ])])]),
        IF("flag:q_bday & !flag:bdayDone & !flag:bless_teri", [
            say("照燒貓", "生日哥的祝福卡？……那小子還在每天過生日啊。", "寫好了。『生日快樂，照燒雞腿請你吃。』"),
            give("card"), F("bless_teri"),
        ]),
        choice(("看看照燒料理", [IF("flag:teriDone", [shop("teriyaki2")], [shop("teriyaki")])]),
               ("不用了", [say("照燒貓", "慢走。醬汁要慢慢燒才香，人也是。")])),
    ]


# ---- 智障神（新番鎮）：每天洗開箱文的「開箱之神」 ----
zz_bless = IF("flag:q_bday & !flag:bdayDone & !flag:bless_zz", [
    say("智障神", "生日哥？那個天天生日的？", "……以前我還在他的串底下嗆過他。", "寫好了。『生日快樂。這次是真心的。——開箱之神』"),
    give("card"), F("bless_zz"),
])
zz_after = [
    say("智障神", "嗚……我的限定版……"),
    say("智障神", "……其實，從來沒有人回我的開箱文。", "大家只會叫我『智障神』，然後無視。", "我只是……想要有人說一句『好看』而已。"),
    choice(("模型乙（真的很好看）", [
        say("智障神", "……", "……模型乙。", "被這樣說……原來是這種感覺啊。"),
        say("智障神", "這個送你。我的限定版模型。", "……不、不是因為你打贏我！是因為你有眼光！"),
        give("acc_figure"), karma(1), quest("zz", "done"), F("zzFriend"), zz_bless,
    ]), ("無視", [say("智障神", "……果然。"), nar("智障神抱著箱子，轉過身去。")])),
]
zz_script = [IF("flag:zzFriend", [
    say("智障神", "喔！無名氏！今天的開箱看了沒？", "大家現在都會回我『模型乙』了。……嘿嘿。"),
    zz_bless,
    IF("flag:abyssOpen", [say("智障神", "要去主機之心了吧？", "開箱之神在這裡幫你們加油！……推！")]),
], [IF("flag:zzBeaten", zz_after, [
    say("智障神", "看什麼看！沒看過開箱之神嗎！", "今天開的是限定版！全島只有三隻！", "你們這些買不起的窮鬼，只能在旁邊看我開箱！"),
    nar("旁邊的島民默默地發動了「無視」。"),
    IF("flag:sageJoin", [say("莎吉", "……他今天在新番捏他版洗了三十串開箱文。", "sage 都 sage 不完。")]),
    choice(("想看開箱", [
        say("智障神", "想看？哼，那就先過我這關！", "我的模型可是關節可動的！"),
        quest("zz", "open"), battle("zz"), F("zzBeaten"),
    ] + zz_after), ("無視", [say("智障神", "……又是無視。", "大家都這樣。……哼！")])),
])])]

# ---- 其他島上名人 ----
watermelon_script = [IF("flag:boss3", [
    say("西瓜哥", "釣魚王倒了……我也不釣了。", "以前我在別的論壇釣人，被趕到這座島，還是繼續釣。", "現在想想，好累喔。以後只吃西瓜。"),
    IF("flag:q_bday & !flag:bdayDone & !flag:bless_wm", [
        say("西瓜哥", "祝福卡？……『生日快樂』。", "這次不是反串，是真的。"), give("card"), F("bless_wm"),
    ]),
], [
    say("西瓜哥", "我覺得這季最好看的，是大家都說爛的那部。", "（他的眼神閃爍）……你不覺得嗎？不覺得就是你不懂。"),
    IF("flag:gagJoin", [say("阿梗", "西瓜哥，你又在反串了。"), say("西瓜哥", "……被發現了。")],
       [nar("這是釣魚。發動島民技能「無視」吧。")]),
    IF("flag:q_bday & !flag:bdayDone", [say("西瓜哥", "祝福卡？等我不釣了再說吧。")]),
])]
fangshi_script = [
    IF("flag:boss2", [
        say("放矢哥", "我朋友在製作公司說……", "……好啦，其實我沒有朋友在製作公司。", "我只是希望有人聽我說話。"),
    ], [
        say("放矢哥", "跟你說個內線消息，我朋友在製作公司。", "下一季的主角，最後會——"),
        IF("flag:sageJoin", [say("莎吉", "sage。"), nar("放矢哥被 sage 了。"), say("放矢哥", "……！……！")],
           [say("放矢哥", "——算了，說出來就不好玩了。"), nar("（他根本不知道。）")]),
    ]),
    IF("flag:q_bday & !flag:bdayDone & !flag:bless_fs", [
        say("放矢哥", "生日哥的派對？我朋友說他也會去。", "……我沒有朋友。我自己去。生日快樂。"),
        give("card"), F("bless_fs"),
    ]),
]
doodler_script = [
    IF("flag:boss4", [
        say("塗鴉廚", "小遙的畫回來了……", "我以前老是在別人的圖上亂塗。因為我不敢畫自己的。", "……我想試試看，畫我自己的。"),
    ], [
        say("塗鴉廚", "嘿嘿，這些空白的畫框，不塗一下太可惜了吧？"), nar("他手上拿著一支麥克筆。"),
        IF("flag:delJoin", [say("戴爾", "……自重。"), say("塗鴉廚", "是、是！")]),
    ]),
    IF("flag:q_bday & !flag:bdayDone & !flag:bless_dd", [
        say("塗鴉廚", "生日哥的祝福卡？我來畫！", "……這次不是塗鴉，是我自己畫的。"),
        nar("卡片上畫著一個戴著派對帽、笑得很開心的人。"),
        give("card"), F("bless_dd"),
    ]),
]
yijing_script = [
    say("易經廚", "來來來，讓我卜一卦。", "……卦象顯示：「{goal}」。", "嗯，這卦很準。"),
    IF("flag:sageJoin", [say("易經廚", "另外，你的桃花……"), nar("易經廚看了莎吉一眼。"), say("易經廚", "……天機不可洩漏。")],
       [say("易經廚", "另外，你的桃花……", "你連名字都沒有，桃花找不到你。")]),
]

MAPS = {}


def addmap(id, name, canvas_or_rows, bg, ents=(), warps=(), enc=None, auto=()):
    rows = canvas_or_rows.rows() if isinstance(canvas_or_rows, Canvas) else canvas_or_rows
    m = {"name": name, "rows": rows, "bg": bg, "ents": list(ents), "warps": [list(w) for w in warps], "auto": list(auto)}
    if enc:
        m["enc"] = enc
    MAPS[id] = m


# =====================================================================
# 綜合村
# =====================================================================
v = Canvas(24, 18)
v.border("T")
v.house(3, 1, 6, 3, "^", door=3, win=(1, 4))
v.rect(11, 1, 15, 3, "S")
v.set(13, 3, "X")
v.house(18, 1, 5, 3, "v", door=2, win=(0, 4))
v.house(2, 7, 5, 3, "v", door=2, win=(0, 4))
v.house(18, 12, 5, 3, "^", door=1, win=(3,))
v.house(2, 13, 5, 3, "^", door=3, win=(1,))
v.rect(10, 12, 13, 14, "~")
v.h(1, 23, 10)
v.set(23, 9, "=")
v.v(6, 4, 10); v.v(13, 4, 10); v.v(20, 4, 10); v.h(6, 20, 6)
v.v(19, 11, 13)
v.v(8, 11, 16); v.h(5, 8, 16)
v.dots(",", [(1, 5), (9, 2), (16, 2), (22, 7), (9, 15), (15, 15), (21, 16), (11, 8), (3, 5), (17, 9), (1, 11)])
v.dots("T", [(15, 12), (14, 16), (10, 16), (22, 5), (16, 3), (9, 1)])

elder_script = [
    IF("flag:abyssOpen", [
        say("綜合伯", "精華區的門開了。主機之心就在最深處。", "……無名氏。不管結局怎樣，都要回來吃泡麵。"),
    ], [IF("flag:mid", [
        say("綜合伯", "（綜合伯的頭上纏著繃帶）……抱歉，綜合之石被搶走了。",
            "雪見……沒想到會是她。她以前是綜合版最溫柔的版主啊。",
            "去釣魚港搭船吧。實名要塞就在島的邊緣。"),
    ], [IF("flag:raidDone", [
        say("綜合伯", "精華石一共四顆：新番之石、惡搞之石、掛圖之石，還有我手上的綜合之石。",
            "往東穿過新手串原，就是捏他平原。新番鎮在平原的北邊。"),
    ], [IF("flag:talkedElder", [
        say("綜合伯", "沉船灘在新手串原的南邊。洗版蟲最怕『炎上』……可惜你不會魔法。用推文斬多推幾下吧。"),
    ], [
        say("綜合伯", "你來了。看到南邊的沉船灘了嗎？昨晚又沉了一大片。",
            "舊的串會沉下去，本來是島的自然循環。新的回應蓋過舊的回應，島才會長出新的土地。",
            "可是這次不一樣。沉的速度太快了，而且海邊冒出了一大堆『洗版蟲』。",
            "那些蟲會把同一句話重複貼一萬次，把整片土地灌成廢串。"),
        say("無名氏", "（……又是爆破的前兆嗎？）"),
        say("綜合伯", "我老了，打不動了。你去沉船灘看看，把洗版的源頭找出來。",
            "這些拿去。島上的規矩：出門前，要吃飽。"),
        give("noodle", 3), give("tea", 1), gold(50),
        say("綜合伯", "沉船灘在村子東邊、新手串原的南方。累了就去癒姊的『癒之湯』泡一下。",
            "對了——按 Esc（或 X）可以打開選單。換裝備、用道具、存檔都在那裡。"),
        F("talkedElder"), goal("前往沉船灘（村子東邊 → 新手串原 → 往南）"),
    ])])])]),
]

fat_script = [
    IF("flag:untag1", [say("肥宅大叔", "聽好了，肥宅是一種態度。", "不是體型——是對喜歡的東西，永遠認真的態度！")],
       [say("肥宅大叔", "肥宅是一種態度。", "……你問我什麼態度？吃完泡麵再告訴你。")]),
]
fat_t_script = [
    say("肥宅大叔（名牌）", "……我是……我的名字是……", "……"), nar("他的嘴一開一合，卻說不出完整的話。"),
    IF("item:scissors", [
        choice(("用去背剪刀剪掉名牌", [
            nar("喀嚓。名牌掉了下來。"),
            say("肥宅大叔", "……呼！我又可以說話了！謝啦，無名氏！", "肥宅是一種態度！這個給你，我的珍藏。"),
            give("cola", 3), F("untag1"), ["call", "untagCheck"],
        ]), ("等一下再說", [])),
    ]),
]
wguy_script = [IF("flag:untag2", [say("www 哥", "wwwwwwwwwwwwwwwwwwwww！！！", "（他笑到停不下來。看起來很幸福。）")],
                  [say("www 哥", "wwwwww")])]
wguy_t_script = [
    say("www 哥（名牌）", "w……", "……"), nar("他好像忘記怎麼笑了。"),
    IF("item:scissors", [
        choice(("用去背剪刀剪掉名牌", [
            nar("喀嚓。"), say("www 哥", "……w……ww……wwwwwwwwwwwwww！！", "（他抱著你的手一直笑。）"),
            give("noodle2", 2), F("untag2"), ["call", "untagCheck"],
        ]), ("等一下再說", [])),
    ]),
]
old_script = [
    IF("flag:untag3", [
        say("老島民", "……謝謝你。被貼上名牌的時候，我心裡想說的話，一句都說不出來。",
            "沒有名字的回應，常常被說是不負責任。可是啊——", "也正因為沒有名字，才有人敢說出『我好痛苦』、『救救我』。")
    ], [
        say("老島民", "這座島被爆破了不知道多少次。", "每一次，都是一群連名字都不知道的人，一串一串地把它蓋回來。",
            "……能救這座島的，不是力量。", "是你在沒有人看見的時候，做的那些選擇。"),
    ]),
]
old_t_script = [
    say("老島民（名牌）", "……島……很安全……島……很安全……"), nar("他的眼神空洞。"),
    IF("item:scissors", [
        choice(("用去背剪刀剪掉名牌", [
            nar("喀嚓。"), say("老島民", "……啊。我剛剛，好像做了一個很安靜的夢。"),
            give("revive", 1), F("untag3"), ["call", "untagCheck"],
        ]), ("等一下再說", [])),
    ]),
]
cat_lady = [
    IF("flag:catDone", [say("貓奴阿姨", "喵咪說牠很喜歡你喔。"), say("肥宅快樂獸", "喵～")], [
        IF("flag:catFound", [
            say("貓奴阿姨", "喵咪！！你找到牠了！", "這是喵咪以前戴的貓耳髮箍。送你，戴上會跑得比較快喔。"),
            give("acc_cat"), karma(1), quest("cat", "done"), F("catDone"),
        ], [IF("flag:q_cat", [say("貓奴阿姨", "喵咪還沒回來……新手串原東北邊的樹叢，拜託了。")], [
            say("貓奴阿姨", "我家的喵咪……肥宅快樂獸跑不見了！", "牠最喜歡躲在新手串原東北邊的樹叢裡……可以幫我找找嗎？"),
            F("q_cat"), quest("cat", "open"),
        ])]),
    ]),
]
guardian_script = [
    IF("flag:fragDone", [say("精華區守門人", "島主之劍，用起來順手嗎？那是這座島最初的回應。")], [
        IF("item:frag>=5", [
            say("精華區守門人", "五片……全部都找到了。", "古串碎片，是很久很久以前，島上第一批神串碎掉留下的。", "我用它們為你打造一把劍。"),
            take("frag", 5), give("kb6"), karma(1), quest("frag", "done"), F("fragDone"),
            say("精華區守門人", "……據說，島上第一則回應只有一句話：「有人在嗎？」"),
        ], [IF("flag:q_frag", [
            say("精華區守門人", "古串碎片，你現在有 {item:frag} 片。找到 5 片再來吧。"),
        ], [
            say("精華區守門人", "我是精華區的守門人。被選進精華區的串，永遠不會沉。",
                "島上散落著『古串碎片』，是很久以前的神串碎掉留下的。", "如果你找齊五片，我可以用它們打造一把劍。"),
            F("q_frag"), quest("frag", "open"),
        ])]),
    ]),
]

raid_auto = [
    nar("回到村子的時候，廣場上一片騷動——"),
    say("名牌兵", "奉署名者大人之命！所有島民，即刻登記真實姓名！", "貼上名牌之後，你們就再也不能匿名亂說話了！"),
    say("肥宅大叔", "我、我不要名字！我是肥宅，肥宅是一種態度啊！"),
    say("名牌兵", "囉嗦！……喂，那邊那個。你叫什麼名字？"),
    say("無名氏", "……無名氏。"),
    say("名牌兵", "無名氏？那就給你貼上『無名氏』——", "……奇怪？名牌貼不上去！"),
    say("名牌兵", "可惡，抵抗實名就是罪！拿下他！"),
    battle("raid", noFlee=True),
    say("名牌兵", "嗚……撤退！向署名者大人報告！"),
    F("raidDone"), F("tagged"),
    say("綜合伯", "無名氏，你沒事吧！",
        "那些是『實名教團』的人。他們從島外來，說匿名是一切爆破的根源……要讓所有島民都貼上名牌。",
        "被貼上名牌的人，就說不出心裡真正想說的話了。你看，肥宅他們……"),
    IF("item:tag", [say("無名氏", "（在沉船灘撿到的空白名牌……跟他們身上的一模一樣。）")]),
    say("綜合伯", "但你不一樣。『無名氏』本身就是沒有名字的名字，名牌貼不上去。",
        "……聽好。這座島的地底有『主機之心』，那是島的心臟。它被四顆『精華石』封印著。",
        "綜合之石在我這裡。另外三顆，分別在新番版、歡樂惡搞版、掛圖版。",
        "教團想要的，一定是主機之心。你得搶在他們前面，把精華石收好！"),
    gold(150),
    say("綜合伯", "這是旅費。往東穿過新手串原，就是捏他平原。新番鎮在平原的北邊。"),
    goal("前往東方的捏他平原，到北邊的新番鎮尋找新番之石"),
]

village_ents = [
    ent("elder", "elder", 6, 4, elder_script, mark="!flag:talkedElder"),
    sign("sign_hall", 7, 4, "綜合村會館　（村長：綜合伯）"),
    ent("nurse", "nurse", 21, 4, [say("癒姊", "歡迎來到『癒之湯』，這裡是島上最療癒的地方。"), inn(20)]),
    ent("clerk", "clerk", 3, 10, [
        say("店員", "歡迎光臨～便利商店 24 小時營業，島沉了也照開。"),
        IF("flag:mid", [shop("village_late")], [shop("village_item")])]),
    ent("smith", "smith", 20, 15, [say("鍵盤師傅", "鍵盤就是島民的劍。手感決定一切。"), shop("village_gear")]),
    ent("fatguy", "fatguy", 16, 7, fat_script, show="!flag:tagged | flag:untag1"),
    ent("fatguy_t", "tagged", 16, 7, fat_t_script, show="flag:tagged & !flag:untag1", mark="item:scissors"),
    ent("wguy", "wguy", 16, 12, wguy_script, show="!flag:tagged | flag:untag2"),
    ent("wguy_t", "tagged", 16, 12, wguy_t_script, show="flag:tagged & !flag:untag2", mark="item:scissors"),
    ent("oldman", "oldman", 10, 4, old_script, show="!flag:tagged | flag:untag3"),
    ent("oldman_t", "tagged2", 10, 4, old_t_script, show="flag:tagged & !flag:untag3", mark="item:scissors"),
    ent("kid", "kid", 9, 7, [
        say("新手", "哥哥！我最近學到好多東西喔！",
            "怪物都有『弱點屬性』：炎上、冷場、暴雷、神串、黑歷史。打中弱點會『效果拔群』！",
            "戰鬥中選『防禦』，受到的傷害會減半。看到魔王準備大招的時候特別好用！",
            "還有還有，被『sage』的話就不能用技能，要喝冷靜茶才會好。",
            "……這些都是我在綜合版看到的。整理乙！")]),
    ent("villager2", "villager2", 9, 13, [
        say("島民", "島上的串啊，有人回應就會浮上來，沒人回的就會慢慢沉下去。", "所以我們說，回應就是島的生命。")]),
    ent("catlady", "catlady", 4, 16, cat_lady, mark="flag:catFound & !flag:catDone"),
    ent("bday", "bday", 12, 11, bday_script, mark="flag:raidDone & !flag:q_bday | item:card>=4 & !flag:bdayDone"),
    ent("yijing", "yijing", 8, 8, yijing_script),
    ent("teri_a", "teriyaki", 17, 5, teri_script("這座島被爆破過很多次。每次爆破完，綜合版總是第一個重新長出來的。",
        "……那時候的武將，大安萌綱、蘆洲洛克李……現在都不知道去哪了。"), show="!flag:boss1"),
    ent("teri_f", "teriyaki", 17, 5, teri_script("精華區開了啊。", "島爆了這麼多次，每次都有人回來。這次……換你了，無名氏。"),
        show="flag:abyssOpen"),
    ent("cat_v", "cat", 3, 16, [say("肥宅快樂獸", "喵～（牠蹭了蹭你的腳）")], show="flag:catDone"),
    ent("guardian", "guardian", 15, 4, guardian_script, mark="item:frag>=5 & !flag:fragDone"),
    ent("seal", "seal", 13, 3, [nar("精華區的大門。被四顆精華石的力量封印著，紋風不動。")], show="!flag:abyssOpen"),
    ent("snow_v", "snow", 14, 4, [say("雪見", "……我向綜合伯道歉了。他只說了一句『回來就好』。", "我在精華區等你們。這一次，讓我跟你們站在同一邊。")],
        show="flag:forgaveSnow & flag:abyssOpen"),
    sign("sign_v", 22, 8, "→ 新手串原　（往南）沉船灘　（往東）捏他平原"),
    ent("raid1", "soldier", 12, 9, [], show="flag:boss1 & !flag:raidDone"),
    ent("raid2", "soldier", 14, 9, [], show="flag:boss1 & !flag:raidDone"),
]
untag_check = [IF("flag:untag1 & flag:untag2 & flag:untag3", [
    nar("綜合村的名牌，全部剪掉了！"), quest("tags", "done"), karma(1), give("acc_charm"),
    say("綜合伯", "謝謝你，無名氏。這是村裡大家湊錢買的護符，收下吧。"),
])]
addmap("village", "綜合村", v, "field", village_ents,
       warps=[(23, 9, "field1", 1, 9, "R"), (23, 10, "field1", 1, 10, "R"), (13, 3, "abyss1", 12, 18, "U")],
       auto=[{"cond": "flag:boss1 & !flag:raidDone", "script": raid_auto}])

# =====================================================================
# 新手串原
# =====================================================================
f = Canvas(28, 20)
f.border("T")
f.h(0, 27, 9); f.h(0, 2, 10)
f.v(13, 9, 19); f.v(14, 17, 19)
f.rect(19, 1, 26, 6, "T"); f.rect(21, 2, 25, 4, "."); f.v(22, 5, 6, ".")
f.rect(18, 13, 21, 15, "~")
f.dots("T", [(3, 3), (4, 3), (8, 2), (9, 5), (5, 6), (16, 4), (11, 13), (4, 12), (8, 16), (23, 12), (25, 16), (17, 17), (6, 4), (1, 15), (24, 11)])
f.dots("R", [(10, 3), (17, 11), (6, 13), (22, 17), (2, 5), (15, 15)])
f.dots(",", [(5, 2), (11, 6), (16, 7), (3, 12), (9, 14), (20, 11), (24, 8), (11, 17), (18, 6)])
field1_ents = [
    sign("sign_f", 2, 8, "← 綜合村　→ 捏他平原　↓ 沉船灘"),
    ent("gateguard", "villager", 26, 9, [say("看守島民", "前面是捏他平原，最近有奇怪的白衣人出沒。", "先把沉船灘的事解決吧，綜合伯在等你的消息。")], show="!flag:boss1"),
    ent("gateguard2", "villager", 26, 8, [say("看守島民", "路開了。小心，捏他平原上有『暴雷菇』。", "被劇透到的話，會氣到說不出話來（sage 狀態），沒辦法用技能。")], show="flag:boss1"),
    ent("traveler", "xd", 8, 11, [say("旅行的島民", "你知道嗎？用『XD』的人會被說是外來種喔。島民都用 www。", "……不過我覺得，笑就是笑，用什麼符號都一樣啦。")]),
    chest("c1", 5, 15, "noodle", 2),
    chest("c2", 25, 2, gold_=60),
    chest("c3", 2, 17, "tea", 2),
    ent("cat_f", "cat", 24, 3, [say("肥宅快樂獸", "喵～"), nar("你抱起了肥宅快樂獸。牠發出滿足的呼嚕聲。"), F("catFound")],
        show="flag:q_cat & !flag:catFound"),
]
addmap("field1", "新手串原", f, "field", field1_ents,
       warps=[(0, 9, "village", 22, 9, "L"), (0, 10, "village", 22, 10, "L"), (27, 9, "plain", 1, 9, "R"),
              (13, 19, "beach", 11, 1, "D"), (14, 19, "beach", 12, 1, "D")],
       enc={"rate": 8, "troops": [["f1a", 3], ["f1b", 3], ["f1c", 2], ["f1d", 1], ["f1e", 2]]})

# =====================================================================
# 沉船灘
# =====================================================================
beach_rows = [
    "TTTTTTTTTTT==TTTTTTTT~~~",
    "Tssssssssss==sssssssss~~",
    "TssswsssssssssssJsssss~~",
    "TsswwssssJsssssssssssss~",
    "Tssssssssssswwwsssssss~~",
    "TssJsssssssssssssswssss~",
    "Tssssswwwssssssssswwsss~",
    "Tsssssssssssssssssssss~~",
    "TswsssssssJsssswwsssss~~",
    "Tsssssssssssssssssssss~~",
    "TssssssJsssswwssssssss~~",
    "Tsssssssssssssssssssss~~",
    "~ssswwssssssssssssssss~~",
    "~~sssssssssssssssss~~~~~",
    "~~~~sssssssssssssss~~~~~",
    "~~~~~~sssswwwsss~~~~~~~~",
    "~~~~~~~~~sssss~~~~~~~~~~",
    "~~~~~~~~~~~~~~~~~~~~~~~~",
]
boss1_script = [
    say("洗版蟲王", "洗版洗版洗版洗版洗版洗版洗版洗版洗版洗版洗版洗版——"),
    say("無名氏", "（牠在用同一句話把整片沙灘灌滿……！）"),
    battle("boss1"),
    nar("洗版蟲王化成一堆亂碼，沉進了沙裡。", "……亂碼之中，有一張白色的卡片。"),
    give("tag"),
    say("無名氏", "（這是……名牌？上面什麼字都沒寫。）"),
    F("boss1"), goal("回綜合村，向綜合伯報告"),
]
kraken_script = [
    say("？？？", "……沉下去的串……都在我這裡……"),
    say("沉船之主", "我是沉船之主。所有沒有人記得的串，都是我的一部分。", "想帶走它們？那就證明你們記得住！"),
    battle("kraken"),
    nar("沉船之主緩緩沉回海底。海面上，浮起了一顆發光的牙齒。"),
    give("acc_tooth"), quest("kraken", "done"), F("krakenDone"),
    say("沉船之主", "……偶爾……想起我們吧……"),
]
beach_ents = [
    ent("observer", "sailor", 15, 2, [
        IF("flag:abyssOpen & !flag:krakenDone", [
            say("沉船觀察員", "最近海底傳來奇怪的聲音……像是很多很多人在同時說話。", "就在沙灘最南邊。你們要去看看嗎？"),
            quest("kraken", "open"),
        ], [say("沉船觀察員", "我在這裡看串沉下去，已經看了十年。", "以前沉下去的，都是沒人回應的舊串。但是現在……連昨天才開的新串都在沉。",
                "有什麼東西，在海底把串往下拉。")])]),
    ent("boss1", "worm_king", 11, 14, boss1_script, show="!flag:boss1"),
    ent("kraken", "kraken", 16, 14, kraken_script, show="flag:abyssOpen & !flag:krakenDone"),
    crystal("crystal_b", 6, 11),
    chest("c1", 2, 1, "tea", 2),
    chest("c2", 21, 5, "frag"),
    chest("c3", 2, 9, "cola", 2),
    chest("c4", 19, 11, gold_=80),
    chest("sauce_b", 20, 3, "sauce"),
]
addmap("beach", "沉船灘", beach_rows, "beach", beach_ents,
       warps=[(11, 0, "field1", 13, 18, "U"), (12, 0, "field1", 14, 18, "U")],
       enc={"rate": 8, "troops": [["b1a", 3], ["b1b", 2], ["b1c", 3], ["b1d", 1], ["b1e", 2]]})

# =====================================================================
# 捏他平原
# =====================================================================
p = Canvas(28, 20)
p.border("T")
p.h(0, 20, 9); p.v(13, 0, 9); p.v(20, 9, 19); p.h(20, 27, 14)
p.rect(7, 0, 8, 19, "~"); p.set(7, 9, "b"); p.set(8, 9, "b")
p.dots("T", [(3, 5), (4, 5), (2, 12), (5, 15), (11, 3), (16, 3), (17, 4), (24, 3), (25, 7), (15, 12), (10, 16), (24, 18), (17, 17), (11, 12), (26, 11), (3, 18), (22, 6)])
p.dots("R", [(5, 2), (18, 7), (23, 11), (12, 15), (4, 8), (26, 17)])
p.dots(",", [(2, 2), (10, 6), (15, 6), (19, 2), (22, 16), (4, 14), (16, 17), (11, 11), (25, 12)])
plain_ents = [
    sign("sign_p", 12, 10, "↑ 新番鎮　→ 捏他之森　↓ 惡搞谷"),
    ent("fogguard", "otaku", 20, 18, [say("戴耳塞的島民", "別過去！南邊的惡搞谷整片被『捏他霧』包住了！", "聽說霧是從東邊的捏他之森飄出來的……")], show="!flag:boss2"),
    ent("otaku_p", "otaku", 16, 12, [say("戴眼罩的島民", "這季新番我全部都還沒看……", "因為一出門就會被暴雷。（他戴著眼罩，摸索著走路）")]),
    chest("c1", 3, 3, "noodle2"),
    chest("c2", 25, 4, gold_=150),
    chest("c3", 3, 16, "cola", 2),
]
addmap("plain", "捏他平原", p, "field", plain_ents,
       warps=[(0, 9, "field1", 26, 9, "L"), (13, 0, "shinban", 12, 16, "U"), (27, 14, "forest", 1, 10, "R"), (20, 19, "valley", 20, 1, "D")],
       enc={"rate": 8, "troops": [["p2a", 3], ["p2b", 3], ["p2c", 3], ["p2d", 2], ["p2e", 2]]})

# =====================================================================
# 新番鎮
# =====================================================================
s = Canvas(24, 18)
s.border("T")
s.house(2, 1, 7, 4, "v", door=3, win=(1, 5))
s.house(15, 1, 6, 3, "^", door=2)
s.set(16, 2, "P"); s.set(18, 2, "P"); s.set(19, 2, "P"); s.set(20, 2, "P")
s.house(2, 10, 6, 3, "v", door=2, win=(4,))
s.house(16, 10, 5, 3, "^", door=2, win=(0, 4))
s.set(17, 11, "P")
s.v(12, 5, 17); s.h(5, 19, 5); s.v(17, 4, 5)
s.h(4, 18, 13)
s.dots(",", [(1, 7), (10, 3), (14, 8), (21, 7), (9, 15), (20, 16), (15, 15), (1, 15)])
s.dots("T", [(22, 4), (1, 9), (22, 9), (10, 1), (13, 1), (8, 16), (16, 16)])
sage_join = [
    say("莎吉", "……你是誰？", "……無名氏？名牌兵貼不上去的那個人？傳聞跑得比你還快。"),
    say("莎吉", "我是莎吉。這間工作室，是新番版的『sage 術士』之家。",
        "sage 的意思是『不把自己推上去』。我們的魔法，是讓吵鬧的東西安靜下來。",
        "捏他霧就是我們一直在壓制的東西。可是三天前，森林裡出現了『捏他魔』，霧一下子濃到壓不住了。"),
    say("莎吉", "新番之石就在捏他之森深處的神社。如果被教團或捏他魔拿走……新番版就完了。"),
    say("莎吉", "……我一個人去不了。我不擅長……主動。", "你願意……讓我跟你一起去嗎？"),
    choice(("一起去吧", [say("莎吉", "……謝謝。我會盡量不拖累你。")]),
           ("（點頭）", [say("莎吉", "……嗯。")])),
    join("sage"), nar("莎吉加入了隊伍！"),
    say("莎吉", "我會用炎上術和冷場術。洗版蟲那種東西，一燒就沒了。", "……捏他之森在捏他平原的東邊。"),
    F("sageJoin"), goal("前往捏他平原東邊的捏他之森"),
]
xd_event = [
    say("島民甲", "喂，你剛剛打了『XD』對吧？"),
    say("島民乙", "XD 是外來種！島民都用 www！"),
    say("島民甲", "外來種你好，外來種再見～"),
    say("XD 君", "我、我只是覺得好笑而已……XD……"),
    choice(
        ("幫 XD 君說話", [
            say("無名氏", "笑就是笑。用什麼符號，有那麼重要嗎？"),
            say("島民甲", "……嘖。算了算了。"),
            say("XD 君", "謝、謝謝你……！我從島外來，一直不知道怎麼融入這裡。", "這個給你……島外買的眼罩，聽說可以防捏他。"),
            give("acc_mask"), karma(1), F("xdHelped"),
        ]),
        ("跟著一起笑他", [
            say("無名氏", "……www"), say("XD 君", "……"), nar("XD 君低著頭跑走了。"), karma(-1),
        ]),
        ("不關我的事", [nar("你轉身離開。背後傳來島民們的笑聲。")]),
    ),
    F("xdDone"), quest("xd", "done"),
]
shinban_ents = [
    ent("sage", "sage", 6, 6, sage_join, show="!flag:sageJoin", mark="!flag:sageJoin"),
    ent("streamer", "streamer", 6, 14, [say("實況主", "我是實況主兼旅館老闆！住一晚 30 K 幣，附贈我的實況配音。"), inn(30)]),
    ent("clerk2", "clerk", 19, 4, [say("動畫店店員", "歡迎光臨！最新的周邊和裝備都在這裡～", "……最新一集的內容？不能說！"), shop("shinban")]),
    ent("fansub", "fansub", 19, 14, [IF("flag:q_tags", [say("字幕組", "剪名牌的時候要小心，不要剪到人。")], [
        say("字幕組", "我們字幕組什麼都剪——片頭、片尾、多餘的雜訊。",
            "你說綜合村的人被貼了名牌？……那種東西，也剪得掉喔。", "這把『去背剪刀』給你，連最頑固的名牌都剪得下來。"),
        give("scissors"), F("q_tags"), quest("tags", "open"),
        say("無名氏", "……字幕組乙。"), say("字幕組", "被這樣說，還是會害羞耶。"),
        say("字幕組", "回綜合村的時候，找那些被貼名牌的人說話吧。")])]),
    ent("xd", "xd", 9, 9, xd_event, show="!flag:xdDone"),
    ent("bully1", "otaku", 8, 9, xd_event, show="!flag:xdDone"),
    ent("bully2", "villager", 10, 9, xd_event, show="!flag:xdDone"),
    ent("xd2", "xd", 9, 9, [say("XD 君", "我現在也會用 www 了……wwwXD", "……啊，混在一起了。不過大家好像也不在意了！")], show="flag:xdHelped"),
    ent("otaku_s", "otaku", 14, 15, [say("島民", "最新一集被劇透了……我的人生……", "（他陷入了冷場）")]),
    ent("zz", "zz", 15, 6, zz_script, show="!flag:zzFriend | !flag:boss2 | flag:boss3", mark="flag:zzBeaten & !flag:zzFriend"),
    ent("fangshi", "fangshi", 3, 15, fangshi_script),
    ent("teri_b", "teriyaki", 16, 8, teri_script("新番鎮那個抱著箱子大叫的，大家都叫他智障神。",
        "嘴巴是很壞啦……但他是真的喜歡模型。喜歡到不知道怎麼跟人說話。"), show="flag:boss1 & !flag:boss2"),
    ent("artist", "artist", 20, 7, [
        IF("flag:boss2", [say("繪師", "霧散了！大家都摘下眼罩了！", "第一次看的感動，一生只有一次。謝謝你們守住了它。")],
           [say("繪師", "新番版的人都很怕捏他。", "因為『第一次看』的感動，一生只有一次。")])]),
    ent("otaku3", "otaku", 3, 7, [say("戴眼罩的島民", "別、別跟我說話！我還沒看最新一集！")], show="!flag:boss2"),
    sign("sign_s", 13, 16, "新番鎮　——全面禁止暴雷——"),
]
shinban_auto = [{"cond": "!flag:shinbanIntro", "script": [
    nar("新番鎮——全島最熱愛動畫的島民聚集的地方。", "但是現在，街上的人都戴著眼罩和耳塞。空氣裡飄著淡淡的霧……"),
    say("戴眼罩的島民", "別、別跟我說話！我還沒看最新一集！"),
    F("shinbanIntro"), goal("在新番鎮打聽新番之石的下落（北邊的工作室）"),
]}]
addmap("shinban", "新番鎮", s, "field", shinban_ents, warps=[(12, 17, "plain", 13, 1, "D")], auto=shinban_auto)

# =====================================================================
# 捏他之森
# =====================================================================
fo = Canvas(28, 22, "K")
fo.carve([(0, 10), (6, 10), (6, 4), (12, 4), (12, 8), (18, 8), (18, 15), (24, 15), (24, 18)], "m")
fo.carve([(12, 8), (12, 16), (5, 16), (5, 19)], "m")
fo.carve([(18, 8), (18, 6), (21, 6)], "m")
fo.carve([(6, 4), (3, 4), (3, 2)], "m")
fo.carve([(18, 12), (23, 12), (23, 10)], "m")
fo.carve([(12, 16), (15, 16), (15, 18)], "m")
fo.rect(19, 1, 25, 6, "m"); fo.rect(21, 1, 23, 1, "S")
fo.rect(9, 12, 11, 14, "m"); fo.rect(2, 9, 4, 11, "m"); fo.rect(22, 17, 25, 19, "m")
boss2_script = [
    say("捏他魔", "嘻嘻嘻……來了來了，跟劇本寫的一模一樣！", "我知道你們接下來每一步要做什麼！因為我——已經看過結局了！"),
    say("莎吉", "……你這種人，最討厭了。"),
    battle("boss2"),
    nar("捏他魔的劇本散落一地，霧開始散去。"),
    say("莎吉", "……結束了。"), nar("莎吉從神社的祭壇上，取下一顆發著光的石頭。"),
    give("stone1"),
    say("莎吉", "無名氏……其實我一直很羨慕那些敢把自己推上去的人。",
        "sage 術士不推自己的串。可是，如果什麼都不說，就什麼都改變不了。", "……我想再跟你走一段。去找剩下的精華石吧。"),
    F("boss2"), goal("霧散了。從捏他平原往南，經過惡搞谷前往釣魚港"),
]
forest_ents = [
    ent("demon", "demon", 22, 3, boss2_script, show="!flag:boss2"),
    crystal("crystal_f", 19, 5),
    chest("c1", 3, 2, "frag"),
    chest("c2", 24, 18, "ar2"),
    chest("c3", 5, 19, "revive"),
    chest("c4", 15, 18, "noodle2", 2),
    chest("c5", 23, 10, gold_=200),
    chest("sauce_f", 25, 6, "sauce"),
]
addmap("forest", "捏他之森", fo, "forest", forest_ents,
       warps=[(0, 10, "plain", 26, 14, "L")],
       enc={"rate": 9, "troops": [["n2a", 2], ["n2b", 3], ["n2c", 2], ["n2d", 2]]},
       auto=[{"cond": "!flag:forestIntro", "script": [
           say("莎吉", "霧好濃……小心，這裡的怪物會『暴雷』。被打中會氣到沒辦法用技能（sage）。", "冷靜茶可以解。……新番鎮的動畫店有賣『防捏他眼罩』。"),
           F("forestIntro")]}])

# =====================================================================
# 惡搞谷
# =====================================================================
va = Canvas(28, 20)
va.border("R")
va.v(20, 0, 10); va.h(3, 27, 10); va.v(3, 0, 10)
va.rect(6, 13, 9, 15, "L"); va.rect(14, 3, 16, 5, "L"); va.rect(22, 14, 25, 16, "L")
va.dots("R", [(6, 3), (10, 6), (24, 4), (17, 13), (11, 17), (2, 15), (25, 8), (8, 8), (13, 12), (19, 17), (5, 6)])
va.dots("T", [(11, 2), (24, 2), (1, 12), (16, 8), (26, 12), (9, 18), (4, 17), (21, 6)])
va.dots("f", [(10, 11), (11, 11), (12, 11), (21, 11), (22, 11)])
va.dots(",", [(13, 7), (23, 7), (7, 11), (17, 16), (2, 6)])
valley_ents = [
    ent("herder", "villager", 12, 12, [say("牧羊的島民", "我的羊都在跟風……一隻往東跑，全部就往東跑。", "聽說東邊的釣魚港出大事了，所有人都被『釣』了。")]),
    ent("seal_v", "seal404", 3, 1, [nar("掛圖美術館的入口，被奇怪的封印擋住了。", "上面寫著：404 Not Found。"), say("莎吉", "……要先拿到惡搞之石，封印才會有反應吧。")], show="!flag:boss3"),
    sign("sign_va", 19, 11, "→ 釣魚港　↖ 掛圖美術館　↑ 捏他平原"),
    chest("c1", 25, 18, "frag"),
    chest("c2", 8, 3, "cracker", 2),
    chest("c3", 14, 17, "acc_ring"),
    chest("c4", 1, 1, "noodle2", 2),
    chest("sauce_v", 26, 1, "sauce"),
]
addmap("valley", "惡搞谷", va, "valley", valley_ents,
       warps=[(20, 0, "plain", 20, 18, "U"), (27, 10, "port", 1, 10, "R"), (3, 0, "gallery1", 11, 14, "U")],
       enc={"rate": 8, "troops": [["v3a", 3], ["v3b", 3], ["v3c", 1], ["v3d", 2], ["v3e", 2]]},
       auto=[{"cond": "!flag:valleyIntro", "script": [
           nar("惡搞谷——歡樂惡搞版的地盤。到處都是梗、到處都是笑聲……", "……本來應該是這樣。"),
           say("莎吉", "……好安靜。而且好熱。那些岩漿是……『炎上』？"),
           F("valleyIntro")]}])

# =====================================================================
# 釣魚港
# =====================================================================
po = Canvas(26, 18, "=")
po.rect(0, 0, 25, 0, "T"); po.rect(0, 0, 0, 17, "T"); po.set(0, 10, "=")
po.rect(0, 13, 25, 17, "~"); po.rect(21, 0, 25, 17, "~")
po.rect(19, 4, 24, 4, "k")
po.v(6, 13, 16, "k"); po.v(15, 13, 15, "k")
po.house(2, 1, 5, 3, "v", door=2, win=(0, 4))
po.house(9, 1, 5, 3, "^", door=2, win=(0, 4))
po.house(15, 1, 4, 3, "v", door=1, win=(3,))
po.rect(10, 7, 14, 8, "c")
po.dots("B", [(8, 12), (17, 12), (19, 9), (2, 7), (20, 2), (1, 12)])
gag_join = [
    say("阿梗", "各位觀眾！今天的梗是——『我本來想釣魚，結果被魚釣了』！", "……"),
    nar("台下一片寂靜。"),
    say("阿梗", "……www？沒人笑嗎？……唉。"),
    say("阿梗", "喔？你們兩個看起來沒被釣嘛。我是阿梗，歡樂惡搞版的梗王——自稱的。"),
    say("阿梗", "釣魚王把整個港口的人都釣了。他在棧橋盡頭，拿著惡搞之石，每天往港裡丟假消息當餌。",
        "我想用笑話讓大家清醒過來，可是被釣的人……是笑不出來的。"),
    say("阿梗", "……老實說，釣魚王是我以前的師父。",
        "我以前也是專門反串、釣魚的人。看大家氣得跳腳，我覺得很好笑。", "直到有一次，有人因為我的釣魚文……真的離開了這座島。"),
    say("阿梗", "所以我改行說笑話。這次，我想親手阻止他。", "讓我加入吧！wwww"),
    join("gag"), nar("阿梗加入了隊伍！"),
    say("阿梗", "我會用『wwww』幫大家回血，還會『冷靜一下』解除異常狀態。", "釣魚王最喜歡讓人『被釣』（混亂），港口的商店有賣『理智線』，可以防。"),
    F("gagJoin"), goal("前往棧橋盡頭，阻止釣魚王"),
]
boss3_script = [
    say("釣魚王", "哦？這不是我那個笨徒弟嗎？還帶了朋友。"),
    say("阿梗", "師父，收手吧。你釣到的不是魚，是人。"),
    say("釣魚王", "人跟魚有什麼不同？給點餌就上鉤，上鉤了就生氣，生氣了就更好釣。",
        "反串、釣魚、討戰……匿名的島最好玩了。沒人知道是我，我也不用負責。wwwww"),
    say("釣魚王", "來吧，讓我看看你們上不上鉤！"),
    battle("boss3"),
    nar("釣魚王跪倒在棧橋上。惡搞之石滾到了你的腳邊。"),
    give("stone2"),
    say("釣魚王", "……哼，刪了我吧。", "反正我只是個匿名的釣魚仔。消失了，也不會有人在乎。"),
    say("阿梗", "……無名氏，你決定吧。"),
    choice(
        ("放過他", [
            say("無名氏", "……你走吧。去說一個真正好笑的笑話。"),
            say("釣魚王", "……你這傢伙，天真得好笑。", "……哼。我會記住的。"),
            karma(1), F("sparedTroll"),
        ]),
        ("刪除他", [
            say("阿梗", "……我知道了。"),
            nar("阿梗按下了刪除鍵。釣魚王的身影像一則舊串，沉進了海裡。"),
            karma(-1), F("deletedTroll"),
        ]),
    ),
    say("阿梗", "……謝了。港口的人應該會慢慢清醒過來。"),
    say("莎吉", "最後一顆是掛圖之石。在惡搞谷西北邊的『掛圖美術館』。"),
    F("boss3"), goal("前往惡搞谷西北邊的掛圖美術館"),
]
sailor_script = [IF("flag:mid", [
    say("船夫", "要去實名要塞？……好吧，我載你們去。"),
    choice(("出發", [nar("小船駛向島的邊緣……"), warp("fgate", 3, 14, "U")]), ("再等等", [])),
], [say("船夫", "現在沒有船要出海喔。", "最近島的邊緣，出現了一座奇怪的白色要塞……")])]
port_ents = [
    ent("gag", "gag", 12, 7, gag_join, show="!flag:gagJoin", mark="!flag:gagJoin"),
    ent("bouncer", "fisher", 21, 4, [say("釣魚兵", "棧橋現在禁止通行。釣魚王大人正在『創作』。")], show="!flag:gagJoin"),
    ent("troll", "troll", 24, 4, boss3_script, show="!flag:boss3"),
    ent("troll2", "troll", 24, 4, [say("釣魚王", "……我在想笑話。不釣人的那種。", "……很難。比釣魚難多了。")], show="flag:sparedTroll"),
    ent("innkeep", "villager2", 5, 4, [say("旅館老闆娘", "海景房一晚 40 K 幣。", "……海景就是一直在沉的串。很療癒喔。"), inn(40)]),
    ent("clerk3", "clerk", 12, 4, [say("港口商店", "什麼都賣！真的！不是釣魚！"), shop("port")]),
    ent("fisher1", "fisher", 8, 10, [IF("flag:boss3", [say("島民", "我……我怎麼會相信那種東西……", "綜合村明明好好的啊。")],
                                         [say("被釣的島民", "聽說了嗎！？綜合村整個沉了！", "……什麼？你剛從綜合村來？騙人！網路上都這麼說！")])]),
    ent("fisher2", "villager", 16, 9, [IF("flag:boss3", [say("島民", "原來那篇文是釣魚……我還轉貼了一百次……")],
                                           [say("被釣的島民", "我看到一篇文說，吃泡麵會讓人變成肥宅！", "……我已經是肥宅了，怎麼辦！？")])]),
    ent("fisher3", "otaku", 4, 8, [IF("flag:boss3", [say("島民", "下次看到太誇張的標題，我會先發動「無視」。")],
                                       [say("被釣的島民", "我不相信！我不相信！我不相信！", "……你說什麼我都不相信！")])]),
    ent("sailor", "sailor", 7, 12, sailor_script, mark="flag:mid & !flag:fgateIntro"),
    ent("watermelon", "watermelon", 18, 7, watermelon_script),
    ent("zz_p", "zz", 3, 6, [
        say("智障神", "無名氏！我在這裡買到了『超限定版』……", "……結果箱子裡只有一張紙，寫著『你被釣了 www』。"),
        say("智障神", "……", "釣魚王，我跟你沒完！"), zz_bless,
    ], show="flag:zzFriend & flag:boss2 & !flag:boss3"),
    ent("teri_c", "teriyaki", 10, 11, teri_script("被釣不可恥，釣人才可恥。", "我也被釣過很多次。上鉤一次，下次就學會無視了。"),
        show="flag:boss2 & !flag:boss3"),
    sign("sign_po", 2, 11, "釣魚港　——本港不負責任何上鉤——"),
]
addmap("port", "釣魚港", po, "port", port_ents, warps=[(0, 10, "valley", 26, 10, "L")],
       auto=[{"cond": "!flag:portIntro", "script": [
           nar("釣魚港。港口裡到處都是坐著發呆、或是突然生氣的島民。"),
           say("被釣的島民", "聽說了嗎！？綜合村整個沉了！"),
           say("莎吉", "……他們全都被『釣』了。相信了假消息。", "舞台那邊好像有人在表演……"),
           F("portIntro"), goal("調查釣魚港（舞台上有人）"),
       ]}])

# =====================================================================
# 掛圖美術館 1F
# =====================================================================
g1 = Canvas(22, 16, "M")
g1.rect(0, 0, 21, 1, "F")
g1.dots("Q", [(4, 1), (9, 1), (15, 1), (18, 1), (2, 0), (13, 0)], only="F")
g1.rect(0, 0, 0, 15, "F"); g1.rect(21, 0, 21, 15, "F"); g1.rect(0, 15, 21, 15, "F")
g1.set(11, 15, "M"); g1.set(11, 1, "E")
g1.v(11, 2, 14, "c")
g1.dots("I", [(5, 4), (16, 4), (5, 10), (16, 10)], only="M")
g1.rect(1, 7, 4, 7, "F"); g1.rect(17, 7, 20, 7, "F")
del_join = [
    say("戴爾", "止步。", "我是刪文騎士戴爾，掛圖美術館最後的守衛。"),
    say("戴爾", "……又是想來拿掛圖之石的人嗎？教團的人上禮拜才被我趕走。"),
    say("莎吉", "我們不是教團的人。我們是來保護精華石的。"),
    say("戴爾", "口說無憑。在匿名的島上，誰都可以說自己是好人。", "拔劍吧。讓我用劍，確認你們的回應是真是假。"),
    battle("duel"),
    say("戴爾", "……夠了。你們的劍裡，沒有惡意。"),
    say("戴爾", "我曾經是版主騎士團的一員。大爆破的那個晚上，我們什麼都沒能保護住。",
        "騎士團解散了。我一個人留在這裡，守著這些還沒消失的圖。"),
    say("戴爾", "……二樓的『失落之圖』，已經吞掉了一半的收藏。掛圖之石也在牠那裡。", "我一個人打不過牠。讓我跟你們一起去吧。"),
    join("del"), nar("戴爾加入了隊伍！"),
    say("戴爾", "我會用『挑釁』吸引敵人的攻擊，保護你們。", "『刪除』可以直接刪掉快不行的雜魚。"),
    F("delJoin"), goal("前往美術館二樓，找回三張失落的縮圖，打倒失落之圖"),
]
mid_event = [
    nar("下樓的時候，大廳裡站著一群白色的身影。"),
    say("名牌兵", "署名者大人駕到！"),
    say("雪見", "……辛苦了，各位。", "你就是那個貼不上名牌的『無名氏』嗎？"),
    say("戴爾", "……雪見？你是……綜合版的雪見版主？"),
    say("雪見", "好久不見，戴爾。版主騎士團解散之後，我去了島外。",
        "我在外面看了很多。看著這座島一次又一次被爆破，被匿名的人鬧版、洗版、討戰、釣到崩潰。"),
    say("雪見", "我最好的朋友小遙，是掛圖版最會畫畫的人。她被一群匿名的廚罵到再也不畫了。",
        "罵她的人是誰？沒有人知道。沒有人需要負責。"),
    say("雪見", "所以，我要讓這座島實名化。在主機之心刻下每一個人的名字。",
        "有了名字，就有了責任。這座島，就再也不會被爆破了。"),
    say("阿梗", "……可是被貼上名牌的人，連笑都笑不出來了啊！"),
    say("雪見", "安靜，總比崩壞好。", "──實名之光。"),
    nar("一道白光閃過。身體動不了……！"),
    nar("雪見從你的背包裡，取走了三顆精華石。"),
    take("stone1"), take("stone2"), take("stone3"),
    say("雪見", "綜合之石，我已經從綜合伯那裡拿到了。",
        "無名氏，我不討厭你。但是沒有名字的人，是保護不了任何東西的。"),
    nar("雪見和名牌兵們離開了。"),
    say("戴爾", "……可惡。", "她要去的地方，一定是島邊緣的『實名要塞』。從釣魚港搭船就能到。"),
    say("莎吉", "……綜合伯！綜合村也出事了嗎……？"),
    F("mid"), goal("從釣魚港搭船前往實名要塞（也可以先回綜合村看看）"),
]
gallery1_ents = [
    ent("del", "del", 11, 3, del_join, show="!flag:delJoin", mark="!flag:delJoin"),
    ent("doodler", "doodler", 16, 6, doodler_script),
    ent("teri_d", "teriyaki", 16, 12, teri_script("畫圖的人最怕兩件事：沒人看，和被亂塗。",
        "附近那個塗鴉廚……其實他也會畫，只是不敢畫自己的。"), show="flag:boss3 & !flag:mid"),
    chest("c1", 2, 2, "noodle2", 3),
    chest("c2", 19, 2, "acc_line"),
    chest("c3", 2, 13, "cola", 3),
    chest("c4", 19, 13, "boba", 2),
    ent("snow_g", "snow", 11, 9, [], show="flag:boss4 & !flag:mid"),
    ent("sold_g1", "soldier", 10, 10, [], show="flag:boss4 & !flag:mid"),
    ent("sold_g2", "soldier", 12, 10, [], show="flag:boss4 & !flag:mid"),
]
addmap("gallery1", "掛圖美術館 1F", g1, "gallery", gallery1_ents,
       warps=[(11, 15, "valley", 3, 1, "D"), (11, 1, "gallery2", 11, 13, "U")],
       enc={"rate": 7, "troops": [["g4a", 3], ["g4b", 1], ["g4c", 3], ["g4d", 2], ["g4e", 2]]},
       auto=[{"cond": "!flag:galleryIntro", "script": [
           nar("掛圖美術館。島民們分享過的每一張圖，都掛在這裡。", "……但是有很多畫框是空的，只剩下『404』的字樣。"),
           say("阿梗", "這裡是島的記憶倉庫。圖片消失了，就代表有人忘記了它們。"),
           F("galleryIntro")]},
           {"cond": "flag:boss4 & !flag:mid", "script": mid_event}])

# =====================================================================
# 掛圖美術館 2F
# =====================================================================
g2 = Canvas(22, 16, "M")
g2.border("F")
g2.dots("Q", [(3, 0), (8, 0), (14, 0), (19, 0), (0, 4), (21, 10)], only="F")
g2.rect(1, 6, 20, 6, "F"); g2.set(11, 6, "c")
g2.v(8, 7, 14, "F"); g2.set(8, 10, "M")
g2.v(14, 7, 14, "F"); g2.set(14, 10, "M")
g2.v(11, 1, 13, "c"); g2.set(11, 14, "E")
g2.dots("I", [(3, 3), (18, 3)], only="M")
seal2 = [IF("item:thumbA & item:thumbB & item:thumbC", [
    nar("你把三張失落的縮圖，放回封印的畫框裡……", "404 的字樣消失了。門開了！"),
    take("thumbA"), take("thumbB"), take("thumbC"), F("sealOpen"),
], [nar("畫框上寫著：404 Not Found。", "旁邊有三個空著的縮圖位置。"),
    say("戴爾", "失落的縮圖……應該散落在這層樓的展示間裡。")])]
boss4_script = [
    say("失落之圖", "……你們……記得我嗎……", "……沒有人記得我……我是被刪掉的圖……被遺忘的圖……"),
    say("戴爾", "牠是所有被遺忘的圖片聚集成的……", "小心，牠會進入『404』狀態，變得幾乎打不中！只有神串屬性的攻擊能讓牠現形。"),
    battle("boss4"),
    nar("失落之圖的身體一片一片剝落，變回一張張普通的圖片，回到了牆上的畫框裡。"),
    give("stone3"),
    say("戴爾", "……這些圖，都回來了。"),
    say("阿梗", "原來被遺忘的東西，只是在等人想起它而已。"),
    F("boss4"), goal("帶著三顆精華石離開美術館"),
]
mimic_script = [nar("寶箱……動了！"), battle("mimic1"), F("mimicDone"), nar("畫框怪倒下了。裡面藏著東西！"), give("revive", 2)]
gallery2_ents = [
    ent("seal2", "seal404", 11, 6, seal2, show="!flag:sealOpen"),
    ent("phantom", "phantom", 11, 3, boss4_script, show="!flag:boss4"),
    chest("tA", 2, 8, "thumbA"),
    chest("tB", 19, 8, "thumbB"),
    chest("tC", 2, 13, "thumbC"),
    ent("mimic_a", "chest", 19, 13, mimic_script, show="!flag:mimicDone"),
    ent("mimic_b", "chest_open", 19, 13, [nar("空的。畫框怪的牙齒還卡在邊上。")], show="flag:mimicDone"),
    crystal("crystal_g", 10, 9),
    chest("c1", 1, 1, "pen3"),
    chest("c2", 20, 1, "hv3"),
]
addmap("gallery2", "掛圖美術館 2F", g2, "gallery", gallery2_ents,
       warps=[(11, 14, "gallery1", 11, 2, "D")],
       enc={"rate": 7, "troops": [["g4a", 3], ["g4b", 1], ["g4c", 3], ["g4d", 2], ["g4e", 2]]})

# =====================================================================
# 實名要塞外圍
# =====================================================================
fg = Canvas(24, 18, "G")
fg.border("W")
fg.set(12, 0, "X")
fg.rect(0, 10, 6, 17, "~"); fg.v(3, 10, 16, "k")
fg.rect(8, 3, 8, 8, "W"); fg.rect(15, 3, 15, 8, "W")
fg.set(8, 5, "N"); fg.set(15, 5, "N"); fg.set(5, 0, "N"); fg.set(18, 0, "N"); fg.set(23, 6, "N")
fg.rect(17, 11, 19, 11, "W"); fg.rect(10, 13, 12, 13, "W")
prison_intro = [nar("實名要塞——建在島的邊緣，一半在島上，一半懸在資訊之海上。", "白色的牆上，掛滿了寫著名字的旗幟。"),
                say("戴爾", "入口在北邊。守衛很多，小心。", "……聽說教團把不肯登記的島民，都關在要塞裡。"),
                quest("prison", "open"), F("fgateIntro"), goal("潛入實名要塞，找到雪見")]
fgate_ents = [
    ent("gatesoldier", "soldier", 12, 1, [say("名牌兵隊長", "站住！未登記者不得進入！"), battle("gate"), F("gateOpen"), nar("通往要塞內部的門打開了。")], show="!flag:gateOpen"),
    ent("deserter", "deserter", 20, 14, [say("逃兵", "噓……我是逃兵。我受不了每天幫人貼名牌了。", "我偷了一些軍需品，便宜賣你們。"), shop("fortress")]),
    ent("teri_e", "teriyaki", 9, 12, teri_script("實名要塞啊……我的名號全島都知道，他們第一個就來抓我。",
        "所以我躲到這裡擺攤了。……名字從來就不是重點，重要的是你說了什麼。"), show="flag:mid & !flag:abyssOpen"),
    crystal("crystal_fg", 5, 8),
    ent("sailor2", "sailor", 3, 16, [say("船夫", "要回釣魚港嗎？"), choice(("回去", [warp("port", 7, 11, "D")]), ("留下", []))]),
    chest("c1", 21, 2, "boba", 2),
    chest("c2", 1, 2, "cracker", 3),
    chest("c3", 22, 16, "chicken", 2),
]
addmap("fgate", "實名要塞外圍", fg, "fortress", fgate_ents,
       warps=[(12, 0, "fin", 12, 16, "U")],
       enc={"rate": 7, "troops": [["r5a", 3], ["r5b", 2], ["r5c", 2], ["r5d", 2], ["r5e", 2]]},
       auto=[{"cond": "!flag:fgateIntro", "script": prison_intro}])

# =====================================================================
# 實名要塞內部
# =====================================================================
fi = Canvas(24, 18, "G")
fi.border("W")
fi.set(12, 17, "X")
fi.rect(1, 1, 9, 10, "W"); fi.rect(14, 1, 22, 10, "W")
fi.rect(1, 11, 9, 11, "W"); fi.rect(14, 11, 22, 11, "W")
fi.rect(10, 8, 13, 8, "W"); fi.set(12, 8, "G")
fi.rect(6, 7, 9, 9, "G"); fi.rect(14, 7, 17, 9, "G")
fi.rect(6, 2, 9, 4, "G"); fi.rect(14, 2, 17, 4, "G")
fi.v(4, 12, 15, "W")
fi.dots("N", [(10, 0), (13, 0), (5, 1), (18, 1), (1, 11), (22, 11)], only="W")


def prisoner(id, x, y, sprite):
    return ent(id, sprite, x, y, [
        say("被實名的島民", "……救……我……"),
        IF("item:scissors", [nar("你用去背剪刀，剪掉了他的名牌。")], [nar("戴爾用劍尖，小心地挑掉了他的名牌。")]),
        say("島民", "……謝謝你們！我會從後門逃出去！"),
        F(id), ["call", "prisonCheck"],
    ], show="!flag:" + id)


boss5a_script = [
    say("名牌騎士團長", "我是署名者大人的劍——名牌騎士團長。",
        "名字就是秩序。秩序就是和平。", "你們這些沒有名字的雜音，就在這裡被消音吧！"),
    battle("boss5a"),
    nar("騎士團長倒下了。通往頂樓的路打開了。"),
    F("boss5a"),
]
boss5b_script = [
    say("雪見", "……你們還是來了。", "主機之心的實名儀式，只差最後一步。四顆精華石已經送進儀式之間了。"),
    say("無名氏", "……這座島上的人，不需要名字，也能好好說話。"),
    say("雪見", "你要怎麼證明？你看過匿名的人能有多殘忍嗎？"),
    say("戴爾", "雪見，你說的都是真的。", "可是那天晚上，最先衝去救火的，也都是匿名的人。"),
    say("雪見", "……夠了。如果你們要阻止我，就用力量說服我吧！"),
    battle("boss5b"),
    nar("雪見單膝跪地。"),
    say("雪見", "……為什麼……我明明……是為了這座島……"),
    nar("就在這時——要塞深處傳來刺耳的笑聲。"),
    say("？？？", "辛苦了，雪見。你做得非常好。"),
    say("雪見", "……島主大人？這個聲音……不對……你不是島主大人……！"),
    say("無貌者", "島主？那傢伙早就不管這座島了。一直在你耳邊說話的，是我。"),
    say("無貌者", "我是『無貌者』。所有匿名者沒說出口的惡意、所有的爆破、洗版、釣魚、炎上……都是我。",
        "實名儀式會把主機之心的力量抽乾。到時候，這座島就是我的了。"),
    say("無貌者", "謝謝你啊，雪見。是你親手把精華石送到我面前的。www"),
    nar("黑影帶著四顆精華石，鑽進了地板的縫隙。地底深處傳來轟隆聲——"),
    say("戴爾", "……那個方向，是綜合村！精華區的入口！"),
    say("雪見", "……我……我到底做了什麼……"),
    choice(
        ("向雪見伸出手", [
            say("無名氏", "你想保護這座島。這一點，我們是一樣的。"),
            say("雪見", "……你……不恨我嗎？"),
            say("阿梗", "恨你又不會比較好笑。走吧，一起去揍那個黑影！"),
            say("雪見", "……謝謝。我先回綜合村，向綜合伯謝罪。", "在精華區見。"),
            karma(2), F("forgaveSnow"),
        ]),
        ("「這一切，都是你造成的。」", [
            say("無名氏", "……這一切，都是你造成的。"),
            say("雪見", "……嗯。我知道。"),
            nar("雪見沒有再說話，一個人離開了。"),
            karma(-1),
        ]),
    ),
    F("boss5b"), F("abyssOpen"),
    nar("你們搭上逃兵準備的小船，全速趕回綜合村……"),
    warp("village", 13, 5, "U"),
    nar("精華區的封印，已經被從內側打破了。"),
    goal("從綜合村的精華區入口，前往最深處的主機之心"),
]
fin_ents = [
    prisoner("p1", 7, 8, "tagged"),
    prisoner("p2", 16, 8, "tagged2"),
    prisoner("p3", 2, 13, "tagged"),
    ent("general", "general", 12, 8, boss5a_script, show="!flag:boss5a"),
    ent("snow_f", "snow", 12, 2, boss5b_script, show="!flag:boss5b"),
    crystal("crystal_fi", 15, 13),
    chest("c1", 22, 16, "frag"),
    chest("c2", 8, 2, "acc_fat"),
    chest("c3", 15, 2, "chicken", 2),
    chest("c4", 1, 16, "pen4"),
]
prison_check = [IF("flag:p1 & flag:p2 & flag:p3", [
    nar("被關的島民全部救出來了！"), quest("prison", "done"), karma(1), give("bento", 2),
    say("戴爾", "……做得好。他們會記得今天的。"),
])]
addmap("fin", "實名要塞內部", fi, "fortress", fin_ents,
       warps=[(12, 17, "fgate", 12, 1, "D")],
       enc={"rate": 7, "troops": [["r5a", 3], ["r5b", 2], ["r5c", 2], ["r5d", 2], ["r5e", 2]]})

# =====================================================================
# 精華區深淵
# =====================================================================
ab = Canvas(24, 20, "V")
ab.carve([(12, 19), (12, 15), (4, 15), (4, 10), (9, 10), (9, 6), (4, 6), (4, 2), (2, 2)], "Z")
ab.carve([(12, 15), (19, 15), (19, 10), (14, 10), (14, 6), (19, 6), (19, 2), (21, 2)], "Z")
ab.carve([(9, 6), (12, 6), (12, 1)], "Z")
ab.carve([(4, 15), (4, 17), (2, 17)], "Z")
ab.carve([(19, 15), (19, 17), (21, 17)], "Z")
ab.carve([(9, 10), (11, 10), (11, 12)], "Z")
ab.rect(11, 1, 13, 3, "Z")
ab.set(12, 19, "E"); ab.set(12, 1, "E")
ab.set(3, 10, "Z"); ab.set(20, 10, "Z"); ab.set(10, 7, "Z")
for (x, y) in [(3, 1), (5, 1), (18, 1), (20, 1), (1, 9), (22, 9), (6, 18), (17, 18), (10, 0), (14, 0)]:
    ab.set(x, y, "Y")
abyss_ents = [
    crystal("crystal_a", 13, 3),
    chest("c1", 2, 2, "kb5"),
    chest("c2", 21, 2, "pen5"),
    chest("c3", 2, 17, "ar5"),
    chest("c4", 21, 17, "hv4"),
    chest("c5", 11, 12, "frag"),
    ent("memory1", "sign", 3, 10, [nar("一則很久以前的回應：", "「沒關係，島爆了，我們再蓋一次就好。」")]),
    ent("memory2", "sign", 20, 10, [nar("一則很久以前的回應：", "「謝謝你昨天回我。我本來以為，不會有人看到。」")]),
    ent("memory3", "sign", 10, 7, [nar("一則很久以前的回應：", "「有人在嗎？」", "底下有一萬則回應，全部寫著：「有。」")]),
]
addmap("abyss1", "精華區深淵", ab, "abyss", abyss_ents,
       warps=[(12, 19, "village", 13, 4, "D"), (12, 1, "core", 8, 12, "U")],
       enc={"rate": 7, "troops": [["a6a", 3], ["a6b", 2], ["a6c", 2], ["a6d", 2], ["a6e", 1]]},
       auto=[{"cond": "!flag:abyssIntro", "script": [
           nar("精華區深淵——被選進精華區的神串，都沉睡在這裡。"),
           say("莎吉", "好安靜……這裡的每一道光，都是某個人很久以前寫下的回應。"),
           say("戴爾", "黑影的氣息，從最深處傳來。"),
           F("abyssIntro")]}])

# =====================================================================
# 主機之心
# =====================================================================
co = Canvas(16, 14, "V")
co.rect(3, 2, 12, 12, "C")
co.set(8, 13, "E")
for (x, y) in [(3, 2), (12, 2), (3, 12), (12, 12), (2, 6), (13, 6)]:
    co.set(x, y, "Y")
voices = [
    say("綜合伯", "推。……記得回來吃泡麵。"),
    say("肥宅大叔", "推！！肥宅是一種態度！"),
    IF("flag:catDone", [say("貓奴阿姨", "推～　喵咪也說推！"), say("肥宅快樂獸", "喵！")]),
    IF("flag:xdHelped", [say("XD 君", "推 XD……不對，推 www！")]),
    IF("flag:sparedTroll", [say("釣魚王", "……推。這次不是釣魚。")]),
    IF("flag:untag3", [say("老島民", "推。……我就說吧。")]),
    IF("flag:bdayDone", [say("生日哥", "今天我生日ㄛ！……不對，今天是島的生日！", "推！生日快樂！")]),
    IF("flag:metTeri", [say("照燒貓", "推。醬汁要慢慢燒才香，島也是。")]),
    IF("flag:zzFriend", [say("智障神", "開箱之神參上！這次要開的是……島的未來！", "推！模型乙！")]),
    IF("flag:bless_wm", [say("西瓜哥", "推。這次不是反串。")]),
    say("莎吉", "……age。"),
    say("阿梗", "推推推推推推推推wwwwwwwwww"),
    say("戴爾", "推。"),
    say("雪見", "……推。"),
    say("無名氏", "+1", "+2", "+3", "這串要收進精華區", "推"),
]
final_script = [
    say("無貌者", "來了啊，無名氏。",
        "看看你們——一群沒有名字的傢伙，想守護一座沒有名字的島。",
        "可笑。你知道在沒有人看見的地方，人會變得多殘忍嗎？我就是證據。"),
    IF("flag:forgaveSnow", [say("雪見", "……也會變得多溫柔。我也見過。")]),
    say("無名氏", "……那就來比比看吧。"),
    battle("final1"),
    IF("karma>=5 & flag:forgaveSnow", [
        say("無貌者", "……沒用的……我是殺不死的……", "只要還有人匿名，只要還有人在黑暗裡打出惡毒的字……我就會一直回來！"),
        nar("黑影吞噬了主機之心的光，膨脹成巨大的形體——"),
        say("雪見", "……主機之心的光被吸走了！再這樣下去……"),
        say("無名氏", "……那就讓它重新亮起來。", "用回應。"),
        nar("就在那一刻——", "主機之心的表面，浮現了一行字。"),
        say("無名氏", "推"),
    ] + voices + [
        nar("一則、十則、一百則、一萬則——", "匿名的回應像雨一樣落下。每一則，都寫著同一個字。", "沒有名字，沒有 ID。只有——推。"),
        ["heal"],
        nar("溫暖的光包圍了隊伍！HP、MP 全回復，攻擊力提升！"),
        say("無貌者‧真形", "……這是什麼……這麼多……這麼多沒有名字的……溫柔……！？"),
        battle("final2", partyBuff="atkUp"),
        F("finalDone"), ending("true"),
    ], [
        nar("無貌者發出刺耳的尖叫，化成黑煙散去了。", "但是主機之心上，也出現了巨大的裂痕。光芒正一點一點地流失。"),
        IF("flag:forgaveSnow", [
            say("雪見", "……實名儀式還能啟動。只要刻下所有人的名字，主機之心就會被固定住，島就不會再沉了。",
                "但是，這座島就再也不是……匿名的島了。", "無名氏，你決定吧。"),
        ], [
            say("戴爾", "……主機之心撐不住了。祭壇上的實名儀式還在運轉……如果啟動它，島就能被固定住。",
                "但是，所有人都會被刻上名字。", "無名氏，你決定吧。"),
        ]),
        choice(("啟動實名儀式", [F("finalDone"), ending("real")]),
               ("封印主機之心，維持匿名", [F("finalDone"), ending("anon")])),
    ]),
]
core_ents = [
    ent("faceless", "faceless", 8, 4, final_script, show="!flag:finalDone"),
    crystal("crystal_c", 5, 11),
    ent("snow_c", "snow", 10, 6, [say("雪見", "我在這裡。……一起結束這一切吧。")], show="flag:forgaveSnow"),
]
addmap("core", "主機之心", co, "core", core_ents, warps=[(8, 13, "abyss1", 12, 2, "D")])

# =====================================================================
# 追加內容：章節卡、討論板
# =====================================================================
raid_auto.append(CH["ch1"])
boss2_script.append(CH["ch2"])
boss3_script.append(CH["ch3"])
mid_event.append(CH["ch4"])
boss5b_script.append(CH["ch5"])
for _mid, (_x, _y, _b) in BOARD_PLACES.items():
    MAPS[_mid]["ents"].append(ent("board_" + _mid, "board", _x, _y, [["board", _b]]))

# =====================================================================
# 結局
# =====================================================================
ENDINGS = {
    "real": {"title": "結局：實名之島", "lines": [
        "實名儀式啟動了。主機之心刻滿了島民的名字。",
        "島，不再沉沒。再也沒有爆破，沒有洗版，沒有釣魚。",
        "每個人都有了名字，說話也都變得很小心。",
        "……也再也沒有人打出「wwwww」了。",
        "只有一個人的名牌，永遠是空白的。",
        "糟糕島，再也不糟糕了。",
        "——也再也不是糟糕島了。",
    ]},
    "anon": {"title": "結局：匿名之海", "lines": [
        "主機之心被封印了。島，沒有停止下沉。",
        "舊的串依然一條一條地沉進海裡，新的回應依然一則一則地冒出來。",
        "也許有一天，無貌者還會回來。也許有一天，島還會再被爆破。",
        "但是到了那一天，島民們也會一串一串地，把它重新建起來。",
        "就像以前的每一次一樣。",
    ]},
    "true": {"title": "真結局：最後的回應", "lines": [
        "無貌者在無數的「推」之中，慢慢地變小、變淡……",
        "最後，牠變成了一則普通的回應。上面只寫著：「……對不起。」",
        "主機之心重新亮了起來。比以前任何時候，都還要亮。",
        "島民們決定，繼續匿名下去。",
        "不是因為匿名就不用負責。",
        "而是因為，就算沒有人知道是誰——也還是有人，願意說出溫柔的話。",
        "雪見回到了綜合版，重新當上了版主。",
        "阿梗的笑話，終於讓整個港口笑翻了。",
        "綜合村裡，每天還是有人說「今天我生日ㄛ」，也每天都有人回他「生日快樂」。",
        "莎吉開始在自己的串裡……偶爾 age 一下。",
        "戴爾在美術館掛上了一張新的圖：四個人站在主機之心前面的樣子。",
        "後來，有人問那個沒有名字的勇者：「你到底叫什麼名字？」",
        "他笑了笑，回答——",
        "「無名氏就好。」",
    ]},
}

CALLS = {"untagCheck": untag_check, "prisonCheck": prison_check}

GAME = {
    "title": "糟糕島物語",
    "subtitle": "～無名氏與最後的回應～",
    "tiles": TILES,
    "elements": ELEMENTS,
    "statuses": STATUSES,
    "actors": ACTORS,
    "skills": SKILLS,
    "items": ITEMS,
    "enemies": ENEMIES,
    "troops": TROOPS,
    "shops": SHOPS,
    "quests": QUESTS,
    "maps": MAPS,
    "calls": CALLS,
    "endings": ENDINGS,
    "start": {"map": "village", "x": 9, "y": 6, "dir": "D", "gold": 30, "items": [["noodle", 2]], "party": ["hero"],
              "script": [
                  CH["prologue"],
                  nar("在資訊之海的正中央，漂浮著一座島。",
                      "島上的每一寸土地，都是島民們留下的『回應』堆起來的。",
                      "有人叫它 K 島。也有人叫它——糟糕島。",
                      "第一天來到這裡的人，都覺得島民很糟糕；住久了，才發現大家其實都很純樸。",
                      "島上沒有人需要名字。大家互相稱呼對方：「無名氏」。",
                      "這座島被爆破過很多次。每一次，島民都會一串一串地，把它重新建起來。",
                      "然而這一次……島，開始沉了。"),
                  say("綜合伯", "喂——無名氏！你總算醒了！", "快來會館門口一趟，出大事了！",
                      "會館就是你左上方那棟紅屋頂的大房子，我在門口等你！"),
                  goal("到左上方紅屋頂的會館門口，找綜合伯（頭上有「！」的人）"),
              ]},
    "expCurve": {"mul": 10, "pow": 2.2},
    "boards": BOARDS,
    "skits": SKITS,
    "travel": TRAVEL,
    "noTravel": NO_TRAVEL_MAPS,
    "gauge": GAUGE,
    "combos": COMBOS,
    "maxLevel": 40,
}

# =====================================================================
# 驗證
# =====================================================================
errors = []
warns = []


def err(m):
    errors.append(m)


COND_TERM = ("flag:", "item:", "karma>=", "gold>=", "party:")


def check_cond(c, where):
    for alt in c.split("|"):
        for t in alt.split("&"):
            t = t.strip().lstrip("!")
            if not t.startswith(COND_TERM):
                err(f"{where}: bad cond term {t!r}")
            if t.startswith("item:"):
                iid = t[5:].split(">=")[0]
                if iid not in ITEMS:
                    err(f"{where}: unknown item in cond {iid}")


def check_script(sc, where):
    if not isinstance(sc, list):
        err(f"{where}: script not list")
        return
    for cmd in sc:
        if not isinstance(cmd, list) or not cmd:
            err(f"{where}: bad cmd {cmd!r}")
            continue
        op = cmd[0]
        if op == "say":
            if len(cmd) < 3:
                err(f"{where}: say without text")
        elif op == "if":
            check_cond(cmd[1], where)
            check_script(cmd[2], where)
            if len(cmd) > 3:
                check_script(cmd[3], where)
        elif op == "choice":
            for label, sub in cmd[1:]:
                check_script(sub, where)
        elif op in ("give", "take"):
            if cmd[1] not in ITEMS:
                err(f"{where}: unknown item {cmd[1]}")
        elif op == "battle":
            if cmd[1] not in TROOPS:
                err(f"{where}: unknown troop {cmd[1]}")
        elif op == "join":
            if cmd[1] not in ACTORS:
                err(f"{where}: unknown actor {cmd[1]}")
        elif op == "shop":
            if cmd[1] not in SHOPS:
                err(f"{where}: unknown shop {cmd[1]}")
        elif op == "warp":
            m = MAPS.get(cmd[1])
            if not m:
                err(f"{where}: unknown warp map {cmd[1]}")
            elif not walk(m, cmd[2], cmd[3]):
                err(f"{where}: warp target not walkable {cmd}")
        elif op == "quest":
            if cmd[1] not in QUESTS:
                err(f"{where}: unknown quest {cmd[1]}")
        elif op == "ending":
            if cmd[1] not in ENDINGS:
                err(f"{where}: unknown ending {cmd[1]}")
        elif op == "call":
            if cmd[1] not in CALLS:
                err(f"{where}: unknown call {cmd[1]}")
        elif op == "board":
            if cmd[1] not in BOARDS:
                err(f"{where}: unknown board {cmd[1]}")
        elif op in ("flag", "unflag", "gold", "goal", "karma", "heal", "save", "inn", "chapter"):
            pass
        else:
            err(f"{where}: unknown op {op}")


def walk(m, x, y):
    rows = m["rows"]
    if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[0]):
        return False
    return TILES[rows[y][x]][1] == 1


for mid, m in MAPS.items():
    rows = m["rows"]
    W = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != W:
            err(f"{mid}: row {i} length {len(r)} != {W}")
        for ch in r:
            if ch not in TILES:
                err(f"{mid}: unknown tile {ch!r} in row {i}")
    if W < 16 or len(rows) < 12:
        err(f"{mid}: map smaller than viewport")
    ids = set()
    for e in m["ents"]:
        if e["id"] in ids:
            err(f"{mid}: duplicate ent id {e['id']}")
        ids.add(e["id"])
        if not walk(m, e["x"], e["y"]) and e["sprite"] not in ("seal", "seal404"):
            err(f"{mid}: ent {e['id']} on blocked tile at {e['x']},{e['y']} ({rows[e['y']][e['x']]})")
        if "show" in e:
            check_cond(e["show"], f"{mid}.{e['id']}.show")
        if "script" in e:
            check_script(e["script"], f"{mid}.{e['id']}")
        if "chest" in e and e["chest"].get("item") and e["chest"]["item"] not in ITEMS:
            err(f"{mid}.{e['id']}: chest unknown item")
    for w in m["warps"]:
        x, y, tm, tx, ty, d = w
        if tm not in MAPS:
            err(f"{mid}: warp to unknown map {tm}")
            continue
        if not walk(m, x, y):
            err(f"{mid}: warp source not walkable {w}")
        if not walk(MAPS[tm], tx, ty):
            err(f"{mid}: warp target not walkable {w}")
    for a in m["auto"]:
        check_cond(a["cond"], f"{mid}.auto")
        check_script(a["script"], f"{mid}.auto")
    if "enc" in m:
        for t, wgt in m["enc"]["troops"]:
            if t not in TROOPS:
                err(f"{mid}: unknown troop {t}")
check_script(GAME["start"]["script"], "start")
for _bid, _b in BOARDS.items():
    for _i, _p in enumerate(_b["posts"]):
        if "cond" in _p:
            check_cond(_p["cond"], f"board {_bid}#{_i}")
_skit_ids = set()
for _sk in SKITS:
    if _sk["id"] in _skit_ids:
        err(f"skit dup {_sk['id']}")
    _skit_ids.add(_sk["id"])
    check_cond(_sk["cond"], "skit " + _sk["id"])
    check_script(_sk["script"], "skit " + _sk["id"])
for _t in TRAVEL:
    if _t["map"] not in MAPS or not walk(MAPS[_t["map"]], _t["x"], _t["y"]):
        err(f"travel point bad {_t}")
    if "cond" in _t:
        check_cond(_t["cond"], "travel")
for k, sc in CALLS.items():
    check_script(sc, "call." + k)
for tid, tr in TROOPS.items():
    for e in tr:
        if e not in ENEMIES:
            err(f"troop {tid}: unknown enemy {e}")
for eid, e in ENEMIES.items():
    for sk, wgt in e["ai"]["pattern"]:
        if sk not in SKILLS:
            err(f"enemy {eid}: unknown skill {sk}")
    for key in ("every", "low"):
        if key in e["ai"] and e["ai"][key][1] not in SKILLS:
            err(f"enemy {eid}: unknown {key} skill")
for aid, a in ACTORS.items():
    for lv, sk in a["skills"]:
        if sk not in SKILLS:
            err(f"actor {aid}: unknown skill {sk}")
    for slot, iid in a["equip"].items():
        if iid and iid not in ITEMS:
            err(f"actor {aid}: unknown equip {iid}")
for sid, lst in SHOPS.items():
    for i in lst:
        if i not in ITEMS:
            err(f"shop {sid}: unknown item {i}")

# 可達性：從每個入口 BFS，檢查所有實體旁邊、傳送點是否到得了
entries = {mid: [] for mid in MAPS}
for mid, m in MAPS.items():
    for x, y, tm, tx, ty, d in m["warps"]:
        entries[tm].append((tx, ty))
entries["village"].append((GAME["start"]["x"], GAME["start"]["y"]))
entries["fgate"].append((3, 14))
entries["port"].append((7, 11))
entries["village"].append((13, 5))
for mid, m in MAPS.items():
    rows = m["rows"]
    H, W = len(rows), len(rows[0])
    # 只把「一直存在」（沒有 show 條件）的實體當作障礙
    solid = {(e["x"], e["y"]) for e in m["ents"] if "show" not in e}
    seen = set()
    dq = deque(entries[mid])
    for p0 in entries[mid]:
        seen.add(p0)
    while dq:
        x, y = dq.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H and (nx, ny) not in seen and walk(m, nx, ny) and (nx, ny) not in solid:
                seen.add((nx, ny))
                dq.append((nx, ny))
    for e in m["ents"]:
        adj = [(e["x"] + dx, e["y"] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        # 隔著櫃台也算
        if not any(a in seen for a in adj):
            err(f"{mid}: ent {e['id']} at {e['x']},{e['y']} not reachable")
    for w in m["warps"]:
        if (w[0], w[1]) not in seen:
            adj = [(w[0] + dx, w[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if not any(a in seen for a in adj):
                err(f"{mid}: warp {w[:3]} not reachable")
    if not entries[mid]:
        warns.append(f"{mid}: no entry")

if warns:
    print("WARN:\n  " + "\n  ".join(warns))
if errors:
    print("ERRORS:\n  " + "\n  ".join(errors))
    sys.exit(1)

with open(OUT, "w", encoding="utf-8") as fp:
    json.dump(GAME, fp, ensure_ascii=False, separators=(",", ":"))
print("ok:", OUT, "maps", len(MAPS), "ents", sum(len(m["ents"]) for m in MAPS.values()))
