/*
 * HeyeHack
 * Copyright 2017 Pierre-Jean Grenier
 * Licensed under MIT 
 */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <netinet/in.h>
#include <linux/netfilter.h>		/* for NF_ACCEPT */
#include <errno.h>
#include <libnfnetlink/libnfnetlink.h>
#include <libnetfilter_queue/libnetfilter_queue.h>

#include "timestamp.h"

int sleep_time = 0;
int queue_number = 0;

static void treat_packet(struct nfq_data *tb, u_int32_t *id,
        u_int32_t *mark, int *verdict, int *len_data, unsigned char **data)
{
    struct nfqnl_msg_packet_hdr *ph;
    *mark = nfq_get_nfmark(tb);
    ph = nfq_get_msg_packet_hdr(tb);
    if (ph) {
        *id = ntohl(ph->packet_id);
    }
    
    // All times are in 10^(-1) ms, that is 100 us
    // except sleep_time that is in ms
    u_int32_t now = get_current_timestamp();
    long packet_waiting_for = now - *mark;
	long wait_for = (long) (sleep_time*10 - packet_waiting_for);
	
    // in the case of wrapping around
    if (wait_for < 0) wait_for = 0;

	// just sleep before accepting packet
    // TODO: adjust time to wait (remove a few us?)
	usleep(wait_for*100);

	// accept all packets
	*verdict = NF_ACCEPT;
}
	

static int cb(struct nfq_q_handle *qh, struct nfgenmsg *nfmsg,
	      struct nfq_data *nfa, void *data)
{
	unsigned char *packet = NULL;
	int verdict, len_packet = 0;
	u_int32_t id, mark = 0;
	treat_packet(nfa, &id, &mark, &verdict, &len_packet, &packet);
	return nfq_set_verdict2(qh, id, verdict, mark, len_packet, packet);
}

int main(int argc, char **argv)
{
	struct nfq_handle *h;
	struct nfq_q_handle *qh;
	int fd, rv;
	char buf[4096] __attribute__ ((aligned));
	
	if (argc != 3) {
		fprintf(stderr, "Usage: %s sleep_time_ms [queue_number]\n", argv[0]);
		exit(1);
	}
	queue_number = atoi(argv[2]);

	sleep_time = atoi(argv[1]);
	// printf("Sleep time set to %i ms on queue %i. After this delay, all packets on this queue will be accepted.\n", sleep_time, queue_number);

	h = nfq_open();
	if (!h) {
		fprintf(stderr, "error during nfq_open()\n");
		exit(1);
	}

	// unbind existing nf_queue handler, if any
	if (nfq_unbind_pf(h, AF_INET6) < 0) {
		fprintf(stderr, "error during nfq_unbind_pf()\n");
		exit(1);
	}

	if (nfq_bind_pf(h, AF_INET6) < 0) {
		fprintf(stderr, "error during nfq_bind_pf()\n");
		exit(1);
	}

	// bind this to queue number queue_number
	qh = nfq_create_queue(h, queue_number, &cb, NULL);
	if (!qh) {
		fprintf(stderr, "error during nfq_create_queue()\n");
		exit(1);
	}

	if (nfq_set_mode(qh, NFQNL_COPY_PACKET, 0xffff) < 0) {
		fprintf(stderr, "can't set packet_copy mode\n");
		exit(1);
	}

	fd = nfq_fd(h);

	// increase queue length
	nfq_set_queue_maxlen(qh, 1500);

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
