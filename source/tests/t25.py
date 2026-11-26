# 補 MP 道具選對象時，右欄要顯示 MP（不是 HP）；補 HP 道具維持顯示 HP。地圖選單與戰鬥都檢查。
import asyncio
from playwright.async_api import async_playwright

LAST_MENU = """(()=>{const ms=document.querySelectorAll('.menu'); const m=ms[ms.length-1];
  return {title:m.querySelector('.mt')?.textContent||'', rows:[...m.querySelectorAll('li')].map(li=>li.textContent)};})()"""

async def start(pg):
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
    await pg.evaluate('KDBG.speed(0.05)')
    await pg.keyboard.press('Enter')
    for _ in range(80):
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)
        if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
    await pg.evaluate("KDBG.mons(false); KDBG.join('sage'); KDBG.level(20)")

async def field(pg, item):
    # 只留下這一個道具，讓它排第一個
    await pg.evaluate(f"for (const k in KDBG.S.inv) delete KDBG.S.inv[k]; KDBG.give('{item}',1); KDBG.S.party.forEach(a=>{{a.mp=1;a.hp=5}}); KDBG.closeUI()")
    await pg.evaluate("KDBG.S.menus.length=0")
    await pg.keyboard.press('m'); await pg.wait_for_timeout(150)  # 開主選單
    for _ in range(8):
        m = await pg.evaluate(LAST_MENU)
        if any('道具' in r for r in m['rows']): break
        await pg.wait_for_timeout(100)
    idx = next(i for i, r in enumerate(m['rows']) if r.startswith('道具'))
    for _ in range(idx): await pg.keyboard.press('ArrowDown')
    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(100)
    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(100)
    m = await pg.evaluate(LAST_MENU)
    await pg.evaluate("KDBG.closeUI()")
    return m

async def battle(pg, item):
    await pg.evaluate(f"for (const k in KDBG.S.inv) delete KDBG.S.inv[k]; KDBG.give('{item}',1); KDBG.S.party.forEach(a=>{{a.mp=1}})")
    await pg.evaluate("void KDBG.battle(Object.keys(KDBG.D.troops)[0])"); await pg.wait_for_timeout(1500)
    m = await pg.evaluate(LAST_MENU)
    idx = next(i for i, r in enumerate(m['rows']) if r.startswith('道具'))
    for _ in range(idx): await pg.keyboard.press('ArrowDown')
    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
    m = await pg.evaluate(LAST_MENU)
    await pg.screenshot(path=f'/tmp/t25_battle_{item}.png')
    await pg.keyboard.press('Escape'); await pg.keyboard.press('Escape'); await pg.keyboard.press('Escape')
    await pg.evaluate("KDBG.god(1)")
    return m

async def main():
    ok = True
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs = []
        pg = await (await b.new_context(viewport={'width': 1000, 'height': 900})).new_page()
        pg.on('pageerror', lambda e: errs.append(str(e)))
        await start(pg)
        for where, fn in (('地圖', field), ('戰鬥', battle)):
            for item, want, bad in (('cola', 'MP', None), ('teri_rice', 'MP', None), ('boba', 'MP', None)):
                m = await fn(pg, item)
                good = m['rows'] and all(want in r for r in m['rows'])
                print(where, item, m['title'], m['rows'], 'OK' if good else 'NG')
                ok &= bool(good)
            if where == '地圖':
                m = await fn(pg, 'noodle') if await pg.evaluate("!!KDBG.D.items.noodle") else None
                if m:
                    good = all('HP' in r and 'MP' not in r for r in m['rows'])
                    print(where, 'noodle', m['rows'], 'OK' if good else 'NG'); ok &= good
        print('errors', errs); ok &= not errs
        await b.close()
    print('PASS' if ok else 'FAIL')

asyncio.run(main())
