FROM python:3.11.18-slim-bookworm as user-manager-build
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.2
COPY requirements.txt .
RUN pip3 install --no-cache-dir --user --no-warn-script-location  -r requirements.txt

FROM golang:1.18 as outline-ss-server-build
WORKDIR /user-manager
RUN git clone https://github.com/Jigsaw-Code/outline-ss-server.git
WORKDIR /user-manager/outline-ss-server
RUN git checkout v1.3.5 && CGO_ENABLED=0 GOOS=linux go build -o outline-ss-server .

FROM python:3.11.18-slim-bookworm
RUN python -m pip install --no-cache-dir --upgrade pip==26.2.2
WORKDIR /user-manager
COPY --from=user-manager-build /root/.local /root/.local
COPY --from=outline-ss-server-build /user-manager/outline-ss-server/outline-ss-server /user-manager/outline-ss-server/outline-ss-server

ENV PATH=/root/.local/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends make supervisor && rm -rf /var/lib/apt/lists/*

COPY Makefile .
COPY supervisord.conf .
COPY main.py .

# user-manager http api
EXPOSE 8080
# ss-server proxy port
EXPOSE 9000
# ss-server metrics
EXPOSE 9091

CMD ["supervisord", "-c", "supervisord.conf"]
