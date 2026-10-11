#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一个 src/<id>/ 打成 packages/<id>-<version>.tar.gz，并更新 index.json。

    python3 tools/pack.py kms

为什么要有这个脚本：sha256 与 size 是模块身份的**唯一**凭据（本体只认它），
手工 `sha256sum` 再抄进 index.json 迟早抄错。这里从 manifest.json 读 id/version，
打包、算哈希、回填 index.json 一条龙。

打包约定（本体解包时依赖它）：**包根就是 manifest.json**，不能套一层目录。
"""
import gzip
import hashlib
import io
import json
import os
import pathlib
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
PKG = ROOT / "packages"
INDEX = ROOT / "index.json"

# 打进包里的东西：manifest 必须有，compose 可选，其余一律不要
ALLOW = ("manifest.json", "compose.yml")
MANIFEST_REQUIRED = ("schema", "id", "name", "version", "summary")


def die(msg):
    print("错误：" + msg, file=sys.stderr)
    sys.exit(1)


def main():
    if len(sys.argv) != 2:
        die("用法：python3 tools/pack.py <模块 id>")
    mid = sys.argv[1]

    src = SRC / mid
    if not src.is_dir():
        die("没有 src/%s/ 这个目录" % mid)
    mp = src / "manifest.json"
    if not mp.is_file():
        die("src/%s/ 里没有 manifest.json" % mid)

    man = json.loads(mp.read_text(encoding="utf-8"))
    for k in MANIFEST_REQUIRED:
        if not man.get(k):
            die("manifest.json 缺字段：%s" % k)
    if man["id"] != mid:
        die("manifest.json 的 id（%s）与目录名（%s）不一致" % (man["id"], mid))

    version = man["version"]
    files = [f for f in ALLOW if (src / f).is_file()]
    if "manifest.json" not in files:
        die("包里没有 manifest.json")
    # compose 字段声明了就必须带上对应文件
    if man.get("compose") and man["compose"].get("file"):
        want = man["compose"]["file"]
        if want not in files:
            die("manifest 声明了 compose.file=%s，但 src/%s/ 里没有这个文件" % (want, mid))

    PKG.mkdir(exist_ok=True)
    out = PKG / ("%s-%s.tar.gz" % (mid, version))

    # 确定性打包：固定 mtime/uid/gid、按名字排序，**gzip 头也固定 mtime** ——
    # 同样的源打两次必须得到同样的哈希，否则「哈希即身份」名存实亡。
    # 坑：只用 tarfile 的 "w:gz"，tar 里的 mtime 固定了，gzip 头里还会写当前时间，
    # 于是每次打包哈希都变。所以这里自己套一层 GzipFile(mtime=0)。
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as gz:
        with tarfile.open(fileobj=gz, mode="w") as tf:
            for name in sorted(files):
                p = src / name
                info = tf.gettarinfo(str(p), arcname=name)
                info.mtime = 0
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mode = 0o644
                with open(p, "rb") as fh:
                    tf.addfile(info, fh)
    data = buf.getvalue()
    out.write_bytes(data)

    sha = hashlib.sha256(data).hexdigest()
    size = len(data)

    idx = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.is_file() else {
        "schema": 1, "registry": "Yumina0789/N1bus-modules", "modules": []}
    idx.setdefault("registry", "Yumina0789/N1bus-modules")
    idx.setdefault("modules", [])
    entry = None
    for e in idx["modules"]:
        if e.get("id") == mid:
            entry = e
            break
    if entry is None:
        entry = {"id": mid}
        idx["modules"].append(entry)
    entry.update({
        "name": man["name"],
        "summary": man["summary"],
        "icon": man.get("icon", ""),
        "homepage": man.get("homepage", ""),
        "latest": version,
    })
    entry.setdefault("versions", {})
    entry["versions"][version] = {
        "url": "packages/%s" % out.name,
        "sha256": sha,
        "size": size,
        "min_core": man.get("min_core", man.get("min_panel", "1.0")),
    }
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("已打包 %s" % out.relative_to(ROOT))
    print("  含文件  %s" % ", ".join(files))
    print("  sha256  %s" % sha)
    print("  size    %d" % size)
    print("  index   %s v%s 已回填" % (mid, version))


if __name__ == "__main__":
    main()
