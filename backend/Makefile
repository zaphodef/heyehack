all: filter sleep_queue

filter: filter.o dns.o timestamp.o
	cc -g -o filter $^ -lnfnetlink -lnetfilter_queue

sleep_queue: sleep_queue.o timestamp.o
	cc -g -o sleep_queue $^ -lnfnetlink -lnetfilter_queue

.c.o:
	cc -c -Wall -g $< -lnfnetlink -lnetfilter_queue

sleep_queue.o: sleep_queue.c dns.h timestamp.h

filter.o: filter.c dns.h timestamp.h

clean:
	rm *.o filter sleep_queue
