using System.Text.Json;
using System.Text.Json.Serialization;

namespace KomicaRPG.Engine;

/// <summary>
/// wwwroot/data/game.json 的資料模型（和網頁版共用同一份 JSON）。
/// 混合型別的陣列（例如 [3, "e_summon", "警告文字"]）先用 JsonElement 讀進來，再在 Prepare() 轉成強型別。
/// </summary>
public class GameData
{
    public string Title { get; set; } = "";
    public string Subtitle { get; set; } = "";
    public Dictionary<string, JsonElement> Tiles { get; set; } = new();
    public Dictionary<string, StatusDef> Statuses { get; set; } = new();
    public Dictionary<string, ActorDef> Actors { get; set; } = new();
    public Dictionary<string, SkillDef> Skills { get; set; } = new();
    public Dictionary<string, ItemDef> Items { get; set; } = new();
    public Dictionary<string, EnemyDef> Enemies { get; set; } = new();
    public Dictionary<string, List<string>> Troops { get; set; } = new();
    public Dictionary<string, List<string>> Shops { get; set; } = new();
    public Dictionary<string, QuestDef> Quests { get; set; } = new();
    public Dictionary<string, MapDef> Maps { get; set; } = new();
    public Dictionary<string, JsonElement> Calls { get; set; } = new();
    public Dictionary<string, EndingDef> Endings { get; set; } = new();
    public StartDef Start { get; set; } = new();
    public ExpCurveDef ExpCurve { get; set; } = new();
    public int MaxLevel { get; set; } = 40;
    public Dictionary<string, BoardDef> Boards { get; set; } = new();
    public List<SkitDef> Skits { get; set; } = new();
    public List<TravelDef> Travel { get; set; } = new();
    public List<string> NoTravel { get; set; } = new();
    public GaugeDef Gauge { get; set; } = new();
    public Dictionary<string, ComboDef> Combos { get; set; } = new();
    /// <summary>對話框用「手寫字」顯示的角色。</summary>
    public List<string> Hand { get; set; } = new();

    [JsonIgnore] public Dictionary<char, TileInfo> TileMap { get; } = new();

    public static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = true };

    public static GameData Load(string json)
    {
        var d = JsonSerializer.Deserialize<GameData>(json, JsonOptions) ?? throw new InvalidOperationException("game.json 讀取失敗");
        d.Prepare();
        return d;
    }

    void Prepare()
    {
        foreach (var kv in Tiles)
            TileMap[kv.Key[0]] = new TileInfo(kv.Value[0].GetString() ?? "grass", kv.Value[1].GetInt32() == 1);
        foreach (var a in Actors.Values) a.Prepare();
        foreach (var e in Enemies.Values) e.Prepare();
        foreach (var m in Maps.Values) m.Prepare();
        Start.Prepare();
    }
}

public record TileInfo(string Image, bool Walk);
public record WarpDef(int X, int Y, string Map, int Tx, int Ty, string Dir);

public class StatusDef
{
    public string Name { get; set; } = "";
    public string Color { get; set; } = "#ccc";
}

public class ActorDef
{
    public string Name { get; set; } = "";
    public string Sprite { get; set; } = "";
    public int JoinLevel { get; set; } = 1;
    public Dictionary<string, double> Base { get; set; } = new();
    public Dictionary<string, double> Growth { get; set; } = new();
    public List<JsonElement> Skills { get; set; } = new();
    public Dictionary<string, string?> Equip { get; set; } = new();
    public List<string> Wtypes { get; set; } = new();
    public List<string> Atypes { get; set; } = new();

    [JsonIgnore] public List<(int Level, string Skill)> SkillList { get; } = new();

    public void Prepare()
    {
        foreach (var s in Skills) SkillList.Add((s[0].GetInt32(), s[1].GetString() ?? ""));
    }
}

public class SkillDef
{
    public string Name { get; set; } = "";
    public int Mp { get; set; }
    public string Target { get; set; } = "enemy";
    public string Kind { get; set; } = "phys";
    public string Desc { get; set; } = "";
    public double Power { get; set; }
    public double Base { get; set; }
    public string? Elem { get; set; }
    public string? Status { get; set; }
    public double? Chance { get; set; }
    public int? Turns { get; set; }
    public string? Status2 { get; set; }
    public double? Chance2 { get; set; }
    public string? Fx { get; set; }
    public string? Summon { get; set; }
    public double Rate { get; set; }
    public bool Revive { get; set; }
    public bool Field { get; set; }
    public bool First { get; set; }
}

public class ItemDef
{
    public string Name { get; set; } = "";
    public string Type { get; set; } = "use";
    public int Price { get; set; }
    public string Desc { get; set; } = "";
    public string? Target { get; set; }
    public int Heal { get; set; }
    public int Mp { get; set; }
    public double Revive { get; set; }
    public bool Cure { get; set; }
    public int Damage { get; set; }
    public string? Elem { get; set; }
    public bool BattleOnly { get; set; }
    public string? Wtype { get; set; }
    public string? Atype { get; set; }
    public Dictionary<string, int>? Stats { get; set; }
    public List<string>? Immune { get; set; }

    public int StatOf(string k) => Stats != null && Stats.TryGetValue(k, out var v) ? v : 0;
    [JsonIgnore] public bool IsEquip => Type is "weapon" or "armor" or "acc";
}

public class EnemyDef
{
    public string Name { get; set; } = "";
    public string Sprite { get; set; } = "";
    public int Hp { get; set; }
    public int Atk { get; set; }
    public int Def { get; set; }
    public int Mag { get; set; }
    public int Spd { get; set; }
    public int Exp { get; set; }
    public int Gold { get; set; }
    public AiDef Ai { get; set; } = new();
    public List<string>? Weak { get; set; }
    public List<string>? Resist { get; set; }
    public List<string>? Immune { get; set; }
    public List<JsonElement>? Drops { get; set; }
    public bool Boss { get; set; }
    public string? Size { get; set; }
    public double YieldAt { get; set; }
    public string Desc { get; set; } = "";

    [JsonIgnore] public List<(string Item, double Chance)> DropList { get; } = new();

    public double Stat(string k) => k switch { "atk" => Atk, "def" => Def, "mag" => Mag, "spd" => Spd, "hp" => Hp, _ => 0 };

    public void Prepare()
    {
        Ai.Prepare();
        if (Drops != null)
            foreach (var d in Drops) DropList.Add((d[0].GetString() ?? "", d[1].GetDouble()));
    }
}

public class AiDef
{
    public List<JsonElement> Pattern { get; set; } = new();
    public JsonElement? Every { get; set; }
    public JsonElement? Low { get; set; }

    [JsonIgnore] public List<(string Skill, double Weight)> PatternList { get; } = new();
    [JsonIgnore] public int EveryN { get; private set; }
    [JsonIgnore] public string? EverySkill { get; private set; }
    [JsonIgnore] public string? EveryWarn { get; private set; }
    [JsonIgnore] public double LowAt { get; private set; }
    [JsonIgnore] public string? LowSkill { get; private set; }
    [JsonIgnore] public string? LowWarn { get; private set; }

    public void Prepare()
    {
        foreach (var p in Pattern) PatternList.Add((p[0].GetString() ?? "e_attack", p[1].GetDouble()));
        if (Every is JsonElement ev && ev.ValueKind == JsonValueKind.Array)
        {
            EveryN = ev[0].GetInt32();
            EverySkill = ev[1].GetString();
            EveryWarn = ev.GetArrayLength() > 2 ? ev[2].GetString() : null;
        }
        if (Low is JsonElement lo && lo.ValueKind == JsonValueKind.Array)
        {
            LowAt = lo[0].GetDouble();
            LowSkill = lo[1].GetString();
            LowWarn = lo.GetArrayLength() > 2 ? lo[2].GetString() : null;
        }
    }
}

public class MapDef
{
    public string Name { get; set; } = "";
    public string[] Rows { get; set; } = Array.Empty<string>();
    public string Bg { get; set; } = "field";
    public List<EntDef> Ents { get; set; } = new();
    public List<JsonElement> Warps { get; set; } = new();
    public List<AutoDef> Auto { get; set; } = new();
    public EncDef? Enc { get; set; }

    [JsonIgnore] public List<WarpDef> WarpList { get; } = new();
    [JsonIgnore] public int W => Rows[0].Length;
    [JsonIgnore] public int H => Rows.Length;

    public void Prepare()
    {
        foreach (var w in Warps)
            WarpList.Add(new WarpDef(w[0].GetInt32(), w[1].GetInt32(), w[2].GetString() ?? "", w[3].GetInt32(), w[4].GetInt32(), w[5].GetString() ?? "D"));
        Enc?.Prepare();
    }
}

public class EntDef
{
    public string Id { get; set; } = "";
    public string Sprite { get; set; } = "";
    public int X { get; set; }
    public int Y { get; set; }
    public JsonElement? Script { get; set; }
    public string? Show { get; set; }
    /// <summary>條件成立時，人物頭上會出現跳動的「！」，提示現在該找他說話。</summary>
    public string? Mark { get; set; }
    public ChestDef? Chest { get; set; }
}

public class ChestDef
{
    public string? Item { get; set; }
    public int N { get; set; } = 1;
    public int Gold { get; set; }
}

public class AutoDef
{
    public string Cond { get; set; } = "";
    public JsonElement Script { get; set; }
}

public class EncDef
{
    public int Rate { get; set; }
    public List<JsonElement> Troops { get; set; } = new();
    [JsonIgnore] public List<(string Troop, int Weight)> TroopList { get; } = new();

    public void Prepare()
    {
        foreach (var t in Troops) TroopList.Add((t[0].GetString() ?? "", t[1].GetInt32()));
    }
}

public class QuestDef
{
    public string Name { get; set; } = "";
    public string Desc { get; set; } = "";
}

public class EndingDef
{
    public string Title { get; set; } = "";
    public List<string> Lines { get; set; } = new();
}

public class StartDef
{
    public string Map { get; set; } = "village";
    public int X { get; set; }
    public int Y { get; set; }
    public string Dir { get; set; } = "D";
    public int Gold { get; set; }
    public List<JsonElement> Items { get; set; } = new();
    public List<string> Party { get; set; } = new();
    public JsonElement Script { get; set; }

    [JsonIgnore] public List<(string Item, int Count)> ItemList { get; } = new();

    public void Prepare()
    {
        foreach (var i in Items) ItemList.Add((i[0].GetString() ?? "", i[1].GetInt32()));
    }
}

public class ExpCurveDef
{
    public double Mul { get; set; } = 10;
    public double Pow { get; set; } = 2.2;
}

public class BoardDef
{
    public string Title { get; set; } = "";
    public List<PostDef> Posts { get; set; } = new();
}

public class PostDef
{
    public string? Cond { get; set; }
    public string Text { get; set; } = "";
    public bool Owner { get; set; }
}

public class SkitDef
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public string Cond { get; set; } = "";
    public JsonElement Script { get; set; }
}

public class TravelDef
{
    public string Map { get; set; } = "";
    public string Name { get; set; } = "";
    public int X { get; set; }
    public int Y { get; set; }
    public string Dir { get; set; } = "D";
    public string? Cond { get; set; }
}

public class GaugeDef
{
    public int Hit { get; set; } = 4;
    public int Weak { get; set; } = 9;
    public int Crit { get; set; } = 6;
    public int Hurt { get; set; } = 3;
    public int Defend { get; set; } = 6;
    public int Ko { get; set; } = 12;
}

public class ComboDef
{
    public string Name { get; set; } = "";
    public string Desc { get; set; } = "";
    public string Kind { get; set; } = "damage";
    public double Atk { get; set; }
    public double Mag { get; set; }
    public string? Elem { get; set; }
}
