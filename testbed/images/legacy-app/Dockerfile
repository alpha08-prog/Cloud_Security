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
COPY common/integrity.py /opt/integrity/integrity.py
RUN python /opt/integrity/integrity.py --create /usr/local/bin/python3.12 /opt/integrity/integrity.py /opt/app/idle.py /opt/probes/probe.py
USER 10001:10001
ENTRYPOINT ["python", "/opt/integrity/integrity.py", "--"]
CMD ["python", "-u", "/opt/app/idle.py", "legacy-app"]
