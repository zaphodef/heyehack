/*
 * dns.h
 * Authors: jiaziyi, Pierre-Jean Grenier
 */
#include <stdbool.h>

#ifndef DNS_H_
#define DNS_H_

typedef signed char int8_t;
typedef unsigned char uint8_t;
typedef short int16_t;
typedef unsigned short uint16_t;
typedef int int32_t;
typedef unsigned int uint32_t;

#define BUF_SIZE 65536
#define HOST_NAME_SIZE 4096
#define ANS_SIZE 10
#define IN_SIZE 4
#define IN6_SIZE 16

// QR values
#define QR_QUESTION 0
#define QR_ANSWER 1

// query type values
#define TYPE_A 1    //v4
#define TYPE_NS 2    //name server
#define TYPE_CNAME 5 //the canonical name for an alias
#define TYPE_SOA 6    //marks the start of a zone of authority
#define TYPE_WKS 11 //a well known service description
#define TYPE_PTR 12 // a domain name pointer
#define TYPE_HINFO 13 // host information
#define TYPE_MINFO 14 //mailbox or mail list information
#define TYPE_MX 15    //mail exchange
#define TYPE_TXT 16 //txt strings
#define TYPE_AAAA 28 //ipv6

// query class values
#define CLASS_IN 1    // the internet -- that's pretty much we need :)

//DNS general format
//
//+---------------------+
//|        Header       |
//+---------------------+
//|       Question      | the question for the name server
//+---------------------+
//|        Answer       | RRs answering the question
//+---------------------+
//|      Authority      | RRs pointing toward an authority
//+---------------------+
//|      Additional     | RRs holding additional information
//+---------------------+

// DNS header
//                               1  1  1  1  1  1
// 0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|              ID                               |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|QR|   Opcode  |AA|TC|RD|RA| Z|AD|CD|   RCODE   |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|        QDCOUNT/ZOCOUNT                        |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|        ANCOUNT/PRCOUNT                        |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|        NSCOUNT/UPCOUNT        |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|            ARCOUNT            |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

struct dns_header
{
    uint16_t id;
    //    ID          A 16 bit identifier assigned by the program that
    //            generates any kind of query.  This identifier is copied
    //            the corresponding reply and can be used by the requester
    //            to match up replies to outstanding queries.

    // make use of bit fields here  http://www.tutorialspoint.com/cprogramming/c_bit_fields.htm
    uint8_t rd :1; // recursion desired
    uint8_t tc :1; // truncated message
    uint8_t aa :1; // authenticated answer
    uint8_t opcode :4; // purpose of message
    //    This value is set by the originator of a query
    //    and copied into the response.  The values are:
    //      0           a standard query (QUERY)
    //      1           an inverse query (IQUERY)
    //      2           a server status request (STATUS)
    //      3-15        reserved for future use
    uint8_t qr :1; // query/response
    //    QR          A one bit field that specifies whether this message is a
    //            query (0), or a response (1).

    uint8_t rcode :4; // response code.
    //    0           No error condition
    //
    //    1           Format error - The name server was
    //            unable to interpret the query.
    //
    //    2           Server failure - The name server was
    //            unable to process this query due to a
    //            problem with the name server.
    //
    //    3           Name Error - Meaningful only for
    //            responses from an authoritative name
    //            server, this code signifies that the
    //            domain name referenced in the query does
    //            not exist.
    //
    //    4           Not Implemented - The name server does
    //            not support the requested kind of query.
    //
    //    5           Refused - The name server refuses to
    //            perform the specified operation for
    //            policy reasons.  For example, a name
    //            server may not wish to provide the
    //            information to the particular requester,
    //            or a name server may not wish to perform
    //            a particular operation (e.g., zone
    //            transfer) for particular data.
    //
    //    6-15        Reserved for future use.
    uint8_t cd :1; // checking disabled
    uint8_t ad :1; // authenticated data
    uint8_t z :1; // reserved -- must set to 0
    uint8_t ra :1; //recursion available


    uint16_t qd_count;
    //    QDCOUNT     an unsigned 16 bit integer specifying the number of
    //            entries in the question section.
    uint16_t an_count;
    //    ANCOUNT     an unsigned 16 bit integer specifying the number of
    //            resource records in the answer section.
    uint16_t ns_count;
    //    NSCOUNT     an unsigned 16 bit integer specifying the number of name
    //            server resource records in the authority records
    //            section.
    uint16_t ar_count;
    //    ARCOUNT     an unsigned 16 bit integer specifying the number of
    //            resource records in the additional records section.

};
typedef struct dns_header dns_header;

//DNS query
//
//                1  1  1  1  1  1
//  0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|                           |
///             QNAME             /
///                           /
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|             QTYPE             |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|             QCLASS            |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

//only the fixed size part
struct question
{
    uint16_t qtype;
    //    QTYPE       a two octet code which specifies the type of the query.
    //            The values for this field include all codes valid for a
    //            TYPE field, together with some more general codes which
    //            can match more than one type of RR.
    uint16_t qclass;
    //    QCLASS      a two octet code that specifies the class of the query.
    //            For example, the QCLASS field is IN for the Internet.
};
typedef struct question question;

// query
struct query
{
    uint8_t  *qname;
    //    QNAME       a domain name represented as a sequence of labels, where
    //            each label consists of a length octet followed by that
    //            number of octets.  The domain name terminates with the
    //            zero length octet for the null label of the root.  Note
    //            that this field may be an odd number of octets; no
    //            padding is used.
    //        for example, www.abcd.com will become 3www4abcd3com
    question *ques;

};
typedef struct query query;

//                                1  1  1  1  1  1
//  0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|                                               |
///                                               /
///              NAME                             /
//|                                               |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|              TYPE                             |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|             CLASS                             |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|              TTL                              |
//|                                               |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
//|           RDLENGTH                            |
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--|
///             RDATA                             /
///                                               /
//+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

//the fixed size part
struct r_element
{
    uint16_t type;
    //    TYPE        two octets containing one of the RR type codes.  This
    //            field specifies the meaning of the data in the RDATA
    //            field.
    uint16_t _class;
    //    CLASS       two octets which specify the class of the data in the
    //            RDATA field.
    uint32_t ttl;
    //    TTL         a 32 bit unsigned integer that specifies the time
    //            interval (in seconds) that the resource record may be
    //            cached before it should be discarded.  Zero values are
    //            interpreted to mean that the RR can only be used for the
    //            transaction in progress, and should not be cached.
    uint16_t rdlength;
    //    RDLENGTH    an unsigned 16 bit integer that specifies the length in
    //            octets of the RDATA field.
}__attribute((packed));
typedef struct r_element r_element;

//a resource record
struct res_record
{
    uint8_t *name;
    //    NAME        a domain name to which this resource record pertains.
    r_element *element;
    uint8_t *rdata;
    //    RDATA       a variable length string of octets that describes the
    //            resource.  The format of this information varies
    //            according to the TYPE and CLASS of the resource record.
    //            For example, the if the TYPE is A and the CLASS is IN,
    //            the RDATA field is a 4 octet ARPA Internet address.


};
typedef struct res_record res_record;

bool check_question_type(uint8_t *dns_buf, int type);
bool check_aaaa(uint8_t *dns_buf); 
bool check_a(uint8_t *dns_buf); 
void extract_domain_query(uint8_t *dns_buf, uint8_t *domain_name);
int extract_a_delay(char *domain_name);
int extract_aaaa_delay(char *domain_name);
void get_domain_name(uint8_t *p, uint8_t *buff, uint8_t *name, int *position);

#endif /* DNS_H_ */

