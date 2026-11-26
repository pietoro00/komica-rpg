import asyncio
from playwright.async_api import async_playwright
async def start(pg):
    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
    await pg.evaluate('KDBG.speed(0.05)')
    await pg.keyboard.press('Enter')
    for _ in range(80):
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(50)
        if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
    await pg.evaluate("KDBG.join('sage'); KDBG.join('gag'); KDBG.join('del'); KDBG.level(99)")
CHECK = """(()=>{const scr=document.getElementById('scr').getBoundingClientRect(); const out=[];
  document.querySelectorAll('.pc').forEach(pc=>{const r=pc.getBoundingClientRect(); const n=pc.querySelector('.pc-n b').textContent;
    const hp=pc.querySelectorAll('.pc-r')[0].getBoundingClientRect();
    // 被畫面上的按鍵蓋住？
    let covered=false; for(const b of document.querySelectorAll('.controls button')){const c=b.getBoundingClientRect(); if(getComputedStyle(b).display!=='none' && c.width && !(c.right<hp.left||c.left>hp.right||c.bottom<hp.top||c.top>hp.bottom)) covered=b.textContent;}
    out.push(n+(hp.bottom<=scr.bottom+0.5&&hp.top>=scr.top?' HP可見':' HP超出畫面')+(covered?' (被「'+covered+'」半透明蓋住)':''));});
  return out.join(' | ');})()"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs=[]
        for name,vw,vh,mobile,fs in [('desktop',1000,900,False,False),('phone',390,844,True,False),('phone-fs-portrait',390,844,True,True),('phone-fs-landscape',844,390,True,True)]:
            ctx = await b.new_context(viewport={'width':vw,'height':vh}, is_mobile=mobile, has_touch=mobile)
            pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
            await start(pg)
            if fs: await pg.evaluate("document.querySelector('.fsbtn').click()"); await pg.wait_for_timeout(300)
            # 四個人都帶狀態異常，數字拉到四位數
            await pg.evaluate("void KDBG.battle('boss5a')"); await pg.wait_for_timeout(1500)
            await pg.evaluate("KDBG.S.party.forEach(a=>{a.st={sage:2,flame:2,troll:2}}); KDBG.S.party[3].hp=1234")
            await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('ArrowUp'); await pg.wait_for_timeout(300)
            print(name, '→', await pg.evaluate(CHECK))
            await pg.screenshot(path=f'/tmp/hp_{name}.png')
            await ctx.close()
        print('errors', errs); await b.close()
asyncio.run(main())
