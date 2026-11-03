---
patterns: [传文件, 取文件, send the file, attach, fetch a share key, shares, share key]
---

## shares 文件域操作指导

- `put` 交付一份已写完的文件(内容哈希键),`get <键>` 取回,`to` 定向知会
- 拒投不丢件:目标门控拒收时代记,收方自取
- 不要用于:还在长的字节(走 pipes)、只发一条消息(走 agents/streams)
