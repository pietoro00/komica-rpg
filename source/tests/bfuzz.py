import asyncio, random, sys
from playwright.async_api import async_playwright
SEED=int(sys.argv[1]); N=int(sys.argv[2]); random.seed(SEED)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':900,'height':900})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.02)')
        S=lambda e: pg.evaluate(e)
        await pg.keyboard.press('Enter')
        for _ in range(80):
            await pg.keyboard.press('Enter'); await pg.wait_for_timeout(40)
            if await S("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
        await pg.evaluate("KDBG.join('sage'); KDBG.join('gag'); KDBG.join('del')")
        troops = await S("Object.keys(KDBG.D.troops)")
        items = await S("Object.entries(KDBG.D.items).filter(([k,v])=>v.type==='use'||v.heal||v.target).map(([k])=>k)")
        res={'win':0,'lose':0,'flee':0,'timeout':0}; nan=[]
        for n in range(N):
            if await S("KDBG.S.mode")!='map':
                # 全滅畫面：照玩家的操作按 Enter（沒有存檔時游標應該停在「回到標題」）
                if await S("KDBG.S.mode")=='gameover':
                    await pg.wait_for_timeout(300)
                    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(300)
                    for _ in range(60):
                        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(30)
                        if await S("KDBG.S.mode==='map' && !KDBG.S.busy"): break
                    if await S("KDBG.S.mode")!='map': print('cannot recover from', await S("JSON.stringify({mode:KDBG.S.mode,busy:KDBG.S.busy,menus:KDBG.S.menus.map(m=>m.cls+':'+m.cursor),dlg:KDBG.S.dialog&&KDBG.S.dialog.text,card:!!KDBG.S.card,map:KDBG.S.mapId,party:KDBG.S.party.length})")); await pg.screenshot(path='/tmp/stuck.png'); break
                    if await S("KDBG.S.party.length")<4: await pg.evaluate("KDBG.join('sage'); KDBG.join('gag'); KDBG.join('del')")
            await pg.evaluate("KDBG.closeUI()")
            lv=random.randint(5,45); await pg.evaluate(f"KDBG.level({lv})")
            for it in random.sample(items,min(6,len(items))): await pg.evaluate(f"KDBG.give('{it}',3)")
            t=random.choice(troops)
            await pg.evaluate(f"void KDBG.battle('{t}')"); await pg.wait_for_timeout(100)
            gauge_full = random.random()<0.3
            for step in range(1500):
                if gauge_full: await pg.evaluate("KDBG.S.battle && (KDBG.S.battle.gauge=100)")
                r=random.random()
                k = 'Enter' if r<0.5 else 'ArrowDown' if r<0.8 else 'ArrowUp' if r<0.9 else 'Escape'
                await pg.keyboard.press(k)
                if step%10==0:
                    st = await S("""(()=>{const B=KDBG.S.battle; if(!B) return null; const bad=[];
                      for(const e of B.enemies){ if(!Number.isFinite(e.hp)) bad.push('enemy hp '+e.name+' '+e.hp); }
                      for(const a of KDBG.S.party){ if(!Number.isFinite(a.hp)||!Number.isFinite(a.mp)||a.mp<0) bad.push('pc '+a.id+' '+a.hp+'/'+a.mp); }
                      return bad;})()""")
                    if st: nan += st
                    if await S("KDBG.S.mode")!='battle': break
            mode = await S("KDBG.S.mode")
            if mode=='battle':
                res['timeout']+=1
                await pg.evaluate("KDBG.S.battle && KDBG.S.battle.enemies.forEach(e=>e.hp=1)")
                for _ in range(300):
                    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(10)
                    if await S("KDBG.S.mode")!='battle': break
                if await S("KDBG.S.mode")=='battle': print('BATTLE STUCK', t, await S("JSON.stringify({a:KDBG.S.battle.actor,done:KDBG.S.battle.done,menus:KDBG.S.menus.length,dlg:!!KDBG.S.dialog,busy:KDBG.S.busy,wait:!!KDBG.S.waitOk})")); break
                mode = await S("KDBG.S.mode")
            elif mode=='gameover': res['lose']+=1
            else: res['win']+=1
        print('seed',SEED,res,'nan',nan[:5],'errors',errs[:5])
        await b.close()
asyncio.run(main())
