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
        async def items(): return await S("JSON.stringify(S.inv)")
        lines=[]
        orig_say = None
        await pg.evaluate("""(()=>{window.__said=[]; const o=Object.getOwnPropertyDescriptor; setInterval(()=>{const d=KDBG.S.dialog; if(d&&d.text&&window.__said[window.__said.length-1]!==d.speaker+'：'+d.text) window.__said.push(d.speaker+'：'+d.text);},15);})()""")
        async def said(n=6): r = await pg.evaluate(f"window.__said.slice(-{n})"); await pg.evaluate("window.__said=[]"); return r
        await pg.evaluate("KDBG.level(10)")
        print('bday pre-raid', await talk('village',12,12,'U',[0]), await said(3), 'cake', await S("S.inv.cake||0"))
        print('yijing', await talk('village',8,9,'U'), await said(4))
        print('teri A', await talk('village',17,6,'U',[1]), await said(8), 'quest', await S("JSON.stringify(S.quests)"))
        for f in ['boss1','raidDone','tagged']: await pg.evaluate(f"KDBG.flag('{f}')")
        print('bday quest', await talk('village',12,12,'U'), (await said(12))[-2:], await S("S.quests.bday"))
        print('zz', await talk('shinban',15,7,'U',[0,0],lv=12), (await said(30))[-6:], 'friend', await S("!!S.flags.zzFriend"), 'fig', await S("S.inv.acc_figure||0"), 'cards', await S("S.inv.card||0"), 'karma', await S("S.karma"))
        print('fangshi', await talk('shinban',3,16,'U'), 'cards', await S("S.inv.card||0"))
        print('teri B', await talk('shinban',16,9,'U',[1]), 'cards', await S("S.inv.card||0"))
        print('chest b', await talk('beach',20,4,'U')); print('chest f', await talk('forest',24,6,'R')); print('chest v', await talk('valley',26,2,'U'))
        print('sauce', await S("S.inv.sauce||0"))
        print('teri B again', await talk('shinban',16,9,'U',[1]), 'apron', await S("S.inv.acc_apron||0"), 'teriDone', await S("!!S.flags.teriDone"), 'menu', await pg.evaluate("[...document.querySelectorAll('.menu.active li')].map(l=>l.textContent).join('|')"))
        await pg.evaluate("KDBG.closeUI()")
        for f in ['boss2','boss3']: await pg.evaluate(f"KDBG.flag('{f}')")
        print('lion', await talk('port',20,9,'U'), 'wmDone', await S("!!S.flags.wmDone"), 'cards', await S("S.inv.card||0"))
        print('watermelon', await talk('port',18,8,'U'), 'cards', await S("S.inv.card||0"))
        print('huangmao (no pen)', await talk('gallery1',16,7,'U'), 'cards', await S("S.inv.card||0"))
        print('party!', await talk('village',12,12,'U'), (await said(20))[-4:], 'hat', await S("S.inv.acc_party||0"), 'done', await S("S.quests.bday"), 'karma', await S("S.karma"), 'cards', await S("S.inv.card||0"))
        print('quests', await S("JSON.stringify(S.quests)"))
        # 討論板
        await pg.evaluate("void KDBG.run([['board','b_village']])"); await pg.wait_for_timeout(200)
        print('board posts', await pg.evaluate("document.querySelectorAll('.board .post').length"), await pg.evaluate("[...document.querySelectorAll('.board .pb')].slice(-2).map(p=>p.innerText.split('\\n')[0])"))
        await k('Escape'); await settle()
        await pg.evaluate("KDBG.join('sage'); KDBG.join('gag'); KDBG.join('del')")
        print('skits', await S("KDBG.D.skits.filter(k=>['bday1','teri1','zz1'].includes(k.id)).map(k=>k.id)"))
        # 最後的回應：確認新角色的台詞
        voices = await S("JSON.stringify(KDBG.D.maps.core.ents[0].script).match(/生日哥|照燒貓|智障神|西瓜哥|獅子老大|黃毛|慕內/g)")
        print('final voices', voices)
        print('errors', errs)
        await b.close()
asyncio.run(main())
