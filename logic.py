"""logic.py — игровая логика игры про шарики, без визуального интерфейса.

Модуль отвечает только за поведение шариков: движение, «всасывание» и
«выплёвывание», смешивание цветов при касании и зону удаления. Визуальная
часть подключается отдельно (см. gui.py) и только читает состояние.

Смешивание цветов — математическое: новый цвет считается как усреднение
RGB-компонент двух соприкасающихся шариков. Таблица соответствий не
используется, поэтому результат работает для любого из 16,7 млн цветов.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

Color = tuple[int, int, int]


def clamp(value: float, low: float, high: float) -> float:
    """Ограничивает значение диапазоном [low, high]."""
    return max(low, min(high, value))


def random_color(rng: random.Random | None = None) -> Color:
    """Возвращает случайный яркий цвет."""
    rng = rng or random
    return (
        rng.randint(40, 255),
        rng.randint(40, 255),
        rng.randint(40, 255),
    )


def mix_colors(first: Color, second: Color) -> Color:
    """Смешивает два цвета как усреднение RGB-компонент.

    В отличие от заранее заданной палитры, формула универсальна: даёт
    корректный результат для любой пары цветов, включая близкие оттенки.
    """
    return tuple(  # type: ignore[return-value]
        int(round((a + b) / 2)) for a, b in zip(first, second)
    )


def color_distance(first: Color, second: Color) -> int:
    """Суммарная разница по каналам — чтобы не «смешивать» одинаковые цвета."""
    return sum(abs(a - b) for a, b in zip(first, second))


@dataclass
class Ball:
    """Шарик: позиция, скорость, радиус и цвет."""

    x: float
    y: float
    vx: float
    vy: float
    radius: float
    color: Color

    def move(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

    def distance_to(self, other: "Ball") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


@dataclass
class Rect:
    """Прямоугольная область (зона удаления)."""

    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float, margin: float = 0.0) -> bool:
        return (
            self.x - margin <= px <= self.x + self.width + margin
            and self.y - margin <= py <= self.y + self.height + margin
        )

    def contains_ball(self, ball: Ball) -> bool:
        return self.contains(ball.x, ball.y, -ball.radius * 0.5)


@dataclass
class BallWorld:
    """Мир шариков: движение, столкновения, инвентарь и зона удаления."""

    width: float = 900
    height: float = 700
    ball_count: int = 12
    delete_zone: Rect = field(
        default_factory=lambda: Rect(900 - 140, 700 - 140, 110, 110)
    )
    inventory_limit: int = 25
    rng: random.Random = field(default_factory=random.Random)

    balls: list[Ball] = field(default_factory=list)
    inventory: list[Color] = field(default_factory=list)
    total_mixes: int = 0

    def __post_init__(self) -> None:
        if not self.balls:
            self.reset()

    # --- создание ---------------------------------------------------------
    def reset(self) -> None:
        """Пересоздаёт стартовый набор шариков."""
        self.balls.clear()
        self.inventory.clear()
        self.total_mixes = 0
        for _ in range(self.ball_count):
            self.spawn()

    def spawn(
        self,
        color: Color | None = None,
        x: float | None = None,
        y: float | None = None,
    ) -> Ball:
        """Добавляет шарик со случайной позицией, скоростью и цветом."""
        radius = self.rng.uniform(12, 22)
        speed = self.rng.uniform(40, 130)
        angle = self.rng.uniform(0, math.tau)
        ball = Ball(
            x=self.rng.uniform(radius, self.width - radius) if x is None else x,
            y=self.rng.uniform(radius, self.height - radius) if y is None else y,
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            radius=radius,
            color=color or random_color(self.rng),
        )
        self.balls.append(ball)
        return ball

    # --- движение ---------------------------------------------------------
    def update(self, dt: float) -> None:
        """Один шаг симуляции: движение, отскок от стен, смешивание цветов."""
        dt = min(dt, 0.05)
        for ball in self.balls:
            ball.move(dt)
            if ball.x - ball.radius < 0:
                ball.x = ball.radius
                ball.vx = abs(ball.vx)
            elif ball.x + ball.radius > self.width:
                ball.x = self.width - ball.radius
                ball.vx = -abs(ball.vx)
            if ball.y - ball.radius < 0:
                ball.y = ball.radius
                ball.vy = abs(ball.vy)
            elif ball.y + ball.radius > self.height:
                ball.y = self.height - ball.radius
                ball.vy = -abs(ball.vy)

        self._mix_on_contact()
        self.remove_in_delete_zone()

    def _mix_on_contact(self) -> None:
        """Смешивает цвета при касании. Шарики не отталкиваются."""
        balls = self.balls
        for i in range(len(balls)):
            for j in range(i + 1, len(balls)):
                first, second = balls[i], balls[j]
                if first.distance_to(second) > first.radius + second.radius:
                    continue
                if color_distance(first.color, second.color) <= 4:
                    continue  # цвета уже совпадают — смешивать нечего
                mixed = mix_colors(first.color, second.color)
                first.color = mixed
                second.color = mixed
                self.total_mixes += 1

    def remove_in_delete_zone(self) -> int:
        """Удаляет шарики, попавшие в зону удаления. Возвращает их число."""
        kept = [ball for ball in self.balls if not self.delete_zone.contains_ball(ball)]
        removed = len(self.balls) - len(kept)
        if removed:
            self.balls = kept
        return removed

    # --- взаимодействие мышью --------------------------------------------
    def ball_near(self, x: float, y: float, radius: float = 45) -> Ball | None:
        """Ближайший шарик в радиусе курсора."""
        candidates = [
            (math.hypot(ball.x - x, ball.y - y), ball)
            for ball in self.balls
            if math.hypot(ball.x - x, ball.y - y) <= radius + ball.radius
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    def suck(self, x: float, y: float, radius: float = 45) -> Ball | None:
        """Всасывает ближайший шарик в инвентарь."""
        ball = self.ball_near(x, y, radius)
        if ball is None:
            return None
        self.balls.remove(ball)
        if len(self.inventory) < self.inventory_limit:
            self.inventory.append(ball.color)
        return ball

    def suck_all(self, x: float, y: float, radius: float = 45) -> int:
        """Всасывает все шарики в радиусе (для удержания кнопки мыши)."""
        absorbed = 0
        while True:
            ball = self.suck(x, y, radius)
            if ball is None:
                return absorbed
            absorbed += 1

    def spit(
        self,
        x: float,
        y: float,
        angle: float | None = None,
        speed: float | None = None,
    ) -> Ball | None:
        """Выплёвывает последний шарик из инвентаря в точку курсора."""
        if not self.inventory:
            return None
        color = self.inventory.pop()
        radius = self.rng.uniform(12, 22)
        angle = self.rng.uniform(0, math.tau) if angle is None else angle
        speed = self.rng.uniform(60, 160) if speed is None else speed
        ball = Ball(
            x=clamp(x, radius, self.width - radius),
            y=clamp(y, radius, self.height - radius),
            vx=math.cos(angle) * speed,
            vy=math.sin(angle) * speed,
            radius=radius,
            color=color,
        )
        self.balls.append(ball)
        return ball

    # --- статистика -------------------------------------------------------
    @property
    def stats(self) -> dict[str, int]:
        """Краткая сводка состояния мира."""
        return {
            "balls": len(self.balls),
            "inventory": len(self.inventory),
            "mixes": self.total_mixes,
        }
