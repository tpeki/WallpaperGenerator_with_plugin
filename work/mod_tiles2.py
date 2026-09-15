import numpy as np
from PIL import Image
from wall_common import *

TILE_SIZE = 160
TILE_RADIUS = 12
COLOR1 = (0xac, 0xd9, 0xec)
COLOR2 = (0xd8, 0xb7, 0xd8)
COLOR3 = (0x9e, 0xbd, 0x95)
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

tiles_preserv = {'colors': [COLOR1, COLOR2, COLOR3, (0x64, 0x95, 0xed),
                            (0xff, 0x7f, 0x50), (0x3c, 0xb3, 0x71),],
                 'common': {'ncolor': 3, 'tsize': TILE_SIZE,
                            'round': TILE_RADIUS, 'jitter': 30,
                            'shadeint': 0, 'shadecol': (0,0,0),
                            'shadethick': 1, '3d': 0, 'pers': PERS,
                            'angle': 0, },
                 'joint': {'color': ((JOINT_BRIGHTNESS,)*3),
                           'thick': JOINT_WIDTH, 'grain': SAND_GRAIN_SIZE,
                           'bright':INT_BRT , 'dark': INT_DRK,
                           'boder': INT_BDR},
                 'scratchedsand': {'grad': GRAD_STR, 'pitch':LINTERVAL,
                                   'grain': NOISE_THICK,
                                   'density': NOISE_RATE},
                 }
                                   

                                               
# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '正方形タイル [モード 0=3色 / 1=2色 / 2=遠近法]',
                       {'color1':'色1', 'color2':'色2', 'color3':'色3',
                        'color_jitter':'色幅', 'sub_jitter':'目地明度',
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
    return p


def get_hist(atname, catname, default=None, lo=None, hi=None):
    if catname in tiles_preserv:
        categ = tiles_preserv[catname]
    else:
        categ = {}
        tiles_preserv[catname] = categ
    if atname in categ:
        value = categ[atname]
        if value is None:
            value = default
            categ[atname] = value
    else:
        value = default
        categ[atname] = value

    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def set_hist(atname, catname, value):
    if catname not in tiles_preserv:
        tiles_preserv[catname] = {}
    tiles_preserv[catname][atname] = value
    
    return value


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

def trans_pers(image, margin_w, margin_h, org_w, org_h, view):
    
    # --- パース変換の定義 ---
    # 大きな画像の中から、どの台形領域を抜き出して(width, height) に
    # フィットさせるか
    tilt = org_w * view  # パース強度 
    
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


def pre_rotate_size(target_w, target_h, angle):
    """angle度回転した後targetが内接できるサイズ(W,H)を求める"""
    angle_rad = np.deg2rad(angle)
    s = abs(np.sin(angle_rad))
    c = abs(np.cos(angle_rad))

    # target を -angle 回転したときの外接矩形サイズ
    Bw = target_w * c + target_h * s
    Bh = target_w * s + target_h * c

    # 同じアスペクト比の外接矩形 temp_w,temp_h のスケール係数
    k = max(Bw / target_w, Bh / target_h)

    temp_w = k * target_w
    temp_h = k * target_h

    return int(temp_w), int(temp_h)  #, k


def generate(p: Param):
    org_w, org_h = p.width, p.height
    width, height = org_w, org_h

    d = set_hist('tsize', 'common', p.pwidth)  #Tile size
    rr = set_hist('round', 'common', p.pheight)  # Tile radius
    jw = set_hist('thick', 'joint', p.pdepth)
    joint_width = min(max(1, int(d * jw / 100)), d-1)
    joint_color = set_hist('color', 'joint', ((p.sub_jitter,)*3))
    joint_brightness = sum(joint_color)/len(joint_color)
    
    joint_grain = get_hist('grain', 'joint', SAND_GRAIN_SIZE)
    int_bdr = get_hist('border', 'joint', INT_BDR)
    int_brt = get_hist('bright', 'joint', INT_BRT)
    int_drk = get_hist('dark', 'joint', INT_DRK)
    if joint_brightness > int_bdr:
        sand_intensity = 1.0 - int_brt
        sand_int_add = 0
    else:
        sand_intensity = 0
        sand_int_add = ((int_bdr-joint_brightness)/int_bdr)**2 * int_drk


    colors = tiles_preserv['colors']
    colors[0] = p.color1.ctoi()
    colors[1] = p.color2.ctoi()
    colors[2] = p.color3.ctoi()
    tiles_preserv['colors'] = colors
    num_colors = get_hist('ncolor', 'common', 3)
    jitter = set_hist('jitter', 'common', p.color_jitter)

    persmode = get_hist('3d', 'common', 0) == 1
    pers_str = get_hist('pers', 'common', PERS)
    if persmode:  # 3dにする場合は元画像を大きめに
        margin_w, margin_h = int(width*0.3), int(height*0.3)
        width = width+margin_w*2
        height = height+margin_h*2
    
    angle = get_hist('angle', 'common', 0) % 360
    if angle != 0:
        a_width, a_height = width, height
        width, height = pre_rotate_size(width, height, angle)

    # 1. ベース作成（目地色）
    baseimg = p.bg(width, height)
    if baseimg is None:
        baseimg = Image.new('RGB', (width, height), joint_color)
    else:
        baseimg = baseimg.convert('RGB')

    img_array = np.asarray(baseimg, dtype=np.float32)
    grain_mask = np.random.rand(height, width) < joint_grain
    img_array[grain_mask] *= sand_intensity
    img_array[grain_mask] += sand_int_add
    
    tile_size = d - joint_width
    rows = (height + d - 1) // d
    cols = (width + d - 1) // d
    total_h = rows * d
    total_w = cols * d
    offset_y = (height - total_h) // 2
    offset_x = (width - total_w) // 2

    # タイルごとの色インデックスを記録
    color_idx = np.full((rows, cols), -1, dtype=int)

    # --- 共通データの事前計算 ---
    ty, tx = np.meshgrid(np.arange(tile_size),
                         np.arange(tile_size), indexing='ij')
    
    # 角丸マスク
    mask_full = np.ones((tile_size, tile_size), dtype=bool)
    tr = min(max(0, int(tile_size * rr / 100)), tile_size//2)
    #print(f'tile:{d} round:{rr}% -> {tr}')
    
    corners = [(tr, tr), (tr, tile_size-1-tr), (tile_size-1-tr, tr),
               (tile_size-1-tr, tile_size-1-tr)]
    for i, (cy, cx) in enumerate(corners):
        dist_sq = (ty - cy)**2 + (tx - cx)**2
        if i == 0:
            region = (ty < tr) & (tx < tr)
        elif i == 1:
            region = (ty < tr) & (tx > cx)
        elif i == 2:
            region = (ty > cy) & (tx < tr)
        else:
            region = (ty > cy) & (tx > cx)
        mask_full[region] = dist_sq[region] <= tr**2

    # グラデーションマップ
    grad_map = ((ty + tx) / ((tile_size - 1) * 2)
                ).astype(np.float32)[:, :, np.newaxis]
    line_base = (ty + tx).astype(np.float32)
    line_interval = d / get_hist('pitch', 'scratchedsand', LINTERVAL)

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
                possible_idx = list(range(num_colors))
                for e0,e1 in ((-2,0), (-1,-1), (-1,1)):
                    
                    if (0 <= col+e1 < cols) and \
                       0 <= row+e0 and \
                       color_idx[row-1, col] == color_idx[row+e0, col+e1]:
                        invalid = color_idx[row-1, col]
                        if invalid in possible_idx:
                            possible_idx.remove(invalid)
                for e0,e1 in ((-1,-1), (-1,0), (0,-2)):
                    if 0 <= col+e1 and \
                       (0 <= row+e0 < rows) and \
                       color_idx[row, col-1] == color_idx[row+e0, col+e1]:
                        invalid = color_idx[row, col-1]
                        if invalid in possible_idx:
                            possible_idx.remove(invalid)
                            
                c_idx = np.random.choice(possible_idx)

            color_idx[row, col] = c_idx
            base_color = np.array(colors[c_idx], dtype=np.float32)
            
            # グラデーション
            grad = get_hist('grad', 'scratchedsand', GRAD_STR)
            tile_rgb = base_color * (1.0 - grad_map[sy, sx] * grad)
            # 1.0 -> 0.7

            # ラインテクスチャ
            grain = get_hist('grain', 'scratchedsand', NOISE_THICK)
            dens = get_hist('density', 'scratchedsand', NOISE_RATE)
            
            offset = np.random.rand() * line_interval
            line_mask = ((line_base[sy, sx] + offset) % line_interval) < grain
            noise = np.random.rand(dy1-dy0, dx1-dx0) > dens
            
            # ラインの色塗り (tile_rgbを直接書き換え)
            line_rgb = base_color * np.random.uniform(0.7, 0.9)
            tile_rgb[line_mask & noise] = line_rgb

            # マスク適用
            m = mask_full[sy, sx]
            img_array[dy0:dy1, dx0:dx1][m] = tile_rgb[m]  # .astype(np.uint8)

    # --- 最後に一括で目地・タイル全体のノイズ処理 ---
    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
    image = Image.fromarray(img_array).convert('RGBA')

    if angle != 0:
        image = image.rotate(angle, resample=Image.BICUBIC, expand=True)
        iw, ih = image.size
        sx, sy = (iw-a_width)//2,(ih-a_height)//2 
        # image.show()
        # print(iw,ih, '->', sx,sy, sx+a_width, sy+a_height)
        image = image.crop((sx,sy, sx+a_width, sy+a_height))

    if persmode:
        image = trans_pers(image, margin_w, margin_h,
                           org_w, org_h, pers_str)
  
    return image

# --- 実行 ---
if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width, p.height = 1920, 1080
    
    image = generate(p)
    image.show()
