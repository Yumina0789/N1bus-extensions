# N1bus-extensions

N1bus 面板的**扩展 registry**。面板里的「扩展功能 → 商店」只从这个仓库装扩展。

- 规范全文：N1bus 仓库的 [`docs/extensions.md`](https://github.com/Yumina0789/N1bus/blob/main/docs/extensions.md)
- 面板**内置**本仓库地址，不提供「填任意仓库 URL」的入口 —— 想加扩展就提 PR。
  这条路是窄的，但它是「能从网上装东西」和「不做任意命令执行」能同时成立的前提。

---

## 目录结构

```
N1bus-extensions/
├── index.json                     # 商店读这个
├── packages/
│   ├── kms-1.0.0.tar.gz           # 扩展包：整体 sha256 即身份
│   └── harness-1.0.0.tar.gz
└── templates/                     # 写新扩展时抄这里
    ├── manifest.example.json
    ├── compose.example.yml
    └── index-entry.example.json
```

**为什么是归档而不是散文件**：sha256 直接对*一个字节序列*算，不需要「目录哈希规范化」
那种容易出错的东西；下载 → 校验 → 解包是一条直线。

---

## 加一个扩展：五步

```sh
# 1) 写 manifest.json（抄 templates/manifest.example.json）
#    目录长这样：
#    myext/
#    ├── manifest.json      # 必需
#    └── compose.yml        # 可选：需要容器栈才有
#    注意：manifest.json 必须在包的**根**，不能套一层目录。

# 2) 打包（包根就是上面的目录内容）
cd myext && tar -czf ../packages/myext-1.0.0.tar.gz . && cd ..

# 3) 算 sha256 与大小
sha256sum packages/myext-1.0.0.tar.gz
stat -c%s packages/myext-1.0.0.tar.gz

# 4) 在 index.json 的 extensions[] 里加一条（抄 templates/index-entry.example.json）
#    把第 3 步的两个值填进 sha256 与 size

# 5) 提 PR
```

---

## 硬规矩（面板会拒绝不合规的包）

| 规矩 | 拒绝的理由 |
|---|---|
| `id` 必须匹配 `^[a-z][a-z0-9-]{1,31}$` | id 会进路径与 docker project 名 |
| `id` / `version` 必须与 `index.json` 里那条一致 | 防止「清单说是 A、包里是 B」 |
| `sha256` 必须与 `index.json` 一致 | 这是唯一的完整性保证 |
| 包里**不能**有任何「要执行的字符串」 | 面板执行的永远是写死的白名单动作 |
| `compose.project` 必须是 `n1bus-<id>` | 面板不信任任意 project 名 |
| `api.upstream` 只能是 `http://127.0.0.1:<port>` / `http://172.17.0.1:<port>` | 防止把它当跳板去打内网 |
| `page.iframe.path` 必须是 `/` 开头的同源路径 | 面板不代理它、也不给它认证 |
| `icon` 必须是面板**已有**图标集里的名字 | 不加载外部 SVG |

---

## 内置扩展

`kms` 与 `harness` 随面板发布，**不需要安装**，面板里已经标记为 `builtin`。
它们的 manifest 内置在面板代码里，不从这个仓库下载。

本仓库里对应的是**同一个 id 的更新版本**（如果将来有）：面板会提示「可升级」。
