FROM opsbase:latest
MAINTAINER huangyj
COPY new_ordercheck /root/new_ordercheck
WORKDIR /root/new_ordercheck/
RUN yum -y install mysql-connector-python.noarch redis.x86_64\
    && mkdir -p /var/log/order_check \
#    && mkdir /etc/new_ordercheck/ \
    && pip install -r requirements.txt \
    && echo -e "python /root/new_ordercheck/bin/cycle_tencent_cdn.py &\n python /root/new_ordercheck/bin/measure.py" > /root/start.sh
CMD sh /root/start.sh