import asyncio, random, sys, json
from playwright.async_api import async_playwright
SEED=int(sys.argv[1]) if len(sys.argv)>1 else 1
STEPS=int(sys.argv[2]) if len(sys.argv)>2 else 3000
random.seed(SEED)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':900,'height':1000})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)[:300]))
        cons=[]; pg.on('console', lambda m: cons.append(m.text[:200]) if m.type=='error' else None)
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate('KDBG.speed(0.02)')
        await pg.evaluate("window.__dlg=0; setInterval(()=>{},1000)")
        S=lambda e: pg.evaluate(e)
        maps = await S("Object.keys(KDBG.D.maps)")
        keys=['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Enter','Enter','Escape','x','m']
        stuck=0; last=None; inv_bad=[]
        await pg.keyboard.press('Enter')
        for i in range(STEPS):
            r=random.random()
            if r<0.004:
                m=random.choice(maps)
                # 找一格能走的位置
                pos = await S(f"""(()=>{{const m=KDBG.D.maps['{m}'];const c=[];m.rows.forEach((row,y)=>[...row].forEach((t,x)=>{{const td=KDBG.D.tiles[t]; if(td.length<2||td[1]) c.push([x,y]);}}));return c[Math.floor(Math.random()*c.length)];}})()""")
                if await S("KDBG.S.mode==='map' && !KDBG.S.busy"): await pg.evaluate(f"KDBG.warp('{m}',{pos[0]},{pos[1]})")
            elif r<0.006:
                await pg.evaluate(f"KDBG.level({random.randint(3,40)})")
            elif r<0.008:
                it = random.choice(await S("Object.keys(KDBG.D.items)"))
                await pg.evaluate(f"KDBG.give('{it}',2)")
            elif r<0.009 and await S("KDBG.S.party.length<4"):
                for a in ['sage','gag','del']:
                    if not await S(f"KDBG.S.party.some(x=>x.id==='{a}')"): await pg.evaluate(f"KDBG.join('{a}')"); break
            else:
                k=random.choice(keys)
                if k.startswith('Arrow') and random.random()<0.3:
                    await pg.keyboard.down(k); await pg.wait_for_timeout(random.randint(50,400)); await pg.keyboard.up(k)
                else:
                    await pg.keyboard.press(k)
            if i%5==0: await pg.wait_for_timeout(15)
            if i%25==0:
                st = await S("""(()=>{const s=KDBG.S, D=KDBG.D; const m=D.maps[s.mapId]; const t=m.rows[s.y]&&m.rows[s.y][s.x];
                  const bad=[]; if(s.mode==='map'){ if(!t) bad.push('pos out of map '+s.mapId+' '+s.x+','+s.y); else { const td=D.tiles[t]; if(td.length>1&&!td[1]) bad.push('on blocked tile '+s.mapId+' '+s.x+','+s.y);} }
                  if(!Number.isFinite(s.gold)||s.gold<0) bad.push('gold '+s.gold);
                  for(const a of s.party){ if(!Number.isFinite(a.hp)||a.hp<0||!Number.isFinite(a.mp)||a.mp<0) bad.push('hp/mp '+a.id+' '+a.hp+'/'+a.mp); }
                  for(const [k,v] of Object.entries(s.inv)) if(!(v>0)) bad.push('inv '+k+'='+v);
                  const seen=new Set(); const ents=m.ents.filter(e=>!e.show||true);
                  for(const mo of s.mons||[]){ const tt=m.rows[mo.y]&&m.rows[mo.y][mo.x]; if(!tt||D.tiles[tt][1]!==1) bad.push('mon on blocked '+mo.x+','+mo.y);
                    const key=mo.x+','+mo.y; if(seen.has(key)) bad.push('mons overlap '+key); seen.add(key);
                    if(s.mode==='map' && mo.x===s.x && mo.y===s.y) bad.push('mon on player');
                    if(m.warps.some(w=>w[0]===mo.x&&w[1]===mo.y)) bad.push('mon on warp'); }
                  return {bad, sig: s.mode+'|'+s.busy+'|'+!!s.dialog+'|'+s.menus.length+'|'+!!s.battle+'|'+!!s.board+'|'+!!s.card+'|'+!!s.waitOk+'|'+s.mapId+s.x+','+s.y, mode:s.mode, busy:s.busy, dlg:!!s.dialog, menus:s.menus.length, wait:!!s.waitOk, card:!!s.card, board:!!s.board, battle: s.battle?{done:s.battle.done}:null};})()""")
                if st['bad']: inv_bad.append((i,st['bad']))
                # busy 卻沒有任何可以互動的東西 → 卡死
                if st['busy'] and not (st['dlg'] or st['menus'] or st['wait'] or st['card'] or st['board'] or st['mode']=='battle' or st['mode']=='ending'):
                    stuck+=1
                    if stuck>8: print('STUCK', i, st); break
                else: stuck=0
            if await S("KDBG.S.mode")=='gameover' and random.random()<0.5: pass
        print('seed',SEED,'steps',i,'mode',await S("KDBG.S.mode"),'map',await S("KDBG.S.mapId"),'lv',await S("KDBG.S.party.map(a=>a.level).join(',')"))
        print('invariant issues', inv_bad[:10])
        print('pageerrors', errs[:10]); print('console errors', cons[:10])
        await pg.screenshot(path=f'/tmp/fuzz_{SEED}.png')
        await b.close()
asyncio.run(main())
