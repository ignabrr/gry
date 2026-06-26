"""
Flappy Bird – pygbag/GitHub Pages build
Identyczna logika co oryginał pgzero, bez pgzrun.

Wymagana struktura katalogów:
  main.py
  images/
    background.png
    bird1.png
    bird2.png
    birddead.png
    top.png
    bottom.png

Build:
  pip install pygbag
  pygbag .          # → build/web/  gotowe do wrzucenia na GitHub Pages
"""

import asyncio
import random
import sys

import pygame

# ── stałe ───────────────────────────────────────────────────────────────────
WIDTH  = 400
HEIGHT = 708
GAP    = 150
GRAVITY       = 0.3
FLAP_STRENGTH = 6.5
SPEED  = 3
FPS    = 60


# ── minimalna emulacja pgzero.Actor ─────────────────────────────────────────

class Actor:
    """
    Odwzorowuje semantykę pgzero.Actor potrzebną w tej grze:
      - anchor ('left'/'center'/'right', 'top'/'center'/'bottom')
      - właściwości x, y, pos, left, right, top, bottom
      - colliderect, draw
      - dynamiczna podmiana obrazka przez .image = 'nazwa'
    """

    def __init__(self, image_name, pos=(0, 0), anchor=None):
        if anchor is None:
            anchor = ('center', 'center')
        self._name   = image_name
        self._cache: dict = {}
        self._anchor = anchor
        self._pos    = [float(pos[0]), float(pos[1])]
        # atrybuty specyficzne dla tej gry
        self.dead  = False
        self.score = 0
        self.vy    = 0.0

    # ── ładowanie obrazka ───────────────────────────────────────────────────

    def _surf(self) -> pygame.Surface:
        if self._name not in self._cache:
            self._cache[self._name] = (
                pygame.image.load(f"images/{self._name}.png").convert_alpha()
            )
        return self._cache[self._name]

    @property
    def image(self) -> str:
        return self._name

    @image.setter
    def image(self, name: str):
        self._name = name

    # ── rozmiar ─────────────────────────────────────────────────────────────

    @property
    def width(self)  -> int: return self._surf().get_width()
    @property
    def height(self) -> int: return self._surf().get_height()

    # ── geometria: przeliczanie między anchor-pos a top-left ────────────────

    def _topleft(self) -> tuple:
        ax, ay = self._anchor
        px, py = self._pos
        x = (px                if ax == 'left'   else
             px - self.width   if ax == 'right'  else
             px - self.width  // 2)
        y = (py                if ay == 'top'    else
             py - self.height  if ay == 'bottom' else
             py - self.height // 2)
        return x, y

    def _from_topleft(self, tx: float, ty: float):
        ax, ay = self._anchor
        px = (tx                if ax == 'left'   else
              tx + self.width   if ax == 'right'  else
              tx + self.width  // 2)
        py = (ty                if ay == 'top'    else
              ty + self.height  if ay == 'bottom' else
              ty + self.height // 2)
        self._pos = [float(px), float(py)]

    # ── właściwości pozycyjne ────────────────────────────────────────────────

    @property
    def pos(self): return tuple(self._pos)
    @pos.setter
    def pos(self, v): self._pos = [float(v[0]), float(v[1])]

    @property
    def x(self): return self._pos[0]
    @x.setter
    def x(self, v): self._pos[0] = float(v)

    @property
    def y(self): return self._pos[1]
    @y.setter
    def y(self, v): self._pos[1] = float(v)

    @property
    def left(self): return self._topleft()[0]
    @left.setter
    def left(self, v):
        _, top = self._topleft()
        self._from_topleft(float(v), top)

    @property
    def right(self):  return self._topleft()[0] + self.width
    @property
    def top(self):    return self._topleft()[1]
    @property
    def bottom(self): return self._topleft()[1] + self.height

    # ── kolizja i rysowanie ──────────────────────────────────────────────────

    def get_rect(self) -> pygame.Rect:
        x, y = self._topleft()
        return pygame.Rect(int(x), int(y), self.width, self.height)

    def colliderect(self, other: "Actor") -> bool:
        return self.get_rect().colliderect(other.get_rect())

    def draw(self, surface: pygame.Surface):
        x, y = self._topleft()
        surface.blit(self._surf(), (int(x), int(y)))


# ── pomocnicza funkcja rysowania tekstu z cieniem ───────────────────────────

def draw_score(surface: pygame.Surface, font: pygame.font.Font, score: int):
    text = str(score)
    shadow = font.render(text, True, (0, 0, 0))
    main   = font.render(text, True, (255, 255, 255))
    x = WIDTH // 2 - main.get_width() // 2
    y = 10
    surface.blit(shadow, (x + 1, y + 1))
    surface.blit(main,   (x,     y))


# ── główna pętla (async — wymóg pygbag) ─────────────────────────────────────

async def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Flappy Bird")
    clock = pygame.time.Clock()

    bg   = pygame.image.load("images/background.png").convert()
    font = pygame.font.Font(None, 70)   # wbudowana czcionka pygame, działa w WASM

    # ── obiekty gry ──────────────────────────────────────────────────────────

    bird = Actor("bird1", (75, 200))

    pipe_top    = Actor("top",    anchor=("left", "bottom"), pos=(-100, 0))
    pipe_bottom = Actor("bottom", anchor=("left", "top"),    pos=(-100, 0))

    # ── logika — identyczna z oryginałem ─────────────────────────────────────

    def reset_pipes():
        gap_y = random.randint(200, HEIGHT - 200)
        pipe_top.pos    = (WIDTH, gap_y - GAP // 2)
        pipe_bottom.pos = (WIDTH, gap_y + GAP // 2)

    def update_pipes():
        pipe_top.left    -= SPEED
        pipe_bottom.left -= SPEED
        if pipe_top.right < 0:
            reset_pipes()
            bird.score += 1

    def update_bird():
        uy = bird.vy
        bird.vy += GRAVITY
        bird.y  += (uy + bird.vy) / 2
        bird.x   = 75

        if not bird.dead:
            bird.image = "bird2" if bird.vy < -3 else "bird1"

        if bird.colliderect(pipe_top) or bird.colliderect(pipe_bottom):
            bird.dead  = True
            bird.image = "birddead"

        if not 0 < bird.y < 720:
            bird.y     = 200
            bird.dead  = False
            bird.score = 0
            bird.vy    = 0.0
            reset_pipes()

    def flap():
        if not bird.dead:
            bird.vy = -FLAP_STRENGTH

    # ── event loop ───────────────────────────────────────────────────────────

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                flap()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # klik/tap — niezbędne do gry w przeglądarce (mobile/desktop)
                flap()

        update_pipes()
        update_bird()

        screen.blit(bg, (0, 0))
        pipe_top.draw(screen)
        pipe_bottom.draw(screen)
        bird.draw(screen)
        draw_score(screen, font, bird.score)

        pygame.display.flip()
        clock.tick(FPS)
        await asyncio.sleep(0)   # oddajemy sterowanie przeglądarce — wymóg WASM

    pygame.quit()


asyncio.run(main())
