FROM python:3.13-slim
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser teaching_assistant/ teaching_assistant/
USER appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"
CMD ["python", "main.py"]
