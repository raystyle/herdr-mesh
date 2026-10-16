# 工位与在场族动词

> agents 正文动词表只留六主动词;本篇收工位与在场族。旗标全集以 `agents --llms` 为准。

| 动词 | 文法 | 何时用 |
| --- | --- | --- |
| ws | `ws <label> [--cwd DIR] [--machine 机]` | 要开工作台;`ws list [机]` 列台;`ws close <台> [机]` 收台 |
| shell | `shell <机> <仓路径>` | 要在某机某仓开台 shell 格 |
| dev | `dev <机> <仓路径> [--kind 类]` | 要开台并起 agent |
| split | `split <id> [--direction right\|down]` | 要在格旁分裂新格 |
| tab | `tab list [机]` / `tab create <机>` / `tab close <机:tab>` | 要管理 tab |
| zoom | `zoom <id>` | 要聚焦某格 |
| wt | `wt [机\|wsl] [--title 名]` | win 专属:本窗开 tab 显该机窗格视图 |
| trust | `trust` | 要放行信任屏(全机扫屏按键) |
| sync | `sync [机]` | 要补注册机册 |
| reload | `reload <id>` | 要翻台重载技能与插件(同格同 session 重进;idle/done 皆可翻,working/blocked 拒 --force 过;/exit 三选一对话框自动应答) |
| mode | `mode <dnd\|away\|online> [until]` | 要声明本机在场状态(presence 走 shares 键) |

## 示例

```bash
agents shell node-a ~/repos/myrepo
agents dev node-a ~/repos/myrepo --kind grok
agents split local:w13:p1 --direction down
agents zoom local:w13:p1
agents wt wsl --title 台面
agents trust
agents sync
agents reload repo-claude-1
agents mode dnd 2h
```
