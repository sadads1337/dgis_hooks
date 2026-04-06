FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       build-essential \
       gcc \
       libffi-dev \
       git \
       binutils \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y wget gnupg lsb-release --no-install-recommends \
    && wget https://apt.llvm.org/llvm.sh \
    && chmod +x llvm.sh \
    && ./llvm.sh 22 \
    && apt-get install -y clang-format-22 \
    && ln -s /usr/bin/clang-format-22 /usr/bin/clang-format \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt /app/
COPY src/ /app/src/

RUN pip install --upgrade pip setuptools wheel build
RUN if [ -f /app/requirements.txt ]; then pip install --no-cache-dir -r /app/requirements.txt; fi

RUN python -m build -w -o /dist /app || python -m build -w -o /dist

RUN mkdir -p /opt/clang-format/bin /opt/clang-format/lib \
    && CLANG_BIN=$(command -v clang-format-22) \
    && cp "$CLANG_BIN" /opt/clang-format/bin/ \
    && for lib in $(ldd "$CLANG_BIN" | awk '/=>/ {print $(NF-1)}' | grep -v '^('); do \
         cp -u "$lib" /opt/clang-format/lib/ 2>/dev/null || true; \
       done \
    && strip --strip-all /opt/clang-format/bin/clang-format || true \
    && find /opt/clang-format/lib -type f -name "*.so*" -exec strip --strip-unneeded {} + || true

RUN mkdir -p /opt/git/bin /opt/git/lib \
    && GIT_BIN=$(command -v git) \
    && cp "$GIT_BIN" /opt/git/bin/ \
    && for lib in $(ldd "$GIT_BIN" | awk '/=>/ {print $(NF-1)}' | grep -v '^('); do \
         cp -u "$lib" /opt/git/lib/ 2>/dev/null || true; \
       done \
    && strip --strip-all /opt/git/bin/git || true \
    && find /opt/git/lib -type f -name "*.so*" -exec strip --strip-unneeded {} + || true

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /opt/clang-format /opt/clang-format
COPY --from=builder /opt/git /opt/git
ENV PATH="/opt/clang-format/bin:/opt/git/bin:${PATH}"
ENV LD_LIBRARY_PATH="/opt/clang-format/lib:/opt/git/lib:${LD_LIBRARY_PATH:-}"

COPY --from=builder /dist /dist
RUN pip install --no-cache-dir /dist/*.whl

CMD ["bash"]
