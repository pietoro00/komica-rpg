# 目標箭頭、全自動變速（→／←）、看板依內容停留、手寫字選項與 hand 指令、本次冒險紀錄。失敗會印 FAIL。
import asyncio, time
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 820, 'height': 860})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        fails = []
        def check(label, ok, extra=''):
            print(('ok   ' if ok else 'FAIL ') + label, extra)
            if not ok: fails.append(label)
        S = lambda e: pg.evaluate(f"(()=>{{const S=KDBG.S;return {e};}})()")
        clip = {'x': 0, 'y': 60, 'width': 820, 'height': 640}

        # ---- 自己玩：開場後箭頭指向會館門口的綜合伯 ----
        await pg.evaluate('KDBG.speed(0.05)')
        await pg.keyboard.press('Enter'); await pg.keyboard.press('Enter')
        for _ in range(80):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(40)
            if await S("!S.busy && !S.dialog && S.mode==='map'"): break
        await pg.evaluate('KDBG.mons(false)'); await pg.wait_for_timeout(200)
        arrow = await pg.evaluate("(()=>{const a=document.querySelector('.garrow');return a&&{cls:a.className,title:a.title};})()")
        check('箭頭：開場指向綜合伯', arrow and 'on' in arrow['cls'] and '綜合伯' in arrow['title'], arrow)
        await pg.screenshot(path='/tmp/t28_arrow_on.png', clip=clip)
        # 往右走到畫面外，箭頭應該跑到邊緣
        await pg.evaluate("KDBG.warp('village',22,9)"); await pg.wait_for_timeout(200)
        await pg.evaluate("KDBG.warp('field1',20,10)"); await pg.wait_for_timeout(300)
        arrow = await pg.evaluate("(()=>{const a=document.querySelector('.garrow');return a&&{cls:a.className,title:a.title};})()")
        check('箭頭：別張地圖指向出口', arrow and 'edge' in arrow['cls'], arrow)
        await pg.screenshot(path='/tmp/t28_arrow_edge.png', clip=clip)

        # ---- 手寫：精華區的舊回應（hand 指令） ----
        await pg.evaluate("KDBG.flag('abyssOpen'); KDBG.warp('abyss1',3,11); KDBG.S.dir='U'")
        await pg.wait_for_timeout(200); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(250)
        h = await pg.evaluate("(()=>{const d=document.querySelector('.dialog');return d&&{cls:d.className,text:d.innerText};})()")
        check('hand 指令：舊回應用手寫字', h and 'hand' in h['cls'] and '再蓋一次' in h['text'], h)
        await pg.screenshot(path='/tmp/t28_hand.png', clip=clip)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        # 設定：對話字體改手寫 → 一般對話也變手寫
        await pg.evaluate("void KDBG.run([['say','綜合伯','測試一下。']])"); await pg.wait_for_timeout(150)
        before = await pg.evaluate("document.querySelector('.dialog').className")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        await pg.keyboard.press('m'); await pg.wait_for_timeout(150)
        items = await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>l.textContent)")
        for _ in range(items.index('設定')): await pg.keyboard.press('ArrowDown')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        items = await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>l.textContent)")
        check('設定有新項目', any('全自動範圍' in i for i in items) and any('目標箭頭' in i for i in items) and any('對話字體' in i for i in items), items)
        idx = next(i for i, t in enumerate(items) if t.startswith('對話字體'))
        for _ in range(idx): await pg.keyboard.press('ArrowDown')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        await pg.evaluate("KDBG.closeUI()")
        await pg.evaluate("void KDBG.run([['say','綜合伯','測試一下。']])"); await pg.wait_for_timeout(150)
        after = await pg.evaluate("document.querySelector('.dialog').className")
        check('對話字體：手寫', 'hand' not in before and 'hand' in after, (before, after))
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        await pg.evaluate("(()=>{const m=JSON.parse(localStorage.getItem('komica_rpg_meta_v1'));m.hand=false;localStorage.setItem('komica_rpg_meta_v1',JSON.stringify(m));})()")

        # ---- 全自動：→ 加速、← 減速 ----
        await pg.evaluate("KDBG.warp('village',9,6); KDBG.auto(true)"); await pg.wait_for_timeout(200)
        for _ in range(4): await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(60)
        badge = await pg.evaluate("document.querySelector('.autob b').textContent")
        check('→ 加速到 ×4（按第四次停在 ×4）', badge == 'AUTO ×4', badge)
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(60)
        badge = await pg.evaluate("document.querySelector('.autob b').textContent")
        check('← 減速到 ×3', badge == 'AUTO ×3', badge)
        await pg.screenshot(path='/tmp/t28_auto_x3.png', clip=clip)
        for _ in range(3): await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(60)
        badge = await pg.evaluate("document.querySelector('.autob b').textContent")
        check('← 回到正常速度', badge == 'AUTO', badge)

        # ---- 全自動看板：字多的看板停比較久，而且會一則一則捲到底 ----
        async def board_time(bid):
            await pg.evaluate(f"void KDBG.run([['board','{bid}']])")
            t0 = time.time(); tops = set()
            while await S("!!S.board"):
                tops.add(await S("S.board.top")); await pg.wait_for_timeout(20)
                if time.time() - t0 > 60: break
            return time.time() - t0, len(tops), await S(f"KDBG.D.boards['{bid}'].posts.filter(p=>!p.cond).map(p=>p.text).join('').length")
        await pg.evaluate("KDBG.auto(false); KDBG.speed(0.2); KDBG.auto(true)")
        t_small, n_small, c_small = await board_time('b_abyss')
        t_big, n_big, c_big = await board_time('b_village')
        check('看板：一則一則捲到底', n_big > 5, (n_small, n_big))
        check('看板：字越多停越久', t_big > t_small * 1.5, f'精華區 {c_small} 字 {t_small:.1f}s／綜合版 {c_big} 字 {t_big:.1f}s')
        await pg.evaluate("KDBG.auto(false); KDBG.speed(0.05)")

        # ---- 本次冒險紀錄 ----
        await pg.evaluate("KDBG.closeUI(); void KDBG.run([['ending','true']])")
        for _ in range(60):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(60)
            if await S("S.ending && S.ending.card"): break
        await pg.wait_for_timeout(300)
        rec = await pg.evaluate("(()=>{const r=document.querySelector('.rec');return r&&r.innerText;})()")
        check('結局卡有冒險紀錄', rec and '本次冒險紀錄' in rec and '戰鬥' in rec and '寶箱' in rec, rec)
        await pg.screenshot(path='/tmp/t28_record.png', clip=clip)

        check('沒有錯誤', not errs, errs)
        print('RESULT', 'PASS' if not fails else 'FAIL ' + ', '.join(fails))
        await b.close()

asyncio.run(main())
