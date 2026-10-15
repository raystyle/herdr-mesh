# tailnet 自托管控制面部署(headscale + 客户端)

> 范例真源:舰队在役控制面实采(2026-10-15),全脱敏(域名/网段/密钥占位)。
> 形态:docker 容器 headscale + 前置反代(caddy)终结 TLS + 自建 DERP 区 + sqlite。

## 〇、单机服务栈一键(caddy + headscale + rustdesk 全家)

有 `server-compose.yml`:TLS 前置(caddy 443,证书自动 acme)+ tailnet 控制面(headscale,仅网内暴露，caddy 反代)+ 远程桌面中继(rustdesk hbbs/hbbr,host 网打洞)。配套 `Caddyfile.example` / `server.env.example`,与 headscale 三配置件同目录:

```bash
cp server.env.example server.env   # 填控制面域名
cp Caddyfile.example Caddyfile    # 填域名(反代形同真源)
docker compose -f server-compose.yml --env-file server.env up -d
```

## 一、控制面部署(docker)

**目录**:`/opt/headscale/`(config.yaml / derpmap.yaml / policy.hujson / 数据卷 db.sqlite + 密钥)

**起容器**(host 网络或按需映射 8080;unless-stopped):

```bash
sudo mkdir -p /opt/headscale
# 放入本目录三个模板(config.yaml / derpmap.yaml / policy.hujson),改占位符
sudo docker run -d --name headscale --restart unless-stopped \
  -v /opt/headscale:/etc/headscale \
  -v /opt/headscale/data:/var/lib/headscale \
  headscale/headscale:latest serve
```

**TLS 前置**:headscale 裸听 8080,TLS 由反代终结(caddy/nginx 任一);
`server_url` 填 https 域名,反代把 443 转 127.0.0.1:8080。

## 二、config.yaml 范例(占位符形)

```yaml
server_url: https://<控制面域名>
listen_addr: 0.0.0.0:8080
metrics_listen_addr: 127.0.0.1:9090
noise:
  private_key_path: /var/lib/headscale/noise_private.key
prefixes:
  v4: 100.64.0.0/10        # 私有段占位,任选未占用段
  v6: fd7a:115c:a1e0::/48
  allocation: sequential
derp:
  server:
    enabled: true           # 内嵌 DERP,与自建区并存
    region_id: 999
    region_code: headscale
    region_name: Headscale Embedded DERP
    verify_clients: true
    stun_listen_addr: 0.0.0.0:3478
    private_key_path: /var/lib/headscale/derp_server_private.key
    automatically_add_embedded_derp_region: true
  urls: []
  paths:
    - /etc/headscale/derpmap.yaml
  auto_update_enabled: true
node:
  expiry: 0                 # 节点永不过期
database:
  type: sqlite
  sqlite:
    path: /var/lib/headscale/db.sqlite
    write_ahead_log: true
log:
  level: info
  format: text
```

## 三、derpmap.yaml 范例(自建区,剔公网表)

```yaml
regions:
  100:
    regionid: 100
    regioncode: <区代号>
    regionname: <区名>
    nodes:
      - name: 100a
        regionid: 100
        hostname: <控制面域名>
        derpport: 443
        stunport: 3478
```

**要点(判例在档)**:derp 只留自建区,剔官方公网表;全对等同区中继,
免境外中继被单向黑洞。内嵌 999 区与自建 100 区并存,客户端就近。

## 四、policy.hujson 范例(tailscale ssh 授权)

```json
{
  "ssh": [
    { "action": "accept",
      "src": ["autogroup:member"],
      "dst": ["autogroup:self"],
      "users": ["autogroup:nonroot"] }
  ]
}
```

acls 省略 = allow-all(官方文档形);ssh 段 = 成员可 ssh 到自己名下任何节点
(策略层授权,免分发钥匙)。

## 五、控制面运维命令

```bash
docker exec headscale headscale users create <用户名>
docker exec headscale headscale preauthkeys create --user <用户名> --expiration 24h
docker exec headscale headscale nodes list
docker exec headscale headscale derpmap 2>/dev/null || true
```

## 六、节点客户端接入

```bash
# linux(官方脚本装)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --login-server=https://<控制面域名> --hostname=<节点名>

# win:官方安装器 -> Tailscale 服务常驻 -> 同款 tailscale up
# mac:官方客户端;tailscale-ssh 客户端握手缺口,互补道 = 普通 ssh 走网内地址
```

prefs 生效形:`ControlURL=https://<控制面域名>`、`RunSSH=true`、
`Hostname=<节点名>`、`WantRunning=true`。

## 七、验收

- 控制面:`curl https://<控制面域名>/health` 活(302/200)
- 节点:`tailscale status` 列全网;`tailscale ping <对端短名>` 通
- 中继:`tailscale netcheck` Nearest DERP = 自建区;对等 rx>0
