# herdr-mesh

七原语(agents / shares / streams / tasks / pipes / ports / ctxs)全量公开归档仓:
命令源码、操作 SKILL、方案契约(CONTRACT)、部署套件(部署文档 + 全自动脚本 + 冒烟测试)。
单机可跑的最小 mesh 部署,到多机舰队互操作,一套仓全收。

```
agent 节点(linux/mac/win)
  herdr server(窗格物理层)+ tailscale(headscale 纯自托管)
  七原语命令面(uv 安装自本仓 src/)
    agents  消息域:窗格检索/读屏/投递/工作台;寻址双轨制(窗格操作 机:格,消息收发 机:agent别名)
    shares  文件域:S3 内容哈希键中转
    streams 流域:S2 持久流;room 一等概念(rooms/room/dm),view -f 活跟随,stdin 管道,--file 切片传档
    tasks   持久任务域:hst task 全局遥控
    pipes   实时字节域:tailcat 临时加密连接(传文件/转发端口/管道)
    ctx     对话历史域:ClickHouse 全文检索(view/show/search,直连证书道)
store-node(存储宿主)
  garage(S3 对象)+ s2-lite(流服务),全自动部署脚本 + 本机最小验证
```

## 快速开始

部署(全官方源,逐步文档见 docs/deploy.md):

```bash
cp deploy/env.example deploy/env   # 填别名与密钥占位
bash deploy/install-mesh.sh deploy/env
```

本机最小验证(单机全链,不动远端):

```bash
bash smoke/local.sh
```

七命令安装(uv):

```bash
uv tool install --force git+https://github.com/raystyle/herdr-mesh#subdirectory=src
```

各命令 `--llms` 出手册;操作技能见 `skills/`(复制进 agent 技能目录即用)。

## 目录

| 路径 | 内容 |
| --- | --- |
| CONTRACT.md | 七原语命令契约单一真源(动词表/信封/错误码/批次史) |
| src/ | prim 命令包(七入口,uv 安装源) |
| skills/ | 七原语操作 SKILL(写作标准:动词表/文法/示例/坑表;附 distil 技能自进化) |
| docs/ | 部署文档(运行时来源/逐步安装/故障定位)+ 使用文档 |
| deploy/ | 部署脚本与配置(存储面 compose+脚本双形/节点面/总控/garage 初始化/tailnet 控制面) |
| smoke/ | 冒烟:local.sh 本机最小验证;smoke.sh 多节点全链 |

## 兄弟项目

| 仓 | 角色 |
| --- | --- |
| [herdr](https://github.com/herdrdev/herdr)(官方) | 窗格物理层:workspace > tab > pane,agent 生命周期检测 |
| [s5_rs](https://github.com/raystyle/s5_rs) | 对象与流引擎 CLI:S3 文件交换 + S2 流记录(shares/streams 的引擎) |
| [hst_rs](https://github.com/raystyle/hst_rs) | 会话态引擎 CLI:hook 落盘/状态栏/只读对话 trace/诊断(tasks 的引擎) |
| [overcast](https://github.com/raystyle/overcast) | 大模型网关:请求全量日志入 ClickHouse(ctx 的数据源) |
| [project-evo](https://github.com/raystyle/project-evo) | skill 插件市场仓(操作 SKILL 的上游) |
| ai-ccoe(私有) | 总集成验收:知识库 + 执行面,七原语的验收与演进总台 |

## 安全

密钥永不入仓:deploy/env 与 credentials 文件均 gitignore(占位符见 env.example);
skills 与 src 全脱敏(角色代称 store-node/node-a/workbench-*,无真实主机名与网段)。
