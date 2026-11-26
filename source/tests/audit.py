import json, os, re, collections
D=json.load(open(__import__('os').path.join(__import__('os').path.dirname(__file__),'..','..','data','game.json'),encoding='utf-8'))
issues=[]
set_flags=collections.defaultdict(list); used_flags=collections.defaultdict(list)
items=D['items']; skills=D['skills']; enemies=D['enemies']; troops=D['troops']; shops=D['shops']; quests=D['quests']; calls=D['calls']; maps=D['maps']
KNOWN={'say','hand','if','choice','flag','unflag','give','take','gold','goal','quest','karma','chapter','board','battle','join','heal','inn','shop','warp','save','ending','call'}
def cond_terms(c, where):
    if not c: return
    for alt in c.split('|'):
        for t in alt.split('&'):
            t=t.strip()
            while t.startswith('!'): t=t[1:]
            if t.startswith('flag:'): used_flags[t[5:]].append(where)
            elif t.startswith('item:'):
                iid=t[5:].split('>=')[0]
                if iid not in items: issues.append(('cond unknown item',where,t))
            elif t.startswith('party:'):
                if t[6:] not in D['actors']: issues.append(('cond unknown actor',where,t))
            elif t.startswith('karma>=') or t.startswith('gold>='): pass
            else: issues.append(('bad cond term',where,repr(t)))
def walkable(mid,x,y):
    m=maps[mid]
    if not(0<=y<len(m['rows']) and 0<=x<len(m['rows'][0])): return False
    return D['tiles'][m['rows'][y][x]][1] if len(D['tiles'][m['rows'][y][x]])>1 else True
def scan(sc, where):
    if not isinstance(sc,list): issues.append(('script not list',where)); return
    for c in sc:
        if not isinstance(c,list) or not c: issues.append(('bad cmd',where,c)); continue
        op=c[0]
        if op not in KNOWN: issues.append(('unknown op',where,op)); continue
        if op in ('say','hand'):
            for t in c[2:]:
                for m in re.findall(r'\{(\w+):(\w+)\}', t):
                    if not (m[0]=='item' and m[1] in items): issues.append(('bad placeholder',where,m))
        elif op=='if': cond_terms(c[1],where); scan(c[2],where); scan(c[3] if len(c)>3 else [],where)
        elif op=='choice':
            for opt in c[1:]: scan(opt[1],where)
        elif op=='flag': set_flags[c[1]].append(where)
        elif op in('give','take'):
            if c[1] not in items: issues.append((op+' unknown item',where,c[1]))
        elif op=='quest':
            if c[1] not in quests: issues.append(('unknown quest',where,c[1]))
        elif op=='battle':
            if c[1] not in troops: issues.append(('unknown troop',where,c[1]))
        elif op=='join':
            if c[1] not in D['actors']: issues.append(('unknown actor',where,c[1]))
        elif op=='shop':
            if c[1] not in shops: issues.append(('unknown shop',where,c[1]))
        elif op=='warp':
            if c[1] not in maps: issues.append(('warp unknown map',where,c[1]))
            elif not walkable(c[1],c[2],c[3]): issues.append(('warp to blocked tile',where,c[1:4]))
        elif op=='ending':
            if c[1] not in D['endings']: issues.append(('unknown ending',where,c[1]))
        elif op=='call':
            if c[1] not in calls: issues.append(('unknown call',where,c[1]))
        elif op=='board':
            if c[1] not in D['boards']: issues.append(('unknown board',where,c[1]))
scan(D['start']['script'],'start')
for iid in D['start']['items']: 
    if (iid[0] if isinstance(iid,list) else iid) not in items: issues.append(('start item',iid))
for k,v in calls.items(): scan(v,'call:'+k)
for mid,m in maps.items():
    W=len(m['rows'][0])
    for r in m['rows']:
        if len(r)!=W: issues.append(('ragged map',mid))
    for e in m['ents']:
        w=f'{mid}:{e["id"]}'
        scan(e.get('script',[]),w); cond_terms(e.get('show'),w); cond_terms(e.get('mark'),w)
        if e.get('chest'):
            ch=e['chest']; 
        if 'auto' in e: pass
    au=m.get('auto')
    if au:
        for a in (au if isinstance(au,list) else [au]):
            if isinstance(a,dict): cond_terms(a.get('cond'),mid+':auto'); scan(a['script'],mid+':auto')
            elif isinstance(a,list) and a and isinstance(a[0],str) and a[0] not in KNOWN: cond_terms(a[0],mid+':auto'); scan(a[1],mid+':auto')
            else: scan(a if isinstance(a[0],list) else [a],mid+':auto')
    for wp in m['warps']:
        if wp[2] not in maps: issues.append(('warp map',mid,wp))
        elif not walkable(wp[2],wp[3],wp[4]): issues.append(('warp dest blocked',mid,wp))
    if m.get('enc'):
        for t in m['enc']['troops']:
            if t[0] not in troops: issues.append(('enc troop',mid,t))
for sk in D['skits']:
    cond_terms(sk.get('cond'),'skit:'+sk['id']); scan(sk['script'],'skit:'+sk['id'])
for bid,b in D['boards'].items():
    for i,p in enumerate(b['posts']):
        cond_terms(p.get('cond'),f'board:{bid}:{i}')
        for m in re.findall(r'\{no:(\d+)\}',p['text']):
            if int(m)>=len(b['posts']): issues.append(('board no ref out of range',bid,i))
for t in D['travel']:
    cond_terms(t.get('cond'),'travel:'+t['map'])
    if not walkable(t['map'],t['x'],t['y']): issues.append(('travel blocked',t))
for k,e in D['endings'].items():
    if isinstance(e,dict) and 'script' in e: scan(e['script'],'ending:'+k)
# troops / enemies / skills / items
for k,t in troops.items():
    ens = t['enemies'] if isinstance(t,dict) else t
    for en in ens:
        if en not in enemies: issues.append(('troop enemy',k,en))
for k,e in enemies.items():
    ai=e['ai']
    sids=[p[0] for p in ai.get('pattern',[])]+([ai['every'][1]] if 'every' in ai else [])+([ai['low'][1]] if 'low' in ai else [])
    for sid in sids:
        if sid not in skills: issues.append(('enemy ai skill',k,sid))
    for d in e.get('drops',[]):
        if d[0] not in items: issues.append(('drop item',k,d))
    for el in e.get('weak',[])+e.get('resist',[]):
        if el not in D['elements']: issues.append(('element',k,el))
for k,a in D['actors'].items():
    for lv,sid in a.get('skills',[]):
        if sid not in skills: issues.append(('learn skill',k,sid))
    for sl,iid in (a.get('equip') or {}).items():
        if iid and iid not in items: issues.append(('actor equip',k,iid))
for k,sh in shops.items():
    for iid in sh:
        if iid not in items: issues.append(('shop item',k,iid))
for k,s in skills.items():
    for st in [s.get('status'), s.get('cure')]:
        if isinstance(st,str) and st not in D['statuses'] and st!='all': issues.append(('skill status',k,st))
    if s.get('elem') and s['elem'] not in D['elements']: issues.append(('skill elem',k,s['elem']))
for k,it in items.items():
    for st in [it.get('status'), it.get('cure')]:
        if isinstance(st,str) and st not in D['statuses'] and st!='all': issues.append(('item status',k,st))
for c in D['combos'].values() if isinstance(D['combos'],dict) else D['combos']:
    pass
print('ISSUES:'); [print(' ',i) for i in issues]
print('flags used but never set:', {f:v[:2] for f,v in used_flags.items() if f not in set_flags})
print('flags set but never used:', [f for f in set_flags if f not in used_flags])
print('troop sample', list(troops.items())[0], '| enemy ai sample', enemies['worm']['ai'], '| actor keys', list(D['actors']['hero'].keys()))
print('skill sample', skills['flame']); print('ending sample keys', list(D['endings']['true'].keys()) if isinstance(D['endings']['true'],dict) else D['endings']['true'])
print('combos', D['combos'])
