FROM python:3.13-slim
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=appuser:appuser hub.py ui_common.py app.py financial_planner_app.py teaching_assistant_app.py ./
COPY --chown=appuser:appuser teaching_assistant/ teaching_assistant/
COPY --chown=appuser:appuser health_assistant/ health_assistant/
COPY --chown=appuser:appuser financial_planner/ financial_planner/
USER appuser
ENV PATH="/home/appuser/.local/bin:${PATH}"
CMD ["sh", "-c", "streamlit run hub.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
