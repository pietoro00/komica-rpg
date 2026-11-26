# 《糟糕島物語》資料庫：角色、技能、道具、怪物、敵群、商店、任務
# 由 build_content.py 匯入，輸出成 game.json

ELEMENTS = {"phys": "物理", "fire": "炎上", "ice": "冷場", "thunder": "暴雷", "holy": "神串", "dark": "黑歷史"}

STATUSES = {
    "burn": {"name": "炎上", "color": "#ff7a3a"},
    "silence": {"name": "sage", "color": "#b48cff"},
    "confuse": {"name": "被釣", "color": "#4ad0a0"},
    "sleep": {"name": "潛水", "color": "#7fb2f0"},
    "atkUp": {"name": "攻↑", "color": "#ffd54a"},
    "defUp": {"name": "防↑", "color": "#9ad0ff"},
    "atkDown": {"name": "攻↓", "color": "#c08080"},
    "defDown": {"name": "防↓", "color": "#a090b0"},
    "taunt": {"name": "挑釁", "color": "#ff5a5a"},
    "counter": {"name": "誘餌", "color": "#2ad0d0"},
    "hidden": {"name": "404", "color": "#c0c0cc"},
}

# 角色：基礎值 + 每級成長；skills = [[習得等級, 技能]]
ACTORS = {
    "hero": {
        "name": "無名氏", "sprite": "hero", "joinLevel": 1,
        "base": {"hp": 46, "mp": 10, "atk": 10, "def": 7, "mag": 6, "spd": 8},
        "growth": {"hp": 10, "mp": 2.2, "atk": 2.4, "def": 1.8, "mag": 1.6, "spd": 1.4},
        "skills": [[1, "push"], [3, "reply"], [6, "multi"], [10, "holy"], [14, "cheer"], [18, "nameless"], [23, "last"]],
        "equip": {"weapon": "kb0", "armor": "ar0", "acc": None},
        "wtypes": ["sword"], "atypes": ["light", "heavy"],
    },
    "sage": {
        "name": "莎吉", "sprite": "sage", "joinLevel": 6,
        "base": {"hp": 32, "mp": 18, "atk": 4, "def": 4, "mag": 11, "spd": 9},
        "growth": {"hp": 6.8, "mp": 3.6, "atk": 1.1, "def": 1.3, "mag": 2.7, "spd": 1.6},
        "skills": [[1, "flame"], [1, "chill"], [5, "sage"], [8, "spark"], [12, "age"], [15, "firestorm"], [20, "freeze"]],
        "equip": {"weapon": "pen1", "armor": "ar1", "acc": None},
        "wtypes": ["pen"], "atypes": ["light"],
    },
    "gag": {
        "name": "阿梗", "sprite": "gag", "joinLevel": 11,
        "base": {"hp": 38, "mp": 14, "atk": 7, "def": 6, "mag": 8, "spd": 12},
        "growth": {"hp": 8.2, "mp": 2.8, "atk": 1.8, "def": 1.5, "mag": 2.0, "spd": 2.0},
        "skills": [[1, "www"], [1, "calm"], [9, "bait"], [11, "follow"], [14, "meme"], [19, "song"]],
        "equip": {"weapon": "pen2", "armor": "ar2", "acc": None},
        "wtypes": ["pen"], "atypes": ["light"],
    },
    "del": {
        "name": "戴爾", "sprite": "del", "joinLevel": 15,
        "base": {"hp": 60, "mp": 8, "atk": 11, "def": 11, "mag": 3, "spd": 5},
        "growth": {"hp": 11.5, "mp": 1.6, "atk": 2.3, "def": 2.4, "mag": 0.8, "spd": 1.1},
        "skills": [[1, "taunt"], [1, "delete"], [12, "guard"], [14, "block"], [17, "rule"], [22, "ban"]],
        "equip": {"weapon": "kb3", "armor": "hv2", "acc": None},
        "wtypes": ["sword"], "atypes": ["light", "heavy"],
    },
}

# 技能
#  kind: phys / mag / heal / revive / buff / debuff / cure / special
#  target: enemy / enemies / random3 / ally / allies / self / deadAlly
S = {}


def sk(id, name, mp, target, kind, desc, **kw):
    d = {"name": name, "mp": mp, "target": target, "kind": kind, "desc": desc}
    d.update(kw)
    S[id] = d


# --- 無名氏 ---
sk("push", "推文斬", 3, "enemy", "phys", "用力推一下。1.5 倍物理傷害。", power=1.5)
sk("reply", "回應", 4, "ally", "heal", "溫暖的回應。回復一名同伴的 HP。", base=28, power=1.3, field=True)
sk("multi", "連續回應", 6, "random3", "phys", "隨機攻擊敵人 3 次。", power=0.75)
sk("holy", "神串之光", 9, "enemy", "mag", "神串屬性魔法。", base=22, power=1.9, elem="holy")
sk("cheer", "全體推", 10, "allies", "buff", "全隊攻擊力提升 3 回合。", status="atkUp", turns=3)
sk("nameless", "無名之劍", 16, "enemy", "phys", "沒有名字的一劍。神串屬性 2.8 倍。", power=2.8, elem="holy")
sk("last", "最後的回應", 30, "allies", "heal", "全隊大幅回復，並讓倒下的同伴復活。", base=150, power=2.0, revive=True, field=True)
# --- 莎吉 ---
sk("flame", "炎上術", 4, "enemy", "mag", "炎上屬性魔法。", base=12, power=1.5, elem="fire")
sk("chill", "冷場術", 4, "enemy", "mag", "冷場屬性魔法。", base=12, power=1.5, elem="ice")
sk("sage", "sage", 5, "enemy", "debuff", "讓敵人安靜下來（sage：無法使用技能）。", status="silence", chance=85, turns=3)
sk("spark", "暴雷術", 9, "enemies", "mag", "對全體敵人造成暴雷屬性傷害。", base=10, power=1.15, elem="thunder")
sk("age", "age", 15, "deadAlly", "revive", "把倒下的同伴推回來。以一半 HP 復活。", rate=0.5, field=True)
sk("firestorm", "炎上風暴", 14, "enemies", "mag", "全體炎上魔法。", base=26, power=1.5, elem="fire")
sk("freeze", "絕對冷場", 22, "enemies", "mag", "全體冷場魔法，有機率讓敵人潛水。", base=42, power=2.0, elem="ice", status="sleep", chance=20, turns=2)
# --- 阿梗 ---
sk("www", "wwww", 8, "allies", "heal", "笑聲回復全隊 HP。", base=24, power=0.9, field=True)
sk("calm", "冷靜一下", 5, "allies", "cure", "解除全隊的炎上、sage、被釣、潛水。", field=True)
sk("bait", "反釣魚", 6, "enemy", "debuff", "讓敵人被釣（混亂）。", status="confuse", chance=75, turns=3)
sk("follow", "跟風", 10, "allies", "buff", "大家一起跟風！全隊攻擊力提升。", status="atkUp", turns=3)
sk("meme", "梗圖轟炸", 12, "enemies", "mag", "對全體敵人造成黑歷史屬性傷害。", base=20, power=1.35, elem="dark")
sk("song", "肥宅快樂歌", 22, "allies", "heal", "全隊大幅回復 HP。", base=85, power=1.7, field=True)
# --- 戴爾 ---
sk("taunt", "挑釁", 3, "self", "buff", "吸引敵人的攻擊 3 回合。", status="taunt", turns=3)
sk("delete", "刪除", 6, "enemy", "phys", "1.4 倍物理傷害。HP 低於 30% 的一般敵人會被直接刪除。", power=1.4, fx="delete")
sk("guard", "鐵壁", 8, "allies", "buff", "全隊防禦力提升 3 回合。", status="defUp", turns=3)
sk("block", "封鎖", 6, "enemy", "debuff", "降低敵人攻擊力。", status="atkDown", chance=90, turns=3)
sk("rule", "版規之劍", 10, "enemy", "phys", "神串屬性 2.2 倍物理傷害。", power=2.2, elem="holy")
sk("ban", "永久封鎖", 18, "enemies", "phys", "對全體敵人 1.3 倍物理傷害，並降低攻擊力。", power=1.3, status="atkDown", chance=60, turns=3)

# --- 敵人技能 ---
sk("e_attack", "攻擊", 0, "enemy", "phys", "", power=1.0)
sk("e_bite", "撕咬", 0, "enemy", "phys", "", power=1.4)
sk("e_spam", "洗版", 0, "enemies", "phys", "", power=0.6)
sk("e_splash", "灌水", 0, "enemy", "mag", "", base=6, power=1.0, elem="ice")
sk("e_pinch", "夾擊", 0, "enemy", "phys", "", power=1.2, status="defDown", chance=30, turns=3)
sk("e_sting", "潛水觸手", 0, "enemy", "mag", "", base=6, power=1.0, elem="thunder", status="sleep", chance=25, turns=2)
sk("e_summon", "分裂", 0, "self", "special", "", fx="summon", summon="worm")
sk("e_recruit", "貼名牌", 0, "enemy", "phys", "", power=0.8, status="silence", chance=30, turns=2)
sk("e_spoil", "暴雷", 0, "enemy", "mag", "", base=10, power=1.0, elem="thunder", status="silence", chance=35, turns=2)
sk("e_peck", "劇透啄", 0, "enemy", "phys", "", power=1.15)
sk("e_netabite", "捏他咬", 0, "enemy", "phys", "", power=1.0, status="silence", chance=25, turns=2)
sk("e_netawave", "捏他波", 0, "enemies", "mag", "", base=14, power=0.9, elem="dark", status="silence", chance=25, turns=2)
sk("e_foresee", "預知捏他", 0, "enemies", "debuff", "", status="silence", chance=55, turns=2, first=True)
sk("e_follow", "跟風", 0, "allies", "buff", "", status="atkUp", turns=3)
sk("e_trash", "嘴砲", 0, "enemy", "phys", "", power=0.7, status="defDown", chance=60, turns=3)
sk("e_troll", "釣魚", 0, "enemy", "debuff", "", status="confuse", chance=55, turns=2)
sk("e_trollall", "大釣魚", 0, "enemies", "debuff", "", status="confuse", chance=35, turns=2)
sk("e_flame", "炎上", 0, "enemy", "mag", "", base=14, power=1.2, elem="fire", status="burn", chance=40, turns=3)
sk("e_flameall", "大炎上", 0, "enemies", "mag", "", base=16, power=0.95, elem="fire", status="burn", chance=30, turns=3)
sk("e_lure", "拋出誘餌", 0, "self", "buff", "", status="counter", turns=1, first=True)
sk("e_charge", "衝鋒", 0, "enemy", "phys", "", power=1.6)
sk("e_block", "封鎖", 0, "enemy", "debuff", "", status="atkDown", chance=70, turns=3)
sk("e_haunt", "作祟", 0, "enemy", "mag", "", base=14, power=1.2, elem="dark", status="sleep", chance=25, turns=2)
sk("e_hide", "404", 0, "self", "buff", "", status="hidden", turns=1, first=True)
sk("e_framebite", "畫框咬", 0, "enemy", "phys", "", power=1.5)
sk("e_paint", "潑顏料", 0, "enemies", "mag", "", base=10, power=0.8, elem="ice")
sk("e_blank", "空白", 0, "enemies", "mag", "", base=20, power=1.0, elem="dark")
sk("e_tag", "貼名牌", 0, "enemy", "debuff", "", status="silence", chance=60, turns=2)
sk("e_tagall", "全員實名", 0, "enemies", "debuff", "", status="defDown", chance=50, turns=3, status2="silence", chance2=35)
sk("e_stare", "監視", 0, "enemy", "debuff", "", status="defDown", chance=80, turns=3)
sk("e_iceray", "凝視光線", 0, "enemy", "mag", "", base=20, power=1.2, elem="ice")
sk("e_rally", "重整旗鼓", 0, "self", "buff", "", status="atkUp", turns=4, status2="defUp")
sk("e_oath", "實名之誓", 0, "self", "special", "", fx="healself", rate=0.3)
sk("e_icelance", "真名之槍", 0, "enemy", "mag", "", base=36, power=1.9, elem="ice")
sk("e_blizzard", "實名冰牢", 0, "enemies", "mag", "", base=28, power=1.25, elem="ice", status="sleep", chance=15, turns=2)
sk("e_malice", "惡意", 0, "enemy", "mag", "", base=24, power=1.5, elem="dark", status="burn", chance=25, turns=3)
sk("e_explode", "爆破", 0, "enemies", "special", "", fx="explode", base=120)
sk("e_darknova", "匿名之惡", 0, "enemies", "mag", "", base=36, power=1.35, elem="dark")
sk("e_devour", "吞噬回應", 0, "enemy", "phys", "", power=1.3, fx="drain")
sk("e_absorb", "吸收惡意", 0, "self", "buff", "", status="atkUp", turns=5, status2="defUp")
sk("e_bigbang", "大爆破", 0, "enemies", "mag", "", base=60, power=1.5, elem="fire")
sk("e_tentacle", "觸手", 0, "enemies", "phys", "", power=0.85)
sk("e_whirl", "漩渦", 0, "enemies", "mag", "", base=30, power=1.2, elem="ice", status="confuse", chance=30, turns=2)
sk("e_tsunami", "沉船大浪", 0, "enemies", "mag", "", base=70, power=1.7, elem="ice")
SKILLS = S

# 道具
I = {}


def it(id, name, type, price, desc, **kw):
    d = {"name": name, "type": type, "price": price, "desc": desc}
    d.update(kw)
    I[id] = d


it("noodle", "泡麵", "use", 12, "HP 回復 50。島民的主食。", target="ally", heal=50)
it("noodle2", "豪華泡麵", "use", 45, "HP 回復 160。加了蛋和肉片。", target="ally", heal=160)
it("chicken", "大雞排", "use", 130, "HP 回復 450。比臉還大。", target="ally", heal=450)
it("bento", "宅配便當", "use", 280, "全隊 HP 回復 300。", target="allies", heal=300)
it("cola", "肥宅快樂水", "use", 30, "MP 回復 25。", target="ally", mp=25)
it("boba", "珍珠奶茶", "use", 95, "MP 回復 70。", target="ally", mp=70)
it("revive", "神回應", "use", 110, "讓倒下的同伴以一半 HP 復活。", target="deadAlly", revive=0.5)
it("tea", "冷靜茶", "use", 20, "解除炎上、sage、被釣、潛水。", target="ally", cure=True)
it("cracker", "鞭炮", "use", 60, "戰鬥中使用：對全體敵人造成 90 點炎上傷害。", target="enemies", damage=90, elem="fire", battleOnly=True)
# 武器：sword（無名氏、戴爾）/ pen（莎吉、阿梗）
it("kb0", "木鍵盤", "weapon", 0, "練習用的木製鍵盤。", wtype="sword", stats={"atk": 4})
it("kb1", "機械鍵盤", "weapon", 120, "清脆的手感。", wtype="sword", stats={"atk": 11})
it("kb2", "青軸之劍", "weapon", 480, "每一擊都喀喀作響。", wtype="sword", stats={"atk": 20})
it("kb3", "紅軸之刃", "weapon", 1300, "安靜又迅速。", wtype="sword", stats={"atk": 31})
it("kb4", "光軸聖劍", "weapon", 3400, "以光速觸發的聖劍。", wtype="sword", stats={"atk": 44})
it("kb5", "版主之劍", "weapon", 0, "歷代版主傳承的劍。", wtype="sword", stats={"atk": 58, "def": 5})
it("kb6", "島主之劍", "weapon", 0, "用五片古串碎片打造。這座島最初的回應。", wtype="sword", stats={"atk": 74, "mag": 12, "spd": 6})
it("pen0", "原子筆", "weapon", 0, "隨處可見的原子筆。", wtype="pen", stats={"atk": 2, "mag": 4})
it("pen1", "繪圖筆", "weapon", 110, "繪師愛用的筆。", wtype="pen", stats={"atk": 3, "mag": 10})
it("pen2", "數位板之杖", "weapon", 460, "壓力感應 8192 階。", wtype="pen", stats={"atk": 5, "mag": 19})
it("pen3", "麥克風杖", "weapon", 1250, "實況主的武器。", wtype="pen", stats={"atk": 8, "mag": 29})
it("pen4", "神繪師之筆", "weapon", 3300, "一筆就能畫出神圖。", wtype="pen", stats={"atk": 10, "mag": 42})
it("pen5", "精華之杖", "weapon", 0, "沉睡在精華區的杖。", wtype="pen", stats={"atk": 12, "mag": 56, "mp": 20})
# 防具：light（全員）/ heavy（無名氏、戴爾）
it("ar0", "肥宅 T 恤", "armor", 0, "穿到起毛球的 T 恤。", atype="light", stats={"def": 3})
it("ar1", "連帽外套", "armor", 100, "帽子拉起來就是匿名。", atype="light", stats={"def": 8})
it("ar2", "痛衣", "armor", 420, "印著老婆的 T 恤。精神防禦力很高。", atype="light", stats={"def": 14, "mag": 2})
it("ar3", "冷氣毯", "armor", 1150, "夏天吹冷氣蓋棉被。", atype="light", stats={"def": 22})
it("ar4", "被窩護甲", "armor", 3000, "全世界最安全的地方。", atype="light", stats={"def": 31, "hp": 30})
it("ar5", "精華之衣", "armor", 0, "織入神串的衣服。", atype="light", stats={"def": 42, "mag": 6})
it("hv1", "紙箱鎧", "armor", 150, "躲在紙箱裡就沒人看得到你。", atype="heavy", stats={"def": 12, "spd": -1})
it("hv2", "鍵帽鎧", "armor", 560, "用一萬顆鍵帽拼成的鎧甲。", atype="heavy", stats={"def": 21})
it("hv3", "伺服器機殼", "armor", 3200, "比爆破還硬。", atype="heavy", stats={"def": 34, "spd": -2})
it("hv4", "版主重甲", "armor", 0, "歷代版主騎士的重甲。", atype="heavy", stats={"def": 48, "hp": 60})
# 飾品
it("acc_cat", "貓耳髮箍", "acc", 0, "速度 +8。喵咪的謝禮。", stats={"spd": 8})
it("acc_mask", "防捏他眼罩", "acc", 400, "防止 sage（不會被暴雷氣到說不出話）。", immune=["silence"])
it("acc_head", "降噪耳機", "acc", 500, "防止潛水（睡眠）。", immune=["sleep"])
it("acc_ring", "抗炎上手環", "acc", 700, "防止炎上。", immune=["burn"])
it("acc_line", "理智線", "acc", 900, "防止被釣（混亂）。", immune=["confuse"])
it("acc_fat", "肥宅之戒", "acc", 1800, "HP +80。", stats={"hp": 80})
it("acc_charm", "精華護符", "acc", 0, "攻擊、防禦、魔力、速度各 +6。", stats={"atk": 6, "def": 6, "mag": 6, "spd": 6})
it("acc_tooth", "沉船之牙", "acc", 0, "攻擊 +16、魔力 +16。所有被遺忘的串的力量。", stats={"atk": 16, "mag": 16})
# 重要道具
it("tag", "奇怪的名牌", "key", 0, "在沉船灘撿到的空白名牌。")
it("scissors", "去背剪刀", "key", 0, "字幕組的剪刀。剪得掉名牌。")
it("stone1", "新番之石", "key", 0, "精華石之一。閃著期待的光。")
it("stone2", "惡搞之石", "key", 0, "精華石之一。摸起來會想笑。")
it("stone3", "掛圖之石", "key", 0, "精華石之一。表面映著無數張圖。")
it("frag", "古串碎片", "key", 0, "很久以前的神串碎片。精華區守門人在收集。")
it("thumbA", "失落的縮圖 A", "key", 0, "一張夕陽的圖。")
it("thumbB", "失落的縮圖 B", "key", 0, "一張貓咪的圖。")
it("thumbC", "失落的縮圖 C", "key", 0, "一張很多人一起笑的圖。")
ITEMS = I

# 怪物
E = {}


def en(id, name, sprite, hp, atk, df, mag, spd, exp, gold, ai, **kw):
    d = {"name": name, "sprite": sprite, "hp": hp, "atk": atk, "def": df, "mag": mag, "spd": spd,
         "exp": exp, "gold": gold, "ai": ai}
    d.update(kw)
    E[id] = d


# 第一章
en("worm", "洗版蟲", "worm", 18, 11, 3, 2, 6, 5, 4, {"pattern": [["e_attack", 3], ["e_spam", 1]]}, weak=["fire"], drops=[["noodle", 10]])
en("slime", "灌水史萊姆", "slime_blue", 22, 10, 5, 8, 5, 6, 5, {"pattern": [["e_attack", 2], ["e_splash", 1]]}, weak=["fire", "thunder"], resist=["ice"])
en("crab", "沉船蟹", "crab", 34, 14, 10, 2, 4, 10, 9, {"pattern": [["e_attack", 2], ["e_pinch", 1]]}, weak=["thunder"], resist=["ice"], drops=[["tea", 15]])
en("jelly", "潛水水母", "jelly", 24, 8, 4, 11, 9, 9, 8, {"pattern": [["e_sting", 2], ["e_attack", 1]]}, weak=["thunder", "fire"])
en("recruit", "名牌見習兵", "soldier", 42, 13, 8, 4, 6, 14, 18, {"pattern": [["e_attack", 3], ["e_recruit", 1]]}, weak=["dark"])
en("worm_king", "洗版蟲王", "worm_king", 230, 14, 7, 8, 7, 60, 120,
   {"pattern": [["e_attack", 3], ["e_spam", 2]], "every": [3, "e_summon", "洗版蟲王的身體開始蠕動……（下回合會分裂出洗版蟲！）"]},
   weak=["fire"], boss=True, size="l")
# 第二章
en("mush", "暴雷菇", "mush", 85, 20, 10, 17, 6, 22, 16, {"pattern": [["e_attack", 2], ["e_spoil", 2]]}, weak=["fire"], drops=[["tea", 15]])
en("crow", "劇透鴉", "crow", 70, 24, 8, 4, 14, 21, 15, {"pattern": [["e_peck", 3], ["e_attack", 1]]}, weak=["thunder"])
en("bat_neta", "捏他蝙蝠", "bat_neta", 78, 21, 9, 15, 12, 23, 17, {"pattern": [["e_attack", 2], ["e_netabite", 2]]}, weak=["holy"], drops=[["cola", 10]])
en("demon", "捏他魔", "demon", 980, 27, 14, 26, 11, 120, 420,
   {"pattern": [["e_attack", 2], ["e_spoil", 2], ["e_netawave", 1]], "every": [4, "e_foresee", "捏他魔翻到了劇本的下一頁……（下回合會預知捏他！）"]},
   weak=["holy"], resist=["dark"], boss=True, size="l")
# 第三章
en("sheep", "跟風羊", "sheep", 165, 33, 15, 6, 9, 46, 30, {"pattern": [["e_attack", 3], ["e_follow", 1]]}, weak=["fire"])
en("mouth", "嘴砲兵", "mouth", 150, 30, 13, 28, 10, 48, 34, {"pattern": [["e_trash", 2], ["e_attack", 1], ["e_troll", 1]]}, weak=["holy"], drops=[["noodle2", 8]])
en("fox", "炎上狐", "fox", 155, 35, 14, 30, 15, 50, 32, {"pattern": [["e_attack", 2], ["e_flame", 2]]}, weak=["ice"], resist=["fire"], immune=["burn"])
en("fish", "釣魚魚", "fish", 140, 31, 13, 22, 12, 46, 36, {"pattern": [["e_attack", 2], ["e_troll", 1]]}, weak=["thunder"], drops=[["tea", 15]])
en("troll_b", "釣魚王", "troll", 1850, 38, 18, 34, 15, 250, 760,
   {"pattern": [["e_attack", 3], ["e_trollall", 1], ["e_flameall", 1]], "every": [3, "e_lure", "釣魚王拋出了誘餌！（這回合用物理攻擊會被反擊！）"]},
   weak=["holy"], boss=True, size="l")
en("del_e", "刪文騎士 戴爾", "del", 2000, 44, 30, 10, 9, 150, 0,
   {"pattern": [["e_attack", 3], ["e_charge", 1], ["e_block", 1]]}, boss=True, size="l", yieldAt=0.3)
# 第四章
en("ghost", "404 幽靈", "ghost", 300, 40, 18, 46, 14, 95, 50, {"pattern": [["e_haunt", 2], ["e_attack", 1]]}, weak=["holy"], resist=["phys"])
en("mimic", "畫框怪", "mimic", 460, 54, 28, 10, 8, 120, 110, {"pattern": [["e_framebite", 2], ["e_attack", 1]]}, weak=["thunder"], drops=[["revive", 25]])
en("slime_paint", "顏料史萊姆", "slime_paint", 290, 38, 18, 42, 10, 90, 55, {"pattern": [["e_attack", 1], ["e_paint", 1]]}, weak=["ice"])
en("bat_thumb", "縮圖蝠", "bat_thumb", 270, 44, 16, 8, 20, 92, 52, {"pattern": [["e_attack", 2], ["e_bite", 1]]}, weak=["fire"])
en("phantom", "失落之圖", "phantom", 2800, 46, 24, 52, 16, 350, 1300,
   {"pattern": [["e_haunt", 2], ["e_attack", 1], ["e_blank", 1]], "every": [2, "e_hide", "失落之圖的輪廓開始模糊……（下回合會進入 404 狀態！用神串屬性才打得中）"]},
   weak=["holy"], resist=["dark"], boss=True, size="l")
# 第五章
en("soldier", "名牌兵", "soldier", 680, 62, 34, 30, 14, 150, 90, {"pattern": [["e_attack", 2], ["e_tag", 1]]}, weak=["dark"], drops=[["noodle2", 12]])
en("dog", "實名犬", "dog", 600, 66, 28, 6, 22, 140, 75, {"pattern": [["e_bite", 2], ["e_attack", 2]]}, weak=["fire"])
en("eye", "監視之眼", "eye", 540, 46, 26, 60, 18, 155, 95, {"pattern": [["e_stare", 2], ["e_iceray", 2]]}, weak=["dark"], drops=[["boba", 10]])
en("general_b", "名牌騎士團長", "general", 4500, 66, 38, 30, 15, 450, 2000,
   {"pattern": [["e_attack", 2], ["e_charge", 2], ["e_tagall", 1]], "low": [0.5, "e_rally", "名牌騎士團長怒吼：「秩序不會倒下！」"]},
   weak=["dark"], boss=True, size="l")
en("snow_b", "署名者 雪見", "snow", 4000, 50, 34, 62, 22, 550, 0,
   {"pattern": [["e_icelance", 2], ["e_blizzard", 1], ["e_tagall", 1]], "low": [0.35, "e_oath", "雪見：「……我不能在這裡倒下！」"]},
   weak=["dark"], resist=["ice"], boss=True, size="l")
# 第六章
en("slime_dark", "惡意塊", "slime_dark", 1000, 74, 36, 72, 16, 240, 130, {"pattern": [["e_attack", 1], ["e_malice", 2]]}, weak=["holy"])
en("bomb", "爆破彈", "bomb", 760, 60, 48, 60, 10, 250, 140, {"pattern": [["e_attack", 1]], "every": [3, "e_explode", "爆破彈的引信燒得越來越短……！"]}, weak=["ice"])
en("faceless_man", "無貌兵", "faceless_man", 1100, 84, 40, 40, 20, 270, 150, {"pattern": [["e_attack", 2], ["e_devour", 1]]}, weak=["holy"], drops=[["chicken", 8]])
en("blackhist", "黑歷史", "blackhist", 900, 62, 32, 80, 18, 255, 135, {"pattern": [["e_haunt", 2], ["e_blank", 1]]}, weak=["holy"], resist=["phys"])
en("faceless_b", "無貌者", "faceless", 9200, 76, 42, 78, 22, 0, 0,
   {"pattern": [["e_malice", 2], ["e_attack", 2], ["e_devour", 1], ["e_trollall", 1]], "every": [4, "e_darknova", "無貌者的身體裡湧出無數張沒有臉的臉……（下回合「匿名之惡」！）"],
    "low": [0.5, "e_absorb", "無貌者吸收了全島的惡意，身體膨脹起來！"]},
   weak=["holy"], resist=["dark"], boss=True, size="l")
en("faceless_t", "無貌者‧真形", "faceless_true", 7800, 80, 44, 82, 24, 0, 0,
   {"pattern": [["e_malice", 2], ["e_darknova", 1], ["e_devour", 1], ["e_tagall", 1]], "every": [4, "e_bigbang", "主機之心劇烈震動……（下回合「大爆破」！記得防禦或補血！）"]},
   weak=["holy"], resist=["dark"], immune=["confuse", "sleep", "silence"], boss=True, size="l")
en("kraken_b", "沉船之主", "kraken", 11000, 90, 46, 86, 18, 9000, 6000,
   {"pattern": [["e_tentacle", 2], ["e_whirl", 1], ["e_attack", 1]], "every": [5, "e_tsunami", "海面開始退潮……（下回合「沉船大浪」！）"]},
   weak=["thunder"], resist=["ice"], immune=["confuse", "sleep"], boss=True, size="l")
ENEMIES = E

TROOPS = {
    "f1a": ["worm", "worm"], "f1b": ["worm", "slime"], "f1c": ["slime", "slime"], "f1d": ["worm", "worm", "worm"], "f1e": ["slime"],
    "b1a": ["crab"], "b1b": ["jelly", "jelly"], "b1c": ["crab", "worm"], "b1d": ["jelly", "worm", "worm"], "b1e": ["crab", "jelly"],
    "p2a": ["mush", "mush"], "p2b": ["crow", "crow"], "p2c": ["bat_neta", "mush"], "p2d": ["crow", "bat_neta"], "p2e": ["mush"],
    "n2a": ["mush", "bat_neta", "crow"], "n2b": ["bat_neta", "bat_neta"], "n2c": ["mush", "mush", "mush"], "n2d": ["crow", "crow", "crow"],
    "v3a": ["sheep", "sheep"], "v3b": ["mouth", "fox"], "v3c": ["sheep", "sheep", "sheep"], "v3d": ["fox", "fox"], "v3e": ["mouth", "fish"],
    "g4a": ["ghost", "ghost"], "g4b": ["mimic"], "g4c": ["slime_paint", "bat_thumb"], "g4d": ["ghost", "bat_thumb", "bat_thumb"], "g4e": ["slime_paint", "slime_paint"],
    "r5a": ["soldier", "dog"], "r5b": ["eye", "eye"], "r5c": ["soldier", "soldier"], "r5d": ["dog", "dog", "eye"], "r5e": ["soldier", "eye"],
    "a6a": ["slime_dark", "slime_dark"], "a6b": ["bomb", "faceless_man"], "a6c": ["blackhist", "blackhist"], "a6d": ["faceless_man", "faceless_man"], "a6e": ["bomb", "bomb", "slime_dark"],
    "boss1": ["worm_king"], "raid": ["recruit", "recruit"], "boss2": ["demon"], "boss3": ["fish", "troll_b", "fish"],
    "duel": ["del_e"], "boss4": ["phantom"], "mimic1": ["mimic"], "gate": ["soldier", "eye", "soldier"],
    "boss5a": ["general_b"], "boss5b": ["snow_b"], "final1": ["faceless_b"], "final2": ["faceless_t"], "kraken": ["kraken_b"],
}

SHOPS = {
    "village_item": ["noodle", "tea", "cola"],
    "village_gear": ["kb1", "pen1", "ar1", "hv1"],
    "shinban": ["noodle", "noodle2", "cola", "tea", "revive", "kb2", "pen2", "ar2", "hv2", "acc_mask"],
    "port": ["noodle2", "cola", "boba", "tea", "revive", "cracker", "kb3", "pen3", "ar3", "acc_head", "acc_ring", "acc_line"],
    "fortress": ["noodle2", "chicken", "boba", "revive", "bento", "tea", "kb4", "pen4", "ar4", "hv3", "acc_fat"],
    "village_late": ["noodle2", "chicken", "boba", "revive", "bento", "tea", "cracker"],
}

QUESTS = {
    "cat": {"name": "走失的喵咪", "desc": "綜合村的貓奴阿姨說，肥宅快樂獸躲在新手串原東北邊的樹叢裡。"},
    "xd": {"name": "外來種", "desc": "新番鎮的島民在嘲笑一個用 XD 的人。"},
    "tags": {"name": "剪掉名牌", "desc": "用去背剪刀，剪掉綜合村三位島民身上的名牌（肥宅大叔、www 哥、老島民）。"},
    "frag": {"name": "古串碎片", "desc": "收集 5 片古串碎片，交給綜合村的精華區守門人。"},
    "prison": {"name": "被實名的島民", "desc": "救出被關在實名要塞裡的 3 位島民。"},
    "kraken": {"name": "沉船之主", "desc": "沉船灘的海底傳來奇怪的聲音……"},
}

# ---- 圖鑑說明 ----
ENEMY_DESC = {
    "worm": "把同一句話貼一萬次的蟲。被炎上一燒就會停。",
    "slime": "不停灌水的史萊姆，回應裡全是「+1」。",
    "crab": "在沉船殘骸上築巢。殼很硬，怕暴雷。",
    "jelly": "平常都在潛水，偶爾浮上來電你一下。",
    "recruit": "實名教團的見習兵。名牌貼得還不太熟練。新手自重。",
    "worm_king": "洗版蟲的女王。身體裡塞滿了重複的回應。",
    "mush": "一碰就會暴雷的菇。被暴雷到會氣到說不出話。",
    "crow": "搶在你看之前，把結局叼走的烏鴉。",
    "bat_neta": "倒掛在新番鎮屋簷下，專門偷聽劇透。",
    "demon": "自稱「已經看過結局」的魔物。翻開的劇本會讓人沉默。",
    "sheep": "只要有一隻往東跑，全部都往東跑。",
    "mouth": "只會嘴砲、討戰的生物。看到請發動島民技能「無視」。",
    "fox": "尾巴一甩，整片谷就炎上了。",
    "fish": "嘴邊永遠掛著誘餌。上鉤你就輸了。",
    "troll_b": "歡樂惡搞版最惡名昭彰的釣魚仔。據說釣過整座島。",
    "del_e": "版主騎士團最後的騎士。劍下從不留情，也從不留下惡意。",
    "ghost": "被刪掉的圖變成的幽靈。物理攻擊常常穿過它。",
    "mimic": "偽裝成名畫的畫框。看到太漂亮的寶箱要小心。",
    "slime_paint": "調色盤打翻變成的史萊姆。怕冷場。",
    "bat_thumb": "縮圖化成的蝙蝠，飛得比點開還快。",
    "phantom": "所有被遺忘的圖聚集而成。只有神串之光能讓它現形。",
    "soldier": "實名教團的主力。名牌一貼，就說不出真心話。",
    "dog": "嗅得到匿名者的氣味。",
    "eye": "監視一切的眼睛。被盯上會讓防禦崩潰。",
    "general_b": "「名字就是秩序」——名牌騎士團的團長。",
    "snow_b": "曾經是綜合版最溫柔的版主。",
    "slime_dark": "匿名者沒說出口的惡意，凝固成了塊。",
    "bomb": "每一次爆破留下的碎片。引信燒完就會爆炸。",
    "faceless_man": "沒有臉的士兵。吞噬回應來壯大自己。",
    "blackhist": "每個人都有的黑歷史。物理攻擊對它沒什麼用。",
    "faceless_b": "所有惡意的集合體。一直躲在別人的聲音裡。",
    "faceless_t": "吸收了主機之心光芒的無貌者。",
    "kraken_b": "所有沉下去、沒有人記得的串的集合。",
}
for _k, _v in ENEMY_DESC.items():
    ENEMIES[_k]["desc"] = _v

# ---- 推量表與合體技 ----
GAUGE = {"hit": 4, "weak": 9, "crit": 6, "hurt": 3, "defend": 6, "ko": 12}
COMBOS = {
    "godthread": {"name": "神串降臨", "desc": "全員一起推！對全體敵人造成大量神串屬性傷害。", "kind": "damage", "atk": 0.8, "mag": 0.8, "elem": "holy"},
    "pushall": {"name": "全島推爆", "desc": "全隊回復 60% HP、復活倒下的同伴、解除異常，並提升攻擊與防禦。", "kind": "support"},
}

# =====================================================================
# 島上的武將與知名人物（以島上流傳的梗為靈感的虛構角色）
# =====================================================================
ITEMS.update({
    # 生日哥
    "cake": {"name": "生日蛋糕", "type": "use", "price": 0, "desc": "全隊 HP 回復 250。今天是誰的生日？每天都是。", "target": "allies", "heal": 250},
    "card": {"name": "祝福卡", "type": "key", "price": 0, "desc": "島民寫給生日哥的生日祝福。收集 4 張交給他。"},
    "acc_party": {"name": "派對帽", "type": "acc", "price": 0, "desc": "HP +60、魔力 +6、速度 +6。不會潛水（睡眠）。生日哥的謝禮。", "stats": {"hp": 60, "mag": 6, "spd": 6}, "immune": ["sleep"]},
    # 照燒貓
    "teri_leg": {"name": "照燒雞腿", "type": "use", "price": 70, "desc": "HP 回復 220。照燒貓的招牌。", "target": "ally", "heal": 220},
    "teri_rice": {"name": "照燒飯糰", "type": "use", "price": 55, "desc": "MP 回復 40。", "target": "ally", "mp": 40},
    "teri_don": {"name": "照燒丼", "type": "use", "price": 160, "desc": "全隊 HP 回復 150。", "target": "allies", "heal": 150},
    "teri_set": {"name": "照燒全家餐", "type": "use", "price": 360, "desc": "全隊 HP 回復 500。祕傳醬汁的力量。", "target": "allies", "heal": 500},
    "sauce": {"name": "祕方材料", "type": "key", "price": 0, "desc": "照燒貓祕傳醬汁的材料。收集 3 個交給他。"},
    "acc_apron": {"name": "照燒圍裙", "type": "acc", "price": 0, "desc": "HP +40、防禦 +10、魔力 +10。不會炎上。照燒的人不怕火。", "stats": {"hp": 40, "def": 10, "mag": 10}, "immune": ["burn"]},
    # 智障神
    "acc_figure": {"name": "限定版模型", "type": "acc", "price": 0, "desc": "攻擊 +8、防禦 +4、魔力 +8。開箱之神的珍藏。", "stats": {"atk": 8, "def": 4, "mag": 8}},
})
SKILLS.update({
    "e_unbox": {"name": "開箱轟炸", "mp": 0, "target": "enemies", "kind": "phys", "desc": "", "power": 0.62},
    "e_mock": {"name": "窮鬼之嘲", "mp": 0, "target": "enemies", "kind": "debuff", "desc": "", "status": "defDown", "chance": 55, "turns": 3},
    "e_limited": {"name": "限定版光輝", "mp": 0, "target": "self", "kind": "buff", "desc": "", "status": "atkUp", "turns": 3},
    "e_figure": {"name": "模型開箱", "mp": 0, "target": "self", "kind": "special", "desc": "", "fx": "summon", "summon": "figure"},
    "e_figkick": {"name": "可動關節踢", "mp": 0, "target": "enemy", "kind": "phys", "desc": "", "power": 1.1},
})
ENEMIES.update({
    "zz_god": {"name": "智障神", "sprite": "zz_battle", "hp": 980, "atk": 25, "def": 13, "mag": 19, "spd": 10, "exp": 130, "gold": 360,
               "ai": {"pattern": [["e_attack", 2], ["e_unbox", 2], ["e_mock", 1]],
                      "every": [4, "e_figure", "智障神撕開了一個新的箱子……（下回合模型會動起來！）"],
                      "low": [0.4, "e_limited", "智障神大喊：「限定版是不會輸的！」"]},
               "weak": ["ice"], "boss": True, "size": "l", "drops": []},
    "figure": {"name": "暴走模型", "sprite": "figure", "hp": 110, "atk": 22, "def": 14, "mag": 0, "spd": 12, "exp": 14, "gold": 10,
               "ai": {"pattern": [["e_attack", 1], ["e_figkick", 1]]}, "weak": ["fire"], "drops": []},
})
ENEMIES["zz_god"]["desc"] = "自稱「開箱之神」的島民。每天在新番捏他版洗開箱文，嘴巴很壞。其實只是想要有人回他一句。最怕被冷場。"
ENEMIES["figure"]["desc"] = "智障神的限定版模型。關節可動，所以會踢人。塑膠做的，怕火。"
TROOPS.update({"zz": ["zz_god"]})
SHOPS.update({
    "teriyaki": ["teri_leg", "teri_rice", "teri_don", "tea"],
    "teriyaki2": ["teri_leg", "teri_rice", "teri_don", "teri_set", "tea"],
})
QUESTS.update({
    "bday": {"name": "今天我生日ㄛ", "desc": "幫綜合村的生日哥收集 4 張祝福卡，辦一場真正的生日派對。（智障神、照燒貓、西瓜哥、塗鴉廚……島上的知名人物都可以問問看）"},
    "teriyaki": {"name": "照燒的祕方", "desc": "照燒貓的祕傳醬汁少了 3 個材料。聽說藏在沉船灘、捏他之森和惡搞谷的寶箱裡。"},
    "zz": {"name": "開箱之神", "desc": "新番鎮的智障神每天洗開箱文、嗆人是窮鬼。打贏他之後，他好像有話想說。"},
})

# =====================================================================
# 島上名人重構（照燒貓、易經廚、生日哥……）與塗鴉角落的塗鴉廚們
# 以島上流傳的梗為靈感的虛構角色；造型、劇情與台詞皆為創作
# =====================================================================
ITEMS.update({
    # 生日哥：派對之後，島民把口頭禪改成各種版本
    "candle": {"name": "生日蠟燭", "type": "use", "price": 0, "desc": "讓倒下的同伴以全部 HP 復活。「今天我復活ㄛ」。", "target": "deadAlly", "revive": 1.0},
    # 照燒貓：不掛名之後的第一份便當
    "nameless_bento": {"name": "無名照燒便當", "type": "use", "price": 0, "desc": "全隊 HP 回復 400、MP 回復 30。沒有掛名的照燒。", "target": "allies", "heal": 400, "mp": 30},
    # 易經廚
    "acc_lot": {"name": "月老籤詩", "type": "acc", "price": 0, "desc": "防禦 +8、魔力 +8、速度 +4。上面寫著：「先問，再說。」", "stats": {"def": 8, "mag": 8, "spd": 4}},
    # 黃毛
    "penhm": {"name": "黃毛的筆", "type": "key", "price": 0, "desc": "一支用到很舊的筆。筆桿上貼著紅色緞帶。"},
    "acc_ribbon": {"name": "紅緞帶髮箍", "type": "acc", "price": 0, "desc": "攻擊 +6、魔力 +12、速度 +5。火跟雷都會比較聽話。", "stats": {"atk": 6, "mag": 12, "spd": 5}},
    # 星芳
    "star": {"name": "星星貼紙", "type": "use", "price": 0, "desc": "全隊 MP 回復 30。星芳自己做的，每一張都是真心的。", "target": "allies", "mp": 30},
    # 外來種
    "tongue": {"name": "毒舌語錄", "type": "use", "price": 0, "desc": "戰鬥中使用：對全體敵人造成 140 點黑歷史傷害。外來種的嘴。", "target": "enemies", "damage": 140, "elem": "dark", "battleOnly": True},
    # 獨眼／雀斑
    "acc_patch": {"name": "封印眼罩", "type": "acc", "price": 0, "desc": "攻擊 +8、速度 +8。不會潛水（睡眠）。其實只是忘了畫另一隻眼睛。", "stats": {"atk": 8, "spd": 8}, "immune": ["sleep"]},
    # 西瓜哥（被獅子老大嘴到回不了嘴之後）
    "melon": {"name": "冰西瓜", "type": "use", "price": 0, "desc": "全隊 HP 回復 200、MP 回復 20。這是真心的，不是反串。", "target": "allies", "heal": 200, "mp": 20},
    # 慕內
    "acc_beanie": {"name": "毛帽", "type": "acc", "price": 0, "desc": "HP +40、防禦 +10、魔力 +10。戴著它畫畫，比較不怕被罵。", "stats": {"hp": 40, "def": 10, "mag": 10}},
})
ENEMIES.update({
    "anti_teri": {"name": "反照燒團員", "sprite": "anti_teri", "hp": 170, "atk": 30, "def": 14, "mag": 20, "spd": 11, "exp": 48, "gold": 40,
                  "ai": {"pattern": [["e_attack", 2], ["e_trash", 2]]}, "weak": ["holy"], "drops": [["tea", 15]],
                  "desc": "自稱「反照燒團」的島民。罵照燒貓罵得比誰都認真，其實沒吃過他的照燒。"},
    "teri_guard": {"name": "照燒親衛隊", "sprite": "teri_guard", "hp": 190, "atk": 32, "def": 16, "mag": 10, "spd": 9, "exp": 50, "gold": 42,
                   "ai": {"pattern": [["e_attack", 3], ["e_follow", 1]]}, "weak": ["ice"], "drops": [["teri_leg", 20]],
                   "desc": "「照燒大大說什麼都對！」護航護到誰都不准說話的島民。冷場一下就會清醒。"},
})
TROOPS.update({"teri_fans": ["anti_teri", "teri_guard", "anti_teri"]})
QUESTS.update({
    "teri2": {"name": "照燒的兩派", "desc": "罵照燒貓的人跟護照燒貓的人，在他的攤子前吵了起來。"},
    "yijing": {"name": "易經的卦", "desc": "綜合村的易經廚總是不問就幫人卜卦。他自己好像也在等一支籤。"},
    "hm": {"name": "黃毛的筆", "desc": "美術館塗鴉角落的黃毛從不打字，只用手寫。她的筆好像掉在二樓的展示間了。"},
    "xf": {"name": "星星的回應", "desc": "美術館的星芳說，她的串有十則回應。"},
    "dy": {"name": "雀斑的工作", "desc": "綜合村的獨眼（雀斑）喜歡動物，想找跟動物有關的工作。"},
    "alien": {"name": "外來種你好", "desc": "新番鎮有個嘴很毒的塗鴉廚，一下是男生，一下是女生。"},
    "lion": {"name": "獅子老大", "desc": "釣魚港那隻叫不出聲音的汪醬，後來變成了嘴砲一流的獅子老大。"},
    "mu": {"name": "最後一張四格", "desc": "惡搞谷有個戴毛帽的人，以前畫諷刺漫畫，已經退出綜合了。"},
})
QUESTS["bday"]["desc"] = "幫綜合村的生日哥收集 4 張祝福卡，辦一場真正的生日派對。（智障神、放矢哥、照燒貓、西瓜哥、獅子老大、美術館的黃毛……島上的知名人物都可以問問看）"
