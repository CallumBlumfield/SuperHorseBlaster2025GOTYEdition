import pygame
import math
import random
import sys
import os

# === Constants ===
WIDTH, HEIGHT = 640, 480
HALF_HEIGHT = HEIGHT // 2
FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = 120
DELTA_ANGLE = FOV / NUM_RAYS
MAX_DEPTH = 800
DIST = NUM_RAYS / (2 * math.tan(HALF_FOV))
PROJ_COEFF = 3 * DIST * 40
SCALE = WIDTH // NUM_RAYS
TILE = 64
FPS = 60
ammo_standard = 15
ammo_pony = 15

# === Game State ===
game_state = 'normal'       # can be 'normal' or 'judgement'
player_health = 100
max_health = 100

# Pony‐blaster toggle and names
pony_mode = False
pony_names = ["Fluttershy", "Twilight Sparkle", "Rainbow Dash"]

# === Map ===
game_map = [
    '1111111111111',
    '1...........1',
    '1...........1',
    '1...........1',
    '1...........1',
    '1...........1',
    '1...........1',
    '1...........1',
    '1...........1',
    '1111111111111',
]

def mapping(x, y):
    return int(x // TILE), int(y // TILE)

def is_wall(x, y):
    mx, my = mapping(x, y)
    if 0 <= my < len(game_map) and 0 <= mx < len(game_map[0]):
        return game_map[my][mx] == '1'
    return True

player_x, player_y = 6 * TILE, 6 * TILE
player_angle = 0

ai_horses = []
ammo_pickups = []

for _ in range(5):
    ai_horses.append({
        'x': random.uniform(2 * TILE, 9 * TILE),
        'y': random.uniform(2 * TILE, 7 * TILE),
        'angle': random.uniform(0, 2 * math.pi),
        'timer': random.randint(30, 120),
        'exploding': False,
        'explode_timer': 0,
        'pony_name': None
    })

SKY = (135, 206, 235)
GRASS = (34, 139, 34)
WALL = (139, 69, 19)
PLAYER_COLOR = (0, 0, 255)
HORSE_COLOR = (150, 75, 0)
MINIMAP_BG = (50, 50, 50, 180)

HORSE_IMAGE = None
SHOTGUN_IMAGE = None
EXPLOSION_IMAGE = None
explode_sound = None
font = None
screen = None
EMPTY_SOUND = None


# Dictionary to hold each pony’s image once loaded
PONY_IMAGES = {
    "Fluttershy": None,
    "Twilight Sparkle": None,
    "Rainbow Dash": None
}

def draw_background():
    screen.fill(SKY, (0, 0, WIDTH, HALF_HEIGHT))
    screen.fill(GRASS, (0, HALF_HEIGHT, WIDTH, HALF_HEIGHT))

def ray_casting(pos, angle):
    ox, oy = pos
    cur_angle = angle - HALF_FOV
    for ray in range(NUM_RAYS):
        sin_a = math.sin(cur_angle)
        cos_a = math.cos(cur_angle)
        for depth in range(4, MAX_DEPTH, 4):
            x = ox + depth * cos_a
            y = oy + depth * sin_a
            if is_wall(x, y):
                depth *= math.cos(angle - cur_angle)
                wall_height = PROJ_COEFF / (depth + 0.0001)
                shade = 1 / (1 + depth * 0.01)
                colour = (
                    int(WALL[0] * shade),
                    int(WALL[1] * shade),
                    int(WALL[2] * shade),
                )
                pygame.draw.rect(
                    screen,
                    colour,
                    (
                        ray * SCALE,
                        HALF_HEIGHT - wall_height // 2,
                        SCALE,
                        wall_height
                    )
                )
                break
        cur_angle += DELTA_ANGLE



def draw_ammo_pickups(player_pos, player_angle):
    ox, oy = player_pos
    for pickup in ammo_pickups:
        dx = pickup['x'] - ox
        dy = pickup['y'] - oy
        dist = math.hypot(dx, dy)

        angle_to_pickup = math.atan2(dy, dx)
        rel_angle = angle_to_pickup - player_angle
        rel_angle = (rel_angle + math.pi) % (2 * math.pi) - math.pi

        if -HALF_FOV < rel_angle < HALF_FOV and dist > 30:
            size = PROJ_COEFF / (dist + 0.0001)
            x = int((rel_angle + HALF_FOV) / FOV * WIDTH) - int(size) // 4

            # ✨ Lower the Y position to sit closer to the ground
            y = HALF_HEIGHT + int(size) // 4  # Lower than before

            pygame.draw.circle(screen, (255, 255, 0), (x, y), max(4, int(size // 12)))





def draw_ai_horses(player_pos, player_angle):
    ox, oy = player_pos
    for horse in ai_horses:
        dx = horse['x'] - ox
        dy = horse['y'] - oy
        dist = math.hypot(dx, dy)
        angle_to_horse = math.atan2(dy, dx)
        rel_angle = angle_to_horse - player_angle
        rel_angle = (rel_angle + math.pi) % (2 * math.pi) - math.pi

        if -HALF_FOV < rel_angle < HALF_FOV and dist > 30:
            size = PROJ_COEFF / (dist + 0.0001)
            x = int((rel_angle + HALF_FOV) / FOV * WIDTH) - int(size) // 2
            y = HALF_HEIGHT - int(size) // 2

            # If exploding, draw explosion sprite
            if horse['exploding'] and EXPLOSION_IMAGE:
                scaled_exp = pygame.transform.scale(EXPLOSION_IMAGE, (int(size), int(size)))
                screen.blit(scaled_exp, (x, y))

            # If in pony mode (pony_name is set), draw the pony’s image
            elif horse['pony_name']:
                pony_name = horse['pony_name']
                pony_img = PONY_IMAGES.get(pony_name)
                if pony_img:
                    scaled_pony = pygame.transform.scale(pony_img, (int(size // 2), int(size)))
                    screen.blit(scaled_pony, (x, y))
                else:
                    # Fallback to horse image if pony image missing
                    if HORSE_IMAGE:
                        scaled_img = pygame.transform.scale(
                            HORSE_IMAGE,
                            (int(size // 2), int(size))
                        )
                        screen.blit(scaled_img, (x, y))

            # Otherwise draw normal horse sprite
            elif HORSE_IMAGE:
                scaled_img = pygame.transform.scale(
                    HORSE_IMAGE,
                    (int(size // 2), int(size))
                )
                screen.blit(scaled_img, (x, y))

def move_ai_horses(update):
    if not update:
        return
    for horse in ai_horses[:]:
        if horse['exploding']:
            horse['explode_timer'] -= 1
            if horse['explode_timer'] <= 0:
                ai_horses.remove(horse)
            continue

        # Even if it’s a pony, let it wander
        if horse['timer'] <= 0:
            horse['angle'] = random.uniform(0, 2 * math.pi)
            horse['timer'] = random.randint(60, 180)
        else:
            dx = math.cos(horse['angle']) * 0.5
            dy = math.sin(horse['angle']) * 0.5
            next_x = horse['x'] + dx
            next_y = horse['y'] + dy
            if not is_wall(next_x, next_y):
                horse['x'] = next_x
                horse['y'] = next_y
            else:
                horse['angle'] += math.pi
            horse['timer'] -= 1

def draw_minimap(player_pos, player_angle):
    minimap_scale = 6
    surf = pygame.Surface(
        (len(game_map[0]) * minimap_scale, len(game_map) * minimap_scale),
        pygame.SRCALPHA
    )
    surf.fill(MINIMAP_BG)

    for y_coord, row in enumerate(game_map):
        for x_coord, char in enumerate(row):
            if char == '1':
                pygame.draw.rect(
                    surf,
                    (100, 100, 100),
                    (x_coord * minimap_scale, y_coord * minimap_scale, minimap_scale, minimap_scale)
                )

    for horse in ai_horses:
        hx = horse['x'] / TILE * minimap_scale
        hy = horse['y'] / TILE * minimap_scale
        if horse['exploding']:
            col = (255, 0, 0)
        elif horse['pony_name']:
            col = (255, 182, 193)
        else:
            col = HORSE_COLOR
        pygame.draw.circle(surf, col, (int(hx), int(hy)), 3)

    px = player_pos[0] / TILE * minimap_scale
    py = player_pos[1] / TILE * minimap_scale
    pygame.draw.circle(surf, PLAYER_COLOR, (int(px), int(py)), 4)
    dx = math.cos(player_angle) * 10
    dy = math.sin(player_angle) * 10
    pygame.draw.line(surf, PLAYER_COLOR, (px, py), (px + dx, py + dy), 2)

    screen.blit(surf, (5, 5))

def draw_health_bar():
    bar_width = 200
    bar_height = 20
    x = 10
    y = HEIGHT - bar_height - 10
    health_ratio = player_health / max_health

    pygame.draw.rect(screen, (60, 60, 60), (x, y, bar_width, bar_height))
    pygame.draw.rect(screen, (200, 0, 0), (x, y, int(bar_width * health_ratio), bar_height))
    pygame.draw.rect(screen, (255, 255, 255), (x, y, bar_width, bar_height), 2)
    
    ammo = ammo_pony if pony_mode else ammo_standard
    ammo_text = font.render(f"Ammo: {ammo}/15", True, (255, 255, 255))
    screen.blit(ammo_text, (10, HEIGHT - 60))


def trigger_judgement_level():
    global game_state
    instr_font = pygame.font.SysFont('Arial', 30)
    text1 = instr_font.render("Neigh, please don't shoot me, mate...", True, (255, 255, 255))
    text2 = instr_font.render("Press SPACE to shoot or L to let live", True, (255, 255, 255))
    waiting = True
    while waiting:
        screen.fill((0, 0, 0))
        screen.blit(text1, (WIDTH // 2 - text1.get_width() // 2, HEIGHT // 3))
        screen.blit(text2, (WIDTH // 2 - text2.get_width() // 2, HEIGHT // 2))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game_state = 'normal'
                    return
                if event.key == pygame.K_l:
                    screen.fill((0, 0, 0))
                    goodbye = instr_font.render("You showed mercy. Game over.", True, (255, 255, 255))
                    screen.blit(goodbye, (WIDTH // 2 - goodbye.get_width() // 2, HEIGHT // 2))
                    pygame.display.flip()
                    pygame.time.wait(3000)
                    pygame.quit()
                    sys.exit()

def shoot(player_pos, player_angle, explode_sound):
    global pony_mode
    ox, oy = player_pos
    for horse in ai_horses:
        # Only skip if already exploding; allow shooting even if it’s a pony
        if horse['exploding']:
            continue

        dx = horse['x'] - ox
        dy = horse['y'] - oy
        dist = math.hypot(dx, dy)
        if dist > 200:
            continue

        rel_angle = math.atan2(dy, dx) - player_angle
        rel_angle = (rel_angle + math.pi) % (2 * math.pi) - math.pi

        if abs(rel_angle) < math.radians(15):
            if pony_mode:
                # If pony_mode, turn it into a pony (even if it was already a pony, reassign name)
                horse['pony_name'] = random.choice(pony_names)
            else:
                # Normal mode: explode regardless of pony_name
                horse['exploding'] = True
                horse['explode_timer'] = FPS
                explode_sound.play()
                if random.randint(1, 8) == 3:
                    trigger_judgement_level()
            break

shoot_cooldown = 0

def main():
    global player_health, player_x, player_y, player_angle
    global HORSE_IMAGE, SHOTGUN_IMAGE, EXPLOSION_IMAGE, screen, game_state, pony_mode, font
    global ammo_standard, ammo_pony
    global shoot_cooldown



    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("The Quest To Fetch The Holy Grilled Beer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 24)

    # === Load images and sounds ===
    required_files = [
        'horse.png', 'explode.png', 'shot.png',
        'explode.mp3', 'gunshot.mp3',
        'fluttershy.png', 'twilight_sparkle.png', 'rainbow_dash.png',
        'MLP_gun.png'
    ]
    for fname in required_files:
        if not os.path.exists(fname):
            print(f"ERROR: Missing required file '{fname}'")
            pygame.quit()
            sys.exit()

    HORSE_IMAGE = pygame.image.load('horse.png').convert_alpha()
    EXPLOSION_IMAGE = pygame.image.load('explode.png').convert_alpha()

    # Load both gun sprites
    SHOTGUN_STANDARD = pygame.image.load('shot.png').convert_alpha()
    SHOTGUN_MLP = pygame.image.load('MLP_gun.png').convert_alpha()

    # Scale both gun sprites
    def scale_gun(image):
        return pygame.transform.scale(
            image,
            (200, int(200 * image.get_height() / image.get_width()))
        )

    SHOTGUN_STANDARD = scale_gun(SHOTGUN_STANDARD)
    SHOTGUN_MLP = scale_gun(SHOTGUN_MLP)

    SHOTGUN_IMAGE = SHOTGUN_STANDARD

    # Load pony images
    PONY_IMAGES["Fluttershy"] = pygame.image.load('fluttershy.png').convert_alpha()
    PONY_IMAGES["Twilight Sparkle"] = pygame.image.load('twilight_sparkle.png').convert_alpha()
    PONY_IMAGES["Rainbow Dash"] = pygame.image.load('rainbow_dash.png').convert_alpha()

    gunshot_sound = pygame.mixer.Sound('gunshot.mp3')
    explode_sound = pygame.mixer.Sound('explode.mp3')
    EMPTY_SOUND = pygame.mixer.Sound('empty.mp3')

    shoot_cooldown = 0
    gun_recoil_offset = 0
    recoil_speed = 2
    gun_recoil_max = 20

    frame_counter = 0
    space_pressed_last_frame = False
    q_pressed_last_frame = False

    while True:
        frame_counter += 1
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()

        # Toggle pony-mode on Q press (debounce)
        if keys[pygame.K_q] and not q_pressed_last_frame:
            pony_mode = not pony_mode
            SHOTGUN_IMAGE = SHOTGUN_MLP if pony_mode else SHOTGUN_STANDARD
            q_pressed_last_frame = True
        elif not keys[pygame.K_q]:
            q_pressed_last_frame = False

        if game_state == 'normal':
# Shooting input and logic
            # === Shooting input and logic (debounced) ===
            if keys[pygame.K_SPACE] and not space_pressed_last_frame and shoot_cooldown == 0:
                if pony_mode:
                    if ammo_pony <= 0:
                        EMPTY_SOUND.play()
                    else:
                        gunshot_sound.play()
                        shoot((player_x, player_y), player_angle, explode_sound)
                        ammo_pony -= 1
                        shoot_cooldown = 5
                        gun_recoil_offset = gun_recoil_max
                else:
                    if ammo_standard <= 0:
                        EMPTY_SOUND.play()
                    else:
                        gunshot_sound.play()
                        shoot((player_x, player_y), player_angle, explode_sound)
                        ammo_standard -= 1
                        shoot_cooldown = 5
                        gun_recoil_offset = gun_recoil_max


            dx = dy = 0
            sin_a = math.sin(player_angle)
            cos_a = math.cos(player_angle)

            if keys[pygame.K_w]:
                dx += 2 * cos_a
                dy += 2 * sin_a
            if keys[pygame.K_s]:
                dx -= 2 * cos_a
                dy -= 2 * sin_a
            if keys[pygame.K_a]:
                player_angle -= 0.035
            if keys[pygame.K_d]:
                player_angle += 0.035

            # Spawn new horse on H
            if keys[pygame.K_h]:
                for _ in range(100):
                    rand_x = random.randint(1, len(game_map[0]) - 2) * TILE + TILE // 2
                    rand_y = random.randint(1, len(game_map) - 2) * TILE + TILE // 2
                    if not is_wall(rand_x, rand_y):
                        ai_horses.append({
                            'x': rand_x,
                            'y': rand_y,
                            'angle': random.uniform(0, 2 * math.pi),
                            'timer': random.randint(30, 120),
                            'exploding': False,
                            'explode_timer': 0,
                            'pony_name': None
                        })
                        break
            # Spawn ammo pickup with "/"
            if keys[pygame.K_k]:
                for _ in range(100):  # Try up to 100 times to find a free spot
                    rand_x = random.randint(1, len(game_map[0]) - 2) * TILE + TILE // 2
                    rand_y = random.randint(1, len(game_map) - 2) * TILE + TILE // 2
                    if not is_wall(rand_x, rand_y):
                        ammo_pickups.append({'x': rand_x, 'y': rand_y})
                        break


            next_x = player_x + dx
            next_y = player_y + dy
            if not is_wall(next_x, player_y):
                player_x = next_x
            if not is_wall(player_x, next_y):
                player_y = next_y


            # === Check for ammo pickup ===
            for pickup in ammo_pickups[:]:
                dx = pickup['x'] - player_x
                dy = pickup['y'] - player_y
                if math.hypot(dx, dy) < 40:
                    if pony_mode:
                        ammo_pony = min(ammo_pony + 1, 15)
                    else:
                        ammo_standard = min(ammo_standard + 1, 15)
                    ammo_pickups.remove(pickup)



            move_ai_horses(update=(frame_counter % 2 == 0))
            draw_background()
            ray_casting((player_x, player_y), player_angle)
            draw_ai_horses((player_x, player_y), player_angle)
            draw_ammo_pickups((player_x, player_y), player_angle)
            draw_minimap((player_x, player_y), player_angle)
            draw_health_bar()

            if player_health <= 0:
                game_over_font = pygame.font.SysFont('Arial', 40)
                game_over_text = game_over_font.render("You died. Bad luck, mate.", True, (255, 0, 0))
                screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 2))
                pygame.display.flip()
                pygame.time.wait(3000)
                pygame.quit()
                sys.exit()

            # === Cooldown and gun drawing ===
            if shoot_cooldown > 0:
                shoot_cooldown -= 1
                gun_recoil_offset = max(0, gun_recoil_offset - recoil_speed)

            gun_x = WIDTH // 2 - SHOTGUN_IMAGE.get_width() // 2 - gun_recoil_offset // 2
            gun_y = HEIGHT - SHOTGUN_IMAGE.get_height() - gun_recoil_offset
            screen.blit(SHOTGUN_IMAGE, (gun_x, gun_y))

            # === Update last-frame input tracking ===
            space_pressed_last_frame = keys[pygame.K_SPACE]

            pygame.display.flip()
            clock.tick(FPS)
if __name__ == '__main__':
    main()