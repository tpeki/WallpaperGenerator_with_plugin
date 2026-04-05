import numpy as np
from PIL import Image, ImageDraw
from wall_common import *
import random

# --- Global 変数の設定 ---
ITERATION = 6                  # 再帰の深さ（次数）
LINE_WIDTH = 20                # 計算時の曲線の太さ（余白の幅にもなります）
LINE_COLOR = (240, 170, 120)   # 曲線の色
BG_COLOR = (90, 100, 120)      # 背景の色
JITTER = 40

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       'ヒルベルト曲線(重い) 解像度20、次数3～6推奨',
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


def generate_points(n, cell_size):
    total = n * n
    xs = np.empty(total, dtype=np.int32)
    ys = np.empty(total, dtype=np.int32)

    for d in range(total):
        x, y = d2xy(n, d)
        xs[d] = x
        ys[d] = y

    # スケーリングとオフセットを一括処理
    xs = xs * cell_size + cell_size // 2
    ys = ys * cell_size + cell_size // 2

    return np.column_stack((xs, ys))


def rot(n, x, y, rx, ry):
    """ヒルベルト曲線の向きを回転・反転させる補助関数"""
    if ry == 0:
        if rx == 1:
            x = n - 1 - x
            y = n - 1 - y
        return y, x
    return x, y


def d2xy(n, d):
    """1次元の距離dを2次元の座標(x, y)に変換する"""
    t = d
    x = y = 0
    s = 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = rot(s, x, y, rx, ry)
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


def generate(p: Param):
    width = p.width
    height = p.height
    line_color = p.color1.ctoi()
    bg_color = p.color2
    line_width = min(max(p.pwidth,1),100)
    iteration = min(max(p.pheight,1),10)
    jitter = p.color_jitter

    long_edge = max(width, height)
    
    # 1. グリッドの分割数を決定 (2^n)
    n = 2**iteration
    
    # 2. 全ポイントの計算 (0 から n^2 - 1 まで)
    # 曲線の幅と余白を同じにするため、1つのグリッドセルを LINE_WIDTH * 2 と定義
    cell_size = line_width * 2
    
    # キャンバスサイズを計算（グリッドに合わせる）
    side = n * cell_size
    padding = cell_size // 2 # 外側の余白
    canvas_size = (side, side)
    line_width = int(line_width*(long_edge/side))
    
    # 座標リストを生成
    if iteration > 6:
        points = generate_points(n, cell_size)
    else:
        points = []
        for d in range(n * n):
            x, y = d2xy(n, d)
            # 座標を中心にオフセット
            px = x * cell_size + cell_size // 2
            py = y * cell_size + cell_size // 2
            points.append((px, py))

    # 3. 描画＋背景を作成 → 背景透明(後で合成)
    image = Image.new('RGBA', canvas_size, (0,0,0,0))
    draw = ImageDraw.Draw(image)

    # ヒルベルト曲線を一気に描画
    lc = tuple(list(line_color)+[255])
    if iteration > 5:
        draw.line([tuple(p) for p in points], fill=lc,
                  width=line_width, joint="curve")
    else:
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
