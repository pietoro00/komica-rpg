import asyncio, json
from playwright.async_api import async_playwright
async def newgame(pg, easy):
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
    await pg.evaluate("localStorage.clear()"); await pg.reload(); await pg.wait_for_timeout(800)
    await pg.evaluate('KDBG.speed(0.05)')
    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
    menu = await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>l.textContent).join('|')")
    if easy: await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(100)
    desc = await pg.evaluate("(document.querySelector('.menu.active .md')||{}).textContent")
    await pg.screenshot(path=f'/tmp/diff_{int(easy)}.png')
    await pg.keyboard.press('Enter')
    for _ in range(100):
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(40)
        if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
    return menu, desc
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs=[]
        for easy in [False, True]:
            pg = await b.new_page(viewport={'width':1000,'height':900}); pg.on('pageerror', lambda e: errs.append(str(e)))
            menu, desc = await newgame(pg, easy)
            print('=== easy' if easy else '=== normal', '| menu:', menu, '| desc:', (desc or '')[:40])
            print(' S.easy', await pg.evaluate("KDBG.S.easy"), 'village mons', await pg.evaluate("KDBG.S.mons.length"))
            await pg.evaluate("KDBG.warp('field1',1,9)"); await pg.wait_for_timeout(300)
            mons = await pg.evaluate("KDBG.S.mons.map(m=>m.troop+'@'+m.x+','+m.y+' '+m.sprite)")
            print(' field1 mons', len(mons), mons)
            print(' min dist to player', await pg.evaluate("Math.min(...KDBG.S.mons.map(m=>Math.abs(m.x-KDBG.S.x)+Math.abs(m.y-KDBG.S.y)))"))
            await pg.wait_for_timeout(2500)
            print(' moved after 2.5s', await pg.evaluate("KDBG.S.mons.map(m=>m.x+','+m.y).join(' ')"))
            print(' dom mons', await pg.evaluate("document.querySelectorAll('#mons img').length"))
            await pg.locator('#scr').screenshot(path=f'/tmp/mons_{int(easy)}.png')
            # 把一隻怪放到玩家旁邊 → 應該追過來並開戰
            await pg.evaluate("(()=>{const m=KDBG.S.mons[0]; m.x=KDBG.S.x+2; m.y=KDBG.S.y; m.next=0;})()")
            for _ in range(30):
                await pg.wait_for_timeout(100)
                if await pg.evaluate("KDBG.S.mode")=='battle': break
            print(' chased into battle:', await pg.evaluate("KDBG.S.mode"))
            hp = await pg.evaluate("KDBG.S.battle.enemies.map(e=>e.name+':'+e.hp+'/'+e.def.hp).join(', ')")
            print(' enemy hp', hp)
            # 打贏：全部敵人 1 HP，按 Enter 直到結束
            await pg.evaluate("KDBG.level(30)"); await pg.evaluate("KDBG.S.battle.enemies.forEach(e=>e.hp=1)")
            lines=set()
            for _ in range(200):
                await pg.keyboard.press('Enter'); await pg.wait_for_timeout(20)
                t = await pg.evaluate("KDBG.S.battle ? [...document.querySelectorAll('.log div')].map(d=>d.textContent).join('/') : ''")
                for l in t.split('/'):
                    if '經驗值' in l: lines.add(l)
                if await pg.evaluate("KDBG.S.mode")=='map': break
            print(' reward', lines, '| mons left', await pg.evaluate("KDBG.S.mons.length"))
            # 撞上去開戰 + 無視
            await pg.wait_for_timeout(1700)
            await pg.evaluate("(()=>{const m=KDBG.S.mons[0]; m.x=KDBG.S.x+1; m.y=KDBG.S.y; m.next=1e12;})()"); await pg.evaluate("KDBG.closeUI()")
            await pg.keyboard.press('ArrowRight'); await pg.wait_for_timeout(300)
            print(' bump → mode', await pg.evaluate("KDBG.S.mode"))
            for _ in range(20):
                if await pg.evaluate("KDBG.S.battle && KDBG.S.battle.actor>=0 && KDBG.S.menus.length>0"): break
                await pg.keyboard.press('Enter'); await pg.wait_for_timeout(80)
            # 選「無視」（最後一項）
            await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(80); await pg.keyboard.press('Enter')
            for _ in range(60):
                await pg.wait_for_timeout(60)
                if await pg.evaluate("KDBG.S.mode")=='map': break
                await pg.keyboard.press('Enter')
            print(' after flee mode', await pg.evaluate("KDBG.S.mode"), 'monster calm', await pg.evaluate("KDBG.S.mons[0].calm > performance.now()"), 'still there', await pg.evaluate("KDBG.S.mons.length"))
            # 設定切換難度
            await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
            for _ in range(8): await pg.keyboard.press('ArrowDown')
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
            print(' settings', await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>l.textContent).join('|')"))
            await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
            print(' toggled easy →', await pg.evaluate("KDBG.S.easy"))
            await pg.close()
        print('errors', errs); await b.close()
asyncio.run(main())
