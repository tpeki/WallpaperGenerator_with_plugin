import numpy as np
from PIL import Image, ImageDraw
import random
from wall_common import *

# ================= 定数 =================
BASE_COLOR=(255,255,255)  # 白指定＝6色モード
BORDER_COLOR=(0xdd, 0xdd, 0xdd)  # 目地色
JITTER=15  # タイル色の変動幅
GRAD_TONE=70  # タイル明るさ(グラデーション割合) (%) 
CELL_SIZE=80  # タイルサイズ
ANGLE_NUM=6  # 角度バリエーション
JOINT_WIDTH=2  # 目地幅

DEFAULT_COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255),
                  (255, 255, 0), (255, 0, 255), (0, 255, 255),]
DEFAULT_ANGLES = [240, 300, 180, 0, 60, 120,]
#DEFAULT_ANGLES = [240]
# =======================================


# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '六角タイル',
                       {'color1':'色(白=6色)', 'color2':'目地色',
                        'color_jitter':'色差分', 'sub_jitter':'明度(%)',
                        'sub_jitter2':'角度数(1..6)',
                        'pwidth':'タイル幅', 'pheight':'目地幅'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BASE_COLOR)
    p.color2.itoc(*BORDER_COLOR)
    p.pwidth = CELL_SIZE
    p.pheight = JOINT_WIDTH
    p.color_jitter = JITTER
    p.sub_jitter = GRAD_TONE
    p.sub_jitter2 = ANGLE_NUM
    return p


def generate(p: Param):
    width = p.width
    height = p.height
    color1 = p.color1
    border = p.color2.ctox()
    size = min(max(6,p.pwidth),width)
    jwidth = min(max(0,p.pheight),int(size*0.85))
    jitter = p.color_jitter
    tone = min(1.0, max(0.0, 1.0 - (p.sub_jitter/100)))
    angl_num = min(6, max(p.sub_jitter2, 1))
    p.sub_jitter2 = angl_num

    img = Image.new('RGB', (width, height), border)
    draw = ImageDraw.Draw(img)

    # タイル色セットの準備    
    if color1.ctox() == '#ffffff':
        basic_colors = DEFAULT_COLORS
    else:
        basic_colors = []
        for i in range(5):
            basic_colors.append(rgb_random_jitter(color1, jitter).ctoi())
        basic_colors.append(color1.ctoi())

    # 描画準備
    h = np.sqrt(3) * size
    x_step = size * 1.5
    y_step = h

    color_map = {}

    # 許可されるグラデーション角度のリスト（度）
    allowed_angles_deg = DEFAULT_ANGLES[:angl_num]

    rows = int(height / y_step) + 2
    cols = int(width / x_step) + 2

    for c in range(cols):
        for r in range(rows):
            # 隣接タイルは同色回避
            neighbor_coords = [(c, r-1), (c-1, r), (c+1, r)]
            if c % 2 == 1: neighbor_coords.extend([(c-1, r+1), (c+1, r+1)])
            else: neighbor_coords.extend([(c-1, r-1), (c+1, r-1)])
            used_colors = {color_map.get(coord) for coord in neighbor_coords if coord in color_map}
            available_colors = [i for i, _ in enumerate(basic_colors) if i not in used_colors]
            chosen_idx = random.choice(available_colors if available_colors else range(len(basic_colors)))
            color_map[(c, r)] = chosen_idx
            base_color = np.array(basic_colors[chosen_idx])

            # 座標計算
            offset = (h / 2) if (c % 2 == 1) else 0
            cx, cy = c * x_step, r * y_step + offset
            points = []
            for i in range(6):
                angle_rad = np.deg2rad(60 * i)
                points.append((cx + size * np.cos(angle_rad), cy + size * np.sin(angle_rad)))
            
            points_array = np.array(points)
            min_coords = points_array.min(axis=0).astype(int)
            max_coords = points_array.max(axis=0).astype(int)
            min_x, min_y = min_coords[0], min_coords[1]
            max_x, max_y = max_coords[0], max_coords[1]
            if max_x < 0 or min_x > width or max_y < 0 or min_y > height: continue

            mask = Image.new('L', (width, height), 0)
            ImageDraw.Draw(mask).polygon(points, fill=255)
            
            # 角度をリストから選択し、ラジアンに変換
            chosen_angle_deg = random.choice(allowed_angles_deg)
            angle = np.deg2rad(chosen_angle_deg)

            bw, bh = max(1, max_x - min_x), max(1, max_y - min_y)
            yy, xx = np.mgrid[0:bh, 0:bw]
            
            grad = xx * np.cos(angle) + yy * np.sin(angle)
            grad = (grad - grad.min()) / (grad.max() - grad.min() + 1e-5)
            grad = grad * tone + (1.0-tone)
            #print(f'grad: {grad}')

            tile_arr = (np.tile(base_color, (bh, bw, 1)) * grad[..., np.newaxis]).clip(0, 255).astype(np.uint8)
            tile_img = Image.fromarray(tile_arr)
            img.paste(tile_img, (min_x, min_y),
                      mask.crop((min_x, min_y, max_x, max_y)))

            draw.polygon(points, outline=border, width=jwidth)

    return img


if __name__ == "__main__":
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080

    p.color1.itoc(0x20, 0xa0, 0xe0)
    p.color_jitter = 45    
    image = generate(p)
    image.show()
