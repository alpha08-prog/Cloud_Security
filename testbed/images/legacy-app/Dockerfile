# tenant-c: legacy-app. The insecure profile builds it from a floating tag with no
# provenance labels; the hardened profile from the pinned base. Build context: testbed/images
ARG BASE_IMAGE=python:3.12-alpine3.22@sha256:a190708a2dec1bd18b1decb539f8e8f5407abaa9bf39cacda583f7f8c11db322
FROM ${BASE_IMAGE}
ARG BASE_IMAGE
ARG GIT_SHA=dev
LABEL org.opencontainers.image.title="isolab legacy-app"
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app app && mkdir -p /data /opt/probes && chown 10001:10001 /data
COPY common/probe.py /opt/probes/probe.py
COPY common/idle.py /opt/app/idle.py
USER 10001:10001
ENTRYPOINT ["python", "-u", "/opt/app/idle.py", "legacy-app"]
