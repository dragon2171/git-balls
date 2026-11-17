# Графический контейнер для игры про шарики.
# Окно игры выводится через X11: контейнер получает DISPLAY хоста.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SDL_VIDEODRIVER=x11

WORKDIR /app

# Библиотеки X11, без них pygame не откроет окно в контейнере.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libx11-6 \
        libxext6 \
        libxrender1 \
        libsm6 \
        libice6 \
        libx11-xcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY logic.py gui.py ./

# Точка входа — gui.py, игра запускается одной командой.
CMD ["python", "gui.py"]
