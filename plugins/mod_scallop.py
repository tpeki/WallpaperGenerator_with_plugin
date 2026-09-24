import numpy as np
from PIL import Image, ImageChops
import random
from wall_common import *

# --- 基本パラメータ ---
BASE_COLOR = (0xfe, 0xd0, 0x50) # 貝の基本色 [200, 185, 170]
MAX_R = 140  # 貝の幅
RIBS = 27  # 貝の襞数
JITTER = 25  # 色ゆらぎ(%) 
SHADOW_CONTRAST = 16  # 明度設定(%)  {0..255の時の推奨は30～60 = 11～23%}

# --- 内部定数
LOC_JITTER = (15,2)  # 横位置の揺らぎ (変位数,単位ピクセル)
WIDTH_FREQ = 1.5  # 横周期
HEIGHT_FREQ = 0.75  # 縦周期 1を超えると隙間が大きく出てくる
# ================

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'ほたて貝',
                       {'color1':'基本色',
                        'color_jitter':'色変化(%)', 'sub_jitter':'陰影(%)',
                        'pwidth':'幅', 'pheight':'ひだ数'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BASE_COLOR)
    p.color_jitter = JITTER
    p.sub_jitter = SHADOW_CONTRAST
    p.pwidth = MAX_R
    p.pheight = RIBS
    return p


def create_scallop_tile(max_r, n_ribs, rib_depth, shadow_contrast):
    """1つの貝殻パーツ（透過背景）を作成する"""
    # キャンバスに十分な余白を持たせる
    tile_size = int(max_r * 2.5)
    tile = Image.new('RGBA', (tile_size, tile_size), (0, 0, 0, 0))
    pixels = tile.load()
    max_contrast = 255 - (shadow_contrast * 0.7) 
    
    cx, cy = tile_size // 2, tile_size - 108
    
    for py in range(tile_size):
        for px in range(tile_size):
            dx = px - cx
            dy = cy - py
            if dy <= 0: continue
            
            rho = np.sqrt(dx**2 + dy**2)
            theta = np.arctan2(dx, dy)
            
            # 扇の広がり角度
            max_theta = np.radians(75)  # 75
            if abs(theta) < max_theta:
                # 縁の曲線（貝殻らしい肩の落ち方）
                r_border = max_r * np.cos(theta * 0.4) * (1 + rib_depth * np.cos(n_ribs * theta))
                
                if rho < r_border:
                    norm_rho = rho / r_border
                    # 襞の陰影計算
                    # shadow_contrastを掛けることで影の深さを調整
                    shading = np.cos(n_ribs * theta) * (norm_rho ** 2) * 1.8
                    
                    # 210をベースの明るさとし、コントラストを加減
                    val = int(max_contrast + shadow_contrast * shading)
                    val = max(0, min(255, val))
                    pixels[px, py] = (val, val, val, 255)
                    
    return tile, (cx, cy)

def generate(p: Param):
    img_width = p.width
    img_height = p.height
    max_r = min(max(p.pwidth,20),int(img_width/2))
    n_ribs = min(max(p.pheight,0),240)
    base_color = p.color1
    jitter = np.clip(p.color_jitter, 0, 100)
    shadow = np.clip(p.sub_jitter, 0, 100)
    
    # --- 周期の設定 ---
    wave_w = int(max_r*3/2*WIDTH_FREQ) 
    wave_h = int(max_r/2*HEIGHT_FREQ)
    wave_j = int(LOC_JITTER[0]/LOC_JITTER[1])
    # ------------------
    
    rib_depth = np.clip(1 / n_ribs, 0.01, 0.05)
    
    
    # テンプレート作成
    scallop_template, (offset_x, offset_y) = \
                      create_scallop_tile(max_r, n_ribs,
                                          rib_depth, shadow)
    
    # メインキャンバス（背景暗灰）
    canvas = Image.new('RGBA', (img_width, img_height), (68, 68, 68, 255))
    
    # 描画ループ（奥から手前へ）
    for y in range(-max_r, img_height + max_r * 2, wave_h):
        row_count = y // wave_h
        row_shift = (wave_w // 2) if row_count % 2 == 1 else 0
        
        # 段ごとの色を決定（ジッター適用）
        current_color = rated_jitter(base_color, jitter).ctoi()
        
        # テンプレートに段の色を乗算
        colored_scallop = Image.new('RGBA', scallop_template.size,
                                    current_color + (255,))
        row_tile = ImageChops.multiply(scallop_template, colored_scallop)

        for x in range(-(wave_w), img_width + wave_w, wave_w):
            pos_x = x + row_shift - offset_x +\
                    int((wave_j/2)-random.randint(0,wave_j))*LOC_JITTER[1]
            pos_y = y - offset_y
            
            # 合成
            canvas.alpha_composite(row_tile, (pos_x, pos_y))

    # 表示
    return canvas.convert('RGB')
    

# テスト
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height= 1080
    
    img = generate(p)
    img.show()
