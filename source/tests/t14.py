import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1000,'height':1000})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.05)'); await pg.evaluate('KDBG.mons(false)')
        await pg.keyboard.press('Enter')
        for _ in range(80):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(60)
            if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
        await pg.evaluate("KDBG.S.inv={noodle:2, tea:1}; KDBG.S.party[0].hp=5; KDBG.closeUI()")
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)   # 道具
        await pg.keyboard.press('ArrowDown'); await pg.wait_for_timeout(100) # tea (last)
        print('items', await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>l.textContent).join('|')"))
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)     # use → target menu
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(400)
        for _ in range(5):
            if await pg.evaluate("!!KDBG.S.dialog"): await pg.keyboard.press('Enter'); await pg.wait_for_timeout(150)
        print('after use (no esc): menus', await pg.evaluate("KDBG.S.menus.map(m=>m.cls+':'+m.cursor).join(',')"), await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>(l.classList.contains('sel')?'*':'')+l.textContent).join('|')"))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(150)
        print('after use, menus', await pg.evaluate("KDBG.S.menus.length"), 'items', await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>(l.classList.contains('sel')?'*':'')+l.textContent).join('|')"))
        print('errors', errs); await b.close()
asyncio.run(main())
