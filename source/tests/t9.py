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
        S = lambda e: pg.evaluate(e)
        # 1) 滑鼠按住十字鍵「右」
        await pg.evaluate("KDBG.warp('field1',1,9)"); await pg.wait_for_timeout(200)
        x0 = await S("KDBG.S.x")
        box = await pg.locator('.dpad .r').bounding_box()
        await pg.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2); await pg.mouse.down()
        await pg.wait_for_timeout(720)
        print('held class on', await S("document.querySelector('.dpad .r').classList.contains('on')"))
        await pg.mouse.up(); await pg.wait_for_timeout(300)
        x1 = await S("KDBG.S.x"); print('mouse hold 0.72s: moved', x1-x0, 'tiles', 'class off', not await S("document.querySelector('.dpad .r').classList.contains('on')"))
        # 2) 鍵盤按住
        await pg.evaluate("KDBG.warp('field1',1,9)"); await pg.wait_for_timeout(200)
        await pg.keyboard.down('ArrowRight'); await pg.wait_for_timeout(720); await pg.keyboard.up('ArrowRight'); await pg.wait_for_timeout(300)
        print('key hold 0.72s: moved', await S("KDBG.S.x")-1)
        # 3) 單擊只走一格
        await pg.evaluate("KDBG.warp('field1',1,9)"); await pg.wait_for_timeout(200)
        await pg.mouse.click(box['x']+box['width']/2, box['y']+box['height']/2); await pg.wait_for_timeout(400)
        print('single tap moved', await S("KDBG.S.x")-1)
        # 4) 觸控：按住右再滑到下
        await pg.evaluate("KDBG.warp('field1',1,9)"); await pg.wait_for_timeout(200)
        y0 = await S("KDBG.S.y")
        await pg.evaluate("""(() => { const r = document.querySelector('.dpad .r').getBoundingClientRect();
          const o = {pointerId: 7, pointerType: 'touch', isPrimary: true, bubbles: true, clientX: r.x + r.width/2, clientY: r.y + r.height/2};
          document.querySelector('.dpad .r').dispatchEvent(new PointerEvent('pointerdown', o)); })()""")
        await pg.wait_for_timeout(450)
        await pg.evaluate("""(() => { const r = document.querySelector('.dpad .d').getBoundingClientRect();
          document.querySelector('.dpad .r').dispatchEvent(new PointerEvent('pointermove', {pointerId: 7, pointerType: 'touch', bubbles: true, clientX: r.x + r.width/2, clientY: r.y + r.height/2})); })()""")
        await pg.wait_for_timeout(450)
        await pg.evaluate("document.querySelector('.dpad .r').dispatchEvent(new PointerEvent('pointerup', {pointerId: 7, pointerType: 'touch', bubbles: true}))")
        await pg.wait_for_timeout(300)
        print('touch slide: dx', await S("KDBG.S.x")-1, 'dy', await S("KDBG.S.y")-y0, 'dir', await S("KDBG.S.dir"))
        # 5) 選單裡按住下
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        await pg.keyboard.down('ArrowDown'); await pg.wait_for_timeout(600); await pg.keyboard.up('ArrowDown'); await pg.wait_for_timeout(200)
        print('menu cursor after 0.6s hold', await S("KDBG.S.menus[0].cursor"))
        await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        x = await S("KDBG.S.x"); await pg.wait_for_timeout(500)
        print('no runaway after release', await S("KDBG.S.x") == x)
        print('errors', errs)
        await b.close()
asyncio.run(main())
