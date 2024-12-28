FROM alpine:3.19

RUN touch /dummyfile1
RUN echo "hello" > /dummyfile2
RUN dd if=/dev/zero of=/largefile bs=1M count=128
