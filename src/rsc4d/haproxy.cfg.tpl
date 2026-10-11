# rsc4d 的限流层。参数由入口脚本从环境变量套进来（haproxy 的配置本身不支持插值）。
#
# 限流模型：**同一个来源 IP 在 @BAN_TIME@ 秒内最多 @RATE_LIMIT@ 次连接**。
# 用一个 stick-table 同时干两件事：
#   * 记这个来源发起了多少次连接（conn_cnt）
#   * 表项在**最后一次**连接之后 @BAN_TIME@ 秒过期
# 于是「超限」与「惩罚时长」是同一个数字管理的：一旦超过上限，后续连接一律丢弃；
# 这个来源老实 @BAN_TIME@ 秒不再尝试，表项过期，它就能重新连上。
#
# 刻意不用 conn_rate：它返回的是经过换算的速率，阈值要靠试；conn_cnt 是多少就是多少。
# 这里是纯代理层限流 —— 不写 ufw / nftables 规则，宿主的防火墙一个字都不动。

global
	maxconn 4096
	# **必须单线程**：stick-table 是每个线程各一份的，容器里默认按 CPU 数起 2 个线程，
	# 同一个来源的连接会分散到两张表上，计数永远攒不起来 —— 表现是限流时灵时不灵。
	# 这个前端只是转发短连接，单线程绰绰有余。
	nbthread 1
	# 容器里没有 syslog，日志直接走 stdout（docker logs 看得到被拒的来源）
	log stdout format raw local0

defaults
	mode tcp
	log global
	option tcplog
	timeout connect 5s
	timeout client  30s
	timeout server  30s

frontend kms_in
	bind *:1688

	stick-table type ip size 100k expire @BAN_TIME@s store conn_cnt
	tcp-request connection track-sc0 src
	# 注意是 sc0_conn_cnt 而不是 sc0_conn_cnt(0)：带下表的关键字本身就已经指定了
	# tracker，再给个括号会被当成「第几个 table」而报 unable to find table '0'。
	tcp-request connection reject if { sc0_conn_cnt gt @RATE_LIMIT@ }

	default_backend kms_srv

backend kms_srv
	server kms n1bus-rsc4d:1688 check
