FROM alpine

RUN touch /1 /2 /3
RUN rm /2
RUN echo "hello" > /3

RUN mkdir -p /dir/4 /dir/5 /dir/6
RUN rm -r /dir/5
RUN touch /dir/6/somefile
