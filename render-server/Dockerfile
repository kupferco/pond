# Pond render server. Build context: the render-server directory.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libcairo2: cairosvg. libosmesa6: headless MuJoCo rendering (no GPU on Cloud Run).
# The rest: runtime libraries the OpenCascade (cadquery-ocp) wheels link against.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcairo2 \
        libgl1 libglu1-mesa libegl1 \
        libx11-6 libxext6 libxrender1 libxi6 libxcursor1 libxinerama1 libxrandr2 libxfixes3 \
        libsm6 libice6 libfontconfig1 libfreetype6 \
        fonts-dejavu-core \
        libosmesa6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY pyproject.toml ./
COPY pond_render ./pond_render
RUN pip install --no-deps .

# Warm the import cache so the first request after a cold start is faster, and prove the stack loads.
RUN python -c "import cadquery, cairosvg, mcp, mujoco, imageio_ffmpeg; print('cadquery', cadquery.__version__, 'mujoco', mujoco.__version__)"

RUN useradd --create-home --uid 1000 pond
USER pond

ENV POND_HOST=0.0.0.0 \
    PORT=8080 \
    MUJOCO_GL=osmesa \
    PYOPENGL_PLATFORM=osmesa
EXPOSE 8080

CMD ["python", "-m", "pond_render"]
