import asyncio, json, sys
from collections import deque
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs=[]
        res={}
        for easy in [False]:
            for mapid,start,goalx in [('plain',(1,9),None)]:
                fights=[]; lens=[]
                for trial in range(8):
                    pg = await b.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
                    await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(600)
                    await pg.evaluate('KDBG.speed(0.02)'); await pg.evaluate('KDBG.god(1)')
                    await pg.keyboard.press('Enter'); await pg.wait_for_timeout(100)
                    if easy: await pg.keyboard.press('ArrowDown')
                    await pg.keyboard.press('Enter')
                    for _ in range(100):
                        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(30)
                        if await pg.evaluate("!KDBG.S.busy && !KDBG.S.dialog && KDBG.S.mode==='map'"): break
                    await pg.evaluate("KDBG.level(12)")
                    await pg.evaluate(f"KDBG.warp('{mapid}',{start[0]},{start[1]})"); await pg.wait_for_timeout(200)
                    M = await pg.evaluate("(()=>{const m=KDBG.D.maps[KDBG.S.mapId];return {rows:m.rows,tiles:KDBG.D.tiles,warps:m.warps,ents:m.ents.map(e=>[e.x,e.y])}})()")
                    rows=M['rows']; W=len(rows[0]); H=len(rows)
                    ok=lambda x,y: 0<=x<W and 0<=y<H and M['tiles'][rows[y][x]][1]==1 and [x,y] not in M['ents']
                    # 目標：離起點最遠的出口
                    tgt=max(M['warps'], key=lambda w: abs(w[0]-start[0])+abs(w[1]-start[1]))
                    def bfs(sx,sy):
                        prev={(sx,sy):None}; q=deque([(sx,sy)])
                        while q:
                            c=q.popleft()
                            if c==(tgt[0],tgt[1]): break
                            for d,(dx,dy) in {'ArrowUp':(0,-1),'ArrowDown':(0,1),'ArrowLeft':(-1,0),'ArrowRight':(1,0)}.items():
                                n=(c[0]+dx,c[1]+dy)
                                if n not in prev and ok(*n): prev[n]=(c,d); q.append(n)
                        path=[]; c=(tgt[0],tgt[1])
                        while prev.get(c): c,d=prev[c]; path.append(d)
                        return path[::-1]
                    n=0; steps=0
                    for _ in range(400):
                        st = await pg.evaluate("({m:KDBG.S.mode,map:KDBG.S.mapId,x:KDBG.S.x,y:KDBG.S.y,busy:KDBG.S.busy})")
                        if st['m']=='battle':
                            n+=1
                            for _ in range(400):
                                await pg.keyboard.press('Enter'); await pg.wait_for_timeout(15)
                                if await pg.evaluate("KDBG.S.mode")!='battle': break
                            await pg.wait_for_timeout(200); continue
                        if st['map']!=mapid: break
                        if st['busy']: await pg.wait_for_timeout(50); continue
                        path=bfs(st['x'],st['y'])
                        if not path: break
                        await pg.keyboard.press(path[0]); steps+=1; await pg.wait_for_timeout(150)
                    fights.append(n); lens.append(steps)
                    await pg.close()
                res[(mapid,easy)]=(fights,lens)
                rate=8
                L=sum(lens)/len(lens)
                print(f"{mapid} {'easy' if easy else 'normal'}: fights {fights} avg {sum(fights)/len(fights):.1f} | steps avg {L:.0f} | old system expected ≈ {max(0,L-5)*rate/100:.1f}")
        print('errors', errs); await b.close()
asyncio.run(main())
