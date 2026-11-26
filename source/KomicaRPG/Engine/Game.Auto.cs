using System.Text;
using System.Text.Json;

namespace KomicaRPG.Engine;

/// <summary>預演用的狀態複本（全自動模式）。</summary>
public class SimState
{
    public Dictionary<string, bool> Flags = new();
    public Dictionary<string, int> Inv = new();
    public int Karma, Gold;
    public Dictionary<string, string> Quests = new();
    public List<string> Party = new();

    public SimState Clone() => new()
    {
        Flags = new(Flags), Inv = new(Inv), Karma = Karma, Gold = Gold, Quests = new(Quests), Party = new(Party),
    };
}

/// <summary>預演的結果：這段腳本會做什麼。</summary>
class SimAcc
{
    public int Prod, Karma;
    public readonly StringBuilder Sig = new();
    public string Who = "";
    public readonly List<string> Shops = new();
    public string? Warp, Ending, Battle;
}

class AutoLeg
{
    public string Map = "";
    public List<string> Path = new();
    public string Act = "walk";   // walk / talk / ferry / travel
    public string Dir = "D";
    public string? Ent, To;
    public TravelDef? Tp;
}

class AutoPlanState
{
    public List<AutoLeg> Legs = new();
    public string Label = "", Key = "", TKey = "";
}

class AutoTarget
{
    public string Map = "", Key = "", Label = "";
    public EntDef? Ent;
    public int Prio;
}

class AutoNode
{
    public string Map = "";
    public int X, Y, Cost;
    public List<AutoLeg> Legs = new();
}

/// <summary>地圖內的最短路徑表。</summary>
class Bfs
{
    public int W, H;
    public int[] Dist = Array.Empty<int>(), Prev = Array.Empty<int>();
    public int DistAt(int x, int y) => x < 0 || y < 0 || x >= W || y >= H ? -1 : Dist[y * W + x];

    public List<string> PathTo(int x, int y)
    {
        var outp = new List<string>();
        var c = y * W + x;
        while (Prev[c] >= 0)
        {
            var p = Prev[c];
            var d = c - p;
            outp.Add(d == 1 ? "R" : d == -1 ? "L" : d == W ? "D" : "U");
            c = p;
        }
        outp.Reverse();
        return outp;
    }
}

/// <summary>
/// 全自動模式：開啟後由電腦代替玩家走路、對話、選擇、戰鬥、買裝備、換裝備，一路玩到結局。
/// 怎麼決定下一步：對每個看得到的人「預演」他的對話腳本（在狀態的複本上跑一次，不會真的改到遊戲）。
/// 會讓劇情前進的人要去找；台詞跟上次聽過的不一樣就是「有新對話」，在同一張地圖裡順便聊一下；結局最後才去。
/// 跨地圖的路線用傳送點、會載人的 NPC（船夫）、跳串一起算最短的走法。和網頁版 game.js 的邏輯相同。
/// </summary>
public partial class Game
{
    static readonly double[] AutoSpeeds = { 1, 0.55, 0.3 };
    static readonly string[] AutoSpeedNames = { "普通", "快", "超快" };
    static readonly string[] Dirs = { "U", "D", "L", "R" };
    int autoSpeed;
    long autoNext;
    AutoPlanState? autoPlan;
    bool autoBusy, autoDone;
    (string Map, string Ent, string Key, string Before)? autoTalk;
    string? autoIntent;
    string autoInvKey = "";
    readonly Dictionary<string, string> autoSkip = new();
    int autoFails;
    DialogState? autoDlg;
    HashSet<string>? toggles;
    string? goalMap, shopId;
    object? autoChoice;   // List<JsonElement>（選項）或 int（旅館價錢）

    public bool Auto { get; private set; }
    public Dictionary<string, string> AutoSeen { get; private set; } = new();
    public string AutoNote { get; private set; } = "";

    double AutoDelay(double ms) => ms * AutoSpeeds[autoSpeed];

    void ResetAuto()
    {
        Auto = false; AutoSeen = new(); AutoNote = ""; goalMap = null; shopId = null; autoChoice = null;
        autoPlan = null; autoTalk = null; autoIntent = null; autoSkip.Clear(); autoFails = 0; autoDone = false; autoDlg = null;
    }

    public void SetAuto(bool on)
    {
        Auto = on;
        autoPlan = null; autoTalk = null; autoIntent = null; autoSkip.Clear(); autoFails = 0;
        if (on)
        {
            Easy = true;   // 全自動一律用簡單難度
            ShowToast("全自動模式開啟（難度：簡單）");
        }
        else
        {
            AutoNote = "";
            ShowToast("全自動模式關閉，換你自己玩了");
        }
        Render();
    }

    // 會被 unflag 的旗標（例如外來種的男／女切換），不算劇情前進
    HashSet<string> Toggles
    {
        get
        {
            if (toggles != null) return toggles;
            var set = new HashSet<string>();
            void Walk(JsonElement? sc)
            {
                if (sc is not JsonElement s || s.ValueKind != JsonValueKind.Array) return;
                foreach (var c in s.EnumerateArray())
                {
                    var op = c[0].GetString();
                    if (op == "unflag") set.Add(Str(c, 1));
                    else if (op == "if") { Walk(c[2]); if (c.GetArrayLength() > 3) Walk(c[3]); }
                    else if (op == "choice") foreach (var o in Opts(c)) Walk(o[1]);
                }
            }
            foreach (var m in D.Maps.Values)
            {
                foreach (var e in m.Ents) Walk(e.Script);
                foreach (var a in m.Auto) Walk(a.Script);
            }
            foreach (var c in D.Calls.Values) Walk(c);
            toggles = set;
            return set;
        }
    }

    static List<JsonElement> Opts(JsonElement c)
    {
        var list = new List<JsonElement>();
        for (var i = 1; i < c.GetArrayLength(); i++) list.Add(c[i]);
        return list;
    }

    // ---------------------------------------------------------------- 預演
    SimState Snapshot() => new()
    {
        Flags = new(Flags), Inv = new(Inv), Karma = Karma, Gold = Gold, Quests = new(Quests), Party = Party.Select(a => a.Id).ToList(),
    };

    /// <summary>回傳 false 表示腳本在這裡結束（結局）。</summary>
    bool SimRun(JsonElement? script, SimState st, SimAcc acc, int depth = 0)
    {
        if (depth > 30 || script is not JsonElement sc || sc.ValueKind != JsonValueKind.Array) return true;
        foreach (var c in sc.EnumerateArray())
            if (!SimExec(c, st, acc, depth)) return false;
        return true;
    }

    bool SimExec(JsonElement c, SimState st, SimAcc acc, int depth)
    {
        switch (c[0].GetString())
        {
            case "say":
            {
                var sp = Str(c, 1);
                acc.Sig.Append(sp).Append('|');
                for (var i = 2; i < c.GetArrayLength(); i++) { if (i > 2) acc.Sig.Append('/'); acc.Sig.Append(Str(c, i)); }
                acc.Sig.Append(';');
                if (acc.Who.Length == 0 && sp.Length > 0 && sp != "無名氏") acc.Who = sp;
                break;
            }
            case "if":
                if (Cond(Str(c, 1), st)) return SimRun(c[2], st, acc, depth + 1);
                return c.GetArrayLength() > 3 ? SimRun(c[3], st, acc, depth + 1) : true;
            case "choice":
            {
                var opts = Opts(c);
                var i = AutoPick(opts, st);
                acc.Sig.Append('?').Append(i);
                return SimRun(opts[i][1], st, acc, depth + 1);
            }
            case "flag":
            {
                var f = Str(c, 1);
                if (!st.Flags.GetValueOrDefault(f)) { st.Flags[f] = true; if (!Toggles.Contains(f)) acc.Prod++; }
                break;
            }
            case "unflag": st.Flags.Remove(Str(c, 1)); break;
            case "give": { var id = Str(c, 1); st.Inv[id] = st.Inv.GetValueOrDefault(id) + Int(c, 2, 1); acc.Prod++; break; }
            case "take":
            {
                var id = Str(c, 1);
                if (st.Inv.GetValueOrDefault(id) > 0) { st.Inv[id] = Math.Max(0, st.Inv[id] - Int(c, 2, 1)); acc.Prod++; }
                break;
            }
            case "gold": st.Gold += Int(c, 1, 0); acc.Prod++; break;
            case "quest":
            {
                var id = Str(c, 1);
                var s = Str(c, 2);
                var cur = st.Quests.GetValueOrDefault(id);
                if (cur != "done" && cur != s) { st.Quests[id] = s; acc.Prod++; }
                break;
            }
            case "karma": { var n = Int(c, 1, 0); st.Karma += n; acc.Karma += n; break; }
            case "battle": acc.Battle = Str(c, 1); acc.Prod++; break;
            case "join": { var id = Str(c, 1); if (!st.Party.Contains(id)) { st.Party.Add(id); acc.Prod++; } break; }
            case "warp": acc.Warp = Str(c, 1); if (!Visited.GetValueOrDefault(acc.Warp)) acc.Prod++; break;
            case "ending": acc.Ending = Str(c, 1); acc.Prod++; return false;
            case "call": return SimRun(D.Calls[Str(c, 1)], st, acc, depth + 1);
            case "shop": acc.Shops.Add(Str(c, 1)); break;
            case "board": acc.Sig.Append('B').Append(Str(c, 1)).Append(':').Append(BoardPosts(Str(c, 1)).Count).Append(';'); break;
        }
        return true;
    }

    /// <summary>選項怎麼選：善行最優先，再來是會讓劇情前進的；不逛照燒攤、不坐船回頭（除非正要去那裡）。</summary>
    int AutoPick(List<JsonElement> opts, SimState st)
    {
        var best = 0;
        var bestScore = double.NegativeInfinity;
        for (var i = 0; i < opts.Count; i++)
        {
            var a = new SimAcc();
            SimRun(opts[i][1], st.Clone(), a, 1);
            double sc = a.Karma * 10 + a.Prod;
            if (a.Shops.Count > 0) sc -= 0.5;
            if (a.Warp != null) sc += autoIntent == a.Warp ? 100 : Visited.GetValueOrDefault(a.Warp) ? -50 : 0;
            if (a.Ending == "real") sc -= 1;
            if (sc > bestScore) { bestScore = sc; best = i; }
        }
        return best;
    }

    SimAcc EntInfo(string mapId, EntDef e)
    {
        var a = new SimAcc();
        if (e.Chest != null)
        {
            a.Prod = Flags.GetValueOrDefault($"chest:{mapId}:{e.Id}") ? 0 : 1;
            a.Who = "寶箱";
            return a;
        }
        SimRun(e.Script, Snapshot(), a);
        return a;
    }

    /// <summary>會載人去別的地方的 NPC（船夫）：腳本裡只有對話和傳送。</summary>
    (string Map, int X, int Y)? FerryOf(EntDef e)
    {
        (string, int, int)? found = null;
        var bad = false;
        void Walk(JsonElement? sc)
        {
            if (sc is not JsonElement s || s.ValueKind != JsonValueKind.Array) return;
            foreach (var c in s.EnumerateArray())
            {
                if (bad) return;
                var op = c[0].GetString();
                if (op == "warp") found ??= (Str(c, 1), Int(c, 2, 0), Int(c, 3, 0));
                else if (op == "if") Walk(Cond(Str(c, 1)) ? c[2] : c.GetArrayLength() > 3 ? c[3] : (JsonElement?)null);
                else if (op == "choice") foreach (var o in Opts(c)) Walk(o[1]);
                else if (op is "battle" or "ending" or "join" or "give" or "flag" or "quest") bad = true;
            }
        }
        Walk(e.Script);
        return bad ? null : found;
    }

    // ---------------------------------------------------------------- 裝備
    bool IsCaster(Actor a)
    {
        var d = Ad(a);
        return d.Growth.GetValueOrDefault("mag") > d.Growth.GetValueOrDefault("atk");
    }

    double EquipScore(Actor a, string? id)
    {
        if (id == null) return 0;
        var it = D.Items[id];
        var c = IsCaster(a);
        var w = new Dictionary<string, double>
        {
            ["atk"] = c ? 0.4 : 2, ["mag"] = c ? 2 : 0.3, ["def"] = 1.2, ["spd"] = 0.8, ["hp"] = 0.25, ["mp"] = c ? 0.3 : 0.1,
        };
        double s = 0;
        if (it.Stats != null)
            foreach (var (k, v) in it.Stats) s += w.GetValueOrDefault(k) * v;
        return s + (it.Immune?.Count ?? 0) * 6;
    }

    void AutoEquipAll()
    {
        foreach (var slot in Slots)
            foreach (var a in Party)
            {
                var cur = a.Equip.GetValueOrDefault(slot);
                var best = cur;
                var bs = EquipScore(a, cur);
                foreach (var id in InvList((it, iid) => SlotOf(it) == slot && CanEquip(a, iid)))
                {
                    var sc = EquipScore(a, id);
                    if (sc > bs + 0.01) { bs = sc; best = id; }
                }
                if (best == null || best == cur) continue;
                RemoveItem(best);
                if (cur != null) AddItem(cur);
                a.Equip[slot] = best;
                a.Hp = Math.Min(a.Hp, MaxHp(a));
                a.Mp = Math.Min(a.Mp, MaxMp(a));
                ShowToast($"{Ad(a).Name}換上了【{D.Items[best].Name}】");
            }
    }

    /// <summary>這間店有沒有買得起、又比現在好的裝備？回傳要買的清單。</summary>
    List<string> ShopBuys(string shop)
    {
        var list = D.Shops.GetValueOrDefault(shop)?.Where(id => SlotOf(D.Items[id]) != null).ToList() ?? new List<string>();
        var buys = new List<string>();
        if (list.Count == 0) return buys;
        var pool = new Dictionary<string, int>(Inv);
        var g = Gold;
        foreach (var slot in Slots)
            foreach (var a in Party)
            {
                var have = a.Equip.GetValueOrDefault(slot);
                var hs = EquipScore(a, have);
                foreach (var id in pool.Keys.ToList())
                    if (pool[id] > 0 && SlotOf(D.Items[id]) == slot && CanEquip(a, id) && EquipScore(a, id) > hs) { have = id; hs = EquipScore(a, id); }
                if (have != null && have != a.Equip.GetValueOrDefault(slot)) pool[have]--;   // 背包裡的備品先留給這個人
                string? best = null;
                var bs = hs;
                foreach (var id in list)
                {
                    if (SlotOf(D.Items[id]) != slot || !CanEquip(a, id) || D.Items[id].Price > g) continue;
                    var sc = EquipScore(a, id);
                    if (sc > bs + 0.01) { bs = sc; best = id; }
                }
                if (best != null) { buys.Add(best); g -= D.Items[best].Price; }
            }
        return buys;
    }

    // ---------------------------------------------------------------- 路線
    bool WalkM(MapDef m, int x, int y) => y >= 0 && y < m.H && x >= 0 && x < m.W && D.TileMap[m.Rows[y][x]].Walk;

    Bfs BfsMap(string mapId, int sx, int sy)
    {
        var m = D.Maps[mapId];
        int W = m.W, H = m.H;
        var block = new HashSet<int>(m.Ents.Where(e => Cond(e.Show)).Select(e => e.Y * W + e.X));
        var warps = new HashSet<int>(m.WarpList.Select(w => w.Y * W + w.X));
        var b = new Bfs { W = W, H = H, Dist = Enumerable.Repeat(-1, W * H).ToArray(), Prev = Enumerable.Repeat(-1, W * H).ToArray() };
        var q = new List<int> { sy * W + sx };
        b.Dist[q[0]] = 0;
        for (var h = 0; h < q.Count; h++)
        {
            var c = q[h];
            int x = c % W, y = c / W;
            if (h > 0 && warps.Contains(c)) continue;   // 踩上傳送點就會被傳走，不能再往前
            foreach (var d in Dirs)
            {
                var (dx, dy) = Step(d);
                int nx = x + dx, ny = y + dy, n = ny * W + nx;
                if (!WalkM(m, nx, ny) || block.Contains(n) || b.Dist[n] >= 0) continue;
                b.Dist[n] = b.Dist[c] + 1;
                b.Prev[n] = c;
                q.Add(n);
            }
        }
        return b;
    }

    /// <summary>站在哪裡可以跟這個人說話：正前方，或隔著櫃台。</summary>
    (int D, int X, int Y, string Dir, List<string> Path)? StandFor(Bfs bfs, string mapId, EntDef e)
    {
        var m = D.Maps[mapId];
        (int D, int X, int Y, string Dir)? best = null;
        foreach (var dir in Dirs)
        {
            var (dx, dy) = Step(dir);
            var cands = new List<(int, int)> { (e.X - dx, e.Y - dy) };
            int cx = e.X - dx, cy = e.Y - dy;
            if (cy >= 0 && cy < m.H && cx >= 0 && cx < m.W && m.Rows[cy][cx] == 'u') cands.Add((e.X - 2 * dx, e.Y - 2 * dy));
            foreach (var (x, y) in cands)
            {
                var d = bfs.DistAt(x, y);
                if (d < 0 || m.WarpList.Any(w => w.X == x && w.Y == y)) continue;
                if (best == null || d < best.Value.D) best = (d, x, y, dir);
            }
        }
        if (best is not { } bb) return null;
        return (bb.D, bb.X, bb.Y, bb.Dir, bfs.PathTo(bb.X, bb.Y));
    }

    /// <summary>目前目標提到的地圖（加上設定目標時所在的地圖）：主線要往那裡走。</summary>
    HashSet<string> GoalMaps()
    {
        var set = new HashSet<string>();
        if (goalMap != null) set.Add(goalMap);
        foreach (var (mid, m) in D.Maps)
        {
            var baseName = m.Name.Split(' ')[0];
            if (baseName.EndsWith("外圍") || baseName.EndsWith("內部")) baseName = baseName[..^2];
            if (Goal.Contains(m.Name) || Goal.Contains(baseName)) set.Add(mid);
        }
        return set;
    }

    string AutoStateKey() => string.Join("|", MapId, Flags.Count, JsonSerializer.Serialize(Inv), JsonSerializer.Serialize(Quests),
        Party.Count, AutoSeen.Count, Gold >> 6);

    /// <summary>
    /// 目標的優先順序（數字小的先做）：0 這張地圖上的事　1 主線（目前目標提到的地圖、頭上有「！」的人）
    /// 2 其他地圖的支線與寶箱　3 不在目前目標裡的魔王戰（免得跳過劇情先打掉）　4 結局
    /// </summary>
    List<AutoTarget> AutoTargets()
    {
        var outp = new List<AutoTarget>();
        var gm = GoalMaps();
        var sk = AutoStateKey();
        foreach (var (mid, m) in D.Maps)
        {
            foreach (var e in m.Ents)
            {
                if (!Cond(e.Show)) continue;
                var key = mid + ":" + e.Id;
                if (autoSkip.GetValueOrDefault(key) == sk) continue;
                var a = EntInfo(mid, e);
                var here = mid == MapId;
                var main = gm.Contains(mid) || (e.Mark != null && Cond(e.Mark));
                var boss = a.Battle != null && D.Troops[a.Battle].Any(id => D.Enemies[id].Boss);
                if (a.Prod > 0)
                    outp.Add(new AutoTarget { Map = mid, Ent = e, Key = key, Label = a.Who, Prio = a.Ending != null ? 4 : boss && !main ? 3 : here ? 0 : main ? 1 : 2 });
                else if (here && a.Sig.Length > 0 && AutoSeen.GetValueOrDefault(key) != a.Sig.ToString())
                    outp.Add(new AutoTarget { Map = mid, Ent = e, Key = key, Label = a.Who, Prio = 0 });
                else if (here && a.Shops.Any(s => ShopBuys(s).Count > 0))
                    outp.Add(new AutoTarget { Map = mid, Ent = e, Key = key, Label = a.Who + "（買裝備）", Prio = 0 });
            }
            if (mid == MapId) continue;
            foreach (var au in m.Auto)
            {
                if (!Cond(au.Cond)) continue;
                var a = new SimAcc();
                SimRun(au.Script, Snapshot(), a);
                if (a.Prod > 0) { outp.Add(new AutoTarget { Map = mid, Key = mid + ":auto", Label = m.Name, Prio = gm.Contains(mid) ? 1 : 2 }); break; }
            }
        }
        return outp;
    }

    static List<AutoLeg> Append(List<AutoLeg> legs, AutoLeg leg) => legs.Concat(new[] { leg }).ToList();

    AutoPlanState? AutoComputePlan()
    {
        var targets = AutoTargets();
        if (targets.Count == 0) return null;
        var seen = new HashSet<string>();
        var pq = new List<AutoNode> { new() { Map = MapId, X = X, Y = Y } };
        AutoTarget? bestT = null;
        int bestCost = 0, bestPrio = int.MaxValue;
        List<AutoLeg>? bestLegs = null;
        bool Better(int prio, int cost) => bestT == null || prio < bestPrio || (prio == bestPrio && cost < bestCost);
        for (var n = 0; pq.Count > 0 && n < 120; n++)
        {
            pq.Sort((a, b) => a.Cost.CompareTo(b.Cost));
            var node = pq[0];
            pq.RemoveAt(0);
            if (!seen.Add(node.Map + ":" + node.X + ":" + node.Y)) continue;
            if (bestT != null && node.Cost > bestCost && bestPrio == 0) break;
            var bfs = BfsMap(node.Map, node.X, node.Y);
            foreach (var t in targets.Where(x => x.Map == node.Map))
            {
                if (t.Ent == null)
                {
                    if (node.Legs.Count > 0 && Better(t.Prio, node.Cost)) { bestT = t; bestPrio = t.Prio; bestCost = node.Cost; bestLegs = node.Legs; }
                    continue;
                }
                if (StandFor(bfs, node.Map, t.Ent) is not { } st) continue;
                var cost = node.Cost + st.D;
                if (!Better(t.Prio, cost)) continue;
                bestT = t; bestPrio = t.Prio; bestCost = cost;
                bestLegs = Append(node.Legs, new AutoLeg { Map = node.Map, Path = st.Path, Act = "talk", Dir = st.Dir, Ent = t.Ent.Id });
            }
            var m = D.Maps[node.Map];
            foreach (var w in m.WarpList)
            {
                var d = bfs.DistAt(w.X, w.Y);
                if (d > 0)
                    pq.Add(new AutoNode { Map = w.Map, X = w.Tx, Y = w.Ty, Cost = node.Cost + d + 2, Legs = Append(node.Legs, new AutoLeg { Map = node.Map, Path = bfs.PathTo(w.X, w.Y) }) });
            }
            foreach (var e in m.Ents)
            {
                if (!Cond(e.Show) || FerryOf(e) is not { } f || f.Map == node.Map) continue;
                if (StandFor(bfs, node.Map, e) is not { } st) continue;
                pq.Add(new AutoNode
                {
                    Map = f.Map, X = f.X, Y = f.Y, Cost = node.Cost + st.D + 6,
                    Legs = Append(node.Legs, new AutoLeg { Map = node.Map, Path = st.Path, Act = "ferry", Dir = st.Dir, Ent = e.Id, To = f.Map }),
                });
            }
            if (node.Legs.Count == 0 && !D.NoTravel.Contains(node.Map))
                foreach (var tp in D.Travel)
                    if (tp.Map != node.Map && Visited.GetValueOrDefault(tp.Map) && Cond(tp.Cond))
                        pq.Add(new AutoNode { Map = tp.Map, X = tp.X, Y = tp.Y, Cost = 40, Legs = new List<AutoLeg> { new() { Map = node.Map, Act = "travel", Tp = tp } } });
        }
        if (bestT == null || bestLegs == null) return null;
        var mapName = D.Maps[bestT.Map].Name;
        return new AutoPlanState
        {
            Legs = bestLegs.Select(l => new AutoLeg { Map = l.Map, Path = l.Path.ToList(), Act = l.Act, Dir = l.Dir, Ent = l.Ent, To = l.To, Tp = l.Tp }).ToList(),
            Label = bestT.Ent != null ? $"{mapName}：{(bestT.Label.Length > 0 ? bestT.Label : "看看")}" : $"前往{mapName}",
            Key = AutoStateKey(),
            TKey = bestT.Key,
        };
    }

    // ---------------------------------------------------------------- 戰鬥
    double EstHit(Unit u, Unit t, SkillDef sk)
    {
        var raw = sk.Kind == "mag"
            ? Math.Max(1, UStat(u, "mag") * (sk.Power == 0 ? 1 : sk.Power) + sk.Base - UStat(t, "def") * 0.25)
            : Math.Max(1, UStat(u, "atk") * (sk.Power == 0 ? 1 : sk.Power) - UStat(t, "def") * 0.5);
        var elem = sk.Elem ?? "phys";
        return raw * ElemMult(t, elem) * (t.St.ContainsKey("hidden") && elem != "holy" ? 0.25 : 1) * (t.St.ContainsKey("counter") && sk.Kind == "phys" ? 0.4 : 1);
    }

    static readonly SkillDef PlainAttack = new() { Kind = "phys", Power = 1 };

    /// <summary>全自動模式的戰鬥指令：補血、復活、打弱點、能一次打全部就打全部。</summary>
    async Task<BattleAction> AutoCommand(Actor a)
    {
        var b = Battle!;
        await BWait((int)AutoDelay(150));
        var foes = AliveEnemies();
        var allies = AliveParty();
        var dead = Party.Where(x => x.Hp <= 0).ToList();
        if (b.Gauge >= 100 && !b.ComboQueued)
        {
            b.ComboQueued = true;
            var hurtN = allies.Count(x => x.Hp < MaxHp(x) * 0.45) + dead.Count;
            return new BattleAction { Type = "combo", U = a, Combo = hurtN >= 2 ? "pushall" : "godthread" };
        }
        var sks = a.St.ContainsKey("silence") ? new List<(string Id, SkillDef Sk)>()
            : SkillsOf(a).Select(id => (Id: id, Sk: D.Skills[id])).Where(x => a.Mp >= x.Sk.Mp).ToList();
        var rev = sks.FirstOrDefault(x => x.Sk.Kind == "revive" || (x.Sk.Revive && x.Sk.Kind == "heal"));
        if (dead.Count > 0 && rev.Id != null) return new BattleAction { Type = "skill", U = a, Skill = rev.Id, T = dead[0] };
        var hurt = allies.Where(x => x.Hp < MaxHp(x) * 0.5).OrderBy(x => (double)x.Hp / MaxHp(x)).ToList();
        if (hurt.Count > 0)
        {
            var heals = sks.Where(x => x.Sk.Kind == "heal" && !x.Sk.Revive).ToList();
            var group = heals.Where(x => x.Sk.Target == "allies").OrderByDescending(x => x.Sk.Base).ToList();
            var single = heals.Where(x => x.Sk.Target == "ally").ToList();
            if (hurt.Count >= 2 && group.Count > 0) return new BattleAction { Type = "skill", U = a, Skill = group[0].Id };
            if (single.Count > 0) return new BattleAction { Type = "skill", U = a, Skill = single[0].Id, T = hurt[0] };
            if (group.Count > 0) return new BattleAction { Type = "skill", U = a, Skill = group[0].Id };
        }
        var bad = allies.Count(x => x.St.ContainsKey("silence") || x.St.ContainsKey("confuse") || x.St.ContainsKey("sleep"));
        var cure = sks.FirstOrDefault(x => x.Sk.Kind == "cure");
        if (bad >= 2 && cure.Id != null) return new BattleAction { Type = "skill", U = a, Skill = cure.Id };
        var target = foes.OrderBy(x => x.Hp).First();
        var best = new BattleAction { Type = "attack", U = a, T = target };
        var bestVal = EstHit(a, target, PlainAttack);
        foreach (var (id, sk) in sks)
        {
            if (sk.Kind is not ("phys" or "mag") || sk.Mp <= 0) continue;
            if (sk.Target == "enemy")
            {
                // 單體技能：挑這招打起來最痛的那一隻（打弱點）
                Unit bt = target;
                var bv = EstHit(a, target, sk);
                foreach (var t in foes)
                {
                    var v = EstHit(a, t, sk) * (t.Hp <= bv ? 1.2 : 1);
                    if (v > bv) { bv = v; bt = t; }
                }
                if (bv > bestVal * 1.2) { bestVal = bv; best = new BattleAction { Type = "skill", U = a, Skill = id, T = bt }; }
                continue;
            }
            double val;
            if (sk.Target == "enemies") val = foes.Sum(t => EstHit(a, t, sk));
            else if (sk.Target == "random3") val = EstHit(a, target, sk) * 3;
            else continue;
            if (val > bestVal * 1.2) { bestVal = val; best = new BattleAction { Type = "skill", U = a, Skill = id }; }
        }
        return best;
    }

    /// <summary>全自動模式：倒下的同伴自動復活，HP 與 MP 全滿。</summary>
    async Task AutoRevive()
    {
        foreach (var a in Party.Where(x => x.Hp <= 0).ToList())
        {
            a.Hp = MaxHp(a);
            a.Mp = MaxMp(a);
            a.St = new();
            ShowPopup(a, "AUTO", "heal");
            await Msg($"（全自動）{Ad(a).Name}被推回來了！HP 與 MP 全滿！", 500);
        }
    }

    // ---------------------------------------------------------------- 每 40 毫秒由畫面呼叫一次
    async Task AfterDelay(double ms, Action act)
    {
        await Task.Delay((int)ms);
        act();
    }

    public void AutoTick()
    {
        if (!Auto || autoBusy) return;
        var now = clock.ElapsedMilliseconds;
        if (now < autoNext) return;
        void Later(double ms) => autoNext = now + (long)AutoDelay(ms);
        var top = Menus.Count > 0 ? Menus[^1] : null;
        if (Menus.Count > 0 && Menus[0].Cls == "main") return;   // 玩家自己打開了選單：暫停
        if (Mode == "ending")
        {
            if (Dialog != null && Menus.Count == 0)
            {
                if (autoDlg != Dialog) { autoDlg = Dialog; Later(900 + Dialog.Text.Length * 130); }
                else { autoDlg = null; AdvanceDialog(); Later(40); }
            }
            else if (Ending is { Card: true } && !autoDone) { autoDone = true; AutoNote = "全破！"; ShowToast("全自動模式：全破了！"); }
            return;
        }
        if (Mode == "gameover") { if (top != null) { top.OnPick(SaveExists ? 0 : 1, new MenuItem()); Later(800); } return; }
        if (Mode == "title") return;
        if (Card != null) { CloseCard(Card); Later(300); return; }
        if (Board != null) { CloseBoard(); Later(300); return; }
        if (waitOk != null) { var w = waitOk; waitOk = null; w.TrySetResult(); Later(250); return; }
        if (top != null && top.Cls.Contains("battle"))
        {
            // 剛打開全自動時還停在戰鬥選單：交給「自動」
            var items = MenuItems(top);
            var i = items.FindIndex(it => it.Cmd == "auto");
            if (i >= 0) top.OnPick(i, items[i]); else if (top.OnBack != null) top.OnBack(); else PopMenu();
            Later(200);
            return;
        }
        if (top != null && top.Cls == "choice")
        {
            var i = 0;
            if (autoChoice is List<JsonElement> opts) i = AutoPick(opts, Snapshot());
            else if (autoChoice is int price) i = Gold >= price && Party.Any(a => a.Hp < MaxHp(a) || a.Mp < MaxMp(a)) ? 0 : 1;
            autoChoice = null;
            top.Cursor = i;
            Render();
            autoBusy = true;
            var pick = i;
            _ = AfterDelay(AutoDelay(450), () =>
            {
                autoBusy = false;
                if (Menus.Count > 0 && Menus[^1] == top) top.OnPick(pick, MenuItems(top)[pick]);
            });
            Later(500);
            return;
        }
        if (top != null && top.Cls.Contains("shop"))
        {
            if (top.Title == "商店" && shopId != null)
            {
                foreach (var id in ShopBuys(shopId))
                {
                    Gold -= D.Items[id].Price;
                    AddItem(id);
                    ShowToast($"買了【{D.Items[id].Name}】");
                }
                AutoEquipAll();
                if (top.OnBack != null) top.OnBack(); else PopMenu();
            }
            else PopMenu();
            Later(500);
            return;
        }
        if (Dialog != null && Menus.Count == 0)
        {
            // 每句話停留一段「讀得完」的時間再翻頁
            if (autoDlg != Dialog) { autoDlg = Dialog; Later(500 + Dialog.Text.Length * 110); return; }
            autoDlg = null;
            AdvanceDialog();
            Later(40);
            return;
        }
        if (Mode != "map" || Busy || Menus.Count > 0 || Dialog != null) return;

        // ---- 地圖上、可以自由行動 ----
        if (autoTalk is { } talk)
        {
            // 剛剛跟誰說完話：把現在聽得到的台詞記成「聽過了」
            var e0 = D.Maps.GetValueOrDefault(talk.Map)?.Ents.FirstOrDefault(x => x.Id == talk.Ent);
            if (e0 != null) AutoSeen[talk.Key] = EntInfo(talk.Map, e0).Sig.ToString();
            if (AutoStateKey() == talk.Before) autoSkip[talk.Key] = AutoStateKey();   // 說了也沒變化：先跳過
            autoTalk = null; autoIntent = null; autoPlan = null;
        }
        var ik = JsonSerializer.Serialize(Inv) + Party.Count;
        if (ik != autoInvKey) { autoInvKey = ik; AutoEquipAll(); }
        if (autoPlan == null || autoPlan.Key != AutoStateKey() || autoPlan.Legs.Count == 0 || autoPlan.Legs[0].Map != MapId)
        {
            autoPlan = AutoComputePlan();
            if (autoPlan == null)
            {
                AutoNote = "（四處看看……）";
                var dirs = Dirs.Where(d => { var (dx, dy) = Step(d); return Walkable(X + dx, Y + dy) && EntAt(X + dx, Y + dy) == null && !WarpAt(X + dx, Y + dy); }).ToList();
                if (dirs.Count > 0) MoveStep(dirs[R.Next(dirs.Count)]);
                Later(400);
                return;
            }
            AutoNote = autoPlan.Label;
        }
        var leg = autoPlan.Legs[0];
        if (leg.Path.Count > 0)
        {
            int fx = X, fy = Y;
            var r = MoveStep(leg.Path[0]);
            if (r == 1 && (X != fx || Y != fy || MapId != leg.Map))
            {
                leg.Path.RemoveAt(0);
                autoFails = 0;
                if (MapId != leg.Map) autoPlan.Legs.RemoveAt(0);
            }
            else if (r != 2 && ++autoFails > 3) { autoSkip[autoPlan.TKey] = AutoStateKey(); autoPlan = null; autoFails = 0; }
            Later(150);
            return;
        }
        if (leg.Act == "travel" && leg.Tp != null)
        {
            ShowToast("跳串：" + leg.Tp.Name);
            Teleport(leg.Tp.Map, leg.Tp.X, leg.Tp.Y, leg.Tp.Dir);
            _ = SaveGame();
            Render();
            _ = RunBusy(null);
            autoPlan = null;
            Later(500);
            return;
        }
        if (leg.Act is "talk" or "ferry")
        {
            Dir = leg.Dir;
            Render();
            var (dx, dy) = Step(leg.Dir);
            int tx = X + dx, ty = Y + dy;
            if (TileAt(tx, ty) == 'u') { tx += dx; ty += dy; }
            var e = EntAt(tx, ty);
            if (e == null || e.Id != leg.Ent) { autoSkip[autoPlan.TKey] = AutoStateKey(); autoPlan = null; Later(200); return; }
            autoTalk = (MapId, e.Id, MapId + ":" + e.Id, AutoStateKey());
            if (leg.Act == "ferry") autoIntent = leg.To;
            autoPlan.Legs.RemoveAt(0);
            autoBusy = true;
            _ = AfterDelay(AutoDelay(250), () => { autoBusy = false; Interact(); });
            Later(400);
            return;
        }
        autoPlan.Legs.RemoveAt(0);
        Later(100);
    }

    /// <summary>手寫字：每個字隨機歪一點、大小不一（同一句話每次都歪得一樣）。回傳 (字, style)。</summary>
    public static IEnumerable<(string Ch, string Style)> HandChars(string text)
    {
        uint h = 2166136261;
        foreach (var ch in text) { h ^= ch; h *= 16777619; }
        var i = 0;
        var e = System.Globalization.StringInfo.GetTextElementEnumerator(text);
        while (e.MoveNext())
        {
            var r = unchecked((h ^ (uint)(i * 2654435761u)) * 2246822519u);
            var rot = (int)(r % 21) - 10;
            var dy = (int)((r >> 5) % 9) - 4;
            var sc = 0.8 + ((r >> 9) % 8) * 0.05;
            yield return ((string)e.Current, $"transform:translateY({dy}px) rotate({rot}deg) scale({sc.ToString("0.00", System.Globalization.CultureInfo.InvariantCulture)})");
            i++;
        }
    }
}
