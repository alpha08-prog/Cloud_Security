FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir docker==7.1.0 psutil==7.0.0 pydantic==2.11.7 numpy==2.2.6 scikit-learn==1.7.2 tensorflow-cpu==2.20.0 pyspark==4.0.1
ENV PYTHONPATH=/workspace/auditor/src:/workspace/experiments TF_CPP_MIN_LOG_LEVEL=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 TF_NUM_INTRAOP_THREADS=2 TF_NUM_INTEROP_THREADS=1
WORKDIR /workspace
