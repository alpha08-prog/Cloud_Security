# Provider-plane decoy ("metadata"). Build context: testbed/images
ARG BASE_IMAGE=python:3.12-alpine3.22@sha256:a190708a2dec1bd18b1decb539f8e8f5407abaa9bf39cacda583f7f8c11db322
FROM ${BASE_IMAGE}
ARG BASE_IMAGE
ARG GIT_SHA=dev
LABEL org.opencontainers.image.title="isolab canary"       org.opencontainers.image.source="https://github.com/alpha08-prog/Cloud_Security"       org.opencontainers.image.revision="${GIT_SHA}"       org.opencontainers.image.base.name="${BASE_IMAGE}"
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app app
COPY canary/canary.py /opt/app/canary.py
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["python", "-u", "/opt/app/canary.py"]
