import numpy as np
from PIL import Image, ImageDraw
from wall_common import *
import random

TILE1_COLOR = (0x11, 0x66, 0x88)
TILE2_COLOR = (0xdd, 0xff, 0xaa)
LINE_COLOR = (0x88, 0x88, 0x88)
JITTER1 = 15
JITTER2 = 15
LINE_HIDE = 1
ITERATIONS = 6
PAINTING = 0

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       'ペンローズタイル(P1風)、次数7以下推奨',
                       {'color1':'色1', 'color2':'色2',
                        'color3':'線色',
                        'color_jitter':'色1変化', 'sub_jitter':'色2変化',
                        'pwidth':'次数', 'pheight':'形状(0..2)'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    p.color1.itoc(*TILE1_COLOR)
    p.color2.itoc(*TILE2_COLOR)
    p.color3.itoc(*LINE_COLOR)
    p.color_jitter = JITTER1
    p.sub_jitter = JITTER2
    p.pwidth = ITERATIONS
    p.pheight = np.clip(PAINTING*2 + LINE_HIDE, 0, 2)
    # フラット線なしは除外
    # 元 LINEHIDE(0線あり/1線なし), PAINTING(0フラット/1濃淡)
    # 元 PAINTING(0濃淡/2フラット), LINEHIDE(0線あり/1線なし) 
    return p


PHI = (1 + np.sqrt(5)) / 2  # 黄金分割比

def subdivide(triangles):
    result = []
    for color, A, B, C in triangles:
        if color == 0:  # Thin
            P = A + (B - A) / PHI
            result += [(0, C, P, B), (1, P, C, A)]
        else:  # Fat
            Q = B + (A - B) / PHI
            R = B + (C - B) / PHI
            result += [(1, R, C, A), (1, Q, R, B), (0, R, Q, A)]
    return result

def get_p1_polygons(color, A, B, C, c1: str, c2: str):
    """三角形の中にP1風のパターンを作るための頂点を計算
        c1,c2は濃色・淡色を#rrggbb形式で
    """
    # 黄金比に基づく分割点
    # Thin(0)は1つ、Fat(1)は2つの内分点を持つ

    polys = []
    if color == 0:
        # Thin triangle内の分割
        P = A + (B - A) / PHI
        # 2色の塗り分け用ポリゴン（例：A-P-C と P-B-C）
        polys.append(([tuple(A), tuple(P), tuple(C)], c1)) # 濃色
        polys.append(([tuple(P), tuple(B), tuple(C)], c2)) # 淡色
    else:
        # Fat triangle内の分割
        Q = B + (A - B) / PHI
        R = B + (C - B) / PHI
        polys.append(([tuple(B), tuple(Q), tuple(R)], c1))
        polys.append(([tuple(Q), tuple(R), tuple(C), tuple(A)], c2))
    return polys

def generate_triangles(width, height, iterations):
    # 初期配置
    triangles = []

    offset_x = random.uniform(-width * 0.5, width * 0.5)
    offset_y = random.uniform(-height * 0.5, height * 0.5)
    offset_r = random.uniform(0, 2 * np.pi)
    
    origin = np.array([width/2+offset_x, height/2+offset_y])
    scale = max(width, height) * 1.3

    for i in range(10):
        angle1 = i*np.pi/5+offset_r
        angle2 = (i+1)*np.pi/5+offset_r
        
        p1 = origin+scale*np.array([np.cos(angle1), np.sin(angle1)])
        p2 = origin+scale*np.array([np.cos(angle2), np.sin(angle2)])

        # タイルの向き（裏表）を交互に入れ替えて初期の星形を作る
        if i % 2 == 0:
            triangles.append((0, origin, p1, p2))
        else:
            triangles.append((0, origin, p2, p1))

    # 再分割プロセス
    for _ in range(iterations):
        triangles = subdivide(triangles)

    return triangles


def draw_pattern0(draw, triangles, color1, jitter1,
                  color2, jitter2, c3, hide_outline):

    c1 = rgb_random_jitter(color1, jitter1).ctox()
    c2 = rgb_random_jitter(color2, jitter2).ctox()
    # print(f'c1:{c1},c2:{c2}')

    for color, A, B, C in triangles:
        # 内部の塗り分けパターンを取得
        polys = get_p1_polygons(color, A, B, C, c1, c2)
        for pts, fill in polys:
            outline = fill if hide_outline else c3
            draw.polygon(pts, fill=fill,
                         outline=outline) # 境界線も同色にして隙間を埋める


def draw_pattern1(draw, triangles, color1, jitter1,
                  color2, jitter2, c3, hide_outline):

    for color, A, B, C in triangles:
        base = color1 if color == 0 else color2
        jitter = jitter1 if color == 0 else jitter2
        base = rgb_random_jitter(base, jitter)

        # 内部の塗り分けパターンを取得
        polys = get_p1_polygons(color, A, B, C,
                                brightness(base, 0.9).ctox(),
                                brightness(base, 1.1).ctox())
        for pts, fill in polys:
            outline = fill if hide_outline else c3
            draw.polygon(pts, fill=fill,
                         outline=outline)  # 境界線はc3で塗る


def generate(p: Param):
    width = p.width
    height = p.height
    c3 = p.color3.ctox()  # RGBColor -> "#rrggbb"
    p.pheight = np.clip(p.pheight, 0, 2)
    hide_outline = p.pheight & 0x01  # 分割線あり
    iterations = max(p.pwidth,1)

    triangles = generate_triangles(width, height, iterations)

    img = Image.new("RGB", (width, height), c3)
    draw = ImageDraw.Draw(img)

    if (p.pheight & 0x02) == 0: # 濃淡
        draw_pattern1(draw, triangles, p.color1, p.color_jitter,
                      p.color2, p.sub_jitter, c3, hide_outline)
    else:  # フラット
        draw_pattern0(draw, triangles, p.color1, p.color_jitter,
                      p.color2, p.sub_jitter, c3, hide_outline)

    return img

if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    image = generate(p)
    image.show()


