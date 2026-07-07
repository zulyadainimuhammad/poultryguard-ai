# Placeholder Dockerfile for future offline deployment testing.
# The application runtime is not implemented yet, but this image establishes
# the expected Python 3.11 base and project layout for later work.

FROM python:3.11-slim

WORKDIR /app

# Install only declared Python dependencies. Future system packages for
# llama.cpp can be added here once inference is implemented.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8501

CMD ["python", "-m", "app.backend.main"]

