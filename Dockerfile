FROM python:3.11-slim

# 系統時區設定（台灣）
ENV TZ=Asia/Taipei
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先複製 requirements 利用 Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 非 root 執行
RUN adduser --disabled-password --gecos "" posuser
USER posuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
