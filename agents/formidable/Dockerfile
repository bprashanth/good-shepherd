FROM public.ecr.aws/docker/library/python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*
# Pinned via config.sh CODEX_VERSION (passed as --build-arg) for a reproducible
# image that matches the validated local codex. Bump deliberately.
ARG CODEX_VERSION=0.142.5
RUN npm install -g @openai/codex@${CODEX_VERSION}
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 \
     /lambda-adapter /opt/extensions/lambda-adapter
ENV PORT=8080 AWS_LWA_PORT=8080 \
    AWS_LWA_READINESS_CHECK_PATH=/vision/health \
    HOME=/tmp
WORKDIR /var/task
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
