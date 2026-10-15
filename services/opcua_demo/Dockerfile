FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY contracts ./contracts
RUN pip install --no-cache-dir ".[opcua]"
ENV APP_ROOT=/app
ENV OPCUA_EVIDENCE_DIR=/evidence
CMD ["python", "-m", "iiot_stack.opcua_demo", "--mqtt"]
