import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1000,'height':1000})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        bad=[]; pg.on('response', lambda r: bad.append(r.url) if r.status>=400 else None)
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.05)'); await pg.evaluate('KDBG.mons(false)')
        await pg.keyboard.press('Enter')
        for _ in range(80):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(60)
            if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
        await pg.evaluate("KDBG.warp('field1',6,9)"); await pg.wait_for_timeout(300)
        src = "document.getElementById('pl').getAttribute('src') + (document.getElementById('pl').classList.contains('flip')?' [flip]':'')"
        for key in ['ArrowRight','ArrowLeft','ArrowUp','ArrowDown']:
            await pg.keyboard.down(key); seen=[]
            for _ in range(8):
                await pg.wait_for_timeout(40); v = await pg.evaluate(src)
                if not seen or seen[-1]!=v: seen.append(v)
            await pg.keyboard.up(key); await pg.wait_for_timeout(250)
            print(key, 'while walking:', seen, '| stopped:', await pg.evaluate(src))
        await pg.evaluate("KDBG.warp('field1',6,9)"); await pg.wait_for_timeout(200)
        await pg.keyboard.press('ArrowLeft'); await pg.wait_for_timeout(250)
        await pg.locator('#scr').screenshot(path='/tmp/face_left.png')
        print('errors', errs, 'bad', bad)
        await b.close()
asyncio.run(main())
