import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':820,'height':900})
        msgs=[]; pg.on('console', lambda m: msgs.append(m.type+': '+m.text)); pg.on('pageerror', lambda e: msgs.append('pageerror: '+str(e)))
        r = await pg.goto('http://127.0.0.1:8766/index.html'); print('CSP header:', (r.headers.get('content-security-policy') or '')[:40])
        await pg.wait_for_timeout(800)
        await pg.evaluate("KDBG.speed(0.1)")
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400); await pg.keyboard.press('Enter')
        for _ in range(20):
            if not await pg.evaluate("!!KDBG.S.dialog"): break
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(60)
        await pg.evaluate("void KDBG.battle('f1a')"); await pg.wait_for_timeout(1200)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(1500)
        print('mode', await pg.evaluate("KDBG.S.mode"), 'scale ok', await pg.evaluate("document.getElementById('frame').style.transform"))
        await pg.mouse.wheel(0, 2000); await pg.wait_for_timeout(300)
        await pg.screenshot(path='/tmp/about.png')
        print('\n'.join(msgs) or 'no console errors')
        await b.close()
asyncio.run(main())
