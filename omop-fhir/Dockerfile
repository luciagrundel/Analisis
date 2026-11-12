FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY prototype.py pg_backend.py lab.py test_prototype.py test_lab.py ./
COPY examples ./examples
ENTRYPOINT ["python", "lab.py"]
CMD ["demo"]
