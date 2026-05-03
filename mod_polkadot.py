import numpy as np
from PIL import Image
import inspect
from wall_common import *
import TkEasyGUI as sg

COLOR1 = '#94867B'
COLOR2 = '#E7CBAD'
RADIUS = 20
DISTANCE = 120
QUALITY = 2

TRIANGULAR = 0
SQUARE = 1

polkadot_preserv = {'shape': None,
                    'lattice': TRIANGULAR,
                    'funcs': None,
                    'arglists': None,
                    'args': {}
                    }
STANDARD_ARGS = {} # 'shade':0, 'angle':215, 'shift':40}

FN = {}  # 関数名
AG = {}  # 引数名
DF = {}  # デフォルト値

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
    AG[func.__name__] = [p.name for p in params]
    DF[func.__name__] = {
        p.name: p.default
        for p in params
        if p.default is not inspect._empty
    }

    return func

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '水玉など',
                       {'color1':'背景色',
                        'color2':'前景色',
                        'pwidth':'ドット径',
                        'pheight':'格子間隔',
                        'pdepth':'品質(1..4)',
                        })
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1 = RGBColor(COLOR1)
    p.color2 = RGBColor(COLOR2)
    p.pwidth = RADIUS
    p.pheight = DISTANCE
    p.pdepth = QUALITY
    return p

# =========================
# 詳細設定
# =========================
def confline(shape, current):
    args = AG[shape]
    defaults = DF[shape]
    
    line = [sg.Radio('', group_id='radio', key=shape,
                     default=True if shape == current else False),
            sg.Text(shape, size=(12,1))]
    for a in args:
        line.append(sg.Text(f' {a}'))
        if a in polkadot_preserv['args']:
            value = polkadot_preserv['args'][a]
        elif a in STANDARD_ARGS:
            value = STANDARD_ARGS[a]
        elif a in defaults:
            value = defaults[a]
        else:
            value = ''
        line.append(sg.Input(f'{value}', key=f'-{shape}_{a}-', width=4,))

    return line

def desc(p: Param):
    lat = 'TRIANGULAR' if polkadot_preserv['lattice'] == TRIANGULAR \
          else 'SQUARE'
    layout = [[sg.Text('[POLKADOT configure]   Lattice Type:'),
               sg.Combo(['TRIANGULAR','SQUARE'],
                        default_value=lat,
                        key='-lattice-'),
               ]]
    curshape = polkadot_preserv['shape']
    for fn in polkadot_preserv['funcs']:
        layout.append(confline(fn, curshape))
    layout.append([sg.Text('', expand_x=True),
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
        elif ev == '-ok-':
            change = True
            if va['-lattice-'] == 'TRIANGULAR':
                polkadot_preserv['lattice'] = TRIANGULAR
            else:
                polkadot_preserv['lattice'] = SQUARE
            shape = va['radio']
            args = {}
            for a in AG[shape]:
                args[a] = int(va[f'-{shape}_{a}-'])
            break

    wn.close()

    if change:
        polkadot_preserv['args'] = args
        polkadot_preserv['shape'] = shape
        new_img = generate(p)
        return new_img
    else:
        return
                   

# =========================
# 保存パラメータがあれば返す
# =========================
def check_preservarg(name, value):
    if name in polkadot_preserv['args']:
        return polkadot_preserv['args'][name]
    else:
        return value

# =========================
# グラデーション
# =========================
def add_gradation(x, y, R, color, shade, angle, shift):
    """ shade : 0..255
        angle : 度
        shift : ％
    """
    # --- グラデーション ---
    angle = np.deg2rad(angle)
    dx = np.sin(angle) * shift * R
    dy = np.cos(angle) * shift * R

    dist_grad = np.sqrt((x - dx)**2 + (y - dy)**2)

    size = max(max(*x.shape),max(*y.shape))   
    patch = np.zeros((size, size, 3), dtype=np.float32)
    
    if shade > 0:
        grad = 1 - (dist_grad / R)
        grad = np.clip(grad, 0, 1)
        for k in range(3):
            patch[..., k] = (color[k] - shade) + shade * grad
    else:
        patch[:] = color

    return patch

def clip(v, minimum, maximum):
    return int(min(max(v,minimum),maximum))

# =========================
# 円パッチ生成（AA + グラデーション + 中心ずらし）
# =========================
@regi
def circle_dot(p: Param, *, shade=0, angle=215, shift=40):
    c2 = p.color2.ctoi()
    gs = p.pdepth  # global scale
    r = p.pwidth * gs
    shade = np.clip(check_preservarg('shade', shade),0,255)
    angle = check_preservarg('angle', angle)
    shift = check_preservarg('shift', shift) / 100.0

    scale=4
    R = r * scale
    size = 2 * R + 1

    y, x = np.ogrid[-R:R+1, -R:R+1]

    # 円マスク（高解像度）
    dist_center = np.sqrt(x**2 + y**2)
    mask = (dist_center <= R).astype(np.float32)

    patch = add_gradation(x, y, R, c2, shade, angle, shift)
    patch *= mask[..., None]

    # ---- SSAA ダウンサンプリング ----
    h = size // scale
    w = size // scale

    patch = patch[:h*scale, :w*scale]
    mask  = mask[:h*scale, :w*scale]

    patch = patch.reshape(h, scale, w, scale, 3).mean(axis=(1, 3))
    mask  = mask.reshape(h, scale, w, scale).mean(axis=(1, 3))
    
    eps = 1e-6
    mask_safe = np.maximum(mask, eps)
    patch = patch / mask_safe[..., None]
    patch[mask <= eps] = 0

    return patch, mask

# =========================
# 六角ドット
# =========================
@regi
def hex_dot(p: Param, *, inner_r=40, shade=0, angle=215, shift=40):
    c2 = p.color2.ctoi()
    gs = p.pdepth  # global scale
    r = p.pwidth * gs

    inner_r = clip(check_preservarg('inner_r', inner_r), 0, 99) / 100.0
    shade = clip(check_preservarg('shade', shade),0,255)
    angle = check_preservarg('angle', angle)
    shift = check_preservarg('shift', shift) / 100.0
    
    scale=4
    R = r * scale
    size = 2 * R + 1
    inner = R * inner_r

    y, x = np.ogrid[-R:R+1, -R:R+1]

    # --- 六角形マスク ---
    ax = np.abs(x)
    ay = np.abs(y)
    
    cond1 = ax <= R
    cond2 = ay <= (np.sqrt(3)/2) * R
    cond3 = ax + ay / np.sqrt(3) <= R
    cond4 = (x**2+y**2) <= inner**2
    mask = ((cond1 & cond2 & cond3) & (~cond4)).astype(np.float32)

    patch = add_gradation(x, y, R, c2, shade, angle, shift)
    patch *= mask[..., None]

    # --- SSAA ---
    h = size // scale
    w = size // scale

    patch = patch[:h*scale, :w*scale]
    mask  = mask[:h*scale, :w*scale]

    patch = patch.reshape(h, scale, w, scale, 3).mean(axis=(1, 3))
    mask  = mask.reshape(h, scale, w, scale).mean(axis=(1, 3))

    return patch, mask

# =========================
# アスタリスクパッチ
# =========================
@regi
def spike_dot(p: Param, *, spikes=6, inner_r=40, shade=0, angle=215, shift=40):
    c2 = p.color2.ctoi()
    gs = p.pdepth  # global scale
    r = p.pwidth * gs

    shade = clip(check_preservarg('shade', shade),0,255)
    angle = check_preservarg('angle', angle)
    shift = check_preservarg('shift', shift) / 100.0

    # --- 星形半径 ---
    spikes = clip(check_preservarg('spikes', spikes),3,255)
    inner_r = clip(check_preservarg('inner_r', inner_r), 0, 99) / 100.0

    scale = 4
    R = r * scale
    size = 2 * R + 1

    y, x = np.ogrid[-R:R+1, -R:R+1]

    # --- 極座標 ---
    theta = np.arctan2(y, x)
    dist  = np.sqrt(x**2 + y**2)

    star_r = R * (inner_r + (1-inner_r) * (0.5 + 0.5*np.cos(spikes * theta)))

    # --- マスク ---
    mask = (dist <= star_r).astype(np.float32)

    patch = add_gradation(x, y, R, c2, shade, angle, shift)
    patch *= mask[..., None]

    # --- SSAA ---
    h = size // scale
    w = size // scale

    patch = patch[:h*scale, :w*scale]
    mask  = mask[:h*scale, :w*scale]

    patch = patch.reshape(h, scale, w, scale, 3).mean(axis=(1, 3))
    mask  = mask.reshape(h, scale, w, scale).mean(axis=(1, 3))

    return patch, mask

# =========================
# 五芒星パッチ
# =========================
@regi
def pentastar_dot(p: Param, *, spikes=5, shade=0, angle=215, shift=40):
    c2 = p.color2.ctoi()
    gs = p.pdepth  # global scale
    r = p.pwidth * gs

    spikes = clip(check_preservarg('spikes', spikes),5,255)
    shade = clip(check_preservarg('shade', shade),0,255)
    angle = check_preservarg('angle', angle)
    shift = check_preservarg('shift', shift) / 100.0

    scale = 4
    R = r * scale
    size = 2 * R + 1

    y, x = np.ogrid[-R:R+1, -R:R+1]

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

    patch = add_gradation(x, y, R, c2, shade, angle, shift)
    patch *= mask[..., None]

    # --- SSAA ---
    h = size // scale
    w = size // scale

    patch = patch[:h*scale, :w*scale]
    mask  = mask[:h*scale, :w*scale]

    patch = patch.reshape(h, scale, w, scale, 3).mean(axis=(1, 3))
    mask  = mask.reshape(h, scale, w, scale).mean(axis=(1, 3))

    return patch, mask

# =========================
# 雪の結晶パッチ
# =========================
@regi
def snowflake_dot(p: Param, *, shade=0, angle=215, shift=40,
                  bthick=50, blength=50, btaper=70):
    c2 = p.color2.ctoi()
    gs = p.pdepth  # global scale
    r = p.pwidth * gs

    shade = clip(check_preservarg('shade', shade),0,255)
    angle = check_preservarg('angle', angle)
    shift = check_preservarg('shift', shift) / 100.0
    bthick = check_preservarg('bthick', bthick) / 100.0
    blength = check_preservarg('blength', blength) / 100.0
    btaper = check_preservarg('btaper', btaper) / 100.0

    scale = 4
    R = r * scale
    size = 2 * R + 1

    y, x = np.ogrid[-R:R+1, -R:R+1]

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

    patch = add_gradation(x, y, R, c2, shade, angle, shift)
    patch *= mask[..., None]

    # --- SSAA ---
    h = size // scale
    w = size // scale

    patch = patch[:h*scale, :w*scale]
    mask  = mask[:h*scale, :w*scale]

    patch = patch.reshape(h, scale, w, scale, 3).mean(axis=(1, 3))
    mask  = mask.reshape(h, scale, w, scale).mean(axis=(1, 3))

    return patch, mask


# =========================
# 三角格子配置
# =========================
def polkadot(param: Param):
    scale = clip(int(param.pdepth), 1, 4)
    r = param.pwidth * scale  # パッチ基本サイズ
    v = param.pheight * scale  # 格子点間の距離
    #c2 = param.color2.ctoi()  # 前景色(パッチ基本色)
    w, h = param.width * scale, param.height * scale  # 画像サイズ
    lattice = polkadot_preserv['lattice']  # 格子タイプ(TRIANGULAR|SQUARE)

    W = w + 4*r
    H = h + 4*r
    
    img = np.zeros((H, W, 3), dtype=np.float32)
    alpha = np.zeros((H, W), dtype=np.float32)

    shape = polkadot_preserv['shape']
    if shape in polkadot_preserv['funcs']:
        patch, mask = FN[shape](param)
    else:
        patch, mask = circle_dot(param)
    ps_y, ps_x = patch.shape[:2]

    dy = v * np.sqrt(3) / 2 if lattice == TRIANGULAR else v
    n_rows = int(H / dy) + 2
    n_cols = int(W / v) + 2

    cx_base = np.arange(n_cols) * v

    for j in range(n_rows):
        cy = int(j * dy)
        if lattice == TRIANGULAR:
            offset = int(v / 2) if (j % 2) else 0
        else:
            offset = 0
        cx_row = (cx_base + offset).astype(int)

        for i in range(n_cols):
            cx = cx_row[i]

            # --- 貼り付け位置（パッチ基準） ---
            y0 = cy - ps_y // 2
            x0 = cx - ps_x // 2
            y1 = y0 + ps_y
            x1 = x0 + ps_x

            # --- クリッピング ---
            py0 = max(0, -y0)
            px0 = max(0, -x0)
            py1 = min(ps_y, H - y0)
            px1 = min(ps_x, W - x0)

            iy0 = max(0, y0)
            ix0 = max(0, x0)
            iy1 = iy0 + (py1 - py0)
            ix1 = ix0 + (px1 - px0)

            # 空ならスキップ
            if py0 >= py1 or px0 >= px1:
                continue

            # --- 必ず同じサイズで切り出す（最重要） ---
            sub_patch = patch[py0:py1, px0:px1]
            sub_mask  = mask[py0:py1, px0:px1]
            sub_img   = img[iy0:iy1, ix0:ix1]
            sub_alpha = alpha[iy0:iy1, ix0:ix1]
            
            mask3 = sub_mask[..., None]
            sub_img[:] = sub_img * (1 - mask3) + sub_patch * mask3
            sub_alpha[:] = np.maximum(sub_alpha, sub_mask)

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
        polkadot_preserv['arglists'] = AG

    if polkadot_preserv['shape'] is None:
        polkadot_preserv['shape'] = polkadot_preserv['funcs'][0]

    shape = polkadot_preserv['shape']
    for a in polkadot_preserv['arglists'][shape]:
        if a in STANDARD_ARGS:
            polkadot_preserv['args'][a] = STANDARD_ARGS[a]

    scale = clip(int(p.pdepth), 1, 4)
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
    

