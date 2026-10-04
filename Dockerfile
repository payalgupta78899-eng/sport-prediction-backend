FROM python:3.11-slim

WORKDIR /app

# install dependencies first (Docker layer caching)
# if requirements.txt unchanged this layer is reused
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app code
COPY . .

# run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
