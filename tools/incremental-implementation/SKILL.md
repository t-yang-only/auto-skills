---
name: incremental-implementation
description: "Thin vertical slices: implement, verify, and commit one independently reversible unit at a time instead of a big-bang change. Use when a change touches more than one file, when starting a feature or refactor, when a task feels too large to verify in one shot, or when the user asks for incremental / 分步 / 小步 提交."
---

# Incremental Implementation（增量实现）

## 核心原则

**一次只推进一个薄垂直切片：改一点、验一点、提交一点。**

一个「切片」= 一条能独立验证、独立回滚的改动。垂直切片穿透所需的各层（界面 → 逻辑 → 存储），但只做**一件事**；水平切片只做一层（先把所有 model 写完、再写所有 view），结果是**很久都无法验证任何东西**。

## 铁律

```
在动手改第二个文件之前，先问：第一个文件的改动能不能单独验证？
```

不能，说明切片切错了。

## 垂直 vs 水平

| | 垂直切片（要） | 水平切片（不要） |
|---|---|---|
| 切法 | 一个完整小功能穿透各层 | 一层全部改完再下一层 |
| 中途可验证 | 是（每片都能跑） | 否（直到最后才拼得起来） |
| 出问题时 | 回滚最后一片 | 回滚全部 |
| 典型错法 | — | 「先把 8 个 model 都写完」 |

## 切片循环（Slice Loop）

1. **SCOPE** —— 这一刀切什么？用一句话说清；说不清就是切大了。
2. **IMPLEMENT** —— 只改这一刀必需的代码。顺手发现的其他问题记下来，**不在这刀里改**。
3. **TEST** —— 立刻验证这一刀（跑测试/跑命令/看输出），**不是「最后一起测」**。
4. **COMMIT** —— 提交成一个可独立回滚的单元。
5. **NEXT** —— 到此才允许开下一刀。

## 安全网三件套

改动有风险时，至少用一件：

| 手段 | 做法 | 什么时候用 |
|---|---|---|
| **Feature flag** | 新路径默认关闭，验证后再开 | 新功能要上线但还没验完 |
| **安全默认值** | 老行为逐字不变，新行为显式开启 | 改共享代码/公共接口 |
| **可回滚提交** | 一个 commit 能撤掉整片 | 所有生产改动 |

**顺序**：先让老行为在改完后逐字不变，再切换默认值。反过来做，出问题时你分不清是新代码还是切换引起的。

## 反合理化表

| 你会想 | 现实 |
|---|---|
| 「改动不大，一起改完再测」 | 「不大」是事后判断；测试是唯一能证明它的东西 |
| 「分步提交太碎，历史不好看」 | 一个巨大的 commit 出问题时更难查，且无法部分回滚 |
| 「先写完再统一测，省时间」 | 同时引入 N 个错误，定位成本是 N² |
| 「这个顺手也改了吧」 | 顺手改动混进切片，回滚时会连带撤掉不该撤的 |
| 「反正是小项目」 | 项目变大之前没人通知你 |

## 红线信号（STOP）

- 一次改动跨 3 个以上文件且说不清最小可验证单元
- 心里想「最后一起测」
- 提交信息里出现「and」把两件不相关的事连起来
- 切片做完发现「还差一点才能跑」——说明切片切错了，退回去重切

## 与 auto-skills 台账的结合

每完成一个切片，把证据落进工具轨迹表，让「增量」这件事本身可被检索：

```bash
python scripts/auto_router.py trace incremental_implementation "切片: <做了什么> | 验证: <命令> → <结果>" --stage implement --status SUCCESS --query "<任务关键词>" --project-root "<工程根>"
```

多 Agent 并行时，切片边界要与 nm-skills 的认领范围一致：认领时声明的 `--files` 应当正好是这一片要动的文件，不要让切片范围溢出认领范围（否则文件防撞预警会失效）。

## 边界

本技能管**怎么切**，不管**切什么**（那是 brainstorming / spec 的事），也不管**验没验**（那是 verification-before-completion 的事）。
