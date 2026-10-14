# herdr-mesh

多端点 agent 网格的部署套件:存储服务、网络层、节点工作台与三条协作命令,
全自动安装脚本 + 部署文档 + 冒烟测试。

```
store-node(存储宿主,docker)
  garage(S3 对象)+ s2-lite(S2 流服务)
        ^
        | tailscale 网络层
        |
node-a / node-b / ...(agent 节点,linux/mac)
  herdr server(窗格物理层)
  agents / shares / streams(协作命令面,uv 安装自本仓 src/)
```

## 快速开始

1. 配 SSH 别名互信(docs/deploy.md 第零步)
2. `cp deploy/env.example deploy/env`,填存储宿主与节点别名
3. 全自动部署 + 全链冒烟:

```bash
bash deploy/install-mesh.sh deploy/env
```

只要本机最小验证(单机全链,不动远端):

```bash
bash smoke/local.sh
```

## 目录

| 路径 | 内容 |
| --- | --- |
| docs/deploy.md | 部署文档:逐步安装、运行时环境(docker/uv/rust)与来源、故障定位 |
| docs/usage.md | 使用文档:agents/shares/streams 三命令文法与惯例 |
| deploy/ | 部署脚本(env 模板、存储面、节点面、总控) |
| smoke/ | 冒烟:local.sh 本机最小验证;smoke.sh 全链多节点验收 |
| src/ | prim 命令包(agents/shares/streams),uv 安装源 |

## 命令安装(uv)

```bash
uv tool install --force git+https://github.com/raystyle/herdr-mesh#subdirectory=src
```

三入口进 PATH:`agents` / `shares` / `streams`,各带 `--llms` 手册。

## 相关仓

- herdr(窗格物理层):https://github.com/raystyle/herdr
- s5(对象与流引擎 CLI):https://github.com/raystyle/s5_rs
- garage(存储引擎):https://git.deuxfleurs.fr/Deuxfleurs/garage(镜像 `dxflrs/garage`)
- s2-lite(流服务):https://github.com/s2-streamstore/s2(镜像 `ghcr.io/s2-streamstore/s2`)
- tailscale(网络层):https://tailscale.com;自托管控制面 https://github.com/juanfont/headscale

## 安全

密钥永不入仓:env 与 credentials 文件均 gitignore;占位符见 deploy/env.example。
