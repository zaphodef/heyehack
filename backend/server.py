#!/usr/bin/env python3
import sys
import socket
import threading
import re
import subprocess
import copy
import os
import pymysql
import time
import datetime
import resource
import signal
from tstp_defaultdict import tstp_defaultdict
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# If the lock timeout is (really) too high, the client might
# re-use the same TCP port to make another GET request.
# We would consequently misinterprete the data parsed
# (the data collected for the 2nd usage of that particular
# TCP port could be thought to be data for the 1st usage)
# On the other hand, if it is too low, the parser will not
# have enough time to get the relevant data, and the session
# will not be fully logged.
LOCK_TIMEOUT = 20

# The GC will try to clean all unused memory every
# GC_CLEAN seconds, and any data that haven't been
# used for at least GC_EXPIRE_DELAY seconds will be
# deleted
GC_CLEAN = 30
GC_EXPIRE_DELAY = 60

# Constant: one day in microseconds (us)
ONE_DAY_IN_US = 24*3600*1000*1000

###
# This is used for debug purposes
###
locked = 0
count_get = 0
count_lock = threading.Lock()


def incr_lock():
    global locked
    count_lock.acquire()
    locked += 1
    count_lock.release()


def decr_lock():
    global locked
    count_lock.acquire()
    locked -= 1
    count_lock.release()

###


class HeyeHackHTTPRequestHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    close_connection = True

    def log_message(self, format_p, *args):
        return

    def escape(self, string):
        return re.sub("[^0-9a-zA-Z\-\._]+", "", string)

    def get_domain(self):
        """Get the domain of the host requested."""
        # full_host is: host[:port]
        full_host = self.headers.get('Host')
        full_host = self.escape(full_host)
        return full_host.split(":")[0]

    def get_seed(self):
        """
        Extract and return the seed from the domain.
        eg. the seed of de9-50-0.test.ds.6cn-prs.6cn.io
            is de9-50-0
        """
        return self.get_domain().split(".")[0]

    def get_callback(self):
        """
        Get the callback, for JSONP requests.
        The name of the callback is handle like a PHP argument,
        eg. http://de9-50-0.test.ds.6cn-prs.6cn.io/ip?callback=mycallback
        """
        callback = self.path.split("callback=")[1].split("&")[0]
        return self.escape(callback)

    def get_ip_client(self):
        """Get the IP of the client."""
        return self.client_address[0]

    def get_port_client(self):
        """Get the port the client is connected from."""
        return str(self.client_address[1])

    def get_user_agent(self):
        """Get the user-agent of the client."""
        return self.headers['user-agent']

    def deduce_dns_delays(self):
        """
        Deduce the DNS delays from the seed.
        @return: (delay A, delay AAAA)
        """
        seed = self.get_seed()
        parts = seed.split("-")
        if (len(parts) < 3):
            return (0, 0)
        else:
            return (min(5000, int(parts[2])), min(5000, int(parts[1])))

    def deduce_synack_delays(self):
        """
        Deduce the SYN-ACK delays from the port used.
        @return: (SYN-ACK/IPv4, SYN-ACK/IPv6)
        """
        port = self.server.server_address[1]
        delta_port = 0
        delay_v6 = None

        if (port < 10000 or port >= 11000):
            return (None, None)
        if (port >= 10000 and port < 10500):
            delta_port = port - 10000
            delay_v6 = False
        elif (port >= 10500 and port < 11000):
            delta_port = port - 10500
            delay_v6 = True

        delay = 0
        if (delta_port <= 300):
            delay = delta_port*2
        elif (delta_port <= 600):
            delay = 600 + (delta_port-300)*4
        elif (delta_port < 500):
            delay = 1000 + (delta_port-400)*20

        if (delay_v6):
            return (0, delay)
        else:
            return (delay, 0)

    def format_delay(self, x):
        if (type(x) == str) and (x[0] == "d"):
            return int(x[1:])
        else:
            # x is not a delay, return None
            return None

    def do_GET(self):
        """
        Handle the GET requests.
        The server only serves the /ip page, and you need to specify
        the callback parameter to get an answer.
        When the page requested is anything else than /ip, return
        a 404 error.
        """
        global dict_dns, dict_synack, dict_conditions, sql_queue, count_get

        count_get += 1

        if (self.path.startswith("/ip?callback")):
            callback = self.get_callback()
            ip_client = self.get_ip_client()
            port_client = self.get_port_client()

            type_ip = "ipv6"
            if (len(ip_client.split(".")) == 4):
                type_ip = "ipv4"
                ip_client = ip_client.replace("::ffff:", "")  # IPv6 <-> IPv4

            # If we have RTT info, return it to the client so that the
            # webbrowser can show it.
            rtt = None
            str_rtt = "null"
            if ip_client in dict_rtt and len(dict_rtt[ip_client]) >= 3:
                rtt = sum(dict_rtt[ip_client])/len(dict_rtt[ip_client])
                str_rtt = "%.1f" % (rtt/1000.)

            # the content we will send to the client
            content = callback + '({"ip":"' + ip_client + '","type":"' \
                    + type_ip + '","rtt":' + str_rtt + '});\n'

            self.send_response(200)
            self.send_header('Content-type', 'text/plain;charset=UTF-8')
            self.send_header('Content-Length', len(content))
            self.send_header('Pragma', 'no-cache')
            self.send_header('Cache-Control', 'no-cache')

            # We ask to close the connection at the end of this transaction,
            # in order not to have to many opened files by Python
            self.send_header('Connection', 'close')

            self.end_headers()

            # write content as utf-8 data
            self.wfile.write(bytes(content, "utf8"))

            ###
            # log the session
            ###
            # check whether logreader has already parsed the relevant logs,
            # and if not, acquire a lock and wait for the signal from logreader
            # when it has the info we want
            seed = self.get_seed()
            # print("[http_server] Found link:", seed, ip_client+"."+port_client)

            # incr_lock()
            dict_conditions[ip_client+"."+port_client].acquire()
            try:
                t0 = time.time()
                while not ("done" in dict_synack[ip_client+"."+port_client]):
                    dict_conditions[ip_client+"."+port_client].wait(LOCK_TIMEOUT)
                    t1 = time.time()
                    if ("done" not in dict_synack[ip_client+"."+port_client] and t1-t0 >= LOCK_TIMEOUT):
                        print("[http_server] Timeout on lock", ip_client+"."+port_client, "ie.", seed, "will not log this session")
                        return
                    elif ("abort" in dict_synack[ip_client+"."+port_client]):
                        print("[http_server] Received abort signal for ", ip_client+"."+port_client, "ie.", seed, "will not log this session")
                        return
            except Exception as e:
                print("ERROR:", e.__class__.__name__, e)
            finally:
                dict_conditions[ip_client+"."+port_client].release()
                # decr_lock()

            delay_a_th, delay_aaaa_th = self.deduce_dns_delays()
            delay_acksyn_v4_th, delay_acksyn_v6_th = self.deduce_synack_delays()
            delay_a_mes = dict_dns[seed].get("A", None)
            delay_aaaa_mes = dict_dns[seed].get("AAAA", None)

            delay_synack_v4_mes = None
            delay_synack_v6_mes = None
            if (dict_synack[ip_client+"."+port_client]["ipversion"] == "ipv6"):
                delay_synack_v6_mes = dict_synack[ip_client+"."+port_client]["value"]
            elif (dict_synack[ip_client+"."+port_client]["ipversion"] == "ipv4"):
                delay_synack_v4_mes = dict_synack[ip_client+"."+port_client]["value"]
            else:
                print("ERROR: unknown ip version")
                return

            delay_a_mes = self.format_delay(delay_a_mes)
            delay_aaaa_mes = self.format_delay(delay_aaaa_mes)
            delay_synack_v4_mes = self.format_delay(delay_synack_v4_mes)
            delay_synack_v6_mes = self.format_delay(delay_synack_v6_mes)

            # Wait until the main thread has copied the
            # data to insert into the SQL database.
            lock_sql.acquire()
            try:
                while sql_updating:
                    lock_sql.wait()
            finally:
                lock_sql.release()

            sql_queue.append((self.get_user_agent(), delay_aaaa_th, delay_a_th,
                                delay_acksyn_v4_th, delay_acksyn_v6_th,
                                delay_aaaa_mes, delay_a_mes, delay_synack_v4_mes,
                                delay_synack_v6_mes, type_ip, ip_client, rtt))

            ###
            # "free" memory
            ###
            # incr_lock()
            dict_conditions[ip_client+"."+port_client].acquire()
            try:
                del dict_synack[ip_client+"."+port_client]
                del dict_dns[seed]
            except Exception as e:
                print("ERROR:", e.__class__.__name__, e)
            finally:
                dict_conditions[ip_client+"."+port_client].release()
                # decr_lock()
        else:
            # the client asked for something else than /ip or didn't
            # passed a correct "callback" parameter
            self.send_response(404)
            self.send_header('Content-type', 'text/plain;charset=UTF-8')
            self.send_header('Connection', 'close')
            self.end_headers()

        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """
    Handle every request in a new thread.
    """
    address_family = socket.AF_INET6


class server(threading.Thread):
    def __init__(self, port, handler):
        super().__init__()
        self.port = port
        self.handler = handler
        self.httpd = None

    def run(self):
        server_address = ('::', self.port)
        self.httpd = ThreadedHTTPServer(server_address, self.handler)
        try:
            self.httpd.serve_forever()
        except Exception as e:
            print("ERROR: (server)", e.__class__.__name__, e)

    def shutdown(self):
        if (self.httpd):
            self.httpd.shutdown()


class ServerKiller(threading.Thread):
    def __init__(self, server):
        # server must be an instance of the server class
        self.server = server
        super().__init__()

    def run(self):
        self.server.shutdown()


def timestamp_to_us(tms):
    """
    Converts a tcpdump-formated timestamp to microseconds.
    """
    # us stands for microseconds
    # timestamp is formatted like 10:57:34.468898
    us = -1
    try:
        s = int(tms[0:2])*3600 + int(tms[3:5])*60 + int(tms[6:8])
        us = s*1000000 + int(tms[9:15])
    finally:
        return us


def delta(t0, t1):
    """
    Do t1-t0 but if t0 was just before midnight and t1 right after,
    corrects the subtraction to get the right delta.
    @param t0, t1: output of timestamp_to_us()
    """
    # one day in microseconds
    res = t1 - t0
    if (res < 0):
        res = (ONE_DAY_IN_US - t0) + t1
    return res


# TODO: make 2 parsers? one for DNS, one for TCP
# (more efficient? no "fail regex check" because bad type)
class LogReader(threading.Thread):
    def __init__(self):
        self.count = 0
        self.p = None
        # tcpdump DNS entry regex
        self.dns_r = re.compile("([0-9\:\.]+) (IP|IP6) ([0-9a-f\:\.]+)\.([0-9]+) > ([0-9a-f\:\.]+)\.([0-9]+): ([0-9]+)(\*?).+ (A|AAAA)(?:\? (.+-[0-9]*-[0-9]*)\..*\.ds\.6cn-prs\.6cn\.io| (?:163\.172\.77\.214|2001:bc8:2543:100::1:2))")
        # tcpdump TCP entry regex
        self.tcp_r = re.compile("([0-9\:\.]+) (IP|IP6) ([0-9a-f\:\.]+)\.([0-9]+) > ([0-9a-f\:\.]+)\.([0-9]+): Flags \[([SAFRUPEW\.]{1,})\].+ length ([0-9]+)")
        # dameon will cause the thread to be killed when there is no more
        # non-daemon threads running
        super().__init__(daemon=True)

    def run(self):
        global dict_dns, dict_synack, dict_conditions

        # This dict will allow us to match transaction ids to the domains requested.
        # This way, when answering back to the client, we will be able to know what
        # the request was.
        global dict_dns_transactions

        # 2 is the mask for the SYN flag in 'tcp[13] & 2'
        # 'tcp' expression doesn't work for IPv6, see http://seclists.org/tcpdump/2010/q4/103
        # and tcpdump manual; if using IPv6 we check that the header right after IP header
        # is the TCP header (it could be something else... TODO: handle it), and then
        # we look up for the SYN flag in the TCP header
        self.p = subprocess.Popen(('tcpdump', '-n', '-l', '(', 'portrange', '10000-11000', 'and', '(', 'tcp[13]', '&', '2', '!=', '0', 'or', '(', 'ip6[6]', '=', '6', 'and', 'ip6[53]', '&', '2', '!=', '0', ')', ')', ')', 'or', 'port', '53'), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(self.p.stdout.readline, b''):
            # print("[parsing] (%i) (%i) Parsing:" % (self.count, len(line)), line)
            line = line.decode('utf-8')
            self.count += 1
            result = self.tcp_r.search(line)
            if result:
                tms, ipversion, ip_src, port_src, ip_dst, port_dst, flags, length = result.groups()
                ipversion = "ipv6" if ipversion == "IP6" else "ipv4"
                us = timestamp_to_us(tms)
                if (us < 0):
                    print("WARNING: timestamp not recognized, skipping.", tms)
                    continue
                length = int(length)

                if ("S" in flags) and not ("." in flags) and (ip_dst in ("192.168.3.2", "2001:bc8:2543:100::1:2")) and (length == 0):
                    # this is the SYN
                    # incr_lock()
                    dict_conditions[ip_src+"."+port_src].acquire()
                    try:
                        dict_synack[ip_src+"."+port_src]["value"] = "#" + str(us)
                        dict_synack[ip_src+"."+port_src]["ipversion"] = ipversion
                    except Exception as e:
                        print("ERROR: (SYN)", e.__class__.__name__, e)
                    finally:
                        dict_conditions[ip_src+"."+port_src].release()
                        # decr_lock()

                if ("S" in flags) and ("." in flags) and (ip_src in ("192.168.3.2", "2001:bc8:2543:100::1:2")) and (length == 0):
                    # this is the SYN-ACK
                    # incr_lock()
                    dict_conditions[ip_dst+"."+port_dst].acquire()
                    try:
                        if (ip_dst+"."+port_dst) not in dict_synack:
                            # because was deleted by the server?
                            print("WARNING: key", (ip_dst+"."+port_dst), "not found in dict_synack, skipping")
                            continue

                        if (dict_synack[ip_dst+"."+port_dst]["ipversion"] != ipversion):
                            print("ERROR: IP version changed between SYN and SYN-ACK, on " + ip_dst+"."+port_dst)
                            continue

                        us_0 = dict_synack[ip_dst+"."+port_dst]["value"]
                        if (type(us_0) != str):
                            # in case of re-emission (?) -> the program here expects a timestamp,
                            # not a time elapsed
                            print("WARNING: (SYN-ACK) timestamp for", ip_dst+"."+port_dst,
                                    "is not a string as expected:", us_0,
                                    "Skipping.")
                            continue

                        if (us_0[0] != "#"):
                            print("WARNING: (SYN-ACK) timestamp for", ip_dst+"."+port_dst,
                                    "doesn't look right:", us_0,
                                    "Skipping.")
                            continue

                        # TODO: make function to store us_0 and unstore it
                        # dict_synack[ip_dst+"."+port_dst]["value"] is something like
                        #   "#BIG_NUMBER"
                        us_0 = int(us_0[1:])
                        dict_synack[ip_dst+"."+port_dst]["value"] = "d" + str(delta(us_0, us))
                        dict_synack[ip_dst+"."+port_dst]["done"] = True
                        dict_conditions[ip_dst+"."+port_dst].notifyAll()
                    except Exception as e:
                        print("ERROR: (SYN-ACK)", e.__class__.__name__, e)
                    finally:
                        dict_conditions[ip_dst+"."+port_dst].release()
                        # decr_lock()
            else:
                result = self.dns_r.search(line)
                if not result:
                    continue
                tms, ipversion, ip_src, port_src, ip_dst, port_dst, id_transaction, answer, type_query, seed = result.groups()
                answer = (answer == "*")  # there's a "*" after the transaction_id when this is an answer
                us = timestamp_to_us(tms)
                if (us < 0):
                    print("WARNING: timestamp not recognized, skipping.", tms)
                    continue
                if (answer):
                    id_transaction = ip_dst+"."+port_dst+"#"+id_transaction
                    # incr_lock()
                    dict_conditions[ip_dst+"."+port_dst].acquire()
                    try:
                        if id_transaction not in dict_dns_transactions:
                            # when a dns query asks for some domain that is not in the regex,
                            # the question doesn't match so no transaction id is registered
                            # however the answer matches, hence the check here
                            continue

                        if type_query not in dict_dns[dict_dns_transactions[id_transaction]]:
                            # The client may have already sent the GET query and got
                            # the answer from our server, though we hadn't answered
                            # him yet regarding this DNS query.
                            # This can happen eg. when you send both A and AAAA queries,
                            # get the AAAA answer first, do the TCP handshake and the GET
                            # request, and only then get the A answer.
                            # But at this point, to avoid memory leaks, the server has
                            # already destroyed the key dict_dns_transactions[id_transaction] in dict_dns.
                            # Thus, to avoid further memory leaks, we simply destroy the
                            # key id_transaction in dict_dns_transactions and continue.
                            del dict_dns_transactions[id_transaction]
                            continue

                        us_0 = dict_dns[dict_dns_transactions[id_transaction]][type_query]

                        # We here expect us_0 to be a timestamp, but in some cases it can be a
                        # delay measure.
                        # eg.    A query (d1.tld) -> id X
                        #        AAAA query (d1.tld) -> id Y
                        #        A anwer (d1.tld)
                        #        SYN, SYN-ACK, ACK, GET / IPv4
                        #           <----- client cancels its AAAA query on his side
                        #                  (he can now re-use id Y)
                        #        A query (d2.tld) -> id Z
                        #        AAAA query (d2.tld) -> id Y
                        #        A answer (d2.tld)
                        #        AAAA answer (d2.tld)
                        #        AAAA answer (d1.tld) <---- us_0 is a delay, not a timestamp
                        if (type(us_0) != str):
                            print("WARNING: (DNS) timestamp for", dict_dns_transactions[id_transaction],
                                    type_query, "is not a string as expected:", dict_dns[dict_dns_transactions[id_transaction]][type_query],
                                    "Skipping.")
                            continue

                        if (us_0[0] != "#"):
                            print("WARNING: (DNS) timestamp for", dict_dns_transactions[id_transaction],
                                    type_query, "doesn't look right:", dict_dns[dict_dns_transactions[id_transaction]][type_query],
                                    "Skipping.")
                            continue

                        # dict_dns[dict_dns_transactions[id_transaction]][type_query] is something like
                        #  "#BIG_NUMBER"
                        us_0 = int(us_0[1:])
                        diff = delta(us_0, us)
                        dict_dns[dict_dns_transactions[id_transaction]][type_query] = "d" + str(diff)
                    except Exception as e:
                        print("ERROR: (DNS answer)", e.__class__.__name__, e)
                    finally:
                        dict_conditions[ip_dst+"."+port_dst].release()
                        # decr_lock()

                # we can arrive at this point in various cases:
                #    - the client is emitting this query for the first time,
                #      and type_query is not in dict_dns[seed] because either
                #      it is the first time the client use this ID, or
                #      it is not but we have successfully measured A and AAAA
                #      delays last time, and destroyed them afterwards through
                #      the web server, after it logged the relevant session
                #    - this transaction ID is being re-used for a new query,
                #      and dict_dns[seed][type_query] may contain an actual
                #      time elapsed calculated at some previous iteration,
                #      which has not been destroyed by the web server
                #      for some reason (eg. big delay required, so basically
                #      the answer was parsed way after the web server logged
                #      the session)
                #         eg. A query
                #             AAAA query
                #             A answer
                #             SYN/IPv4
                #             SYN-ACK
                #             ACK
                #             GET
                #                <---- here we log the session and destroy
                #                      A delay measured, and AAAA timestamp
                #                      stored
                #             AAAA query (re-emission)
                #             AAAA answer
                #      (in this case, we HAVE to erase the old value, and
                #       store the new timestamp)
                #    - the client is re-emitting its query
                #      because we haven't answered him yet, but we have
                #      already stored the timestamp of the first query
                #      (in this case we have to keep the original query
                #      to measure the correct delay applied for the answer)
                elif (type_query not in dict_dns[seed]) or (type(dict_dns[seed][type_query]) == int):
                    id_transaction = ip_src+"."+port_src+"#"+id_transaction
                    # incr_lock()
                    dict_conditions[ip_src+"."+port_src].acquire()
                    try:
                        dict_dns_transactions[id_transaction] = seed
                        # the "#" added indicates this is not the time taken to answer
                        # but the timestamp of the query: we still have to parse the DNS answer
                        dict_dns[seed][type_query] = '#'+str(us)
                    except Exception as e:
                        print("ERROR: (DNS query)", e.__class__.__name__, e)
                    finally:
                        dict_conditions[ip_src+"."+port_src].release()
                        # decr_lock()

                else:
                    print("INFO: [parsing] Skipping line that matches no condition:", line[:-1], "checks: (type_query not in dict_dns[seed])?",
                            (type_query not in dict_dns[seed]), "type(dict_dns[seed][type_query])", type(dict_dns[seed][type_query]))


class ACKParser(threading.Thread):
    def __init__(self):
        self.tcp_r = re.compile("([0-9\:\.]+) (IP|IP6) ([0-9a-f\:\.]+)\.([0-9]+) > ([0-9a-f\:\.]+)\.([0-9]+): Flags \[([SAFRUPEW\.]{1,})\].+ ack ([0-9]+), .+ length ([0-9]+)")
        self.p = None
        super().__init__(daemon=True)

    def run(self):
        global dict_rtt, dict_ping_records

        self.p = subprocess.Popen(('tcpdump', '-n', '-l', '(', 'portrange', '10000-11000', 'and', '(', 'tcp[13]', '&', '18', '!=', '0', 'or', '(', 'ip6[6]', '=', '6', 'and', 'ip6[53]', '&', '18', '!=', '0', ')', ')', ')'), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in iter(self.p.stdout.readline, b''):
            line = line.decode('utf-8')
            result = self.tcp_r.search(line)
            if result:
                tms, ipversion, ip_src, port_src, ip_dst, port_dst, flags, ack, length = result.groups()
                us = timestamp_to_us(tms)
                if (us < 0):
                    print("WARNING: timestamp not recognized, skipping.", tms)
                    continue
                length = int(length)

                if ("S" in flags) and ("." in flags) and (ip_src in ("192.168.3.2", "2001:bc8:2543:100::1:2")) and (length == 0):
                    # this is the SYN-ACK
                    dict_ping_records[ip_dst+"."+port_dst] = us
                    # print("[ping parser] parsing", line[:-1])

                if ("S" not in flags) and ("." in flags) and (ip_dst in ("192.168.3.2", "2001:bc8:2543:100::1:2")) \
                        and (length == 0) and (dict_ping_records[ip_src+"."+port_src] != 0) and (ack == '1'):
                    # this is the ACK, and given dict_ping_records[ip_src] != 0, this is the end of
                    # the TCP handshake
                    # we need to ensure ack number is 1, otherwise the ACK analysed could be the answer
                    # to some other signal than the SYN-ACK previously analysed
                    # eg. with re-emission (when SYN-ACK delay):
                    #   [S], [S], [S], [S.], [.], [P.], [S.], [.]

                    # Don't forget to delete this record! (here through .pop())
                    dict_rtt[ip_src].append(delta(dict_ping_records.pop(ip_src+"."+port_src), us))


class GarbageCollector(threading.Thread):
    def __init__(self, run_every=30, expiration_delay=60):
        super().__init__()
        self.RUN_EVERY = run_every
        self.EXPIRATION_DELAY = expiration_delay

    def clean_one_dict(self, d):
        """
        This function assumes d is a tstp_defaultdict().
        It will clean all entries that have not been used
        for self.EXPIRATION_TIME seconds.
        """
        now = datetime.datetime.now()
        delete_after = now - datetime.timedelta(0, self.EXPIRATION_DELAY)

        # We make a copy in order to avoid the RuntimeError
        # "dictionary changed size during iteration",
        # because dict.keys() returns a view, and using
        # list(dict.keys()) is not thread-safe because it is
        # not an atomic operation
        try:
            keys = copy.copy(d.timestamp_use)
            for k in keys:
                # k may not be in to_check anymore due to
                # race condition
                if k in d and d.get_tstp(k) <= delete_after:
                    del d[k]
            del keys
        except RuntimeError as e:
            print("ERROR (GC): RuntimeError (dict length has changed, race condition)")

    def clean(self):
        global dict_dns, dict_synack, dict_conditions, dict_dns_transactions, dict_rtt, dict_ping_records

        # print("[garbage collector] %s GC will now clean unused memory" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
        for d in (dict_dns, dict_synack, dict_conditions, dict_dns_transactions, dict_rtt, dict_ping_records):
            self.clean_one_dict(d)
            # print("[garbage collector] len(dict)=%i" % len(d))

        # print("[garbage collector] %s GC has cleand unused memory" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    def run(self):
        while True:
            for i in range(self.RUN_EVERY):
                time.sleep(1)
                if exit_now:
                    return

            self.clean()


def exit_program(signum, frame):
    global exit_now
    exit_now = True
    print("Exiting, please wait...")


def init_all():
    global dict_dns, dict_synack, dict_conditions, dict_rtt, dict_ping_records, dict_dns_transactions
    global db, sql_insert, sql_queue, sql_updating, lock_sql, list_server, exit_now, logreader, ack_logreader

    if (os.getuid() != 0):
        print("\033[35mMust be run as root\033[0m")
        exit()

    # Catch SIGINT and SIGTERM
    signal.signal(signal.SIGINT, exit_program)
    signal.signal(signal.SIGTERM, exit_program)
    exit_now = False

    # for race conditions in Python with dictionaries, see
    # https://stackoverflow.com/questions/1312331
    dict_dns = tstp_defaultdict(dict)
    dict_synack = tstp_defaultdict(dict)
    dict_conditions = tstp_defaultdict(threading.Condition)
    dict_rtt = tstp_defaultdict(lambda: deque(maxlen=20))
    dict_ping_records = tstp_defaultdict(int)

    # see the usage of this dict in the logreader class
    dict_dns_transactions = tstp_defaultdict(str)

    # This is the connection to the MySQL database to store the logs
    db = pymysql.connect("localhost", "USER", "PASSWORD", "DATABASE")
    sql_insert = """INSERT INTO log(user_agent, delay_aaaa_th, delay_a_th, delay_synack_v4_th, delay_synack_v6_th, \
            delay_aaaa_mes, delay_a_mes, delay_synack_v4_mes, delay_synack_v6_mes, ipversion, ip, rtt) \
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    sql_queue = list()
    sql_updating = False

    # This lock is used by the web servers not to add requests
    # when the main thread processes to an update of the database.
    lock_sql = threading.Condition()

    # We need to set the limit for open files higher than
    # default, because we handle threads that listen
    # on many ports.
    resource.setrlimit(resource.RLIMIT_NOFILE, (4000, 65536))
    # resource.setrlimit(resource.RLIMIT_MEMLOCK, (1048576, 1048576))
    # resource.setrlimit(resource.RLIMIT_NPROC, (1048576, 1048576))

    logreader = LogReader()
    print("Starting main logreader...", end="")
    print("\033[32;1m done\033[0m")
    logreader.start()

    # NB: no native support by python for a real dual-stack server yet
    # IPv4 are mapped to IPv6 by the kernel
    list_server = []
    for port in range(10000, 11000):
        print("Starting servers... \033[36m%i\033[0m" % port, end="\r")
        server_v6 = server(port, HeyeHackHTTPRequestHandler)
        server_v6.start()
        list_server.append(server_v6)
    print("Starting servers... \033[32;1m done\033[0m")

    print("Starting SYN-ACK/ACK logreader... ", end="")
    ack_logreader = ACKParser()
    ack_logreader.start()
    print("\033[32;1m done\033[0m")

    print("Starting the GC... ", end="")
    gc = GarbageCollector(GC_CLEAN, GC_EXPIRE_DELAY)
    gc.start()
    print("\033[32;1m done\033[0m")


def main_loop():
    global sql_queue, sql_updating, db
    while True:
        for i in range(3):
            time.sleep(1)
            if exit_now:
                return

        # print("Currently locked:", locked)

        lock_sql.acquire()

        # for ip in dict_rtt:
        #     print("RTT for %s: %i" % (ip, sum(dict_rtt[ip])/len(dict_rtt[ip])))

        try:
            sql_updating = True
            to_insert = copy.copy(sql_queue)
            sql_queue = []
        finally:
            lock_sql.notifyAll()
            lock_sql.release()
            sql_updating = False

        if len(to_insert) > 0:
            try:
                cursor = db.cursor()
                cursor.executemany(sql_insert, to_insert)
                db.commit()
            except Exception as e:
                print("ERROR (SQL):", e.__class__.__name__, e, to_insert)
                try:
                    db = pymysql.connect("localhost", "pgrenier", "", "heyehack")
                    print("INFO (SQL): re-init database link")
                except:
                    print("ERROR (SQL): cannot re-init database link")
            else:
                t1 = datetime.datetime.now()
                print("Count GET: %i; %s: Database updated" % (count_get, t1.strftime("%Y/%m/%d %H:%M:%S")))
            finally:
                del to_insert
        else:
            print("Count GET: %i" % count_get)

        sys.stdout.flush()


if __name__ == "__main__":
    global dict_synack, dict_conditions, list_server
    try:
        init_all()
        main_loop()
    finally:
        print("Exiting servers...")
        # Kill all servers
        for serv in list_server:
            killer = ServerKiller(serv)
            killer.start()

        print("Terminating waiting processes...")
        # Terminate processes waiting for logging a session
        for cond in dict_conditions:
            if cond in dict_synack:
                dict_conditions[cond].acquire()
                try:
                    dict_synack[cond] = "abort"
                    dict_conditions[cond].notifyAll()
                finally:
                    dict_conditions[cond].release()

        print("Terminating tcpdump listeners")
        logreader.p.kill()
        ack_logreader.p.kill()

        print("Program successfully terminated.")
