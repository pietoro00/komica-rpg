using System.Text.Json;

namespace KomicaRPG.Engine;

/// <summary>回合制戰鬥：輸入、敵人 AI、傷害、異常狀態、勝利結算。</summary>
public partial class Game
{
    static readonly Dictionary<string, string> StatusMsg = new()
    {
        ["burn"] = "被炎上了！", ["silence"] = "被 sage 了！（無法使用技能）", ["confuse"] = "被釣了！（混亂）", ["sleep"] = "開始潛水了……（睡眠）",
        ["atkUp"] = "攻擊力提升了！", ["defUp"] = "防禦力提升了！", ["atkDown"] = "攻擊力下降了！", ["defDown"] = "防禦力下降了！",
        ["taunt"] = "開始挑釁敵人！", ["counter"] = "拋出了誘餌！", ["hidden"] = "變成了 404 狀態！",
    };
    static readonly string[] BadStatus = { "burn", "silence", "confuse", "sleep" };

    List<Actor> AliveParty() => Party.Where(a => a.Alive).ToList();
    List<Enemy> AliveEnemies() => Battle!.Enemies.Where(e => e.Alive).ToList();
    List<Unit> OppOf(Unit u) => u.IsEnemy ? AliveParty().Cast<Unit>().ToList() : AliveEnemies().Cast<Unit>().ToList();
    List<Unit> SideOf(Unit u) => u.IsEnemy ? AliveEnemies().Cast<Unit>().ToList() : AliveParty().Cast<Unit>().ToList();
    List<string> BattleItems() => InvList((it, iid0) => it.Type == "use");

    Enemy NewEnemy(string id, string label)
    {
        var def = D.Enemies[id];
        // 簡單模式：敵人 HP 較少
        var hp = Easy ? Math.Max(1, (int)Math.Round(def.Hp * EasyEnemyHp, MidpointRounding.AwayFromZero)) : def.Hp;
        return new Enemy { Uid = Guid.NewGuid().ToString("N"), Id = id, Def = def, Name = def.Name + label, Hp = hp, MaxHp = hp };
    }

    async Task Msg(string text, int ms = 380)
    {
        var b = Battle;
        if (b == null) return;
        b.Log.Add(text);
        if (b.Log.Count > 4) b.Log.RemoveAt(0);
        Render();
        await BWait(ms);
    }

    async Task Flash(Unit u, string cls, int ms = 260)
    {
        u.Fx = cls;
        Render();
        await BWait(ms);
        u.Fx = "";
    }

    void AddGauge(int n)
    {
        if (Battle != null) Battle.Gauge = Math.Min(100, Battle.Gauge + n);
    }

    /// <summary>戰鬥單位在畫面上的識別碼（給傷害數字定位用）。</summary>
    public static string UnitKey(Unit u) => u is Enemy e ? e.Uid : "p-" + ((Actor)u).Id;

    void ShowPopup(Unit u, string text, string cls)
    {
        var p = new Popup { Id = ++popupSeq, Key = UnitKey(u), Text = text, Cls = cls };
        Popups.Add(p);
        _ = RemovePopupLater(p);
    }

    async Task RemovePopupLater(Popup p)
    {
        await Task.Delay(900);
        Popups.Remove(p);
        Render();
    }

    static bool OptBool(JsonElement o, string key) =>
        o.ValueKind == JsonValueKind.Object && o.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.True;

    static string? OptStr(JsonElement o, string key) =>
        o.ValueKind == JsonValueKind.Object && o.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

    async Task<string> RunBattle(string troopId, JsonElement opts)
    {
        var ids = D.Troops[troopId];
        var counts = ids.GroupBy(x => x).ToDictionary(g => g.Key, g => g.Count());
        var seen = new Dictionary<string, int>();
        var enemies = new List<Enemy>();
        foreach (var id in ids)
        {
            seen[id] = seen.GetValueOrDefault(id) + 1;
            enemies.Add(NewEnemy(id, counts[id] > 1 ? " " + "ABCD"[seen[id] - 1] : ""));
        }
        var b = Battle = new BattleState
        {
            Enemies = enemies,
            Bg = CurMap.Bg,
            FromMon = OptBool(opts, "mon"),
            NoFlee = OptBool(opts, "noFlee") || enemies.Any(e => e.Def.Boss),
        };
        foreach (var en in enemies) DexOf(en.Id).Seen = true;
        foreach (var a in Party) { a.St = new(); a.Guard = false; a.Fx = ""; }
        Mode = "battle";
        Busy = true;
        Banner = null;
        Render();
        await Msg(string.Join("、", ids.Distinct().Select(id => D.Enemies[id].Name)) + "出現在串裡了！", 650);
        b.Intro = false;
        var buff = OptStr(opts, "partyBuff");
        if (buff != null)
        {
            foreach (var a in AliveParty()) a.St[buff] = 99;
            await Msg("全隊的攻擊力大幅提升了！");
        }

        string? result = null;
        while (result == null)
        {
            b.Turn++;
            b.ComboQueued = false;
            var input = await PartyInput();
            List<BattleAction> acts;
            if (input == null)
            {
                var ap = AliveParty();
                var ae = AliveEnemies();
                var ps = ap.Average(a => UStat(a, "spd"));
                var es = ae.Average(e => (double)e.Def.Spd);
                if (Easy || R.NextDouble() < Math.Clamp(0.55 + (ps - es) * 0.02, 0.3, 0.9))
                {
                    await Msg("發動島民技能「無視」，成功離開了這串！");
                    result = "flee";
                    break;
                }
                await Msg("無視失敗！被拉回串裡了！");
                acts = new List<BattleAction>();
            }
            else acts = input;

            foreach (var act in acts)
                act.Pri = act.Type == "combo" ? 2e4 : act.Type == "defend" ? 1e4 : UStat(act.U, "spd") * (0.75 + R.NextDouble() * 0.5);
            foreach (var e in AliveEnemies())
            {
                var act = EnemyAction(e);
                act.Pri = (D.Skills[act.Skill!].First ? 5000 : 0) + e.Def.Spd * (0.75 + R.NextDouble() * 0.5);
                acts.Add(act);
            }
            acts.Sort((x, y) => y.Pri.CompareTo(x.Pri));
            foreach (var act in acts)
            {
                if (!act.U.Alive) continue;
                await ExecAction(act);
                result = CheckEnd();
                if (result == "lose" && Auto) { await AutoRevive(); result = null; }
                if (result != null) break;
            }
            if (result == null)
            {
                await EndOfRound();
                result = CheckEnd();
                if (result == "lose" && Auto) result = null;
            }
            if (result == null && Auto) await AutoRevive();
        }
        if (Auto)
            foreach (var a in Party)
                if (a.Hp <= 0) { a.Hp = MaxHp(a); a.Mp = MaxMp(a); }

        if (result == "win") await Victory();
        else if (result == "lose") await Msg("全隊倒下了……", 1100);
        foreach (var a in Party) { a.St = new(); a.Guard = false; }
        Battle = null;
        Mode = "map";
        Render();
        return result;
    }

    string? CheckEnd()
    {
        var b = Battle!;
        if (b.Enemies.Any(e => e.Alive && e.Def.YieldAt > 0 && e.Hp <= e.MaxHp * e.Def.YieldAt)) return "win";
        if (AliveEnemies().Count == 0) return "win";
        if (AliveParty().Count == 0) return "lose";
        return null;
    }

    async Task Victory()
    {
        var b = Battle!;
        // 地圖上的怪物可以躲開，打到的那幾場給比較多；簡單模式再多一些
        var mul = (b.FromMon ? MonReward : 1.0) * (Easy ? EasyReward : 1.0);
        var exp = (int)Math.Round(b.Enemies.Sum(e => e.Def.Exp) * mul, MidpointRounding.AwayFromZero);
        var gold = (int)Math.Round(b.Enemies.Sum(e => e.Def.Gold) * mul, MidpointRounding.AwayFromZero);
        foreach (var e in b.Enemies)
            if (e.Hp <= 0) DexOf(e.Id).Killed++;
        await Msg("戰鬥勝利！大家辛苦乙！", 500);
        if (exp > 0 || gold > 0) await Msg($"獲得 {exp} 經驗值、{gold} K 幣。", 500);
        Gold += gold;
        foreach (var a in AliveParty())
            foreach (var line in GainExp(a, exp)) await Msg(line, 650);
        foreach (var e in b.Enemies)
            foreach (var (item, chance) in e.Def.DropList)
                if (e.Hp <= 0 && R.NextDouble() * 100 < chance)
                {
                    AddItem(item);
                    await Msg($"{e.Def.Name}掉落了【{D.Items[item].Name}】！", 550);
                }
        b.Done = true;
        await WaitOk();
    }

    // ---------------------------------------------------------------- 玩家輸入
    async Task<List<BattleAction>?> PartyInput()
    {
        var b = Battle!;
        var members = AliveParty();
        var acts = new BattleAction?[members.Count];
        var i = 0;
        while (i < members.Count)
        {
            var a = members[i];
            if (a.St.ContainsKey("sleep") || a.St.ContainsKey("confuse"))
            {
                acts[i] = new BattleAction { Type = "auto", U = a };
                i++;
                continue;
            }
            b.ActorIndex = Party.IndexOf(a);
            Render();
            var r = Auto ? await AutoCommand(a) : await CommandFor(a, i > 0);
            if (r.Back)
            {
                acts[i] = null;
                i--;
                while (i > 0 && acts[i] is { Type: "auto" }) i--;
                i = Math.Max(0, i);
                continue;
            }
            if (r.Flee)
            {
                b.ActorIndex = -1;
                return null;
            }
            if (r.AutoAll)
            {
                for (var j = i; j < members.Count; j++)
                {
                    var m = members[j];
                    acts[j] = m.St.ContainsKey("sleep") || m.St.ContainsKey("confuse")
                        ? new BattleAction { Type = "auto", U = m }
                        : new BattleAction { Type = "attack", U = m };
                }
                break;
            }
            acts[i] = r;
            i++;
        }
        b.ActorIndex = -1;
        b.Hi = null;
        return acts.Where(x => x != null).Select(x => x!).ToList();
    }

    Task<BattleAction> CommandFor(Actor a, bool canBack)
    {
        var b = Battle!;
        var tcs = new TaskCompletionSource<BattleAction>(TaskCreationOptions.RunContinuationsAsynchronously);

        void Done(BattleAction r)
        {
            Menus.Clear();
            b.Hi = null;
            Render();
            tcs.TrySetResult(r);
        }

        void PickTarget(string kind, Action<Unit?> after, string vk = "hp")
        {
            List<Unit> list;
            if (kind == "enemy") list = AliveEnemies().Cast<Unit>().ToList();
            else if (kind == "ally") list = AliveParty().Cast<Unit>().ToList();
            else if (kind == "deadAlly") list = Party.Where(x => x.Hp <= 0).Cast<Unit>().ToList();
            else { after(null); return; }
            if (list.Count == 0) { ShowToast("沒有可以選擇的對象"); return; }
            PushMenu(new Menu
            {
                Cls = "battle",
                Title = "選擇對象",
                Build = () => list.Select(t => new MenuItem { Label = UName(t), Right = t is Actor ac ? VitalText(ac, vk, true) : KnownText(((Enemy)t).Id) }).ToList(),
                OnMove = j => b.Hi = list[j],
                OnBack = () => { b.Hi = null; PopMenu(); },
                OnPick = (j, mi) => after(list[j]),
            });
            b.Hi = list[0];
            Render();
        }

        PushMenu(new Menu
        {
            Cls = "battle",
            Title = Ad(a).Name,
            Build = () =>
            {
                var list = new List<MenuItem>();
                if (b.Gauge >= 100 && !b.ComboQueued) list.Add(new MenuItem { Label = "★ 合體技", Right = "推 MAX", Cmd = "combo" });
                list.Add(new MenuItem { Label = "攻擊", Cmd = "attack" });
                list.Add(new MenuItem { Label = "技能", Disabled = a.St.ContainsKey("silence"), Right = a.St.ContainsKey("silence") ? "sage" : null, Cmd = "skill" });
                list.Add(new MenuItem { Label = "道具", Disabled = BattleItems().Count == 0, Cmd = "item" });
                list.Add(new MenuItem { Label = "防禦", Cmd = "defend" });
                list.Add(new MenuItem { Label = "自動", Right = "全員攻擊", Cmd = "auto" });
                list.Add(new MenuItem { Label = "無視", Disabled = b.NoFlee, Cmd = "flee" });
                return list;
            },
            OnBack = () => { if (canBack) Done(new BattleAction { Back = true, U = a }); },
            OnPick = (i0, mi) =>
            {
                var i = mi.Cmd switch { "attack" => 0, "skill" => 1, "item" => 2, "defend" => 3, "flee" => 4, "combo" => 5, _ => 6 };
                if (i == 5)
                {
                    PushMenu(new Menu
                    {
                        Cls = "battle wide",
                        Title = "合體技",
                        Build = () => D.Combos.Select(kv => new MenuItem { Label = kv.Value.Name, Desc = kv.Value.Desc, Id = kv.Key }).ToList(),
                        OnPick = (j, it) => { b.ComboQueued = true; Done(new BattleAction { Type = "combo", U = a, Combo = it.Id }); },
                    });
                    return;
                }
                if (i == 6) { Done(new BattleAction { AutoAll = true, U = a }); return; }
                if (i == 0) PickTarget("enemy", t => Done(new BattleAction { Type = "attack", U = a, T = t }));
                else if (i == 1)
                {
                    PushMenu(new Menu
                    {
                        Cls = "battle wide",
                        Title = "技能",
                        Build = () => SkillsOf(a).Select(id => new MenuItem
                        {
                            Label = D.Skills[id].Name, Right = "MP " + D.Skills[id].Mp, Disabled = a.Mp < D.Skills[id].Mp, Desc = D.Skills[id].Desc, Id = id,
                        }).ToList(),
                        OnPick = (j, it) =>
                        {
                            var sk = D.Skills[it.Id!];
                            PickTarget(sk.Target, t => Done(new BattleAction { Type = "skill", U = a, Skill = it.Id, T = t }));
                        },
                    });
                }
                else if (i == 2)
                {
                    PushMenu(new Menu
                    {
                        Cls = "battle wide",
                        Title = "道具",
                        Build = () => BattleItems().Select(id => new MenuItem { Label = D.Items[id].Name, Right = "×" + Inv[id], Desc = D.Items[id].Desc, Id = id }).ToList(),
                        OnPick = (j, it) =>
                        {
                            var item = D.Items[it.Id!];
                            var kind = item.Target == "ally" ? "ally" : item.Target == "deadAlly" ? "deadAlly" : "";
                            PickTarget(kind, t => Done(new BattleAction { Type = "item", U = a, Item = it.Id, T = t }), VitalKind(item));
                        },
                    });
                }
                else if (i == 3) Done(new BattleAction { Type = "defend", U = a });
                else Done(new BattleAction { Flee = true, U = a });
            },
        });
        return tcs.Task;
    }

    // ---------------------------------------------------------------- 敵人 AI
    BattleAction EnemyAction(Enemy e)
    {
        var ai = e.Def.Ai;
        if (e.St.ContainsKey("silence")) return new BattleAction { Type = "skill", U = e, Skill = "e_attack" };
        if (ai.LowSkill != null && !e.LowUsed && e.Hp <= e.MaxHp * ai.LowAt)
        {
            e.LowUsed = true;
            return new BattleAction { Type = "skill", U = e, Skill = ai.LowSkill, Warn = ai.LowWarn };
        }
        if (ai.EverySkill != null && ai.EveryN > 0 && Battle!.Turn % ai.EveryN == 0)
            return new BattleAction { Type = "skill", U = e, Skill = ai.EverySkill };
        var total = ai.PatternList.Sum(p => p.Weight);
        var r = R.NextDouble() * total;
        foreach (var (sk, w) in ai.PatternList)
        {
            r -= w;
            if (r < 0) return new BattleAction { Type = "skill", U = e, Skill = sk };
        }
        return new BattleAction { Type = "skill", U = e, Skill = ai.PatternList[0].Skill };
    }

    Unit PickOne(Unit u, List<Unit> list)
    {
        if (u.IsEnemy)
        {
            var taunters = list.Where(t => t.St.ContainsKey("taunt")).ToList();
            if (taunters.Count > 0 && R.NextDouble() < 0.75) return taunters[R.Next(taunters.Count)];
        }
        return list[R.Next(list.Count)];
    }

    // ---------------------------------------------------------------- 行動執行
    async Task ExecAction(BattleAction act)
    {
        var u = act.U;
        if (act.Type == "defend")
        {
            u.Guard = true;
            AddGauge(D.Gauge.Defend);
            await Msg($"{UName(u)}擺出了防禦姿勢。", 300);
            return;
        }
        if (act.Type == "combo")
        {
            await DoCombo(act.Combo!);
            return;
        }
        if (u.St.ContainsKey("sleep")) { await Msg($"{UName(u)}正在潛水……（睡眠中）"); return; }
        if (u.St.ContainsKey("confuse"))
        {
            var pool = AliveParty().Cast<Unit>().Concat(AliveEnemies()).Where(x => x != u).ToList();
            await Msg($"{UName(u)}被釣了，胡亂攻擊！");
            if (pool.Count > 0) await HitPhys(u, pool[R.Next(pool.Count)], 1, "phys");
            return;
        }
        if (act.Type == "auto") act.Type = "attack";
        if (act.Warn != null) await Msg(act.Warn, 600);

        if (act.Type == "attack")
        {
            var t = act.T;
            if (t == null || !t.Alive)
            {
                var o = OppOf(u);
                if (o.Count == 0) return;
                t = PickOne(u, o);
            }
            await Msg($"{UName(u)}的攻擊！", 300);
            await HitPhys(u, t, 1, "phys");
            return;
        }

        if (act.Type == "item")
        {
            var id = act.Item!;
            if (ItemCount(id) <= 0) { await Msg("道具已經用完了！"); return; }
            var it = D.Items[id];
            RemoveItem(id);
            await Msg($"{UName(u)}使用了【{it.Name}】！", 350);
            if (it.Damage > 0)
            {
                foreach (var t in AliveEnemies())
                {
                    var dmg = (int)Math.Round(it.Damage * ElemMult(t, it.Elem) * Var());
                    await ApplyDamage(u, t, dmg, ElemNote(t, it.Elem), it.Elem);
                }
                return;
            }
            List<Unit> targets;
            if (it.Target == "allies") targets = AliveParty().Cast<Unit>().ToList();
            else if (it.Target == "ally" && (act.T == null || !act.T.Alive))
                targets = AliveParty().OrderBy(a => (double)a.Hp / MaxHp(a)).Take(1).Cast<Unit>().ToList();
            else targets = act.T != null ? new List<Unit> { act.T } : new List<Unit>();
            foreach (var m in ApplyItem(id, targets)) await Msg(m, 380);
            return;
        }

        // 技能
        var sk = D.Skills[act.Skill!];
        if (u is Actor actor)
        {
            if (actor.St.ContainsKey("silence")) { await Msg($"{UName(u)}被 sage 了，說不出咒語！"); return; }
            if (actor.Mp < sk.Mp) { await Msg($"{UName(u)}的 MP 不足！"); return; }
            actor.Mp -= sk.Mp;
        }
        if (sk.Name != "攻擊") await Msg($"{UName(u)}使用了「{sk.Name}」！", 380);
        else await Msg($"{UName(u)}的攻擊！", 300);
        await DoSkill(u, sk, act.T);
    }

    static string ElemNote(Unit t, string? elem)
    {
        var m = ElemMult(t, elem);
        return m > 1 ? "效果拔群！" : m < 1 ? "被無視了，效果不太好……" : "";
    }

    async Task HitPhys(Unit u, Unit t, double power, string elem)
    {
        if (R.NextDouble() < 0.04) { await Msg("但是沒打中！"); return; }
        if (t.St.ContainsKey("hidden") && elem != "holy" && R.NextDouble() < 0.75) { await Msg("404 Not Found——攻擊撲空了！"); return; }
        var dmg = PhysDamage(u, t, power) * ElemMult(t, elem);
        var note = ElemNote(t, elem);
        if (!u.IsEnemy && R.NextDouble() < 0.06) { dmg *= 1.5; note = "神回！" + note; }
        await ApplyDamage(u, t, (int)Math.Round(dmg), note, elem);
        if (t.Alive && u.Alive && t.St.ContainsKey("counter") && t.IsEnemy != u.IsEnemy)
        {
            var c = (int)Math.Round(PhysDamage(t, u, 1.5));
            await Msg($"上鉤了！{UName(t)}的反擊！", 350);
            await ApplyDamage(t, u, c, "", null);
        }
    }

    async Task DoCombo(string id)
    {
        var b = Battle!;
        var c = D.Combos[id];
        b.Gauge = 0;
        await Msg($"合體技！全員一起推——「{c.Name}」！", 700);
        if (c.Kind == "damage")
        {
            var power = AliveParty().Sum(p => UStat(p, "atk") * c.Atk + UStat(p, "mag") * c.Mag);
            foreach (var t in AliveEnemies())
            {
                var dmg = (int)Math.Round(Math.Max(1, power - UStat(t, "def") * 0.5) * (0.95 + R.NextDouble() * 0.1) * ElemMult(t, c.Elem));
                await ApplyDamage(null, t, dmg, ElemNote(t, c.Elem), c.Elem);
            }
            return;
        }
        foreach (var a in Party)
        {
            if (a.Hp <= 0)
            {
                a.Hp = MaxHp(a) * 3 / 10;
                a.St.Clear();
                await Msg($"{Ad(a).Name}復活了！", 300);
            }
            else
            {
                var h = Math.Min(MaxHp(a) * 6 / 10, MaxHp(a) - a.Hp);
                a.Hp += h;
                foreach (var k in BadStatus) a.St.Remove(k);
                ShowPopup(a, "+" + h, "heal");
            }
            if (a.Hp > 0)
            {
                a.St["atkUp"] = Math.Max(a.St.GetValueOrDefault("atkUp"), 3);
                a.St["defUp"] = Math.Max(a.St.GetValueOrDefault("defUp"), 3);
            }
        }
        await Msg("全隊回復了！攻擊力與防禦力提升了！", 600);
    }

    async Task ApplyDamage(Unit? u, Unit t, int dmg, string note, string? elem)
    {
        if (Easy && !t.IsEnemy) dmg = (int)Math.Round(dmg * EasyDmgTaken, MidpointRounding.AwayFromZero);  // 簡單模式：我方受到的傷害較少
        if (t.Guard) dmg = (int)Math.Round(dmg * 0.5);
        dmg = Math.Max(1, dmg);
        t.Hp = Math.Max(0, t.Hp - dmg);
        var mult = ElemMult(t, elem);
        if (t is Enemy te0)
        {
            if (u != null && !u.IsEnemy)
                AddGauge(D.Gauge.Hit + (note.Contains("拔群") ? D.Gauge.Weak : 0) + (note.Contains("神回") ? D.Gauge.Crit : 0));
            var d = DexOf(te0.Id);
            if (elem != null && mult > 1 && !d.Weak.Contains(elem))
            {
                d.Weak.Add(elem);
                note += "（發現弱點：" + ElemName.GetValueOrDefault(elem, elem) + "）";
            }
            if (elem != null && mult < 1 && !d.Resist.Contains(elem)) d.Resist.Add(elem);
        }
        else
        {
            AddGauge(D.Gauge.Hurt);
            if (t.Hp <= 0) AddGauge(D.Gauge.Ko);
        }
        ShowPopup(t, dmg.ToString(), mult > 1 ? "weak" : t.IsEnemy ? "" : "hurt");
        if (elem == "holy" && t.St.Remove("hidden")) note += "（404 被解除了！）";
        await Flash(t, "hit");
        await Msg($"{(note.Length > 0 ? note + " " : "")}{UName(t)}受到 {dmg} 點傷害。", 380);
        if (t.St.ContainsKey("sleep") && t.Hp > 0)
        {
            t.St.Remove("sleep");
            await Msg($"{UName(t)}從潛水中醒來了！", 300);
        }
        if (t.Hp <= 0) await Msg(t.IsEnemy ? $"{UName(t)}倒下了！" : $"{UName(t)}倒下了……", 420);
    }

    List<Unit> ResolveTargets(Unit u, SkillDef sk, Unit? chosen)
    {
        switch (sk.Target)
        {
            case "enemy":
            {
                var o = OppOf(u);
                if (chosen != null && chosen.Alive && o.Contains(chosen)) return new List<Unit> { chosen };
                return o.Count > 0 ? new List<Unit> { PickOne(u, o) } : new List<Unit>();
            }
            case "enemies": return OppOf(u);
            case "ally":
            {
                if (chosen != null && chosen.Alive) return new List<Unit> { chosen };
                return SideOf(u).OrderBy(x => (double)x.Hp / UMaxHp(x)).Take(1).ToList();
            }
            case "allies": return SideOf(u);
            case "self": return new List<Unit> { u };
            case "deadAlly":
                if (chosen != null && !chosen.Alive) return new List<Unit> { chosen };
                return u.IsEnemy ? new List<Unit>() : Party.Where(a => !a.Alive).Take(1).Cast<Unit>().ToList();
            default: return new List<Unit>();
        }
    }

    async Task AddStatus(Unit t, string? st, double? chance, int? turns, bool quietMiss)
    {
        if (st == null || !t.Alive) return;
        var immune = t is Enemy e ? e.Def.Immune ?? new List<string>() : ImmunesOf((Actor)t);
        var bossResist = t is Enemy be && be.Def.Boss && st == "confuse" && R.NextDouble() < 0.5;
        if (immune.Contains(st) || bossResist)
        {
            if (!quietMiss) await Msg($"{UName(t)}沒有受到影響。", 320);
            return;
        }
        if (R.NextDouble() * 100 >= (chance ?? 100))
        {
            if (!quietMiss) await Msg($"{UName(t)}沒有中招。", 320);
            return;
        }
        t.St[st] = Math.Max(t.St.GetValueOrDefault(st), turns ?? 3);
        await Msg($"{UName(t)}{StatusMsg.GetValueOrDefault(st, "")}", 380);
    }

    async Task DoSkill(Unit u, SkillDef sk, Unit? chosen)
    {
        var b = Battle!;
        if (sk.Kind == "special")
        {
            if (sk.Fx == "summon")
            {
                if (AliveEnemies().Count >= 3) { await Msg("……但是沒有空間分裂了。"); return; }
                var ne = NewEnemy(sk.Summon!, " " + "XYZ"[R.Next(3)]);
                b.Enemies.Add(ne);
                await Msg($"{ne.Name}也跑來回文了！");
                return;
            }
            if (sk.Fx == "healself" && u is Enemy self)
            {
                var h = (int)Math.Floor(self.MaxHp * sk.Rate);
                self.Hp = Math.Min(self.MaxHp, self.Hp + h);
                await Flash(u, "heal");
                await Msg($"{UName(u)}回復了 {h} HP！");
                return;
            }
            if (sk.Fx == "explode")
            {
                foreach (var t in AliveParty())
                {
                    var dmg = (int)Math.Round(Math.Max(1, sk.Base * Var() - UStat(t, "def") * 0.25));
                    await ApplyDamage(u, t, dmg, "", null);
                }
                u.Hp = 0;
                await Msg($"{UName(u)}炸成了碎片！");
                return;
            }
        }

        if (sk.Target == "random3")
        {
            for (var h = 0; h < 3; h++)
            {
                var o = OppOf(u);
                if (o.Count == 0) break;
                await HitPhys(u, o[R.Next(o.Count)], sk.Power, sk.Elem ?? "phys");
            }
            return;
        }

        var targets = ResolveTargets(u, sk, chosen);
        if (targets.Count == 0) { await Msg("但是沒有效果。"); return; }
        foreach (var t in targets)
        {
            if (!t.Alive && sk.Kind != "revive" && !sk.Revive) continue;
            switch (sk.Kind)
            {
                case "phys":
                    await HitPhys(u, t, sk.Power, sk.Elem ?? "phys");
                    if (sk.Fx == "delete" && t.Alive && t is Enemy te && !te.Def.Boss && te.Hp <= te.MaxHp * 0.3)
                    {
                        te.Hp = 0;
                        await Flash(te, "hit");
                        await Msg($"{UName(te)}被刪除了！");
                    }
                    if (sk.Fx == "drain" && u.Alive)
                    {
                        var h = (int)Math.Round(UStat(u, "atk") * 0.4);
                        u.Hp = Math.Min(UMaxHp(u), u.Hp + h);
                    }
                    if (sk.Status != null) await AddStatus(t, sk.Status, sk.Chance, sk.Turns, true);
                    break;
                case "mag":
                {
                    if (t.St.ContainsKey("hidden") && sk.Elem != "holy" && R.NextDouble() < 0.75) { await Msg("404 Not Found——魔法撲空了！"); break; }
                    var dmg = (int)Math.Round(MagDamage(u, t, sk) * ElemMult(t, sk.Elem));
                    await ApplyDamage(u, t, dmg, ElemNote(t, sk.Elem), sk.Elem);
                    if (sk.Status != null) await AddStatus(t, sk.Status, sk.Chance, sk.Turns, true);
                    break;
                }
                case "heal":
                {
                    if (!t.Alive && sk.Revive)
                    {
                        t.Hp = Math.Max(1, UMaxHp(t) / 2);
                        t.St.Clear();
                        await Msg($"{UName(t)}復活了！");
                        break;
                    }
                    var h = Math.Min(HealAmount(u, sk), UMaxHp(t) - t.Hp);
                    t.Hp += h;
                    ShowPopup(t, "+" + h, "heal");
                    await Flash(t, "heal", 200);
                    await Msg($"{UName(t)}回復了 {h} HP。", 330);
                    break;
                }
                case "revive":
                    if (t.Alive) { await Msg($"{UName(t)}沒有倒下。"); break; }
                    t.Hp = Math.Max(1, (int)Math.Floor(UMaxHp(t) * (sk.Rate > 0 ? sk.Rate : 0.5)));
                    t.St.Clear();
                    await Flash(t, "heal");
                    await Msg($"{UName(t)}被推回來了！復活了！");
                    break;
                case "buff":
                    await AddStatus(t, sk.Status, 100, sk.Turns, true);
                    if (sk.Status2 != null) await AddStatus(t, sk.Status2, 100, sk.Turns, true);
                    break;
                case "debuff":
                    await AddStatus(t, sk.Status, sk.Chance, sk.Turns, false);
                    if (sk.Status2 != null) await AddStatus(t, sk.Status2, sk.Chance2, sk.Turns, true);
                    break;
                case "cure":
                    foreach (var k in BadStatus) t.St.Remove(k);
                    await Msg($"{UName(t)}冷靜下來了。", 300);
                    break;
            }
        }
    }

    async Task EndOfRound()
    {
        var b = Battle!;
        var units = AliveParty().Cast<Unit>().Concat(AliveEnemies()).ToList();
        foreach (var u in units)
        {
            u.Guard = false;
            if (u.St.ContainsKey("burn"))
            {
                var d = u is Enemy e ? Math.Min(e.MaxHp / 20, 90) : (int)Math.Floor(MaxHp((Actor)u) * 0.06 * (Easy ? EasyDmgTaken : 1));
                d = Math.Max(1, d);
                u.Hp = Math.Max(0, u.Hp - d);
                await Flash(u, "hit", 160);
                await Msg($"{UName(u)}因為炎上受到 {d} 點傷害。", 360);
                if (u.Hp <= 0) await Msg($"{UName(u)}倒下了……");
            }
            foreach (var k in u.St.Keys.ToList())
            {
                if (k == "confuse" && R.NextDouble() < 0.3) u.St[k] = 1;
                u.St[k]--;
                if (u.St[k] <= 0)
                {
                    u.St.Remove(k);
                    if (u.Alive)
                    {
                        string? endMsg = k switch { "silence" => "又可以說話了。", "confuse" => "清醒過來了。", "sleep" => "浮上來了。", _ => null };
                        if (endMsg != null) await Msg(UName(u) + endMsg, 320);
                    }
                }
            }
        }
        foreach (var e in AliveEnemies())
        {
            var ai = e.Def.Ai;
            if (ai.EveryN > 0 && ai.EveryWarn != null && (b.Turn + 1) % ai.EveryN == 0) await Msg(ai.EveryWarn, 750);
        }
    }
}
