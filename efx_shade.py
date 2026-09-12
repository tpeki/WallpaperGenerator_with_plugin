from wall_common import *
import TkEasyGUI as sg
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np
import math
import copy
import os.path as pa
import filedialog as fdi
import inspect

# 各maskのパラメータ設定もいれられるようにする：mod_ivy参照

FN = {}  # 登録先辞書
shade_preserv = {'shade':{'shift':30, 'alpha':90, 'blur':20, 'adjbri':-80.0},
                 }
File_types = [('PNG','*.png'),('JPG','*.jpg'),('Any','*.*'),]
Preview_Size = (560,315)
Shrink_Size = (192,108)

# ==========
# 関数登録用デコレータ
# ==========
def reg(*, display=None):
    """使用例： @reg(display="<Menu String>")
    FN{} に関数情報をすべて登録
    FN.keys()で登録関数名を取得
    FN[name]['func']() で登録関数を実行
    """
    def decorator(func):
        # 関数名
        name = func.__name__

        # 引数情報
        sig = inspect.signature(func)
        params = sig.parameters

        # デフォルト値辞書
        defaults = {
            p.name: p.default
            for p in params.values()
            if p.default is not inspect._empty
        }

        # docstring を description として使う
        description = (func.__doc__ or "").strip()

        # display が指定されていなければ関数名を使う
        disp = display or name

        # 辞書にまとめて登録
        FN[name] = {
            "func": func,
            "display": disp,
            "description": description,
            "defaults": defaults,
            "args": list(params.keys())[2:],
        }

        return func
    return decorator


def intro(efxlist: EfxModules, module_name):
    efxlist.add_module(module_name, '前景＋影貼り付け',
                       {'mask': list(FN.keys()),
                        'proc': ['add_silhouette',
                                 ]
                        })
    # proc: [(<function>, <usable_subs>),...]
    return module_name


# 保存パラメータがあれば返す
# =========================
def prevset(name, value, funcname, lo=None, hi=None):
    retv = shade_preserv.get(funcname, {}).get(name, value)
    
    if lo is not None:
        retv = max(lo, retv)
    if hi is not None:
        retv = min(retv, hi)
    
    return retv


def storehist(name, value, funcname):
    if shade_preserv.get(funcname,None) is None:
        shade_preserv[funcname] = {}
    shade_preserv[funcname][name] = value
    return


# MASK functions
@reg(display='Checker')
def checker_mask(W, H, Pitch=640, Skew=50, Angle=0):
    """チェック"""
    Pitch = prevset('Pitch', Pitch, 'checker_mask', 0)
    Angle = prevset('Angle', Angle, 'checker_mask') % 360
    Skew = prevset('Skew', Skew, 'checker_mask', 1, 100) / 100

    theta = np.deg2rad(Angle)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    # 座標生成
    yg, xg = np.mgrid[0:H, 0:W]

    # 画像中心を原点に
    cx = W / 2
    cy = H / 2
    xg = xg - cx
    yg = yg - cy

    # 回転
    xr = xg * cos_t + yg * sin_t
    yr = -xg * sin_t + yg * cos_t

    # 中央がマス中心になるよう半マスずらす
    bandw = Pitch * Skew

    band_x = np.mod(xr, Pitch) < bandw
    band_y = np.mod(yr, Pitch) < bandw
    npmask = band_x ^ band_y

    img_array = (npmask * 255).astype(np.uint8)
    mask = Image.fromarray(img_array, mode="L")

    return mask


@reg(display='Houndstooth')
def chidori_mask(W, H, Pitch=300, Twill=50, Angle=0):
    """千鳥格子"""
    Pitch = prevset('Pitch', Pitch, 'chidori_mask', 0)
    Angle = prevset('Angle', Angle, 'chidori_mask') % 360
    Twill = prevset('Twill', Twill, 'chidori_mask', 0, 200) / 100
    
    theta = np.deg2rad(Angle)

    yg, xg = np.mgrid[0:H, 0:W]

    cx = W/2
    cy = H/2

    xg = xg - cx
    yg = yg - cy

    xr = xg*np.cos(theta) + yg*np.sin(theta)
    yr = -xg*np.sin(theta) + yg*np.cos(theta)

    xi = np.floor(xr).astype(np.int32)
    yi = np.floor(yr).astype(np.int32)

    warp_grid = ((xi // (Pitch//2)) & 1)
    weft_grid = ((yi // (Pitch//2)) & 1)

    weave = max(1, int(Twill * Pitch / 2))
    weave_mask = ((xi + yi) % (2*weave)) < weave

    raw_fabric = np.where(weave_mask, warp_grid, weft_grid).astype(np.uint8)
    img = Image.fromarray(raw_fabric * 255, mode='L')
    
    return img


@reg(display='Mesh')
def wiremesh_mask(W, H, Pitch=135, Thickness=53,
                       Angle1=72, Angle2 = -72):
    """ラティス"""
    # Pitch = 135        板間隔
    # Thickness = 53     板幅
    # Angle1 = 72        メッシュ角度1
    # Angle2 = -Angle1   メッシュ角度2
    
    Pitch = prevset('Pitch', Pitch, 'wiremesh_mask', 0)
    Thickness = prevset('Thickness', Thickness, 'wiremesh_mask', 0)
    Angle1 = prevset('Angle1', Angle1, 'wiremesh_mask') % 360
    Angle2 = prevset('Angle2', Angle2, 'wiremesh_mask') % 360

    mask1 = create_stripe_mask(W, H, Pitch, Thickness, Angle1)
    mask2 = create_stripe_mask(W, H, Pitch, Thickness, Angle2)

    mesh_mask = mask1 | mask2

    img_array = (mesh_mask * 255).astype(np.uint8)
    mask = Image.fromarray(img_array, mode="L")

    return mask


@reg(display='Stripe')
def stripe_mask(W, H, Pitch=135, Thickness=75, Angle=89):
    """ストライプ"""
    # Pitch = 135        線間隔
    # Thickness = 53     線幅
    # Angle1 = 72        ストライプ角度1
    
    Pitch = prevset('Pitch', Pitch, 'stripe_mask', 0)
    Thickness = prevset('Thickness', Thickness, 'stripe_mask', 0)
    Angle = prevset('Angle', Angle, 'stripe_mask') % 360
    
    mask = create_stripe_mask(W, H, Pitch, Thickness, Angle)

    img_array = (mask * 255).astype(np.uint8)
    mask = Image.fromarray(img_array, mode="L")

    return mask


def create_stripe_mask(W, H, Pitch, Thickness, Angle):
    theta = np.deg2rad(Angle)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    # 座標生成
    yg, xg = np.mgrid[0:H, 0:W]

    # ===== 中央を原点にする =====
    cx = W / 2
    cy = H / 2
    xg = xg - cx
    yg = yg - cy

    # 斜め方向へ射影
    ug = xg * cos_t + yg * sin_t

    # 中央対称にするために絶対値を使う方法もあるが、
    # 今回は周期を中央基準にする
    stripe = np.mod(ug + Pitch/2, Pitch)

    np_mask = stripe < Thickness

    return np_mask


@reg(display='Punch Metal')
def punching_mask(W, H, Pitch=210, R=70, Angle=0):
    """穴開き鋼板"""
    Pitch = prevset('Pitch', Pitch, 'punching_mask', 0)
    R = prevset('R', R, 'punching_mask', 0)
    Angle = prevset('Angle', Angle, 'punching_mask') % 360
    
    yg, xg = np.mgrid[0:H, 0:W]

    theta = np.deg2rad(Angle)
    xr = xg*np.cos(theta) + yg*np.sin(theta)
    yr = -xg*np.sin(theta) + yg*np.cos(theta)

    xr = xr - W/2
    yr = yr - H/2

    row_pitch = Pitch * np.sqrt(3) / 2

    row = np.floor((yr + row_pitch/2) / row_pitch)

    # 奇数行を半ピッチずらす
    xshift = (row % 2) * (Pitch/2)

    dx = (xr - xshift + Pitch/2) % Pitch - Pitch/2
    dy = (yr + row_pitch/2) % row_pitch - row_pitch/2

    np_mask = dx**2 + dy**2 > R**2

    img_array = (np_mask * 255).astype(np.uint8)
    mask = Image.fromarray(img_array, mode="L")

    return mask


@reg(display='Farniture')
def chair_and_table(W, H, Scale=4, Prop=2.2, Position=8.3):
    """家具"""
    # Scale=4      全体サイズ(H)
    # Prop=2.2     縦横比(X)
    # Position=8.3 配置(W%)

    Scale = prevset('Scale', Scale, 'chair_and_table', 1E-6)
    Prop = prevset('Prop', Prop, 'chair_and_table', 1E-6)
    Position = prevset('Position', Position, 'chair_and_table', 0, 100)
    
    # マスクベース
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)

    # 配置領域
    region_h = int(H * Scale/12)   # FHDの時360
    region_w = int(region_h * Prop)

    x0 = int(Position/100*W)
    y0 = H - region_h

    # print('Screen',W,H, 'pos',x0, y0, 'size',region_w,region_h,
    #      'add',x0+region_w, y0+region_h)

    # ====================
    # 椅子
    # ====================
    chair_w = int(region_w * 0.3)
    chair_h = region_h
    cx0 = x0
    cx1 = x0 + chair_w
    
    leg_h = int(chair_h * 0.4)  # 脚長 2/5
    back_h = int(chair_h * 0.6)   # 背板長 3/5
    seat_h = int(chair_h * 0.1)  # 座面厚

    seat_y1 = y0 + chair_h - leg_h
    seat_y0 = seat_y1 - seat_h
    back_y0 = seat_y0 - back_h
    back_y1 = seat_y0

    # 背板
    back_shift = int(np.cos(np.deg2rad(85))*chair_w)
    back_thick = chair_w * 0.13
    md.polygon((cx0, back_y0, cx0+back_thick, back_y0,
                cx0+back_thick+back_shift, back_y1,
                cx0+back_shift, back_y1), fill=255)

    # 座面（L字）
    md.rectangle((cx0, seat_y0, cx0+chair_w*0.9, seat_y1), fill=255)

    # 脚
    leg_shift = int(np.cos(np.deg2rad(87))*chair_w)
    leg_w = chair_w*0.15

    # 左脚
    lleg_x0 = cx0 + leg_w*0.08
    md.polygon((lleg_x0+leg_shift, seat_y1,
                lleg_x0+leg_shift+leg_w, seat_y1,
                lleg_x0+leg_w, y0+chair_h,
                lleg_x0, y0+chair_h), fill=255)
    
    # 右脚
    rleg_x1 = cx0 + chair_w*0.9 - leg_w*0.08
    md.polygon((rleg_x1-leg_w-leg_shift, seat_y1,
                rleg_x1-leg_shift, seat_y1,
                rleg_x1, y0+chair_h,
                rleg_x1-leg_w, y0+chair_h), fill=255)

    # ====================
    # 机
    # ====================
    table_w = int((region_w - chair_w)*0.9)
    table_y0 = int((back_y0 + seat_y0) / 2)
    table_h = H - table_y0
    tx0 = int(cx1 + table_w * 0.1)
    tx1 = tx0+table_w
    
    # 天板
    table_top = table_y0  # 天板上面(背板と座面の中間)
    table_thick = int(table_h * 0.18)  # 天板厚さ
    #print(Scale, table_h, table_top, table_thick)

    # 天板
    md.rectangle((tx0, table_top, tx1, table_top+table_thick), fill=255)

    # 脚
    leg_shift = int(np.cos(np.deg2rad(89))*table_w)
    leg_w = int(table_w * 0.11)  # 脚幅
    leg_off = int(table_w * 0.1)  # 脚繰込み
    leg_top = table_top + table_thick  # 脚上端Y
    leg_h = y0 + region_h - leg_top  # 脚高さ

    # 左脚
    lleg_x = int(tx0 + leg_off)
    md.polygon((lleg_x+leg_shift, leg_top,
                lleg_x+leg_shift+leg_w, leg_top,
                lleg_x+leg_w, y0+region_h,
                lleg_x, y0+region_h), fill=255)
    
    # 右脚
    rleg_x = tx0 + table_w - leg_off - leg_w
    md.polygon((rleg_x-leg_shift, leg_top,
                rleg_x-leg_shift+leg_w, leg_top,
                rleg_x+leg_w, y0+region_h,
                rleg_x, y0+region_h), fill=255)

    # 筋交い
    md.line((lleg_x+leg_shift+leg_w//2,leg_top,
             rleg_x-leg_shift+leg_w//2,leg_top+leg_h//3),
            fill=255, width=leg_w//2)
    md.line((rleg_x-leg_shift+leg_w//2,leg_top,
             lleg_x+leg_shift+leg_w//2,leg_top+leg_h//3),
            fill=255, width=leg_w//2)

    return mask


@reg(display='Ladder')
def ladder_mask(W, H, Steps=8, Width=12.0, Rail=10.0,
                     Height=90.0, Rung=18.0, Position=83.0):
    """はしご"""
    # Steps=8       段数
    # Width=12.0    梯子幅(横木)(W%)
    # Rail=10.0     レール幅(%)
    # Height=90.0   梯子長(H%)
    # Rung=18.0     横木厚(%)
    # Position=83.0 配置(W%)

    Steps = prevset('Steps', Steps, 'ladder_mask', 0)
    Width = prevset('Width', Width, 'ladder_mask', 0, 100)
    Rail = prevset('Rail', Rail, 'ladder_mask', 0, 100)
    Height = prevset('Height', Height, 'ladder_mask', 0, 100)
    Rung = prevset('Rung', Rung, 'ladder_mask', 0, 100)
    Position = prevset('Position', Position, 'ladder_mask', 0, 100)
    
    x0 = int(W * Position/100)
    y0 = int(H * (1-Height/100))
    y1 = H
    ladder_w = int(W * Width/100)
    step_h = (y1-y0) / Steps
    rail_width_ratio = Rail/100
    rung_height_ratio= Rung/100
    
    set_width = W - x0
    rail_w = int(ladder_w * rail_width_ratio)
    rung_h = step_h * rung_height_ratio

    # print('Pos', x0, y0, y1, 'Width', ladder_w, 'Rail', rail_w,
    #       'Rung', rung_h, 'Steps', Steps)
    
    mask = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(mask)

    # 梯子
    md.rectangle((x0, y0, x0 + rail_w, y1), fill=255)
    md.rectangle((x0 + ladder_w - rail_w, y0, x0 + ladder_w, y1), fill=255)

    for i in range(Steps):
        cy = y0 + step_h * (i + 0.5)
        sy = int(cy - rung_h / 2)
        ey = int(cy + rung_h / 2)
        md.rectangle((x0, sy, x0 + ladder_w, ey), fill=255)

    return mask


# PROC functions
# 前景を切り抜いて影付きで貼る(numpy版)
def add_silhouette(fgimg, mask, bgimg,
                   shift=30, alpha=90, blur=8, adjbri=0.0,
                   sharp_radius=0, sharp_percent=180, sharp_threshold=3,
                   W=1920, H=1080):
    # shift = 30  影のシフト量(pixel)
    # alpha = 90  影の透過度(0-255)
    # blur = 8    影のぼかし半径(pixel)


    W, H = fgimg.size

    if isinstance(mask, None | str):
        if mask in FN.keys():
            mask = FN[mask]['func'](W, H)
        else:
            mask = FN[next(iter(FN))]['func'](W, H)

    # 影
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, alpha), mask=mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))

    # 周期シフト
    dx = -shift
    dy = -shift

    base_np = np.array(fgimg.convert("RGBA"))
    shifted_np = np.roll(base_np, shift=(dy, dx), axis=(0, 1))
    shifted = Image.fromarray(shifted_np, mode="RGBA")

    # マスクで切り抜き
    fg = Image.composite(shifted,
                         Image.new("RGBA", (W, H), (0, 0, 0, 0)),
                         mask)
    if sharp_radius > 0:
        fg = fg.filter(ImageFilter.UnsharpMask(radius=sharp_radius,
                                               percent=sharp_percent,
                                               threshold=sharp_threshold))
    # 合成
    result = adjust_brightness(bgimg.convert("RGBA"), adjbri)
    result = Image.alpha_composite(result, shadow)
    result = Image.alpha_composite(result, fg)

    return result


def resize_keepasp(img, W, H):
    iw, ih = img.size
    if ih == H and iw == W:
        return img

    r = min(W/iw, H/ih)
    return img.resize((int(iw*r),int(ih*r)), resample=Image.LANCZOS)


def plain_image(W, H, base=(192,192,192), baseadd=(64,64,64), contrast=0.02):
    c = []
    for i in range(3):
        c.append(clip8(base[i]))
        if c[i] < 255 and baseadd[i] > 0:
            c[i] = clip8(np.random.randint(c[i], base[i]+baseadd[i]))
    img = Image.new('RGBA', (W, H), color=tuple(c))

    fg = np.array(img, dtype=np.float32)
    factor = swirl_marble(W,H, swirl=8, contrast=contrast)
    res = (fg * factor[...,None]).astype(np.uint8)
        
    return Image.fromarray(res, mode='RGBA')


def swirl_marble(W, H, freq=10, swirl=6, wobble=0.25, contrast=0.22):
    xs = np.linspace(-1, 1, W, endpoint=False)
    ys = np.linspace(-1, 1, H, endpoint=False)
    X, Y = np.meshgrid(xs, ys)

    # アスペクト比補正
    aspect = W / H
    if aspect > 1:
        Y = Y * aspect
    else:
        X = X / aspect

    rad = np.sqrt(X * X + Y * Y)
    phi = np.arctan2(Y, X)

    flow = (
        rad * freq
        + phi * swirl
        + wobble * np.sin(phi * 5 + rad * 8)
    )

    base = (1.0 + contrast * np.sin(flow)).astype(np.float32)
    return np.clip(base, 0, 1)


# -----
# 明度変更
# -----
def srgb_to_linear(x, gamma):
    """numpy配列: sRGB(ガンマあり) → リニア変換"""
    x = x / 255.0
    base = np.maximum(x + 0.055, 0.0) / 1.055
    return np.where(x <= 0.04045, x / 12.92, base ** gamma)

def linear_to_srgb(x, gamma):
    """numpy配列: リニア → sRGB(ガンマあり)変換"""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x < 0.0031308, x * 12.92,
                    1.055 * (x ** (1/gamma)) - 0.055) * 255.0

def luminance_linear(arr_lin):
    """numpy配列の輝度算出(リニア)"""
    return 0.2126*arr_lin[...,0] + 0.7152*arr_lin[...,1] + 0.0722*arr_lin[...,2]


# --- 明度加算（ガンマ込み） ---
def adjust_brightness(img: Image.Image, delta: float,
                      gamma: float = 2.2) -> Image.Image:
    """PILイメージの明度をdelta(-255.0..255.0)加算
    (gamma=2.2(sRGB), 1.8(Mac68k), )"""
    
    arr = np.asarray(img).astype(np.float32)

    # RGB / RGBA 判定
    has_alpha = (arr.shape[-1] == 4)
    rgb = arr[..., :3]
    alpha = arr[..., 3] if has_alpha else None

    # sRGB → linear
    rgb_lin = srgb_to_linear(rgb, gamma)

    # delta を linear に変換
    delta_lin = srgb_to_linear(np.array([delta], dtype=np.float32), gamma)[0]
    # print(np.max(delta_lin), np.min(delta_lin)) 

    # 明度加算（linear 空間で行う）
    rgb_lin = rgb_lin + delta_lin
    # print(np.max(rgb_lin), np.min(rgb_lin)) 

    # linear → sRGB
    rgb_srgb = linear_to_srgb(rgb_lin, gamma)

    # 再構成
    if has_alpha:
        out = np.dstack([rgb_srgb, alpha])
    else:
        out = rgb_srgb

    return Image.fromarray(out.astype(np.uint8))


# --- 明度を絶対値指定 ---
def set_brightness_absolute(img: Image.Image, target_L: float,
                            gamma: float = 2.2) -> Image.Image:
    """PILイメージの明度を絶対値(0.0..255.0)で指定
    (gamma=2.2(sRGB), 1.8(Mac68k), )"""
    arr = np.asarray(img).astype(np.float32)

    # RGB / RGBA 判定
    has_alpha = (arr.shape[-1] == 4)
    rgb = arr[..., :3]
    alpha = arr[..., 3] if has_alpha else None

    rgb_lin = srgb_to_linear(rgb, gamma)

    # 現在の明度（linear）
    L = luminance_linear(rgb_lin)

    # RGB 比を維持してスケール
    target_lin = srgb_to_linear(np.array([target_L], dtype=np.float32),
                                gamma)[0]
    scale = target_lin / (L + 1e-6)
    rgb_lin = rgb_lin * scale[..., None]

    # linear → sRGB
    rgb_srgb = linear_to_srgb(rgb_lin, gamma)

    # 再構成
    if has_alpha:
        out = np.dstack([rgb_srgb, alpha])
    else:
        out = rgb_srgb

    return Image.fromarray(out.astype(np.uint8))


# --------------------
# main
# --------------------
def mask_line(mask_name, sw):
    if not mask_name in FN:
        return None
    args = FN[mask_name]['defaults']
    
    lo = [sg.Radio('', default=sw, key=mask_name, group_id='-item-'),
          sg.Text(FN[mask_name]['display'], width=12)]
    for param in args.keys():
        lo.append(sg.Text(param))
        val = prevset(param, args[param], mask_name)
        lo.append(sg.Input(f'{val}', key=f'-{mask_name}_{param}-', width=4))

    return lo

def scan_va(va, mask_name):
    args = FN[mask_name]['defaults']
    pre = f'-{mask_name}_'
    for param in args.keys():
        if f'-{mask_name}_{param}-' in va:
            val = va[f'-{mask_name}_{param}-']
            try:
                if '.' in val:
                    val = float(val)
                else:
                    val = int(val,0)
            except ValueError:
                continue
            storehist(param, val, mask_name)
    return

    
def getto(va, name, default, lo=None, hi=None):
    key = f'-s_{name}-'
    pv = shade_preserv['shade'].get(name, default)
    
    try:
        v = va[key]
    except KeyError:
        v = ''
        
    retv = safeint(v, default)
    
    if lo:
        retv = max(lo, retv)
    if hi:
        retv = min(retv, hi)

    shade_preserv['shade'][name] = retv
    return retv


def safeint(s, default=0):
    if not isinstance(s,str):
        return default
    if '.' in s:
        try:
            r = float(s)
        except ValueError:
            r = default
    else:
        try:
            r = int(s,0)
        except ValueError:
            r = default
    return r


def efx(image, p: Param):
    global shade_preserv
    
    dcpy = copy.deepcopy(shade_preserv)
    MASKS = {FN[_]['display']: _ for _ in FN.keys()}

    W, H = p.width, p.height
    init_fgimg = image if image else plain_image(W,H)    
    try:
        if init_fgimg.size != (W,H):
            init_fgimg = init_fgimg.resize((W,H), resample=Image.LANCZOS)
    except AttributeError:
        pass

    init_bgimg = p.bg(W,H)

    # default Bacic Params
    shift = shade_preserv['shade']['shift']
    alpha = shade_preserv['shade']['alpha']
    blur = shade_preserv['shade']['blur']
    adjbri = shade_preserv['shade']['adjbri']
    bgmenu = ['FG', 'BG', 'File', 'Plain']
    bgind = ['*frontimage*', '*internal*', '*file*', '*plain*']
    if init_bgimg:
        bgfile = bgind[1]
        bgmode = 'BG'
        bgimg = init_bgimg
    else:
        bgfile = bgind[0]
        bgmode = 'FG'
        bgimg = init_fgimg
 
    base = (192,192,192)
    swirlcont = 0
    file_image = None
    fgc, bgc = bg_and_font(base)
     
    # UI panel                
    menu_lo = []
    for i, x in enumerate(FN.keys()):
        menu_lo.append(mask_line(x, True if i == 0 else False))

    shadeset = [[sg.Text(' Shift='),
                 sg.Input(f'{shift}', key='-s_shift-', width=4),
                 sg.Text(' Blur='),
                 sg.Input(f'{blur}', key='-s_blur-', width=4),
                 sg.Text(' Intent'),
                 sg.Input(f'{alpha}', key='-s_alpha-', width=4),
                 sg.Text(' BG Brightness='),
                 sg.Input(f'{adjbri}', key='-s_adjbri-', width=5),
                 ]]

    bgset = [[sg.Combo(bgmenu, default_value=bgmode, key='-bgsel-',
                       width=5, readonly=True, enable_events=True),
              sg.Text(' BG file:'),
              sg.Text(bgfile, key='-fn1-', background_color='#f8f8f8',
                      expand_x=True),
              sg.Button('<File', key='-file1-', background_color='#ffffdd'),
              ],
             [sg.Checkbox('Swap FG/BG', default=False, key='-swap-'),
              sg.Text(' Plain: '),
              sg.Button('BaseColor', key='-bgc-', text_color=fgc,
                        background_color=bgc),
              sg.Text('Jitter'), sg.Input(f'{clip8(255-max(*base))}',
                                          key='-badd-', width=4),
              sg.Text('Contrast%'), sg.Input(f'{swirlcont}',
                                             key='-bcont-', width=4),
              sg.Text(' ', expand_x=True),
            ]]
    buttonset = [[sg.Text('', expand_y=True)],
                 [sg.Text(' ', expand_x=True),
                  sg.Button('Test', key='-test-'),
                  sg.Button('Ok', key='-ok-', background_color='#ddffdd'),
                  sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
                  ]]

    lo = [[sg.Frame(title='Flavor Type', layout=menu_lo,
                    relief='ridge', expand_x=True)],
          [sg.Image(size=Preview_Size, key='-timg-'),
           sg.Column([[sg.Button('<',key='-pfold-', text_color='white',
                                 background_color='#6688cc')],
                      [sg.Text(expand_y=True)]], expand_y=True)],
          [sg.Frame('Common Shading', layout=shadeset, relief='ridge',
                    expand_x=True)],
          [sg.Frame('Background', layout=bgset, relief='ridge'),
           sg.Column(buttonset, expand_x=True, expand_y=True),],
           ]
           
    src_path = None
    mask_name = next(iter(FN))
    folded = False

    sample = add_silhouette(init_fgimg, mask_name, bgimg,
                            shift=shift, alpha=alpha, blur=blur, adjbri=adjbri) 
   
    wn = sg.Window('Add Flavor', layout=lo)
    
    while True:
        wn['-timg-'].update(data=sample)
        
        ev, va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            sample = image
            shade_preserv = dcpy
            break
        elif ev == '-ok-':
            break
        elif ev == '-file1-':
            src_path = fdi.get_openfile(fdi.sanitize_filename(bgfile),
                                        filetypes=File_types)
            bgfile = pa.basename(src_path)
            if pa.exists(src_path):
                file_image = Image.open(src_path).convert('RGBA')
                file_image = file_image.resize((W,H), resample=Image.LANCZOS)
                va['-bgsel-'] = 'File'
                bgmode = None
            fdi.flush_ev(wn)
        elif ev == '-bgc-':
            base = to_rgb(sg.popup_color('Select Base Color', default_color=base))
            fgc, bgc = bg_and_font(base)
            wn['-bgc-'].update(background_color=bgc, text_color=fgc)
            va['-bgsel-'] = 'Plain'
            bgmode = None
            fdi.flush_ev(wn)
        elif ev == '-test-':
            bgmode = None
        elif ev == '-pfold-':
            if folded:
                wn['-timg-'].update(size=Preview_Size)
                folded = False
                wn['-pfold-'].update('<')
            else:
                wn['-timg-'].update(size=Shrink_Size)
                folded = True
                wn['-pfold-'].update('>')
            continue

        if '-item-' in va:
            if va['-item-'] in FN:
                mask_name = va['-item-']
        scan_va(va, mask_name)

        shift = getto(va, 'shift', shift, 0)
        alpha = getto(va, 'alpha', alpha, 0, 255)
        blur = getto(va, 'blur', blur, 0)
        adjbri = getto(va, 'adjbri', adjbri)

        if va['-bgsel-'] == 'Plain' and bgmode != 'Plain':
            # print('Plain selected')
            bgmode = 'Plain'
            wn['-fn1-'].update(bgind[3])
            addv = safeint(va['-badd-'])
            contrast = min(max(0,safeint(va['-bcont-'])),100)
            bgimg = plain_image(W, H, base=base, baseadd=(addv,addv,addv),
                                contrast=contrast/100)
        elif va['-bgsel-'] == 'File':
            # print('File selected')
            if file_image is not None and bgmode != 'File':
                bgmode = 'File'
                wn['-fn1-'].update(bgfile)
                bgimg = file_image
        elif va['-bgsel-'] == 'BG':
            # print('BG selected')
            if init_bgimg is not None and bgmode != 'BG':
                bgmode = 'BG'
                wn['-fn1-'].update(bgind[1])
                bgimg = init_bgimg
        elif va['-bgsel-'] == 'FG':  # and bgmode != 'FG':
            # print('FG selected')
            bgmode = 'FG'
            wn['-fn1-'].update(bgind[0])
            bgimg = init_fgimg

        wn['-bgsel-'].update(bgmode)
                
        if va['-swap-']:
              bg = init_fgimg
              fg = bgimg
        else:
              fg = init_fgimg
              bg = bgimg

        sample = add_silhouette(fg, mask_name, bg, shift=shift, alpha=alpha,
                                blur=blur, adjbri=adjbri)
        wn['-timg-'].update(sample)

        wn.refresh()

    wn.close()

    return sample


if __name__ == "__main__":
    p = Param()
    p.width, p.height = (1920,1080)
    
    img = efx(None, p)
    if img is not None:
        img.show()
