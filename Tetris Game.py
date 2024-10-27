import pygame
import random
import json
import time
from typing import List, Optional

# Инициализация
pygame.init()
pygame.font.init()

# Константы
BLOCK_SIZE = 30
FIELD_WIDTH = 10
FIELD_HEIGHT = 20
PREVIEW_SIZE = 4
SCREEN_WIDTH = BLOCK_SIZE * (FIELD_WIDTH + 8)
SCREEN_HEIGHT = BLOCK_SIZE * FIELD_HEIGHT
PARTICLE_GRAVITY = 0.2
MAX_NEXT_PIECES = 3
GHOST_ALPHA = 30

# Цвета с градиентами для блоков
COLORS = {
    'I': [(0, 255, 255), (0, 220, 220)],
    'O': [(255, 255, 0), (220, 220, 0)],
    'T': [(255, 0, 255), (220, 0, 220)],
    'L': [(255, 165, 0), (220, 140, 0)],
    'J': [(0, 0, 255), (0, 0, 220)],
    'S': [(0, 255, 0), (0, 220, 0)],
    'Z': [(255, 0, 0), (220, 0, 0)]
}

# Фигуры
SHAPES = {
    'I': [[1, 1, 1, 1]],
    'O': [[1, 1], [1, 1]],
    'T': [[1, 1, 1], [0, 1, 0]],
    'L': [[1, 1, 1], [1, 0, 0]],
    'J': [[1, 1, 1], [0, 0, 1]],
    'S': [[1, 1, 0], [0, 1, 1]],
    'Z': [[0, 1, 1], [1, 1, 0]]
}

class Particle:
    def __init__(self, x: float, y: float, color: tuple):
        self.x = x
        self.y = y
        self.color = color
        self.velocity = [random.uniform(-2, 2), random.uniform(-5, -1)]
        self.lifetime = 30

    def update(self):
        self.x += self.velocity[0]
        self.y += self.velocity[1]
        self.velocity[1] += PARTICLE_GRAVITY
        self.lifetime -= 1

    def draw(self, screen):
        if self.lifetime > 0:
            pygame.draw.circle(screen, self.color,
                             (int(self.x), int(self.y)), 2)

class Achievement:
    def __init__(self, name: str, description: str, condition):
        self.name = name
        self.description = description
        self.condition = condition
        self.unlocked = False
        self.just_unlocked = False

    def check(self, game) -> bool:
        if not self.unlocked and self.condition(game):
            self.unlocked = True
            self.just_unlocked = True
            return True
        return False

class Tetris:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption('Тетрис')
        self.clock = pygame.time.Clock()

        self.main_font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 48)

        self.particles: List[Particle] = []
        self.paused = False
        self.next_pieces = []
        self.next_shapes = []
        self.last_cleared = 0
        self.init_achievements()

        self.reset_game()
        self.load_highscore()

    def init_achievements(self):
        self.achievements = [
            Achievement("Новичок", "Наберите 1000 очков",
                        lambda game: game.score >= 1000),
            Achievement("Мастер", "Очистите 4 линии одновременно",
                        lambda game: game.last_cleared == 4),
            Achievement("Скоростной", "Достигните 10 уровня",
                        lambda game: game.level >= 10)
        ]

    def reset_game(self):
        self.field = [[0] * FIELD_WIDTH for _ in range(FIELD_HEIGHT)]
        self.current_piece = None
        self.current_shape = None
        self.next_pieces = []
        self.next_shapes = []
        self.current_x = 0
        self.current_y = 0
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.game_over = False
        self.particles = []
        self.paused = False
        self.last_cleared = 0

        # Генерируем несколько следующих фигур
        for _ in range(MAX_NEXT_PIECES):
            self.generate_next_piece()
        self.new_piece()

    def load_highscore(self):
        try:
            with open('tetris_highscore.json', 'r') as f:
                self.highscore = json.load(f)['highscore']
        except:
            self.highscore = 0

    def save_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            with open('tetris_highscore.json', 'w') as f:
                json.dump({'highscore': self.highscore}, f)

    def generate_next_piece(self):
        shape_name = random.choice(list(SHAPES.keys()))
        self.next_shapes.append(shape_name)
        self.next_pieces.append(SHAPES[shape_name])

    def new_piece(self):
        if not self.next_pieces:
            self.generate_next_piece()

        self.current_piece = self.next_pieces.pop(0)
        self.current_shape = self.next_shapes.pop(0)
        self.current_x = FIELD_WIDTH // 2 - len(self.current_piece[0]) // 2
        self.current_y = 0

        if len(self.next_pieces) < MAX_NEXT_PIECES:
            self.generate_next_piece()

        if self.check_collision():
            self.game_over = True

    def draw_block(self, x, y, color_pair, shadow=False):
        color1, color2 = color_pair
        if shadow:
            color1 = tuple(max(0, c - 100) for c in color1)
            color2 = tuple(max(0, c - 100) for c in color2)

        rect = pygame.Rect(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE - 1, BLOCK_SIZE - 1)
        pygame.draw.rect(self.screen, color1, rect)

        # Градиент и блик
        pygame.draw.line(self.screen, color2,
                         (x * BLOCK_SIZE, y * BLOCK_SIZE),
                         (x * BLOCK_SIZE + BLOCK_SIZE - 1, y * BLOCK_SIZE))
        pygame.draw.line(self.screen, (*color2, 128),
                         (x * BLOCK_SIZE, y * BLOCK_SIZE),
                         (x * BLOCK_SIZE, y * BLOCK_SIZE + BLOCK_SIZE - 1))

    def draw_ghost_piece(self):
        if self.current_piece:
            # Находим самую нижнюю возможную позицию для текущей фигуры
            ghost_y = FIELD_HEIGHT - len(self.current_piece)  # Фиксированная высота

            # Проверяем коллизии с уже размещенными фигурами
            while ghost_y > 0 and any(self.field[ghost_y + y][self.current_x + x]
                                      for y, row in enumerate(self.current_piece)
                                      for x, cell in enumerate(row) if cell
                                      if 0 <= self.current_x + x < FIELD_WIDTH
                                         and 0 <= ghost_y + y < FIELD_HEIGHT):
                ghost_y -= 1

            # Создаем прозрачную поверхность для призрачной фигуры
            ghost_surface = pygame.Surface((BLOCK_SIZE * len(self.current_piece[0]),
                                            BLOCK_SIZE * len(self.current_piece)),
                                           pygame.SRCALPHA)

            # Рисуем фигуру на прозрачной поверхности
            for y, row in enumerate(self.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        ghost_rect = pygame.Rect(
                            x * BLOCK_SIZE,
                            y * BLOCK_SIZE,
                            BLOCK_SIZE - 1,
                            BLOCK_SIZE - 1
                        )
                        pygame.draw.rect(ghost_surface,
                                         (*COLORS[self.current_shape][0], 30), ghost_rect)

            # Отображаем призрачную фигуру на экране
            self.screen.blit(ghost_surface,(self.current_x * BLOCK_SIZE, ghost_y * BLOCK_SIZE))

    def draw_next_pieces(self):
        # Заголовок секции
        next_text = self.main_font.render('Следующие:', True, (255, 255, 255))
        self.screen.blit(next_text, (FIELD_WIDTH * BLOCK_SIZE + 20, 70))

        for i, (piece, shape) in enumerate(zip(self.next_pieces, self.next_shapes)):
            # Позиция для каждого превью
            preview_x = FIELD_WIDTH * BLOCK_SIZE + 20
            preview_y = 100 + i * (PREVIEW_SIZE * BLOCK_SIZE + 20)  # Увеличен отступ между фигурами

            # Рисуем фон для превью
            preview_bg = pygame.Surface((PREVIEW_SIZE * BLOCK_SIZE + 20,
                                         PREVIEW_SIZE * BLOCK_SIZE + 20))
            preview_bg.fill((40, 40, 40))  # Тёмно-серый фон

            # Добавляем градиентную рамку
            pygame.draw.rect(preview_bg, (60, 60, 60),
                             preview_bg.get_rect(), 2)  # Внешняя рамка
            pygame.draw.rect(preview_bg, (30, 30, 30),
                             preview_bg.get_rect().inflate(-2, -2), 2)  # Внутренняя рамка

            self.screen.blit(preview_bg, (preview_x - 10, preview_y - 10))

            # Вычисляем центр для фигуры
            piece_width = len(piece[0]) * BLOCK_SIZE
            piece_height = len(piece) * BLOCK_SIZE
            offset_x = (PREVIEW_SIZE * BLOCK_SIZE - piece_width) // 2
            offset_y = (PREVIEW_SIZE * BLOCK_SIZE - piece_height) // 2

            # Рисуем фигуру
            for y, row in enumerate(piece):
                for x, cell in enumerate(row):
                    if cell:
                        block_x = preview_x + offset_x + x * BLOCK_SIZE
                        block_y = preview_y + offset_y + y * BLOCK_SIZE

                        # Основной блок
                        block_rect = pygame.Rect(block_x, block_y,
                                                 BLOCK_SIZE - 2, BLOCK_SIZE - 2)

                        # Градиент для блока
                        color1, color2 = COLORS[shape]
                        pygame.draw.rect(self.screen, color1, block_rect)

                        # Добавляем блики
                        highlight_rect = pygame.Rect(block_x, block_y,
                                                     BLOCK_SIZE - 2, BLOCK_SIZE // 3)
                        pygame.draw.rect(self.screen, color2, highlight_rect)

                        # Добавляем тень
                        shadow_rect = pygame.Rect(block_x,
                                                  block_y + BLOCK_SIZE - (BLOCK_SIZE // 3),
                                                  BLOCK_SIZE - 2, BLOCK_SIZE // 3)
                        shadow_color = tuple(max(0, c - 50) for c in color1)
                        pygame.draw.rect(self.screen, shadow_color, shadow_rect)

            # Номер следующей фигуры (маленький)
            number_text = self.main_font.render(f'#{i + 1}', True, (150, 150, 150))
            number_rect = number_text.get_rect()
            number_rect.topright = (preview_x + PREVIEW_SIZE * BLOCK_SIZE + 5,
                                    preview_y - 5)
            self.screen.blit(number_text, number_rect)

    def draw_info(self):
        # Счет
        score_text = self.main_font.render(f'Счет: {self.score}', True, (255, 255, 255))
        self.screen.blit(score_text, (FIELD_WIDTH * BLOCK_SIZE + 20, 20))

        # Рекорд
        high_text = self.main_font.render(f'Рекорд: {self.highscore}', True, (255, 255, 255))
        self.screen.blit(high_text, (FIELD_WIDTH * BLOCK_SIZE + 20, 50))

        # Уровень
        level_text = self.main_font.render(f'Уровень: {self.level}', True, (255, 255, 255))
        self.screen.blit(level_text, (FIELD_WIDTH * BLOCK_SIZE + 20, 200))

        # Линии
        lines_text = self.main_font.render(f'Линии: {self.lines_cleared}', True, (255, 255, 255))
        self.screen.blit(lines_text, (FIELD_WIDTH * BLOCK_SIZE + 20, 230))

    def draw_achievements(self):
        y_pos = 300
        for achievement in self.achievements:
            if achievement.unlocked:
                color = (0, 255, 0) if achievement.just_unlocked else (255, 255, 255)
                text = self.main_font.render(f"{achievement.name}", True, color)
                self.screen.blit(text, (FIELD_WIDTH * BLOCK_SIZE + 20, y_pos))
                achievement.just_unlocked = False
            y_pos += 30

    def draw(self):
        if self.paused:
            return

        self.screen.fill((0, 0, 0))

        # Отрисовка сетки
        for x in range(FIELD_WIDTH + 1):
            pygame.draw.line(self.screen, (30, 30, 30),
                             (x * BLOCK_SIZE, 0),
                             (x * BLOCK_SIZE, FIELD_HEIGHT * BLOCK_SIZE))
        for y in range(FIELD_HEIGHT + 1):
            pygame.draw.line(self.screen, (30, 30, 30),
                             (0, y * BLOCK_SIZE),
                             (FIELD_WIDTH * BLOCK_SIZE, y * BLOCK_SIZE))

        # Отрисовка поля
        for y, row in enumerate(self.field):
            for x, cell in enumerate(row):
                if cell:
                    self.draw_block(x, y, cell)

        # Отрисовка призрачной фигуры
        self.draw_ghost_piece()

        # Отрисовка текущей фигуры
        if self.current_piece:
            for y, row in enumerate(self.current_piece):
                for x, cell in enumerate(row):
                    if cell:
                        self.draw_block(self.current_x + x, self.current_y + y,
                                        COLORS[self.current_shape])

        # Отрисовка частиц
        for particle in self.particles[:]:
            particle.update()
            if particle.lifetime <= 0:
                self.particles.remove(particle)
            else:
                particle.draw(self.screen)

        # Отрисовка превью и информации
        self.draw_next_pieces()
        self.draw_info()
        self.draw_achievements()

        if self.game_over:
            # Затемнение экрана
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            s.set_alpha(128)
            s.fill((0, 0, 0))
            self.screen.blit(s, (0, 0))

            # Текст окончания игры
            game_over_text = self.big_font.render('GAME OVER', True, (255, 255, 255))
            restart_text = self.main_font.render('Нажмите R для перезапуска', True, (255, 255, 255))

            self.screen.blit(game_over_text,
                             (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2,
                              SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(restart_text,
                             (SCREEN_WIDTH // 2 - restart_text.get_width() // 2,
                              SCREEN_HEIGHT // 2 + 10))

        pygame.display.flip()

    def check_collision(self, dx=0, dy=0):
        future_x = self.current_x + dx
        future_y = self.current_y + dy

        for y, row in enumerate(self.current_piece):
            for x, cell in enumerate(row):
                if cell:
                    if (future_x + x < 0 or future_x + x >= FIELD_WIDTH or
                            future_y + y >= FIELD_HEIGHT or
                            (future_y + y >= 0 and self.field[future_y + y][future_x + x])):
                        return True
        return False

    def rotate_piece(self):
        rotated = list(zip(*self.current_piece[::-1]))
        old_piece = self.current_piece
        self.current_piece = rotated

        # Проверка коллизий после поворота и попытка сдвинуть фигуру
        if self.check_collision():
            # Попытка сдвинуть вправо
            self.current_x += 1
            if self.check_collision():
                # Попытка сдвинуть влево
                self.current_x -= 2
                if self.check_collision():
                    # Если ничего не помогло, отменяем поворот
                    self.current_x += 1
                    self.current_piece = old_piece

    def move(self, dx):
        if not self.check_collision(dx, 0):
            self.current_x += dx

    def create_particles(self, y):
        for x in range(FIELD_WIDTH):
            if self.field[y][x]:
                for _ in range(3):  # 3 частицы на блок
                    self.particles.append(Particle(
                        x * BLOCK_SIZE + BLOCK_SIZE // 2,
                        y * BLOCK_SIZE + BLOCK_SIZE // 2,
                        self.field[y][x][0]
                    ))

    def drop(self):
        if not self.check_collision(0, 1):
            self.current_y += 1
            return False
        else:
            self.merge_piece()
            lines_cleared = self.remove_lines()
            self.last_cleared = lines_cleared
            self.lines_cleared += lines_cleared
            self.score += lines_cleared * 100 * self.level

            # Повышение уровня каждые 10 линий
            self.level = self.lines_cleared // 10 + 1

            self.new_piece()
            return True

    def hard_drop(self):
        while not self.check_collision(0, 1):
            self.current_y += 1
        self.drop()

    def merge_piece(self):
        for y, row in enumerate(self.current_piece):
            for x, cell in enumerate(row):
                if cell:
                    self.field[self.current_y + y][self.current_x + x] = COLORS[self.current_shape]

    def remove_lines(self):
        lines = 0
        y = FIELD_HEIGHT - 1
        while y >= 0:
            if all(cell != 0 for cell in self.field[y]):
                self.create_particles(y)
                lines += 1
                for y2 in range(y, 0, -1):
                    self.field[y2] = self.field[y2 - 1][:]
                self.field[0] = [0] * FIELD_WIDTH
            else:
                y -= 1
        return lines

    def pause_game(self):
        self.paused = not self.paused
        if self.paused:
            pause_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            pause_surface.set_alpha(128)
            pause_surface.fill((0, 0, 0))
            self.screen.blit(pause_surface, (0, 0))
            pause_text = self.big_font.render('ПАУЗА', True, (255, 255, 255))
            self.screen.blit(pause_text,
                             (SCREEN_WIDTH // 2 - pause_text.get_width() // 2,
                              SCREEN_HEIGHT // 2 - pause_text.get_height() // 2))
            pygame.display.flip()

    def run(self):
        fall_speed = 1000
        fall_time = 0
        last_fall = pygame.time.get_ticks()

        while True:
            current_time = pygame.time.get_ticks()
            fall_time = current_time - last_fall

            fall_speed = max(50, 1000 - (self.level - 1) * 100)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_highscore()
                    return

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.pause_game()
                    elif not self.paused:
                        if not self.game_over:
                            if event.key == pygame.K_LEFT:
                                self.move(-1)
                            elif event.key == pygame.K_RIGHT:
                                self.move(1)
                            elif event.key == pygame.K_UP:
                                self.rotate_piece()
                            elif event.key == pygame.K_DOWN:
                                self.drop()
                            elif event.key == pygame.K_SPACE:
                                self.hard_drop()
                        if event.key == pygame.K_r and self.game_over:
                            self.reset_game()

            if not self.game_over and not self.paused:
                keys = pygame.key.get_pressed()
                if keys[pygame.K_DOWN]:
                    fall_speed = 50

                if fall_time >= fall_speed:
                    self.drop()
                    last_fall = current_time

                # Проверка достижений
                for achievement in self.achievements:
                    achievement.check(self)

            self.draw()
            self.clock.tick(60)

if __name__ == '__main__':
    game = Tetris()
    game.run()