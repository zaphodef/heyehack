#!/bin/bash

if [[ $EUID > 0 ]]; then 
    echo "Must be run as root"
    exit 1
fi

echo "Launching, please wait.."
echo "ctrl-c to exit"
echo ""

run_folder=/var/run/heyehack
running_file=$run_folder/running
reload_file=$run_folder/reload

function rule_apache {
    echo "OUTPUT -t mangle -p tcp -o ens3 -m multiport --sport $1:$2 --tcp-flags ALL SYN,ACK -j NFQUEUE --queue-num $3"
}
rule_dns="OUTPUT -t mangle -p udp -o ens3 --sport 53 -j NFQUEUE --queue-num 42000"

mkdir -p $run_folder
rm -f $reload_file
mkfifo $reload_file

pid0=$$
echo $pid0 > $run_folder/heyehack.pid

function set_filters {
    pids_filters=""
    /home/pgrenier/happy-eyeballs/filter 42000 aaaa a &
    pids_filters+="$! "
    /home/pgrenier/happy-eyeballs/filter 42004 port_v4 &
    pids_filters+="$! "
    /home/pgrenier/happy-eyeballs/filter 42006 port_v6 &
    pids_filters+="$! "
}

function set_queues {
    pids_queues=""
    for i in {1..5000}; do
        /home/pgrenier/happy-eyeballs/sleep_queue $i $i &
        pids_queues+="$! "
    done
}

function set_iptables {
    iptables -A $(rule_apache 10001 10499 42004)
    ip6tables -A $(rule_apache 10501 10999 42006)
    ip6tables -A $rule_dns
    iptables -A $rule_dns
}

function launch_server {
    /home/pgrenier/happy-eyeballs/server.py > /var/log/heyehack.log &
    pid_server=$!
}

function set_all {
    set_iptables
    set_queues
    echo $pids_queues > $run_folder/queues.pid
    set_filters
    echo $pid_filters > $run_folder/filters.pid
    launch_server
    echo $pid_server > $run_folder/server.pid
    echo 1 > $running_file
    echo "Launched!"
}

function kill_filters {
    kill $pids_filters
    echo "killed filters"
}

function kill_queues {
    kill $pids_queues
    echo "killed queues"
}

function kill_server {
    kill $pid_server
    echo "killed server"
}

function reset_iptables {
    iptables -D $(rule_apache 10001 10499 42004)
    ip6tables -D $(rule_apache 10501 10999 42006)
    ip6tables -D $rule_dns
    iptables -D $rule_dns
}

function reset {
    echo "Resetting all parameters back, DO NOT ABORT."
    kill_filters
    kill_queues
    kill_server
    reset_iptables
    echo "Back to normality - at the probability of two to the power of 276,709 to one against!"
}

function restart_all {
    echo ""
    echo "Restart everyting..."
    reset 
    set_all
}

function quit {
    echo 0 > $running_file
    reset
}

trap 'quit; wait $pid_server' EXIT
trap restart_all USR1

set_all

while true; do
    sleep 1
done
