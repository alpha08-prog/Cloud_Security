# cloudaudit - the IsoLab auditor (provider plane). Build context: auditor/
#   target `runtime` (default): the service the testbed runs
#   target `dev`: + pytest/ruff/jsonschema, used by `lab.py test` and `lab.py contract`
FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258 AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY requirements.lock /tmp/requirements.lock
RUN pip install --require-hashes --no-deps -r /tmp/requirements.lock \
 && groupadd -g 10001 app && useradd -u 10001 -g app -M -s /usr/sbin/nologin app

FROM base AS dev
COPY requirements-dev.lock /tmp/requirements-dev.lock
RUN pip install --require-hashes --no-deps -r /tmp/requirements-dev.lock
ENV PYTHONPATH=/repo/auditor/src
WORKDIR /repo/auditor

FROM base AS runtime
ARG GIT_SHA=dev
LABEL org.opencontainers.image.title="isolab cloudaudit" \
      org.opencontainers.image.source="https://github.com/alpha08-prog/Cloud_Security" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.base.name="python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258"
COPY src/cloudaudit /opt/cloudaudit/cloudaudit
ENV PYTHONPATH=/opt/cloudaudit
USER 10001:10001
EXPOSE 8088
ENTRYPOINT ["python", "-m", "cloudaudit"]
CMD ["serve"]
