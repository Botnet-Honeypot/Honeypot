#!/bin/bash
# script for limiting the bandwidth on all ports except the IANA unregistered port range
# adapted from https://unix.stackexchange.com/questions/76495/which-set-of-commands-will-limit-the-outgoing-data-rate-to-x-kbps-for-traffic-to

# network interface on which to limit traffic
IF="eth0"
# limit of the network interface in question
LINKCEIL="1gbit"
# rate of default limit
LIMIT1="10mbit"
# rate of super-limit
LIMIT2="1kbit"

# delete existing rules
tc qdisc del dev ${IF} root

# add root class, 1:11 default for all unspecified traffic
tc qdisc add dev ${IF} root handle 1: htb default 11

# add parent class
tc class add dev ${IF} parent 1: classid 1:1 htb rate ${LINKCEIL} ceil ${LINKCEIL}

# add our classes.
# 1:10 unlimited bandwidth
# 1:11 limited to LIMIT1 bandwidth, default for all unspecified traffic
# 1:12 super-limited to LIMIT2 bandwidth
tc class add dev ${IF} parent 1:1 classid 1:10 htb rate ${LINKCEIL} ceil ${LINKCEIL} prio 0
tc class add dev ${IF} parent 1:1 classid 1:11 htb rate ${LIMIT1} ceil ${LIMIT1} prio 1
tc class add dev ${IF} parent 1:1 classid 1:12 htb rate ${LIMIT2} ceil ${LIMIT2} prio 2

# add handles to our classes so packets marked with <x> go into the class with "... handle <x> fw ..."
tc filter add dev ${IF} parent 1: protocol ip prio 1 handle 1 fw classid 1:10
tc filter add dev ${IF} parent 1: protocol ip prio 2 handle 2 fw classid 1:11
tc filter add dev ${IF} parent 1: protocol ip prio 3 handle 3 fw classid 1:12

# sends packets in port range 49152:65535 to 1:10 (unlimited)
# sends packets in port list  21,22,23,25,53,110,135,137,138,139,1433,1434 to 1:12 (super-limited by LIMIT2)
# sends all other packets to 1:11 (limited by LIMIT1)
iptables -t mangle -A OUTPUT -p tcp --match multiport --sport 49152:65535 -j MARK --set-mark 0x1
iptables -t mangle -A OUTPUT -p tcp --match multiport --dport 49152:65535 -j MARK --set-mark 0x1
iptables -t mangle -A OUTPUT -p tcp --match multiport --sports 21,22,23,25,53,110,135,137,138,139,1433,1434 -j MARK --set-mark 0x3
iptables -t mangle -A OUTPUT -p tcp --match multiport --dports 21,22,23,25,53,110,135,137,138,139,1433,1434 -j MARK --set-mark 0x3
iptables -t mangle -A OUTPUT -p tcp -j MARK --set-mark 0x2