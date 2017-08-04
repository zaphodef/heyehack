/*
 * HeyeHack
 * Copyright 2017 Pierre-Jean Grenier
 * Licensed under MIT 
 */
#include<stdio.h>
#include<string.h>
#include<stdlib.h>
#include<arpa/inet.h>
#include<netinet/in.h>
#include<stdbool.h>

#include "dns.h"

bool check_aaaa(uint8_t *dns_buf) {
    return check_question_type(dns_buf, TYPE_AAAA);
}

bool check_a(uint8_t *dns_buf) {
    return check_question_type(dns_buf, TYPE_A);
}

bool check_question_type(uint8_t *dns_buf, int type) {
	// dns_buff points to the start of the DNS data
	
    // parse the DNS headers
	dns_header *hdr = (dns_header*)dns_buf;
	dns_buf += sizeof(dns_header);
	
	int cnt_questions = ntohs(hdr->qd_count);
	// go through the questions
	for (int i=0; i<cnt_questions; ++i) {
		// get the requested name
		uint8_t *name = malloc(75);
		int len;
		get_domain_name((uint8_t*) dns_buf, (uint8_t*) hdr, name, &len);
		dns_buf += len;

		// get the question on the domain
		question *ques = (question*)dns_buf;
		if (ntohs(ques->qtype) == type) {
			return true;
		} 
	}
	return false;
}

// read the domain name in the DNS query, and put it in domain_name
// domain_name must have been initialized through malloc or similar
void extract_domain_query(uint8_t *dns_buf, uint8_t *domain_name)
{
	// dns_buff points to the start of the DNS data
	
    // parse the DNS headers
	dns_header *hdr = (dns_header*)dns_buf;
	dns_buf += sizeof(dns_header);
	
	int cnt_questions = ntohs(hdr->qd_count);
	// go through the questions
	for (int i=0; i<cnt_questions; ++i) {
		// get the requested name
		int len;
		get_domain_name((uint8_t*) dns_buf, (uint8_t*) hdr, domain_name, &len);
		dns_buf += len;
	}

}

int extract_a_delay(char *domain_name) {
    char *p = strtok(domain_name, ".");
    p = strtok(p, "-");
    p = strtok(NULL, "-");
    char *a_delay_str = strtok(NULL, "-");
    
    int a_delay = 0;
    if (a_delay_str != NULL) a_delay = atoi(a_delay_str);
    return a_delay;
}

int extract_aaaa_delay(char *domain_name) {
    char *p = strtok(domain_name, ".");
    p = strtok(p, "-");
    char *aaaa_delay_str = strtok(NULL, "-");

    int aaaa_delay = 0;
    if (aaaa_delay_str != NULL) aaaa_delay = atoi(aaaa_delay_str);
    return aaaa_delay;
}

void get_domain_name(uint8_t *p, uint8_t *buff, uint8_t *name, int *position)
{
    // ré-écrit pour gérer correctement les pointeurs
    
    // true iif the buffer uses compression (see below)
    bool compressed = false;
    
    int i = 0;
    
    // real length of the buffer, that is if we use compression,
    // the length will be smaller
    //     eg. 01 62 c0 5f will have buffer_len 4
    //         but the actual host_name is longer, because
    //         we use compression and concatenate what is
    //         at position 5f immediatly after 01 62
    int buffer_len = -1;
    
    while(*p!=0)
    {
        // the rest of the chain points to somewhere else
        if ((*p & 0xc0) == 0xc0) {
            //	The pointer takes the form of a two octet sequence:
            //
            //	    +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
            //	    | 1  1|                OFFSET                   |
            //	    +--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
            //
            //	The first two bits are ones. The OFFSET field specifies an offset from
            //	the start of the message (i.e., the first octet of the ID field in the
            //	domain header).
            
            uint16_t offset = ntohs(*((uint16_t*)p)) & 0x3fff;
            p = buff+offset;
            
            // +2 comes from c0 xx, where xx is the address
            // the pointer points to
            if (!compressed){
                buffer_len = i+2;
                compressed = true;
            }
            
        }
        uint8_t num = *((uint8_t*)p);
        strncpy((char*)(name+i), (char*)(p+1), num);
        p+= (num+1);
        i+= num;
        strncpy((char*)(name+i), ".", 1);
        i++;
    }
    *(name+i)='\0';
    
    // +1 because we take into account the null-length end character,
    // which is not present when using a pointer (ie. when we use
    // compression). Indeed, the pointer points to a chain already
    // ending by the \0 char
    if (compressed == false) buffer_len = i+1;
    
    // position can change both when there is compression
    // and when there is not. Thus, use not_compressed_len to see
    // if we moved forward in the chain
    if(buffer_len > 0) *position = buffer_len;
}

