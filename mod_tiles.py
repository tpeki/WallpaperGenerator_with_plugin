import numpy as np
from PIL import Image
from wall_common import *

TILE_SIZE = 160
TILE_RADIUS = 12
COLOR1 = (172,217,236)  # (100, 149, 237) #
COLOR2 = (219,183,216)  # (255, 127, 80) #
COLOR3 = (158,189,149)  # (60, 179, 113) #
JITTER = 30
CHECKER = 0
JOINT_WIDTH = 5
JOINT_BRIGHTNESS = 208

# 内部定数
GRAD_STR = 0.3  # end_color = color*(1-GRAD_STR)
NOISE_THICK = 1.8  # 大きいほどnoiseが太目に出る
NOISE_RATE = 0.4  # 小さいほどnoise線の密度が上がる
LINTERVAL = 20.0  # テクスチャ(斜線)密度 (d / LINTERVAL) 20.0だとd=60でも可
PERS = 0.27  # パース強度 0.01～0.3程度

# 目地の粒状感と粒の明るさ
SAND_GRAIN_SIZE = 0.1  # 砂目率
INT_BRT = 0.15  # 明るい地の時の減算率
INT_DRK = 128  # 暗い地の時の加算率
INT_BDR = 140  # 切替閾値
                                               
# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '正方形タイル [モード 0=3色 / 1=2色 / 2=遠近法]',
                       {'color1':'色1', 'color2':'色2', 'color3':'色3',
                        'color_jitter':'色幅', 'sub_jitter':'目地明度',
                        'sub_jitter2':'モード',
                        'pwidth':'タイル幅', 'pheight':'角半径',
                        'pdepth':'目地幅(%)'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.color3.itoc(*COLOR3)
    p.pwidth = TILE_SIZE
    p.pheight = TILE_RADIUS
    p.pdepth = JOINT_WIDTH
    p.color_jitter = JITTER
    p.sub_jitter = JOINT_BRIGHTNESS
    p.sub_jitter2 = CHECKER
    return p


# ---
# 生成
# ---
def find_coeffs(pa, pb):
    """パース変換行列を計算するヘルパー関数"""
    matrix = []
    for p1, p2 in zip(pa, pb):
        matrix.append([p1[0], p1[1], 1, 0, 0, 0, -p2[0]*p1[0], -p2[0]*p1[1]])
        matrix.append([0, 0, 0, p1[0], p1[1], 1, -p2[1]*p1[0], -p2[1]*p1[1]])
    A = np.matrix(matrix, dtype=float)
    B = np.array(pb).reshape(8)
    res = np.linalg.solve(A, B)
    return np.array(res).reshape(8)


def generate(p: Param):
    width, height = p.width, p.height

    d = p.pwidth  #Tile size
    r = p.pheight  # Tile radius
    joint_width = min(max(1, int(d * p.pdepth / 100)), d-1)
    joint_color = [p.sub_jitter]*3
    sand_grain_size = SAND_GRAIN_SIZE  # * p.sub_jitter/512
    if p.sub_jitter > INT_BDR:
        sand_intensity = 1.0 - INT_BRT
        sand_int_add = 0
    else:
        sand_intensity = 0
        sand_int_add = ((INT_BDR-p.sub_jitter)/INT_BDR)**2 * INT_DRK
    jitter = p.color_jitter
    color1 = rgb_random_jitter(p.color1, jitter).ctoi()
    color2 = rgb_random_jitter(p.color2, jitter).ctoi()
    color3 = rgb_random_jitter(p.color3, jitter).ctoi()
    if (p.sub_jitter2 & 1) == 1:
        colors = [color1, color2]
    else:
        colors = [color1, color2, color3]
    if (p.sub_jitter2 & 2) == 2:
        org_w, org_h = width, height
        margin_w, margin_h = int(width*0.3), int(height*0.3)
        width = width+margin_w*2
        height = height+margin_h*2
    
    # 1. ベース作成（目地色）
    img_array = np.full((height, width, 3), joint_color, dtype=np.float32)
    grain_mask = np.random.rand(height, width) < sand_grain_size
    img_array[grain_mask] *= sand_intensity
    img_array[grain_mask] += sand_int_add
    
    tile_size = d - joint_width
    rows = (height + d - 1) // d
    cols = (width + d - 1) // d
    total_h = rows * d
    total_w = cols * d
    offset_y = (height - total_h) // 2
    offset_x = (width - total_w) // 2
    num_colors = len(colors)

    # タイルごとの色インデックスを記録
    color_indices = np.full((rows, cols), -1, dtype=int)

    # --- 共通データの事前計算 ---
    ty, tx = np.meshgrid(np.arange(tile_size),
                         np.arange(tile_size), indexing='ij')
    
    # 角丸マスク
    mask_full = np.ones((tile_size, tile_size), dtype=bool)
    corners = [(r, r), (r, tile_size-1-r), (tile_size-1-r, r),
               (tile_size-1-r, tile_size-1-r)]
    for cy, cx in corners:
        dist_sq = (ty - cy)**2 + (tx - cx)**2
        if cy == r and cx == r: region = (ty < r) & (tx < r)
        elif cy == r: region = (ty < r) & (tx > cx)
        elif cy > r and cx == r: region = (ty > cy) & (tx < r)
        else: region = (ty > cy) & (tx > cx)
        mask_full[region] = dist_sq[region] <= r**2

    # グラデーションマップ
    grad_map = ((ty + tx) / ((tile_size - 1) * 2)).astype(np.float32)[:, :, np.newaxis]
    line_base = (ty + tx).astype(np.float32)
    line_interval = d / LINTERVAL

    # --- 各タイルの描画 ---
    for row in range(rows):
        y0 = offset_y + row*d + joint_width//2
        dy0, dy1 = max(0, y0), min(y0 + tile_size, height)
        if dy1 <= dy0: continue
        sy = slice(dy0 - y0, dy1 - y0)

        for col in range(cols):
            x0 = offset_x + col*d + joint_width//2
            dx0, dx1 = max(0, x0), min(x0 + tile_size, width)
            if dx1 <= dx0: continue
            sx = slice(dx0 - x0, dx1 - x0)

            # 色の決定
            if num_colors == 2:  # 2色の場合は市松模様
                c_idx = (row + col) % 2
            else:  # 3色以上の場合は、同色3枚隣接禁止のランダム
                possible_indices = list(range(num_colors))
                for e in ((-2,0), (-1,-1), (-1,1)):
                    if (0 <= col+e[1] < cols) and \
                       0 <= row+e[0] and \
                       color_indices[row-1, col] == color_indices[row+e[0], col+e[1]]:
                        invalid = color_indices[row-1, col]
                        if invalid in possible_indices:
                            possible_indices.remove(invalid)
                for e in ((-1,-1), (-1,0), (0,-2)):
                    if 0 <= col+e[1] and \
                       (0 <= row+e[0] < rows) and \
                       color_indices[row, col-1] == color_indices[row+e[0], col+e[1]]:
                        invalid = color_indices[row, col-1]
                        if invalid in possible_indices:
                            possible_indices.remove(invalid)
                            
                c_idx = np.random.choice(possible_indices)

            color_indices[row, col] = c_idx
            base_color = np.array(colors[c_idx], dtype=np.float32)
            
            # グラデーション
            tile_rgb = base_color * (1.0 - grad_map[sy, sx] * GRAD_STR)
            # 1.0 -> 0.7

            # ラインテクスチャ
            offset = np.random.rand() * line_interval
            line_mask = ((line_base[sy, sx] + offset) % line_interval) < NOISE_THICK
            noise = np.random.rand(dy1-dy0, dx1-dx0) > NOISE_RATE
            
            # ラインの色塗り (tile_rgbを直接書き換え)
            line_rgb = base_color * np.random.uniform(0.7, 0.9)
            tile_rgb[line_mask & noise] = line_rgb

            # マスク適用
            m = mask_full[sy, sx]
            img_array[dy0:dy1, dx0:dx1][m] = tile_rgb[m]  # .astype(np.uint8)

    # --- 最後に一括で目地・タイル全体のノイズ処理 ---
    #noise = np.random.normal(0, 2, img_array.shape).astype(np.int16)
    #img_arry = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    noise = np.random.normal(0, 2, img_array.shape)
    img_arry = np.clip(img_array + noise, 0, 255).astype(np.uint8)
    image = Image.fromarray(img_arry)

    if (p.sub_jitter2 & 2) == 2:
        # --- パース変換の定義 ---
        # 大きな画像の中から、どの台形領域を抜き出して(width, height) に
        # フィットさせるか
        tilt = org_w * PERS  # パース強度 
        
        # ターゲット（台形）の4点座標
        # 奥（上辺）を狭くし、手前（下辺）を広く取る
        src_points = [
            (margin_w + org_w + tilt, margin_h + org_h), # 右下
            (margin_w - tilt, margin_h + org_h),      # 左下
            (margin_w + tilt, margin_h),              # 左上
            (margin_w + org_w - tilt, margin_h),     # 右上
        ]
        
        # 出力先の四隅
        dest_points = [
            (0, 0), (org_w, 0), (org_w, org_h), (0, org_h)
        ]

        coeffs = find_coeffs(dest_points, src_points)
        
        # 変形と同時に、指定サイズで切り出し
        image = image.transform((org_w, org_h), Image.PERSPECTIVE,
                                coeffs, Image.BICUBIC)
            
    return image

# --- 実行 ---
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width, p.height = 1920, 1080
    
    image = generate(p)
    image.show()
