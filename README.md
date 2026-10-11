# N1bus-modules

N1bus 面板的**模块 registry**。面板里的「模块商店」只从这个仓库取清单与包。

- 规范全文：N1bus 仓库的 [`docs/modules.md`](https://github.com/Yumina0789/N1bus/blob/main/docs/modules.md)
- 面板**内置**本仓库地址（GitHub Pages），不提供「填任意仓库 URL」的入口 ——
  想加模块就往这里提 PR。这条路是窄的，但它是「能从网上装东西」与
  「本体不执行外部提供的命令」（ADR 0002）能同时成立的前提。
- 商店站就是本仓库的 GitHub Pages：<https://yumina0789.github.io/N1bus-modules/>
  （面板安装模块时读的是 `index.json` 与 `packages/*.tar.gz`）

---

## 目录结构

```
N1bus-modules/
├── index.json                 # 商店读这个（由 tools/pack.py 回填）
├── src/                       # 模块源文件（人在这里改）
│   ├── rsc4d/
│   │   ├── manifest.json
│   │   ├── compose.yml
│   │   ├── Caddyfile          # 模块自己那个 web 服务的配置
│   │   └── web/index.html     # 模块页面（被面板以 iframe 嵌入）
│   └── harness/
│       ├── manifest.json
│       └── compose.yml
├── packages/                  # 打包产物（本体在这里下载）
├── templates/                 # 写新模块时抄这里
└── tools/
    └── pack.py                # 打包 + 算哈希 + 回填 index.json
```

**为什么源文件与产物都在同一个仓库**：模块的身份就是那个 sha256，而哈希是**算出来的**。
源文件留在仓库里、用脚本一条龙打包，才不会出现「手工 `sha256sum` 抄错一位」这种事。

**为什么是归档而不是散文件**：sha256 直接对一个字节序列计算，不需要「目录哈希规范化」
那种容易出错的东西；下载 → 校验 → 解包是一条直线。

---

## 一个模块由什么构成

| 部分 | 必需 | 说明 |
|---|---|---|
| `manifest.json` | ✔ | 模块的身份与声明。**必须位于包根** |
| `compose.yml` | ✖ | 需要容器栈才有；文件名由 manifest 的 `compose.file` 指定 |
| 其它文件 | ✖ | 页面、静态资源、模块自己的配置。本体不执行其中任何代码 |

**模块的逻辑全在它自己的容器里。** manifest 里没有任何「要执行的字符串」——
面板执行的永远是写死的 `module.*` 动作（`docker compose -p n1bus-<id> -f <path>/... `），
`<path>` 由面板算成 `/opt/n1bus/modules/<id>/`，不从 manifest 里取。

### 页面（`page`）

页面只有一种形态：**iframe**，由面板嵌入，地址是站内路径 `/m/<id>/`。

| 字段 | 说明 |
|---|---|
| `page.url` | 站内路径，如 `/m/rsc4d/`。面板按它嵌 iframe |
| `page.upstream` | Caddy 把这个前缀转给谁，`host:port` 形式（容器名 + 端口） |
| `page.entry` | 入口地址**不是固定值**时才需要，见下 |

面板在装 / 卸模块时会生成一段 Caddy 路由（`handle_path /m/<id>/* { reverse_proxy ... }`）
并热重载，所以**模块容器必须挂在 Caddy 所在的那个 docker 网络上**（通常是 `docker_default`）。
没有 `page.upstream` 的模块不会生成路由。

`page.entry` 目前只有一种类型 `container-log-token`：入口地址每次启动才生成、
只打印在容器日志里（用一次性 token 换会话 cookie 的那类）。面板会读指定容器的日志、
用**面板自己内置的**规则提取 token 再拼地址 —— 正则由面板写死，模块给不了。
`harness` 模块就是这么工作的。

```json
"page": {
  "kind": "iframe",
  "title": "DeepSeek Harness",
  "url": "/m/harness/",
  "upstream": "n1bus-harness:3081",
  "entry": {"type": "container-log-token", "container": "n1bus-harness"}
}
```

---

## 加一个模块：四步

```sh
# 1) 写源文件
mkdir -p src/myext
cp templates/manifest.example.json src/myext/manifest.json
cp templates/compose.example.yml  src/myext/compose.yml   # 需要容器栈才要
$EDITOR src/myext/manifest.json

# 2) 打包（同时把 sha256 / size 回填进 index.json）
python3 tools/pack.py myext

# 3) 自检：再打一次，哈希必须与上次一样（pack.py 是确定性的）
python3 tools/pack.py myext

# 4) 提 PR
```

打包约定：**包根就是 `manifest.json`**，不能再套一层目录。`pack.py` 保证这一点，
`compose.file` 声明的文件也会被带上；包内路径就是 `src/<id>/` 下的相对路径。

---

## 硬规矩（面板解包与校验时会拒绝不合规的包）

| 规矩 | 拒绝的理由 |
|---|---|
| `id` 匹配 `^[a-z][a-z0-9-]{1,31}$` | id 会进路径与 docker project 名 |
| `id` / `version` 与 `index.json` 里那条一致 | 防止「清单说是 A、包里是 B」 |
| `sha256` 与 `index.json` 一致 | 这是唯一的完整性保证 |
| 包里不能有绝对路径、`..`、符号链接 | 防穿越解包，导入模块不该能写到目标目录之外 |
| 包里没有任何「要执行的字符串」 | 面板执行的永远是写死的 `module.*` 动作 |
| `compose.project` 等于 `n1bus-<id>` | 面板不信任任意 project 名 |
| `page.url` 是 `/` 开头的站内路径 | 它会被原样写进 Caddy 配置，字符集卡得很紧 |
| `page.upstream` 是 `host:port` | 同上 |
| `page.entry.container` 是合法容器名 | 会作为 `docker logs` 的一个参数 |
| `icon` 是面板**已有**图标集里的名字 | 不加载外部 SVG |

---

## 现有模块

| id | 是什么 | 页面 |
|---|---|---|
| `rsc4d` | [RSC4D](https://github.com/Yumina0789/RSC4D)：KMS wire 协议服务端 v4 / v5 / v6，静态二进制 | 状态页（实时探测 KMS 可达性 + 客户端配置命令） |
| `harness` | DeepSeek Harness：容器里的 agent 工作台 | dsh 自己的界面，入口用一次性 token 换取会话 |

`rsc4d` 的镜像是 `ghcr.io/yumina0789/rsc4d:latest`（公开）。
`harness` 的镜像是 `dsh:local`，**需要目标机器上已有该镜像** —— 它由本机自行构建，
不在任何公开 registry 里。
