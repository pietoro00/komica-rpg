/* 糟糕島物語 ～無名氏與最後的回應～  網頁版引擎
 * 讀取 data/game.json（與 Blazor 版共用同一份資料）
 */
'use strict';

const T = 48, VW = 16, VH = 12;
const SAVE_KEY = 'komica_rpg_save_v1', META_KEY = 'komica_rpg_meta_v1';
let D = null;   // 遊戲資料
let S = null;   // 遊戲狀態
const STOP = Symbol('stop');

const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
let SPEED = 1, GOD = false;
/* 簡單模式的倍率：敵人 HP、我方受到的傷害、經驗值與 K 幣 */
const EASY = { enemyHp: 0.7, dmgTaken: 0.6, reward: 1.5 };
/* 明雷怪的經驗值與 K 幣倍率：怪物看得到、躲得掉，遇到的場數比以前的暗雷少，用這個補回升級速度 */
const MON_REWARD = 1.8;
const BSPEEDS = [1, 0.6, 0.35], BSPEED_NAMES = ['普通', '快', '超快'];
let bspeed = 0;
const bwait = ms => wait(ms * BSPEEDS[bspeed]);
const wait = ms => new Promise(r => setTimeout(r, ms * SPEED));
const rnd = n => Math.floor(Math.random() * n);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const pct = (a, b) => clamp(Math.floor(a * 100 / Math.max(1, b)), 0, 100);

/* ================================================================ 角色與數值 */
const ad = a => D.actors[a.id];
function expFor(L) { return Math.round(D.expCurve.mul * Math.pow(L - 1, D.expCurve.pow)); }
function baseStat(a, k) { const d = ad(a); return Math.floor(d.base[k] + d.growth[k] * (a.level - 1)); }
function equipStat(a, k) {
  let s = 0;
  for (const slot of ['weapon', 'armor', 'acc']) {
    const id = a.equip[slot];
    const st = id && D.items[id].stats;
    if (st && st[k]) s += st[k];
  }
  return s;
}
function stat(a, k) { return Math.max(1, baseStat(a, k) + equipStat(a, k)); }
const maxHp = a => stat(a, 'hp'), maxMp = a => stat(a, 'mp');
function skillsOf(a) { return ad(a).skills.filter(([lv]) => lv <= a.level).map(([, id]) => id); }
function immunesOf(a) { const acc = a.equip.acc; return (acc && D.items[acc].immune) || []; }
function makeActor(id, level) {
  const d = D.actors[id];
  const a = { id, level, exp: expFor(level), hp: 0, mp: 0, equip: Object.assign({}, d.equip), st: {} };
  a.hp = maxHp(a); a.mp = maxMp(a);
  return a;
}
function canEquip(a, itemId) {
  const it = D.items[itemId], d = ad(a);
  if (it.type === 'weapon') return d.wtypes.includes(it.wtype);
  if (it.type === 'armor') return d.atypes.includes(it.atype);
  return it.type === 'acc';
}
function gainExp(a, n) {
  const lines = [];
  a.exp += n;
  while (a.level < D.maxLevel && a.exp >= expFor(a.level + 1)) {
    const oh = maxHp(a), om = maxMp(a), before = new Set(skillsOf(a));
    a.level++;
    a.hp += maxHp(a) - oh; a.mp += maxMp(a) - om;
    lines.push(`${ad(a).name}升到了 Lv ${a.level}！`);
    for (const s of skillsOf(a)) if (!before.has(s)) lines.push(`${ad(a).name}學會了「${D.skills[s].name}」！`);
  }
  return lines;
}

/* ---- 戰鬥單位（隊員或敵人）共用 ---- */
const isEnemy = u => u.side === 'enemy';
const uname = u => isEnemy(u) ? u.name : ad(u).name;
const alive = u => u.hp > 0;
const uMaxHp = u => isEnemy(u) ? u.maxHp : maxHp(u);
function uStat(u, k) {
  let v = isEnemy(u) ? u.def[k] : stat(u, k);
  const st = u.st || {};
  if (k === 'atk') { if (st.atkUp) v *= 1.3; if (st.atkDown) v *= 0.7; }
  if (k === 'def') { if (st.defUp) v *= 1.3; if (st.defDown) v *= 0.7; }
  return v;
}
function elemMult(t, elem) {
  if (!isEnemy(t)) return 1;
  if ((t.def.weak || []).includes(elem)) return 1.5;
  if ((t.def.resist || []).includes(elem)) return 0.5;
  return 1;
}
function physDamage(u, t, power) { return Math.max(1, uStat(u, 'atk') * power - uStat(t, 'def') * 0.5) * (0.9 + Math.random() * 0.2); }
function magDamage(u, t, sk) { return Math.max(1, uStat(u, 'mag') * (sk.power || 1) + (sk.base || 0) - uStat(t, 'def') * 0.25) * (0.9 + Math.random() * 0.2); }
function healAmount(u, sk) { return Math.round(((sk.base || 0) + uStat(u, 'mag') * (sk.power || 0)) * (0.95 + Math.random() * 0.1)); }

/* ================================================================ 條件與文字 */
function itemCount(id) { return S.inv[id] || 0; }
// st：要檢查的狀態（省略時是目前的遊戲狀態；全自動模式「預演」腳本時會傳入一份複本）
function condTerm(t, st) {
  st = st || S;
  t = t.trim();
  if (t.startsWith('!')) return !condTerm(t.slice(1), st);
  if (t.startsWith('flag:')) return !!st.flags[t.slice(5)];
  if (t.startsWith('item:')) { const [id, n] = t.slice(5).split('>='); return (st.inv[id] || 0) >= (n ? +n : 1); }
  if (t.startsWith('karma>=')) return st.karma >= +t.slice(7);
  if (t.startsWith('gold>=')) return st.gold >= +t.slice(6);
  if (t.startsWith('party:')) return st.party.some(a => (a.id || a) === t.slice(6));
  return false;
}
function cond(c, st) { return !c || c.split('|').some(alt => alt.split('&').every(t => condTerm(t, st))); }
// 對話裡的 {item:道具} 換成持有數量，{goal} 換成目前目標
function fmt(s) { return s.replace(/\{item:(\w+)\}/g, (_, id) => itemCount(id)).replace(/\{goal\}/g, () => S.goal || '……'); }

/* ================================================================ 狀態 */
function freshState() {
  return {
    mode: 'title', mapId: 'village', x: 0, y: 0, dir: 'D', party: [], inv: {}, gold: 0, flags: {}, karma: 0,
    quests: {}, goal: '', playTime: 0, busy: false, menus: [], dialog: null, toasts: [], banner: null, bannerId: 0,
    battle: null, ending: null, waitOk: null, dex: {}, visited: {}, card: null, board: null,
    easy: false, mons: [], invuln: 0, auto: false, autoSeen: {}, autoNote: '',
  };
}
const curMap = () => D.maps[S.mapId];
function addItem(id, n = 1) { S.inv[id] = (S.inv[id] || 0) + n; }
function removeItem(id, n = 1) { S.inv[id] = Math.max(0, (S.inv[id] || 0) - n); if (!S.inv[id]) delete S.inv[id]; }
function fullHeal() { for (const a of S.party) { a.hp = maxHp(a); a.mp = maxMp(a); } }

function saveGame() {
  const data = {
    v: 1, mapId: S.mapId, x: S.x, y: S.y, dir: S.dir, gold: S.gold, inv: S.inv, flags: S.flags, karma: S.karma,
    quests: S.quests, goal: S.goal, playTime: S.playTime, dex: S.dex, visited: S.visited, easy: !!S.easy,
    auto: !!S.auto, autoSeen: S.autoSeen, goalMap: S.goalMap,
    party: S.party.map(a => ({ id: a.id, level: a.level, exp: a.exp, hp: a.hp, mp: a.mp, equip: a.equip })),
  };
  try { localStorage.setItem(SAVE_KEY, JSON.stringify(data)); return true; } catch (e) { return false; }
}
function hasSave() { try { return !!localStorage.getItem(SAVE_KEY); } catch (e) { return false; } }
function loadGame() {
  let data;
  try { data = JSON.parse(localStorage.getItem(SAVE_KEY)); } catch (e) { data = null; }
  if (!data) return false;
  S = freshState();
  Object.assign(S, { mapId: data.mapId, x: data.x, y: data.y, dir: data.dir, gold: data.gold, inv: data.inv, flags: data.flags,
    karma: data.karma, quests: data.quests, goal: data.goal, playTime: data.playTime, mode: 'map', dex: data.dex || {}, visited: data.visited || {}, easy: !!data.easy,
    auto: !!data.auto, autoSeen: data.autoSeen || {}, goalMap: data.goalMap });
  S.party = data.party.map(p => Object.assign({ st: {} }, p));
  built = null;
  spawnMons();
  return true;
}
function meta() { try { return JSON.parse(localStorage.getItem(META_KEY)) || { endings: [] }; } catch (e) { return { endings: [] }; } }
function saveMeta(m) { try { localStorage.setItem(META_KEY, JSON.stringify(m)); } catch (e) { /* 沒有存檔空間也能玩 */ } }

/* ================================================================ 對話、選單、提示 */
function say(speaker, text) {
  S.lastSay = { speaker, text };
  return new Promise(res => { S.dialog = { speaker, text, res }; render(); });
}
function advanceDialog() {
  const d = S.dialog;
  if (!d) return;
  S.dialog = null;
  d.res();
}
function choose(labels, title) {
  return new Promise(res => {
    if (S.lastSay) S.dialog = { speaker: S.lastSay.speaker, text: S.lastSay.text, res() {} };
    pushMenu({ cls: 'choice', title, build: () => labels.map(l => ({ label: l })), onPick: i => { S.dialog = null; popMenu(); res(i); }, onBack: () => {} });
  });
}
function toast(text) {
  const t = { id: Math.random(), text };
  S.toasts.push(t);
  render();
  setTimeout(() => { S.toasts = S.toasts.filter(x => x !== t); render(); }, 2400);
}
function pushMenu(m) { m.cursor = m.cursor || 0; S.menus.push(m); render(); }
function popMenu() { S.menus.pop(); render(); }
function menuItems(m) {
  const items = m.build();
  // 清單變短（例如賣掉或用掉最後一個道具）時，把游標拉回最後一項
  if (m.cursor >= items.length) m.cursor = Math.max(0, items.length - 1);
  return items;
}
function menuKey(btn) {
  const m = S.menus[S.menus.length - 1];
  const items = menuItems(m);
  if (btn === 'up' || btn === 'down') {
    if (!items.length) return;
    m.cursor = (m.cursor + (btn === 'up' ? items.length - 1 : 1)) % items.length;
    if (m.onMove) m.onMove(m.cursor);
    render();
  } else if (btn === 'ok') {
    const it = items[m.cursor];
    if (it && !it.disabled) m.onPick(m.cursor, it);
  } else if (btn === 'back' || btn === 'menu') {
    if (m.onBack) m.onBack(); else popMenu();
  }
}
function waitOk() { return new Promise(res => { S.waitOk = res; render(); }); }

/* ================================================================ 腳本 */
async function run(script) {
  for (const c of script || []) {
    const r = await exec(c);
    if (r === STOP) return STOP;
  }
}
async function exec(c) {
  const op = c[0];
  switch (op) {
    case 'say':
      for (let i = 2; i < c.length; i++) await say(c[1], fmt(c[i]));
      break;
    case 'if':
      if (cond(c[1])) return run(c[2]);
      if (c[3]) return run(c[3]);
      break;
    case 'choice': {
      S.autoChoice = c.slice(1);
      const i = await choose(c.slice(1).map(o => o[0]));
      return run(c[1 + i][1]);
    }
    case 'flag': S.flags[c[1]] = true; break;
    case 'unflag': delete S.flags[c[1]]; break;
    case 'give': {
      const n = c[2] || 1;
      addItem(c[1], n);
      await say('', `獲得了【${D.items[c[1]].name}】${n > 1 ? ' ×' + n : ''}！`);
      break;
    }
    case 'take': removeItem(c[1], c[2] || 1); break;
    case 'gold': S.gold += c[1]; await say('', `得到了 ${c[1]} K 幣！`); break;
    case 'goal': S.goal = c[1]; S.goalMap = S.mapId; toast('目標：' + c[1]); break;
    case 'quest': {
      const q = D.quests[c[1]];
      if (S.quests[c[1]] === 'done') break;
      S.quests[c[1]] = c[2];
      toast((c[2] === 'done' ? '任務完成：' : '新任務：') + q.name);
      break;
    }
    case 'karma':
      S.karma += c[1];
      toast(c[1] > 0 ? '（島上某處，有人默默回了一句：推。）' : '（島上某處，有人只回了一個字：閱。）');
      break;
    case 'chapter': await showCard(c[1], c[2], c[3]); break;
    case 'board': await openBoard(c[1]); break;
    case 'battle': {
      const r = await battle(c[1], c[2] || {});
      if (r === 'lose') { await gameOver(); return STOP; }
      break;
    }
    case 'join': {
      const lv = Math.max(D.actors[c[1]].joinLevel, S.party[0].level - 1);
      S.party.push(makeActor(c[1], lv));
      break;
    }
    case 'heal': fullHeal(); break;
    case 'inn': {
      const price = c[1];
      S.autoChoice = { inn: price };
      const i = await choose([`休息（${price} K 幣）`, '不用了']);
      if (i === 0) {
        if (S.gold < price) await say('', 'K 幣不夠……');
        else { S.gold -= price; fullHeal(); await say('', '安心地潛水了一晚。全隊的 HP 與 MP 都回復了！'); }
      }
      break;
    }
    case 'shop': await openShop(c[1]); break;
    case 'warp': teleport(c[1], c[2], c[3], c[4]); break;
    case 'save': await say('', saveGame() ? '冒險已記錄。這串不會沉了。' : '（這個瀏覽器無法存檔）'); break;
    case 'ending': await showEnding(c[1]); return STOP;
    case 'call': return run(D.calls[c[1]]);
  }
}
async function runBusy(script) {
  S.busy = true;
  render();
  try {
    const r = await run(script);
    if (r === STOP) return;
    while (S.pendingAuto) { S.pendingAuto = false; if (await runAutos() === STOP) return; }
  } finally {
    if (S.mode === 'map' || S.mode === 'battle') S.busy = false;
    render();
  }
}
async function runAutos() {
  for (const a of curMap().auto || []) {
    if (cond(a.cond)) { const r = await run(a.script); if (r === STOP) return STOP; }
  }
}

/* ================================================================ 地圖 */
function teleport(mapId, x, y, dir) {
  S.mapId = mapId; S.x = x; S.y = y; S.dir = dir;
  S.visited[mapId] = true;
  S.banner = D.maps[mapId].name; S.bannerId++;
  S.pendingAuto = true;
  spawnMons();
}

/* ---------------------------------------------------------------- 明雷：地圖上看得到的怪物
   進入有怪物的地圖時，在離玩家遠一點的地方放幾隻怪。牠們平常亂晃，玩家靠近就會追過來；
   碰到就開戰。打贏的怪在離開地圖前不會再出現；用「無視」逃走時，那隻怪會暫時不追人。 */
let MONS_ON = true;  // 測試用開關
const monAt = (x, y) => S.mons.find(m => m.x === x && m.y === y);
const warpAt = (x, y) => curMap().warps.some(w => w[0] === x && w[1] === y);
function monFree(x, y) { return walkable(x, y) && !entAt(x, y) && !warpAt(x, y) && !monAt(x, y) && !(x === S.x && y === S.y); }
function monCount(walkTiles) { const n = clamp(Math.round(walkTiles / 45), 3, 9); return S.easy ? Math.max(2, n - 3) : n; }
function pickTroop(enc) {
  const total = enc.troops.reduce((s, t) => s + t[1], 0);
  let r = Math.random() * total;
  for (const [id, w] of enc.troops) { r -= w; if (r < 0) return id; }
  return enc.troops[0][0];
}
function spawnMons() {
  S.mons = [];
  const m = curMap(), enc = m.enc;
  if (!enc || !MONS_ON) return;
  const walk = [];
  m.rows.forEach((row, y) => { for (let x = 0; x < row.length; x++) if (D.tiles[row[x]][1] === 1) walk.push([x, y]); });
  const cand = walk.filter(([x, y]) => Math.abs(x - S.x) + Math.abs(y - S.y) >= 6 && monFree(x, y));
  const now = performance.now();
  for (let i = 0, n = monCount(walk.length); i < n && cand.length; i++) {
    const [x, y] = cand.splice(rnd(cand.length), 1)[0];
    const troop = pickTroop(enc);
    // 地圖上顯示這一組裡最強（HP 最高）的怪
    const lead = D.troops[troop].reduce((a, b) => (D.enemies[b].hp > D.enemies[a].hp ? b : a));
    S.mons.push({ id: 'm' + i + '_' + Math.random().toString(36).slice(2, 7), x, y, troop, sprite: D.enemies[lead].sprite || lead, next: now + 600 + Math.random() * 1200, calm: 0, chasing: false });
  }
}
function monIdle() { return MONS_ON && S && S.mode === 'map' && !S.busy && !S.menus.length && !S.dialog && !S.board && !S.card; }
function monTick() {
  if (!monIdle() || !S.mons.length) return;
  const now = performance.now();
  let acted = false;
  for (const m of S.mons) {
    if (now < m.next) continue;
    acted = true;
    const dist = Math.abs(m.x - S.x) + Math.abs(m.y - S.y);
    m.chasing = dist <= (S.easy ? 3 : 6) && now >= m.calm;
    let dirs;
    if (m.chasing) {
      const sx = Math.sign(S.x - m.x), sy = Math.sign(S.y - m.y);
      dirs = Math.abs(S.x - m.x) >= Math.abs(S.y - m.y) ? [[sx, 0], [0, sy]] : [[0, sy], [sx, 0]];
      dirs = dirs.filter(([a, b]) => a || b);
      m.next = now + (S.easy ? 520 : 300);
    } else {
      m.next = now + 700 + Math.random() * 900;
      if (Math.random() < 0.45) continue;
      dirs = [[[1, 0], [-1, 0], [0, 1], [0, -1]][rnd(4)]];
    }
    for (const [ax, ay] of dirs) {
      const nx = m.x + ax, ny = m.y + ay;
      if (nx === S.x && ny === S.y) {
        if (now >= S.invuln) { renderMons(); encounter(m); return; }
        continue;
      }
      if (monFree(nx, ny)) { m.x = nx; m.y = ny; break; }
    }
  }
  if (acted) renderMons();
}
function encounter(m) {
  if (S.busy || S.mode !== 'map') return;
  S.busy = true;
  holdClear();
  (async () => {
    try {
      const r = await battle(m.troop, { mon: true });
      if (r === 'lose') { await gameOver(); return; }
      if (r === 'win') S.mons = S.mons.filter(x => x !== m);
      else m.calm = performance.now() + 4000;   // 無視成功：這隻怪暫時不追
      S.invuln = performance.now() + 1500;      // 剛打完的一小段時間不會再被碰到
    } finally {
      if (S.mode === 'map' || S.mode === 'battle') S.busy = false;
      render();
    }
  })();
}
const STEP = { U: [0, -1], D: [0, 1], L: [-1, 0], R: [1, 0] };
function visibleEnts() { return curMap().ents.filter(e => cond(e.show)); }
function entAt(x, y) { return visibleEnts().find(e => e.x === x && e.y === y); }
function walkable(x, y) {
  const m = curMap();
  if (y < 0 || y >= m.rows.length || x < 0 || x >= m.rows[0].length) return false;
  return D.tiles[m.rows[y][x]][1] === 1;
}
function tileAt(x, y) { const m = curMap(); return (m.rows[y] || '')[x]; }

let lastMove = 0, walkAlt = 0, walkTimer = 0;
/* 主角的圖：依面向選正面／背面／側面（朝左時把側面左右翻轉），走路時短暫換成跨步的圖 */
const HERO_FRAMES = { D: ['hero', 'hero_d1', 'hero_d2'], U: ['hero_back', 'hero_u1', 'hero_u2'], R: ['hero_side', 'hero_s1', 'hero_s2'], L: ['hero_side', 'hero_s1', 'hero_s2'] };
function heroSprite() { return (HERO_FRAMES[S.dir] || HERO_FRAMES.D)[S.walk || 0]; }
function stepAnim() {
  walkAlt = walkAlt === 1 ? 2 : 1;
  S.walk = walkAlt;
  clearTimeout(walkTimer);
  walkTimer = setTimeout(() => { S.walk = 0; if (S.mode === 'map') render(); }, 120);
}
function tryMove(dir) {
  const now = performance.now();
  if (now - lastMove < 135) return;
  lastMove = now;
  moveStep(dir);
}
// 往一個方向走一格。回傳：true 走過去了、'mon' 撞到怪物、false 被擋住
function moveStep(dir) {
  const now = performance.now();
  S.dir = dir;
  const [dx, dy] = STEP[dir];
  const nx = S.x + dx, ny = S.y + dy;
  if (!walkable(nx, ny) || entAt(nx, ny)) { render(); return false; }
  const mon = monAt(nx, ny);
  if (mon) { render(); if (now >= S.invuln) encounter(mon); return 'mon'; }
  S.x = nx; S.y = ny;
  stepAnim();
  const w = curMap().warps.find(w => w[0] === nx && w[1] === ny);
  if (w) {
    teleport(w[2], w[3], w[4], w[5]);
    saveGame();
    render();
    runBusy([]);
    return true;
  }
  render();
  return true;
}
function interact() {
  const [dx, dy] = STEP[S.dir];
  let fx = S.x + dx, fy = S.y + dy;
  if (tileAt(fx, fy) === 'u') { fx += dx; fy += dy; }
  const e = entAt(fx, fy);
  if (!e) return;
  if (e.chest) return openChest(e);
  runBusy(e.script);
}
function chestFlag(e) { return `chest:${S.mapId}:${e.id}`; }
function openChest(e) {
  if (S.flags[chestFlag(e)]) { runBusy([['say', '', '寶箱是空的。']]); return; }
  S.flags[chestFlag(e)] = true;
  if (e.chest.item) runBusy([['say', '', '打開了寶箱！'], ['give', e.chest.item, e.chest.n || 1]]);
  else runBusy([['say', '', '打開了寶箱！'], ['gold', e.chest.gold]]);
}

/* ================================================================ 選單（地圖） */
// 選對象時右欄顯示的數值：回復 MP 的道具顯示 MP，兩者都回復就都顯示
function vitalKind(it) { return it && it.mp ? (it.heal ? 'both' : 'mp') : 'hp'; }
function vitalText(a, kind, short) {
  const hp = `${a.hp}/${maxHp(a)}`, mp = `MP ${a.mp}/${maxMp(a)}`;
  if (kind === 'mp') return mp;
  if (kind === 'both') return `HP ${hp} ${mp}`;
  return short ? hp : 'HP ' + hp;
}
function partyPicker(title, onPick, filter, kind) {
  pushMenu({
    title, build: () => S.party.map(a => ({
      label: `${ad(a).name}　Lv ${a.level}`, right: vitalText(a, kind || 'hp'), disabled: filter ? !filter(a) : false,
    })), onPick: i => onPick(S.party[i]),
  });
}
function itemDesc(id) {
  const it = D.items[id];
  let s = it.desc;
  if (['weapon', 'armor', 'acc'].includes(it.type)) {
    const parts = S.party.filter(a => canEquip(a, id)).map(a => {
      const cur = a.equip[slotOf(id)];
      const diffs = ['atk', 'def', 'mag', 'spd', 'hp', 'mp'].map(k => {
        const d = ((it.stats || {})[k] || 0) - ((cur && D.items[cur].stats || {})[k] || 0);
        return d ? `${STATN[k]}${d > 0 ? '+' : ''}${d}` : '';
      }).filter(Boolean).join(' ');
      return `${ad(a).name} ${diffs || '±0'}`;
    });
    s += parts.length ? '｜' + parts.join('／') : '｜目前隊伍無人可裝備';
  }
  return s;
}
const STATN = { atk: '攻', def: '防', mag: '魔', spd: '速', hp: 'HP', mp: 'MP' };
const slotOf = id => ({ weapon: 'weapon', armor: 'armor', acc: 'acc' })[D.items[id].type];
const SLOTN = { weapon: '武器', armor: '防具', acc: '飾品' };

const skitSeen = k => !!S.flags['skit:' + k.id];
const skitsAvail = () => (D.skits || []).filter(k => cond(k.cond));
function openMainMenu() {
  pushMenu({
    cls: 'main', title: '選單',
    build: () => [
      { label: '道具' }, { label: '技能' }, { label: '裝備' }, { label: '狀態' },
      { label: '雜談', right: skitsAvail().some(k => !skitSeen(k)) ? 'NEW' : '', disabled: !skitsAvail().length },
      { label: '圖鑑' }, { label: '跳串', right: '傳送' }, { label: '任務' }, { label: '設定' }, { label: '存檔' }, { label: '關閉' },
    ],
    onPick: i => [menuItemsField, menuSkillsField, menuEquip, menuStatus, menuSkits, menuDex, menuTravel, menuQuests, menuSettings,
      () => { toast(saveGame() ? '已存檔。這串不會沉了。' : '無法存檔'); }, popMenu][i](),
  });
}
function menuSkits() {
  pushMenu({
    title: '隊伍雜談', cls: 'wide',
    build: () => skitsAvail().map(k => ({ label: k.title, right: skitSeen(k) ? '' : 'NEW', id: k.id })),
    onPick: (i, it) => {
      const k = D.skits.find(x => x.id === it.id);
      S.menus.length = 0;
      S.flags['skit:' + k.id] = true;
      runBusy(k.script);
    },
  });
}
function dexEntry(id) { return S.dex[id] || (S.dex[id] = { seen: false, killed: 0, weak: [], resist: [] }); }
const EN = { fire: '炎上', ice: '冷場', thunder: '暴雷', holy: '神串', dark: '黑歷史', phys: '物理' };
function knownText(id) {
  const d = S.dex[id];
  if (!d) return '';
  const w = d.weak.map(e => EN[e]).join('、'), r = d.resist.map(e => EN[e]).join('、');
  return [w && '弱：' + w, r && '抗：' + r].filter(Boolean).join('　');
}
function menuDex() {
  const ids = Object.keys(D.enemies);
  pushMenu({
    title: `怪物圖鑑（${ids.filter(id => S.dex[id] && S.dex[id].seen).length} / ${ids.length}）`, cls: 'wide dex',
    build: () => ids.map(id => {
      const d = S.dex[id], e = D.enemies[id];
      if (!d || !d.seen) return { label: '？？？', id, desc: '還沒有遇過。' };
      const k = knownText(id) || '弱點：？？？（用屬性攻擊打打看）';
      return { label: e.name, right: d.killed ? '打倒 ' + d.killed : '', id,
        desc: `HP ${e.hp}　攻 ${e.atk}　防 ${e.def}　魔 ${e.mag}　速 ${e.spd}｜${k}｜${e.desc || ''}` };
    }),
    onPick: () => {},
  });
}
function menuTravel() {
  if ((D.noTravel || []).includes(S.mapId)) { toast('這裡的訊號太強，沒辦法跳串。'); return; }
  pushMenu({
    title: '跳串（傳送到去過的地方）', cls: 'wide',
    build: () => {
      const list = (D.travel || []).filter(t => S.visited[t.map] && cond(t.cond)).map(t => ({ label: t.name, right: t.map === S.mapId ? '現在位置' : '', t }));
      return list.length ? list : [{ label: '（還沒有可以傳送的地方）', disabled: true }];
    },
    onPick: (i, it) => {
      const t = it.t;
      S.menus.length = 0;
      teleport(t.map, t.x, t.y, t.dir);
      built = null;
      saveGame();
      render();
      runBusy([]);
    },
  });
}
function menuSettings() {
  pushMenu({
    title: '設定', cls: 'wide',
    build: () => [
      { id: 'speed', label: '戰鬥速度', right: BSPEED_NAMES[bspeed], desc: '按 Enter 切換。設定會記在這台裝置上。' },
      { id: 'easy', label: '難度', right: S.easy ? '簡單' : '普通', desc: '按 Enter 切換，會跟著存檔記錄。簡單：敵人比較弱、受到的傷害較少、經驗值與 K 幣 1.5 倍、「無視」一定成功、怪物比較少也不太追人。' },
      { id: 'auto', label: '全自動模式', right: S.auto ? '開' : '關', desc: '開啟後由電腦幫你玩：自動走路、找人說話、做主線和支線、戰鬥、買裝備換裝備，一路玩到結局。難度會自動改成「簡單」，戰鬥中倒下會自動復活並補滿 HP／MP。按「選單」可以暫停，點畫面左上角的 AUTO 可以關掉。' },
      { id: 'aspeed', label: '自動速度', right: AUTO_SPEED_NAMES[autoSpeed], desc: '全自動模式的走路與對話速度。按 Enter 切換。' },
      { id: 'back', label: '返回' },
    ],
    onPick: (i, it) => {
      if (it.id === 'back') { popMenu(); return; }
      if (it.id === 'auto') { setAuto(!S.auto); if (S.auto) S.menus.length = 0; render(); return; }
      if (it.id === 'aspeed') { autoSpeed = (autoSpeed + 1) % AUTO_SPEEDS.length; const m = meta(); m.autoSpeed = autoSpeed; saveMeta(m); render(); return; }
      if (it.id === 'easy') { S.easy = !S.easy; toast(S.easy ? '難度改為「簡單」' : '難度改為「普通」'); render(); return; }
      bspeed = (bspeed + 1) % BSPEEDS.length;
      const m = meta(); m.speed = bspeed; saveMeta(m);
      render();
    },
  });
}

/* ================================================================ 討論板、章節卡 */
function hashId(str) {
  let h = 2166136261;
  for (const ch of str) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); }
  return (h >>> 0).toString(36).padStart(7, '0').slice(0, 8);
}
function boardPosts(id) {
  const b = D.boards[id];
  return b.posts.map((p, i) => ({ ...p, i })).filter(p => cond(p.cond));
}
function openBoard(id) {
  return new Promise(res => { S.board = { id, top: 0, res }; render(); });
}
function closeBoard() { const b = S.board; S.board = null; render(); b.res(); }
function boardKey(btn) {
  const b = S.board, n = boardPosts(b.id).length;
  if (btn === 'up') b.top = Math.max(0, b.top - 1);
  else if (btn === 'down') b.top = Math.min(n - 1, b.top + 1);
  else if (btn === 'ok' || btn === 'back' || btn === 'menu') { closeBoard(); return; }
  render();
}
function showCard(label, title, sub) {
  return new Promise(res => {
    const done = () => { if (S.card && S.card.res === done) { S.card = null; render(); res(); } };
    S.card = { label, title, sub, res: done };
    render();
    setTimeout(done, 3200);
  });
}
function invList(filter) { return Object.keys(S.inv).filter(id => S.inv[id] > 0 && filter(D.items[id], id)); }
function menuItemsField() {
  pushMenu({
    title: '道具', cls: 'wide',
    build: () => {
      const ids = invList(it => it.type === 'use' || it.type === 'key');
      if (!ids.length) return [{ label: '（什麼都沒有）', disabled: true, desc: '' }];
      return ids.map(id => ({ label: D.items[id].name, right: '×' + S.inv[id], disabled: D.items[id].type !== 'use' || D.items[id].battleOnly, desc: D.items[id].desc, id }));
    },
    onPick: (i, it) => {
      const item = D.items[it.id];
      if (item.target === 'allies') { applyItemField(it.id, S.party); return; }
      partyPicker('對誰使用？', a => { popMenu(); applyItemField(it.id, [a]); },
        a => item.target === 'deadAlly' ? a.hp <= 0 : a.hp > 0, vitalKind(item));
    },
  });
}
function applyItemField(id, targets) {
  const msgs = applyItem(null, id, targets);
  removeItem(id);
  toast(msgs.join(' '));
  render();
}
function applyItem(user, id, targets) {
  const it = D.items[id];
  const msgs = [];
  for (const t of targets) {
    if (it.revive) {
      if (t.hp > 0) { msgs.push(`${uname(t)}沒有倒下。`); continue; }
      t.hp = Math.max(1, Math.floor(maxHp(t) * it.revive)); if (t.st) t.st = {};
      msgs.push(`${uname(t)}復活了！`);
      continue;
    }
    if (t.hp <= 0) continue;
    if (it.heal) { const h = Math.min(it.heal, uMaxHp(t) - t.hp); t.hp += h; msgs.push(`${uname(t)}回復了 ${h} HP。`); }
    if (it.mp) { const h = Math.min(it.mp, maxMp(t) - t.mp); t.mp += h; msgs.push(`${uname(t)}回復了 ${h} MP。`); }
    if (it.cure) { if (t.st) for (const k of ['burn', 'silence', 'confuse', 'sleep']) delete t.st[k]; msgs.push(`${uname(t)}冷靜下來了。`); }
  }
  return msgs;
}
function menuSkillsField() {
  partyPicker('誰要使用技能？', a => {
    pushMenu({
      title: ad(a).name + '的技能', cls: 'wide',
      build: () => skillsOf(a).map(id => {
        const sk = D.skills[id];
        return { label: sk.name, right: 'MP ' + sk.mp, disabled: !sk.field || a.mp < sk.mp || a.hp <= 0, desc: sk.desc, id };
      }),
      onPick: (i, it) => {
        const sk = D.skills[it.id];
        const use = targets => {
          a.mp -= sk.mp;
          const msgs = [];
          for (const t of targets) {
            if (sk.kind === 'revive' || (sk.revive && t.hp <= 0)) {
              if (t.hp <= 0) { t.hp = Math.max(1, Math.floor(maxHp(t) * (sk.rate || 0.3))); msgs.push(`${ad(t).name}復活了！`); }
              if (sk.kind === 'revive') continue;
            }
            if (sk.kind === 'heal' && t.hp > 0) { const h = Math.min(healAmount(a, sk), maxHp(t) - t.hp); t.hp += h; msgs.push(`${ad(t).name}回復了 ${h} HP。`); }
            if (sk.kind === 'cure') msgs.push(`${ad(t).name}冷靜下來了。`);
          }
          toast(msgs.join(' ') || '沒有效果。');
          render();
        };
        if (sk.target === 'allies') use(S.party);
        else if (sk.target === 'self') use([a]);
        else partyPicker('對誰使用？', t => { popMenu(); use([t]); }, t => sk.target === 'deadAlly' ? t.hp <= 0 : t.hp > 0);
      },
    });
  });
}
function menuEquip() {
  partyPicker('誰要換裝備？', a => {
    pushMenu({
      title: ad(a).name + '的裝備', cls: 'wide',
      build: () => ['weapon', 'armor', 'acc'].map(slot => ({
        label: SLOTN[slot] + '：' + (a.equip[slot] ? D.items[a.equip[slot]].name : '（無）'), slot,
        desc: a.equip[slot] ? D.items[a.equip[slot]].desc : '',
      })),
      onPick: (i, it) => {
        const slot = it.slot;
        pushMenu({
          title: SLOTN[slot], cls: 'wide',
          build: () => {
            const list = invList((item, id) => slotOf(id) === slot && canEquip(a, id)).map(id => ({ label: D.items[id].name, right: '×' + S.inv[id], desc: itemDesc(id), id }));
            if (slot !== 'weapon') list.push({ label: '（卸下）', id: null, desc: '' });
            return list.length ? list : [{ label: '（沒有可以裝備的東西）', disabled: true }];
          },
          onPick: (j, it2) => {
            const old = a.equip[slot];
            if (it2.id) removeItem(it2.id);
            if (old) addItem(old);
            a.equip[slot] = it2.id || null;
            a.hp = Math.min(a.hp, maxHp(a)); a.mp = Math.min(a.mp, maxMp(a));
            popMenu();
          },
        });
      },
    });
  });
}
function menuStatus() {
  partyPicker('查看誰的狀態？', a => {
    pushMenu({ title: ad(a).name, cls: 'status', actor: a, build: () => [{ label: '返回' }], onPick: () => popMenu() });
  });
}
function menuQuests() {
  pushMenu({ title: '任務', cls: 'quests', build: () => [{ label: '返回' }], onPick: () => popMenu() });
}

/* ================================================================ 商店 */
function openShop(shopId) {
  S.shopId = shopId;
  return new Promise(res => {
    const close = () => { popMenu(); res(); };
    pushMenu({
      title: '商店', cls: 'shop', build: () => [{ label: '購買' }, { label: '賣出' }, { label: '離開' }],
      onBack: close,
      onPick: i => {
        if (i === 2) return close();
        if (i === 0) {
          pushMenu({
            title: '購買', cls: 'wide shop',
            build: () => D.shops[shopId].map(id => ({ label: D.items[id].name, right: D.items[id].price + ' K', disabled: S.gold < D.items[id].price, desc: itemDesc(id) + `（持有 ${itemCount(id)}）`, id })),
            onPick: (j, it) => { S.gold -= D.items[it.id].price; addItem(it.id); toast(`買了【${D.items[it.id].name}】`); },
          });
        } else {
          pushMenu({
            title: '賣出', cls: 'wide shop',
            build: () => {
              const ids = invList(it => it.type !== 'key' && it.price > 0);
              return ids.length ? ids.map(id => ({ label: D.items[id].name, right: Math.floor(D.items[id].price / 2) + ' K', desc: `持有 ×${S.inv[id]}`, id }))
                : [{ label: '（沒有可以賣的東西）', disabled: true }];
            },
            onPick: (j, it) => { S.gold += Math.floor(D.items[it.id].price / 2); removeItem(it.id); toast(`賣掉了【${D.items[it.id].name}】`); },
          });
        }
      },
    });
  });
}

/* ================================================================ 戰鬥 */
function newEnemy(id, label) {
  const def = D.enemies[id];
  const hp = S.easy ? Math.max(1, Math.round(def.hp * EASY.enemyHp)) : def.hp;  // 簡單模式：敵人 HP 較少
  return { uid: Math.random().toString(36).slice(2), side: 'enemy', id, def, name: def.name + label, hp, maxHp: hp, st: {}, lowUsed: false, fx: '' };
}
const aliveParty = () => S.party.filter(alive);
const aliveEnemies = () => S.battle.enemies.filter(alive);
const oppOf = u => isEnemy(u) ? aliveParty() : aliveEnemies();
const sideOf = u => isEnemy(u) ? aliveEnemies() : aliveParty();

async function msg(text, ms = 380) {
  const B = S.battle;
  B.log.push(text);
  if (B.log.length > 4) B.log.shift();
  render();
  await bwait(ms);
}
async function flash(u, cls, ms = 260) { u.fx = cls; render(); await bwait(ms); u.fx = ''; }
function addGauge(n) { const B = S.battle; if (B) B.gauge = Math.min(100, B.gauge + n); }
function popup(u, text, cls) {
  const scr = el('scr'), fx = el('fx');
  if (!scr || !fx) return;
  const key = isEnemy(u) ? u.uid : 'p-' + u.id;
  const target = scr.querySelector(`[data-u="${key}"]`);
  if (!target) return;
  const sr = scr.getBoundingClientRect(), tr = target.getBoundingClientRect();
  const k = sr.width / 774 || 1;
  const d = document.createElement('div');
  d.className = 'pop ' + (cls || '');
  d.textContent = text;
  d.style.left = ((tr.left - sr.left + tr.width / 2) / k) + 'px';
  d.style.top = ((tr.top - sr.top + (isEnemy(u) ? tr.height * 0.45 : 6)) / k) + 'px';
  fx.appendChild(d);
  setTimeout(() => d.remove(), 900);
}

async function battle(troopId, opts = {}) {
  const ids = D.troops[troopId];
  const counts = {}, seen = {};
  ids.forEach(id => counts[id] = (counts[id] || 0) + 1);
  const enemies = ids.map(id => {
    seen[id] = (seen[id] || 0) + 1;
    return newEnemy(id, counts[id] > 1 ? ' ' + 'ABCD'[seen[id] - 1] : '');
  });
  const B = S.battle = { enemies, turn: 0, log: [], bg: curMap().bg, mon: !!opts.mon, noFlee: !!opts.noFlee || enemies.some(e => e.def.boss), actor: -1, hi: null, intro: true, gauge: 0, comboQueued: false };
  for (const e of enemies) dexEntry(e.id).seen = true;
  for (const a of S.party) { a.st = {}; a.guard = false; a.fx = ''; }
  S.mode = 'battle';
  S.busy = true;
  S.banner = null;
  render();
  const names = [...new Set(ids.map(id => D.enemies[id].name))].join('、');
  await msg(`${names}出現在串裡了！`, 650);
  B.intro = false;
  if (opts.partyBuff) { for (const a of aliveParty()) a.st[opts.partyBuff] = 99; await msg('全隊的攻擊力大幅提升了！'); }
  let result = null;
  while (!result) {
    B.turn++;
    B.comboQueued = false;
    let acts = await partyInput();
    if (acts === 'flee') {
      const ps = aliveParty().reduce((s, a) => s + uStat(a, 'spd'), 0) / aliveParty().length;
      const es = aliveEnemies().reduce((s, e) => s + e.def.spd, 0) / aliveEnemies().length;
      if (S.easy || Math.random() < clamp(0.55 + (ps - es) * 0.02, 0.3, 0.9)) { await msg('發動島民技能「無視」，成功離開了這串！'); result = 'flee'; break; }
      await msg('無視失敗！被拉回串裡了！');
      acts = [];
    }
    const all = acts.map(a => ({ ...a, pri: a.type === 'combo' ? 2e4 : a.type === 'defend' ? 1e4 : uStat(a.u, 'spd') * (0.75 + Math.random() * 0.5) }));
    for (const e of aliveEnemies()) {
      const act = enemyAction(e);
      all.push({ ...act, pri: (D.skills[act.sk].first ? 5000 : 0) + e.def.spd * (0.75 + Math.random() * 0.5) });
    }
    all.sort((a, b) => b.pri - a.pri);
    for (const act of all) {
      if (!alive(act.u)) continue;
      await execAction(act);
      result = checkEnd();
      if (result === 'lose' && S.auto) { await autoRevive(); result = null; }
      if (result) break;
    }
    if (!result) { await endOfRound(); result = checkEnd(); if (result === 'lose' && S.auto) result = null; }
    if (!result && S.auto) await autoRevive();
  }
  if (S.auto) for (const a of S.party) if (a.hp <= 0) { a.hp = maxHp(a); a.mp = maxMp(a); }
  if (result === 'win') await victory();
  else if (result === 'lose') await msg('全隊倒下了……', 1100);
  for (const a of S.party) { a.st = {}; a.guard = false; }
  S.battle = null;
  S.mode = 'map';
  render();
  return result;
}
function checkEnd() {
  const B = S.battle;
  if (B.enemies.some(e => alive(e) && e.def.yieldAt && e.hp <= e.maxHp * e.def.yieldAt)) return 'win';
  if (!aliveEnemies().length) return 'win';
  if (!aliveParty().length) return 'lose';
  return null;
}
async function victory() {
  const B = S.battle;
  // 地圖上的怪物可以躲開，打到的那幾場給比較多；簡單模式再多一些
  const mul = (B.mon ? MON_REWARD : 1) * (S.easy ? EASY.reward : 1);
  const exp = Math.round(B.enemies.reduce((s, e) => s + (e.def.exp || 0), 0) * mul);
  const gold = Math.round(B.enemies.reduce((s, e) => s + (e.def.gold || 0), 0) * mul);
  for (const e of B.enemies) if (e.hp <= 0) dexEntry(e.id).killed++;
  await msg('戰鬥勝利！大家辛苦乙！', 500);
  if (exp || gold) await msg(`獲得 ${exp} 經驗值、${gold} K 幣。`, 500);
  S.gold += gold;
  for (const a of aliveParty()) for (const l of gainExp(a, exp)) await msg(l, 650);
  for (const e of B.enemies) for (const [id, ch] of e.def.drops || []) {
    if (e.hp <= 0 && Math.random() * 100 < ch) { addItem(id); await msg(`${e.def.name}掉落了【${D.items[id].name}】！`, 550); }
  }
  B.done = true;
  await waitOk();
}

/* ---- 玩家輸入 ---- */
async function partyInput() {
  const B = S.battle;
  const members = aliveParty();
  const acts = [];
  let i = 0;
  while (i < members.length) {
    const a = members[i];
    if (a.st.sleep || a.st.confuse) { acts[i] = { type: 'auto', u: a }; i++; continue; }
    B.actor = S.party.indexOf(a);
    render();
    const r = S.auto ? await autoCommand(a) : await commandFor(a, i > 0);
    if (r.back) {
      acts[i] = undefined;
      i--;
      while (i > 0 && acts[i] && acts[i].type === 'auto') i--;
      i = Math.max(0, i);
      continue;
    }
    if (r.flee) { B.actor = -1; return 'flee'; }
    if (r.autoAll) {
      for (let j = i; j < members.length; j++) acts[j] = (members[j].st.sleep || members[j].st.confuse) ? { type: 'auto', u: members[j] } : { type: 'attack', u: members[j], t: null };
      break;
    }
    acts[i] = r;
    i++;
  }
  B.actor = -1;
  B.hi = null;
  return acts.filter(Boolean);
}
function battleItems() { return invList(it => it.type === 'use'); }
function commandFor(a, canBack) {
  const B = S.battle;
  return new Promise(res => {
    const done = r => { while (S.menus.length) S.menus.pop(); B.hi = null; render(); res(r); };
    const pickTarget = (kind, after, vk) => {
      let list;
      if (kind === 'enemy') list = aliveEnemies();
      else if (kind === 'ally') list = aliveParty();
      else if (kind === 'deadAlly') list = S.party.filter(x => x.hp <= 0);
      else return after(null);
      if (!list.length) { toast('沒有可以選擇的對象'); return; }
      pushMenu({
        cls: 'battle', title: '選擇對象',
        build: () => list.map(t => ({ label: uname(t), right: isEnemy(t) ? knownText(t.id) : vitalText(t, vk || 'hp', true) })),
        onMove: j => { B.hi = list[j]; },
        onBack: () => { B.hi = null; popMenu(); },
        onPick: j => after(list[j]),
      });
      B.hi = list[0];
      render();
    };
    pushMenu({
      cls: 'battle', title: ad(a).name,
      build: () => [
        ...(B.gauge >= 100 && !B.comboQueued ? [{ label: '★ 合體技', right: '推 MAX', cmd: 'combo' }] : []),
        { label: '攻擊', cmd: 'attack' },
        { label: '技能', disabled: !!a.st.silence, right: a.st.silence ? 'sage' : '', cmd: 'skill' },
        { label: '道具', disabled: !battleItems().length, cmd: 'item' },
        { label: '防禦', cmd: 'defend' },
        { label: '自動', right: '全員攻擊', cmd: 'auto' },
        { label: '無視', disabled: B.noFlee, cmd: 'flee' },
      ],
      onBack: () => { if (canBack) done({ back: true }); },
      onPick: (i0, it0) => {
        const i = { attack: 0, skill: 1, item: 2, defend: 3, flee: 4, combo: 5, auto: 6 }[it0.cmd];
        if (i === 5) {
          pushMenu({
            cls: 'battle wide', title: '合體技',
            build: () => Object.entries(D.combos).map(([id, c]) => ({ label: c.name, desc: c.desc, id })),
            onPick: (j, it) => { B.comboQueued = true; done({ type: 'combo', u: a, combo: it.id }); },
          });
          return;
        }
        if (i === 6) { done({ autoAll: true }); return; }
        if (i === 0) pickTarget('enemy', t => done({ type: 'attack', u: a, t }));
        else if (i === 1) {
          pushMenu({
            cls: 'battle wide', title: '技能',
            build: () => skillsOf(a).map(id => ({ label: D.skills[id].name, right: 'MP ' + D.skills[id].mp, disabled: a.mp < D.skills[id].mp, desc: D.skills[id].desc, id })),
            onPick: (j, it) => {
              const sk = D.skills[it.id];
              pickTarget(sk.target, t => done({ type: 'skill', u: a, sk: it.id, t }));
            },
          });
        } else if (i === 2) {
          pushMenu({
            cls: 'battle wide', title: '道具',
            build: () => battleItems().map(id => ({ label: D.items[id].name, right: '×' + S.inv[id], desc: D.items[id].desc, id })),
            onPick: (j, it) => {
              const item = D.items[it.id];
              const kind = item.target === 'ally' ? 'ally' : item.target === 'deadAlly' ? 'deadAlly' : null;
              pickTarget(kind, t => done({ type: 'item', u: a, item: it.id, t }), vitalKind(item));
            },
          });
        } else if (i === 3) done({ type: 'defend', u: a });
        else done({ flee: true });
      },
    });
  });
}

/* ---- 敵人 AI ---- */
function enemyAction(e) {
  const ai = e.def.ai, B = S.battle;
  if (e.st.silence) return { type: 'skill', u: e, sk: 'e_attack' };
  if (ai.low && !e.lowUsed && e.hp <= e.maxHp * ai.low[0]) { e.lowUsed = true; return { type: 'skill', u: e, sk: ai.low[1], warn: ai.low[2] }; }
  if (ai.every && B.turn % ai.every[0] === 0) return { type: 'skill', u: e, sk: ai.every[1] };
  const total = ai.pattern.reduce((s, p) => s + p[1], 0);
  let r = Math.random() * total;
  for (const [sk, w] of ai.pattern) { r -= w; if (r < 0) return { type: 'skill', u: e, sk }; }
  return { type: 'skill', u: e, sk: ai.pattern[0][0] };
}
function pickOne(u, list) {
  if (isEnemy(u)) {
    const taunters = list.filter(t => t.st && t.st.taunt);
    if (taunters.length && Math.random() < 0.75) return taunters[rnd(taunters.length)];
  }
  return list[rnd(list.length)];
}

/* ---- 行動執行 ---- */
async function execAction(act) {
  const u = act.u, B = S.battle;
  if (act.type === 'defend') { u.guard = true; addGauge(D.gauge.defend); await msg(`${uname(u)}擺出了防禦姿勢。`, 300); return; }
  if (act.type === 'combo') { await doCombo(act.combo); return; }
  if (u.st.sleep) { await msg(`${uname(u)}正在潛水……（睡眠中）`); return; }
  if (u.st.confuse) {
    const pool = [...aliveParty(), ...aliveEnemies()].filter(x => x !== u);
    const t = pool[rnd(pool.length)];
    await msg(`${uname(u)}被釣了，胡亂攻擊！`);
    if (t) await hitPhys(u, t, 1, 'phys');
    return;
  }
  if (act.type === 'auto') act.type = 'attack';
  if (act.warn) await msg(act.warn, 600);
  if (act.type === 'attack') {
    let t = act.t;
    if (!t || !alive(t)) { const o = oppOf(u); if (!o.length) return; t = pickOne(u, o); }
    await msg(`${uname(u)}的攻擊！`, 300);
    await hitPhys(u, t, 1, 'phys');
    return;
  }
  if (act.type === 'item') {
    if (!itemCount(act.item)) { await msg('道具已經用完了！'); return; }
    const it = D.items[act.item];
    removeItem(act.item);
    await msg(`${uname(u)}使用了【${it.name}】！`, 350);
    if (it.damage) {
      for (const t of aliveEnemies()) {
        const dmg = Math.round(it.damage * elemMult(t, it.elem) * (0.9 + Math.random() * 0.2));
        await applyDamage(u, t, dmg, elemNote(t, it.elem));
      }
      return;
    }
    let targets = it.target === 'allies' ? aliveParty() : [act.t];
    if (it.target === 'ally' && (!act.t || !alive(act.t))) targets = [aliveParty().sort((a, b) => a.hp / maxHp(a) - b.hp / maxHp(b))[0]];
    for (const m of applyItem(u, act.item, targets.filter(Boolean))) await msg(m, 380);
    return;
  }
  // 技能
  const sk = D.skills[act.sk];
  if (!isEnemy(u)) {
    if (u.st.silence) { await msg(`${uname(u)}被 sage 了，說不出咒語！`); return; }
    if (u.mp < sk.mp) { await msg(`${uname(u)}的 MP 不足！`); return; }
    u.mp -= sk.mp;
  }
  if (sk.name !== '攻擊') await msg(`${uname(u)}使用了「${sk.name}」！`, 380);
  else await msg(`${uname(u)}的攻擊！`, 300);
  await doSkill(u, sk, act.t);
}
function elemNote(t, elem) { const m = elemMult(t, elem); return m > 1 ? '效果拔群！' : m < 1 ? '被無視了，效果不太好……' : ''; }
async function hitPhys(u, t, power, elem) {
  if (Math.random() < 0.04) { await msg('但是沒打中！'); return; }
  if (t.st.hidden && elem !== 'holy' && Math.random() < 0.75) { await msg('404 Not Found——攻擊撲空了！'); return; }
  let dmg = physDamage(u, t, power) * elemMult(t, elem);
  let note = elemNote(t, elem);
  if (!isEnemy(u) && Math.random() < 0.06) { dmg *= 1.5; note = '神回！' + note; }
  await applyDamage(u, t, Math.round(dmg), note, elem);
  if (alive(t) && alive(u) && t.st.counter && isEnemy(t) !== isEnemy(u)) {
    const c = Math.round(physDamage(t, u, 1.5));
    await msg(`上鉤了！${uname(t)}的反擊！`, 350);
    await applyDamage(t, u, c, '');
  }
}
async function doCombo(id) {
  const B = S.battle, c = D.combos[id];
  B.gauge = 0;
  await msg(`合體技！全員一起推——「${c.name}」！`, 700);
  if (c.kind === 'damage') {
    const power = aliveParty().reduce((s, p) => s + uStat(p, 'atk') * c.atk + uStat(p, 'mag') * c.mag, 0);
    for (const t of aliveEnemies()) {
      const dmg = Math.round(Math.max(1, power - uStat(t, 'def') * 0.5) * (0.95 + Math.random() * 0.1) * elemMult(t, c.elem));
      await applyDamage(null, t, dmg, elemNote(t, c.elem), c.elem);
    }
  } else {
    for (const a of S.party) {
      if (a.hp <= 0) { a.hp = Math.floor(maxHp(a) * 0.3); a.st = {}; await msg(`${ad(a).name}復活了！`, 300); }
      else {
        const h = Math.min(Math.floor(maxHp(a) * 0.6), maxHp(a) - a.hp);
        a.hp += h;
        for (const k of ['burn', 'silence', 'confuse', 'sleep']) delete a.st[k];
        popup(a, '+' + h, 'heal');
      }
      if (a.hp > 0) { a.st.atkUp = Math.max(a.st.atkUp || 0, 3); a.st.defUp = Math.max(a.st.defUp || 0, 3); }
    }
    await msg('全隊回復了！攻擊力與防禦力提升了！', 600);
  }
}
async function applyDamage(u, t, dmg, note, elem) {
  if (S.easy && !isEnemy(t)) dmg = Math.round(dmg * EASY.dmgTaken);  // 簡單模式：我方受到的傷害較少
  if (t.guard) dmg = Math.round(dmg * 0.5);
  dmg = Math.max(1, dmg);
  if (GOD && !isEnemy(t)) dmg = 1;
  t.hp = Math.max(0, t.hp - dmg);
  if (isEnemy(t)) {
    if (u && !isEnemy(u)) addGauge(D.gauge.hit + (note.includes('拔群') ? D.gauge.weak : 0) + (note.includes('神回') ? D.gauge.crit : 0));
    const m = elemMult(t, elem), d = dexEntry(t.id);
    if (m > 1 && !d.weak.includes(elem)) { d.weak.push(elem); note += '（發現弱點：' + EN[elem] + '）'; }
    if (m < 1 && !d.resist.includes(elem)) d.resist.push(elem);
  } else {
    addGauge(D.gauge.hurt);
    if (t.hp <= 0) addGauge(D.gauge.ko);
  }
  popup(t, String(dmg), elemMult(t, elem) > 1 ? 'weak' : isEnemy(t) ? '' : 'hurt');
  if (elem === 'holy' && t.st.hidden) { delete t.st.hidden; note += '（404 被解除了！）'; }
  await flash(t, 'hit');
  await msg(`${note ? note + ' ' : ''}${uname(t)}受到 ${dmg} 點傷害。`, 380);
  if (t.st.sleep && t.hp > 0) { delete t.st.sleep; await msg(`${uname(t)}從潛水中醒來了！`, 300); }
  if (t.hp <= 0) await msg(isEnemy(t) ? `${uname(t)}倒下了！` : `${uname(t)}倒下了……`, 420);
}
function resolveTargets(u, sk, chosen) {
  switch (sk.target) {
    case 'enemy': { const o = oppOf(u); if (chosen && alive(chosen) && o.includes(chosen)) return [chosen]; return o.length ? [pickOne(u, o)] : []; }
    case 'enemies': return oppOf(u);
    case 'ally': { if (chosen && alive(chosen)) return [chosen]; const s = sideOf(u).slice().sort((a, b) => a.hp / uMaxHp(a) - b.hp / uMaxHp(b)); return s.slice(0, 1); }
    case 'allies': return sideOf(u);
    case 'self': return [u];
    case 'deadAlly': return chosen && !alive(chosen) ? [chosen] : (isEnemy(u) ? [] : S.party.filter(a => !alive(a)).slice(0, 1));
    default: return [];
  }
}
const STATUS_MSG = {
  burn: '被炎上了！', silence: '被 sage 了！（無法使用技能）', confuse: '被釣了！（混亂）', sleep: '開始潛水了……（睡眠）',
  atkUp: '攻擊力提升了！', defUp: '防禦力提升了！', atkDown: '攻擊力下降了！', defDown: '防禦力下降了！',
  taunt: '開始挑釁敵人！', counter: '拋出了誘餌！', hidden: '變成了 404 狀態！',
};
async function addStatus(t, st, chance, turns, quietMiss) {
  if (!st || !alive(t)) return;
  const immune = isEnemy(t) ? (t.def.immune || []) : immunesOf(t);
  if (immune.includes(st) || (isEnemy(t) && t.def.boss && st === 'confuse' && Math.random() < 0.5)) { if (!quietMiss) await msg(`${uname(t)}沒有受到影響。`, 320); return; }
  if (Math.random() * 100 >= (chance == null ? 100 : chance)) { if (!quietMiss) await msg(`${uname(t)}沒有中招。`, 320); return; }
  t.st[st] = Math.max(t.st[st] || 0, turns || 3);
  await msg(`${uname(t)}${STATUS_MSG[st]}`, 380);
}
async function doSkill(u, sk, chosen) {
  const B = S.battle;
  if (sk.kind === 'special') {
    if (sk.fx === 'summon') {
      if (aliveEnemies().length >= 3) { await msg('……但是沒有空間分裂了。'); return; }
      const e = newEnemy(sk.summon, ' ' + 'XYZ'[rnd(3)]);
      B.enemies.push(e);
      await msg(`${e.name}也跑來回文了！`);
      return;
    }
    if (sk.fx === 'healself') { const h = Math.floor(u.maxHp * sk.rate); u.hp = Math.min(u.maxHp, u.hp + h); await flash(u, 'heal'); await msg(`${uname(u)}回復了 ${h} HP！`); return; }
    if (sk.fx === 'explode') {
      for (const t of aliveParty()) {
        const dmg = Math.round(Math.max(1, sk.base * (0.9 + Math.random() * 0.2) - uStat(t, 'def') * 0.25));
        await applyDamage(u, t, dmg, '');
      }
      u.hp = 0;
      await msg(`${uname(u)}炸成了碎片！`);
      return;
    }
  }
  const targets = resolveTargets(u, sk, chosen);
  if (sk.target === 'random3') {
    for (let h = 0; h < 3; h++) { const o = oppOf(u); if (!o.length) break; await hitPhys(u, o[rnd(o.length)], sk.power, sk.elem || 'phys'); }
    return;
  }
  if (!targets.length) { await msg('但是沒有效果。'); return; }
  for (const t of targets) {
    if (!alive(t) && sk.kind !== 'revive' && !sk.revive) continue;
    switch (sk.kind) {
      case 'phys': {
        await hitPhys(u, t, sk.power, sk.elem || 'phys');
        if (sk.fx === 'delete' && alive(t) && isEnemy(t) && !t.def.boss && t.hp <= t.maxHp * 0.3) { t.hp = 0; await flash(t, 'hit'); await msg(`${uname(t)}被刪除了！`); }
        if (sk.fx === 'drain' && alive(u)) { const h = Math.round(uStat(u, 'atk') * 0.4); u.hp = Math.min(uMaxHp(u), u.hp + h); }
        if (sk.status) await addStatus(t, sk.status, sk.chance, sk.turns, true);
        break;
      }
      case 'mag': {
        if (t.st.hidden && sk.elem !== 'holy' && Math.random() < 0.75) { await msg('404 Not Found——魔法撲空了！'); break; }
        const dmg = Math.round(magDamage(u, t, sk) * elemMult(t, sk.elem));
        await applyDamage(u, t, dmg, elemNote(t, sk.elem), sk.elem);
        if (sk.status) await addStatus(t, sk.status, sk.chance, sk.turns, true);
        break;
      }
      case 'heal': {
        if (!alive(t) && sk.revive) { t.hp = Math.max(1, Math.floor(uMaxHp(t) * 0.5)); t.st = {}; await msg(`${uname(t)}復活了！`); break; }
        const h = Math.min(healAmount(u, sk), uMaxHp(t) - t.hp);
        t.hp += h;
        popup(t, '+' + h, 'heal');
        await flash(t, 'heal', 200);
        await msg(`${uname(t)}回復了 ${h} HP。`, 330);
        break;
      }
      case 'revive': {
        if (alive(t)) { await msg(`${uname(t)}沒有倒下。`); break; }
        t.hp = Math.max(1, Math.floor(uMaxHp(t) * (sk.rate || 0.5))); t.st = {};
        await flash(t, 'heal');
        await msg(`${uname(t)}被推回來了！復活了！`);
        break;
      }
      case 'buff':
        await addStatus(t, sk.status, 100, sk.turns, true);
        if (sk.status2) await addStatus(t, sk.status2, 100, sk.turns, true);
        break;
      case 'debuff':
        await addStatus(t, sk.status, sk.chance, sk.turns, false);
        if (sk.status2) await addStatus(t, sk.status2, sk.chance2, sk.turns, true);
        break;
      case 'cure':
        for (const k of ['burn', 'silence', 'confuse', 'sleep']) delete t.st[k];
        await msg(`${uname(t)}冷靜下來了。`, 300);
        break;
    }
  }
}
async function endOfRound() {
  const B = S.battle;
  for (const u of [...aliveParty(), ...aliveEnemies()]) {
    u.guard = false;
    if (u.st.burn) {
      const d = isEnemy(u) ? Math.min(Math.floor(u.maxHp * 0.05), 90) : Math.floor(maxHp(u) * 0.06 * (S.easy ? EASY.dmgTaken : 1));
      u.hp = Math.max(0, u.hp - Math.max(1, d));
      await flash(u, 'hit', 160);
      await msg(`${uname(u)}因為炎上受到 ${Math.max(1, d)} 點傷害。`, 360);
      if (u.hp <= 0) await msg(`${uname(u)}倒下了……`);
    }
    for (const k of Object.keys(u.st)) {
      if (k === 'confuse' && Math.random() < 0.3) u.st[k] = 1;
      u.st[k]--;
      if (u.st[k] <= 0) {
        delete u.st[k];
        if (alive(u) && ['silence', 'confuse', 'sleep'].includes(k)) await msg(`${uname(u)}${{ silence: '又可以說話了。', confuse: '清醒過來了。', sleep: '浮上來了。' }[k]}`, 320);
      }
    }
  }
  for (const e of aliveEnemies()) {
    const ev = e.def.ai.every;
    if (ev && (B.turn + 1) % ev[0] === 0 && ev[2]) await msg(ev[2], 750);
  }
}

/* ================================================================ 結局、全滅 */
async function showEnding(id) {
  const e = D.endings[id];
  S.mode = 'ending';
  S.ending = { id, title: e.title, card: false, pid: Math.random().toString(36).slice(2, 10) };
  S.busy = true;
  render();
  await wait(600);
  for (const line of e.lines) await say('', line);
  const m = meta();
  if (!m.endings.includes(id)) m.endings.push(id);
  saveMeta(m);
  S.ending.card = true;
  S.ending.seen = m.endings.length;
  render();
  await new Promise(res => pushMenu({ cls: 'center', build: () => [{ label: '回到標題' }], onPick: () => { popMenu(); res(); }, onBack: () => {} }));
  toTitle();
}
async function gameOver() {
  S.mode = 'gameover';
  S.busy = true;
  render();
  await new Promise(() => pushMenu({
    cls: 'center', cursor: hasSave() ? 0 : 1,  // 沒有存檔時，游標直接停在「回到標題」
    build: () => [{ label: '從存檔把串推回來', disabled: !hasSave() }, { label: '回到標題' }],
    onBack: () => {},
    onPick: i => { if (i === 0) { loadGame(); render(); } else toTitle(); },
  }));
}
function toTitle() {
  S = freshState();
  built = null;
  pushMenu({
    cls: 'center title', build: () => [{ label: '開新串' }, { label: '回到串裡', disabled: !hasSave() }],
    onBack: () => {},
    onPick: i => {
      if (i === 0) pushMenu({
        title: '選擇難度', cls: 'center',
        build: () => [
          { label: '普通', desc: '原本的難度。怪物會追人，魔王不好打。' },
          { label: '簡單', desc: '敵人比較弱、受到的傷害較少、經驗值與 K 幣 1.5 倍、「無視」一定成功、怪物比較少也不太追人。適合想專心看劇情的島民。之後也能在「設定」裡切換。' },
          { label: '全自動', desc: '電腦幫你從頭玩到結局（簡單難度）。主線、支線、戰鬥、買裝備都會自動進行，你只要看就好。隨時可以在「設定」裡關掉，接手自己玩。' },
        ],
        onPick: j => { newGame(j >= 1); if (j === 2) setAuto(true); },
      });
      else { loadGame(); render(); toast('串浮上來了。從存檔繼續。'); }
    },
  });
}
function newGame(easy) {
  S = freshState();
  S.easy = !!easy;
  built = null;
  const st = D.start;
  S.party = st.party.map(id => makeActor(id, D.actors[id].joinLevel));
  S.gold = st.gold;
  for (const [id, n] of st.items) addItem(id, n);
  S.mode = 'map';
  teleport(st.map, st.x, st.y, st.dir);
  render();
  runBusy(st.script);
}

/* ================================================================ 全自動模式
   開啟後由電腦代替玩家：走路、對話、選擇、戰鬥、買裝備、換裝備，一路玩到結局。
   怎麼決定下一步：對每個看得到的人「預演」他的對話腳本（在狀態的複本上跑一次，不會真的改到遊戲）。
   - 會讓劇情前進的（設新旗標、給道具、開／完成任務、開戰、入隊、去沒去過的地方）→ 要去找他（不管在哪張地圖）
   - 台詞跟上次聽過的不一樣 → 「有新對話」，在同一張地圖裡就順便聊一下
   - 結局只在什麼都做完之後才去
   跨地圖的路線用傳送點、船夫這類會載人的 NPC、跳串（快速移動）一起算最短的走法。 */
const AUTO_SPEEDS = [1, 0.55, 0.3], AUTO_SPEED_NAMES = ['普通', '快', '超快'];
let autoSpeed = 0, autoNext = 0, autoPlan = null, autoBusy = false, autoTalk = null, autoIntent = null, autoInvKey = '';
let autoSkip = {}, autoFails = 0, autoLost = 0, autoDlg = null;
let TOGGLES = new Set();   // 會被 unflag 的旗標（例如外來種的男／女切換），不算劇情前進
const autoDelay = ms => ms * SPEED * AUTO_SPEEDS[autoSpeed];

function setAuto(on) {
  if (!S) return;
  S.auto = !!on;
  autoPlan = null; autoTalk = null; autoIntent = null; autoSkip = {}; autoFails = 0;
  S.autoSeen = S.autoSeen || {};
  if (on) {
    S.easy = true;   // 全自動一律用簡單難度
    holdClear();
    toast('全自動模式開啟（難度：簡單）');
  } else { S.autoNote = ''; toast('全自動模式關閉，換你自己玩了'); }
  render();
}
function scanToggles() {
  TOGGLES = new Set();
  const walk = sc => { for (const c of sc || []) {
    if (c[0] === 'unflag') TOGGLES.add(c[1]);
    else if (c[0] === 'if') { walk(c[2]); walk(c[3]); }
    else if (c[0] === 'choice') c.slice(1).forEach(o => walk(o[1]));
  } };
  for (const m of Object.values(D.maps)) { m.ents.forEach(e => walk(e.script)); (m.auto || []).forEach(a => walk(a.script)); }
  Object.values(D.calls || {}).forEach(walk);
}

/* ---- 預演：在狀態的複本上把腳本跑一次，看它會做什麼 ---- */
function simState() { return { flags: { ...S.flags }, inv: { ...S.inv }, karma: S.karma, gold: S.gold, quests: { ...S.quests }, party: S.party.map(a => a.id) }; }
function simClone(st) { return { flags: { ...st.flags }, inv: { ...st.inv }, karma: st.karma, gold: st.gold, quests: { ...st.quests }, party: st.party.slice() }; }
function newAcc() { return { prod: 0, karma: 0, sig: '', who: '', shops: [], warp: null, ending: null, battle: null }; }
function simRun(script, st, acc, depth = 0) {
  if (depth > 30) return;
  for (const c of script || []) if (simExec(c, st, acc, depth) === STOP) return STOP;
}
function simExec(c, st, acc, depth) {
  switch (c[0]) {
    case 'say': acc.sig += c[1] + '|' + c.slice(2).join('/') + ';'; if (!acc.who && c[1] && c[1] !== '無名氏') acc.who = c[1]; break;
    case 'if': return cond(c[1], st) ? simRun(c[2], st, acc, depth + 1) : simRun(c[3], st, acc, depth + 1);
    case 'choice': { const i = autoPick(c.slice(1), st); acc.sig += '?' + i; return simRun(c[1 + i][1], st, acc, depth + 1); }
    case 'flag': if (!st.flags[c[1]]) { st.flags[c[1]] = true; if (!TOGGLES.has(c[1])) acc.prod++; } break;
    case 'unflag': delete st.flags[c[1]]; break;
    case 'give': st.inv[c[1]] = (st.inv[c[1]] || 0) + (c[2] || 1); acc.prod++; break;
    case 'take': if (st.inv[c[1]]) { st.inv[c[1]] = Math.max(0, st.inv[c[1]] - (c[2] || 1)); acc.prod++; } break;
    case 'gold': st.gold += c[1]; acc.prod++; break;
    case 'quest': if (st.quests[c[1]] !== 'done' && st.quests[c[1]] !== c[2]) { st.quests[c[1]] = c[2]; acc.prod++; } break;
    case 'karma': st.karma += c[1]; acc.karma += c[1]; break;
    case 'battle': acc.battle = c[1]; acc.prod++; break;
    case 'join': if (!st.party.includes(c[1])) { st.party.push(c[1]); acc.prod++; } break;
    case 'warp': acc.warp = c[1]; if (!S.visited[c[1]]) acc.prod++; break;
    case 'ending': acc.ending = c[1]; acc.prod++; return STOP;
    case 'call': return simRun(D.calls[c[1]], st, acc, depth + 1);
    case 'shop': acc.shops.push(c[1]); break;
    case 'board': acc.sig += 'B' + c[1] + ':' + boardPosts(c[1]).length + ';'; break;
  }
}
// 選項怎麼選：善行（karma）最優先，再來是會讓劇情前進的；不逛照燒攤、不坐船回頭（除非正要去那裡）
function autoPick(opts, st) {
  let best = 0, bestScore = -Infinity;
  opts.forEach(([, branch], i) => {
    const a = newAcc();
    simRun(branch, simClone(st), a, 1);
    let sc = a.karma * 10 + a.prod;
    if (a.shops.length) sc -= 0.5;
    if (a.warp) sc += autoIntent === a.warp ? 100 : S.visited[a.warp] ? -50 : 0;
    if (a.ending === 'real') sc -= 1;
    if (sc > bestScore) { bestScore = sc; best = i; }
  });
  return best;
}
function entInfo(mapId, e) {
  if (e.chest) { const a = newAcc(); a.prod = S.flags[`chest:${mapId}:${e.id}`] ? 0 : 1; a.who = '寶箱'; return a; }
  const a = newAcc();
  simRun(e.script, simState(), a);
  return a;
}
// 會載人去別的地方的 NPC（船夫）：腳本裡只有對話和傳送，沒有戰鬥或其他事件
function ferryOf(e) {
  let found = null, bad = false;
  const walk = sc => { for (const c of sc || []) {
    if (bad) return;
    if (c[0] === 'warp') { found = found || c; }
    else if (c[0] === 'if') walk(cond(c[1]) ? c[2] : c[3]);
    else if (c[0] === 'choice') c.slice(1).forEach(o => walk(o[1]));
    else if (['battle', 'ending', 'join', 'give', 'flag', 'quest'].includes(c[0])) bad = true;
  } };
  walk(e.script);
  return bad ? null : found;
}

/* ---- 裝備：依角色是物理型還是魔法型，替每件裝備打分數 ---- */
function isCaster(a) { const d = ad(a); return d.growth.mag > d.growth.atk; }
function equipScore(a, id) {
  if (!id) return 0;
  const it = D.items[id], st = it.stats || {}, c = isCaster(a);
  const w = { atk: c ? 0.4 : 2, mag: c ? 2 : 0.3, def: 1.2, spd: 0.8, hp: 0.25, mp: c ? 0.3 : 0.1 };
  let s = 0;
  for (const k in st) s += (w[k] || 0) * st[k];
  return s + (it.immune || []).length * 6;
}
function autoEquipAll() {
  for (const slot of ['weapon', 'armor', 'acc']) for (const a of S.party) {
    const cur = a.equip[slot];
    let best = cur, bs = equipScore(a, cur);
    for (const id of invList((it, iid) => slotOf(iid) === slot && canEquip(a, iid))) { const sc = equipScore(a, id); if (sc > bs + 0.01) { bs = sc; best = id; } }
    if (best && best !== cur) {
      removeItem(best);
      if (cur) addItem(cur);
      a.equip[slot] = best;
      a.hp = Math.min(a.hp, maxHp(a)); a.mp = Math.min(a.mp, maxMp(a));
      toast(`${ad(a).name}換上了【${D.items[best].name}】`);
    }
  }
}
// 這間店有沒有買得起、又比現在好的裝備？回傳要買的清單（每個人每個欄位最多一件）
function shopBuys(shopId) {
  const list = (D.shops[shopId] || []).filter(id => slotOf(id));
  if (!list.length) return [];
  const pool = { ...S.inv }, buys = [];
  let g = S.gold;
  for (const slot of ['weapon', 'armor', 'acc']) for (const a of S.party) {
    let have = a.equip[slot], hs = equipScore(a, have);
    for (const id of Object.keys(pool)) if (pool[id] > 0 && slotOf(id) === slot && canEquip(a, id) && equipScore(a, id) > hs) { have = id; hs = equipScore(a, id); }
    if (have && have !== a.equip[slot]) pool[have]--;   // 背包裡的備品先留給這個人
    let best = null, bs = hs;
    for (const id of list) {
      if (slotOf(id) !== slot || !canEquip(a, id) || D.items[id].price > g) continue;
      const sc = equipScore(a, id);
      if (sc > bs + 0.01) { bs = sc; best = id; }
    }
    if (best) { buys.push(best); g -= D.items[best].price; }
  }
  return buys;
}

/* ---- 路線：地圖內用 BFS，跨地圖把傳送點、船夫、跳串當成邊，用最短路徑 ---- */
function walkM(m, x, y) { return y >= 0 && y < m.rows.length && x >= 0 && x < m.rows[0].length && D.tiles[m.rows[y][x]][1] === 1; }
function bfsMap(mapId, sx, sy) {
  const m = D.maps[mapId], W = m.rows[0].length, H = m.rows.length;
  const block = new Set(m.ents.filter(e => cond(e.show)).map(e => e.y * W + e.x));
  const warps = new Set(m.warps.map(w => w[1] * W + w[0]));
  const dist = new Int32Array(W * H).fill(-1), prev = new Int32Array(W * H).fill(-1);
  const q = [sy * W + sx];
  dist[q[0]] = 0;
  for (let h = 0; h < q.length; h++) {
    const c = q[h], x = c % W, y = (c - x) / W;
    if (h > 0 && warps.has(c)) continue;   // 踩上傳送點就會被傳走，不能再往前
    for (const [dx, dy] of [[0, -1], [0, 1], [-1, 0], [1, 0]]) {
      const nx = x + dx, ny = y + dy, n = ny * W + nx;
      if (!walkM(m, nx, ny) || block.has(n) || dist[n] >= 0) continue;
      dist[n] = dist[c] + 1; prev[n] = c; q.push(n);
    }
  }
  return {
    W, dist: (x, y) => (x < 0 || y < 0 || x >= W || y >= H) ? -1 : dist[y * W + x],
    path(x, y) {   // 回傳方向字串陣列
      const out = [];
      let c = y * W + x;
      while (prev[c] >= 0) { const p = prev[c], d = c - p; out.push(d === 1 ? 'R' : d === -1 ? 'L' : d === W ? 'D' : 'U'); c = p; }
      return out.reverse();
    },
  };
}
// 站在哪裡可以跟 (ex, ey) 的人說話：正前方，或隔著櫃台
function standFor(bfs, mapId, e) {
  const m = D.maps[mapId];
  let best = null;
  for (const [dir, [dx, dy]] of Object.entries(STEP)) {
    const cands = [[e.x - dx, e.y - dy]];
    if ((m.rows[e.y - dy] || '')[e.x - dx] === 'u') cands.push([e.x - 2 * dx, e.y - 2 * dy]);
    for (const [x, y] of cands) {
      const d = bfs.dist(x, y);
      if (d < 0 || m.warps.some(w => w[0] === x && w[1] === y)) continue;
      if (!best || d < best.d) best = { d, x, y, dir };
    }
  }
  if (best) best.path = bfs.path(best.x, best.y);
  return best;
}
// 目前目標提到的地圖（加上設定目標時所在的地圖）：主線要往那裡走
function goalMaps() {
  const g = S.goal || '', set = new Set(S.goalMap ? [S.goalMap] : []);
  for (const [mid, m] of Object.entries(D.maps)) {
    const base = m.name.split(' ')[0].replace(/(外圍|內部)$/, '');
    if (g.includes(m.name) || g.includes(base)) set.add(mid);
  }
  return set;
}
/* 目標的優先順序（數字小的先做）：
   0 這張地圖上的事（聊天、開寶箱、買裝備、任務）   1 主線：目前目標提到的地圖、或頭上有「！」的人
   2 其他地圖的支線與寶箱   3 不在目前目標裡的魔王戰（免得跳過劇情先打掉）   4 結局 */
function autoTargets() {
  const out = [], gm = goalMaps();
  for (const [mid, m] of Object.entries(D.maps)) {
    for (const e of m.ents) {
      if (!cond(e.show)) continue;
      const key = mid + ':' + e.id;
      if (autoSkip[key] === autoStateKey()) continue;
      const a = entInfo(mid, e);
      const here = mid === S.mapId, main = gm.has(mid) || (e.mark && cond(e.mark));
      const boss = a.battle && D.troops[a.battle].some(id => D.enemies[id].boss);
      if (a.prod > 0) out.push({ map: mid, ent: e, key, prio: a.ending ? 4 : boss && !main ? 3 : here ? 0 : main ? 1 : 2, label: a.who });
      else if (here && a.sig && S.autoSeen[key] !== a.sig) out.push({ map: mid, ent: e, key, prio: 0, label: a.who });
      else if (here && a.shops.some(id => shopBuys(id).length)) out.push({ map: mid, ent: e, key, prio: 0, label: a.who + '（買裝備）', shop: true });
    }
    if (mid !== S.mapId) for (const au of m.auto || []) {
      if (!cond(au.cond)) continue;
      const a = newAcc();
      simRun(au.script, simState(), a);
      if (a.prod > 0) { out.push({ map: mid, ent: null, key: mid + ':auto', prio: gm.has(mid) ? 1 : 2, label: m.name }); break; }
    }
  }
  return out;
}
function autoStateKey() {
  return [S.mapId, Object.keys(S.flags).length, JSON.stringify(S.inv), JSON.stringify(S.quests), S.party.length, Object.keys(S.autoSeen).length, S.gold >> 6].join('|');
}
function autoComputePlan() {
  const targets = autoTargets();
  if (!targets.length) return null;
  const seen = new Set(), pq = [{ map: S.mapId, x: S.x, y: S.y, cost: 0, legs: [] }];
  let best = null;
  const better = (c) => !best || c.prio < best.prio || (c.prio === best.prio && c.cost < best.cost);
  for (let n = 0; pq.length && n < 120; n++) {
    pq.sort((a, b) => a.cost - b.cost);
    const node = pq.shift(), nk = node.map + ':' + node.x + ':' + node.y;
    if (seen.has(nk)) continue;
    seen.add(nk);
    if (best && node.cost > best.cost && best.prio === 0) break;
    const bfs = bfsMap(node.map, node.x, node.y);
    for (const t of targets) if (t.map === node.map) {
      if (!t.ent) { if (node.legs.length && better({ prio: t.prio, cost: node.cost })) best = { ...t, cost: node.cost, legs: node.legs }; continue; }
      const st = standFor(bfs, node.map, t.ent);
      if (!st) continue;
      const cost = node.cost + st.d;
      if (better({ prio: t.prio, cost })) best = { ...t, cost, legs: node.legs.concat([{ map: node.map, path: st.path, act: 'talk', dir: st.dir, ent: t.ent.id, key: t.key }]) };
    }
    const m = D.maps[node.map];
    for (const w of m.warps) {
      const d = bfs.dist(w[0], w[1]);
      if (d > 0) pq.push({ map: w[2], x: w[3], y: w[4], cost: node.cost + d + 2, legs: node.legs.concat([{ map: node.map, path: bfs.path(w[0], w[1]), act: 'walk' }]) });
    }
    for (const e of m.ents) {
      if (!cond(e.show)) continue;
      const f = ferryOf(e);
      if (!f || f[1] === node.map) continue;
      const st = standFor(bfs, node.map, e);
      if (st) pq.push({ map: f[1], x: f[2], y: f[3], cost: node.cost + st.d + 6, legs: node.legs.concat([{ map: node.map, path: st.path, act: 'ferry', dir: st.dir, ent: e.id, to: f[1] }]) });
    }
    if (!node.legs.length && !(D.noTravel || []).includes(node.map)) {
      for (const tp of D.travel || []) if (tp.map !== node.map && S.visited[tp.map] && cond(tp.cond)) pq.push({ map: tp.map, x: tp.x, y: tp.y, cost: 40, legs: [{ map: node.map, path: [], act: 'travel', tp }] });
    }
  }
  if (!best) return null;
  return { legs: best.legs.map(l => ({ ...l, path: l.path.slice() })), label: best.ent ? `${D.maps[best.map].name}：${best.label || '看看'}` : `前往${D.maps[best.map].name}`, key: autoStateKey(), tkey: best.key };
}

/* ---- 戰鬥：補血、復活、打弱點、能一次打全部就打全部 ---- */
function estHit(u, t, sk) {
  const raw = sk.kind === 'mag' ? Math.max(1, uStat(u, 'mag') * (sk.power || 1) + (sk.base || 0) - uStat(t, 'def') * 0.25)
    : Math.max(1, uStat(u, 'atk') * (sk.power || 1) - uStat(t, 'def') * 0.5);
  const elem = sk.elem || 'phys';
  return raw * elemMult(t, elem) * (t.st.hidden && elem !== 'holy' ? 0.25 : 1) * (t.st.counter && sk.kind === 'phys' ? 0.4 : 1);
}
async function autoCommand(a) {
  const B = S.battle;
  await bwait(150);
  const foes = aliveEnemies(), allies = aliveParty(), dead = S.party.filter(x => x.hp <= 0);
  if (B.gauge >= 100 && !B.comboQueued) {
    B.comboQueued = true;
    const hurt = allies.filter(x => x.hp < maxHp(x) * 0.45).length + dead.length;
    return { type: 'combo', u: a, combo: hurt >= 2 ? 'pushall' : 'godthread' };
  }
  const sks = a.st.silence ? [] : skillsOf(a).map(id => [id, D.skills[id]]).filter(([, sk]) => a.mp >= sk.mp);
  const rev = sks.find(([, sk]) => sk.kind === 'revive' || (sk.revive && sk.kind === 'heal'));
  if (dead.length && rev) return { type: 'skill', u: a, sk: rev[0], t: dead[0] };
  const hurt = allies.filter(x => x.hp < maxHp(x) * 0.5).sort((x, y) => x.hp / maxHp(x) - y.hp / maxHp(y));
  if (hurt.length) {
    const heals = sks.filter(([, sk]) => sk.kind === 'heal' && !sk.revive);
    const group = heals.filter(([, sk]) => sk.target === 'allies').sort((x, y) => y[1].base - x[1].base);
    const single = heals.filter(([, sk]) => sk.target === 'ally');
    if (hurt.length >= 2 && group.length) return { type: 'skill', u: a, sk: group[0][0] };
    if (single.length) return { type: 'skill', u: a, sk: single[0][0], t: hurt[0] };
    if (group.length) return { type: 'skill', u: a, sk: group[0][0] };
  }
  const bad = allies.filter(x => x.st.silence || x.st.confuse || x.st.sleep).length;
  const cure = sks.find(([, sk]) => sk.kind === 'cure');
  if (bad >= 2 && cure) return { type: 'skill', u: a, sk: cure[0] };
  const target = foes.slice().sort((x, y) => x.hp - y.hp)[0];
  let best = { type: 'attack', u: a, t: target }, bestVal = estHit(a, target, { kind: 'phys', power: 1 });
  for (const [id, sk] of sks) {
    if (!['phys', 'mag'].includes(sk.kind) || sk.mp <= 0) continue;
    let val;
    if (sk.target === 'enemies') val = foes.reduce((s, t) => s + estHit(a, t, sk), 0);
    else if (sk.target === 'random3') val = estHit(a, target, sk) * 3;
    else if (sk.target === 'enemy') {
      // 單體技能：挑這招打起來最痛的那一隻（打弱點）
      let bt = target, bv = estHit(a, target, sk);
      for (const t of foes) { const v = estHit(a, t, sk) * (t.hp <= bv ? 1.2 : 1); if (v > bv) { bv = v; bt = t; } }
      val = bv;
      if (val > bestVal * 1.2) { bestVal = val; best = { type: 'skill', u: a, sk: id, t: bt }; }
      continue;
    } else continue;
    if (val > bestVal * 1.2) { bestVal = val; best = { type: 'skill', u: a, sk: id, t: null }; }
  }
  return best;
}
async function autoRevive() {
  for (const a of S.party) if (a.hp <= 0) {
    a.hp = maxHp(a); a.mp = maxMp(a); a.st = {};
    popup(a, 'AUTO', 'heal');
    await msg(`（全自動）${ad(a).name}被推回來了！HP 與 MP 全滿！`, 500);
  }
}

/* ---- 每 40 毫秒看一次現在該做什麼 ---- */
function autoTick() {
  if (!S || !D || !S.auto || autoBusy) return;
  const now = performance.now();
  if (now < autoNext) return;
  const later = ms => { autoNext = now + autoDelay(ms); };
  const top = S.menus[S.menus.length - 1];
  if (S.menus.length && S.menus[0].cls === 'main') return;   // 玩家自己打開了選單：暫停
  if (S.mode === 'ending') {
    if (S.dialog && !S.menus.length) {
      if (autoDlg !== S.dialog) { autoDlg = S.dialog; later(900 + S.dialog.text.length * 130); }
      else { autoDlg = null; advanceDialog(); later(40); }
    }
    else if (S.ending && S.ending.card && !S.autoDone) { S.autoDone = true; S.autoNote = '全破！'; toast('全自動模式：全破了！'); }
    return;
  }
  if (S.mode === 'gameover') { if (top) { top.onPick(hasSave() ? 0 : 1); later(800); } return; }
  if (S.mode === 'title') return;
  if (S.card) { S.card.res(); later(300); return; }
  if (S.board) { closeBoard(); later(300); return; }
  if (S.waitOk) { const r = S.waitOk; S.waitOk = null; r(); later(250); return; }
  if (top && /battle/.test(top.cls || '')) {   // 剛打開全自動時還停在戰鬥選單：交給「自動」
    const items = menuItems(top), i = items.findIndex(it => it.cmd === 'auto');
    if (i >= 0) top.onPick(i, items[i]); else if (top.onBack) top.onBack(); else popMenu();
    later(200); return;
  }
  if (top && top.cls === 'choice') {
    const ac = S.autoChoice;
    let i = 0;
    if (Array.isArray(ac)) i = autoPick(ac, simState());
    else if (ac && ac.inn) i = (S.gold >= ac.inn && S.party.some(a => a.hp < maxHp(a) || a.mp < maxMp(a))) ? 0 : 1;
    S.autoChoice = null;
    top.cursor = i; render();
    autoBusy = true;
    setTimeout(() => { autoBusy = false; if (S.menus[S.menus.length - 1] === top) top.onPick(i, menuItems(top)[i]); }, autoDelay(450));
    later(500); return;
  }
  if (top && /shop/.test(top.cls || '')) {
    if (top.title === '商店') {
      for (const id of shopBuys(S.shopId)) { S.gold -= D.items[id].price; addItem(id); toast(`買了【${D.items[id].name}】`); }
      autoEquipAll();
      top.onBack ? top.onBack() : popMenu();
    } else popMenu();
    later(500); return;
  }
  if (S.dialog && !S.menus.length) {   // 每句話停留一段「讀得完」的時間再翻頁
    if (autoDlg !== S.dialog) { autoDlg = S.dialog; later(500 + S.dialog.text.length * 110); return; }
    autoDlg = null; advanceDialog(); later(40); return;
  }
  if (S.mode !== 'map' || S.busy || S.menus.length || S.dialog) return;

  // ---- 地圖上、可以自由行動 ----
  if (autoTalk) {   // 剛剛跟誰說完話：把現在聽得到的台詞記成「聽過了」
    const m = D.maps[autoTalk.map], e = m && m.ents.find(x => x.id === autoTalk.ent);
    if (e) S.autoSeen[autoTalk.key] = entInfo(autoTalk.map, e).sig;
    if (autoStateKey() === autoTalk.before) autoSkip[autoTalk.key] = autoStateKey();   // 說了也沒變化：先跳過
    autoTalk = null; autoIntent = null; autoPlan = null;
  }
  const ik = JSON.stringify(S.inv) + S.party.length;
  if (ik !== autoInvKey) { autoInvKey = ik; autoEquipAll(); }
  if (!autoPlan || autoPlan.key !== autoStateKey() || !autoPlan.legs.length || autoPlan.legs[0].map !== S.mapId) {
    autoPlan = autoComputePlan();
    if (!autoPlan) {
      autoLost++;
      S.autoNote = '（四處看看……）';
      const dirs = Object.keys(STEP).filter(d => { const [dx, dy] = STEP[d]; return walkable(S.x + dx, S.y + dy) && !entAt(S.x + dx, S.y + dy) && !warpAt(S.x + dx, S.y + dy); });
      if (dirs.length) moveStep(dirs[rnd(dirs.length)]);
      later(400); return;
    }
    autoLost = 0;
    S.autoNote = autoPlan.label;
  }
  const leg = autoPlan.legs[0];
  if (leg.path.length) {
    const fx = S.x, fy = S.y, r = moveStep(leg.path[0]);
    if (r === true && (S.x !== fx || S.y !== fy || S.mapId !== leg.map)) { leg.path.shift(); autoFails = 0; if (S.mapId !== leg.map) autoPlan.legs.shift(); }
    else if (r !== 'mon' && ++autoFails > 3) { autoSkip[autoPlan.tkey] = autoStateKey(); autoPlan = null; autoFails = 0; }
    later(150); return;
  }
  if (leg.act === 'travel') {
    toast('跳串：' + leg.tp.name);
    teleport(leg.tp.map, leg.tp.x, leg.tp.y, leg.tp.dir); built = null; saveGame(); render(); runBusy([]);
    autoPlan = null; later(500); return;
  }
  if (leg.act === 'talk' || leg.act === 'ferry') {
    S.dir = leg.dir; render();
    const [dx, dy] = STEP[leg.dir];
    let fx = S.x + dx, fy = S.y + dy;
    if (tileAt(fx, fy) === 'u') { fx += dx; fy += dy; }
    const e = entAt(fx, fy);
    if (!e || e.id !== leg.ent) { autoSkip[autoPlan.tkey] = autoStateKey(); autoPlan = null; later(200); return; }
    autoTalk = { map: S.mapId, ent: e.id, key: S.mapId + ':' + e.id, before: autoStateKey() };
    if (leg.act === 'ferry') autoIntent = leg.to;
    autoPlan.legs.shift();
    autoBusy = true;
    setTimeout(() => { autoBusy = false; interact(); }, autoDelay(250));
    later(400); return;
  }
  autoPlan.legs.shift();
  later(100);
}

/* ================================================================ 繪製 */
let built = null;
const el = id => document.getElementById(id);
function bar(cls, v, max) { return `<span class="bar ${cls}"><span style="width:${pct(v, max)}%"></span></span>`; }
function statusBadges(u) {
  return Object.keys(u.st || {}).filter(k => D.statuses[k]).map(k => `<span class="badge" style="--c:${D.statuses[k].color}">${esc(D.statuses[k].name)}</span>`).join('');
}
function render() {
  if (!S || !D) return;
  const scr = el('scr');
  scr.dataset.mode = S.mode;
  let html = '';
  if (S.mode === 'title') html = renderTitle();
  else if (S.mode === 'map') { renderMap(); }
  else if (S.mode === 'battle') html = renderBattle();
  else if (S.mode === 'gameover') html = `<div class="full over"><h2>本串已沉。</h2><p>全隊倒下了……沒有人回應，島沉得更深了。</p></div>`;
  else if (S.mode === 'ending') html = renderEnding();
  const mapLayer = el('maplayer');
  mapLayer.hidden = S.mode !== 'map';
  el('alt').innerHTML = html;
  el('alt').hidden = S.mode === 'map';
  el('ov').innerHTML = renderOverlays();
  for (const li of el('ov').querySelectorAll('.menu.active li.sel')) li.scrollIntoView({ block: 'nearest' });
  const bn = el('bn');
  if (S.mode !== 'map' || !S.banner) { bn.innerHTML = ''; shownBanner = -1; }
  else if (shownBanner !== S.bannerId) { shownBanner = S.bannerId; bn.innerHTML = `<div class="banner">${esc(S.banner)}</div>`; }
}
let shownBanner = -1;
function renderTitle() {
  return `<div class="full title"><img class="t-hero" src="img/hero.png" alt=""><h1>${esc(D.title)}</h1><p class="sub">${esc(D.subtitle)}</p><p class="hint">↑↓ 選擇　Enter 決定</p></div>`;
}
function renderEnding() {
  const e = S.ending;
  if (!e.card) return `<div class="full ending dim"><h2>${esc(e.title)}</h2></div>`;
  const lv = S.party[0] ? S.party[0].level : 1;
  const t = S.playTime;
  return `<div class="full ending"><div class="post"><div class="post-h"><b>無標題</b>　名稱：<b class="nm">無名氏</b>　ID:${e.pid}　No.1</div><p>～ 完 ～</p><p>${esc(e.title)}</p><p class="small">Lv ${lv}　遊玩時間 ${Math.floor(t / 3600)}:${String(Math.floor(t / 60) % 60).padStart(2, '0')}　已看過的結局 ${e.seen} / 3</p>${e.seen < 3 ? '<p class="small">（還有其他的結局……）</p>' : '<p class="small">你看過了所有的結局。謝謝遊玩。</p>'}</div></div>`;
}
function renderMap() {
  const m = curMap();
  const W = m.rows[0].length, H = m.rows.length;
  const layer = el('maplayer');
  if (built !== S.mapId) {
    built = S.mapId;
    let t = '';
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) t += `<i class="tile" style="left:${x * T}px;top:${y * T}px;background-image:url(img/${D.tiles[m.rows[y][x]][0]}.png)"></i>`;
    layer.classList.add('noanim');
    layer.innerHTML = `<div id="tiles" style="width:${W * T}px;height:${H * T}px">${t}</div><div id="ents"></div><div id="mons"></div><img id="pl" class="sprite pl" alt="">`;
    requestAnimationFrame(() => requestAnimationFrame(() => layer.classList.remove('noanim')));
  }
  const cx = clamp(S.x - 7, 0, W - VW), cy = clamp(S.y - 5, 0, H - VH);
  layer.style.transform = `translate(${-cx * T}px,${-cy * T}px)`;
  el('ents').innerHTML = visibleEnts().map(e => {
    const sp = e.chest ? (S.flags[chestFlag(e)] ? 'chest_open' : 'chest') : e.sprite;
    // 頭上的「！」：提示現在該找這個人說話
    const mark = e.mark && cond(e.mark) ? `<div class="mark" style="left:${e.x * T}px;top:${e.y * T - 32}px">！</div>` : '';
    return `<img class="sprite" src="img/${sp}.png" alt="" style="left:${e.x * T}px;top:${e.y * T}px">${mark}`;
  }).join('');
  renderMons();
  const pl = el('pl');
  const src = `img/${heroSprite()}.png`;
  if (pl.getAttribute('src') !== src) pl.setAttribute('src', src);
  pl.classList.toggle('flip', S.dir === 'L');
  pl.style.left = S.x * T + 'px';
  pl.style.top = S.y * T + 'px';
}
// 怪物用固定的元素，移動時才有平滑的動畫
function renderMons() {
  const box = el('mons');
  if (!box) return;
  const have = new Map([...box.children].map(c => [c.dataset.id, c]));
  for (const m of S.mons) {
    let img = have.get(m.id);
    if (!img) { img = document.createElement('img'); img.className = 'sprite mon'; img.alt = ''; img.dataset.id = m.id; img.src = `img/${m.sprite}.png`; box.appendChild(img); }
    have.delete(m.id);
    img.style.left = m.x * T + 'px';
    img.style.top = m.y * T + 'px';
    img.classList.toggle('chase', m.chasing);
  }
  for (const c of have.values()) c.remove();
}
function renderBattle() {
  const B = S.battle;
  const en = B.enemies.map(e => `<div class="foe ${e.def.size === 'l' ? 'big' : ''} ${alive(e) ? '' : 'dead'} ${e.fx} ${B.hi === e ? 'hi' : ''}" data-u="${e.uid}">
      <div class="foe-name">${esc(e.name)}</div>${bar('en', e.hp, e.maxHp)}<div class="badges">${statusBadges(e)}${knownText(e.id) ? `<span class="weak">${esc(knownText(e.id))}</span>` : ''}</div>
      <img src="img/${e.def.sprite}.png" alt="${esc(e.name)}"></div>`).join('');
  const party = S.party.map((a, i) => `<div class="pc ${B.actor === i ? 'act' : ''} ${a.hp <= 0 ? 'ko' : ''} ${a.fx || ''} ${B.hi === a ? 'hi' : ''}" data-u="p-${a.id}">
      <img src="img/${ad(a).sprite}.png" alt=""><div class="pc-b"><div class="pc-n"><b>${esc(ad(a).name)}</b> Lv${a.level} ${statusBadges(a)}</div>
      <div class="pc-r">HP ${bar('hp', a.hp, maxHp(a))} <span>${a.hp}</span></div><div class="pc-r">MP ${bar('mp', a.mp, maxMp(a))} <span>${a.mp}</span></div></div></div>`).join('');
  return `<div class="bscreen bg-${B.bg} ${B.intro ? 'intro' : ''}">
    <div class="log">${B.log.map(l => `<div>${esc(l)}</div>`).join('')}</div>
    <div class="foes">${en}</div>
    <div class="gauge ${B.gauge >= 100 ? 'gmax' : ''}"><b>推</b><span class="gbar"><span style="width:${B.gauge}%"></span></span><em>${B.gauge >= 100 ? 'MAX！合體技' : B.gauge + '%'}</em></div>
    <div class="bpanel"><div class="party">${party}</div><div class="bslot"></div></div></div>`;
}
function menuHtml(m, active) {
  const items = menuItems(m);
  const cur = items[m.cursor];
  let extra = '';
  if (m.cls === 'status') extra = statusPanel(m.actor);
  if (m.cls === 'quests') extra = questPanel();
  if (/dex/.test(m.cls || '') && cur && cur.id) {
    const seen = S.dex[cur.id] && S.dex[cur.id].seen;
    extra = `<div class="dexpic">${seen ? `<img src="img/${D.enemies[cur.id].sprite}.png" alt="">` : '<span>？</span>'}</div>`;
  }
  const list = items.map((it, i) => `<li class="${i === m.cursor ? 'sel' : ''} ${it.disabled ? 'dis' : ''}" data-i="${i}"><span>${esc(it.label)}</span>${it.right ? `<em>${esc(it.right)}</em>` : ''}</li>`).join('');
  return `<div class="menu ${m.cls || ''} ${active ? 'active' : ''}">${m.title ? `<div class="mt">${esc(m.title)}${/shop/.test(m.cls || '') ? `<span>${S.gold} K 幣</span>` : ''}</div>` : ''}
    ${extra}<ul>${list}</ul>${cur && cur.desc ? `<div class="md">${esc(cur.desc)}</div>` : ''}</div>`;
}
function statusPanel(a) {
  const row = k => `<tr><th>${STATN[k] === 'HP' || STATN[k] === 'MP' ? STATN[k] : { atk: '攻擊', def: '防禦', mag: '魔力', spd: '速度' }[k]}</th><td>${k === 'hp' ? a.hp + ' / ' + maxHp(a) : k === 'mp' ? a.mp + ' / ' + maxMp(a) : stat(a, k)}</td></tr>`;
  const next = a.level >= D.maxLevel ? '—' : expFor(a.level + 1) - a.exp;
  return `<div class="stat"><div class="stat-top"><img src="img/${ad(a).sprite}.png" alt=""><div><b>${esc(ad(a).name)}</b>　Lv ${a.level}<br><small>下一級還需 ${next} 經驗值</small></div></div>
    <table>${['hp', 'mp', 'atk', 'def', 'mag', 'spd'].map(row).join('')}</table>
    <div class="eq">${['weapon', 'armor', 'acc'].map(s => `<div>${SLOTN[s]}：${a.equip[s] ? esc(D.items[a.equip[s]].name) : '—'}</div>`).join('')}</div>
    <div class="sk">${skillsOf(a).map(id => `<span>${esc(D.skills[id].name)}</span>`).join('')}</div></div>`;
}
function questPanel() {
  const qs = Object.entries(S.quests).map(([id, st]) => `<li class="${st}"><b>${st === 'done' ? '✔' : '・'} ${esc(D.quests[id].name)}</b><br><small>${esc(D.quests[id].desc)}</small></li>`).join('');
  return `<div class="quest"><div class="goal"><small>目前目標</small><br>${esc(S.goal || '—')}</div><ul class="ql">${qs || '<li><small>還沒有接到支線任務。</small></li>'}</ul></div>`;
}
function postNo(id, i) { return 100000 + hashId(id).charCodeAt(0) * 731 + i * 37; }
function renderBoard() {
  const b = S.board, bd = D.boards[b.id], posts = boardPosts(b.id);
  const day = ['日', '一', '二', '三', '四', '五', '六'];
  const html = posts.slice(b.top).map((p, k) => {
    const no = postNo(b.id, p.i);
    const d = new Date(2026, 10, 1 + (p.i % 24), (p.i * 7) % 24, (p.i * 13) % 60);
    const date = `${d.getFullYear() % 100}/${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}(${day[d.getDay()]})${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    const body = p.text.replace(/\{no:(\d+)\}/g, (_, n) => postNo(b.id, +n)).split('\n').map(l => l.startsWith('>') ? `<span class="q">${esc(l)}</span>` : esc(l)).join('<br>');
    const head = p.owner
      ? `<b class="ttl">無標題</b> 名稱: <b class="own">島主？</b> ${date} ID:${'?'.repeat(8)} No.${no}`
      : `<b class="ttl">無標題</b> 名稱: <b class="nm">無名氏</b> ${date} ID:${hashId(b.id + p.i)} No.${no}`;
    return `<div class="post ${p.i === 0 ? 'op' : ''} ${p.owner ? 'owner' : ''}"><div class="ph">${head}</div><div class="pb">${body}</div></div>`;
  }).join('');
  return `<div class="board"><div class="bh">${esc(bd.title)}<span>↑↓ 捲動　Enter／Esc 關閉　（${b.top + 1}/${posts.length}）</span></div><div class="bl">${html}</div></div>`;
}
function renderOverlays() {
  let h = '';
  const ms = S.menus;
  if (S.board) h += renderBoard();
  if (S.card) h += `<div class="card"><div class="ch">無標題　名稱：無名氏　No.${hashId(S.card.title).length * 1000 + S.card.title.length}</div><div class="cl">${esc(S.card.label)}</div><div class="ct">${esc(S.card.title)}</div><div class="cs">${esc(S.card.sub || '')}</div></div>`;
  if (S.mode === 'battle') {
    const bm = ms.filter(m => /battle/.test(m.cls || ''));
    if (bm.length) h += `<div class="bmenu">${menuHtml(bm[bm.length - 1], true)}</div>`;
    if (S.battle && S.battle.done) h += `<div class="okp">Enter ▼</div>`;
  }
  const others = ms.filter(m => !/battle/.test(m.cls || ''));
  if (others.length) {
    const centered = others[others.length - 1].cls === 'center' || /title/.test(others[0].cls || '');
    if (centered || others[0].cls === 'choice' || others[0].cls === 'shop') {
      h += `<div class="mwrap ${centered ? 'centered' : ''}">`;
      others.forEach((m, i) => { h += menuHtml(m, i === others.length - 1); });
    } else {
      h += '<div class="mwrap cascade">';
      if (others[0].cls === 'main') h += partySummary();
      others.forEach((m, i) => { h += `<div class="casc" style="left:${14 + i * 112}px;top:${14 + i * 26}px">${menuHtml(m, i === others.length - 1)}</div>`; });
    }
    h += '</div>';
  }
  if (S.dialog) {
    const d = S.dialog;
    const hand = !!d.speaker && (D.hand || []).includes(d.speaker);
    h += `<div class="dialog ${d.speaker ? '' : 'nar'} ${hand ? 'hand' : ''}">${d.speaker ? `<div class="spk">${esc(d.speaker)}</div>` : ''}<div class="dt">${hand ? handText(d.text) : esc(d.text)}</div>${ms.length ? '' : '<div class="nx">▼</div>'}</div>`;
  }
  if (S.auto && (S.mode === 'map' || S.mode === 'battle')) h += `<div class="autob" data-autooff title="點一下關閉全自動模式"><b>AUTO</b>${S.autoNote ? `<span>${esc(S.autoNote)}</span>` : ''}</div>`;
  if (S.toasts.length) h += `<div class="toasts">${S.toasts.map(t => `<div>${esc(t.text)}</div>`).join('')}</div>`;
  return h;
}
/* 手寫字：每個字隨機歪一點、大小不一（同一句話每次都歪得一樣） */
function handText(text) {
  let h = 2166136261;
  for (const ch of text) { h ^= ch.codePointAt(0); h = Math.imul(h, 16777619); }
  return [...text].map((ch, i) => {
    const r = Math.imul(h ^ (i * 2654435761), 2246822519) >>> 0;
    const rot = (r % 21) - 10, dy = ((r >>> 5) % 9) - 4, sc = 0.8 + ((r >>> 9) % 8) * 0.05;
    return `<span style="transform:translateY(${dy}px) rotate(${rot}deg) scale(${sc.toFixed(2)})">${esc(ch)}</span>`;
  }).join('');
}
function partySummary() {
  const t = S.playTime;
  return `<div class="psum">${S.party.map(a => `<div class="ps"><img src="img/${ad(a).sprite}.png" alt=""><div><b>${esc(ad(a).name)}</b> Lv ${a.level}<br>HP ${a.hp}/${maxHp(a)}　MP ${a.mp}/${maxMp(a)}</div></div>`).join('')}
    <div class="ps-f"><span>${S.gold} K 幣${S.easy ? '<small class="easy">簡單</small>' : ''}</span><span>${Math.floor(t / 3600)}:${String(Math.floor(t / 60) % 60).padStart(2, '0')}</span></div><div class="ps-g">${esc(S.goal || '')}</div></div>`;
}

/* ================================================================ 輸入 */
const KEYS = {
  ArrowUp: 'up', w: 'up', W: 'up', ArrowDown: 'down', s: 'down', S: 'down', ArrowLeft: 'left', a: 'left', A: 'left',
  ArrowRight: 'right', d: 'right', D: 'right', Enter: 'ok', ' ': 'ok', z: 'ok', Z: 'ok', Escape: 'back', x: 'back', X: 'back',
  m: 'menu', M: 'menu', Backspace: 'back',
};
const DIRK = { up: 'U', down: 'D', left: 'L', right: 'R' };
function press(btn, repeat) {
  if (!S || !D) return;
  if ((btn === 'ok' || btn === 'back' || btn === 'menu') && repeat) return;
  if (S.card) { if (btn === 'ok') S.card.res(); return; }
  if (S.board) { boardKey(btn); return; }
  if (S.dialog && !S.menus.length) { if (btn === 'ok') advanceDialog(); return; }
  if (S.waitOk && btn === 'ok') { const r = S.waitOk; S.waitOk = null; r(); return; }
  if (S.menus.length) {
    if (btn === 'left' || btn === 'right') return;
    menuKey(btn);
    return;
  }
  if (S.mode !== 'map' || S.busy) return;
  if (S.auto) { if (btn === 'back' || btn === 'menu') openMainMenu(); return; }
  if (DIRK[btn]) tryMove(DIRK[btn]);
  else if (btn === 'ok') interact();
  else if (btn === 'back' || btn === 'menu') openMainMenu();
}

/* ---------------------------------------------------------------- 按住連續輸入
   鍵盤方向鍵與畫面上的十字鍵共用：按下立刻動一次，按住不放就持續觸發。
   在地圖上每 140 毫秒走一格；在選單裡先停 280 毫秒，之後每 90 毫秒移動一次游標。 */
const held = [];   // { src, btn }，最後一個是目前生效的方向
let holdTimer = 0;
function holdMenuish() { return !!(S && (S.menus.length || S.board || S.mode !== 'map')); }
function holdLoop(first) {
  clearTimeout(holdTimer);
  if (!held.length) return;
  if (!first) press(held[held.length - 1].btn, true);
  holdTimer = setTimeout(() => holdLoop(false), holdMenuish() ? (first ? 280 : 90) : 140);
}
function holdStart(src, btn) {
  const i = held.findIndex(h => h.src === src);
  if (i >= 0) held.splice(i, 1);
  held.push({ src, btn });
  press(btn, false);
  holdLoop(true);
  holdMark();
}
function holdMove(src, btn) {
  const h = held.find(h => h.src === src);
  if (!h || h.btn === btn) return;
  h.btn = btn;
  if (held[held.length - 1] === h) { press(btn, false); holdLoop(true); }
  holdMark();
}
function holdEnd(src) {
  const i = held.findIndex(h => h.src === src);
  if (i < 0) return;
  held.splice(i, 1);
  if (!held.length) clearTimeout(holdTimer);
  holdMark();
}
function holdClear() { held.length = 0; clearTimeout(holdTimer); holdMark(); }
function holdMark() {
  const cur = held.length ? held[held.length - 1].btn : '';
  document.querySelectorAll('.dpad [data-btn]').forEach(b => b.classList.toggle('on', b.dataset.btn === cur));
}

/* ================================================================ 啟動 */
async function boot() {
  const res = await fetch('data/game.json');
  D = await res.json();
  bspeed = meta().speed || 0;
  autoSpeed = meta().autoSpeed || 0;
  scanToggles();
  S = freshState();
  // 先載入主角的所有方向與走路圖，換圖時才不會閃一下
  for (const n of new Set(Object.values(HERO_FRAMES).flat())) new Image().src = `img/${n}.png`;
  toTitle();
  window.addEventListener('keydown', e => {
    if ((e.key === 'f' || e.key === 'F') && !e.repeat && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); toggleFs(); return; }
    const b = KEYS[e.key];
    if (!b) return;
    e.preventDefault();
    // 方向鍵：自己控制按住時的連續輸入，不依賴系統的按鍵重複（避免第一步後卡一下）
    if (DIRK[b]) { if (!held.some(h => h.src === 'k' + e.code)) holdStart('k' + e.code, b); return; }
    press(b, e.repeat);
  });
  window.addEventListener('keyup', e => holdEnd('k' + e.code));
  window.addEventListener('blur', holdClear);
  document.addEventListener('visibilitychange', () => { if (document.hidden) holdClear(); });
  document.querySelectorAll('[data-btn]').forEach(btn => {
    const b = btn.dataset.btn;
    if (!(DIRK[b] && btn.closest('.dpad'))) { btn.addEventListener('click', () => press(b, false)); return; }
    // 畫面上的十字鍵：按住持續移動，手指滑到別的方向也會跟著轉向
    btn.addEventListener('pointerdown', e => {
      e.preventDefault();
      try { btn.setPointerCapture(e.pointerId); } catch (_) { /* 舊瀏覽器沒有也能用 */ }
      holdStart('p' + e.pointerId, b);
    });
    btn.addEventListener('pointermove', e => {
      const t = document.elementFromPoint(e.clientX, e.clientY);
      const nb = t && t.closest('.dpad [data-btn]');
      if (nb) holdMove('p' + e.pointerId, nb.dataset.btn);
    });
    for (const ev of ['pointerup', 'pointercancel', 'lostpointercapture']) btn.addEventListener(ev, e => holdEnd('p' + e.pointerId));
    btn.addEventListener('contextmenu', e => e.preventDefault());
  });
  el('ov').addEventListener('click', e => {
    if (e.target.closest('[data-autooff]')) { setAuto(false); return; }
    const li = e.target.closest('li[data-i]');
    if (li && S.menus.length) {
      const m = S.menus[S.menus.length - 1];
      const i = +li.dataset.i;
      if (m.cursor !== i) { m.cursor = i; if (m.onMove) m.onMove(i); render(); return; }
      press('ok', false);
      return;
    }
    if (S.card) { press('ok', false); return; }
    if (S.board) { const bl = e.target.closest('.board'); if (!bl || e.target.closest('.bh')) press('back', false); else press('down', false); return; }
    if (S.dialog || (S.waitOk)) press('ok', false);
  });
  setInterval(() => { if (S && (S.mode === 'map' || S.mode === 'battle') && !document.hidden) S.playTime++; }, 1000);
  setInterval(monTick, 100);
  setInterval(autoTick, 40);
  window.KDBG = {
    get S() { return S; }, get D() { return D; },
    warp: (m, x, y) => { S.menus.length = 0; S.dialog = null; teleport(m, x, y, 'D'); S.pendingAuto = false; built = null; render(); },
    closeUI: () => { S.menus.length = 0; S.dialog = null; render(); },
    flag: f => { S.flags[f] = true; render(); },
    give: (id, n = 1) => addItem(id, n),
    level: L => { for (const a of S.party) { a.level = L; a.exp = expFor(L); a.hp = maxHp(a); a.mp = maxMp(a); } render(); },
    join: id => { S.party.push(makeActor(id, S.party[0].level)); render(); },
    battle: t => runBusy([['battle', t, {}]]),
    run: sc => runBusy(sc),
    speed: x => { SPEED = x; },
    god: on => { GOD = !!on; },
    mons: on => { MONS_ON = !!on; if (!on) { S.mons = []; render(); } },
    auto: on => setAuto(!!on),
    autoTargets: () => autoTargets().map(t => `${t.map}:${t.ent ? t.ent.id : '(進入)'}:${t.prio}:${t.label}`),
  };
}

/* 依視窗寬度縮放遊戲畫面 */
function fitStage() {
  const stage = document.getElementById('stage'), frame = document.getElementById('frame');
  if (!stage || !frame) return;
  // 全螢幕時放大到剛好塞滿整個螢幕（保持比例）；平常只依寬度縮小
  const k = document.body.classList.contains('fs')
    ? Math.min(window.innerWidth / 774, window.innerHeight / 582)
    : Math.min(1, (document.documentElement.clientWidth - 16) / 774);
  frame.style.transform = `scale(${k})`;
  stage.style.width = 774 * k + 'px';
  stage.style.height = 582 * k + 'px';
}
/* ---------------------------------------------------------------- 全螢幕
   支援全螢幕 API 的瀏覽器（電腦、Android、iPad）會真的進入全螢幕；
   不支援的（iPhone 的 Safari）就把遊戲畫面放大到填滿可見範圍。 */
let nativeFs = false;
function fsActive() { return document.body.classList.contains('fs'); }
function nativeFsEl() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
function setFs(on) {
  document.body.classList.toggle('fs', on);
  fitStage();
  if (on && S && D) toast(matchMedia('(hover:hover) and (pointer:fine)').matches ? '全螢幕：按 F 或右上角的按鈕離開' : '全螢幕：按右上角的按鈕離開');
}
function toggleFs() {
  if (!fsActive()) {
    setFs(true);
    const el = document.documentElement;
    try {
      const r = el.requestFullscreen ? el.requestFullscreen({ navigationUI: 'hide' }) : el.webkitRequestFullscreen ? el.webkitRequestFullscreen() : null;
      if (r && r.catch) r.catch(() => { /* 被拒絕時維持網頁內的全螢幕 */ });
    } catch (_) { /* 不支援時維持網頁內的全螢幕 */ }
  } else {
    setFs(false);
    if (nativeFsEl()) { try { (document.exitFullscreen || document.webkitExitFullscreen).call(document); } catch (_) { /* 已經離開 */ } }
  }
}
function onFsChange() {
  if (nativeFsEl()) nativeFs = true;
  else if (nativeFs) { nativeFs = false; if (fsActive()) setFs(false); }  // 用 Esc 或返回鍵離開了瀏覽器全螢幕
  fitStage();
}
if (typeof window !== 'undefined') {
  window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-fs]').forEach(b => b.addEventListener('click', toggleFs));
    document.addEventListener('fullscreenchange', onFsChange);
    document.addEventListener('webkitfullscreenchange', onFsChange);
    window.addEventListener('resize', fitStage);
    fitStage();
    new ResizeObserver(fitStage).observe(document.documentElement);
    boot();
  });
}
if (typeof module !== 'undefined') module.exports = { expFor, setData: d => { D = d; } };
