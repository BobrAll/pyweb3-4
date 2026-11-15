FROM python:3.12.8-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /work
COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY sut sut
COPY load load
COPY runner runner
COPY analysis analysis
COPY configs configs
COPY vendor vendor
COPY tests tests
CMD ["python", "-m", "unittest", "discover", "-s", "tests", "-v"]
