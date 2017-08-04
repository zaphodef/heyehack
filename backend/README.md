HeyeHack - a Happy Eyeballs test tool.

Details
====
HeyeHack uses NF\__QUEUES in order to filter packets and make them wait. The packets are enqueued by the iptables just before leaving the server.

All DNS packets over UDP (port 53) are enqueued. Then, based on the domain requested (A or AAAA only), there are sent to a sleep queue to wait the appropriate period of time. Domains are expected to be formatted the following way: SEED-A\_DELAY-AAAA\_DELAY.domain.
    eg. requesting test-0-50 means the AAAA answer will be retained for 50ms by the server, while the A answer will go through with no delay

The packets on ports 10,000-10,999 are also filtered. Those ports are used by the webserver to simulate delays on the ACK-SYN answer. Ports 10,000-10,499 are dedicated to delays over IPv4, while ports 10,500-10,999 are dedicated to delays over IPv6.
    eg. contacting the webserver on port 10,050 over IPv4, the ACK-SYN answer will be delayed by 100ms

License
====
&copy; 2017 Pierre-Jean Grenier
Licensed under the MIT license.

Requirements
=====
* libnetfilter\_queue: https://github.com/fqrouter/libnetfilter\_queue

Installation
====
* Make all binaries : make all
* Change database login in server.py

HOWTO
=====
The webserver, the filters and the queues must be run as root.
To launch the webserver: sudo ./server.py
To launch the filters and the queues, and load the iptables: sudo ./launch.sh
