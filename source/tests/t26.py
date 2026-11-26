# 全自動模式：從標題選「全自動」開新串，什麼都不按，看它能不能自己玩到結局。
# 用法：python3 source/tests/t26.py [最長分鐘數=40] [速度倍率=0.02]
# 每 5 秒印一次進度；卡住（旗標數 3 分鐘沒變）就截圖並印出狀態。
import asyncio, sys, time, json
from playwright.async_api import async_playwright

MAXMIN = float(sys.argv[1]) if len(sys.argv) > 1 else 40
SPD = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02
MAIN = len(sys.argv) > 3 and sys.argv[3] == 'main'   # 第三個參數 main：只跑主線

STATE = """(()=>{const S=KDBG.S;return {mode:S.mode,map:S.mapId,x:S.x,y:S.y,flags:Object.keys(S.flags).filter(f=>!f.startsWith('chest')).length,
 chests:Object.keys(S.flags).filter(f=>f.startsWith('chest')).length,lv:S.party.map(a=>a.id+a.level).join(','),karma:S.karma,gold:S.gold,
 note:S.autoNote,goal:S.goal,auto:S.auto,easy:S.easy,busy:S.busy,dlg:S.dialog&&S.dialog.text,menus:S.menus.map(m=>(m.cls||'')+':'+(m.title||'')),
 quests:S.quests,ending:S.ending&&S.ending.id,card:S.ending&&S.ending.card,battle:S.battle&&S.battle.enemies.map(e=>e.name+':'+e.hp).join(','),
 equip:S.party.map(a=>Object.values(a.equip).join('/')).join(' | ')};})()"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={'width': 820, 'height': 860})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('console:' + m.text) if m.type == 'error' else None)
        await pg.goto('http://localhost:8765/index.html'); await pg.wait_for_timeout(800)
        await pg.evaluate(f'KDBG.speed({SPD})')
        await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)          # 開新串
        await pg.keyboard.press('ArrowDown'); await pg.keyboard.press('ArrowDown')  # 全自動
        await pg.keyboard.press('Enter')
        if MAIN: await pg.evaluate('KDBG.S.autoMain = true')
        t0 = time.time(); last_flags = -1; last_change = time.time(); shots = 0
        while time.time() - t0 < MAXMIN * 60:
            await pg.wait_for_timeout(5000)
            st = await pg.evaluate(STATE)
            el = int(time.time() - t0)
            print(f"[{el//60:02d}:{el%60:02d}] {st['mode']:6} {st['map']:8} flags={st['flags']:3} chests={st['chests']:2} lv={st['lv']} k={st['karma']} g={st['gold']} | {st['note']}", flush=True)
            if st['ending'] and st['card']:
                print('ENDING', st['ending'], 'quests', json.dumps(st['quests'], ensure_ascii=False))
                print('equip', st['equip'])
                await pg.screenshot(path='/tmp/t26_end.png')
                break
            if st['flags'] != last_flags:
                last_flags = st['flags']; last_change = time.time()
            elif time.time() - last_change > 180:
                print('STALL', json.dumps(st, ensure_ascii=False))
                print('targets', await pg.evaluate('KDBG.autoTargets()'))
                await pg.screenshot(path=f'/tmp/t26_stall{shots}.png'); shots += 1
                last_change = time.time()
                if shots >= 3: break
        else:
            print('TIMEOUT', json.dumps(await pg.evaluate(STATE), ensure_ascii=False))
        print('errors', errs[:10])
        await b.close()

asyncio.run(main())
