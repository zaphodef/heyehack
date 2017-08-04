/*
 * HeyeHack
 * Copyright 2017 Pierre-Jean Grenier
 * Licensed under MIT 
 */
#include <stdio.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <linux/netfilter.h>		/* for NF_ACCEPT */
#include <errno.h>
#include <stdbool.h>
#include <string.h>
#include <libnetfilter_queue/libnetfilter_queue.h>

#include "dns.h"
#include "timestamp.h"

#define ETH_HDR 14
#define IPv4_HDR 20
#define IPv6_HDR 40
#define UDP_HDR 8

#define nb_filters 5
#define mark_filter 0
#define a_filter 1
#define aaaa_filter 2
#define port_v4_filter 3
#define port_v6_filter 4

bool active_filter[nb_filters] = {false};
uint16_t queue_number_from = 0;

static uint16_t deduce_delay_from_port(uint16_t port) {
    int delta_port = 0;
    if (port < 10000 || port >= 11000) return 0;
    else if (port >= 10000 && port < 10500) {
        delta_port = port - 10000;
    }
    else if (port >= 10500 && port < 11000) {
        delta_port = port - 10500;
    }

    uint16_t delay=0;
    /*
     * 500 ports for each protocol
     * 0<=delay<=600 : granularity of 2 (delta_port between 0 and 300)
     * 601<=delay<=1000 : granularity of 4 (delta_port between 301 and 400)
     * 1001<=delay<=2999 : granularity of 20 (delta_port between 401 and 499)
     */
    if (delta_port <= 300) delay = delta_port*2;
    else if (delta_port <= 400) delay = 600 + (delta_port-300)*4;
    else if (delta_port < 500) delay = 1000 + (delta_port-400)*20;

    return delay;
}

static void treat_packet(struct nfq_data *tb, u_int32_t *id,
        u_int32_t *mark, u_int32_t *verdict, int *len_data, unsigned char **data)
{
    int ret = 0;
    struct nfqnl_msg_packet_hdr *ph;

    u_int32_t old_mark = nfq_get_nfmark(tb);
    *mark = get_current_timestamp();

    // default : accept packet
    *verdict = NF_ACCEPT;
    
    ph = nfq_get_msg_packet_hdr(tb);
    if (ph) *id = ntohl(ph->packet_id);

    ret = nfq_get_payload(tb, data);
    if (ret <= 0) return;
    *len_data = ret;

    // we will use buf and not data to keep
    // data pointing to the first byte of the packet
    uint8_t *buf = *data;

    // go after the IP headers
    uint8_t *first_byte = buf;
    uint8_t ip_version = *first_byte >> 4;
    int IP_HDR;
    if (ip_version == 6) IP_HDR = IPv6_HDR;
    else if (ip_version == 4) IP_HDR = IPv4_HDR;
    else {
        printf("ERROR: IP version not supported: %i. Skipping packet.\n", ip_version);
        return;
    }

    // NF_QUEUE injects the packet into a different queue 
    // (the target queue number is the high 16 bits of the verdict)
    if (active_filter[mark_filter]) {	
        // The mark on the packet is supposed to contain the sleep time
        // It could have been marked by the iptables for instance
        *verdict = NF_QUEUE;
        ((uint16_t*)verdict)[1] = (uint16_t)old_mark;
        printf("Mark filter shoud not be used.\n");
    } else if (active_filter[port_v4_filter]) {
        // go after the IP headers
        buf += IPv4_HDR;
        uint16_t *ports = (uint16_t*)buf;
        uint16_t src_port = ntohs(ports[0]);
        // uint16_t dst_port = ntohs(ports[1]);
        *verdict = NF_QUEUE;
        ((uint16_t*)verdict)[1] = deduce_delay_from_port(src_port);
    } else if (active_filter[port_v6_filter]) {
        // go after the IP headers
        buf += IPv6_HDR;
        uint16_t *ports = (uint16_t*)buf;
        uint16_t src_port = ntohs(ports[0]);
        // uint16_t dst_port = ntohs(ports[1]);
        *verdict = NF_QUEUE;
        ((uint16_t*)verdict)[1] = deduce_delay_from_port(src_port);
    } else if (active_filter[aaaa_filter] && check_aaaa(buf+IP_HDR+UDP_HDR)) {
        // go after the headers
        buf += IP_HDR;
        buf += UDP_HDR;

        // domain_name is expected to contain the delay
        // format expected: 
        //     {6 random hexa char}-{AAAA delay}-{A delay}.ds.ds.6cn-prs.6cn.io
        uint8_t *domain_name = malloc(60);
        extract_domain_query(buf, domain_name);
         
        int aaaa_delay = extract_aaaa_delay((char*)domain_name);

        if (aaaa_delay > 0) {
            *verdict = NF_QUEUE;
            ((uint16_t*)verdict)[1] = aaaa_delay;
        } 
        free(domain_name);
    } else if (active_filter[a_filter] && check_a(buf+IP_HDR+UDP_HDR)) {
        // go after the headers
        buf += IP_HDR;
        buf += UDP_HDR;

        uint8_t *domain_name = malloc(60);
        extract_domain_query(buf, domain_name);
        
        int a_delay = extract_a_delay((char*)domain_name);
        if (a_delay > 0) {
            *verdict = NF_QUEUE;
            ((uint16_t*)verdict)[1] = a_delay;
        } 
        free(domain_name);
    }

}

static int cb(struct nfq_q_handle *qh, struct nfgenmsg *nfmsg,
        struct nfq_data *nfa, void *data)
{
    unsigned char *packet = NULL;
    int len_packet = 0;
    u_int32_t verdict, id, mark = 0;
    treat_packet(nfa, &id, &mark, &verdict, &len_packet, &packet);
    return nfq_set_verdict2(qh, id, verdict, mark, len_packet, packet);
}

void print_usage(char *program_name) {
    fprintf(stderr, "Usage : %s FROM_QUEUE filter...\n", program_name);
    fprintf(stderr, "\tMonitor the queue number FROM_QUEUE\n\n");
    fprintf(stderr, "\tIf the packet matches the filter, send it to a sleeping queue\n\n");
    fprintf(stderr, "\tfilter can be:");
    fprintf(stderr, "\tmark\tLet go everything through (sleep time based on the mark)");
    fprintf(stderr, "\t4a\tFilter all DNS packets that have an AAAA record\n");
    fprintf(stderr, "\taaaa\n\n");
    fprintf(stderr, "\ta\tFilter all DNS packets that have an A record\n");
}

int main(int argc, char **argv)
{
    struct nfq_handle *h;
    struct nfq_q_handle *qh;
    int fd, rv;
    char buf[4096] __attribute__ ((aligned));

    if (argc < 2) {
        print_usage(argv[0]);
        exit(1);
    }

    queue_number_from = atoi(argv[1]);
    printf("Monitoring queue number %i\n", queue_number_from);

    for (int i=2; i<argc; ++i) {
        if (strcmp(argv[i], "mark") == 0) {
            active_filter[mark_filter] = true;
            printf("\"Mark\" filter detected, on queue %i\n", queue_number_from);
            break;
        }

        if (strcmp(argv[i], "port_v4") == 0) {
            active_filter[port_v4_filter] = true;
            printf("\"Port v4\" filter detected, on queue %i\n", queue_number_from);
            break;
        }

        if (strcmp(argv[i], "port_v6") == 0) {
            active_filter[port_v6_filter] = true;
            printf("\"Port v6\" filter detected, on queue %i\n", queue_number_from);
            break;
        }

        if (strcmp(argv[i], "a") == 0) {
            active_filter[a_filter] = true;
            printf("\"A\" filter detected, on queue %i\n", queue_number_from);
            continue;
        }

        if (strcmp(argv[i], "aaaa") == 0 || strcmp(argv[i], "4a") == 0) {
            active_filter[aaaa_filter] = true;
            printf("\"AAAA\" filter detected, on queue %i\n", queue_number_from);
            continue;
        }

        printf("Filter \"%s\" is not implemented! Skipping.\n", argv[i++]);
    }

    h = nfq_open();
    if (!h) {
        fprintf(stderr, "error during nfq_open()\n");
        exit(1);
    }

    // printf("unbinding existing nf_queue handler for AF_INET (if any)\n");
    if (nfq_unbind_pf(h, AF_INET6) < 0) {
        fprintf(stderr, "error during nfq_unbind_pf()\n");
        exit(1);
    }

    if (nfq_bind_pf(h, AF_INET6) < 0) {
        fprintf(stderr, "error during nfq_bind_pf()\n");
        exit(1);
    }

    // printf("binding this socket to queue '0'\n");
    qh = nfq_create_queue(h, queue_number_from, &cb, NULL);
    if (!qh) {
        fprintf(stderr, "error during nfq_create_queue()\n");
        exit(1);
    }

    if (nfq_set_mode(qh, NFQNL_COPY_PACKET, 0xffff) < 0) {
        fprintf(stderr, "can't set packet_copy mode\n");
        exit(1);
    }

    fd = nfq_fd(h);

    for (;;) {
        if ((rv = recv(fd, buf, sizeof(buf), 0)) >= 0) {
            nfq_handle_packet(h, buf, rv);
            continue;
        }
        if (rv < 0 && errno == ENOBUFS) {
            printf("losing packets!\n");
            continue;
        }
        perror("recv failed");
        break;
    }

    nfq_destroy_queue(qh);
    nfq_close(h);

    exit(0);
}
