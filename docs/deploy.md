# herdr-mesh 部署指南

本仓部署一套 agent mesh:存储面(garage S3 + s2-lite 流服务)、网络面(tailscale)、
节点面(herdr 工作台 + agents/shares/streams 三命令)。全程脚本化,本文逐步解释
每一步装了什么、从哪里装、怎么验证。

## 0. 总览与角色

```
部署机(任意 linux/mac,bash + ssh)
   |
   |-- store-node(存储宿主,linux + docker)
   |      garage(S3 对象,3900/3901/3902/3903) + s2-lite(流,8090)
   |
   |-- node-a / node-b / ...(agent 节点,linux 或 mac)
          tailscale + herdr server + s5 + prim(agents/shares/streams)
```

- 存储面:两容器跑在 store-node(host 网络,unless-stopped 常驻)
- 节点面:每节点一个 herdr server(系统服务化),s5 与 prim 走用户目录
- 网络面:节点间 tailscale 直连(ssh 面开在 tailscale);跨公网节点经 tailnet 回存储面

## 1. 运行时环境与来源

**每个角色要装什么运行时:**

| 角色 | 运行时 | 用途 |
| --- | --- | --- |
| 部署机 | bash、curl、openssl、ssh 客户端 | 跑部署与冒烟脚本 |
| store-node | docker(含 compose v2)、curl、openssl、openssh-server | 跑两个存储容器;自身不需要 python/node/rust |
| 节点(linux/mac) | 无强制系统依赖 | 二进制全预编译;python 由 uv 自管,不占系统 python |
| 节点(例外) | rust 工具链(仅当平台无预编译资产) | 仅 aarch64-linux 的 s5 需要(其余全平台二进制直装) |
| 任意 | 无 node.js | 本套件不含 node 运行时 |

**所有软件从哪里来(全官方源,无内网私有源):**

| 软件 | 来源 | 形态 |
| --- | --- | --- |
| garage v1.1.0 | `docker.io/dxflrs/garage:v1.1.0` | docker 镜像 |
| s2-lite | `ghcr.io/s2-streamstore/s2:latest` | docker 镜像(官方自托管流服务) |
| herdr | `github.com/herdrdev/herdr` releases(官方仓) | 预编译二进制(linux x86_64/aarch64、mac x86_64/aarch64、win x86_64 zip) |
| s5 | `github.com/raystyle/s5_rs` releases | 二进制直装(linux x86_64、mac 双架构、win;附 .sha256 边车;aarch64-linux 走 cargo) |
| prim(agents/shares/streams) | `github.com/raystyle/herdr-mesh` 本仓 `src/` | uv tool 安装(python 包,依赖 pydantic 走 PyPI) |
| uv | `astral.sh/uv/install.sh` | 官方安装脚本(自带 python 管理) |
| tailscale | `tailscale.com/install.sh` | 官方安装脚本 |
| headscale(可选,自托管控制面) | `github.com/juanfont/headscale` | 官方仓(控制面自管;不装则用 tailscale 官方控制面) |

镜像拉不动时给 docker 配官方镜像代理;GitHub 资产慢时可用代理或 `ghproxy` 类前缀,
来源真源不变。

### 1a. 运行时安装命令(逐个,照抄可用)

**docker(store-node 用;官方 get.docker.com 道,发行版自带则跳过):**

```bash
# linux 一键(官方脚本;国内可走阿里/清华镜像安装源,来源仍是官方脚本)
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # 重登生效,免 sudo 跑 docker
docker version                    # 验证:出 Client/Server 版本即成
```

mac 节点不需要 docker(存储面只在 store-node);要本机最小验证(local.sh)则
`brew install --cask docker` 后启动 Docker.app。

**uv(节点用;装与运行 prim 三命令,自带 python 管理,不占系统 python):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh    # 官方安装器
# 装到 ~/.local/bin;新 shell 重开或 source rc 后:
uv --version                                       # 验证
uv python install 3.12                             # 可选:预拉一个托管 python(缺省自动)
uv tool update-shell                               # 可选:把 ~/.local/bin 写进 PATH(提示已有时跳过)
```

国内网络可设 `UV_PYTHON_INSTALL_MIRROR` 与 PyPI 镜像(`UV_INDEX_URL`),来源仍官方仓。

**rust 工具链(例外回退道,仅当平台无预编译资产:目前仅 aarch64-linux 的 s5):**

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # 官方 rustup
source "$HOME/.cargo/env"
cargo install --git https://github.com/herdrdev/herdr             # 例:herdr 源装
# 验证:herdr --version;产物在 ~/.cargo/bin,确认在 PATH
```

不落在上述例外平台的节点完全不需要 rust。

**tailscale(节点网络层):**

```bash
curl -fsSL https://tailscale.com/install.sh | sh   # 官方脚本;mac 也会装 brew 包
tailscale version                                  # 验证
```

**curl / openssl / openssh-server(各角色基础件,发行版一般自带):**

```bash
# debian/ubuntu 例;mac 自带 curl/openssl,openssh 在系统设置开启
sudo apt-get install -y curl openssl openssh-server
```

## 2. 第零步:SSH 别名与密钥互信(手工,一次性)

部署脚本全部经 SSH 别名寻址,先在部署机与各节点配好别名与免密:

1. 部署机 `ssh-keygen -t ed25519`(已有则跳)
2. 公钥铺到 store-node 与每个节点(`ssh-copy-id`)
3. `~/.ssh/config` 写别名,节点名即脚本用名:

```
Host store-node
  HostName <存储宿主地址>
  User <用户名>
Host node-a
  HostName <节点A地址>
  User <用户名>
```

验证:`ssh store-node true && ssh node-a true`(全部静默通过即成)。
节点之间也要互信(herdr 互注册用):在每个节点上同样铺钥+别名。

## 3. 第一步:tailscale 网络面

目标:所有节点(含跨公网的)互相直连,ssh 走 tailscale。

1. 控制面二选一:
   - 官方:`tailscale up` 默认登录 tailscale 官方
   - 自托管:先在某台常驻机装 headscale(官方仓发行包),再节点登录该控制面
2. 节点接入由 `deploy/node/install-node.sh` 自动做:
   装客户端(tailscale.com/install.sh)-> `tailscale up --ssh --login-server=<控制面>`
3. 自托管控制面地址写进 `deploy/env` 的 `TS_CONTROL_URL`

验证:`tailscale status` 列出全部节点;`ssh <对端短名> true` 免密通过。

## 4. 第二步:存储面(store-node)

全自动:`bash deploy/install-mesh.sh`(总控第二步内含),或单跑:

```
bash deploy/store/install-store.sh deploy/env
```

脚本逐步做什么:

1. 预检 store-node 有 docker;建 `/opt/garage/{data,meta}` 数据目录
2. 写 `/opt/garage/garage.toml`(不存在才写;已存在不动):
   lmdb 引擎、单副本、host 网络、3900 S3 / 3901 集群 RPC / 3902 静态站 / 3903 admin、
   admin token 与 rpc secret 来自 env
3. 起 garage 容器(dxflrs/garage:v1.1.0,unless-stopped)
4. `garage-init.sh` 初始化(幂等):
   layout 引导(全新库无角色建桶会 503,自动布单节点 layout) ->
   建两桶(文件桶 `mesh-files` + 流后备桶 `s2-data`);建两钥(`mesh-files` 客户端钥、
   `mesh-s2` 流服务钥);每钥对各自桶授读写(不给 owner);
   密文落 `deploy/.store-credentials`(600,gitignore)
5. 起 s2-lite 容器(ghcr.io/s2-streamstore/s2:latest,`lite --bucket s2-data
   --path s2lite --port 8090`,后备桶专用钥注入环境)
6. 建流 basin(`mesh-basin`,名字至少 8 字节)

手工等价(理解用,勿替代脚本):`docker run --network host ...` + garage admin API
`POST /v1/bucket`、`POST /v1/key`、`POST /v1/bucket/allow` + s2 API `POST /v1/basins`。

验证:

```
curl http://<store-node>:3903/health          # garage 活
curl http://<store-node>:8090/health          # s2-lite 活(回 OK)
```

## 5. 第三步:节点面(逐台)

全自动(总控内含),或单节点:

```
ssh node-a 'bash -s' < deploy/node/install-node.sh  # 需先把 env/creds 传上去,见总控
```

脚本逐步做什么(linux/mac 自适应):

1. tailscale:缺则装;未入网则 `up --ssh`(需浏览器授权,重跑续)
2. herdr:release 下载预编译二进制到 `~/.local/bin/herdr`;
   mac 无资产时 `HERDR_BIN_URL` 直链或 cargo 源装
3. herdr server 服务化:linux 写 systemd 单元(`herdr-server.service`,
   Restart=on-failure);mac 写 launchd(`com.herdr.server.plist`,KeepAlive)
4. s5:release 按 CPU 架构选资产,sha256 边车校验后解包到 `~/.local/bin/s5`;
   无资产平台 cargo 源装
5. prim 三命令:`uv tool install --force
   git+https://github.com/raystyle/herdr-mesh#subdirectory=src`
   -> `agents` / `shares` / `streams` 三入口上 PATH
6. s5 配置:`~/.config/s5/config.toml`(600)写三端点(S3 + admin + S2 basin)
   与客户端钥
7. herdr 互注册:对 `HERDR_PEERS` 逐个 `herdr machine add`(机册互通)

验证:`herdr --version && s5 --version && agents --llms | head -1`。

## 6. 第四步:全链冒烟(自动化验收)

```
bash smoke/smoke.sh deploy/env deploy/.store-credentials
```

三节逐项验收,输出 `OK/FAIL` 与最终 `N 过 / M 败`:

- 一、存储面:garage 健康/版本、两桶在、s2-lite 健康、basin 在
- 二、节点面(逐台):herdr 版本、server 进程活、s5 版本、prim 三命令在位、
  s5 put+get 往返、流 append 写入
- 三、跨节点:对端 tail 见本端 append、herdr 机册含对端、agents/streams 全局面可读

全绿即部署完成。冒烟会在存储留 `smoke/` 前缀小对象,可 `s5 del` 清理。

## 7. 常见故障定位

| 症状 | 定位 |
| --- | --- |
| install-store 等 garage 超时 | `docker logs garage`;查 3903 端口与 admin token |
| s2 容器反复重启 | `docker logs s2`;多半是后备桶钥错,重跑 install-store 重建 |
| 节点 s5 报 connection refused | 节点到 store-node 的 3900/8090 不通;先 ssh 通,再查防火墙 |
| `agents` 报本机无 herdr | `~/.local/bin` 不在 PATH;重开 shell 或写 rc |
| 跨机 `agents view` 不出对端 | 对端未 `herdr machine add`;两端互查 `herdr machine list` |
| tailscale up 卡授权 | 控制面开浏览器授权;或用预发 authkey |

## 8. Windows 节点注记

win 节点装 herdr(官方仓 win 资产或 cargo 源装)+ uv + prim + s5:

```powershell
# uv(官方 Windows 安装器;装到 ~\.local\bin 并写 PATH)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv tool install --force "git+https://github.com/raystyle/herdr-mesh#subdirectory=src"
uv tool list          # 验证:prim 在列,含 agents/shares/streams 三入口
```

s5 release 有 win zip(手动解包进 `~\.local\bin`)。shares/streams 的 s5 引擎在
win 上经 WSL 代役(装 WSL + 同版 s5)。本套自动化脚本面向 linux/mac;win 手工步骤
照上文等价执行。

## 9. 卸载与清场

- 节点:停并删 herdr 服务;`uv tool uninstall prim`;删 `~/.local/bin/{herdr,s5}`、
  `~/.config/s5`
- 存储:停删两容器与 `/opt/garage`(数据全在,删前确认无要保内容)
- 网络:`tailscale logout`;自托管控制面按 headscale 文档下线
