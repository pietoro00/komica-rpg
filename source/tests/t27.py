# 島上名人重構與塗鴉角落：每個人的支線都跑一次，檢查旗標、道具、任務狀態。失敗會印 FAIL。
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 820, 'height': 860})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.05)'); await pg.evaluate('KDBG.mons(false)'); await pg.evaluate('KDBG.god(1)')
        async def k(key, n=1, w=60):
            for _ in range(n): await pg.keyboard.press(key); await pg.wait_for_timeout(w)
        async def S(expr): return await pg.evaluate(f"(()=>{{const S=KDBG.S;return {expr};}})()")
        said = []
        async def settle(choices=()):
            ch = list(choices)
            for _ in range(3000):
                st = await S("({mode:S.mode,busy:S.busy,dlg:S.dialog&&(S.dialog.speaker+'：'+S.dialog.text),menus:S.menus.length,cls:(S.menus[S.menus.length-1]||{}).cls||'',ok:!!S.waitOk,card:!!S.card,board:!!S.board})")
                if st['card']: await k('Enter'); continue
                if st['board']: await k('Escape'); continue
                if st['mode'] == 'battle':
                    if st['ok']: await k('Enter'); continue
                    if st['menus']: await k('Enter', 1, 30); continue
                    await pg.wait_for_timeout(50); continue
                if st['cls'] == 'choice':
                    idx = ch.pop(0) if ch else 0
                    await k('ArrowDown', idx, 30); await k('Enter'); continue
                if st['dlg']:
                    if not said or said[-1] != st['dlg']: said.append(st['dlg'])
                    await k('Enter', 1, 30); continue
                if not st['busy'] and not st['menus']: return
                await pg.wait_for_timeout(50)
            raise SystemExit('STUCK')
        async def talk(m, x, y, d, choices=()):
            said.clear()
            await pg.evaluate(f"KDBG.warp('{m}',{x},{y})"); await pg.evaluate(f"KDBG.S.dir='{d}'")
            await k('Enter'); await settle(choices)
            return list(said)
        fails = []
        def check(label, ok, extra=''):
            print(('ok   ' if ok else 'FAIL ') + label, extra)
            if not ok: fails.append(label)
        flag = lambda f: S(f"!!S.flags['{f}']")
        inv = lambda i: S(f"S.inv['{i}']||0")

        await k('Enter'); await k('Enter'); await settle()
        await pg.evaluate("KDBG.level(30)")

        # 易經廚：第一次「下次可以先問我嗎？」→ 打倒捏他魔之後學會先問
        r = await talk('village', 8, 9, 'U', [1])
        check('易經：不問就算', any('不用開口' in s for s in r) and await flag('yjAsk') and await S("S.quests.yijing") == 'open')
        await pg.evaluate("KDBG.flag('boss2')")
        r = await talk('village', 8, 9, 'U', [0])
        check('易經：學會先問', await flag('yjDone') and await inv('acc_lot') == 1 and any('可以幫你算一卦嗎' in s for s in r))
        r = await talk('village', 8, 9, 'U', [1])
        check('易經：可以拒絕', any('尊重' in s for s in r))

        # 獨眼：第一次見面 → 找回貓之後一起去問貓奴阿姨
        r = await talk('village', 7, 14, 'D', [1])
        check('獨眼：見面', await flag('dyMet') and any('麻雀' in s for s in r))
        for f in ['q_cat', 'catFound', 'catDone']: await pg.evaluate(f"KDBG.flag('{f}')")
        await talk('village', 7, 14, 'D', [0])
        check('獨眼：當上貓保母', await flag('dyDone') and await inv('acc_patch') == 1)

        # 放矢哥：打倒捏他魔之前叫人金光廚，之後坦白
        await pg.evaluate("delete KDBG.S.flags.boss2")
        r = await talk('shinban', 3, 16, 'U', [1])
        check('放矢：金光廚', any('金光廚' in s for s in r))
        await pg.evaluate("KDBG.flag('boss2')")
        r = await talk('shinban', 3, 16, 'U')
        check('放矢：坦白', await flag('fsDone') and any('看了二十年' in s for s in r))

        # 外來種：男女切換；幫過 XD 君之後送毒舌語錄
        r1 = await talk('shinban', 5, 9, 'U'); a1 = await flag('alienF')
        r2 = await talk('shinban', 5, 9, 'U'); a2 = await flag('alienF')
        check('外來種：男→女→男', a1 and not a2 and any('土生土長' in s for s in r1) and any('兩種都是' in s for s in r2))
        await talk('shinban', 9, 10, 'U', [0])
        check('XD 君', await flag('xdHelped'))
        await talk('shinban', 5, 9, 'U')
        check('外來種：毒舌語錄', await flag('alDone') and await inv('tongue') == 3)

        # 驚恐醬：說她的表情有特色（善行 +1）
        kb = await S("S.karma")
        await pg.evaluate("delete KDBG.S.flags.boss2")
        r = await talk('plain', 22, 14, 'U', [0])
        check('驚恐醬：見面', await flag('jkMet') and await S("S.karma") == kb + 1 and any('只會畫這一種表情' in s for s in r))
        await pg.evaluate("KDBG.flag('boss2')")
        await talk('plain', 22, 14, 'U')
        check('驚恐醬：冷靜茶', await flag('jkGift'))

        # 照燒貓：祕方 → 兩派吵架 → 不掛名
        await pg.evaluate("delete KDBG.S.flags.boss2; KDBG.flag('boss1'); KDBG.flag('q_teri'); KDBG.give('sauce',3)")  # 照燒攤在新番鎮的時期
        await talk('shinban', 16, 9, 'U', [1])
        check('照燒：兩派', await flag('teriDone') and await flag('teriFans') and await inv('nameless_bento') == 3 and await S("S.quests.teri2") == 'done')

        # 生日哥：辦派對 → 生日蠟燭
        await pg.evaluate("KDBG.flag('raidDone'); KDBG.flag('q_bday'); KDBG.give('card',4)")
        await talk('village', 12, 12, 'U')
        check('生日哥：派對', await flag('bdayDone'))
        r = await talk('village', 12, 12, 'U')
        check('生日哥：今天我復活ㄛ', await inv('candle') == 3 and any('今天我復活ㄛ' in s for s in r))

        # 汪醬 → 獅子老大 → 西瓜哥說真心話
        r = await talk('port', 20, 9, 'U')
        check('汪醬', await flag('wanMet') and any('汪' in s for s in r))
        await pg.evaluate("KDBG.flag('boss3')")
        r = await talk('port', 18, 8, 'U')
        check('西瓜哥：還在釣', any('還是想釣' in s for s in r))
        r = await talk('port', 20, 9, 'U')
        check('獅子老大：嘴到西瓜回不了嘴', await flag('wmDone') and await inv('melon') == 3 and any('反骨' in s for s in r))
        r = await talk('port', 18, 8, 'U')
        check('西瓜哥：真心話', any('真心話' in s for s in r))

        # 黃毛：沒有筆只能比手畫腳 → 二樓撿到筆 → 手寫
        r = await talk('gallery1', 16, 7, 'U')
        check('黃毛：比手畫腳', await flag('hmMet') and all(s.startswith('：') or s.startswith('無名氏') or s.startswith('戴爾') for s in r))
        await talk('gallery2', 5, 9, 'U')
        check('黃毛的筆', await inv('penhm') == 1)
        hand = await S("KDBG.D.hand.includes('黃毛')")
        r = await talk('gallery1', 16, 7, 'U')
        check('黃毛：手寫', hand and await flag('hmDone') and await inv('acc_ribbon') == 1 and any(s.startswith('黃毛：') for s in r))

        # 星芳：先假裝沒看到，再說實話
        await talk('gallery1', 19, 6, 'U', [0, 1])
        check('星芳：假裝沒看到', not await flag('xfDone'))
        await talk('gallery1', 19, 6, 'U', [0, 0])
        check('星芳：真心的回應', await flag('xfDone') and await inv('star') == 3)

        # 慕內：退出綜合 → 實名教團出現後畫最後一張四格
        await talk('valley', 8, 11, 'D')
        check('慕內：見面', await flag('muMet'))
        await pg.evaluate("KDBG.flag('mid')")
        await talk('valley', 8, 11, 'D', [1])
        check('慕內：不勉強', not await flag('muComic'))
        await talk('valley', 8, 11, 'D', [0])
        check('慕內：四格', await flag('muComic') and await inv('acc_beanie') == 1)
        await pg.evaluate("void KDBG.run([['board','b_port']])"); await pg.wait_for_timeout(300)
        txt = await pg.evaluate("document.querySelector('.board').innerText")
        check('慕內：四格貼上歡樂惡搞版', '名牌兵的一天' in txt)
        await k('Escape'); await settle()

        check('沒有錯誤', not errs, errs)
        print('RESULT', 'PASS' if not fails else 'FAIL ' + ', '.join(fails))
        await b.close()

asyncio.run(main())
