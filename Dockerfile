FROM debian:buster as builder

RUN set -x \
    && apt update \
    && apt install --no-install-recommends \
        -y -q gcc g++ make

ADD server/ .

RUN make

# ---------- 8< ----------

FROM elice/python-nginx:3.7

ENV SERVER=127.0.0.1
ENV PORT=35601
ENV USERNAME=USER
ENV PASSWORD=PASSWORD
ENV INTERVAL=1

ENV PROCFS_PATH=/rootfs/proc
ENV TZ=Asia/Shanghai

RUN set -x \
    && mkdir -p /svrstat \
    && apt update \
    && apt install --no-install-recommends \
        -y -q ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /svrstat

ADD web/ html/
ADD clients/status-client.py status-client.py
ADD nginx.conf /etc/nginx/conf.d/default.conf
ADD entrypoint.sh /entrypoint.sh

COPY --from=builder /config.json hstat/config.json
COPY --from=builder /sergate sergate

WORKDIR /svrstat/hstat

EXPOSE 80 443 35601

VOLUME ["/svrstat/hstat", "/svrstat/html/json", "/etc/nginx/conf.d", "/rootfs/proc"]

ENTRYPOINT ["/entrypoint.sh"]
