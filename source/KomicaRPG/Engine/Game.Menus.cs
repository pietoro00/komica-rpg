namespace KomicaRPG.Engine;

/// <summary>地圖上的選單：道具、技能、裝備、狀態、任務、存檔，以及商店。</summary>
public partial class Game
{
    public static readonly Dictionary<string, string> StatName = new()
    {
        ["atk"] = "攻", ["def"] = "防", ["mag"] = "魔", ["spd"] = "速", ["hp"] = "HP", ["mp"] = "MP",
    };
    public static readonly Dictionary<string, string> SlotName = new() { ["weapon"] = "武器", ["armor"] = "防具", ["acc"] = "飾品" };
    static readonly string[] Slots = { "weapon", "armor", "acc" };

    static string? SlotOf(ItemDef it) => it.Type switch { "weapon" => "weapon", "armor" => "armor", "acc" => "acc", _ => null };

    // 選對象時右欄顯示的數值：回復 MP 的道具顯示 MP，兩者都回復就都顯示
    static string VitalKind(ItemDef? it) => it != null && it.Mp > 0 ? (it.Heal > 0 ? "both" : "mp") : "hp";
    string VitalText(Actor a, string kind, bool shortForm = false)
    {
        var hp = $"{a.Hp}/{MaxHp(a)}";
        var mp = $"MP {a.Mp}/{MaxMp(a)}";
        if (kind == "mp") return mp;
        if (kind == "both") return $"HP {hp} {mp}";
        return shortForm ? hp : "HP " + hp;
    }

    void PartyPicker(string title, Action<Actor> onPick, Func<Actor, bool>? filter = null, string kind = "hp")
    {
        PushMenu(new Menu
        {
            Title = title,
            Build = () => Party.Select(a => new MenuItem
            {
                Label = $"{Ad(a).Name}　Lv {a.Level}",
                Right = VitalText(a, kind),
                Disabled = filter != null && !filter(a),
            }).ToList(),
            OnPick = (i, mi0) => onPick(Party[i]),
        });
    }

    public string ItemDesc(string id)
    {
        var it = D.Items[id];
        var s = it.Desc;
        var slot = SlotOf(it);
        if (slot != null)
        {
            var parts = Party.Where(a => CanEquip(a, id)).Select(a =>
            {
                var cur = a.Equip.GetValueOrDefault(slot);
                var diffs = new List<string>();
                foreach (var k in new[] { "atk", "def", "mag", "spd", "hp", "mp" })
                {
                    var d = it.StatOf(k) - (cur != null ? D.Items[cur].StatOf(k) : 0);
                    if (d != 0) diffs.Add($"{StatName[k]}{(d > 0 ? "+" : "")}{d}");
                }
                return $"{Ad(a).Name} {(diffs.Count > 0 ? string.Join(" ", diffs) : "±0")}";
            }).ToList();
            s += parts.Count > 0 ? "｜" + string.Join("／", parts) : "｜目前隊伍無人可裝備";
        }
        return s;
    }

    bool SkitSeen(SkitDef k) => Flags.GetValueOrDefault("skit:" + k.Id);
    List<SkitDef> SkitsAvail() => D.Skits.Where(k => Cond(k.Cond)).ToList();

    void OpenMainMenu()
    {
        PushMenu(new Menu
        {
            Cls = "main",
            Title = "選單",
            Build = () => new List<MenuItem>
            {
                new() { Label = "道具" }, new() { Label = "技能" }, new() { Label = "裝備" }, new() { Label = "狀態" },
                new() { Label = "雜談", Right = SkitsAvail().Any(k => !SkitSeen(k)) ? "NEW" : "", Disabled = SkitsAvail().Count == 0 },
                new() { Label = "圖鑑" }, new() { Label = "跳串", Right = "傳送" }, new() { Label = "任務" }, new() { Label = "設定" },
                new() { Label = "存檔" }, new() { Label = "關閉" },
            },
            OnPick = (i, mi0) =>
            {
                switch (i)
                {
                    case 0: MenuItemsField(); break;
                    case 1: MenuSkillsField(); break;
                    case 2: MenuEquip(); break;
                    case 3: MenuStatus(); break;
                    case 4: MenuSkits(); break;
                    case 5: MenuDex(); break;
                    case 6: MenuTravel(); break;
                    case 7: MenuQuests(); break;
                    case 8: MenuSettings(); break;
                    case 9: _ = SaveFromMenu(); break;
                    default: PopMenu(); break;
                }
            },
        });
    }

    void MenuSkits()
    {
        PushMenu(new Menu
        {
            Title = "隊伍雜談",
            Cls = "wide",
            Build = () => SkitsAvail().Select(k => new MenuItem { Label = k.Title, Right = SkitSeen(k) ? "" : "NEW", Id = k.Id }).ToList(),
            OnPick = (ix, it) =>
            {
                var k = D.Skits.First(x => x.Id == it.Id);
                Menus.Clear();
                Flags["skit:" + k.Id] = true;
                _ = RunBusy(k.Script);
            },
        });
    }

    public static readonly Dictionary<string, string> ElemName = new()
    {
        ["fire"] = "炎上", ["ice"] = "冷場", ["thunder"] = "暴雷", ["holy"] = "神串", ["dark"] = "黑歷史", ["phys"] = "物理",
    };

    DexEntry DexOf(string id)
    {
        if (!Dex.TryGetValue(id, out var d)) { d = new DexEntry(); Dex[id] = d; }
        return d;
    }

    public string KnownText(string id)
    {
        if (!Dex.TryGetValue(id, out var d)) return "";
        var w = string.Join("、", d.Weak.Select(e => ElemName.GetValueOrDefault(e, e)));
        var r = string.Join("、", d.Resist.Select(e => ElemName.GetValueOrDefault(e, e)));
        var parts = new List<string>();
        if (w.Length > 0) parts.Add("弱：" + w);
        if (r.Length > 0) parts.Add("抗：" + r);
        return string.Join("　", parts);
    }

    public bool DexSeen(string id) => Dex.TryGetValue(id, out var d) && d.Seen;

    void MenuDex()
    {
        var ids = D.Enemies.Keys.ToList();
        PushMenu(new Menu
        {
            Title = $"怪物圖鑑（{ids.Count(DexSeen)} / {ids.Count}）",
            Cls = "wide dex",
            Build = () => ids.Select(id =>
            {
                var e = D.Enemies[id];
                if (!DexSeen(id)) return new MenuItem { Label = "？？？", Id = id, Desc = "還沒有遇過。" };
                var known = KnownText(id);
                if (known.Length == 0) known = "弱點：？？？（用屬性攻擊打打看）";
                var killed = Dex[id].Killed;
                return new MenuItem
                {
                    Label = e.Name, Right = killed > 0 ? "打倒 " + killed : "", Id = id,
                    Desc = $"HP {e.Hp}　攻 {e.Atk}　防 {e.Def}　魔 {e.Mag}　速 {e.Spd}｜{known}｜{e.Desc}",
                };
            }).ToList(),
            OnPick = (ix, it) => { },
        });
    }

    void MenuTravel()
    {
        if (D.NoTravel.Contains(MapId)) { ShowToast("這裡的訊號太強，沒辦法跳串。"); return; }
        PushMenu(new Menu
        {
            Title = "跳串（傳送到去過的地方）",
            Cls = "wide",
            Build = () =>
            {
                var list = D.Travel.Where(t => Visited.GetValueOrDefault(t.Map) && Cond(t.Cond))
                    .Select(t => new MenuItem { Label = t.Name, Right = t.Map == MapId ? "現在位置" : "", Travel = t }).ToList();
                return list.Count > 0 ? list : new List<MenuItem> { new() { Label = "（還沒有可以傳送的地方）", Disabled = true } };
            },
            OnPick = (ix, it) =>
            {
                var t = it.Travel!;
                Menus.Clear();
                Teleport(t.Map, t.X, t.Y, t.Dir);
                _ = SaveGame();
                Render();
                _ = RunBusy(null);
            },
        });
    }

    void MenuSettings()
    {
        PushMenu(new Menu
        {
            Title = "設定",
            Cls = "wide",
            Build = () => new List<MenuItem>
            {
                new() { Label = "戰鬥速度", Right = BSpeedNames[bspeed], Desc = "按 Enter 切換。設定會記在這台裝置上。" },
                new() { Label = "難度", Right = Easy ? "簡單" : "普通", Desc = "按 Enter 切換，會跟著存檔記錄。簡單：敵人比較弱、受到的傷害較少、經驗值與 K 幣 1.5 倍、「無視」一定成功、怪物比較少也不太追人。" },
                new() { Label = "全自動模式", Right = Auto ? "開" : "關", Desc = "開啟後由電腦幫你玩：自動走路、找人說話、做主線和支線、戰鬥、買裝備換裝備，一路玩到結局。難度會自動改成「簡單」，戰鬥中倒下會自動復活並補滿 HP／MP。按「選單」可以暫停，點畫面左上角的 AUTO 可以關掉。" },
                new() { Label = "自動速度", Right = AutoSpeedNames[autoSpeed], Desc = "全自動模式的走路與對話速度。按 Enter 切換。" },
                new() { Label = "返回" },
            },
            OnPick = (i, mi0) =>
            {
                if (i == 4) { PopMenu(); return; }
                if (i == 2) { SetAuto(!Auto); if (Auto) Menus.Clear(); Render(); return; }
                if (i == 3) { autoSpeed = (autoSpeed + 1) % AutoSpeeds.Length; _ = SaveSpeed(); Render(); return; }
                if (i == 1)
                {
                    Easy = !Easy;
                    ShowToast(Easy ? "難度改為「簡單」" : "難度改為「普通」");
                    Render();
                    return;
                }
                bspeed = (bspeed + 1) % BSpeeds.Length;
                _ = SaveSpeed();
                Render();
            },
        });
    }

    async Task SaveSpeed()
    {
        var meta = await LoadMeta();
        meta.Speed = bspeed;
        meta.AutoSpeed = autoSpeed;
        try { await storageSet(MetaKey, System.Text.Json.JsonSerializer.Serialize(meta, SaveJson)); } catch { /* 無法存也沒關係 */ }
    }

    // ---------------------------------------------------------------- 討論板、章節卡
    public static string HashId(string str)
    {
        uint h = 2166136261;
        foreach (var ch in str)
        {
            h ^= ch;
            h *= 16777619;
        }
        const string digits = "0123456789abcdefghijklmnopqrstuvwxyz";
        var sb = new System.Text.StringBuilder();
        var v = h;
        do { sb.Insert(0, digits[(int)(v % 36)]); v /= 36; } while (v > 0);
        return sb.ToString().PadLeft(7, '0');
    }

    public static int PostNo(string id, int i) => 100000 + HashId(id)[0] * 731 + i * 37;
    public static string PostText(string id, string text) =>
        System.Text.RegularExpressions.Regex.Replace(text, @"\{no:(\d+)\}", m => PostNo(id, int.Parse(m.Groups[1].Value)).ToString());

    public List<(int Index, PostDef Post)> BoardPosts(string id) =>
        D.Boards[id].Posts.Select((p, i) => (i, p)).Where(x => Cond(x.p.Cond)).Select(x => (x.i, x.p)).ToList();

    Task OpenBoard(string id)
    {
        var b = new BoardState { Id = id };
        Board = b;
        Render();
        return b.Tcs.Task;
    }

    void CloseBoard()
    {
        var b = Board;
        Board = null;
        Render();
        b?.Tcs.TrySetResult();
    }

    void BoardKey(string btn)
    {
        var b = Board!;
        var n = BoardPosts(b.Id).Count;
        if (btn == "up") b.Top = Math.Max(0, b.Top - 1);
        else if (btn == "down") b.Top = Math.Min(n - 1, b.Top + 1);
        else if (btn is "ok" or "back" or "menu") { CloseBoard(); return; }
        Render();
    }

    Task ShowCard(string label, string title, string sub)
    {
        var card = new CardState { Label = label, Title = title, Sub = sub };
        Card = card;
        Render();
        _ = CloseCardLater(card);
        return card.Tcs.Task;
    }

    async Task CloseCardLater(CardState card)
    {
        await Task.Delay(3200);
        CloseCard(card);
    }

    void CloseCard(CardState card)
    {
        if (Card != card) return;
        Card = null;
        Render();
        card.Tcs.TrySetResult();
    }

    async Task SaveFromMenu() => ShowToast(await SaveGame() ? "已存檔。這串不會沉了。" : "無法存檔");

    void MenuItemsField()
    {
        PushMenu(new Menu
        {
            Title = "道具",
            Cls = "wide",
            Build = () =>
            {
                var ids = InvList((it, iid0) => it.Type is "use" or "key");
                if (ids.Count == 0) return new List<MenuItem> { new() { Label = "（什麼都沒有）", Disabled = true } };
                return ids.Select(id => new MenuItem
                {
                    Label = D.Items[id].Name, Right = "×" + Inv[id], Desc = D.Items[id].Desc, Id = id,
                    Disabled = D.Items[id].Type != "use" || D.Items[id].BattleOnly,
                }).ToList();
            },
            OnPick = (ix, it) =>
            {
                var id = it.Id!;
                var item = D.Items[id];
                if (item.Target == "allies") { ApplyItemField(id, Party); return; }
                PartyPicker("對誰使用？", a => { PopMenu(); ApplyItemField(id, new List<Actor> { a }); },
                    a => item.Target == "deadAlly" ? a.Hp <= 0 : a.Hp > 0, VitalKind(item));
            },
        });
    }

    void ApplyItemField(string id, List<Actor> targets)
    {
        var msgs = ApplyItem(id, targets.Cast<Unit>().ToList());
        RemoveItem(id);
        ShowToast(string.Join(" ", msgs));
        Render();
    }

    List<string> ApplyItem(string id, List<Unit> targets)
    {
        var it = D.Items[id];
        var msgs = new List<string>();
        foreach (var t in targets)
        {
            if (it.Revive > 0)
            {
                if (t.Hp > 0) { msgs.Add($"{UName(t)}沒有倒下。"); continue; }
                t.Hp = Math.Max(1, (int)Math.Floor(UMaxHp(t) * it.Revive));
                t.St.Clear();
                msgs.Add($"{UName(t)}復活了！");
                continue;
            }
            if (t.Hp <= 0) continue;
            if (it.Heal > 0)
            {
                var h = Math.Min(it.Heal, UMaxHp(t) - t.Hp);
                t.Hp += h;
                msgs.Add($"{UName(t)}回復了 {h} HP。");
            }
            if (it.Mp > 0 && t is Actor a)
            {
                var h = Math.Min(it.Mp, MaxMp(a) - a.Mp);
                a.Mp += h;
                msgs.Add($"{UName(t)}回復了 {h} MP。");
            }
            if (it.Cure)
            {
                foreach (var k in new[] { "burn", "silence", "confuse", "sleep" }) t.St.Remove(k);
                msgs.Add($"{UName(t)}冷靜下來了。");
            }
        }
        return msgs;
    }

    void MenuSkillsField()
    {
        PartyPicker("誰要使用技能？", a =>
        {
            PushMenu(new Menu
            {
                Title = Ad(a).Name + "的技能",
                Cls = "wide",
                Build = () => SkillsOf(a).Select(id =>
                {
                    var sk = D.Skills[id];
                    return new MenuItem { Label = sk.Name, Right = "MP " + sk.Mp, Disabled = !sk.Field || a.Mp < sk.Mp || a.Hp <= 0, Desc = sk.Desc, Id = id };
                }).ToList(),
                OnPick = (ix, it) =>
                {
                    var sk = D.Skills[it.Id!];
                    void Use(List<Actor> targets)
                    {
                        a.Mp -= sk.Mp;
                        var msgs = new List<string>();
                        foreach (var t in targets)
                        {
                            if (sk.Kind == "revive" || (sk.Revive && t.Hp <= 0))
                            {
                                if (t.Hp <= 0)
                                {
                                    t.Hp = Math.Max(1, (int)Math.Floor(MaxHp(t) * (sk.Rate > 0 ? sk.Rate : 0.3)));
                                    msgs.Add($"{Ad(t).Name}復活了！");
                                }
                                if (sk.Kind == "revive") continue;
                            }
                            if (sk.Kind == "heal" && t.Hp > 0)
                            {
                                var h = Math.Min(HealAmount(a, sk), MaxHp(t) - t.Hp);
                                t.Hp += h;
                                msgs.Add($"{Ad(t).Name}回復了 {h} HP。");
                            }
                            if (sk.Kind == "cure") msgs.Add($"{Ad(t).Name}冷靜下來了。");
                        }
                        ShowToast(msgs.Count > 0 ? string.Join(" ", msgs) : "沒有效果。");
                        Render();
                    }
                    if (sk.Target == "allies") Use(Party);
                    else if (sk.Target == "self") Use(new List<Actor> { a });
                    else PartyPicker("對誰使用？", t => { PopMenu(); Use(new List<Actor> { t }); },
                        t => sk.Target == "deadAlly" ? t.Hp <= 0 : t.Hp > 0);
                },
            });
        });
    }

    void MenuEquip()
    {
        PartyPicker("誰要換裝備？", a =>
        {
            PushMenu(new Menu
            {
                Title = Ad(a).Name + "的裝備",
                Cls = "wide",
                Build = () => Slots.Select(slot =>
                {
                    var cur = a.Equip.GetValueOrDefault(slot);
                    return new MenuItem
                    {
                        Label = SlotName[slot] + "：" + (cur != null ? D.Items[cur].Name : "（無）"),
                        Slot = slot,
                        Desc = cur != null ? D.Items[cur].Desc : "",
                    };
                }).ToList(),
                OnPick = (ix, it) =>
                {
                    var slot = it.Slot!;
                    PushMenu(new Menu
                    {
                        Title = SlotName[slot],
                        Cls = "wide",
                        Build = () =>
                        {
                            var list = InvList((item, id) => SlotOf(item) == slot && CanEquip(a, id))
                                .Select(id => new MenuItem { Label = D.Items[id].Name, Right = "×" + Inv[id], Desc = ItemDesc(id), Id = id }).ToList();
                            if (slot != "weapon") list.Add(new MenuItem { Label = "（卸下）", Id = null, Desc = "" });
                            return list.Count > 0 ? list : new List<MenuItem> { new() { Label = "（沒有可以裝備的東西）", Disabled = true } };
                        },
                        OnPick = (ix2, it2) =>
                        {
                            var old = a.Equip.GetValueOrDefault(slot);
                            if (it2.Id != null) RemoveItem(it2.Id);
                            if (old != null) AddItem(old);
                            a.Equip[slot] = it2.Id;
                            a.Hp = Math.Min(a.Hp, MaxHp(a));
                            a.Mp = Math.Min(a.Mp, MaxMp(a));
                            PopMenu();
                        },
                    });
                },
            });
        });
    }

    void MenuStatus()
    {
        PartyPicker("查看誰的狀態？", a =>
            PushMenu(new Menu { Title = Ad(a).Name, Cls = "status", Actor = a, Build = () => new List<MenuItem> { new() { Label = "返回" } }, OnPick = (ix, mi) => PopMenu() }));
    }

    void MenuQuests()
    {
        PushMenu(new Menu { Title = "任務", Cls = "quests", Build = () => new List<MenuItem> { new() { Label = "返回" } }, OnPick = (ix, mi) => PopMenu() });
    }

    Task OpenShop(string shopId)
    {
        this.shopId = shopId;
        var tcs = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        void Close() { PopMenu(); tcs.TrySetResult(); }
        PushMenu(new Menu
        {
            Title = "商店",
            Cls = "shop",
            Build = () => new List<MenuItem> { new() { Label = "購買" }, new() { Label = "賣出" }, new() { Label = "離開" } },
            OnBack = Close,
            OnPick = (i, mi0) =>
            {
                if (i == 2) { Close(); return; }
                if (i == 0)
                {
                    PushMenu(new Menu
                    {
                        Title = "購買",
                        Cls = "wide shop",
                        Build = () => D.Shops[shopId].Select(id => new MenuItem
                        {
                            Label = D.Items[id].Name, Right = D.Items[id].Price + " K", Disabled = Gold < D.Items[id].Price,
                            Desc = ItemDesc(id) + $"（持有 {ItemCount(id)}）", Id = id,
                        }).ToList(),
                        OnPick = (ix, it) =>
                        {
                            Gold -= D.Items[it.Id!].Price;
                            AddItem(it.Id!);
                            ShowToast($"買了【{D.Items[it.Id!].Name}】");
                        },
                    });
                }
                else
                {
                    PushMenu(new Menu
                    {
                        Title = "賣出",
                        Cls = "wide shop",
                        Build = () =>
                        {
                            var ids = InvList((it, iid0) => it.Type != "key" && it.Price > 0);
                            return ids.Count > 0
                                ? ids.Select(id => new MenuItem { Label = D.Items[id].Name, Right = D.Items[id].Price / 2 + " K", Desc = $"持有 ×{Inv[id]}", Id = id }).ToList()
                                : new List<MenuItem> { new() { Label = "（沒有可以賣的東西）", Disabled = true } };
                        },
                        OnPick = (ix, it) =>
                        {
                            Gold += D.Items[it.Id!].Price / 2;
                            RemoveItem(it.Id!);
                            ShowToast($"賣掉了【{D.Items[it.Id!].Name}】");
                        },
                    });
                }
            },
        });
        return tcs.Task;
    }
}
