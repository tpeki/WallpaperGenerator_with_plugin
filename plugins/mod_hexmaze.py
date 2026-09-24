import random
import math
from PIL import Image, ImageDraw
from wall_common import *

# ==========================================
# 定数
# ==========================================
HEX_RADIUS = 22  # タイル半径
PATH_WIDTH = 18  # 通路幅
JOINT_WIDTH = 1  # 目地幅
COLOR_GRASS = (0x64, 0xc0, 0x50)  # タイル面: 草色
COLOR_DIRT = (0xdd, 0xbb, 0x77)  # 通路: 土色
COLOR_EDGE = (0x46, 0x55, 0x46)  # 目地色
JITTER = 5
DISP_GOAL = 1

COLOR_START = (0xc8, 0xcc, 0x60)  # スタート：黄色
COLOR_GOAL = (0xb4, 0x32, 0x64)  # ゴール：暗いピンク

# ==========================================
# プラグイン定義
# ==========================================
# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '六角迷路',
                       {'color1':'通路', 'color2':'背景', 'color3':'枠線',
                        'color_jitter':'色変化', 'sub_jitter':'起点(1:表示)',
                        'pwidth':'セル半径', 'pheight':'通路幅',
                        'pdepth':'枠線幅'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR_DIRT)
    p.color2.itoc(*COLOR_GRASS)
    p.color3.itoc(*COLOR_EDGE)
    p.pwidth = HEX_RADIUS
    p.pheight = PATH_WIDTH
    p.pdepth = JOINT_WIDTH
    p.color_jitter = JITTER
    p.sub_jitter = DISP_GOAL
    return p

# ==========================================
# 補助定数
# ==========================================
SQRT3 = math.sqrt(3)
DIR_VECTORS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
OPPOSITE = [3, 4, 5, 0, 1, 2]

# 花の描画パラメータ  変数が増えすぎたので固定値
FLOWER_PROB = 0.05  # 行き止まりに花がある確率
COLOR_PETAL = (255, 50, 50)  # 花弁色
PETAL_JITTER = 40  # 花弁色のゆらぎ
COLOR_STAMEN = (255, 255, 0)   # 雄蕊色
COLOR_STEM = (50, 120, 30)  # 茎色
FLOWER_SIZE = 0.14 # 花サイズ(半径比)

# ==========================================
# 補助関数
# ==========================================
def hex_to_pixel(q, r, radius):
    x = radius * SQRT3 * (q + r/2.0)
    y = radius * 1.5 * r
    return x, y


def ellip(draw, c, r, colr):
    draw.ellipse((c[0]-r, c[1]-r, c[0]+r, c[1]+r), fill=colr)


def draw_custom_flower(draw, cx, cy, hex_radius):
    size = round(hex_radius * FLOWER_SIZE)
    fx = cx + random.uniform(-hex_radius/3, hex_radius/3)
    fy = cy + random.uniform(-hex_radius/3, hex_radius/3)
    
    stem_bbox = [fx, fy, fx + 2*3*size, fy + 2*size] 
    draw.arc(stem_bbox, start=0, end=90, fill=COLOR_STEM, width=2)

    offsets = [(-size, -size), (size, -size), (-size, size), (size, size)]
    for dx, dy in offsets:
        col = rgb_random_jitter(RGBColor(COLOR_PETAL), PETAL_JITTER).ctoi()
        ellip(draw, (fx+dx, fy+dy), size, col)

    ellip(draw, (fx, fy), size, COLOR_STAMEN)

# ==========================================
# 迷路生成とセルの特定
# ==========================================
def create_grid(p: Param):
    width = p.width
    height = p.height
    hex_radius = p.pwidth
    
    grid = {}
    attr = {}
    cols = int(width / (SQRT3 * hex_radius))
    rows = int(height / (1.5 * hex_radius))
    for r_idx in range(rows):
        r_offset = r_idx // 2
        for q_idx in range(-r_offset, cols - r_offset):
            grid[(q_idx, r_idx)] = set()

    sorted_cells = sorted(grid.keys(), key=lambda c: c[0] + c[1])
    start_cell = sorted_cells[0]
    goal_cell = sorted_cells[-1]
    attr['start_cell'] = start_cell
    attr['goal_cell'] = goal_cell

    visited = {start_cell}
    walls = []
    def add_walls(cell):
        for i, (dq, dr) in enumerate(DIR_VECTORS):
            neighbor = (cell[0] + dq, cell[1] + dr)
            if neighbor in grid and neighbor not in visited:
                walls.append((cell, i, neighbor))
    add_walls(start_cell)

    while walls:
        cell_a, d_idx, cell_b = walls.pop(random.randrange(len(walls)))
        if cell_b not in visited:
            if len(grid[cell_a]) < 3 and len(grid[cell_b]) < 3:
                grid[cell_a].add(d_idx)
                grid[cell_b].add(OPPOSITE[d_idx])
                visited.add(cell_b)
                add_walls(cell_b)

    dead_ends = [c for c, conns in grid.items() \
                 if len(conns) == 1 and c != start_cell and c != goal_cell]
    num_flowers = max(1, int(len(dead_ends) * FLOWER_PROB))
    attr['flower_cells'] = set(random.sample(dead_ends, num_flowers))

    return grid, attr

# ==========================================
# レンダリング ステップ1: 地面描画
# ==========================================
def draw_tiles(draw, p: Param, grid, attr, offset_x, offset_y):
    hex_radius = p.pwidth
    base_color = p.color2
    jitter = p.color_jitter
    disp_goal = p.sub_jitter != 0
    jcolor = p.color3.ctoi()
    jwidth = p.pdepth
    
    start_cell = attr['start_cell']
    goal_cell =  attr['goal_cell']

    for (q, r) in grid:
        cx, cy = hex_to_pixel(q, r, hex_radius)
        cx, cy = cx + offset_x, cy + offset_y
        
        # セルの背景色
        if (q, r) == start_cell and disp_goal:
            tile_color = COLOR_START
        elif (q, r) == goal_cell and disp_goal:
            tile_color = COLOR_GOAL
        else:
            tile_color = rgb_random_jitter(base_color, jitter).ctoi()
        
        points = []
        for i in range(6):
            angle_rad = math.radians(60 * i + 30)
            points.append((cx + hex_radius * 1.02 * math.cos(angle_rad),
                           cy + hex_radius * 1.02 * math.sin(angle_rad)))
            
        draw.polygon(points, fill=tile_color, width=jwidth, outline=jcolor)


# ==========================================
# レンダリング ステップ2: 通路と花
# ==========================================
def draw_paths(draw, p: Param, grid, attr, offset_x, offset_y):
    hex_radius = p.pwidth
    path_width = p.pheight
    dirt_color = p.color1.ctoi()
    jitter = p.color_jitter
    disp_goal = p.sub_jitter != 0
    
    for (q, r), conns in grid.items():
        cx, cy = hex_to_pixel(q, r, hex_radius)
        cx, cy = cx + offset_x, cy + offset_y
        for d_idx in conns:
            angle_rad = math.radians(60 * d_idx)
            dist = hex_radius * SQRT3 / 2
            ex, ey = cx + dist * math.cos(angle_rad), \
                     cy + dist * math.sin(angle_rad)
            draw.line([cx, cy, ex, ey], fill=dirt_color, width=path_width)
        if conns:
            r_p = path_width // 2
            draw.ellipse([cx - r_p, cy - r_p, cx + r_p, cy + r_p],
                         fill=dirt_color)

        if disp_goal:
            if (q, r) in attr['flower_cells']:
                draw_custom_flower(draw,  cx,  cy, hex_radius)


# ==========================================
# 迷路画像生成
# ==========================================
def generate(p: Param):
    width = p.width
    height = p.height
    radius = min(max(6,p.pwidth),int(min(width,height)/4))
    p.pwidth = radius
    path_width = min(max(p.pheight, 2), int(radius*1.2))
    p.pheight = path_width
    jwidth = min(max(p.pdepth,0),radius)
    p.pdepth = jwidth
    cstart = brightness(p.color2, f=0.9)
    cend = brightness(p.color2, f=0.4)
    
    grid, attr = create_grid(p)

    img = vertical_gradient_rgb(width, height, cstart, cend)
    # img = Image.new('RGB', (width, height), COLOR_VOID)
    draw = ImageDraw.Draw(img)

    pixel_coords = [hex_to_pixel(q, r, radius) for q, r in grid]
    min_x, max_x = min(c[0] for c in pixel_coords)-radius,\
                   max(c[0] for c in pixel_coords)+radius
    min_y, max_y = min(c[1] for c in pixel_coords)-radius,\
                   max(c[1] for c in pixel_coords)+radius
    offset_x = (W_PI_X := width - (max_x - min_x)) / 2 - min_x
    offset_y = (H_PI_X := height - (max_y - min_y)) / 2 - min_y

    draw_tiles(draw, p, grid, attr, offset_x, offset_y)
    draw_paths(draw, p, grid, attr, offset_x, offset_y)
    return img


# ==========================================
# 実行テスト
# ==========================================
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080

    img = generate(p)
    
    img.show("hex_maze_complete.png")
