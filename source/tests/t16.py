import asyncio
from playwright.async_api import async_playwright
async def start(pg):
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
    await pg.evaluate('KDBG.speed(0.05)')
    await pg.keyboard.press('Enter')
    for _ in range(80):
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)
        if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
    await pg.wait_for_timeout(2600)  # 等提示消失
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        errs=[]
        # 手機直向、橫向
        for name,vw,vh in [('portrait',390,844),('landscape',844,390)]:
            ctx = await b.new_context(viewport={'width':vw,'height':vh}, device_scale_factor=2, is_mobile=True, has_touch=True)
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await start(pg)
            print(name, 'coarse?', await pg.evaluate("matchMedia('(hover:hover) and (pointer:fine)').matches"))
            await pg.locator('.fsbtn').tap(); await pg.wait_for_timeout(500)
            print(' fs on', await pg.evaluate("document.body.classList.contains('fs')"), 'stage', await pg.evaluate("JSON.stringify(document.getElementById('stage').getBoundingClientRect())"))
            await pg.screenshot(path=f'/tmp/fs_{name}.png')
            # 疊在畫面上的按鍵能操作
            x0 = await pg.evaluate("KDBG.S.x")
            await pg.locator('.dpad .r').tap(); await pg.wait_for_timeout(300)
            print(' tap right moved', await pg.evaluate("KDBG.S.x")-x0)
            await pg.locator('.abtn.m:not(.fsbtn)').tap(); await pg.wait_for_timeout(300)
            print(' menu opened', await pg.evaluate("KDBG.S.menus.length"))
            await pg.locator('.abtn.b').tap(); await pg.wait_for_timeout(200)
            await pg.locator('.fsx').tap(); await pg.wait_for_timeout(400)
            print(' fs off', not await pg.evaluate("document.body.classList.contains('fs')"), 'stage w', await pg.evaluate("document.getElementById('stage').getBoundingClientRect().width"))
            await ctx.close()
        # 電腦
        ctx = await b.new_context(viewport={'width':1366,'height':768})
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await start(pg)
        await pg.keyboard.press('f'); await pg.wait_for_timeout(600)
        print('desktop fs', await pg.evaluate("document.body.classList.contains('fs')"), 'native', await pg.evaluate("!!document.fullscreenElement"), 'controls visible', await pg.evaluate("getComputedStyle(document.querySelector('.controls')).display"), 'stage', await pg.evaluate("JSON.stringify(document.getElementById('stage').getBoundingClientRect())"))
        await pg.screenshot(path='/tmp/fs_desktop.png')
        await pg.keyboard.press('f'); await pg.wait_for_timeout(500)
        print('desktop fs off', not await pg.evaluate("document.body.classList.contains('fs')"), 'native', await pg.evaluate("!!document.fullscreenElement"))
        await pg.keyboard.press('f'); await pg.wait_for_timeout(500)
        await pg.evaluate("document.exitFullscreen && document.fullscreenElement && document.exitFullscreen()"); await pg.wait_for_timeout(500)
        print('exit via browser → fs class removed', not await pg.evaluate("document.body.classList.contains('fs')"))
        print('errors', errs)
        await b.close()
asyncio.run(main())
