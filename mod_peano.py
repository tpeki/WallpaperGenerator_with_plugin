import numpy as np
from PIL import Image, ImageDraw
from wall_common import *
import random

# --- Global 変数の設定 ---
ITERATION = 4                  # 再帰の深さ（次数）
LINE_WIDTH = 20                # 計算時の曲線の太さ（余白の幅にもなります）
LINE_COLOR = (240, 170, 120)   # 曲線の色
BG_COLOR = (90, 100, 120)        # 背景の色
JITTER = 40

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       'ペアノ曲線(とても重い) 解像度20、次数3～5推奨',
                       {'color1':'線色', 'color2':'地色',
                        'color_jitter':'色変化',
                        'pwidth':'解像度', 'pheight':'次数'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    # p.color1.itoc(*LINE_COLOR)
    # p.color2.itoc(*BG_COLOR)
    r,g,b = [random.randint(0,255) for x in range(3)]
    p.color1 = RGBColor(r,g,b)
    p.color2 = RGBColor(255-r, 255-g, 255-b)
    p.pwidth = LINE_WIDTH
    p.pheight = ITERATION
    p.color_jitter = JITTER
    return p


def peano_lsystem(iteration):
    axiom = "X"

    rules = {
        "X": "XFYFX+F+YFXFY-F-XFYFX",
        "Y": "YFXFY-F-XFYFX+F+YFXFY",
    }

    s = axiom
    for _ in range(iteration):
        s = "".join(rules.get(c, c) for c in s)
    return s


def lsystem_to_points(seq, step):
    x = y = 0
    dx, dy = 1, 0  # 初期方向：右
    points = [(x, y)]

    for c in seq:
        if c == "F":
            x += dx * step
            y += dy * step
            points.append((x, y))
        elif c == "+":
            dx, dy = -dy, dx   # 左回転
        elif c == "-":
            dx, dy = dy, -dx   # 右回転

    return points


def generate(p: Param):
    width = p.width
    height = p.height
    line_color = p.color1.ctoi()
    bg_color = p.color2
    line_width = min(max(p.pwidth,5),80)
    iteration = min(max(p.pheight,1),10)
    jitter = p.color_jitter

    long_edge = max(width, height)
    
    # 1. グリッドの分割数を決定 (2^n)
    n = 3**iteration
    
    # 2. 全ポイントの計算 (0 から n^2 - 1 まで)
    # 曲線の幅と余白を同じにするため、1つのグリッドセルを LINE_WIDTH * 2 と定義
    cell_size = line_width * 2
    
    # キャンバスサイズを計算（グリッドに合わせる）
    side = n * cell_size
    padding = cell_size // 2 # 外側の余白
    canvas_size = (side, side)
    line_width = int(line_width*(long_edge/side))
    
    # 座標リストを生成
    seq = peano_lsystem(iteration)
    points = lsystem_to_points(
        seq,
        step=cell_size
    )

    # 3. 描画＋背景を作成 → 背景透明(後で合成)
    image = Image.new('RGBA', canvas_size, (0,0,0,0))
    draw = ImageDraw.Draw(image)
    
    # 描画
    lc = tuple(list(line_color)+[255])
    draw.line(points, fill=lc, width=line_width, joint="curve")

    # 4. リサイズ
    offset_x = 0 if width == long_edge else (long_edge - width) // 2
    offset_y = 0 if height == long_edge else (long_edge - height) // 2
    
    image = image.resize((long_edge,long_edge))
    image = image.crop((offset_x, offset_y, offset_x + width, offset_y+height))

    # 5. 背景生成＋合成
    if p.h_img is None:
        bg_start = rgb_random_jitter(bg_color, jitter)
        bg_end   = rgb_random_jitter(bg_color, jitter)
        bg = diagonal_gradient_rgb(width, height, bg_start, bg_end)
    else:
        bg = p.bg(width, height)

    bg = bg.convert("RGBA")
    bg.alpha_composite(image)

    return bg


if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    image = generate(p)
    image.show()
