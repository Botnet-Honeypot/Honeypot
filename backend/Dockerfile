###############################################
# Base Image
###############################################
FROM python:3.9.2-slim-buster as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.1.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv" \
    PROJECT_DIR="backend"

# Add Poetry and venv to PATH
ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

###############################################
# Builder Image
###############################################
FROM python-base as builder-base
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
    curl \
    build-essential

# Install poetry - respects $POETRY_VERSION & $POETRY_HOME
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python3 -

# Copy project requirement files here to ensure they will be cached
WORKDIR $PYSETUP_PATH
COPY ${PROJECT_DIR}/poetry.lock ${PROJECT_DIR}/pyproject.toml ./
COPY protocols /opt/protocols

# Install runtime deps - uses $POETRY_VIRTUALENVS_IN_PROJECT internally
RUN poetry install --no-dev --no-root

###############################################
# Production Image
###############################################
FROM python-base as production

# Copy venv (Python binary and dependencies) from builder
COPY --from=builder-base $PYSETUP_PATH $PYSETUP_PATH

WORKDIR /usr/src/${PROJECT_DIR}

# Copy source files
COPY ${PROJECT_DIR}/${PROJECT_DIR} ${PROJECT_DIR}
# Copy target system template files
COPY ${PROJECT_DIR}/target-systems target-systems

ENTRYPOINT ["python", "-m", "backend"]