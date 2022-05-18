#The code was adapted from https://pythonspot.com/maze-in-pygame/

import pygame
from pygame.locals import *


class Player:

    def __init__(self):
        self.x = 44
        self.y = 44
        self.speed = 0.05

    def move_right(self, maze):
        b_x = self.x + self.speed
        b_y = self.y
        if maze.collision(b_x, b_y):
            self.x = b_x

    def move_left(self, maze):
        b_x = self.x - self.speed
        b_y = self.y
        if maze.collision(b_x, b_y):
            self.x = b_x

    def move_up(self, maze):
        b_x = self.x
        b_y = self.y - self.speed
        if maze.collision(b_x, b_y):
            self.y = b_y

    def move_down(self, maze):
        b_x = self.x
        b_y = self.y + self.speed
        if maze.collision(b_x, b_y):
            self.y = b_y


class Maze:

    def __init__(self):
        self.player_size = 40
        self.brick_size = 44
        self.M = 10
        self.N = 8
        self.maze = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
                     1, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                     1, 0, 0, 0, 0, 0, 0, 0, 0, 1,
                     1, 0, 1, 1, 1, 1, 1, 1, 0, 1,
                     1, 0, 1, 0, 0, 0, 0, 0, 0, 1,
                     1, 0, 1, 0, 1, 1, 1, 1, 0, 1,
                     1, 0, 0, 0, 0, 0, 0, 0, 0, 2,
                     1, 1, 1, 1, 1, 1False, 1, 1, 1, 1, ]

    def draw(self, display_surf, image_surf, exit_surf):
        bx = 0
        by = 0
        for i in range(0, self.M * self.N):
            if self.maze[bx + (by * self.M)] == 1:
                display_surf.blit(image_surf, (bx * 44, by * 44))
            if self.maze[bx + (by * self.M)] == 2:
                display_surf.blit(exit_surf, (bx * 44, by * 44))
            bx = bx + 1
            if bx > self.M - 1:
                bx = 0
                by = by + 1

    def collision(self, b_x, b_y):
        return self.maze[int((b_x) // self.brick_size) + int((b_y // self.brick_size) * self.M)] != 1 and self.maze[
            int((b_x + self.player_size) // self.brick_size) + int(((b_y + self.player_size) // self.brick_size) * self.M)] != 1 and self.maze[
                   int((b_x + self.player_size) // self.brick_size) + int(((b_y) // self.brick_size) * self.M)] != 1 and self.maze[
                   int((b_x) // self.brick_size) + int(((b_y + self.player_size) // self.brick_size) * self.M)] != 1

    def is_exit(self, b_x, b_y):
        return self.maze[int((b_x) // self.brick_size) + int((b_y // self.brick_size) * self.M)] == 2 or self.maze[
            int((b_x + self.player_size) // self.brick_size) + int(((b_y + self.player_size) // self.brick_size) * self.M)] == 2 or self.maze[
                   int((b_x + self.player_size) // self.brick_size) + int(((b_y) // self.brick_size) * self.M)] == 2 or self.maze[
                   int((b_x) // self.brick_size) + int(((b_y + self.player_size) // self.brick_size) * self.M)] == 2


class App:

    def __init__(self):
        self.windowWidth = 800
        self.windowHeight = 600
        self.player = 0
        self._running = True
        self._display_surf = None
        self._image_surf = None
        self._block_surf = None
        self._exit_surf = None
        self.player = Player()
        self.maze = Maze()

    def on_init(self):
        pygame.init()
        self._display_surf = pygame.display.set_mode((self.windowWidth, self.windowHeight), pygame.HWSURFACE)

        pygame.display.set_caption('Maze')
        self._running = True
        self._image_surf = pygame.image.load("player.png").convert()
        self._block_surf = pygame.image.load("block.png").convert()
        self._exit_surf = pygame.image.load("exit.png").convert()

    def on_event(self, event):
        if event.type == QUIT:
            self._running = False

    def on_loop(self):
        pass

    def on_render(self):
        self._display_surf.fill((0, 0, 0))
        self._display_surf.blit(self._image_surf, (self.player.x, self.player.y))
        self.maze.draw(self._display_surf, self._block_surf, self._exit_surf)  #
        pygame.display.flip()

    def on_cleanup(self):
        pygame.quit()

    def on_execute(self):
        if not self.on_init():
            self._running = True

        while self._running:
            pygame.event.pump()
            keys = pygame.key.get_pressed()

            if keys[K_RIGHT]:
                self.player.move_right(self.maze)

            if keys[K_LEFT]:
                self.player.move_left(self.maze)

            if keys[K_UP]:
                self.player.move_up(self.maze)

            if keys[K_DOWN]:
                self.player.move_down(self.maze)

            if keys[K_ESCAPE]:
                self._running = False

            if self.maze.is_exit(self.player.x, self.player.y):
                self._running = False

            self.on_loop()
            self.on_render()
        self.on_cleanup()


if __name__ == '__main__':
    theApp = App()
    theApp.on_execute()
