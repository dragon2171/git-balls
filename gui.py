"""gui.py — графический интерфейс игры про шарики на pygame.

Точка входа: `python gui.py`. Визуальная часть только отрисовывает состояние
из logic.py и передаёт туда действия мыши, поэтому логика остаётся
независимой и тестируемой.

Управление:
  ЛКМ (удерживать) — всасывать шарики в инвентарь
  ПКМ              — выплюнуть шарик из инвентаря в точку курсора
  R                — перезапуск
  Esc / закрыть    — выход

Служебные ключи (для автоматических проверок и скриншотов):
  --frames N       — прокрутить N кадров и выйти
  --shot PATH      — сохранить кадр в PNG
"""

from __future__ import annotations

import argparse
import math
import os
import random

import pygame

from logic import Ball, BallWorld, Rect

WIDTH, HEIGHT = 900, 700
FPS = 60
START_BALLS = 12          # стартовое количество шариков
SUCTION_RADIUS = 55       # радиус «всасывания» вокруг курсора

WHITE = (255, 255, 255)
INK = (32, 32, 40)
MUTED = (140, 140, 155)
ZONE_FILL = (255, 240, 240)
ZONE_EDGE = (235, 120, 120)


def draw_ball(surface: pygame.Surface, ball: Ball) -> None:
    """Рисует шарик с лёгким бликом."""
    center = (int(ball.x), int(ball.y))
    radius = int(ball.radius)
    pygame.draw.circle(surface, ball.color, center, radius)
    highlight = tuple(min(255, channel + 60) for channel in ball.color)
    pygame.draw.circle(
        surface,
        highlight,
        (int(ball.x - radius * 0.3), int(ball.y - radius * 0.3)),
        max(2, radius // 3),
    )


def draw_delete_zone(surface: pygame.Surface, zone: Rect, font: pygame.font.Font) -> None:
    """Зона удаления: пунктирная рамка и подпись."""
    rect = pygame.Rect(int(zone.x), int(zone.y), int(zone.width), int(zone.height))
    pygame.draw.rect(surface, ZONE_FILL, rect, border_radius=10)
    for offset in range(0, rect.width, 12):
        pygame.draw.line(surface, ZONE_EDGE, (rect.x + offset, rect.y),
                         (rect.x + offset + 6, rect.y), 2)
        pygame.draw.line(surface, ZONE_EDGE, (rect.x + offset, rect.bottom),
                         (rect.x + offset + 6, rect.bottom), 2)
    for offset in range(0, rect.height, 12):
        pygame.draw.line(surface, ZONE_EDGE, (rect.x, rect.y + offset),
                         (rect.x, rect.y + offset + 6), 2)
        pygame.draw.line(surface, ZONE_EDGE, (rect.right, rect.y + offset),
                         (rect.right, rect.y + offset + 6), 2)
    label = font.render("удалить", True, ZONE_EDGE)
    surface.blit(label, (rect.x + 8, rect.y + rect.height - 26))


def draw_hud(
    surface: pygame.Surface,
    world: BallWorld,
    font: pygame.font.Font,
    small: pygame.font.Font,
) -> None:
    """Счётчики и подсказки по управлению."""
    stats = world.stats
    text = font.render(
        f"Шариков: {stats['balls']}    В инвентаре: {stats['inventory']}"
        f"    Смешиваний: {stats['mixes']}",
        True,
        INK,
    )
    surface.blit(text, (20, 16))
    hint = small.render(
        "ЛКМ — всасывать · ПКМ — выплюнуть · R — сброс · Esc — выход",
        True,
        MUTED,
    )
    surface.blit(hint, (20, HEIGHT - 32))


def run(frames: int | None = None, shot: str | None = None) -> None:
    """Главный цикл игры. frames/shot используются для автотестов."""
    pygame.init()
    pygame.display.set_caption("Шарики — CLmB01")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 22, bold=True)
    small = pygame.font.SysFont("arial", 16)

    world = BallWorld(
        width=WIDTH,
        height=HEIGHT,
        ball_count=START_BALLS,
        delete_zone=Rect(WIDTH - 140, HEIGHT - 140, 110, 110),
        rng=random.Random(),
    )

    running = True
    frame = 0
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    world.reset()

        pressed = pygame.mouse.get_pressed(3)
        mouse_x, mouse_y = pygame.mouse.get_pos()
        if pressed[0]:
            world.suck_all(mouse_x, mouse_y, SUCTION_RADIUS)
        if pressed[2]:
            world.spit(mouse_x, mouse_y)

        world.update(clock.get_time() / 1000 or 1 / FPS)

        screen.fill(WHITE)
        draw_delete_zone(screen, world.delete_zone, small)
        for ball in world.balls:
            draw_ball(screen, ball)
        if pressed[0]:
            pygame.draw.circle(screen, (230, 230, 245), (mouse_x, mouse_y),
                               SUCTION_RADIUS, 2)
        draw_hud(screen, world, font, small)
        pygame.display.flip()
        clock.tick(FPS)

        frame += 1
        if frames is not None and frame >= frames:
            running = False

    if shot:
        pygame.image.save(screen, shot)
    pygame.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Игра про шарики")
    parser.add_argument("--frames", type=int, default=None,
                        help="прокрутить N кадров и выйти (автопроверка)")
    parser.add_argument("--shot", type=str, default=None,
                        help="сохранить последний кадр в PNG")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(frames=args.frames, shot=args.shot)
