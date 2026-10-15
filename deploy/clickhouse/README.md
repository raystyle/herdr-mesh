# ctx 存储(ClickHouse)部署模板

> 范例真源:舰队在役 ctx 存储节点实采(2026-10-15),全脱敏。
> 用途:七原语 `ctxs` 检索引擎——agent 请求全链对话历史库(gw_logs 库)。

## 一、形态

单容器 `clickhouse/clickhouse-server:26.8`,四挂载:

| 挂载 | 内容 | 入仓? |
|---|---|---|
| `./data` | 数据层(库表与分区) | 否(gitignore:deploy/*/data/) |
| `./certs` | 自管证书 server.crt / server.key / ca.crt | **恒不入仓** |
| `./config.d` | TLS 面配置(tls.xml.example 复制为 tls.xml) | 模板入仓 |
| `./init.d` | 首起 SQL:建 ctx_reader 只读用户 | 模板入仓(口令占位) |

## 二、安装部署(一步一步)

```bash
cd deploy/clickhouse
mkdir -p data certs
cp config.d/tls.xml.example config.d/tls.xml
cp init.d/01-reader.sql.example init.d/01-reader.sql
cp clickhouse.env.example clickhouse.env

# 1. 证书:自管 CA 签 server 证书(SAN 带 localhost),client 证书给读方;
#    三件 + client 件放 certs/(恒不入仓)。逐字形:
#    openssl req -x509 -newkey rsa:2048 -nodes -keyout certs/ca.key -out certs/ca.crt -days 3650 -subj "/CN=mesh-ca"
#    openssl req -newkey rsa:2048 -nodes -keyout certs/server.key -out certs/server.csr -subj "/CN=ctx-store" -addext "subjectAltName=DNS:localhost"
#    openssl x509 -req -in certs/server.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial -out certs/server.crt -days 825 -copy_extensions copyall
#    openssl req -newkey rsa:2048 -nodes -keyout certs/client.key -out certs/client.csr -subj "/CN=ctx_reader" && openssl x509 -req -in certs/client.csr -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial -out certs/client.crt -days 825

# 2. 口令:clickhouse.env 填 CH_ADMIN_PASSWORD;
#    init.d/01-reader.sql 的 REPLACE_ME_READER_PASSWORD 同步替换
#    (initdb 只在数据目录为空时首起执行一次;改口令后换新数据目录或手动 ALTER USER)

# 3. 起:
docker compose -f clickhouse-compose.yml --env-file clickhouse.env up -d

# 4. 验证:
curl --cacert certs/ca.crt --cert certs/client.crt --key certs/client.key https://localhost:8123/ping
```

## 三、客户端接入(ctxs)

- 直连道:`https://<节点>:8123`,双闸 = TLS client 证书(strict)+ basic(ctx_reader);8123 全接口暴露面收敛责任在宿主防火墙(仅 tailnet 网内可达)
- 客户端凭据经环境变量 `CTX_URL / CTX_USER / CTX_PASSWORD`(可选
  `CTX_CERT / CTX_KEY / CTX_CA`),或落 `~/.ctx/reader.env`(权限 600,恒不入仓)
- 表结构契约:gw_logs.head(请求头行,TTL 365 天)与 gw_logs.gwlog
  (请求正文块,TTL 180 天);数据由采集管道(vector)写入

## 四、运维

```bash
docker compose -f clickhouse-compose.yml ps          # 态
docker exec ctx-store clickhouse-benchmark --help    # 引擎在
# TTL 到期自动清;调窗口改表 TTL:
#   ALTER TABLE gw_logs.gwlog MODIFY TTL ts + INTERVAL 180 DAY;
```

## 五、边界

- 证书与口令恒不入仓(gitignore 挡 *.pem/*.crt/*.key/*.p12、certs/、deploy/*/clickhouse.env、deploy/*/init.d/*.sql、deploy/*/data/)
- reader 只授 SELECT;管理面走 admin 用户,口令只在部署机 env
- 8123 对外暴露面收敛:仅 tailnet 网内可达,不对公网开
