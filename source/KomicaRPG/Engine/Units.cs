namespace KomicaRPG.Engine;

/// <summary>戰鬥單位共用的部分（隊員與敵人）。</summary>
public abstract class Unit
{
    public int Hp { get; set; }
    public Dictionary<string, int> St { get; set; } = new();
    public bool Guard { get; set; }
    public string Fx { get; set; } = "";
    public abstract bool IsEnemy { get; }
    public bool Alive => Hp > 0;
}

/// <summary>隊員。</summary>
public class Actor : Unit
{
    public string Id { get; set; } = "";
    public int Level { get; set; } = 1;
    public int Exp { get; set; }
    public int Mp { get; set; }
    public Dictionary<string, string?> Equip { get; set; } = new();
    public override bool IsEnemy => false;
}

/// <summary>敵人。</summary>
public class Enemy : Unit
{
    public string Uid { get; set; } = "";
    public string Id { get; set; } = "";
    public EnemyDef Def { get; set; } = null!;
    public string Name { get; set; } = "";
    public int MaxHp { get; set; }
    public bool LowUsed { get; set; }
    public override bool IsEnemy => true;
}

public class MenuItem
{
    public string Label { get; set; } = "";
    public string? Right { get; set; }
    public bool Disabled { get; set; }
    public string? Desc { get; set; }
    public string? Id { get; set; }
    public string? Slot { get; set; }
    public string? Cmd { get; set; }
    public TravelDef? Travel { get; set; }
}

public class Menu
{
    public string Cls { get; set; } = "";
    public string? Title { get; set; }
    public int Cursor { get; set; }
    public Func<List<MenuItem>> Build { get; set; } = () => new List<MenuItem>();
    public Action<int, MenuItem> OnPick { get; set; } = (_, _) => { };
    public Action? OnBack { get; set; }
    public Action<int>? OnMove { get; set; }
    public Actor? Actor { get; set; }
}

public class DialogState
{
    public DialogState(string speaker, string text, TaskCompletionSource? tcs, bool hand = false)
    {
        Speaker = speaker;
        Text = text;
        Tcs = tcs;
        Hand = hand;
    }

    public string Speaker { get; }
    public string Text { get; }
    /// <summary>用手寫字顯示（腳本的 hand 指令）。</summary>
    public bool Hand { get; }
    public TaskCompletionSource? Tcs { get; }
}

public class Toast
{
    public string Text { get; set; } = "";
}

public class BattleState
{
    public List<Enemy> Enemies { get; set; } = new();
    public int Turn { get; set; }
    public List<string> Log { get; } = new();
    public string Bg { get; set; } = "field";
    /// <summary>由地圖上的怪物（明雷）引發的戰鬥。</summary>
    public bool FromMon { get; set; }
    public bool NoFlee { get; set; }
    public int ActorIndex { get; set; } = -1;
    public Unit? Hi { get; set; }
    public bool Intro { get; set; } = true;
    public bool Done { get; set; }
    public int Gauge { get; set; }
    public bool ComboQueued { get; set; }
}

public class EndingState
{
    public string Id { get; set; } = "";
    public string Title { get; set; } = "";
    public bool Card { get; set; }
    public int Seen { get; set; }
    public string PostId { get; set; } = "";
}

/// <summary>玩家行動（或敵人行動）。</summary>
public class BattleAction
{
    public string Type { get; set; } = "attack";   // attack / skill / item / defend / auto
    public Unit U { get; set; } = null!;
    public Unit? T { get; set; }
    public string? Skill { get; set; }
    public string? Item { get; set; }
    public string? Warn { get; set; }
    public double Pri { get; set; }
    public bool Back { get; set; }
    public bool Flee { get; set; }
    public bool AutoAll { get; set; }
    public string? Combo { get; set; }
}

/// <summary>存檔格式。</summary>
public class SaveData
{
    public int V { get; set; } = 1;
    public string MapId { get; set; } = "";
    public int X { get; set; }
    public int Y { get; set; }
    public string Dir { get; set; } = "D";
    public int Gold { get; set; }
    public Dictionary<string, int> Inv { get; set; } = new();
    public Dictionary<string, bool> Flags { get; set; } = new();
    public int Karma { get; set; }
    public Dictionary<string, string> Quests { get; set; } = new();
    public string Goal { get; set; } = "";
    public int PlayTime { get; set; }
    public List<SaveActor> Party { get; set; } = new();
    public Dictionary<string, DexEntry> Dex { get; set; } = new();
    public Dictionary<string, bool> Visited { get; set; } = new();
    public bool Easy { get; set; }
    public bool Auto { get; set; }
    public Dictionary<string, string> AutoSeen { get; set; } = new();
    public string? GoalMap { get; set; }
    public bool AutoMain { get; set; }
    public AdvStats Stats { get; set; } = new();
}

/// <summary>本次冒險紀錄（全破時顯示在結局卡）。</summary>
public class AdvStats
{
    public int Battles { get; set; }
    public int Wins { get; set; }
    public int Flees { get; set; }
    public int Steps { get; set; }
    public int Revives { get; set; }
    public bool AutoUsed { get; set; }
}

/// <summary>地圖上看得到的怪物（明雷）。</summary>
public class Mon
{
    public string Id { get; set; } = "";
    public int X { get; set; }
    public int Y { get; set; }
    public string Troop { get; set; } = "";
    public string Sprite { get; set; } = "";
    /// <summary>下一次行動的時間（毫秒）。</summary>
    public long Next { get; set; }
    /// <summary>在這個時間之前不追人（被「無視」之後）。</summary>
    public long Calm { get; set; }
    public bool Chasing { get; set; }
}

public class SaveActor
{
    public string Id { get; set; } = "";
    public int Level { get; set; }
    public int Exp { get; set; }
    public int Hp { get; set; }
    public int Mp { get; set; }
    public Dictionary<string, string?> Equip { get; set; } = new();
}

public class MetaData
{
    public List<string> Endings { get; set; } = new();
    public int Speed { get; set; }
    public int AutoSpeed { get; set; }
    /// <summary>目標箭頭（沒設定過＝開）。</summary>
    public bool? Arrow { get; set; }
    /// <summary>所有對話都用手寫字。</summary>
    public bool Hand { get; set; }
}

/// <summary>怪物圖鑑的一筆紀錄。</summary>
public class DexEntry
{
    public bool Seen { get; set; }
    public int Killed { get; set; }
    public List<string> Weak { get; set; } = new();
    public List<string> Resist { get; set; } = new();
}

/// <summary>戰鬥中跳出的傷害數字。</summary>
public class Popup
{
    public int Id { get; set; }
    public string Key { get; set; } = "";
    public string Text { get; set; } = "";
    public string Cls { get; set; } = "";
}

/// <summary>章節標題卡。</summary>
public class CardState
{
    public string Label { get; set; } = "";
    public string Title { get; set; } = "";
    public string Sub { get; set; } = "";
    public TaskCompletionSource Tcs { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
}

/// <summary>正在閱讀的討論板。</summary>
public class BoardState
{
    public string Id { get; set; } = "";
    public int Top { get; set; }
    public TaskCompletionSource Tcs { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
}
