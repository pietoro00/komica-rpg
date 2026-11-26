using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace KomicaRPG.Engine;

/// <summary>
/// 遊戲引擎：狀態、數值、劇情腳本、地圖、選單、商店、存檔。
/// 戰鬥在 Game.Battle.cs。畫面（GameView.razor）只負責顯示和傳入按鍵。
/// </summary>
public partial class Game
{
    public const int T = 48, VW = 16, VH = 12;
    const string SaveKey = "komica_rpg_save_v1", MetaKey = "komica_rpg_meta_v1";

    static readonly JsonSerializerOptions SaveJson = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase, PropertyNameCaseInsensitive = true };

    readonly Func<string, Task<string?>> storageGet;
    readonly Func<string, string, Task> storageSet;
    readonly Random R = new();
    readonly Stopwatch clock = Stopwatch.StartNew();

    public GameData D { get; }

    public Game(GameData data, Func<string, Task<string?>> get, Func<string, string, Task> set)
    {
        D = data;
        storageGet = get;
        storageSet = set;
    }

    /// <summary>狀態改變時通知畫面重繪。</summary>
    public event Action? Changed;
    public void Render() => Changed?.Invoke();

    // ================================================================ 狀態
    public string Mode { get; private set; } = "title";
    public string MapId { get; private set; } = "village";
    public int X { get; private set; }
    public int Y { get; private set; }
    public string Dir { get; private set; } = "D";
    public List<Actor> Party { get; private set; } = new();
    public Dictionary<string, int> Inv { get; private set; } = new();
    public int Gold { get; private set; }
    public Dictionary<string, bool> Flags { get; private set; } = new();
    public int Karma { get; private set; }
    public Dictionary<string, string> Quests { get; private set; } = new();
    public string Goal { get; private set; } = "";
    public int PlayTime { get; private set; }
    public bool Busy { get; private set; }
    public List<Menu> Menus { get; } = new();
    public DialogState? Dialog { get; private set; }
    (string Speaker, string Text)? lastSay;
    public List<Toast> Toasts { get; } = new();
    public string? Banner { get; private set; }
    public int BannerId { get; private set; }
    public BattleState? Battle { get; private set; }
    public EndingState? Ending { get; private set; }
    TaskCompletionSource? waitOk;
    public bool WaitingOk => waitOk != null;
    bool pendingAuto;
    public bool SaveExists { get; private set; }
    public Dictionary<string, DexEntry> Dex { get; private set; } = new();
    public Dictionary<string, bool> Visited { get; private set; } = new();
    public CardState? Card { get; private set; }
    public BoardState? Board { get; private set; }
    public List<Popup> Popups { get; } = new();
    int popupSeq;

    // 簡單模式：敵人 HP、我方受到的傷害、經驗值與 K 幣的倍率（跟著存檔走）
    public bool Easy { get; private set; }
    const double EasyEnemyHp = 0.7, EasyDmgTaken = 0.6, EasyReward = 1.5;
    // 明雷怪的經驗值與 K 幣倍率：怪物看得到、躲得掉，遇到的場數比以前的暗雷少，用這個補回升級速度
    const double MonReward = 1.8;
    static readonly JsonElement MonBattleOpts = JsonDocument.Parse("{\"mon\":true}").RootElement;

    // 明雷：地圖上看得到的怪物
    public List<Mon> Mons { get; private set; } = new();
    long invuln;
    /// <summary>測試用：關掉怪物移動。</summary>
    public bool MonsOn { get; set; } = true;

    // 戰鬥速度（記在 meta，不跟存檔走）
    static readonly double[] BSpeeds = { 1, 0.6, 0.35 };
    static readonly string[] BSpeedNames = { "普通", "快", "超快" };
    int bspeed;
    Task BWait(int ms) => Task.Delay((int)(ms * BSpeeds[bspeed]));

    public async Task LoadSettings()
    {
        var meta = await LoadMeta();
        bspeed = Math.Clamp(meta.Speed, 0, BSpeeds.Length - 1);
    }

    void ResetState()
    {
        Mode = "title"; MapId = D.Start.Map; X = 0; Y = 0; Dir = "D";
        Party = new(); Inv = new(); Gold = 0; Flags = new(); Karma = 0; Quests = new(); Goal = ""; PlayTime = 0;
        Busy = false; Menus.Clear(); Dialog = null; lastSay = null; Toasts.Clear(); Banner = null; BannerId++;
        Battle = null; Ending = null; waitOk = null; pendingAuto = false;
        Easy = false; Mons = new(); invuln = 0;
        Dex = new(); Visited = new(); Card = null; Board = null; Popups.Clear();
    }

    public MapDef CurMap => D.Maps[MapId];

    // ================================================================ 角色數值
    public ActorDef Ad(Actor a) => D.Actors[a.Id];
    public int ExpFor(int level) => (int)Math.Round(D.ExpCurve.Mul * Math.Pow(level - 1, D.ExpCurve.Pow));

    int BaseStat(Actor a, string k)
    {
        var d = Ad(a);
        return (int)Math.Floor(d.Base.GetValueOrDefault(k) + d.Growth.GetValueOrDefault(k) * (a.Level - 1));
    }

    int EquipStat(Actor a, string k)
    {
        var s = 0;
        foreach (var slot in new[] { "weapon", "armor", "acc" })
        {
            var id = a.Equip.GetValueOrDefault(slot);
            if (id != null) s += D.Items[id].StatOf(k);
        }
        return s;
    }

    public int Stat(Actor a, string k) => Math.Max(1, BaseStat(a, k) + EquipStat(a, k));
    public int MaxHp(Actor a) => Stat(a, "hp");
    public int MaxMp(Actor a) => Stat(a, "mp");
    public List<string> SkillsOf(Actor a) => Ad(a).SkillList.Where(s => s.Level <= a.Level).Select(s => s.Skill).ToList();

    List<string> ImmunesOf(Actor a)
    {
        var acc = a.Equip.GetValueOrDefault("acc");
        return acc != null ? D.Items[acc].Immune ?? new List<string>() : new List<string>();
    }

    Actor MakeActor(string id, int level)
    {
        var d = D.Actors[id];
        var a = new Actor { Id = id, Level = level, Exp = ExpFor(level), Equip = new Dictionary<string, string?>(d.Equip) };
        a.Hp = MaxHp(a);
        a.Mp = MaxMp(a);
        return a;
    }

    bool CanEquip(Actor a, string itemId)
    {
        var it = D.Items[itemId];
        var d = Ad(a);
        return it.Type switch
        {
            "weapon" => it.Wtype != null && d.Wtypes.Contains(it.Wtype),
            "armor" => it.Atype != null && d.Atypes.Contains(it.Atype),
            "acc" => true,
            _ => false,
        };
    }

    List<string> GainExp(Actor a, int n)
    {
        var lines = new List<string>();
        a.Exp += n;
        while (a.Level < D.MaxLevel && a.Exp >= ExpFor(a.Level + 1))
        {
            int oh = MaxHp(a), om = MaxMp(a);
            var before = new HashSet<string>(SkillsOf(a));
            a.Level++;
            a.Hp += MaxHp(a) - oh;
            a.Mp += MaxMp(a) - om;
            lines.Add($"{Ad(a).Name}升到了 Lv {a.Level}！");
            foreach (var s in SkillsOf(a))
                if (!before.Contains(s)) lines.Add($"{Ad(a).Name}學會了「{D.Skills[s].Name}」！");
        }
        return lines;
    }

    // ---- 戰鬥單位共用 ----
    public string UName(Unit u) => u is Enemy e ? e.Name : Ad((Actor)u).Name;
    int UMaxHp(Unit u) => u is Enemy e ? e.MaxHp : MaxHp((Actor)u);

    double UStat(Unit u, string k)
    {
        double v = u is Enemy e ? e.Def.Stat(k) : Stat((Actor)u, k);
        if (k == "atk") { if (u.St.ContainsKey("atkUp")) v *= 1.3; if (u.St.ContainsKey("atkDown")) v *= 0.7; }
        if (k == "def") { if (u.St.ContainsKey("defUp")) v *= 1.3; if (u.St.ContainsKey("defDown")) v *= 0.7; }
        return v;
    }

    static double ElemMult(Unit t, string? elem)
    {
        if (t is not Enemy e || elem == null) return 1;
        if (e.Def.Weak != null && e.Def.Weak.Contains(elem)) return 1.5;
        if (e.Def.Resist != null && e.Def.Resist.Contains(elem)) return 0.5;
        return 1;
    }

    double Var() => 0.9 + R.NextDouble() * 0.2;
    double PhysDamage(Unit u, Unit t, double power) => Math.Max(1, UStat(u, "atk") * power - UStat(t, "def") * 0.5) * Var();
    double MagDamage(Unit u, Unit t, SkillDef sk) => Math.Max(1, UStat(u, "mag") * (sk.Power == 0 ? 1 : sk.Power) + sk.Base - UStat(t, "def") * 0.25) * Var();
    int HealAmount(Unit u, SkillDef sk) => (int)Math.Round((sk.Base + UStat(u, "mag") * sk.Power) * (0.95 + R.NextDouble() * 0.1));

    // ================================================================ 條件與文字
    public int ItemCount(string id) => Inv.GetValueOrDefault(id);

    bool CondTerm(string t)
    {
        t = t.Trim();
        if (t.StartsWith("!")) return !CondTerm(t[1..]);
        if (t.StartsWith("flag:")) return Flags.GetValueOrDefault(t[5..]);
        if (t.StartsWith("item:"))
        {
            var parts = t[5..].Split(">=");
            return ItemCount(parts[0]) >= (parts.Length > 1 ? int.Parse(parts[1]) : 1);
        }
        if (t.StartsWith("karma>=")) return Karma >= int.Parse(t[7..]);
        if (t.StartsWith("gold>=")) return Gold >= int.Parse(t[6..]);
        if (t.StartsWith("party:")) return Party.Any(a => a.Id == t[6..]);
        return false;
    }

    public bool Cond(string? c) => string.IsNullOrEmpty(c) || c.Split('|').Any(alt => alt.Split('&').All(CondTerm));
    // 對話裡的 {item:道具} 換成持有數量，{goal} 換成目前目標
    string Fmt(string s) => Regex.Replace(s, @"\{item:(\w+)\}", m => ItemCount(m.Groups[1].Value).ToString())
        .Replace("{goal}", string.IsNullOrEmpty(Goal) ? "……" : Goal);

    // ================================================================ 物品
    void AddItem(string id, int n = 1) => Inv[id] = Inv.GetValueOrDefault(id) + n;

    void RemoveItem(string id, int n = 1)
    {
        var left = Math.Max(0, Inv.GetValueOrDefault(id) - n);
        if (left == 0) Inv.Remove(id); else Inv[id] = left;
    }

    void FullHeal()
    {
        foreach (var a in Party) { a.Hp = MaxHp(a); a.Mp = MaxMp(a); }
    }

    List<string> InvList(Func<ItemDef, string, bool> filter) =>
        Inv.Keys.Where(id => Inv[id] > 0 && filter(D.Items[id], id)).ToList();

    // ================================================================ 存檔
    public async Task<bool> SaveGame()
    {
        var data = new SaveData
        {
            MapId = MapId, X = X, Y = Y, Dir = Dir, Gold = Gold, Inv = new(Inv), Flags = new(Flags), Karma = Karma,
            Quests = new(Quests), Goal = Goal, PlayTime = PlayTime, Dex = new(Dex), Visited = new(Visited), Easy = Easy,
            Party = Party.Select(a => new SaveActor { Id = a.Id, Level = a.Level, Exp = a.Exp, Hp = a.Hp, Mp = a.Mp, Equip = new(a.Equip) }).ToList(),
        };
        try
        {
            await storageSet(SaveKey, JsonSerializer.Serialize(data, SaveJson));
            SaveExists = true;
            return true;
        }
        catch
        {
            return false;
        }
    }

    public async Task CheckSave()
    {
        try { SaveExists = !string.IsNullOrEmpty(await storageGet(SaveKey)); } catch { SaveExists = false; }
    }

    async Task<bool> LoadGame()
    {
        SaveData? data;
        try
        {
            var json = await storageGet(SaveKey);
            data = string.IsNullOrEmpty(json) ? null : JsonSerializer.Deserialize<SaveData>(json, SaveJson);
        }
        catch { data = null; }
        if (data == null) return false;
        ResetState();
        MapId = data.MapId; X = data.X; Y = data.Y; Dir = data.Dir; Gold = data.Gold; Inv = data.Inv; Flags = data.Flags;
        Karma = data.Karma; Quests = data.Quests; Goal = data.Goal; PlayTime = data.PlayTime;
        Dex = data.Dex ?? new(); Visited = data.Visited ?? new(); Easy = data.Easy;
        Party = data.Party.Select(p => new Actor { Id = p.Id, Level = p.Level, Exp = p.Exp, Hp = p.Hp, Mp = p.Mp, Equip = p.Equip }).ToList();
        Mode = "map";
        SpawnMons();
        Render();
        return true;
    }

    async Task<MetaData> LoadMeta()
    {
        try
        {
            var json = await storageGet(MetaKey);
            return string.IsNullOrEmpty(json) ? new MetaData() : JsonSerializer.Deserialize<MetaData>(json, SaveJson) ?? new MetaData();
        }
        catch { return new MetaData(); }
    }

    // ================================================================ 對話、選單、提示
    Task Say(string speaker, string text)
    {
        lastSay = (speaker, text);
        var tcs = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Dialog = new DialogState(speaker, text, tcs);
        Render();
        return tcs.Task;
    }

    void AdvanceDialog()
    {
        var d = Dialog;
        if (d == null) return;
        Dialog = null;
        d.Tcs?.TrySetResult();
        Render();
    }

    Task<int> Choose(List<string> labels)
    {
        var tcs = new TaskCompletionSource<int>(TaskCreationOptions.RunContinuationsAsynchronously);
        if (lastSay is { } ls) Dialog = new DialogState(ls.Speaker, ls.Text, null);
        PushMenu(new Menu
        {
            Cls = "choice",
            Build = () => labels.Select(l => new MenuItem { Label = l }).ToList(),
            OnPick = (i, _) => { Dialog = null; PopMenu(); tcs.TrySetResult(i); },
            OnBack = () => { },
        });
        return tcs.Task;
    }

    public void ShowToast(string text)
    {
        var t = new Toast { Text = text };
        Toasts.Add(t);
        Render();
        _ = RemoveToastLater(t);
    }

    async Task RemoveToastLater(Toast t)
    {
        await Task.Delay(2400);
        Toasts.Remove(t);
        Render();
    }

    void PushMenu(Menu m)
    {
        Menus.Add(m);
        Render();
    }

    void PopMenu()
    {
        if (Menus.Count > 0) Menus.RemoveAt(Menus.Count - 1);
        Render();
    }

    /// <summary>取得選單項目；清單變短（例如賣掉或用掉最後一個道具）時，把游標拉回最後一項。</summary>
    public static List<MenuItem> MenuItems(Menu m)
    {
        var items = m.Build();
        if (m.Cursor >= items.Count) m.Cursor = Math.Max(0, items.Count - 1);
        return items;
    }

    void MenuKey(string btn)
    {
        var m = Menus[^1];
        var items = MenuItems(m);
        if (btn is "up" or "down")
        {
            if (items.Count == 0) return;
            m.Cursor = (m.Cursor + (btn == "up" ? items.Count - 1 : 1)) % items.Count;
            m.OnMove?.Invoke(m.Cursor);
            Render();
        }
        else if (btn == "ok")
        {
            if (m.Cursor < items.Count && !items[m.Cursor].Disabled) m.OnPick(m.Cursor, items[m.Cursor]);
        }
        else if (btn is "back" or "menu")
        {
            if (m.OnBack != null) m.OnBack(); else PopMenu();
        }
    }

    /// <summary>點擊選單項目：第一次移動游標，第二次確認。</summary>
    public void ClickMenuItem(int i)
    {
        if (Menus.Count == 0) return;
        var m = Menus[^1];
        if (m.Cursor != i)
        {
            m.Cursor = i;
            m.OnMove?.Invoke(i);
            Render();
            return;
        }
        Press("ok", false);
    }

    Task WaitOk()
    {
        waitOk = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        Render();
        return waitOk.Task;
    }

    // ================================================================ 劇情腳本
    /// <summary>執行腳本。回傳 false 表示中止（全滅、結局）。</summary>
    async Task<bool> Run(JsonElement? script)
    {
        if (script is not JsonElement sc || sc.ValueKind != JsonValueKind.Array) return true;
        foreach (var c in sc.EnumerateArray())
            if (!await Exec(c)) return false;
        return true;
    }

    static string Str(JsonElement c, int i) => c.GetArrayLength() > i ? c[i].GetString() ?? "" : "";
    static int Int(JsonElement c, int i, int def) => c.GetArrayLength() > i && c[i].ValueKind == JsonValueKind.Number ? c[i].GetInt32() : def;

    async Task<bool> Exec(JsonElement c)
    {
        var op = c[0].GetString();
        switch (op)
        {
            case "say":
                for (var i = 2; i < c.GetArrayLength(); i++) await Say(Str(c, 1), Fmt(Str(c, i)));
                break;
            case "if":
                if (Cond(Str(c, 1))) return await Run(c[2]);
                if (c.GetArrayLength() > 3) return await Run(c[3]);
                break;
            case "choice":
            {
                var opts = new List<JsonElement>();
                for (var i = 1; i < c.GetArrayLength(); i++) opts.Add(c[i]);
                var pick = await Choose(opts.Select(o => o[0].GetString() ?? "").ToList());
                return await Run(opts[pick][1]);
            }
            case "flag": Flags[Str(c, 1)] = true; break;
            case "unflag": Flags.Remove(Str(c, 1)); break;
            case "give":
            {
                var id = Str(c, 1);
                var n = Int(c, 2, 1);
                AddItem(id, n);
                await Say("", $"獲得了【{D.Items[id].Name}】{(n > 1 ? " ×" + n : "")}！");
                break;
            }
            case "take": RemoveItem(Str(c, 1), Int(c, 2, 1)); break;
            case "gold":
            {
                var n = Int(c, 1, 0);
                Gold += n;
                await Say("", $"得到了 {n} K 幣！");
                break;
            }
            case "goal": Goal = Str(c, 1); ShowToast("目標：" + Goal); break;
            case "quest":
            {
                var id = Str(c, 1);
                if (Quests.GetValueOrDefault(id) == "done") break;
                Quests[id] = Str(c, 2);
                ShowToast((Str(c, 2) == "done" ? "任務完成：" : "新任務：") + D.Quests[id].Name);
                break;
            }
            case "karma":
            {
                var n = Int(c, 1, 0);
                Karma += n;
                ShowToast(n > 0 ? "（島上某處，有人默默回了一句：推。）" : "（島上某處，有人只回了一個字：閱。）");
                break;
            }
            case "chapter": await ShowCard(Str(c, 1), Str(c, 2), Str(c, 3)); break;
            case "board": await OpenBoard(Str(c, 1)); break;
            case "battle":
            {
                var opts = c.GetArrayLength() > 2 ? c[2] : default;
                var r = await RunBattle(Str(c, 1), opts);
                if (r == "lose") { await GameOver(); return false; }
                break;
            }
            case "join":
            {
                var id = Str(c, 1);
                var lv = Math.Max(D.Actors[id].JoinLevel, Party[0].Level - 1);
                Party.Add(MakeActor(id, lv));
                break;
            }
            case "heal": FullHeal(); break;
            case "inn":
            {
                var price = Int(c, 1, 0);
                var i = await Choose(new List<string> { $"休息（{price} K 幣）", "不用了" });
                if (i == 0)
                {
                    if (Gold < price) await Say("", "K 幣不夠……");
                    else { Gold -= price; FullHeal(); await Say("", "安心地潛水了一晚。全隊的 HP 與 MP 都回復了！"); }
                }
                break;
            }
            case "shop": await OpenShop(Str(c, 1)); break;
            case "warp": Teleport(Str(c, 1), Int(c, 2, 0), Int(c, 3, 0), Str(c, 4)); break;
            case "save": await Say("", await SaveGame() ? "冒險已記錄。這串不會沉了。" : "（這個瀏覽器無法存檔）"); break;
            case "ending": await ShowEnding(Str(c, 1)); return false;
            case "call": return await Run(D.Calls[Str(c, 1)]);
        }
        return true;
    }

    async Task RunBusy(JsonElement? script)
    {
        Busy = true;
        Render();
        try
        {
            if (!await Run(script)) return;
            while (pendingAuto)
            {
                pendingAuto = false;
                if (!await RunAutos()) return;
            }
        }
        finally
        {
            if (Mode is "map" or "battle") Busy = false;
            Render();
        }
    }

    async Task<bool> RunAutos()
    {
        foreach (var a in CurMap.Auto)
            if (Cond(a.Cond) && !await Run(a.Script)) return false;
        return true;
    }

    /// <summary>用程式組出一小段腳本（寶箱、遇敵用）。</summary>
    static JsonElement Script(params object[][] cmds) => JsonSerializer.SerializeToElement(cmds);

    // ================================================================ 地圖
    void Teleport(string mapId, int x, int y, string dir)
    {
        MapId = mapId; X = x; Y = y; Dir = dir;
        Visited[mapId] = true;
        Banner = D.Maps[mapId].Name;
        BannerId++;
        pendingAuto = true;
        SpawnMons();
    }

    // ================================================================ 明雷：地圖上看得到的怪物
    // 進入有怪物的地圖時，在離玩家遠一點的地方放幾隻怪。牠們平常亂晃，玩家靠近就會追過來；
    // 碰到就開戰。打贏的怪在離開地圖前不會再出現；用「無視」逃走時，那隻怪會暫時不追人。
    Mon? MonAt(int x, int y) => Mons.FirstOrDefault(m => m.X == x && m.Y == y);
    bool WarpAt(int x, int y) => CurMap.WarpList.Any(w => w.X == x && w.Y == y);
    bool MonFree(int x, int y) => Walkable(x, y) && EntAt(x, y) == null && !WarpAt(x, y) && MonAt(x, y) == null && !(x == X && y == Y);

    int MonCount(int walkTiles)
    {
        var n = Math.Clamp((int)Math.Round(walkTiles / 45.0, MidpointRounding.AwayFromZero), 3, 9);
        return Easy ? Math.Max(2, n - 3) : n;
    }

    string PickTroop(EncDef enc)
    {
        var total = enc.TroopList.Sum(t => t.Weight);
        var r = R.NextDouble() * total;
        foreach (var (troop, weight) in enc.TroopList)
        {
            r -= weight;
            if (r < 0) return troop;
        }
        return enc.TroopList[0].Troop;
    }

    void SpawnMons()
    {
        Mons = new List<Mon>();
        var map = CurMap;
        var enc = map.Enc;
        if (enc == null || enc.TroopList.Count == 0 || !MonsOn) return;
        var walk = new List<(int X, int Y)>();
        for (var y = 0; y < map.H; y++)
            for (var x = 0; x < map.W; x++)
                if (Walkable(x, y)) walk.Add((x, y));
        var cand = walk.Where(p => Math.Abs(p.X - X) + Math.Abs(p.Y - Y) >= 6 && MonFree(p.X, p.Y)).ToList();
        var now = clock.ElapsedMilliseconds;
        var n = MonCount(walk.Count);
        for (var i = 0; i < n && cand.Count > 0; i++)
        {
            var k = R.Next(cand.Count);
            var (px, py) = cand[k];
            cand.RemoveAt(k);
            var troop = PickTroop(enc);
            // 地圖上顯示這一組裡最強（HP 最高）的怪
            var lead = D.Troops[troop].Aggregate((a, b) => D.Enemies[b].Hp > D.Enemies[a].Hp ? b : a);
            var sprite = string.IsNullOrEmpty(D.Enemies[lead].Sprite) ? lead : D.Enemies[lead].Sprite;
            Mons.Add(new Mon { Id = $"m{i}_{R.Next(1000000)}", X = px, Y = py, Troop = troop, Sprite = sprite, Next = now + 600 + R.Next(1200) });
        }
    }

    bool MonIdle => MonsOn && Mode == "map" && !Busy && Menus.Count == 0 && Dialog == null && Board == null && Card == null;

    /// <summary>每 100 毫秒由畫面呼叫一次：讓怪物移動，碰到玩家就開戰。</summary>
    public void MonTick()
    {
        if (!MonIdle || Mons.Count == 0) return;
        var now = clock.ElapsedMilliseconds;
        var acted = false;
        foreach (var m in Mons.ToList())
        {
            if (now < m.Next) continue;
            acted = true;
            var dist = Math.Abs(m.X - X) + Math.Abs(m.Y - Y);
            m.Chasing = dist <= (Easy ? 3 : 6) && now >= m.Calm;
            var dirs = new List<(int Dx, int Dy)>();
            if (m.Chasing)
            {
                int sx = Math.Sign(X - m.X), sy = Math.Sign(Y - m.Y);
                if (Math.Abs(X - m.X) >= Math.Abs(Y - m.Y)) { dirs.Add((sx, 0)); dirs.Add((0, sy)); }
                else { dirs.Add((0, sy)); dirs.Add((sx, 0)); }
                dirs.RemoveAll(d => d.Dx == 0 && d.Dy == 0);
                m.Next = now + (Easy ? 520 : 300);
            }
            else
            {
                m.Next = now + 700 + R.Next(900);
                if (R.NextDouble() < 0.45) continue;
                dirs.Add(R.Next(4) switch { 0 => (1, 0), 1 => (-1, 0), 2 => (0, 1), _ => (0, -1) });
            }
            foreach (var (ax, ay) in dirs)
            {
                int nx = m.X + ax, ny = m.Y + ay;
                if (nx == X && ny == Y)
                {
                    if (now >= invuln) { Render(); Encounter(m); return; }
                    continue;
                }
                if (MonFree(nx, ny)) { m.X = nx; m.Y = ny; break; }
            }
        }
        if (acted) Render();
    }

    void Encounter(Mon m)
    {
        if (Busy || Mode != "map") return;
        Busy = true;
        _ = EncounterAsync(m);
    }

    async Task EncounterAsync(Mon m)
    {
        try
        {
            var r = await RunBattle(m.Troop, MonBattleOpts);
            if (r == "lose") { await GameOver(); return; }
            if (r == "win") Mons.Remove(m);
            else m.Calm = clock.ElapsedMilliseconds + 4000;   // 無視成功：這隻怪暫時不追
            invuln = clock.ElapsedMilliseconds + 1500;        // 剛打完的一小段時間不會再被碰到
        }
        finally
        {
            if (Mode is "map" or "battle") Busy = false;
            Render();
        }
    }

    public IEnumerable<EntDef> VisibleEnts() => CurMap.Ents.Where(e => Cond(e.Show));
    EntDef? EntAt(int x, int y) => VisibleEnts().FirstOrDefault(e => e.X == x && e.Y == y);

    bool Walkable(int x, int y)
    {
        var m = CurMap;
        if (y < 0 || y >= m.H || x < 0 || x >= m.W) return false;
        return D.TileMap[m.Rows[y][x]].Walk;
    }

    char TileAt(int x, int y)
    {
        var m = CurMap;
        if (y < 0 || y >= m.H || x < 0 || x >= m.W) return 'T';
        return m.Rows[y][x];
    }

    static (int Dx, int Dy) Step(string dir) => dir switch { "U" => (0, -1), "D" => (0, 1), "L" => (-1, 0), _ => (1, 0) };

    long lastMove;

    // 主角的圖：依面向選正面／背面／側面（朝左時畫面會把側面左右翻轉），走路時短暫換成跨步的圖
    static readonly string[] HeroDown = { "hero", "hero_d1", "hero_d2" };
    static readonly string[] HeroUp = { "hero_back", "hero_u1", "hero_u2" };
    static readonly string[] HeroSide = { "hero_side", "hero_s1", "hero_s2" };
    public static readonly string[] HeroFrames = HeroDown.Concat(HeroUp).Concat(HeroSide).ToArray();

    /// <summary>0 = 站著，1／2 = 左右腳輪流跨步。</summary>
    public int Walk { get; private set; }
    int walkAlt, walkSeq;

    public string HeroSprite => (Dir switch { "U" => HeroUp, "L" or "R" => HeroSide, _ => HeroDown })[Math.Clamp(Walk, 0, 2)];

    void StepAnim()
    {
        walkAlt = walkAlt == 1 ? 2 : 1;
        Walk = walkAlt;
        _ = WalkReset(++walkSeq);
    }

    async Task WalkReset(int my)
    {
        await Task.Delay(120);
        if (my != walkSeq) return;
        Walk = 0;
        if (Mode == "map") Render();
    }

    void TryMove(string dir)
    {
        var now = clock.ElapsedMilliseconds;
        if (now - lastMove < 135) return;
        lastMove = now;
        Dir = dir;
        var (dx, dy) = Step(dir);
        int nx = X + dx, ny = Y + dy;
        if (!Walkable(nx, ny) || EntAt(nx, ny) != null) { Render(); return; }
        var mon = MonAt(nx, ny);
        if (mon != null)
        {
            Render();
            if (now >= invuln) Encounter(mon);
            return;
        }
        X = nx; Y = ny;
        StepAnim();
        var w = CurMap.WarpList.FirstOrDefault(q => q.X == nx && q.Y == ny);
        if (w != null)
        {
            Teleport(w.Map, w.Tx, w.Ty, w.Dir);
            _ = SaveGame();
            Render();
            _ = RunBusy(null);
            return;
        }
        Render();
    }

    void Interact()
    {
        var (dx, dy) = Step(Dir);
        int fx = X + dx, fy = Y + dy;
        if (TileAt(fx, fy) == 'u') { fx += dx; fy += dy; }
        var e = EntAt(fx, fy);
        if (e == null) return;
        if (e.Chest != null) { OpenChest(e); return; }
        _ = RunBusy(e.Script);
    }

    public string ChestFlag(EntDef e) => $"chest:{MapId}:{e.Id}";

    void OpenChest(EntDef e)
    {
        var f = ChestFlag(e);
        if (Flags.GetValueOrDefault(f)) { _ = RunBusy(Script(new object[] { "say", "", "寶箱是空的。" })); return; }
        Flags[f] = true;
        var chest = e.Chest!;
        if (chest.Item != null)
            _ = RunBusy(Script(new object[] { "say", "", "打開了寶箱！" }, new object[] { "give", chest.Item, Math.Max(1, chest.N) }));
        else
            _ = RunBusy(Script(new object[] { "say", "", "打開了寶箱！" }, new object[] { "gold", chest.Gold }));
    }

    // ================================================================ 標題、新遊戲、結局、全滅
    public void ToTitle()
    {
        ResetState();
        PushMenu(new Menu
        {
            Cls = "center title",
            Build = () => new List<MenuItem> { new() { Label = "開新串" }, new() { Label = "回到串裡", Disabled = !SaveExists } },
            OnBack = () => { },
            OnPick = (i, _) =>
            {
                if (i == 0)
                {
                    PushMenu(new Menu
                    {
                        Title = "選擇難度",
                        Cls = "center",
                        Build = () => new List<MenuItem>
                        {
                            new() { Label = "普通", Desc = "原本的難度。怪物會追人，魔王不好打。" },
                            new() { Label = "簡單", Desc = "敵人比較弱、受到的傷害較少、經驗值與 K 幣 1.5 倍、「無視」一定成功、怪物比較少也不太追人。適合想專心看劇情的島民。之後也能在「設定」裡切換。" },
                        },
                        OnPick = (j, picked) => NewGame(j == 1),
                    });
                }
                else _ = ContinueGame();
            },
        });
    }

    async Task ContinueGame()
    {
        if (await LoadGame()) ShowToast("串浮上來了。從存檔繼續。");
    }

    void NewGame(bool easy)
    {
        ResetState();
        Easy = easy;
        var st = D.Start;
        Party = st.Party.Select(id => MakeActor(id, D.Actors[id].JoinLevel)).ToList();
        Gold = st.Gold;
        foreach (var (item, count) in st.ItemList) AddItem(item, count);
        Mode = "map";
        Teleport(st.Map, st.X, st.Y, st.Dir);
        Render();
        _ = RunBusy(st.Script);
    }

    async Task ShowEnding(string id)
    {
        var e = D.Endings[id];
        Mode = "ending";
        Ending = new EndingState { Id = id, Title = e.Title, PostId = Guid.NewGuid().ToString("N")[..8] };
        Busy = true;
        Render();
        await Task.Delay(600);
        foreach (var line in e.Lines) await Say("", line);
        var meta = await LoadMeta();
        if (!meta.Endings.Contains(id)) meta.Endings.Add(id);
        try { await storageSet(MetaKey, JsonSerializer.Serialize(meta, SaveJson)); } catch { /* 無法存檔也沒關係 */ }
        Ending.Card = true;
        Ending.Seen = meta.Endings.Count;
        Render();
        var tcs = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        PushMenu(new Menu
        {
            Cls = "center",
            Build = () => new List<MenuItem> { new() { Label = "回到標題" } },
            OnPick = (_, _) => { PopMenu(); tcs.TrySetResult(); },
            OnBack = () => { },
        });
        await tcs.Task;
        ToTitle();
    }

    async Task GameOver()
    {
        Mode = "gameover";
        Busy = true;
        PushMenu(new Menu
        {
            Cls = "center",
            Cursor = SaveExists ? 0 : 1, // 沒有存檔時，游標直接停在「回到標題」
            Build = () => new List<MenuItem> { new() { Label = "從存檔把串推回來", Disabled = !SaveExists }, new() { Label = "回到標題" } },
            OnBack = () => { },
            OnPick = (i, _) =>
            {
                if (i == 0) _ = ContinueGame();
                else ToTitle();
            },
        });
        // 永遠不會繼續：讀檔或回標題會重設整個狀態
        await new TaskCompletionSource().Task;
    }

    // ================================================================ 輸入
    public void Press(string btn, bool repeat)
    {
        if (btn is "ok" or "back" or "menu" && repeat) return;
        if (Card != null)
        {
            if (btn == "ok") CloseCard(Card);
            return;
        }
        if (Board != null)
        {
            BoardKey(btn);
            return;
        }
        if (Dialog != null && Menus.Count == 0)
        {
            if (btn == "ok") AdvanceDialog();
            return;
        }
        if (waitOk != null && btn == "ok")
        {
            var w = waitOk;
            waitOk = null;
            w.TrySetResult();
            return;
        }
        if (Menus.Count > 0)
        {
            if (btn is "left" or "right") return;
            MenuKey(btn);
            return;
        }
        if (Mode != "map" || Busy) return;
        switch (btn)
        {
            case "up": TryMove("U"); break;
            case "down": TryMove("D"); break;
            case "left": TryMove("L"); break;
            case "right": TryMove("R"); break;
            case "ok": Interact(); break;
            case "back":
            case "menu": OpenMainMenu(); break;
        }
    }

    /// <summary>點擊對話框。</summary>
    public void ClickDialog()
    {
        if (Dialog != null || waitOk != null) Press("ok", false);
    }

    /// <summary>點擊章節卡或討論板。</summary>
    public void ClickOverlay(bool header)
    {
        if (Card != null) Press("ok", false);
        else if (Board != null) Press(header ? "back" : "down", false);
    }

    /// <summary>每秒呼叫一次，累計遊玩時間。</summary>
    public void Tick()
    {
        if (Mode is "map" or "battle") PlayTime++;
    }
}
