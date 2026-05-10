import numpy as np
import math
from PIL import Image
import random
import copy
import TkEasyGUI as sg
from wall_common import *

# 可変生成パラメータ
WIDTH = 1920
HEIGHT = 1080

BASE_COLOR = (17, 96, 0)
FRONT_COLOR = (160, 160, 160)

FRONT_JITTER = 40  # 前景色を-n%～+n%でランダムに(0-255でclip)
SIZE_JITTER = 50  # ランダム時：大きさを 1-#n%～ 1+n% でランダムに拡縮
ALIGN_MODE = 1  # 0:align 1:random

BASE_R = 7 # 200 -> (BASE_R(1,20) * 50)に変更 (BASE_R=215前後で候補が拾えず)
DEPLOY_NUM = 25
STYLE = 25  # 形状閾値 0.235 ± STYLE/1000  0.16<x<0.31 -> 50+STYLE(0,100) に

# 内部定数
RSIZE = 200
PEN_RADIUS = 3 
FOCUS = 0.7
CONTRAST = 0.85

MASK_CACHE_SIZE = 6
RETRY = 20  # パターン生成中リトライ
MAXATTEMPTS = 100  # パターン生成リトライ

fwks_preserv = {}
PPARAMS = ['icr', 'iodr', 'smin', 'smax', 'dmin', 'dmax', 'spmn', 'spmx']
DPARAMS = {
    'minar': [12, 0, 100],  # drawn area / outer circle area (not tunable)
    'icr':  [30, 1, 99],  # inner circle radius(%)
    'iodr': [5, 0, 45],  # minimum inner-outer density ratio(%)
    'smin': [20, 1, 99],  # small circle size (% with outer circle radius)
    'smax': [67, 2, 100],
    'dmin': [18, 1, 120],  # distance (% with inner circle radius)
    'dmax': [58, 1, 120],
    'spmn': [5, 1, 100],  # spin number
    'spmx': [32, 1, 100],
    }

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '花模様(スピログラフ) 配置 0格子,1ランダム',
                       {'color1':'背景色', 'color2':'基本色',
                        'color_jitter':'色変動%',
                        'sub_jitter':'サイズ変動%',
                        'sub_jitter2':'配置方法',
                        'pwidth':'外接円(2..20)', 'pheight':'配置数',
                        'pdepth':'スタイル'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BASE_COLOR)
    p.color2.itoc(*FRONT_COLOR)
    p.color_jitter = FRONT_JITTER
    p.sub_jitter = SIZE_JITTER
    p.sub_jitter2 = ALIGN_MODE
    p.pwidth = BASE_R
    p.pheight = DEPLOY_NUM
    p.pdepth = STYLE
    if len(fwks_preserv) == 0:
        set_fwks_preserv()
    
    return p

# -----------------------------
# 内部パラメータ初期化
# -----------------------------
def set_fwks_preserv():
    for name in PPARAMS:
        fwks_preserv[name] = DPARAMS[name][0]
        
    fwks_preserv['minar'] = DPARAMS['minar'][0]
    return


# -----------------------------
# パラメータ調整
# -----------------------------
def clip(v,n,x):
    return min(max(v,n),x)
    
def desc(p: Param):
    oparam = copy.deepcopy(p)
    opreserv = copy.deepcopy(fwks_preserv)
    change = False

    lo = [[sg.Text('[FlowerWorlks tuning]'),
           sg.Text('CAUTION!! It crashes process sometime.',
                   text_color='#dd0000')],
          [sg.Text('* Basic Parameters')],
          [sg.Text(' Outer circle radius(x50) [2-20]:'),
           sg.Input(key='-orad-', width=6, enable_events=True)
           ],
          [sg.Text(' Style indicator [0-100]:'),
           sg.Input(key='-style-', width=6, enable_events=True),
           sg.Text(' Calcurated style range min='),
           sg.Text(key='-lsty-', width=6, background_color='white'),
           sg.Text(' max='),
           sg.Text(key='-hsty-', width=6, background_color='white'),
           ],
          [sg.Text('* Pattern Sieving')],
          [sg.Text(f' Inner-area ratio ['+
                   f'{DPARAMS["icr"][1]}-{DPARAMS["icr"][2]}]:'),
           sg.Input(f"{fwks_preserv['icr']}",
                    key='-icr-', width=4),
           sg.Text(' least inner-outer density ratio ['+
                   f'{DPARAMS["iodr"][1]}-{DPARAMS["iodr"][2]}]:'),
           sg.Input(f"{fwks_preserv['iodr']}",
                    key='-iodr-', width=4),
           ],
          [sg.Text(' Innner gear radius ['+
                   f'{DPARAMS["smin"][1]}-{DPARAMS["smax"][2]}]:'),
           sg.Text(' Low='),
           sg.Input(f"{fwks_preserv['smin']}",
                    key='-smin-', width=4),
           sg.Text('<= r <=High='),
           sg.Input(f"{fwks_preserv['smax']}",
                    key='-smax-', width=4),
           ],
          [sg.Text(' Innner gear spin ['+
                   f'{DPARAMS["spmn"][1]}-{DPARAMS["spmx"][2]}]:'),
           sg.Text(' Low='),
           sg.Input(f"{fwks_preserv['spmn']}",
                    key='-spmn-', width=4),
           sg.Text('<= spin <=High='),
           sg.Input(f"{fwks_preserv['spmx']}",
                    key='-spmx-', width=4),
           ],
          [sg.Text(' Pen eccentricity ['+
                   f'{DPARAMS["dmin"][1]}-{DPARAMS["dmax"][2]}]:'),
           sg.Text(' inner='),
           sg.Input(f"{fwks_preserv['dmin']}",
                    key='-dmin-', width=4),
           sg.Text('<= x <= outer='),
           sg.Input(f"{fwks_preserv['dmax']}",
                    key='-dmax-', width=4),
           ],
          [sg.Button('Default', key='-default-', background_color='#ffffdd'),
           sg.Text('', expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Apply', key='-ok-', background_color='#ddffdd'),
           ]]

    wn = sg.Window('Config', layout=lo, modal=True)
    wn['-orad-'].update(f'{p.pwidth}')
    wn['-style-'].update(f'{p.pdepth}')
    fs = (p.pdepth+50)//20
    lsty = max(fs,2)
    hsty = min(10, fs+11)
    wn['-lsty-'].update(f'{lsty}')
    wn['-hsty-'].update(f'{hsty}')
   
    while True:
        ev, va = wn.read()
        # print(ev, va)
        
        if oparam.pdepth != int(wn['-style-'].get(),0):
            fs = oparam.pdepth // 20
            lsty = max(fs,2)
            hsty = min(10, fs+11)
            wn['-lsty-'].update(f'{lsty}')
            wn['-hsty-'].update(f'{hsty}')
            
        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            break
        elif ev == '-ok-':
            p.pwidth = clip(int(wn['-orad-'].get(),0), 2, 20)
            p.pdepth = clip(int(wn['-style-'].get(),0),0,100)
            if wn.parent_window is not None:
               wn.parent_window['-pwidth-1'].update(p.pwidth)
               wn.parent_window['-pdepth-1'].update(p.pdepth) 
            for name in PPARAMS:
                try:
                    d = int(wn[f'-{name}-'].get(),0)
                except ValueError:
                    d = fwks_preserv[name]
                    wn[f'-{name}-'].update(f'{d}')
                d = clip(d, DPARAMS[name][1], DPARAMS[name][2])
                if name == 'smax' and d <= fwks_preserv['smin']:
                    d = fwks_preserv['smin']+1
                elif name == 'dmax' and d < fwks_preserv['dmin']:
                    d = fwks_preserv['dmin']
                elif name == 'spmx' and d < fwks_preserv['spmn']:
                    d = fwks_preserv['spmn']
                    
                fwks_preserv[name] = d
            break
        elif ev == '-default-':
            p.pwidth = oparam.pwidth
            wn['-orad-'].update(int(clip(p.pwidth,2,20)))
            p.pdepth = oparam.pdepth
            wn['-style-'].update(int(clip(p.pdepth,0,100)))
            for name in PPARAMS:
                d = DPARAMS[name][0]
                fwks_preserv[name] = d
                wn[f'-{name}-'].update(f'{d}')
            wn.refresh()

    wn.close()
    if oparam.pwidth != p.pwidth or oparam.pdepth != p.pdepth:
        change = True
    for name in PPARAMS:
        if opreserv[name] != fwks_preserv[name]:
            change = True
    
    if change:
        img = generate(p)
        return img
    else:
        return
          

# -----------------------------
# ペン（ぼかし付き）
# -----------------------------
def make_pen_kernel(fradius):
    offsets = []
    weights = []
    radius = int(fradius)
    
    for dx in range(-radius-1, radius+2):
        for dy in range(-radius-1, radius+2):
            dist = np.sqrt(dx*dx + dy*dy)

            if dist <= fradius + 0.5:
                # --- 中心強調＋なだらか減衰 ---
                w = 1.0 - (dist / (fradius + 0.5))**1.5
                offsets.append((dx, dy))
                weights.append(w)

    offsets = np.array(offsets, dtype=np.int16)
    weights = np.array(weights, dtype=np.float32)

    # 正規化（強すぎ防止）
    weights /= weights.max()

    return offsets, weights


# -----------------------------
# スピログラフマスク（float）
# -----------------------------
def make_spiro_mask(size, center_R, r, d, offsets, weights, pad, n_points=8000):
    W, H = size

    t = np.linspace(0, 2*np.pi * r, n_points, dtype=np.float32)
    k = (center_R - r) / r

    x = (center_R - r)*np.cos(t) + d*np.cos(k*t)
    y = (center_R - r)*np.sin(t) - d*np.sin(k*t)

    # 正規化
    x = (x - x.min()) / (x.max() - x.min()+1e-6)
    y = (y - y.min()) / (y.max() - y.min()+1e-6)

    margin = pad / W
    x = x * (1 - 2*margin) + margin
    y = y * (1 - 2*margin) + margin

    x = (x * (W - 1)).astype(np.int16)
    y = (y * (H - 1)).astype(np.int16)

    mask = np.zeros((H, W), dtype=np.float32)

    # --- ペン描画（ぼかし付き） ---
    for (dx, dy), w in zip(offsets, weights):
        xx = x + dx
        yy = y + dy

        valid = (0 <= xx) & (xx < W) & (0 <= yy) & (yy < H)

        # 加算ではなくmaxで自然に重ねる
        mask[yy[valid], xx[valid]] = np.maximum(
            mask[yy[valid], xx[valid]],
            w
        )

    return mask


# -----------------------------
# ランダムマスク生成
# -----------------------------
def generate_random_mask(offsets, weights, radius, pen_size, style=115):
    lsty = max(style//20,2)
    hsty = min(10, style//20+11)
    pad = int(pen_size * 2.5) + 4
    pw = pen_size**2 * np.pi
    size = radius + 2 * pad
    center = size/2

    # 領域の閾値（距離の2乗）
    inner_r2 = (radius * fwks_preserv['icr']/100) ** 2
    outer_r2 = radius ** 2
    
    minar = fwks_preserv['minar']
    iodr = fwks_preserv['iodr'] / 100.0
    smin = fwks_preserv['smin']
    smax = fwks_preserv['smax']
    dmin = fwks_preserv['dmin']
    dmax = fwks_preserv['dmax']
    spmn = fwks_preserv['spmn']
    spmx = fwks_preserv['spmx']

    for _ in range(RETRY):
        r = int(random.randint(smin,smax) * 0.01 * radius)
        d = int(random.randint(dmin,dmax) * 0.01 * r)

        gcd = math.gcd(radius,r)
        N = radius / gcd  # 小円自転数 spin
        M = r / gcd  # 小円公転数 orbit
        ar = 2*r*d*N*pw / outer_r2  # 全体との面積比(理論値)

        if N < spmn or spmx < N:
            continue
        if M < lsty or hsty < M:  # if M < 2 or 12 < M:
            continue
        if ar < minar/100:
            continue
 
        mask = make_spiro_mask((size, size), radius//2, r, d,
                               offsets, weights, pad)
        # print(_, r, d, f'{N:03.2f} {M:03.2f} {ar:03.3f}')

        active_pixels = mask > 0.1
        total_dots = np.count_nonzero(active_pixels)
        y, x = np.where(active_pixels)
        dist2 = (x - center)**2 + (y - center)**2
        inner_count = np.count_nonzero(dist2 < inner_r2)
        if inner_count/total_dots < iodr:
            continue
       
        return mask

    #print('missed')
    return None

# -----------------------------
# メイン描画（numpy合成）
# -----------------------------
# ランダム版
def scatter_spiro(p: Param):
    iwidth, iheight = p.width, p.height
    largest = max(iwidth, iheight)
    flower = p.color2.ctoi()
    fl_var = p.color_jitter
    sz_var = p.sub_jitter
    
    fradius = clip(p.pwidth, 2, 20) * 50
    fnum = p.pheight
    fstyle = clip(p.pdepth, 0, 100) + 50
    
    pen_size = fradius/RSIZE + 2 # PEN_RADIUS

    # float canvas
    canvas_rgb = np.zeros((iheight, iwidth, 3), dtype=np.float32)
    canvas_a   = np.zeros((iheight, iwidth, 1), dtype=np.float32)

    offsets, weights = make_pen_kernel(pen_size)

    # --- マスクキャッシュ ---
    masks = []
    attempts = 0

    while len(masks) < MASK_CACHE_SIZE and attempts < MAXATTEMPTS:
        attempts += 1
        m = generate_random_mask(offsets, weights, fradius, pen_size, fstyle)
        if m is not None:
            m_tmp = Image.fromarray(m)
            m_reg = m_tmp.resize((RSIZE, RSIZE), resample=Image.BILINEAR)
            masks.append(np.array(m_reg, dtype=np.float32))

    if not masks:
        print("mask生成失敗")
        rgba = np.dstack([canvas_rgb, canvas_a*255])
        return rgba

    # -------------------------
    # 配置
    # -------------------------
    for _ in range(fnum):
        base_mask = random.choice(masks)

        # スケール
        scale = random.uniform(1.0 - sz_var/100.0,
                               1.0 + sz_var/100.0)
        
        new_size = int(base_mask.shape[0] * scale)
        new_size = np.clip(new_size, 50, largest)

        mask_img = Image.fromarray((base_mask * 255).astype(np.uint8))
        mask_img = mask_img.resize((new_size, new_size), Image.BILINEAR)

        # 回転
        angle = random.uniform(0, 360)
        mask_img = mask_img.rotate(angle, expand=True)

        mask = np.array(mask_img, dtype=np.float32) / 255.0

        h, w = mask.shape

        # 色
        seed = np.random.randint(-fl_var, fl_var, size=3)
        color = np.array([
            clip8(flower[i] + flower[i]*seed[i]/100)
            for i in range(3)
        ], dtype=np.float32)

        # 位置
        x = random.randint(-w//2, iwidth - w//2)
        y = random.randint(-h//2, iheight - h//2)

        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(iwidth, x + w)
        y1 = min(iheight, y + h)

        if x0 >= x1 or y0 >= y1:
            continue

        mx0 = x0 - x
        my0 = y0 - y
        mx1 = mx0 + (x1 - x0)
        my1 = my0 + (y1 - y0)

        sub_mask = mask[my0:my1, mx0:mx1][..., None]
        alpha = sub_mask ** FOCUS * CONTRAST

        dst_rgb = canvas_rgb[y0:y1, x0:x1]
        dst_a   = canvas_a[y0:y1, x0:x1]

        # アルファ合成（over演算）
        out_a = alpha + dst_a * (1 - alpha)

        # 0除算防止
        out_rgb = (color * alpha + dst_rgb * dst_a * (1 - alpha))
        out_rgb /= np.maximum(out_a, 1e-6)

        canvas_rgb[y0:y1, x0:x1] = out_rgb
        canvas_a[y0:y1, x0:x1]   = out_a

    # 仕上げ
    #return canvas
    rgba = np.dstack([canvas_rgb,canvas_a * 255])
    return rgba


# 整列版
def align_spiro(p: Param):
    iwidth, iheight = p.width, p.height
    flower = p.color2.ctoi()
    fl_var = p.color_jitter
    sz_var = p.sub_jitter
    
    fradius = clip(p.pwidth, 2, 20) * 50
    fnum = p.pheight
    fstyle = clip(p.pdepth, 0, 100) + 50
    
    pen_size = fradius/RSIZE + 2 # PEN_RADIUS
    
    canvas_rgb = np.zeros((iheight, iwidth, 3), dtype=np.float32)
    canvas_a   = np.zeros((iheight, iwidth, 1), dtype=np.float32)

    offsets, weights = make_pen_kernel(pen_size)

    # --- マスクキャッシュ（scatterと同じ） ---
    masks = []
    attempts = 0

    while len(masks) < MASK_CACHE_SIZE and attempts < MAXATTEMPTS:
        attempts += 1
        m = generate_random_mask(offsets, weights, fradius, pen_size, fstyle)
        if m is not None:
            m_tmp = Image.fromarray(m)
            m_reg = m_tmp.resize((RSIZE, RSIZE), resample=Image.BILINEAR)
            masks.append(np.array(m_reg, dtype=np.float32))

    if not masks:
        print("mask生成失敗")
        rgba = np.dstack([canvas_rgb, canvas_a*255])
        return rgba

    # -------------------------
    # 配置パラメータ
    # -------------------------
    cols = fnum
    cell = iwidth / cols
    rows = int(iheight / cell)+1

    grid_w = cell * cols
    grid_h = cell * rows

    # 余白（センタリング）
    offset_x = (iwidth - grid_w) / 2
    offset_y = (iheight - grid_h) / 2

    for j in range(rows):
        for i in range(fnum):

            base_mask = random.choice(masks)

            # --- サイズ固定 ---
            target_size = int(cell * 0.9)

            mask_img = Image.fromarray((base_mask * 255).astype(np.uint8))
            mask_img = mask_img.resize((target_size, target_size),
                                       Image.BILINEAR)

            # --- 回転 ---
            angle = random.uniform(0, 360)
            mask_img = mask_img.rotate(angle, expand=True)

            mask = np.array(mask_img, dtype=np.float32) / 255.0

            h, w = mask.shape

            # --- 色 ---
            seed = np.random.randint(-fl_var, fl_var, size=3)
            color = np.array([
                clip8(flower[k] + flower[k]*seed[k]/100)
                for k in range(3)
            ], dtype=np.float32)

            # --- セル中央に配置 ---
            cx = offset_x + (i + 0.5) * cell
            cx = int(cx + offset_x*(random.random()-0.5)*0.05)
            cy = offset_y + (j + 0.5) * cell
            cy = int(cy + offset_y*(random.random()-0.5)*0.05)

            x = cx - w // 2
            y = cy - h // 2

            # --- クリッピング ---
            x0 = max(0, x)
            y0 = max(0, y)
            x1 = min(iwidth, x + w)
            y1 = min(iheight, y + h)

            if x0 >= x1 or y0 >= y1:
                continue

            mx0 = x0 - x
            my0 = y0 - y
            mx1 = mx0 + (x1 - x0)
            my1 = my0 + (y1 - y0)

            sub_mask = mask[my0:my1, mx0:mx1][..., None]
            alpha = sub_mask ** FOCUS * CONTRAST
            # alpha = (sub_mask ** FOCUS) * (CONTRAST*1.5)
            
            dst_rgb = canvas_rgb[y0:y1, x0:x1]
            dst_a   = canvas_a[y0:y1, x0:x1]
            
            out_a = alpha + dst_a * (1 - alpha)
            
            out_rgb = (color * alpha + dst_rgb * dst_a * (1 - alpha))
            out_rgb /= np.maximum(out_a, 1e-6)

            canvas_rgb[y0:y1, x0:x1] = out_rgb
            canvas_a[y0:y1, x0:x1]   = out_a
            
    # return canvas
    rgba = np.dstack([canvas_rgb, canvas_a*255])
    return rgba


# イメージ生成FE
def generate(p: Param):
    if p.sub_jitter2:
        fg = scatter_spiro(p)
    else:
        fg = align_spiro(p)
    
    #canvas = np.clip(canvas, 0, 255).astype(np.uint8)
    #return Image.fromarray(canvas)

    fg = np.clip(fg, 0, 255).astype(np.uint8)
    fg_img = Image.fromarray(fg, mode='RGBA')

    # 背景生成
    if p.h_img is None:
        bg = Image.new('RGB', (p.width, p.height), p.color1.ctox())
    else:
        bg = p.bg()

    # アルファで貼り付け
    bg.paste(fg_img, (0, 0), fg_img.split()[3])
    return bg


# -----------------------------
# 実行
# -----------------------------
if __name__ == "__main__":
    if len(fwks_preserv) == 0:
        set_fwks_preserv()
        
    p = default_param(Param())
    img = generate(p)
    img.show()
