import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1000,'height':900})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.03)'); await pg.evaluate('KDBG.mons(false)')
        await pg.keyboard.press('Enter'); await pg.keyboard.press('Enter')
        for _ in range(100):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(30)
            if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
        await pg.evaluate("KDBG.join('sage'); KDBG.level(8); KDBG.give('noodle2',5); KDBG.warp('shinban',15,7)")
        await pg.evaluate("void KDBG.battle('zz')")
        seen=set(); shot=False; logs=set()
        for i in range(1500):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(20)
            st = await pg.evaluate("KDBG.S.battle ? KDBG.S.battle.enemies.map(e=>e.name+':'+e.hp).join(',') : null")
            if st:
                for e in st.split(','): seen.add(e.split(':')[0])
                for l in await pg.evaluate("[...document.querySelectorAll('.log div')].map(d=>d.textContent)"):
                    if '箱' in l or '限定' in l or '模型' in l: logs.add(l)
                if not shot and '暴走模型' in st:
                    await pg.wait_for_timeout(300); await pg.locator('#scr').screenshot(path='/tmp/zz_battle.png'); shot=True
            if await pg.evaluate("KDBG.S.mode")!='battle': break
        print('result mode', await pg.evaluate("KDBG.S.mode"), 'enemies seen', seen)
        print('notable logs', list(logs)[:8])
        print('dex', await pg.evaluate("JSON.stringify(KDBG.S.dex.zz_god)"))
        print('errors', errs); await b.close()
asyncio.run(main())
