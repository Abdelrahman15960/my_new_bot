FROM python:3.10-slim

# تثبيت LibreOffice وحزمة الخطوط لضمان تنسيق الـ PDF
RUN apt-get update && apt-get install -y \
    libreoffice \
    fonts-liberation \
    fonts-dejavu \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    && apt-get clean

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# أمر التشغيل
CMD ["python", "main.py"]
