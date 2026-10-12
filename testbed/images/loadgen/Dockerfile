# Operator-plane load generator for E1. Build context: testbed/images
FROM grafana/k6:1.2.3@sha256:4f82892217f3110cb233e2b2622bcc97fabc70f14bd241fbfbfe7305105c68aa
ARG GIT_SHA=dev
LABEL org.opencontainers.image.title="isolab loadgen"       org.opencontainers.image.revision="${GIT_SHA}"       org.opencontainers.image.base.name="grafana/k6:1.2.3@sha256:4f82892217f3110cb233e2b2622bcc97fabc70f14bd241fbfbfe7305105c68aa"
COPY loadgen/payments.js /scripts/payments.js
