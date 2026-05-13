import numpy as np
from PIL import Image
import inspect
from wall_common import *
import TkEasyGUI as sg

COLOR1 = '#EFEF9C'
COLOR2 = '#FFA684'
COLOR3 = '#EFEF9C'
RADIUS = 20
DISTANCE = 120
QUALITY = 2

LATTICES=['TRIANGULAR','SQUARE','DIAGONAL','ISOMETRIC',
          ]
LATRATIO = [(1, np.sqrt(3)/2, 0.5),  # Triangular h-space, v-space, phase-shift
            (1, 1, 0),
            (np.sqrt(2), np.sqrt(2)/2, 0.5),
            (np.sqrt(3), 0.5, 0.5),
            ]

GRADBIAS = ['NOGRAD', 'VERTICAL', 'HORIZONTAL', 'DIAGONAL', 'RADIAL']

polkadot_preserv = {'shape': None,
                    'lattice': 2,  # DIAGONAL
                    'gradation': 0,  # NOGRAD
                    'funcs': None,
                    'arglists': None,
                    'prevsets': {},
                    }
AASCALE=4

# =========================
# 形状登録デコレータ
# =========================
FN = {}  # 関数名
DF = {}  # パラメータ名及びデフォルト値

def regi(func):
    """
    関数の引数名を抽出して FN 辞書に登録するデコレータ
    """
    # inspectで引数名の一覧を取得（selfなどは除外される）
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # 1つ目(p)を除外
    params = params[1:]

    FN[func.__name__] = func
    DF[func.__name__] = {
        p.name: p.default
        for p in params
        if p.default is not inspect._empty
    }

    return func


# ==== プラグインAPI =====================================================
# =========================
# module基本情報
# =========================
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '水玉など',
                       {'color1':'背景色',
                        'color2':'前景色',
                        'color3':'前景グラデ',
                        'pwidth':'ドット径',
                        'pheight':'格子間隔',
                        'pdepth':'品質(1..4)',
                        })
    return module_name

# =========================
# おすすめパラメータ
# =========================
def default_param(p: Param):
    p.color1 = RGBColor(COLOR1)
    p.color2 = RGBColor(COLOR2)
    p.color3 = RGBColor(COLOR3)
    p.pwidth = RADIUS
    p.pheight = DISTANCE
    p.pdepth = QUALITY
    return p

# =========================
# 詳細設定
# =========================
def confline(shape, current):
    args = DF[shape].keys()
    defaults = DF[shape]
    if shape in polkadot_preserv['prevsets']:
        prevsets = polkadot_preserv['prevsets'][shape]
    else:
        prevsets = DF[shape]
   
    line = [sg.Radio('', group_id='radio', key=shape,
                     default=True if shape == current else False),
            sg.Text(shape, size=(12,1))]
    for a in args:
        line.append(sg.Text(f' {a}'))
        if a in prevsets:
            value = prevsets[a]
        elif a in defaults:
            value = defaults[a]
        else:
            value = ''
        line.append(sg.Input(f'{value}', key=f'-{shape}_{a}-', width=4,))

    return line

def desc(p: Param):
    lat = clip(polkadot_preserv['lattice'], 0, len(LATTICES)-1)
    gra = clip(polkadot_preserv['gradation'], 0, len(GRADBIAS)-1)
   
    layout = [[sg.Text('[POLKADOT configure]   Lattice Type:'),
               sg.Combo(LATTICES,
                        default_value=LATTICES[lat],
                        key='-lattice-', readonly=True),
               sg.Text('Gradation:'),
               sg.Combo(GRADBIAS,
                        default_value=GRADBIAS[gra],
                        key='-gradation-', readonly=True),              
               ]]
    curshape = polkadot_preserv['shape']
    for fn in polkadot_preserv['funcs']:
        layout.append(confline(fn, curshape))
    layout.append([sg.Text('', size=(2,1)),
                   sg.Button('Default',key='-rst-',background_color='#ffffdd'),
                   sg.Text('', expand_x=True),
                   sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
                   sg.Button(' Done ', key='-ok-', background_color='#ddffdd'),
                   ])
    wn = sg.Window('Configure', layout=layout, modal=True)

    while True:
        ev, va = wn.read()
        #print(ev, va)

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            change = False
            break
        elif ev == '-rst-':
            shape = va['radio']
            prevsets = DF[shape]
            for a in prevsets.keys():
                wn[f'-{shape}_{a}-'].update(prevsets[a])
        elif ev == '-ok-':
            change = True
            lname = va['-lattice-']
            polkadot_preserv['lattice'] = LATTICES.index(lname)
            gname = va['-gradation-']
            polkadot_preserv['gradation'] = GRADBIAS.index(gname)
            shape = va['radio']
            args = {}
            for a in DF[shape].keys():
                args[a] = int(va[f'-{shape}_{a}-'])
            break

    wn.close()

    if change:
        polkadot_preserv['shape'] = shape
        polkadot_preserv['prevsets'][shape] = args
        new_img = generate(p)
        return new_img
    else:
        return
                   

# ==== ドット形状関数 =====================================================
# anydot(p,*, <name>=<default>, ...) -> mask: nparray, factor: nparray|None
#  <name>=<default> 拡張設定画面の設定可能変数となる
#  mask   ドットの形状のアルファチャネル
#  factor ドット毎の陰影など
#  色要素は _dot() では持たず、polkadot() の方で付与する

# =========================
# 円パッチ
# =========================
@regi
def disc(p: Param, *, shade=0, angle=215, shift=40):
    shade = prevset('shade', shade, lo=0, hi=100)
    angle = prevset('angle', angle)
    shift = prevset('shift', shift) / 100.0

    R = get_R(p)
    x, y = make_ogrid(R)

    # 円マスク（高解像度）
    dist_center = np.sqrt(x**2 + y**2)
    mask = (dist_center <= R).astype(np.float32)

    lum = luminance(x, y, R, shade, angle, shift)
   
    return finalize_patch(mask, factor=lum)

# =========================
# 六角ドット
# =========================
@regi
def hexnut(p: Param, *, inner_r=40, shade=15, angle=215, shift=45):
    inner_r = prevset('inner_r', inner_r, lo=0, hi=99) / 100.0
    shade = prevset('shade', shade, lo=0, hi=100)
    angle = prevset('angle', angle)
    shift = prevset('shift', shift) / 100.0

    R = get_R(p)
    x, y = make_ogrid(R)

    # --- 六角形マスク ---
    inner = R * inner_r
    ax = np.abs(x)
    ay = np.abs(y)
   
    cond1 = ax <= R
    cond2 = ay <= (np.sqrt(3)/2) * R
    cond3 = ax + ay / np.sqrt(3) <= R
    cond4 = (x**2+y**2) <= inner**2
    mask = ((cond1 & cond2 & cond3) & (~cond4)).astype(np.float32)

    lum = luminance(x, y, R, shade, angle, shift)
   
    return finalize_patch(mask, factor=lum)

# =========================
# アスタリスク系星型
# =========================
@regi
def spike(p: Param, *, spikes=6, inner_r=40):
    spikes = prevset('spikes', spikes, lo=3, hi=255)
    inner_r = prevset('inner_r', inner_r, lo=0, hi=99) / 100.0

    R = get_R(p)
    x, y = make_ogrid(R)

    # --- 極座標 ---
    theta = np.arctan2(y, x)
    dist  = np.sqrt(x**2 + y**2)

    star_r = R * (inner_r + (1-inner_r) * (0.5 + 0.5*np.cos(spikes * theta)))

    # --- マスク ---
    mask = (dist <= star_r).astype(np.float32)

    return finalize_patch(mask)


# =========================
# 多角形系星型
# =========================
@regi
def star(p: Param, *, spikes=5, shade=0, angle=215, shift=40):
    spikes = prevset('spikes', spikes, lo=4, hi=255)
    shade = prevset('shade', shade, lo=0, hi=100)
    angle = prevset('angle', angle)
    shift = prevset('shift', shift) / 100.0

    R = get_R(p)
    x, y = make_ogrid(R)

    # --- 頂点生成 ---
    inner_ratio = 0.38  # 五芒星っぽさのキモ

    angles = np.linspace(0, 2*np.pi, spikes*2, endpoint=False)
    radii = np.empty(spikes*2)
    radii[0::2] = R
    radii[1::2] = R * inner_ratio

    vx = radii * np.cos(angles)
    vy = radii * np.sin(angles)

    verts = np.stack([vx, vy], axis=1)

    # --- ポリゴン内判定（ベクトル化 ray casting） ---
    # 参考：even-odd rule
    px = x[..., None]
    py = y[..., None]

    x1 = verts[:, 0]
    y1 = verts[:, 1]
    x2 = np.roll(x1, -1)
    y2 = np.roll(y1, -1)

    cond = ((y1 > py) != (y2 > py)) & \
           (px < (x2 - x1) * (py - y1) / (y2 - y1 + 1e-6) + x1)

    mask = np.sum(cond, axis=-1) % 2
    mask = mask.astype(np.float32)
    lum = luminance(x, y, R, shade, angle, shift)

    return finalize_patch(mask, factor=lum)

# =========================
# 雪の結晶
# =========================
@regi
def snowflake(p: Param, *, bthick=50, blength=50, btaper=70):
    bthick = prevset('bthick', bthick) / 100.0
    blength = prevset('blength', blength) / 100.0
    btaper = prevset('btaper', btaper) / 100.0

    R = get_R(p)
    x, y = make_ogrid(R)

    # --- 距離関数（線への距離） ---
    def line_dist(px, py, angle):
        dx = np.cos(angle)
        dy = np.sin(angle)
        return np.abs(px * dy - py * dx)

    mask = np.zeros_like(x, dtype=np.float32)

    branches = 6
    main_len = R
    thickness = R * 0.08
    bt = thickness * bthick

    for i in range(branches):
        ang = i * np.pi / 3

        # --- 主枝 ---
        d_line = line_dist(x, y, ang)
        along = x * np.cos(ang) + y * np.sin(ang)

        main = (d_line < thickness) & (along > 0) & (along < main_len)
        mask = np.maximum(mask, main.astype(np.float32))

        # --- 分岐 ---
        for t in [0.4, 0.6, 0.8]:
            bx = np.cos(ang) * main_len * t
            by = np.sin(ang) * main_len * t
            bl = main_len * blength * (1 - t*btaper)

            for side in [-1, 1]:
                ang2 = ang + side * np.pi / 3

                dx2 = x - bx
                dy2 = y - by

                d_line2 = line_dist(dx2, dy2, ang2)
                along2 = dx2 * np.cos(ang2) + dy2 * np.sin(ang2)

                branch = (d_line2 < bt) & (along2 > 0) & (along2 < bl)

                mask = np.maximum(mask, branch.astype(np.float32))

    # --- 軽くぼかし（AA代わり） ---
    mask = np.clip(mask * 1.5, 0, 1)

    return finalize_patch(mask)


# =========================
# クローバー
# =========================
@regi
def clover(p: Param, *, rotate=20, swirl=30):
    rotate = prevset('rotate', rotate)
    swirl = prevset('swirl', swirl, lo=0, hi=100)

    R = get_R(p)
    x, y = make_coordgrid(R)

    # --- 正規化 ---
    xn = x / R
    yn = y / R

    rot = np.deg2rad(rotate)
    c = np.cos(rot)
    s = np.sin(rot)

    xr = xn * c + yn * s
    yr = -xn * s + yn * c
    xn, yn = xr, yr

    # --- 極座標 ---
    theta = np.arctan2(yn, xn)
    radius = np.sqrt(xn**2 + yn**2)

    # --- 回転関数 ---
    def rotate(px, py, ang):
        c = np.cos(ang)
        s = np.sin(ang)
        return px*c - py*s, px*s + py*c

    d = 0.8  # 葉の位置（重要）

    mask = np.zeros_like(xn, dtype=bool)

    for ang in [0, np.pi/2, np.pi, 3*np.pi/2]:
        xr, yr = rotate(xn, yn, ang)
        theta = np.arctan2(yr - d, xr)
        radius = np.sqrt(xr**2 + (yr - d)**2)
        heart_r = 0.32 * (1 - np.sin(theta))
        m = radius <= heart_r
        mask |= m

    center = (xn**2 + yn**2 < 0.4**2)
    mask = mask | center
    mask = mask.astype(np.float32)

    if swirl > 0:
        texture = swirl_marble(R, contrast=swirl/300)
    else:
        texture = None
    
    return finalize_patch(mask, factor=texture)


# =========================
# 渦巻 (may be orange as DC, red as Bakabon)
# =========================
@regi
def whirl(p: Param, *, tight=38, thick=28, start=90):
    tight = prevset('tight', tight)
    dir = 1 if tight >= 0 else -1  # tight>0 CW, tight<0 CCW
    tight = abs(tight)
    thick = prevset('thick', thick)
    start = np.deg2rad(prevset('start', start)%360)

    R = get_R(p)
    X, Y = make_uvgrid(R)

    rad = np.sqrt(X**2+Y**2)
    phi = np.arctan2(Y,X)
   
    freq = 4 + tight*0.4
    #spiral = np.sin(phi+rad*freq)
   
    phase = (start + phi - dir*rad*freq) % (2*np.pi)
    mask = phase < thick * 0.1

    mask[rad < 0.10] = 0
    mask[rad > 0.95] = 0

    return finalize_patch(mask)


# =========================
# 絣模様 (PIL系)
# =========================
@regi
def sharp(p: Param, *, lean=5, pitch=40, arc=18):
    lean = prevset('lean', lean)%360  # ドットの傾き
    pitch = prevset('pitch', pitch)  # 線の間隔
    thick=5  # 線幅は固定に
    arcthick = prevset('arc', arc)/10.0 + 1.0  # 縦線円弧のBBOX幅
    sang, eang = 106, 268  # 円弧の開始・終点角

    R = get_R(p)
    size, img = make_canvas(R)
    
    drw = ImageDraw.Draw(img)

    pitch = size*pitch/100
    pen = max((size*thick)//50,4)
    arcthick = max(pen*arcthick, 10)
    e = arcthick // 4
    sx = clip((size-pitch-arcthick/2)//2,0,size)
    sy = clip((size-pitch)//2,0,size)

    for d in (0,1):
        drw.arc((sx, 0, sx+arcthick, size), sang, eang, fill=255, width=pen)
        drw.line((e, sy, size-e, sy), fill=255, width=pen)
        sx += pitch
        sy += pitch
    img = img.rotate(-lean, resample=Image.BILINEAR, expand=False)
   
    return finalize_patch(img)


# ==== サポート関数 =====================================================
# =========================
# 保存パラメータがあれば返す
# =========================
def prevset(name, value, lo=None, hi=None):
    shape = polkadot_preserv['shape']
    retv = (
        polkadot_preserv['prevsets']
        .get(shape,{})
        .get(name, value)
        )
    
    if lo is not None:
        retv = max(lo, retv)
    if hi is not None:
        retv = min(retv, hi)
    
    return retv

def set_default(shape, arg, value):
    global DF
    DF[shape][arg] = value


# =========================
# グリッド生成
# =========================
def get_R(p: Param, scale=AASCALE):
    gs = p.pdepth  # global scale
    r = p.pwidth * gs

    return r * scale

    
def make_ogrid(R):
    """R:サイズ -> x, y: Broadcast用配列 [2R+1,1],[1,2R+1]"""
    y, x = np.ogrid[-R:R+1, -R:R+1]
   
    return x, y  # ブロードキャスト処理の前提

def make_uvgrid(R):
    """R:サイズ -> X, Y: メッシュ配列 値域は正規化(-1..1)"""
    u = np.linspace(-1, 1, 2*R+1, dtype=np.float32)
    Y, X = np.meshgrid(u, u, indexing='ij')
   
    return X, Y  # 数式で表せる図形向き

def make_coordgrid(R):
    """R:サイズ -> X, Y:  メッシュ配列 値域は座標値(-R .. R+1)"""
    coords = np.arange(-R, R+1)
    y, x = np.meshgrid(coords, coords, indexing='ij')

    return x, y  # ピクセル位置を利用した計算向き

def make_canvas(R):
    """PILで作る方が早いdot向け
       finalize には numpy配列 の代わりに img を渡す"""
    size = 2 * R
    img = Image.new('L', (size,size), 0)

    return size, img

# =========================
# factor(scalar) ドット毎グラデーション(明度)
# =========================
def luminance(x, y, R, shade, angle, shift):
    """shade : 0..100, angle : 0..359, shift : 0..100"""
    if shade == 0:
        return None
   
    # --- グラデーション ---
    angle = np.deg2rad(angle)
    dx = np.sin(angle) * shift * R
    dy = np.cos(angle) * shift * R

    dist2 = (x - dx)**2 + (y - dy)**2
    grad = 1 - dist2 / R**2
    grad = np.clip(grad, 0, 1)

    s = shade/100.0
    lum = (1-s) + s*grad

    return lum.astype(np.float32)

def swirl_marble(R,
                 freq=10,
                 swirl=6,
                 wobble=0.25,
                 contrast=0.22,
                 rgb=False):

    X, Y = make_uvgrid(R)

    rad = np.sqrt(X*X + Y*Y)
    phi = np.arctan2(Y, X)

    # 流れ方向を歪ませる
    flow = (
        rad * freq
        + phi * swirl
        + wobble * np.sin(phi * 5 + rad * 8)
    )

    base = (
        1.0
        + contrast * np.sin(flow)
    ).astype(np.float32)

    if rgb:

        factor = np.dstack([
            base * 0.92,
            base * 1.00,
            base * 1.08,
        ]).astype(np.float32)

        factor = np.clip(factor, 0, 1)

    else:
        factor = np.clip(base, 0, 1)

    return factor


# =========================
# アンチエイリアス(SSAA)仕上
# =========================
def finalize_patch(mask, factor=None, scale=AASCALE):
    """mask: shape, factor: shade/texture """
    if type(mask) == Image.Image:
        mask = np.array(mask, dtype=np.float32) / 255.0  # numpy配列化

    H, W = mask.shape
    h = H // scale
    w = W // scale

    mask  = mask[:h*scale, :w*scale]
    mask  = mask.reshape(h, scale, w, scale).mean(axis=(1, 3))
   
    if factor is not None:
        factor = factor[:h*scale, :w*scale]
        factor = factor.reshape(h, scale, w, scale).mean(axis=(1, 3))
        if factor.ndim == 3:
            factor *= mask[...,None]
        else:
            factor *= mask

    return mask, factor    


# =========================
# クリップ(int)
# =========================
def clip(v, minimum, maximum):
    return int(min(max(v,minimum),maximum))


# =========================
# パッチ配置
# =========================
def clip_box(x0, y0, pw, ph, W, H):
    x1 = x0 + pw
    y1 = y0 + ph

    # patch側
    px0 = max(0, -x0)
    py0 = max(0, -y0)

    px1 = min(pw, W - x0)
    py1 = min(ph, H - y0)

    # 完全画面外
    if px0 >= px1 or py0 >= py1:
        return None

    # image側
    ix0 = max(0, x0)
    iy0 = max(0, y0)

    ix1 = ix0 + (px1 - px0)
    iy1 = iy0 + (py1 - py0)

    return (px0, py0, px1, py1,  # patch bbox
            ix0, iy0, ix1, iy1)  # image bbox


# ==== メイン処理 =====================================================
# =========================
# 格子配置
# =========================
def polkadot(param: Param):
    scale = clip(param.pdepth, 1, 4)
    r = param.pwidth * scale  # パッチ基本サイズ
    v = param.pheight * scale  # 格子点間の距離
    w, h = param.width * scale, param.height * scale  # 画像サイズ
    lattice = polkadot_preserv['lattice']  # 格子タイプ
    gradbias = polkadot_preserv['gradation']  # グラデーションタイプ

    c2 = np.array(param.color2.ctoi(), dtype=np.float32)  # 前景色(パッチ基本色)
    c3 = np.array(param.color3.ctoi(), dtype=np.float32)  # 前景色グラデ

    W = w + 4*r
    H = h + 4*r
    XL = max(W,H)/2
    XL2 = XL*XL
   
    img = np.zeros((H, W, 3), dtype=np.float32)
    alpha = np.zeros((H, W), dtype=np.float32)

    shape = polkadot_preserv['shape']
    if shape in polkadot_preserv['funcs']:
        mask, factor = FN[shape](param)
    else:
        mask, factor = circle_dot(param)
    ps_y, ps_x = mask.shape
    hf_y, hf_x = ps_y//2, ps_x//2
    is_factor_rgb = (factor is not None and factor.ndim == 3)

    lattice = clip(lattice, 0, len(LATTICES)-1)
    dy = v * LATRATIO[lattice][1]
    v = v * LATRATIO[lattice][0]  # 順番大事
    sf = v * LATRATIO[lattice][2]
   
    n_rows = int(H / dy) + 2
    n_cols = int(W / v) + 2

    t=0  # no gradation or fallback

    cx_base = np.arange(n_cols) * v
    cx_even = cx_base.astype(np.int32)
    cx_odd  = (cx_base + sf).astype(np.int32)

    cy_rows = (np.arange(n_rows) * dy).astype(np.int32)
 
    for j, cy in enumerate(cy_rows):
        cx_row = cx_odd if (j & 1) else cx_even
        
        if gradbias == 1:  # vertical
            t = cy/H
        elif gradbias == 4:  # radial
            ty = cy - H/2
            ty2 = ty*ty

        for i in range(n_cols):
            cx = cx_row[i]

            if gradbias == 2:  # horizontal
                t = cx/W
            elif gradbias == 3:  # diagonal
                t = (cx+cy)/(W+H)
            elif gradbias == 4:  # radial
                tx = cx - W/2
                t = (tx*tx+ty2)/XL2
            t = np.clip(t, 0, 1)
            
            color = (c2*(1-t) + c3*t).astype(np.float32)

            # --- 貼り付け位置（パッチ基準） ---
            y0, x0 = cy - hf_y, cx - hf_x
            y1, x1 = y0 + ps_y, x0 + ps_x

            # --- クリッピング ---
            clipped = clip_box(x0, y0, ps_x, ps_y, W, H)

            if clipped is None:
                continue

            px0, py0, px1, py1, ix0, iy0, ix1, iy1 = clipped

            # 切り出し
            sub_mask  = mask[py0:py1, px0:px1]
            sub_img   = img[iy0:iy1, ix0:ix1]
            sub_alpha = alpha[iy0:iy1, ix0:ix1]

            sub_patch = color
            #sub_patch = color.copy()  # 安全寄り

            if factor is not None:
                sub_factor = factor[py0:py1, px0:px1]
                sub_patch = sub_patch * (sub_factor if is_factor_rgb
                                         else sub_factor[..., None]) 

            mask3 = sub_mask[..., None]
            sub_img[:] = sub_img * (1 - mask3) + sub_patch * mask3
            sub_alpha[:] = (sub_alpha + sub_mask*(1 - sub_alpha))

    img = np.clip(img, 0, 255).astype(np.uint8)
    alpha = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    rgba = np.dstack([img, alpha])

    return Image.fromarray(rgba[r*2:r*2+h, r*2:r*2+w], mode='RGBA')


# =========================
# 基本画像生成
# =========================
def generate(p):
    if polkadot_preserv['funcs'] is None:
        polkadot_preserv['funcs'] = list(FN.keys())
        polkadot_preserv['arglists'] = {
            k : list(DF[k].keys())
            for k in polkadot_preserv['funcs']
            }

    if polkadot_preserv['shape'] is None:
        polkadot_preserv['shape'] = polkadot_preserv['funcs'][0]
    shape = polkadot_preserv['shape']

    scale = clip(p.pdepth, 1, 4)
    W = p.width * scale
    H = p.height * scale
    dot_img = polkadot(p)
   
    if p.h_img is not None:
        bg = p.bg(W, H).convert('RGBA')
    else:
        bg = Image.new('RGBA',(W, H),(*p.color1.ctoi(), 255))

    out = Image.alpha_composite(bg, dot_img)
    return out.resize((p.width, p.height), Image.LANCZOS)


# =========================
# テスト実行
# =========================
if __name__ == '__main__':
    p = Param()
    p = default_param(p)

    p.width= 1920
    p.height = 1080

    im = generate(p)
    im.show()
