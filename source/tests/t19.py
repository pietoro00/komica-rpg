import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1000,'height':900})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.05)'); await pg.evaluate('KDBG.mons(false)')
        await pg.keyboard.press('Enter')
        lines=[]
        for _ in range(80):
            d = await pg.evaluate("KDBG.S.dialog && KDBG.S.dialog.text")
            if d and (not lines or lines[-1]!=d): lines.append(d)
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)
            if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
        print('last lines:', lines[-2:])
        print('goal:', await pg.evaluate("KDBG.S.goal"))
        await pg.wait_for_timeout(500)
        print('marks:', await pg.evaluate("[...document.querySelectorAll('.mark')].map(m=>m.style.left+','+m.style.top)"))
        await pg.locator('#scr').screenshot(path='/tmp/start_mark.png')
        # 從起點走到會館門口：左3、上1 → (6,5) 面向上
        for k,n in [('ArrowLeft',3),('ArrowUp',1)]:
            for _ in range(n): await pg.keyboard.press(k); await pg.wait_for_timeout(180)
        print('pos', await pg.evaluate("KDBG.S.x+','+KDBG.S.y+' '+KDBG.S.dir"))
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
        print('talking to:', await pg.evaluate("KDBG.S.dialog && KDBG.S.dialog.speaker"))
        for _ in range(30):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(60)
            if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog"): break
        print('after talk marks:', await pg.evaluate("document.querySelectorAll('.mark').length"), 'goal:', await pg.evaluate("KDBG.S.goal"))
        print('errors', errs); await b.close()
asyncio.run(main())
