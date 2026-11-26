// 戰鬥平衡模擬器：用和遊戲相同的公式，讓簡單 AI 打各個魔王與一般敵群
// 用法：node sim.js ../KomicaRPG/wwwroot/data/game.json
const D = require(process.argv[2]);
const rnd = n => Math.floor(Math.random() * n);
const expFor = L => Math.round(D.expCurve.mul * Math.pow(L - 1, D.expCurve.pow));

function actor(id, level, equip) {
  const d = D.actors[id];
  const a = { id, side: 'p', level, equip: Object.assign({ acc: null }, equip), st: {} };
  a.stat = k => Math.max(1, Math.floor(d.base[k] + d.growth[k] * (level - 1)) + ['weapon', 'armor', 'acc'].reduce((s, sl) => s + ((a.equip[sl] && D.items[a.equip[sl]].stats || {})[k] || 0), 0));
  a.maxHp = a.stat('hp'); a.maxMp = a.stat('mp'); a.hp = a.maxHp; a.mp = a.maxMp;
  a.skills = d.skills.filter(([lv]) => lv <= level).map(([, s]) => s);
  a.name = d.name;
  return a;
}
function enemy(id) { const def = D.enemies[id]; return { id, def, side: 'e', name: def.name, hp: def.hp, maxHp: def.hp, st: {}, stat: k => def[k], lowUsed: false }; }
function uStat(u, k) { let v = u.stat(k); if (k === 'atk') { if (u.st.atkUp) v *= 1.3; if (u.st.atkDown) v *= 0.7; } if (k === 'def') { if (u.st.defUp) v *= 1.3; if (u.st.defDown) v *= 0.7; } return v; }
const em = (t, e) => t.side !== 'e' ? 1 : (t.def.weak || []).includes(e) ? 1.5 : (t.def.resist || []).includes(e) ? 0.5 : 1;
const phys = (u, t, p) => Math.max(1, uStat(u, 'atk') * p - uStat(t, 'def') * 0.5) * (0.9 + Math.random() * 0.2);
const mag = (u, t, sk) => Math.max(1, uStat(u, 'mag') * (sk.power || 1) + (sk.base || 0) - uStat(t, 'def') * 0.25) * (0.9 + Math.random() * 0.2);

function fight(party, troop, items, opts = {}) {
  const P = party.map(a => Object.assign(Object.create(Object.getPrototypeOf(a)), a, { st: {}, hp: a.hp, mp: a.mp }));
  const E = D.troops[troop].map(enemy);
  const inv = Object.assign({}, items);
  if (opts.buff) P.forEach(a => a.st[opts.buff] = 99);
  const alive = u => u.hp > 0;
  const ap = () => P.filter(alive), ae = () => E.filter(alive);
  let turn = 0;
  const dmg = (u, t, d, elem) => {
    if (t.guard) d *= 0.5;
    if (t.st.hidden && elem !== 'holy' && Math.random() < 0.75) return;
    if (elem === 'holy') delete t.st.hidden;
    t.hp = Math.max(0, t.hp - Math.max(1, Math.round(d)));
    delete t.st.sleep;
  };
  const addSt = (t, st, ch, tu) => {
    if (!st || !alive(t)) return;
    const imm = t.side === 'e' ? (t.def.immune || []) : ((t.equip.acc && D.items[t.equip.acc].immune) || []);
    if (imm.includes(st)) return;
    if (Math.random() * 100 < (ch == null ? 100 : ch)) t.st[st] = Math.max(t.st[st] || 0, tu || 3);
  };
  const hitP = (u, t, p, elem) => {
    if (Math.random() < 0.04) return;
    let d = phys(u, t, p) * em(t, elem);
    if (u.side === 'p' && Math.random() < 0.06) d *= 1.5;
    dmg(u, t, d, elem);
    if (alive(t) && alive(u) && t.st.counter && t.side !== u.side) dmg(t, u, phys(t, u, 1.5));
  };
  const pick = (u, list) => { if (u.side === 'e') { const tn = list.filter(x => x.st.taunt); if (tn.length && Math.random() < 0.75) return tn[rnd(tn.length)]; } return list[rnd(list.length)]; };
  const useSkill = (u, skId, chosen) => {
    const sk = D.skills[skId];
    const opp = u.side === 'e' ? ap() : ae(), mine = u.side === 'e' ? ae() : ap();
    if (sk.kind === 'special') {
      if (sk.fx === 'summon' && ae().length < 3) E.push(enemy(sk.summon));
      if (sk.fx === 'healself') u.hp = Math.min(u.maxHp, u.hp + Math.floor(u.maxHp * sk.rate));
      if (sk.fx === 'explode') { for (const t of ap()) dmg(u, t, sk.base * (0.9 + Math.random() * 0.2) - uStat(t, 'def') * 0.25); u.hp = 0; }
      return;
    }
    if (sk.target === 'random3') { for (let i = 0; i < 3; i++) { const o = u.side === 'e' ? ap() : ae(); if (!o.length) break; hitP(u, o[rnd(o.length)], sk.power, sk.elem || 'phys'); } return; }
    let ts;
    switch (sk.target) {
      case 'enemy': ts = chosen && alive(chosen) ? [chosen] : opp.length ? [pick(u, opp)] : []; break;
      case 'enemies': ts = opp; break;
      case 'ally': ts = chosen ? [chosen] : [mine.sort((a, b) => a.hp / a.maxHp - b.hp / b.maxHp)[0]]; break;
      case 'allies': ts = mine.concat(sk.revive ? P.filter(x => !alive(x)) : []); break;
      case 'self': ts = [u]; break;
      case 'deadAlly': ts = chosen ? [chosen] : []; break;
    }
    for (const t of ts) {
      if (!t) continue;
      if (sk.kind === 'phys') { hitP(u, t, sk.power, sk.elem || 'phys'); if (sk.fx === 'delete' && alive(t) && t.side === 'e' && !t.def.boss && t.hp < t.maxHp * 0.3) t.hp = 0; if (sk.fx === 'drain') u.hp = Math.min(u.maxHp, u.hp + uStat(u, 'atk') * 0.4); addSt(t, sk.status, sk.chance, sk.turns); }
      else if (sk.kind === 'mag') { if (t.st.hidden && sk.elem !== 'holy' && Math.random() < 0.75) continue; dmg(u, t, mag(u, t, sk) * em(t, sk.elem), sk.elem); addSt(t, sk.status, sk.chance, sk.turns); }
      else if (sk.kind === 'heal') { if (!alive(t)) { if (sk.revive) t.hp = Math.floor(t.maxHp * 0.5); continue; } t.hp = Math.min(t.maxHp, t.hp + (sk.base || 0) + uStat(u, 'mag') * (sk.power || 0)); }
      else if (sk.kind === 'revive') { if (!alive(t)) t.hp = Math.floor(t.maxHp * (sk.rate || 0.5)); }
      else if (sk.kind === 'buff') { addSt(t, sk.status, 100, sk.turns); if (sk.status2) addSt(t, sk.status2, 100, sk.turns); }
      else if (sk.kind === 'debuff') { addSt(t, sk.status, sk.chance, sk.turns); if (sk.status2) addSt(t, sk.status2, sk.chance2, sk.turns); }
      else if (sk.kind === 'cure') for (const k of ['burn', 'silence', 'confuse', 'sleep']) delete t.st[k];
    }
  };
  // 隊伍 AI
  const plan = a => {
    const boss = E.find(e => alive(e) && e.def.boss);
    const ev = boss && boss.def.ai.every;
    const bigNext = ev && turn % ev[0] === 0 && D.skills[ev[1]].target === 'enemies' && D.skills[ev[1]].kind !== 'debuff';
    const dead = P.filter(x => !alive(x));
    const low = ap().filter(x => x.hp < x.maxHp * 0.4).sort((x, y) => x.hp - y.hp);
    const canSilence = a.st.silence;
    const has = s => !canSilence && a.skills.includes(s) && a.mp >= D.skills[s].mp;
    if (dead.length) { if (has('age')) return ['skill', 'age', dead[0]]; if (inv.revive > 0) { inv.revive--; return ['item', 'revive', dead[0]]; } }
    if (a.st.silence && inv.tea > 0 && Math.random() < 0.6) { inv.tea--; delete a.st.silence; return ['wait']; }
    if (low.length >= 2) { for (const s of ['last', 'song', 'www']) if (has(s)) return ['skill', s]; }
    if (low.length) {
      for (const s of ['reply', 'www']) if (has(s)) return ['skill', s, low[0]];
      for (const it of ['chicken', 'noodle2', 'noodle']) if (inv[it] > 0 && low[0].hp < low[0].maxHp * 0.3) { inv[it]--; const h = D.items[it].heal; low[0].hp = Math.min(low[0].maxHp, low[0].hp + h); return ['wait']; }
    }
    if (bigNext && a.id !== 'gag') return ['defend'];
    if (turn === 1 && boss) { if (has('taunt')) return ['skill', 'taunt']; if (has('cheer')) return ['skill', 'cheer']; if (has('follow')) return ['skill', 'follow']; if (has('guard')) return ['skill', 'guard']; }
    if (a.mp < a.maxMp * 0.15 && inv.boba > 0 && boss) { inv.boba--; a.mp = Math.min(a.maxMp, a.mp + 70); return ['wait']; }
    if (a.mp < a.maxMp * 0.15 && inv.cola > 0 && boss) { inv.cola--; a.mp = Math.min(a.maxMp, a.mp + 25); return ['wait']; }
    // 攻擊：挑期望傷害最高的技能
    const tgt = boss || ae().sort((x, y) => x.hp - y.hp)[0];
    let best = ['attack', null, tgt], bestV = uStat(a, 'atk') - uStat(tgt, 'def') * 0.5;
    const reserve = ['sage', 'gag'].includes(a.id) || a.id === 'hero' ? 0.25 : 0;
    for (const s of a.skills) {
      const sk = D.skills[s];
      if (!has(s) || (a.mp - sk.mp) < a.maxMp * reserve * (sk.kind === 'heal' ? 0 : 1)) continue;
      let v = 0;
      if (sk.kind === 'phys') v = (uStat(a, 'atk') * sk.power - uStat(tgt, 'def') * 0.5) * em(tgt, sk.elem || 'phys') * (sk.target === 'random3' ? 3 : sk.target === 'enemies' ? ae().length : 1);
      if (sk.kind === 'mag') v = (uStat(a, 'mag') * sk.power + (sk.base || 0) - uStat(tgt, 'def') * 0.25) * em(tgt, sk.elem) * (sk.target === 'enemies' ? ae().length : 1);
      if (tgt.st.hidden && sk.elem === 'holy') v *= 4;
      if (v > bestV * 1.15) { bestV = v; best = ['skill', s, tgt]; }
    }
    return best;
  };
  while (turn < 60) {
    turn++;
    const acts = [];
    for (const a of ap()) {
      if (a.st.sleep) { acts.push({ u: a, k: ['sleep'], pri: 0 }); continue; }
      const k = a.st.confuse ? ['confused'] : plan(a);
      acts.push({ u: a, k, pri: k[0] === 'defend' ? 1e4 : uStat(a, 'spd') * (0.75 + Math.random() * 0.5) });
    }
    for (const e of ae()) {
      const ai = e.def.ai;
      let s;
      if (e.st.silence) s = 'e_attack';
      else if (ai.low && !e.lowUsed && e.hp <= e.maxHp * ai.low[0]) { e.lowUsed = true; s = ai.low[1]; }
      else if (ai.every && turn % ai.every[0] === 0) s = ai.every[1];
      else { let r = Math.random() * ai.pattern.reduce((x, p) => x + p[1], 0); for (const [sk, w] of ai.pattern) { r -= w; if (r < 0) { s = sk; break; } } s = s || ai.pattern[0][0]; }
      acts.push({ u: e, k: ['skill', s], pri: (D.skills[s].first ? 5000 : 0) + e.def.spd * (0.75 + Math.random() * 0.5) });
    }
    acts.sort((x, y) => y.pri - x.pri);
    for (const ac of acts) if (ac.k[0] === 'defend') ac.u.guard = true;
    for (const { u, k } of acts) {
      if (!alive(u) || u.st.sleep) continue;
      if (u.st.confuse || k[0] === 'confused') { const pool = [...ap(), ...ae()].filter(x => x !== u); if (pool.length) hitP(u, pool[rnd(pool.length)], 1, 'phys'); }
      else if (k[0] === 'attack') { const o = u.side === 'e' ? ap() : ae(); if (o.length) hitP(u, alive(k[2]) ? k[2] : o[0], 1, 'phys'); }
      else if (k[0] === 'skill') { if (u.side === 'p') { if (u.st.silence || u.mp < D.skills[k[1]].mp) continue; u.mp -= D.skills[k[1]].mp; } useSkill(u, k[1], k[2]); }
      if (E.some(e => alive(e) && e.def.yieldAt && e.hp <= e.maxHp * e.def.yieldAt) || !ae().length) return { win: true, turn, hp: P.reduce((s, a) => s + a.hp, 0) / P.reduce((s, a) => s + a.maxHp, 0), inv };
      if (!ap().length) return { win: false, turn };
    }
    for (const u of [...ap(), ...ae()]) {
      u.guard = false;
      if (u.st.burn) u.hp = Math.max(0, u.hp - Math.max(1, u.side === 'e' ? Math.min(Math.floor(u.maxHp * 0.05), 90) : Math.floor(u.maxHp * 0.06)));
      for (const kk of Object.keys(u.st)) { if (kk === 'confuse' && Math.random() < 0.3) u.st[kk] = 1; if (--u.st[kk] <= 0) delete u.st[kk]; }
    }
    if (!ae().length) return { win: true, turn, hp: 1, inv };
    if (!ap().length) return { win: false, turn };
  }
  return { win: false, turn, timeout: true };
}

function report(label, party, troop, items, n = 300, opts) {
  let w = 0, turns = 0, hp = 0, to = 0;
  for (let i = 0; i < n; i++) { const r = fight(party, troop, items, opts); if (r.win) { w++; turns += r.turn; hp += r.hp; } if (r.timeout) to++; }
  console.log(`${label.padEnd(22)} 勝率 ${(w / n * 100).toFixed(0).padStart(3)}%  平均回合 ${(turns / Math.max(1, w)).toFixed(1).padStart(4)}  剩餘HP ${(hp / Math.max(1, w) * 100).toFixed(0).padStart(3)}%${to ? '  timeout ' + to : ''}`);
}

const H = (lv, w, a, acc) => actor('hero', lv, { weapon: w, armor: a, acc });
const SG = (lv, w, a, acc) => actor('sage', lv, { weapon: w, armor: a, acc });
const GG = (lv, w, a, acc) => actor('gag', lv, { weapon: w, armor: a, acc });
const DL = (lv, w, a, acc) => actor('del', lv, { weapon: w, armor: a, acc });

const it1 = { noodle: 6, tea: 2 };
const it2 = { noodle: 4, noodle2: 4, tea: 3, revive: 1, cola: 2 };
const it3 = { noodle2: 6, tea: 3, revive: 2, cola: 3 };
const it4 = { noodle2: 8, tea: 3, revive: 3, cola: 3, boba: 2 };
const it5 = { chicken: 4, noodle2: 6, revive: 3, boba: 3, tea: 3 };
const it6 = { chicken: 6, revive: 4, boba: 4, tea: 4 };


for (const lv of [6,7,8,9]) {
  report('zz 智障神 Lv'+lv+' 無名氏+莎吉', [H(lv, lv>=8?'kb2':'kb1', lv>=8?'hv2':'hv1'), SG(lv, lv>=8?'pen2':'pen1', lv>=8?'ar2':'ar1')], 'zz', it2);
}
report('zz 智障神 Lv7 只有無名氏', [H(7, 'kb2', 'hv1')], 'zz', it2);
report('boss2 捏他魔 Lv9 (對照)', [H(9, 'kb2', 'hv2'), SG(9, 'pen2', 'ar2')], 'boss2', it2);
