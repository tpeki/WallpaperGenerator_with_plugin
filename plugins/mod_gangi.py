import numpy as np
from PIL import Image
from wall_common import *

#--------------------
# 定数
#--------------------
COLOR1 = (0xff, 0x40, 0x40)
COLOR2 = (0xd0, 0x20, 0x20)
COLOR3 = (0xfa, 0xfa, 0xf0)
JITTER = 15  # 色の振れ幅
CELL_WIDTH = 96  # セルの基本単位
ASPECT = 70  # 扁平率
CELL_COUNT = 2  # セルの幅=勾配 1の時市松模様
REVERSE = True  # 送り方向(reverse=右上り)

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '雁木/市松(勾配=1)',
                       {'color1':'色1', 'color2':'色2', 'color3':'色3(確定)',
                        'color_jitter':'色ゆらぎ',
                        'pwidth':'基本単位', 'pheight':'勾配(0<右上り)',
                        'pdepth':'扁平率'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.color3.itoc(*COLOR3)
    p.pwidth = int(CELL_WIDTH)
    p.pdepth = int(np.clip(ASPECT, 0, 100))
    p.pheight = CELL_COUNT if REVERSE else -CELL_COUNT
    p.color_jitter = JITTER
    return p


# 描画本体
def generate(p: Param):
    image_width = p.width
    image_height = p.height
    
    jitter = p.color_jitter
    rj, gj, bj = tuple(random.randint(-jitter, jitter) for c in range(3))
    color1 = (clip8(p.color1.r+rj),
              clip8(p.color1.g+gj),
              clip8(p.color1.b+bj)) 
    color2 = (clip8(p.color2.r+rj),
              clip8(p.color2.g+gj),
              clip8(p.color2.b+bj)) 

    color3 = p.color3.ctoi()  # Color3はゆらぎなし
    cell_width = min(max(int(p.pwidth),1),min(image_width, image_height))
    aspect = int(p.pdepth) if p.pdepth != 0 else 100
    cell_count = abs(int(p.pheight)) if p.pheight != 0 else 1
    reverse = p.pheight > 0
    
    colors = np.array([color1, color2, color3], dtype=np.uint8)

    # まず セル単位のグリッド を作ります
    cell_w = cell_count * cell_width
    cell_h = int(cell_width * aspect / 100)
    if cell_h < 1:
        cell_h=1

    period = 3 * cell_count
    cols = (image_width + period * cell_width) // cell_w + cell_count
    rows = (image_height + cell_h - 1) // cell_h + 1

    # セル単位の色インデックス作成
    x_idx = np.arange(cols)[None, :]
    y_idx = np.arange(rows)[:, None]
    if reverse:
        color_map = (x_idx + y_idx) % 3
    else:
        color_map = (x_idx - y_idx) % 3

    cell_colors = colors[color_map]

    # ピクセル単位に拡大
    expanded = np.repeat(np.repeat(cell_colors, cell_h, axis=0), cell_w, axis=1)

    # メッシュグリッド（ピクセル座標）の作成
    yy, xx = np.mgrid[0:image_height, 0:image_width]

    # 各行ごとのシフト量を計算 (ピクセル単位)
    # row = yy // cell_h
    if cell_count == 1:
        shifts = 0 if reverse else cell_width
    elif reverse:
        shifts = ((period-1) - ((yy // cell_h) % period)) * cell_width
    else:
        shifts = ((yy // cell_h) % period) * cell_width

    # 参照先のX座標を一括計算
    target_xx = xx + shifts

    # expanded[y座標, x座標] で指定した座標の色を抜き出す
    img_array = expanded[yy, target_xx]

    # PIL Image に変換
    img = Image.fromarray(img_array)

    return img

if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080

    img = generate(p)
    img.show()
