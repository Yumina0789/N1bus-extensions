# N1bus-modules

N1bus 面板的**模块 registry**。面板里的「商店」只从这个仓库装模块。

- 规范全文：N1bus 仓库的 [`docs/modules.md`](https://github.com/Yumina0789/N1bus/blob/main/docs/modules.md)
- 面板**内置**本仓库地址，不提供「填任意仓库 URL」的入口 —— 想加模块就提 PR。
  这条路是窄的，但它是「能从网上装东西」和「不做任意命令执行」能同时成立的前提。

---

## 目录结构

```
N1bus-modules/
├── index.json                 # 商店读这个
├── src/                       # 模块源文件（人在这里改）
│   └── kms/
│       ├── manifest.json
│       └── compose.yml
├── packages/                  # 打包产物（本体在这里下载）
│   └── kms-1.0.0.tar.gz
├── templates/                 # 写新模块时抄这里
└── tools/
    └── pack.py                # 打包 + 算哈希 + 回填 index.json
```

**为什么源文件与产物都在这个仓库**：模块的身份是那个 sha256，而哈希是**算出来的**。
把源文件留在仓库里、用脚本一条龙打包，才不会出现「手工 `sha256sum` 抄错一位」这种事。

**为什么是归档而不是散文件**：sha256 直接对*一个字节序列*算，不需要「目录哈希规范化」
那种容易出错的东西；下载 → 校验 → 解包是一条直线。

---

## 加一个模块：四步

```sh
# 1) 写源文件
mkdir -p src/myext
cp templates/manifest.example.json src/myext/manifest.json
cp templates/compose.example.yml  src/myext/compose.yml   # 需要容器栈才要
$EDITOR src/myext/manifest.json

# 2) 打包（同时把 sha256/size 回填进 index.json）
python3 tools/pack.py myext

# 3) 自检：再打一次，哈希必须一样（pack.py 是确定性的）
python3 tools/pack.py myext

# 4) 提 PR
```

打包约定：**包根就是 `manifest.json`**，不能套一层目录。`pack.py` 保证这点，
`compose.file` 声明的文件也会被带上。

---

## 硬规矩（本体解包时会拒绝不合规的包）

| 规矩 | 拒绝的理由 |
|---|---|
| `id` 必须匹配 `^[a-z][a-z0-9-]{1,31}$` | id 会进路径与 docker project 名 |
| `id` / `version` 必须与 `index.json` 里那条一致 | 防止「清单说是 A、包里是 B」 |
| `sha256` 必须与 `index.json` 一致 | 这是唯一的完整性保证 |
| 包里**不能**有任何「要执行的字符串」 | 本体执行的永远是写死的 `module.*` 动作 |
| `compose.project` 必须是 `n1bus-<id>` | 本体不信任任意 project 名 |
| `api.upstream` 只能是本机地址 | 防止把它当跳板去打内网 |
| `page.iframe.path` 必须是 `/` 开头的同源路径 | 本体不代理它、也不给它认证 |
| `icon` 必须是本体**已有**图标集里的名字 | 不加载外部 SVG |

---

## 现有模块

| id | 是什么 | 页面 |
|---|---|---|
| `kms` | [RSC4D](https://github.com/Yumina0789/RSC4D)（`rs-c4d`）：KMS wire 协议服务端 v4/v5/v6，静态二进制 | 状态 + 激活统计（从日志聚合）+ 最近请求 + 启停 |

`kms` 的镜像是 `ghcr.io/yumina0789/rsc4d:latest`，由私有仓库
[RSC4D-docker](https://github.com/Yumina0789/RSC4D-docker) 构建（仓库私有、**镜像公开**）。

---

## 内置模块

`kms` 与 `harness` 在**本体里也有内置版本**（随面板发布，商店里标 `builtin`）。
它们与本仓库里同 id 的包是同一个东西的两条路径：

- **内置那份**：manifest 写在本体代码里，`module.install` 退化成 `up -d`，
  compose 路径来自本体里的固定常量（**不搬家** —— 换目录会重建容器，KMS 客户端要断约 10 秒）。
- **本仓库这份**：给「新装机 / 想升级」用。

registry 里若有比内置更高的版本，商店会提示「可升级」（升级本身还没做）。
