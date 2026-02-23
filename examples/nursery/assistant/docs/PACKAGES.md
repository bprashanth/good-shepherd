# Adding Python Packages to OpenClaw Assistant

This guide explains how to add Python packages to the OpenClaw nursery assistant container.

## Overview

There are two methods for installing Python packages:

1. **System Packages (via apt)** - Recommended for stable, common libraries
2. **PyPI Packages (via pip)** - For latest versions or packages not in Debian repos

## Method 1: System Packages (OPENCLAW_DOCKER_APT_PACKAGES)

### How it Works

The Dockerfile includes a build argument `OPENCLAW_DOCKER_APT_PACKAGES` that installs Debian packages during the build process:

```dockerfile
ARG OPENCLAW_DOCKER_APT_PACKAGES=""
RUN if [ -n "$OPENCLAW_DOCKER_APT_PACKAGES" ]; then \
      apt-get update && \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $OPENCLAW_DOCKER_APT_PACKAGES && \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*; \
    fi
```

### When to Use

- Installing stable Python libraries (requests, numpy, pandas, etc.)
- Packages available in Debian repositories
- When you want system-managed package versions
- Production deployments

### Installation Steps

#### 1. Update `.env` file

Edit `Dockerfile` (unfortunately this needs to run in the openclaw root repo, as it copies scripts into the Docker):

```bash
# Add or update this line
OPENCLAW_DOCKER_APT_PACKAGES="python3-requests"
```

For multiple packages, use space-separated list:

```bash
OPENCLAW_DOCKER_APT_PACKAGES=python3-requests python3-pandas python3-numpy
```

#### 2. Rebuild the container

```bash
# Stop the running container
docker compose down

cd path/to/your/openclaw/repo/

# Rebuild with the package
docker build -t openclaw:local -f Dockerfile .

cd -

# Start the container
docker compose up -d
```

#### 3. Verify installation

```bash
docker compose exec openclaw-gateway python3 -c "import requests; print('- requests installed')"
```

Expected output: `- requests installed`

### Common System Packages

| Package Name | Python Module | Description |
|-------------|---------------|-------------|
| `python3-requests` | `requests` | HTTP library |
| `python3-pandas` | `pandas` | Data analysis |
| `python3-numpy` | `numpy` | Numerical computing |
| `python3-psycopg2` | `psycopg2` | PostgreSQL adapter |
| `python3-yaml` | `yaml` | YAML parser |
| `python3-pillow` | `PIL` | Image processing |

To find package names:
```bash
# Search Debian packages
apt-cache search python3- | grep <library-name>
```

---

## Method 2: PyPI Packages (requirements.txt)

### How it Works

Create a `requirements.txt` file and modify the Dockerfile to install packages via pip during build.

### When to Use

- Need specific PyPI versions not in Debian repos
- Using packages only available on PyPI
- Development/testing with latest versions
- Packages with complex dependencies

### Installation Steps

#### 1. Create `requirements.txt`

Create `examples/nursery/assistant/requirements.txt`:

```
requests>=2.28.0
urllib3>=1.26.0
pandas>=2.0.0
```

#### 2. Modify Dockerfile

Edit `examples/nursery/assistant/Dockerfile`, add after the `OPENCLAW_DOCKER_APT_PACKAGES` section (again, while you can modify this Dockerfile it must be copied and re-run from within the openclaw repo):

```dockerfile
# Install Python packages from requirements.txt
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
```

Complete example:

```dockerfile
FROM openclaw:base

# Install system packages (if needed)
ARG OPENCLAW_DOCKER_APT_PACKAGES=""
RUN if [ -n "$OPENCLAW_DOCKER_APT_PACKAGES" ]; then \
      apt-get update && \
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends $OPENCLAW_DOCKER_APT_PACKAGES && \
      apt-get clean && \
      rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*; \
    fi

# Install PyPI packages
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ... rest of Dockerfile
```

#### 3. Rebuild the container

```bash
docker compose down
cd path/to/openclaw/repo
docker build -t openclaw:local -f Dockerfile .

cd -
docker compose up -d
```

#### 4. Verify installation

```bash
docker compose exec openclaw-gateway python3 -c "import requests; print(requests.__version__)"
```


