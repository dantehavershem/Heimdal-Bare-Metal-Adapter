FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    xorriso genisoimage p7zip-full libarchive-tools squashfs-tools wimtools \
    gdisk parted dosfstools e2fsprogs ntfs-3g xfsprogs btrfs-progs lvm2 mdadm \
    cifs-utils nfs-common zstd lz4 xz-utils gzip qemu-utils openssl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
