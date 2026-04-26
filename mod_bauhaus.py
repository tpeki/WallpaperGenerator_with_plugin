import numpy as np
from PIL import Image
from wall_common import *
import TkEasyGUI as sg
import copy

#--------------------
# 定数
#--------------------
WIDTH = 1920
HEIGHT = 1080

TILE = 120
COLOR1 = (140, 100, 50)
COLOR2 = (30, 80, 120)
JITTER = 48  # c1,c2共通でrgbに加算(ただしclipされる)
BGCOLOR = (190, 195, 190)

DEFAULT_WEIGHTS = [
    # Name,         reverse_flag,   probability
    ['half_circle', 'r2', 0.8],
    ['half_dbl',    'r',  0.1],
    ['quarter',     'r',  1.0],
    ['quad_quarter','r',  0.05],
    ['leaf',        'r2', 0.2],
    ['circle',      'r1', 0.0],
    ['dbl_circle',  'r',  0.1],
    ['quad_circle', 'r',  0.01],
    ['tri_circle',  'r',  0.02],
    ['mini_circle', 'r',  0.0],
    ['haxa_circle', 'r',  0.02],
    ['ring',        'r1', 0.1],
    ['dbl_ring',    'r1', 0.1],
    ['half_triangl','n',  1.0],
    ['dbl_triangle','r',  0.2],
    ['square',      'n',  0.0],
    ['boko',        'n',  0.4],
    ['half_box',    'n',  0.2],
    ['half_half',   'n',  0.2],
    ['bar',         'na', 0.03],
    ['mesh',        'n1', 0.2],
    ['half_stripe', 'n',  0.1],
    ['stripe',      'n2', 0.1],
    ['pinstripe',   'n2a',0.0],
    ['quarter_rings','n', 0.02],
    ['inset_square','r',  0.0],
    ['triangle',    'r',  0.0],
    ['box',         'n1', 0.05],
    ['cross',       'r1', 0.0],
    ['kamon',       'r1', 0.0],
]

OVERWRITES = {
    'dbl_ring': 'circle',
    'quarter_rings': 'quarter',
    'mesh': 'square',
    'tri_circle': 'mini_circle', 
    }

FN = {}

bauhaus_preserv = {'overwrite':True}

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'バウハウス風 (基本2色+明度加算2色)',
                       {'color1':'色1', 'color2':'色2', 'color3':'背景色',
                        'color_jitter':'明度加算',
                        'pwidth':'パターン幅'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*COLOR1)
    p.color2.itoc(*COLOR2)
    p.color3.itoc(*BGCOLOR)
    p.color_jitter = JITTER
    p.pwidth = TILE
    return p


"""
build_tile_bank_aa 内のマスクパターン関数 pattern(x, y, S) の仕様
    x, y : np.ndarray (座標グリッド)
    S    : スケール後サイズ（s * scale）

    return:
        bool配列
        True  = 塗り
        False = 地

    マスク関数内では、タイルサイズはスケール後になるので以下に注意
    - 関数内のサイズ基準はすべて S に依存する必要あり
    - 中心座標は S 基準 cx, cy = S // 2, S // 2
    
"""

def register(func):
    FN[func.__name__] = func
    return func

@register
def half_triangl(x, y, S):
    return y >= x

@register
def inset_square(x, y, S):
    h = S//4
    edge = (x<h)|(S-h<x)|(y<h)|(S-h<y)
    return (y >= x) ^ edge

@register
def dbl_triangle(x, y, S):
    h = S // 2
    top = (y <= h) & (np.abs(x - h) <= y)
    bottom = (y >= h) & (np.abs(x - h) <= (y-h))
    return top | bottom

@register
def half_circle(x, y, S):
    r = S // 2
    left  = (x - 0)**2 + (y - S//2)**2 <= r**2
    right = (x - S)**2 + (y - S//2)**2 <= r**2
    return left | right

@register
def half_dbl(x, y, S):
    r = S // 2
    top = ((x - S//2)**2 + (y - S//2)**2 <= r**2) & (y < S//2)
    bottom = (x - S//2)**2 + (y - S)**2 <= r**2
    return top | bottom

@register
def quarter(x, y, S):
    return (x**2 + y**2 <= S**2)

@register
def quarter_rings(x, y, S):
    w = S // 10
    r = np.sqrt(x**2 + y**2)

    band = (r // w).astype(int)

    return (band % 2 == 1) & (band < 10)

@register
def quad_quarter(x, y, S):
    r = S // 2
    q1 = (x-S)**2 + y**2 <= r**2
    q2 = (x-S)**2 + (y-S)**2 <= r**2
    q3 = x**2 + (y-S)**2 <= r**2
    q4 = x**2 + y**2 <= r**2
    return q1|q2|q3|q4

@register
def leaf(x, y, S):
    return (x**2 + y**2 <= S**2) & ((x-S)**2 + (y-S)**2 <= S**2)

@register
def dbl_circle(x, y, S):
    r = S // 4
    q1 = (x - S//4)**2 + (y - S//4)**2 <= r**2
    q2 = (x - S//4)**2 + (y - 3*S//4)**2 <= r**2
    return q1 | q2

@register
def quad_circle(x, y, S):
    r = S // 4
    q1 = (x - S//4)**2 + (y - S//4)**2 <= r**2
    q2 = (x - S//4)**2 + (y - 3*S//4)**2 <= r**2
    q3 = (x - 3*S//4)**2 + (y - S//4)**2 <= r**2
    q4 = (x - 3*S//4)**2 + (y - 3*S//4)**2 <= r**2
    return q1 | q2 | q3 | q4

@register
def tri_circle(x, y, S):
    r = S // 4
    q1 = (x - S//4)**2 + (y - S//4)**2 <= r**2
    q2 = (x - S//4)**2 + (y - 3*S//4)**2 <= r**2
    q3 = (x - 3*S//4)**2 + (y - S//4)**2 <= r**2
    return q1 | q2 | q3

@register
def mini_circle(x, y, S):
    r = S // 4
    q4 = (x - 3*S//4)**2 + (y - 3*S//4)**2 <= r**2
    return q4

@register
def haxa_circle(x, y, S):
    r = S // 8
    q = np.zeros((S,S), dtype=bool)
    step = S // 4
    offset = step // 2
    for c in range(15):
        cx = (c % 4) * step + offset
        cy = (c // 4) * step + offset
        q |= (x - cx)**2 + (y - cy)**2 <= r**2
    return q

@register
def circle(x, y, S):
    r = S // 2
    return ((x - r)**2 + (y - r)**2 <= r**2)

@register
def ring(x, y, S):
    cx, cy = S // 2, S // 2
    r_out = S // 2
    r_inn = S // 4
    dist = (x - cx)**2 + (y - cy)**2
    return (dist <= r_out**2) & (dist >= r_inn**2)

@register
def dbl_ring(x, y, S):
    cx, cy = S // 2, S // 2
    r_out = S // 2
    r_mid = S * 2 // 6
    r_inn = S // 6
    dist = (x - cx)**2 + (y - cy)**2
    return (dist <= r_out**2) ^ (dist <= r_mid**2) ^ (dist <= r_inn**2)

@register
def square(x, y, S):
    return (x%2 < 1)

@register
def boko(x, y, S):
    h = S // 2
    return (np.abs(x - h) >= (y-h))

@register
def half_box(x, y, S):
    return (x < S//2)

@register
def half_half(x, y, S):
    return (x < S//2)^(y < S//2)

@register
def bar(x, y, S):
    return (x < S//4)

@register
def mesh(x, y, S):
    sw = S//9
    return ((x % (2*sw)) < sw) ^ ((y % (2*sw)) < sw)

@register
def half_stripe(x, y, S):
    sw = S//8
    return ((x % (2*sw)) < sw) & (y < S//2)

@register
def stripe(x, y, S):
    sw = S//8
    return (x % (2*sw)) < sw

@register
def pinstripe(x, y, S):
    sw = S//30
    return (x % (3*sw)) < sw


@register
def triangle(x, y, S):
    width = S//5
    half = S//2
    angle = np.deg2rad(65) # np.pi/3 # 正三角形
    incl = np.sin(angle)*2 
    wh = width/np.cos(angle)  # 法線方向にwidthを取るのでy切片はcos(60)で割る
    rh = S*incl
    d = 0  # (S-rh/2)//2  # 余白マージンを取ってセンタリング
    left = (incl*x-wh+d<= y) & (y <= incl*x+d) & (x<=half) & (d<=y)
    right = (-incl*x+rh-wh+d <= y) & (y <= -incl*x+rh+d) & (half<=x) & (d<=y)
    bottom = (d<=y) & (y<=width+d) & ((width+d)/2<x) & (x<S-(width+d)/2)
    return left | right | bottom

@register
def box(x, y, S):
    width = S//4
    d = 0  # S//8 # 余白マージン
    l = (d<=x) & (x<=width+d) & (d<y) & (y<S-d)
    r = (S-d-width<=x) & (x<=S-d) & (d<y) & (y<S-d)
    b = (d<=y) & (y<=width+d) & (d<x) & (x<S-d)
    u = (S-d-width<=y) & (y<=S-d) & (d<x) & (x<S-d)
    return l|r|u|b

@register
def cross(x, y, S):
    w = S // 6
    band1 = np.abs(y - x) <= w  # 45°
    band2 = np.abs(y + x - S) <= w  # -45°
    return band1 | band2

@register
def kamon(x, y, S):
    """丸に違い鷹の羽の家紋 0: 背景, 1: 家紋
    x,yは使用しません
    """
    img = Image.new('L', (S, S), 0)
    
    c = S // 2
    margin = S // 50
    radius = c - margin
    base_width = max(2, S // 100) # 基本となる線の太さ
    
    #外枠の丸
    dr = ImageDraw.Draw(img)
    outcircle_width = max(base_width, S//10)
    dr.ellipse((c-radius, c-radius, c+radius, c+radius),
        outline=255, width=outcircle_width)

    # 羽根
    def draw_feather_mask(S, angle, outline=False):
        feather = Image.new('L', (S, S), 0)
        f_dr = ImageDraw.Draw(feather)

        cx = S//2
        cy = S*3//10
        f_radius = S//5
        f_length = f_radius*2
        ly = cy+f_length
        
        # fill body
        f_dr.pieslice((cx-f_radius, cy-f_radius, cx+f_radius, cy+f_radius),
                 start=180, end=360, fill=255)
        f_dr.pieslice((cx-f_radius, ly-f_radius, cx+f_radius, ly+f_radius),
                 start=0, end=180, fill=255)
        f_dr.rectangle((cx-f_radius, cy, cx+f_radius, ly), fill=255)
        # outline
        if outline:
            f_dr.arc((cx-f_radius, cy-f_radius, cx+f_radius, cy+f_radius),
                     start=180, end=360, fill=255, width=base_width*2)
            f_dr.arc((cx-f_radius, ly-f_radius, cx+f_radius, ly+f_radius),
                     start=0, end=180, fill=255, width=base_width*2)
            f_dr.line((cx-f_radius, cy, cx-f_radius, ly),
                      width=base_width*2, fill=255)
            f_dr.line((cx+f_radius, cy, cx+f_radius, ly),
                      width=base_width*2, fill=255)

        rotated = feather.rotate(angle, resample=Image.BICUBIC, center=(cx, cx))
        return rotated
    
    def draw_single_feather(S, angle):
        # 羽根単体
        feather = draw_feather_mask(S, 0)
        f_dr = ImageDraw.Draw(feather)
        
        cx = S//2
        cy = S*3//10
        f_radius = S//5
        f_length = f_radius*2
        ly = cy+f_length
        
        # feather line
        sy = cy - f_radius + f_radius//8
        ey = sy + S//5
        dy = f_radius//10*18
        step = S//20
        for d in range(3):
            f_dr.line((cx-f_radius, sy+d*step, cx, ey+d*step),
                      width=base_width, fill=0)
            f_dr.line((cx-f_radius, sy+dy+d*step, cx, ey+dy+d*step),
                      width=base_width, fill=0)
            f_dr.line((cx+f_radius, sy+d*step, cx, ey+d*step),
                      width=base_width, fill=0)
            f_dr.line((cx+f_radius, sy+dy+d*step, cx, ey+dy+d*step),
                      width=base_width, fill=0)
        dy = base_width*4
        f_dr.arc((cx-f_radius, ly-f_radius-dy, cx+f_radius, ly+f_radius-dy),
                 start=0, end=180, fill=0, width=base_width)
        dx = base_width*2
        f_dr.line((cx, cy-f_radius, cx, ly+f_radius),
                      width=base_width*5, fill=255)
        f_dr.line((cx-dx, cy-f_radius, cx-dx, ly+f_radius),
                      width=base_width, fill=0)
        f_dr.line((cx+dx, cy-f_radius, cx+dx, ly+f_radius),
                      width=base_width, fill=0)
        
        # rotate
        rotated = feather.rotate(angle, resample=Image.BICUBIC, center=(cx, cx))
        return rotated

    # 重ね合わせ
    feather_size = int(S*0.94)
    feather_top = draw_single_feather(feather_size, -45)
    feather_top_m = draw_feather_mask(feather_size, -45, outline=True)
    feather_bottom = draw_single_feather(feather_size, 45)

    df = (S-feather_size)//2
    img.paste(255, (df, df), feather_bottom)
    img.paste(0, (df, df), feather_top_m)
    img.paste(255, (df, df), feather_top)

    # --- 二値配列化 ---
    kamon_array = np.array(img)
    kamon_array = (kamon_array > 127).astype(np.uint8) # 閾値を中央に
    
    return kamon_array


# =========================
# AA付きマスク生成
# =========================
def aa_mask(mask_func, s, scale=4):
    S = s * scale

    y, x = np.ogrid[:S, :S]
    mask_hi = mask_func(x, y, S)

    # float化して縮小
    img = Image.fromarray((mask_hi * 255).astype(np.uint8), 'L')
    img = img.resize((s, s), Image.Resampling.LANCZOS)

    return np.asarray(img) / 255.0  # 0.0〜1.0


# =========================
# タイルパターン生成（AA）
# =========================
def build_tile_bank_aa(s):
    bank = []
    weights = []
    names = []

    def add_pattern(name, base, reverse, weight, inv_ratio=0.25):
        for k in range(4):
            if (k > 1 and '2' in reverse) \
               or (k > 0 and '1' in reverse):
                break
            rot = np.rot90(base, k)

            bank.append(rot)
            weights.append(weight)
            names.append(name)

            if  'n' in reverse:
                continue
            bank.append(1.0 - rot)
            weights.append(weight * inv_ratio)
            names.append(name + '_inv')

    if 'funcs' not in bauhaus_preserv:
        bauhaus_preserv['funcs'] = copy.deepcopy(DEFAULT_WEIGHTS)
    
    for name, rvs, w in bauhaus_preserv['funcs']:
        base = aa_mask(FN[name], s)
        add_pattern(name, base, rvs, w)
    
    weights = np.array(weights, dtype=np.float32)
    weights /= weights.sum()

    return bank, weights, names

# =========================
# 詳細設定
# =========================
def item_sw(itm):
    # Name,         func_id,    reverse_flag,   probability
    name, flag, prob = itm
    line = [
        sg.Checkbox('', default=(prob>0), key=f'en_{name}',
                    group_id='switch'),
        sg.Text(name.ljust(12), size=(12,1)),
        sg.Combo(['r','r1','r2','n','n1','n2'], default_value=flag,
                 key=f'fl_{name}', width=3),
        sg.Input(key=f'pr_{name}', default_text=f'{prob:.2f}',
                 size=(5,1)),
        ]
    return line
    


def desc(p: Param):
    s = p.pwidth

    lines = []
    for itm in bauhaus_preserv['funcs']:
        lines.append(item_sw(itm))

    inum = len(lines)
    ilist = []
    maxrow = 12
    cols = (inum+maxrow-1)//maxrow
    if cols > 4:
        cols = 4
    rows = (inum+cols-1)//cols
    for v in range(cols):  # 1かラムrow行
        clayout = [[sg.Text('Mask Name', size=(14,1)),
                     sg.Text('Flag', size=(6,1)),
                     sg.Text('Prob.', size=(6,1))],]
        for w in range(rows):
            k = v*rows + w
            if k >= inum:
                break
            clayout.append(lines[k])
            
        ilist.append(sg.Column(layout=clayout, vertical_alignment='top',
                               expand_y=True))
        #print(clayout)
        
    lo = [[sg.Text('Bauhaus風テキスタイル：タイルリスト')],
          [sg.Text(size=(4,1)),
           sg.Text('Flag:  r/n=反転パターンのenable/disable'),
           sg.Text(' 1,2=回転パターンの制限(省略時4方向)'),
           sg.Text(' a=重ね書きあり ',expand_x=True)],
          ilist,
          [sg.Button('Reset', key='-reset-', background_color='#ffffdd'),
           sg.Button('Clear', key='-clr-'),
           sg.Text(size=(3,1)),
           sg.Checkbox('重ね書き', key='-ovw-',
                       default=bauhaus_preserv['overwrite']),
           sg.Text(size=(3,1)),
           sg.Text(key='-msg-', text_color='#550000', expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button(' Done ', key='-ok-', background_color='#ddffdd'),
           ]]
    #print(lo)

    touched = False
    last_ovw = bauhaus_preserv['overwrite']
    wn = sg.Window('mod Bauhaus', layout=lo, modal=True)
    while True:
        ev, va = wn.read()
        wn['-msg-'].update('')
        #print(va)

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            break
        elif ev == '-ok-':
            if len(va['switch']) == 0:
                wn['-msg-'].update('No patterns')
                continue
            
            ll = len(bauhaus_preserv['funcs'])
            for i in range(ll):
                itm = bauhaus_preserv['funcs'][i]
                name = itm[0]
                #print(name)
                if itm[1] != va['fl_'+name]:
                    itm[1] = va['fl_'+name]
                    touched = True
                if va['en_'+name]:
                    if itm[2] != float(va['pr_'+name]):
                        itm[2] = float(va['pr_'+name])
                        touched = True
                    elif itm[2] == 0.0:
                        itm[2] = 1.0
                        touched = True
                else:
                    if itm[2] != 0.0:
                        itm[2] = 0.0
                        touched = True
            break
        elif ev == '-reset-':
            bauhaus_preserv['funcs'] = copy.deepcopy(DEFAULT_WEIGHTS)
            ll = len(bauhaus_preserv['funcs'])
            for i in range(ll):
                itm = bauhaus_preserv['funcs'][i]
                name = itm[0]
                if not 'en_'+name in va:
                    continue
                wn['en_'+name].update(True if itm[2] > 0 else False)
                wn['fl_'+name].update(value=itm[1])
                wn['pr_'+name].update(str(itm[2]) if itm[2] > 0 else '0.0')
            touched = True
            continue
        elif ev == '-clr-':
            ll = len(bauhaus_preserv['funcs'])
            for i in range(ll):
                itm = bauhaus_preserv['funcs'][i]
                name = itm[0]
                if not 'en_'+name in va:
                    continue
                wn['en_'+name].update(False)
            touched = True
            continue

        elif ev == '-ovw-':
            if va['event_type'] == 'change':
                bauhaus_preserv['overwrite'] = va['event']
            continue

    wn.close()
    if touched or last_ovw != bauhaus_preserv['overwrite']:
        bank, weights, names = build_tile_bank_aa(s)

        return generate(p)
    else:
        return


# =========================
# 描画色生成
# =========================
def pick_color(c, delta):
    if np.random.rand() < 0.5:
        base = np.array(c)
    else:
        base = np.array(c) + delta

    return np.clip(base, 0, 255).astype(np.uint8)

# =========================
# パターン生成（RGBA）
# =========================
def generate_pattern(w, h, s, c1, c2, delta):
    grid_w = (w + s*2 - 1) // s + 1
    grid_h = (h + s*2 - 1) // s + 1

    W = grid_w * s
    H = grid_h * s

    img = np.zeros((H, W, 4), dtype=np.uint8)

    bank, weights, names = build_tile_bank_aa(s)
    endur = len(bank) // 2

    for gy in range(grid_h):
        for gx in range(grid_w):
            pname = ''
            prgb = (0,0,0)
            for _ in range(endur):
                idx = np.random.choice(len(bank), p=weights)
                alpha = bank[idx]

                base = c1 if np.random.rand() < 0.5 else c2
                r, g, b = pick_color(base, delta)
                if pname != names[idx] and prgb != (r,g,b):
                    break
                pname = names[idx]
                prgb = (r,g,b)
            
            y0 = gy * s
            x0 = gx * s

            sub = img[y0:y0+s, x0:x0+s]

            a = (alpha * 255).astype(np.uint8)

            sub[..., 0] = r
            sub[..., 1] = g
            sub[..., 2] = b
            sub[..., 3] = a

            if not bauhaus_preserv['overwrite']:
                continue
            if names[idx] in OVERWRITES  and np.random.rand() < 0.5:
                overlay_random_pattern(sub, bank, weights, names, c1, c2,
                                       delta, base, idx=idx)
                continue
            itm = next((item for item in bauhaus_preserv['funcs'] \
                        if item[0] == names[idx]),None)
            if itm is not None:
                if 'a' in itm[1]:
                    overlay_random_pattern(sub, bank, weights, names,
                                           c1, c2, delta, base)
                continue

    return img

# =========================
# セルへの重ね書き
# =========================
def overlay_random_pattern(sub, bank, weights, names, c1, c2, delta,
                           c3, idx=None):
    """同じセル(sub)にランダムなパターンを1回重ね書きする"""

    # 別のパターンを選ぶ
    if not idx is None:
        name = names[idx]
        base = [i for i, v in enumerate(names) if v == name]
        no = base.index(idx)
        target = [i for i, v in enumerate(names) if v == OVERWRITES[name]]
        if target is None or len(target) < 1:
            idx2 = None
        else:
            idx2 = target[min(no, len(target)-1)]
    if idx is None or idx2 is None:        
        idx2 = np.random.choice(len(bank), p=weights)
    alpha2 = bank[idx2]

    # ランダム色
    base2 = c2 if c3 == c1 else c1
    # base2 = c1 if np.random.rand() < 0.5 else c2
    r2, g2, b2 = pick_color(base2, delta)

    # アルファ
    a2 = (alpha2 * 255).astype(np.uint8)

    mask = (sub[..., 3] < 127)   # 背景が透明な部分だけ True

    sub[mask, 0] = r2
    sub[mask, 1] = g2
    sub[mask, 2] = b2
    sub[mask, 3] = a2[mask]


    return

# =========================
# crop
# =========================
def center_crop(img, w, h):
    H, W = img.shape[:2]
    x0 = (W - w) // 2
    y0 = (H - h) // 2
    return img[y0:y0+h, x0:x0+w]

# =========================
# 生成
# =========================
def generate(p: Param):
    w, h = p.width, p.height
    c1 = p.color1.ctoi()
    c2 = p.color2.ctoi()
    bgcolor = p.color3.ctoi()
    delta = p.color_jitter
    s = p.pwidth

    # パターン生成（RGBA）
    pattern_big = generate_pattern(w, h, s, c1, c2, delta)
    fg1 = Image.fromarray(pattern_big, 'RGBA')
    print(f'big: {fg1.size}')
    
    pattern = center_crop(pattern_big, w, h)
    fg = Image.fromarray(pattern, 'RGBA')
    print(f'norm: {fg.size}')

    # 背景（RGB）
    if p.h_img is not None:
        bg = p.bg(w, h)
    else:
        bg = Image.new('RGB', (w, h), bgcolor)

    # α付きで貼り付け
    bg.paste(fg, (0, 0), fg)
    return bg


# =========================
# テスト
# =========================
if __name__ == '__main__':
    p = Param()
    p = default_param(p)

    p.width, p.height = WIDTH, HEIGHT
    im = generate(p)

    im.show()
