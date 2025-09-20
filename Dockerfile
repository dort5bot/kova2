#pip install --upgrade pip setuptools wheel satırında --no-cache-dir ekle → daha az katman şişmesi olur
# builder aşamasında gcc/g++ gibi paketleri kuruyorsun ama runtime’da aslında gerek kalmıyor. Yani image küçültmek için sadece build aşamasında bırakıldı 

# Build aşaması
FROM python:3.11-slim AS builder

WORKDIR /app

# Build bağımlılıklarını kur
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
    libc-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pip'i güncelle
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Bağımlılıkları kopyala ve wheel olarak derle
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# requirements.txt'yi de wheels klasörüne kopyala
RUN cp requirements.txt /app/wheels/


# Runtime aşaması
FROM python:3.11-slim AS runtime

WORKDIR /app

# Sadece gerekli runtime bağımlılıkları
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Uygulama kullanıcısı oluştur
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Python optimizasyonları
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPYCACHEPREFIX=/tmp \
    PIP_NO_CACHE_DIR=1

# Wheel'ları ve requirements.txt'yi kopyala
COPY --from=builder /app/wheels /wheels

# Wheel'lardan paketleri kur
RUN pip install --no-index --find-links=/wheels -r /wheels/requirements.txt \
    && rm -rf /wheels

# Uygulama kodunu kopyala
COPY --chown=appuser:appgroup . .

# Health check ve port ayarları
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3000/health || exit 1

# Çalışma kullanıcısını ayarla
USER appuser

# Çalıştırma komutu
CMD ["python", "main.py"]
