import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':820,'height':860})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800); await pg.evaluate('KDBG.mons(false)')
        async def k(key,n=1,w=120):
            for _ in range(n): await pg.keyboard.press(key); await pg.wait_for_timeout(w)
        async def S(e): return await pg.evaluate(f"(()=>{{const S=KDBG.S;return {e};}})()")
        await k('Enter'); await pg.wait_for_timeout(500)
        print('card', await pg.locator('.card').count()); await pg.screenshot(path='/tmp/n_card.png')
        await k('Enter')
        while await S("!!S.dialog"): await k('Enter',1,60)
        # 討論板
        await pg.evaluate("KDBG.warp('village',12,5)"); await pg.evaluate("KDBG.S.dir='U'"); await k('Enter'); await pg.wait_for_timeout(200)
        await k('ArrowDown',1); await pg.screenshot(path='/tmp/n_board.png'); print('board', await pg.locator('.board .post').count())
        await k('Escape'); print('board closed', await S("S.board===null"), 'busy', await S("S.busy"))
        # 跳串、聊天、圖鑑、設定
        await pg.evaluate("KDBG.flag('sageJoin'); KDBG.join('sage'); KDBG.S.visited.shinban=true; KDBG.S.visited.field1=true")
        await k('Escape'); await k('ArrowDown',4); await k('Enter'); await pg.wait_for_timeout(200); await pg.screenshot(path='/tmp/n_skit.png')
        await k('Enter'); 
        while await S("!!S.dialog"): await k('Enter',1,60)
        print('skit seen', await S("!!S.flags['skit:sage1']"))
        await k('Escape'); await k('ArrowDown',6); await k('Enter'); await pg.wait_for_timeout(200); await pg.screenshot(path='/tmp/n_travel.png')
        await k('ArrowDown'); await k('Enter'); await pg.wait_for_timeout(400); print('traveled to', await S("S.mapId"))
        while await S("!!S.dialog"): await k('Enter',1,60)
        await k('Escape'); await k('ArrowDown',8); await k('Enter'); await k('Enter'); print('speed', await pg.evaluate("JSON.parse(localStorage.getItem('komica_rpg_meta_v1')).speed"))
        await pg.evaluate("KDBG.closeUI()")
        # 戰鬥：合體技、自動、彈出數字
        await pg.evaluate("KDBG.level(10)"); await pg.evaluate("void KDBG.battle('p2a')"); await pg.wait_for_timeout(900)
        await pg.evaluate("KDBG.S.battle.gauge=100"); await k('ArrowDown'); await k('ArrowUp'); await pg.wait_for_timeout(100)
        await pg.screenshot(path='/tmp/n_gauge.png')
        print('menu0', await S("S.menus[0].build()[0].label"))
        await k('Enter'); await k('Enter',1,300)   # 合體技 → 神串降臨
        await pg.wait_for_timeout(300); await pg.screenshot(path='/tmp/n_combo.png')
        for _ in range(200):
            if await S("S.mode")!='battle': break
            if await S("!!S.waitOk"): await k('Enter'); continue
            if await S("S.menus.length"):
                await pg.evaluate("(()=>{const m=KDBG.S.menus[KDBG.S.menus.length-1]; const i=m.build().findIndex(x=>x.label==='自動'); if(i>=0) m.cursor=i;})()"); await k('Enter',1,80)
            await pg.wait_for_timeout(80)
        print('after battle', await S("S.mode"), 'dex', await S("JSON.stringify(S.dex)"))
        await k('Escape'); await k('ArrowDown',5); await k('Enter'); await pg.wait_for_timeout(200); await pg.screenshot(path='/tmp/n_dex.png')
        print('errors', errs)
        await b.close()
asyncio.run(main())
