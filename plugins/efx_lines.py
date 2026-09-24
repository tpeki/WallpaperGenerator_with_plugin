from wall_common import *
import TkEasyGUI as sg
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import numpy as np
import copy
import os.path as pa
import filedialog as fdi
import inspect

lines_preserv = {'shade':{'shift':2, 'alpha':40, 'blur':5,},
                 'radial':{'exclude':240, 'freq':120},
                 'stripe':{'exclude':0, 'pitch':20, 'angle':0},
                 'common':{'trans':254, 'duty':0.3},
                 }
Default_Stripe_Color = (192,192,192)
Default_Stripe_Color2 = (128,128,128)
Preview_Size = (560,315)  # (640, 360)
Shrink_Size = (240,135)

File_types = [('PNG','*.png'),('JPG','*.jpg'),('Any','*.*'),]
FN = {}  # 登録先辞書
    
def intro(efxlist: EfxModules, module_name):
    efxlist.add_module(module_name, 'ストライプを上書き',
                       {'mask': list(FN.keys()),
                        'proc': ['add_stripe',
                                 ]
                        })
    # proc: [(<function>, <usable_subs>),...]
    return module_name


# 保存パラメータがあれば返す
# =========================
def prevset(name, default, funcname, lo=None, hi=None):
    """global辞書の値を取得 name=保存名 value=デフォルト値 funcname=グループ名"""
    retv = lines_preserv.get(funcname, {}).get(name, default)
    if retv is None:
        retv = default
    
    if lo is not None:
        retv = max(lo, retv)
    if hi is not None:
        retv = min(retv, hi)
    
    return retv


def storehist(name, value, funcname):
    """global辞書に値を保存 name=保存名 funcname=グループ名"""
    if lines_preserv.get(funcname,None) is None:
        lines_preserv[funcname] = {}
    lines_preserv[funcname][name] = value
    return


# 関数登録用デコレータ
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

# MASK functions
@reg(display="Simple Stripes")
def stripe(W, H, pitch=20, angle=0.0, exclude=0, cx=None, cy=None):
    """W,H: 画像サイズ  cx,cy: 中心位置
    exclude: 非描画半径  pitch:周期(px.)  duty: 白黒比  angle: 角度(水平=90)
    """
    if cx is None:
        cx = 50
    if cy is None:
        cy = 50

    cx = prevset('cx', cx, 'stripe')
    cy = prevset('cy', cy, 'stripe')
    exclude = prevset('exclude', exclude, 'stripe')
    pitch = prevset('pitch', pitch, 'stripe')
    angle = prevset('angle', angle, 'stripe')
    duty = prevset('duty', 0.1, 'common', lo=0.1, hi=1.0)
    trans = prevset('trans', 255, 'common', lo=0, hi=255)

    cx = int(cx*W/100)
    cy = int(cy*H/100)
    
    angle = np.deg2rad(angle)

    # グリッド
    y, x = np.ogrid[:H, :W]
    dx = x - cx
    dy = y - cy

    # 回転後の座標系で「縦ストライプ」を作る
    rot = dx * np.cos(angle) + dy * np.sin(angle)
    phase = (rot / pitch) % 1.0  # 周期化
    stripe = (phase < duty)

    if isinstance(exclude, (tuple, list)):
        rx, ry = exclude
        ellipse = (dx / rx) ** 2 + (dy / ry) ** 2 >= 1.0
        mask = stripe & ellipse
        
    elif exclude > 0:
        r = np.sqrt(dx * dx + dy * dy)
        
        mask = stripe & (r >= exclude)
    else:
        mask = stripe

    return Image.fromarray((mask*255).astype(np.uint8), 'L')


@reg(display="Radial Stripes")
def radial(W, H, freq=120, exclude=240, cx=None, cy=None):
    """W,H : 画像サイズ  cx,cy : 中心位置
    exclude: 中心の非描画半径  freq: 周期  duty: 白黒比(0..1,1=全白)"""

    if cx is None:
        cx = 50
    if cy is None:
        cy = 50

    cx = prevset('cx', cx, 'radial')
    cy = prevset('cy', cy, 'radial')
    exclude = prevset('exclude', exclude, 'radial')
    freq = prevset('freq', freq, 'radial')
    duty = prevset('duty', 0.1, 'common', lo=0.1, hi=1.0)
    trans = prevset('trans', 255, 'common', lo=0, hi=255)

    cx = int(cx*W/100)
    cy = int(cy*H/100)
    
    y, x = np.ogrid[:H, :W]
    dx = x - cx
    dy = y - cy

    # 角度（0〜2π）
    theta = np.arctan2(dy, dx)
    theta = (theta + np.pi) / (2*np.pi)  # 0〜1 に正規化

    # 角度方向のストライプ (角度 0〜1 をpitch freqとみなして周期化)
    stripe_phase = (theta * freq) % 1.0
    stripe = (stripe_phase < duty)

    if isinstance(exclude, (tuple, list)):
        rx, ry = exclude
        ellipse = (dx / rx) ** 2 + (dy / ry) ** 2 >= 1.0
        mask = stripe & ellipse
        
    elif exclude > 0:
        r = np.sqrt(dx * dx + dy * dy)
        
        mask = stripe & (r >= exclude)
    else:
        mask = stripe

    return Image.fromarray((mask*255).astype(np.uint8), 'L')

@reg(display="Zigged Stripes")
def saba(W, H, lw=30, ll=480, sw=58, angle=84):
    """
    ジグザグ接続されたストライプマスク

    lw    : 線幅
    ll    : 長辺の長さ
    sw    : ストライプの中心線間隔
    angle : 回転角 [degree]

    return : 'L' Image ;; not bool ndarray, shape=(H, W)
    """

    lw = prevset('lw', lw, 'saba')
    ll = prevset('ll', ll, 'saba')
    sw = prevset('sw', sw, 'saba')
    angle = prevset('angle', angle, 'saba')

    # 回転後にも十分な大きさになるよう、生成領域を決める
    rad = np.deg2rad(angle)
    ca = abs(np.cos(rad))
    sa = abs(np.sin(rad))

    bw = int(np.ceil(W * ca + H * sa)) + 4
    bh = int(np.ceil(W * sa + H * ca)) + 4

    # 回転時の端切れを避けるための余裕
    margin = int(np.ceil(ll + sw + lw)) + 4

    ww = bw + margin * 2
    hh = bh + margin * 2

    yy, xx = np.indices((hh, ww), dtype=np.float32)

    lr = lw / 2
    sr = sw / 2

    # ==========================================================
    # 1. 水平線
    y0 = margin + sr

    dy = np.mod(yy - y0 + sr, sw) - sr

    mask = np.abs(dy) <= lr

    # ==========================================================
    # 2. ll + sw 周期で幅 sw の縦帯を消す
    pitch_x = ll + sw

    # 縦帯の中心
    x0 = margin + ll + sr

    dx = np.mod(xx - x0 + pitch_x / 2, pitch_x) - pitch_x / 2

    gap = np.abs(dx) <= sr + lr  #(sw -lw)/ 2 

    mask &= ~gap

    # ==========================================================
    # 2'. 長辺の切断端を丸める
    # ==========================================================
    r = lw / 2
    row = np.floor((yy - y0) / sw).astype(np.int32)  # 縦方向の区間番号

    # gap の左端・右端
    left = np.abs(dx + sr + lr)
    right = np.abs(dx - sr - lr)

    circle = (
        ((left ** 2 + dy ** 2) <= lr ** 2) |
        ((right ** 2 + dy ** 2) <= lr ** 2)
        )

    mask |= circle

    # ==========================================================
    # 3. ジグザグ線
    fy = (yy - y0) / sw  # 現在の水平線からの相対位置
    t = fy - np.floor(fy)

    gx = dx / sw   # 縦帯の中心
    line_plus = gx - (t - 0.5)  # / の中心線
    line_minus = gx + (t - 0.5)  # \ の中心線

    inside_gap = np.abs(gx) <= 1.0

    # 線分までの距離を求める
    c = 0.85  # ジグザグ線幅調整 太<1<細
    d_plus = c * np.abs(line_plus) * sw / np.sqrt(2)
    d_minus = c * np.abs(line_minus) * sw / np.sqrt(2)

    zig = np.where(
        (row & 1) == 0,
        d_plus <= lr,
        d_minus <= lr,
    )

    mask |= inside_gap & zig

    # ==========================================================
    # 4. angle 回転
    # PILでrotate
    img = Image.fromarray(
        mask.astype(np.uint8) * 255,
        mode='L'
    )

    img = img.rotate(
        angle,
        resample=Image.Resampling.BICUBIC,
        expand=False
    )

    x0 = (ww - W) // 2
    y0c = (hh - H) // 2

    img = img.crop(
        (x0, y0c, x0 + W, y0c + H)
    )

    #return np.asarray(img) >= 128
    return img


# PROC functions
# maskを貼る(numpy版)
def add_stripe(baseimg, mask, stripeimg):
    """ストライプ設定"""
    shift = prevset('shift', 30, 'shade')  # shift = 30  影のシフト量(pixel)
    alpha = prevset('alpha', 40, 'shade')  # alpha = 90  影の透過度(0-255)
    blur = prevset('blur', 8, 'shade')  # blur = 8    影のぼかし半径(pixel)
    trans = prevset('trans', 255, 'common')

    W, H = baseimg.size

    if isinstance(mask, None | str):
        if mask in FN.keys():
            mask = FN[mask]['func'](W, H)
        else:
            mask = FN[next(iter(FN))]['func'](W, H)

    # 影
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.paste((0, 0, 0, alpha), mask=mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    shadow_np = np.array(shadow.convert("RGBA"))
    shifted_np = np.roll(shadow_np, shift=(shift, shift), axis=(0, 1))
    shadow = Image.fromarray(shifted_np, mode="RGBA")

    if trans == 255:
        stripes = Image.new('RGBA', (W,H), (0,0,0,0))
        stripes.paste(stripeimg, (0,0), mask)
        
        # 影合成
        result = baseimg
        result = Image.alpha_composite(result, shadow)
        result = Image.alpha_composite(result, stripes)
        return result
        

    # 前景合成(透明度あり, 影なし)
    a = trans / 255.0
    result_np = np.array(baseimg).astype(np.float32)
    front = np.array(stripeimg).astype(np.float32)
    mask_np = np.array(mask)
    
    m = (mask_np == 255).astype(np.float32)
    m4 = m[..., None] * np.ones(4, dtype=np.float32)  # (H,W,4)

    result_np = result_np * (1 - m4 * a) + front * (m4 * a)
    result_np = result_np.clip(0, 255).astype(np.uint8)

    return Image.fromarray(result_np, mode='RGBA')


def plain_image(W, H, base=Default_Stripe_Color,
                baseadd=64, contrast=0.0):
    c = []
    for i in range(3):
        c.append(clip8(base[i]))
        c[i] = clip8(np.random.randint(c[i], base[i]+baseadd))
    img = Image.new('RGBA', (W, H), color=tuple(c))

    fg = np.array(img, dtype=np.float32)
    factor = swirl_marble(W,H, swirl=8, contrast=contrast)
    res = (fg * factor[...,None]).astype(np.uint8)
        
    return Image.fromarray(res, mode='RGBA')


def grad_image(W, H, base=Default_Stripe_Color, base2=Default_Stripe_Color2,
               baseadd=64, direction='v', contrast=0.0):
    c1 = to_rgb(rgb_random_jitter(base, baseadd))
    c2 = to_rgb(rgb_random_jitter(base2, baseadd))

    if direction == 'h':
        x_axis = np.linspace(0, 1, W)
        u = np.tile(x_axis, (H, 1))
    elif direction == 'v':
        y_axis = np.linspace(0, 1, H).reshape(-1, 1)
        u = np.tile(y_axis, (1, W))
    else:
        y, x = np.ogrid[:H, :W]
        dx = np.abs(x - W/2)
        dy = np.abs(y - H/2)
        d = ((2*dx / W) ** 2 + (2*dy / H) ** 2) ** (1 / 2)
        edge = 2 ** (1 / 2)
        d /= edge
        u = np.clip(d, 0.0, 1.0)

    r, g, b = [(c1[i] * (1 - u) + c2[i] * u) for i in range(3)]
    fg = np.dstack((r, g, b)).astype(np.uint8)

    factor = swirl_marble(W,H, swirl=8, contrast=contrast)
    res = (fg * factor[...,None]).astype(np.uint8)
        
    return Image.fromarray(res).convert('RGBA')


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
        if val is None:
            val = ''
        wd = 8 if param == 'exclude' else 4
        lo.append(sg.Input(f'{val}', key=f'-{mask_name}_{param}-', width=wd))

    return lo

def scan_va(va, mask_name):
    args = FN[mask_name]['defaults']
    pre = f'-{mask_name}_'
    for param in args.keys():
        if f'-{mask_name}_{param}-' in va:
            val = va[f'-{mask_name}_{param}-']
            if ',' in val and param == 'exclude':
                rx, ry = val.split(',')
                rx = stoi(rx)
                ry = stoi(ry)
                val = [rx,ry]
                #print(f'exclude! <- {val}')
            elif val == 'None' or val == '':
                val = None
                #print(f'{param} <- None')
            else:
                val = stoi(val)
                #print(f'{param} <- {val}')
            storehist(param, val, mask_name)
    return

    
def getval(val, name, default, cat, lo=None, hi=None):
    retv = stoi(val, default, lo, hi)
    if retv is not None:
        storehist(name, retv, cat)
    return retv


def efx(image, p: Param):
    global lines_preserv
    
    dcpy = copy.deepcopy(lines_preserv)
    MASKS = {FN[_]['display']: _ for _ in FN.keys()}

    W, H = p.width, p.height
    if image is None:
        fgimg = plain_image(W,H)
    else:
        fgimg = image.convert('RGBA')
        if fgimg.size != (W,H):
            fgimg = init_fgimg.resize((W,H), resample=Image.LANCZOS)

    # default Bacic Params
    shift = lines_preserv['shade']['shift']
    alpha = lines_preserv['shade']['alpha']
    blur = lines_preserv['shade']['blur']
    duty = lines_preserv['common']['duty']
    trans = lines_preserv['common']['trans']

    bgmenu = ['FG', 'BG', 'File', 'Plain', 'V-Gra', 'H-Gra', 'R-Gra']
    bgind = ['*frontimage*', '*internal*', '*file*', '*plain*',
             '*V-grad*', '*H-grad*', '*radial grad*']

    base = Default_Stripe_Color
    base2 = Default_Stripe_Color2
    addv = clip8(255 - max(base))
    swirlcont = 0

    init_bgimg = p.bg(W,H)
    if init_bgimg is None:
        bgfile = bgind[3]
        bgmode = 'Plain'
        bgimg = plain_image(W,H, base=base, baseadd=addv,
                            contrast=swirlcont)
    else:
        bgfile = bgind[1]
        bgmode = 'BG'
        bgimg = init_bgimg
 
    file_image = None
    fgc, bgc = bg_and_font(base)
    fgc2, bgc2 = bg_and_font(base2)
     
    # UI panel                
    menu_lo = []
    for i, x in enumerate(FN.keys()):
        menu_lo.append(mask_line(x, True if i == 0 else False))
    menu_lo.append([sg.Text('cx,cy are % for W,H;  '\
                            'Set "x,y" to exclude ellipsed void',
                            text_color='#000077',
                            text_align='right', expand_x=True)])

    bgset = [[sg.Combo(bgmenu, default_value=bgmode, key='-bgsel-',
                       width=5, readonly=True, enable_events=True),
              sg.Checkbox('Swap FG/BG', default=False, key='-swap-'),
              sg.Text(' Plain: '),
              sg.Button('BG', key='-bgc-', text_color=fgc,
                        background_color=bgc),
              sg.Button('B2', key='-bgc2-', text_color=fgc2,
                        background_color=bgc2),
              sg.Text('Jitter'), sg.Input(f'{clip8(255-max(*base))}',
                                          key='-badd-', width=4),
              sg.Text('Cont%'), sg.Input(f'{swirlcont}',
                                         key='-bcont-', width=4),
              sg.Text(' '),
              sg.Text(' File:'),
              sg.Text(bgfile, key='-fn1-', background_color='#f8f8f8',
                      expand_x=True),
              sg.Button('< File', key='-file1-', background_color='#ffffdd'),
              ]]
    shadeset = [[sg.Text('Shift', width=6, text_align='right'),
                 sg.Input(f'{shift}', key='-sshift-', width=4),
                 sg.Text('Blur', width=6, text_align='right'),
                 sg.Input(f'{blur}', key='-sblur-', width=4),
                 sg.Text('Intent', width=6, text_align='right'),
                 sg.Input(f'{alpha}', key='-salpha-', width=4),
                 sg.Text(' '),],
                ]
    buttonset = [sg.Text(' '*4, expand_x=True),
                 sg.Button('Test', key='-test-'),
                 sg.Button('Ok', key='-ok-', background_color='#ddffdd'),
                 sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
                 ]
    commonset = [[sg.Text('Duty', width=5, text_align='right'),
                  sg.Input(f'{duty}',key='-duty-',width=4),
                  sg.Text('Conc', width=5, text_align='right'),
                  sg.Input(f'{trans}',key='-trns-',width=4),
                  sg.Text('Trans 0 <-> 255 Solid', text_color='#000077',
                          expand_x=True),]
                 ]
    fold_button = sg.Column([[sg.Button('<',key='-pfold-', text_color='white',
                                       background_color='#6688cc')],
                            [sg.Text(expand_y=True)]], expand_y=True)

    lo = [[sg.Frame(title='Flavor Type', layout=menu_lo,
                    relief='ridge', expand_x=True),],
          [sg.Frame('Stripe Fill', layout=bgset,
                    relief='ridge', expand_x=True),],
          [sg.Frame('Duties', layout=commonset, relief='ridge',
                    expand_x=True),
           sg.Frame('Shade (ON: Conc=255)', layout=shadeset, relief='ridge'),],
          [sg.Image(size=Preview_Size, key='-timg-'),
           fold_button],
          buttonset]

    src_path = None
    mask_name = next(iter(FN))
    folded = False

    sample = add_stripe(fgimg, mask_name, bgimg) 
   
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
                va['-bgsel-'] = bgmenu[2]  # File
                bgmode = None
            fdi.flush_ev(wn)
        elif ev == '-bgc-':
            base = to_rgb(sg.popup_color('Select Base Color',
                                         default_color=base))
            fgc, bgc = bg_and_font(base)
            wn['-bgc-'].update(background_color=bgc, text_color=fgc)
            no = bgmenu.index(va['-bgsel-'])
            if no < 3:
                va['-bgsel-'] = bgmenu[3]  # Plain
            bgmode = None
            fdi.flush_ev(wn)
        
        elif ev == '-bgc2-':
            base2 = to_rgb(sg.popup_color('Select Base Color',
                                          default_color=base2))
            fgc2, bgc2 = bg_and_font(base2)
            wn['-bgc2-'].update(background_color=bgc2, text_color=fgc2)
            no = bgmenu.index(va['-bgsel-'])
            if no < 4:
                va['-bgsel-'] = bgmenu[4]  # Grad.
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
        if '-item-' in va:
            if va['-item-'] in FN:
                mask_name = va['-item-']
                
        scan_va(va, mask_name)
        getval(va['-sshift-'], 'shift', shift, 'shade', lo=0)
        getval(va['-salpha-'], 'alpha', alpha, 'shade', lo=0, hi=255)
        getval(va['-sblur-'], 'blur', blur, 'shade', lo=0)
        getval(va['-duty-'], 'duty', duty, 'common', lo=0.1)
        getval(va['-trns-'], 'trans', trans, 'common', lo=0, hi=255)
        
        if va['-bgsel-'] == bgmenu[3] and bgmode != bgmenu[3]:  # Plain
            # print('Plain selected')
            bgmode = bgmenu[3]
            wn['-fn1-'].update(bgind[3])
            addv = stoi(va['-badd-'])
            contrast = min(max(0,stoi(va['-bcont-'])),100)
            bgimg = plain_image(W, H, base=base, baseadd=addv,
                                contrast=contrast/100)
        elif va['-bgsel-'] == bgmenu[2]:  # File
            # print('File selected')
            if file_image is not None and bgmode != bgmenu[2]:
                bgmode = bgmenu[2]
                wn['-fn1-'].update(bgfile)
                bgimg = file_image
        elif va['-bgsel-'] == bgmenu[1]:  # BG
            # print('BG selected')
            if init_bgimg is not None and bgmode != bgmenu[1]:
                bgmode = bgmenu[1]
                wn['-fn1-'].update(bgind[1])
                bgimg = init_bgimg
        elif va['-bgsel-'] == bgmenu[0]:  # and bgmode != 'FG':
            # print('FG selected')
            bgmode = bgmenu[0]
            wn['-fn1-'].update(bgind[0])
            bgimg = fgimg.copy()
        else:  # any gradation
            if va['-bgsel-'] in (bgmenu[x+4] for x in range(3)):
                if bgmode != va['-bgsel-']:
                    no = bgmenu.index(va['-bgsel-'])
                    bgmode = bgmenu[no]
                    wn['-fn1-'].update(bgind[no])
                    addv = stoi(va['-badd-'])
                    contrast = min(max(0,stoi(va['-bcont-'])),100)
                    m = 'vhr'[no-4]
                    bgimg = grad_image(W, H, base=base, base2=base2,
                                       baseadd=addv, direction=m,
                                       contrast=contrast/100)

        wn['-bgsel-'].update(bgmode)
                
        if va['-swap-']:
              bg = fgimg
              fg = bgimg
        else:
              fg = fgimg
              bg = bgimg

        sample = add_stripe(fg, mask_name, bg)
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
