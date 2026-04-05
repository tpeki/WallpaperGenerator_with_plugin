import numpy as np
from PIL import Image
import random
from wall_common import *

# --- 設定定数 ---
WIDTH, HEIGHT = 1920, 1080
MARGIN = 7                 # 円と円の間の最小距離
MIN_RADIUS = 20             # 隙間を埋める最小の丸
MAX_RADIUS = 160            # 最大の丸

# 背景グラデーション色
BG_COLOR_START = (0x8b, 0xc7, 0xcf)
BG_COLOR_END = (0xba, 0xdd, 0xe2)

# 円の基本色とジッター
CIRCLE_BASE_COLOR = (0x92, 0xca, 0xd1)
COLOR_JITTER = 15
GRADIENT_ANGLE_DEG = 180  # 180度（右から左へ暗くなる）
GRADIENT_RATIO = 0.4
GRADIENT_BIAS = 0.8
# ----------------

def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       '充填型バブル',
                       {'color1':'前景色',
                        'color2':'背景色1', 'color3':'背景色2',
                        'color_jitter':'色変化', 'sub_jitter':'影角度',
                        'pwidth':'最大径', 'pheight':'最小径',
                        'pdepth':'間隔'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    p.color1.itoc(*CIRCLE_BASE_COLOR)
    p.color2.itoc(*BG_COLOR_START)
    p.color3.itoc(*BG_COLOR_END)
    p.color_jitter = COLOR_JITTER
    p.sub_jitter = GRADIENT_ANGLE_DEG
    p.pwidth = MAX_RADIUS
    p.pheight = MIN_RADIUS
    p.pdepth = MARGIN
    return p


def create_gradient_circle(radius, current_color, angle_rad):
    size = int(radius * 2)
    if size < 1: size = 1
    yy, xx = np.mgrid[:size, :size]
    cx, cy = radius, radius
    dx, dy = xx - cx, yy - cy
    
    grad_val = dx * np.cos(angle_rad) + dy * np.sin(angle_rad)
    # 安全に正規化
    denom = radius if radius > 0 else 1
    norm_grad = np.clip((grad_val / denom + 1) / 2, 0, 1)
    
    brightness = norm_grad * GRADIENT_RATIO + GRADIENT_BIAS
    rgb_arr = (np.array(current_color) * brightness[..., np.newaxis]).clip(0, 255).astype(np.uint8)

    dist = np.sqrt(dx**2 + dy**2)
    alpha_arr = (np.clip(radius - dist + 0.5, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb_arr, alpha_arr)), 'RGBA')


def generate(p: Param):
    width = p.width
    height = p.height
    bg_color1 = p.color2
    bg_color2 = p.color3
    circle_color = p.color1
    circle_jitter = p.color_jitter
    grad_angle = p.sub_jitter % 360
    max_r = min(max(p.pwidth, 10), int(width/2))
    min_r = min(max(p.pheight, 10), max_r)
    margin = min(max(p.pdepth, -100), 1000)
    
    if p.h_img is None:
        img = horizontal_gradient_rgb(width, height, bg_color1, bg_color2)
    else:
        img = p.bg()

    angle_rad = np.deg2rad(grad_angle)
    
    placed_circles = [] # (cx, cy, r)
    
    # print("Packing circles...")
    # 大きいサイズから順に隙間を埋めていく戦略
    # これにより効率的に画面が埋まる
    current_r = max_r
    
    while current_r >= min_r:
        # 現在の半径で配置を試みる回数
        attempts_at_this_size = 0
        max_attempts = 100 if current_r > 50 else 300 # 小さい円ほど粘って隙間を探す
        
        while attempts_at_this_size < max_attempts:
            cx = random.randint(-current_r, width + current_r)
            cy = random.randint(-current_r, height + current_r)
            
            # 重なり（＋マージン）チェック
            is_safe = True
            for pcx, pcy, pr in placed_circles:
                dist = np.sqrt((cx - pcx)**2 + (cy - pcy)**2)
                # 判定: 距離 < (半径1 + 半記2 + 12px)
                if dist < (current_r + pr + margin):
                    is_safe = False
                    break
            
            if is_safe:
                # 色のジッター
                ccolor = rgb_random_jitter(circle_color, circle_jitter).ctoi()
                
                circle_img = create_gradient_circle(current_r, ccolor,
                                                    angle_rad)
                img.paste(circle_img, (int(cx - current_r),
                                          int(cy - current_r)), circle_img)
                
                placed_circles.append((cx, cy, current_r))
                attempts_at_this_size = 0 # 成功したらカウントリセット
            else:
                attempts_at_this_size += 1
        
        # 現在のサイズで置けなくなったら半径を小さくして続行
        current_r -= 2 

    # print(f"Total circles placed: {len(placed_circles)}")
    return img

if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = WIDTH
    p.height = HEIGHT
    
    image = generate(p)
    image.show()
    
