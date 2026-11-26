import asyncio, sys
from playwright.async_api import async_playwright
ENDING = sys.argv[1] if len(sys.argv)>1 else 'true'
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width':820,'height':860})
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: errs.append('console:'+m.text) if m.type=='error' else None)
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800); await pg.evaluate('KDBG.speed(0.05)'); await pg.evaluate('KDBG.mons(false)'); await pg.evaluate('KDBG.god(1)')
        async def k(key,n=1,w=70):
            for _ in range(n): await pg.keyboard.press(key); await pg.wait_for_timeout(w)
        async def S(expr): return await pg.evaluate(f"(()=>{{const S=KDBG.S;return {expr};}})()")
        async def settle(choices=(), maxn=4000):
            """推進對話、選項、戰鬥直到回到可操作狀態"""
            ch = list(choices)
            for _ in range(maxn):
                st = await S("({mode:S.mode,busy:S.busy,dlg:!!S.dialog,menus:S.menus.length,cls:(S.menus[S.menus.length-1]||{}).cls||'',ok:!!S.waitOk,card:!!S.card,board:!!S.board})")
                if st['card']: await k('Enter'); continue
                if st['board']: await k('Escape'); continue
                if st['mode']=='battle':
                    if st['ok']: await k('Enter'); continue
                    if st['menus']: await k('Enter',1,30); continue
                    await pg.wait_for_timeout(60); continue
                if st['cls']=='choice':
                    idx = ch.pop(0) if ch else 0
                    await k('ArrowDown', idx, 40); await k('Enter'); continue
                if st['mode'] in ('ending','gameover'):
                    if st['dlg']: await k('Enter',1,40); continue
                    return st['mode']
                if st['dlg']: await k('Enter',1,40); continue
                if not st['busy'] and not st['menus']: return 'free'
                await pg.wait_for_timeout(60)
            await pg.screenshot(path='/tmp/stuck.png'); print('STUCK', await S("JSON.stringify({mode:S.mode,busy:S.busy,dlg:S.dialog&&S.dialog.text,menus:S.menus.map(m=>m.cls+':'+m.title),log:S.battle&&S.battle.log,ok:!!S.waitOk})")); raise SystemExit
        async def talk(m,x,y,d,choices=(),lv=None):
            if lv:
                await pg.evaluate("KDBG.S.party.forEach(a=>{const sw=a.id==='hero'||a.id==='del'; a.equip.weapon=sw?'kb6':'pen5'; a.equip.armor=sw?'hv4':'ar5';})")
                await pg.evaluate(f"KDBG.level({lv})")
            await pg.evaluate(f"KDBG.warp('{m}',{x},{y})"); await pg.evaluate(f"KDBG.S.dir='{d}'")
            await k('Enter'); r = await settle(choices); return r
        async def step(m,x,y,key):
            await pg.evaluate(f"KDBG.warp('{m}',{x},{y})"); await k(key,1,200); return await settle()
        await k('Enter'); await k('Enter'); await settle()  # 開新串 → 難度選「普通」
        log = []
        async def chk(label):
            log.append((label, await S("S.goal"), await S("Object.keys(S.flags).filter(f=>!f.startsWith('chest')).length")))
        print('elder', await talk('village',6,5,'U')); await chk('elder')
        print('boss1', await talk('beach',11,13,'D',lv=40)); await chk('boss1')
        print('raid', await step('field1',1,9,'ArrowLeft')); await chk('raid')
        print('cat1', await talk('village',5,16,'L'))
        print('cat2', await talk('field1',23,3,'R'))
        print('cat3', await talk('village',5,16,'L'))
        print('sage', await talk('shinban',6,7,'U')); await chk('sage')
        print('fansub', await talk('shinban',19,15,'U'))
        print('xd', await talk('shinban',9,10,'U',choices=[0]))
        print('untag1', await talk('village',16,8,'U')); print('untag2', await talk('village',16,13,'U')); print('untag3', await talk('village',10,5,'U'))
        print('boss2', await talk('forest',22,4,'U',lv=40)); await chk('boss2')
        print('port', await step('valley',26,10,'ArrowRight'))
        print('gag', await talk('port',12,8,'U')); await chk('gag')
        print('troll', await talk('port',23,4,'R',choices=[0],lv=40)); await chk('troll')
        print('gallery', await step('valley',3,1,'ArrowUp'))
        print('del', await talk('gallery1',11,4,'U',lv=40)); await chk('del')
        print('tA', await talk('gallery2',3,8,'L')); print('tB', await talk('gallery2',18,8,'R')); print('tC', await talk('gallery2',3,13,'L'))
        print('mimic', await talk('gallery2',18,13,'R'))
        print('seal', await talk('gallery2',11,7,'U'))
        print('boss4', await talk('gallery2',11,4,'U',lv=40)); await chk('boss4')
        print('mid', await step('gallery2',11,13,'ArrowDown')); await chk('mid')
        print('inv stones', await S("['stone1','stone2','stone3'].map(i=>S.inv[i]||0).join(',')"))
        print('sail', await talk('port',7,11,'D',choices=[0])); await chk('fgate')
        print('mapnow', await S("S.mapId"))
        print('gate', await talk('fgate',12,2,'U',lv=40))
        print('p1', await talk('fin',8,8,'L')); print('p2', await talk('fin',15,8,'R')); print('p3', await talk('fin',2,14,'U'))
        print('general', await talk('fin',12,9,'U',lv=40)); await chk('general')
        print('snow', await talk('fin',12,3,'U',choices=[0 if ENDING=='true' else 1],lv=40)); await chk('snow')
        print('mapnow', await S("S.mapId"), await S("S.x+','+S.y"))
        await pg.evaluate("KDBG.give('frag',5)")
        print('guardian', await talk('village',15,5,'U'))
        print('equip kb6', await S("S.inv.kb6||0"))
        print('abyss', await step('village',13,4,'ArrowUp'))
        print('karma', await S("S.karma"), 'quests', await S("JSON.stringify(S.quests)"))
        if ENDING=='real': await pg.evaluate("KDBG.S.karma=0")
        r = await talk('core',8,5,'U',choices=[0 if ENDING!='anon' else 1],lv=40)
        print('final ->', r, await S("S.ending && S.ending.id"))
        await pg.screenshot(path=f'/tmp/end_{ENDING}.png')
        for l in log: print(l)
        print('errors', errs)
        await b.close()
asyncio.run(main())
