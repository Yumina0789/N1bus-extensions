#!/bin/sh
# 把限流参数套进 haproxy 模板再启动它。
#
# 为什么需要这一步：haproxy 的配置文件不支持环境变量插值，而「限流参数要能在面板上改」
# 又必须让它们从环境变量进来。所以用一个最小的模板替换 —— 只认我们自己写的 @XXX@ 占位符，
# 不用 envsubst 那种会把配置里任何 $ 都当成变量展开的做法。
#
# 值本身已由本体校验成整数（见 n1bus_modules._config_value），这里不再做判断。
set -eu

TPL=/usr/local/etc/haproxy/haproxy.cfg.tpl
OUT=/tmp/haproxy.cfg

RATE_LIMIT="${KMS_RATE_LIMIT:-60}"
BAN_TIME="${KMS_BAN_TIME:-600}"

sed -e "s/@RATE_LIMIT@/${RATE_LIMIT}/g" \
    -e "s/@BAN_TIME@/${BAN_TIME}/g" \
    "$TPL" > "$OUT"

echo "[limiter] 每个来源 ${BAN_TIME}s 内最多 ${RATE_LIMIT} 次连接，超出即丢弃"

exec haproxy -W -db -f "$OUT"
