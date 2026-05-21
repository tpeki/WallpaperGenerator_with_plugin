import numpy as np
from PIL import Image, ImageDraw, ImageOps
import inspect
from wall_common import *
import TkEasyGUI as sg

"""mod_ivy  壁に蔦  被覆形状=grid を変えられるように
                    葉の形状=maskも何通りか"""

# ==========
WIDTH = 1920
HEIGHT = 1080

COLOR1 = '#106001'
COLOR_JITTER = 40
BGCOLOR = '#66543B'  # 煉瓦
MCOLOR = '#DCDCDC'  #モルタル
FUCHI = '#EDE1A8'  # 斑

ROT = 15

LEAFSIZE = 43
LEAFDIST = 130
BRICKSIZE = 71
BRICKPROP = 2

LEAF_DFL = 100

ivy_preserv = {'shapes': None,
               'grids': None,
               'mask': 'ivy',
               'grid': 'hangdown',
               }

# =========================
# 形状登録デコレータ
# =========================
SFN = {}  # 関数名: shapes
PFN = {}  # 関数名: planting patterns
DF = {}  # パラメータ名及びデフォルト値

# Shape (mask)
def regis(func):
    """
    関数の引数名を抽出して FN 辞書に登録するデコレータ
    """
    # inspectで引数名の一覧を取得（selfなどは除外される）
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # 2つ目まで(size, c)を除外
    params = params[2:]

    SFN[func.__name__] = func
    DF[func.__name__] = {
        p.name: p.default
        for p in params
        if p.default is not inspect._empty and type(p.default) != bool
    }

    return func

# grid (planting)
def regip(func):
    """
    関数の引数名を抽出して FN 辞書に登録するデコレータ
    """
    # inspectで引数名の一覧を取得（selfなどは除外される）
    sig = inspect.signature(func)
    params = list(sig.parameters.values())

    # 2つ目まで(W,H)を除外
    params = params[2:]

    PFN[func.__name__] = func
    DF[func.__name__] = {
        p.name: p.default
        for p in params
        if p.default is not inspect._empty
    }

    return func

# ==========
# wallpaper 基本
# ==========
# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'ツタの葉   間隔=10x',
                       {'color1':'葉っぱ', 'color2':'壁',
                        'color_jitter':'色ゆらぎ',
                        'sub_jitter':'揺れ角',
                        'pwidth':'粒度', 'pheight':'間隔',
                        'pdepth':'煉瓦サイズ'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1 = RGBColor(COLOR1)
    p.color2 = RGBColor(BGCOLOR)
    p.color_jitter = COLOR_JITTER
    p.sub_jitter = ROT
    p.pwidth = LEAFSIZE
    p.pheight = LEAFDIST
    p.pdepth = BRICKSIZE
    return p

# 詳細設定
def sg_modline(func, ftype):
    # ☑func    param[  ] ...
    # type(param) == bool の場合は無視
    if not ftype in ['sfn', 'pfn']:
        return None
    line = [sg.Radio('', key=f'-{ftype}_{func}-', group_id=ftype,
                     default=True if ivy_preserv['mask'] == func
                     or ivy_preserv['grid'] == func else False),
            sg.Text(func, size=(12,0))]

    dflt = DF[func]
    if len(dflt) == 0:
        line.append(sg.Text('No Parameters'))
        
    for par in dflt.keys():
        v = dflt[par]
        if type(v) == bool:
            continue
        elif type(v) == int:
            line.append(sg.Text(f'{par}[i]'))
        elif type(v) == float:
            line.append(sg.Text(f'{par}[f]'))
        else:
            continue

        if par in ivy_preserv['arglists'][func].keys():
            v = ivy_preserv['arglists'][func][par]
            
        line.append(sg.Input(f'{v}', key=f'-{func}_{par}-',width=4))

    #print(func, dflt, line )
    return line


def split_guikey(s):
    if s is None:
        return None, None
    
    if '_' in s:
        return (_.replace('-','') for _ in s.split('_'))
    
    return s.replace('-',''), None


def firstitem(v):
    if isinstance(v, (list, tuple)):
        if len(v) > 0:
            return v[0]
        else:
            return None
    else:
        return v

def desc(p: Param):
    slo = []
    for fn in ivy_preserv['shapes']:
        line = sg_modline(fn, 'sfn')
        if line is None:
            continue
        slo.append(line)
        
    plo = []
    for fn in ivy_preserv['grids']:
        line = sg_modline(fn, 'pfn')
        if line is None:
            continue
        plo.append(line)
        
    lo = [[sg.Frame('Shapes', layout=slo, relief='ridge', expand_x=True)],
          [sg.Frame('Grids', layout=plo, relief='ridge', expand_x=True)],
          [sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Apply', key='-ok-', background_color='#ddffdd'),
           ],
          ]
          
    curshape = ivy_preserv['mask']
    curgrid = ivy_preserv['grid']

    wn = sg.Window('mod_ivy config', layout=lo)

    while True:
        ev, va = wn.read()

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            change = False
            break
        if ev == '-ok-':
            change = True
            break

    for x in va.keys():
        if not '_' in x:
            continue
        fn, pn = split_guikey(x)
        if fn in ivy_preserv['shapes']+ivy_preserv['grids']:
            if pn in ivy_preserv['arglists'][fn]:
                ivy_preserv['arglists'][fn][pn] = float(va[x])
    wn.close()
    
    if change:
        #print(va)
        fn, pr = split_guikey(firstitem(va['sfn']))
        ivy_preserv['mask'] = pr if pr is not None else curshape
        fn, pr = split_guikey(firstitem(va['pfn']))
        ivy_preserv['grid'] = pr if pr is not None else curgrid
            
        #print(ivy_preserv)
        return generate(p)
    else:
        return


# =========================
# 保存パラメータがあれば返す
# =========================
def prevset(flag, name, value, lo=None, hi=None):
    if flag == 's':
        func = ivy_preserv['mask']
    else:
        func = ivy_preserv['grid']
        
    retv = (
        ivy_preserv['arglists']
        .get(func,{})
        .get(name, value)
        )
    
    if lo is not None:
        retv = max(lo, retv)
    if hi is not None:
        retv = min(retv, hi)
    
    return retv


# ==========
# 葉っぱ基本形
# ==========
def leafmask(size, c=COLOR1):
    y,x = np.ogrid[:size, :size]
    mask = (x**2 + y**2 <= size**2) & ((x-size)**2 + (y-size)**2 <= size**2)
    color = np.array(to_rgb(c), np.uint8)
   
    rgb = (mask[...,None] * color).astype(np.uint8)
    alpha = (mask * 255).astype(np.uint8)
   
    return Image.fromarray(np.dstack([rgb, alpha]), 'RGBA')
    r,g,b = to_rgb(c)
    vein = to_rgb([r*1.3, g*1.3, b*1.3])
    dr = ImageDraw.Draw(img)
    dr.line((size-1,0,0,size-1),width=2,fill=vein)

    return img
    

def leaf(size, c=COLOR1):
    r,g,b = to_rgb(c)
    vein = to_rgb([r*1.3, g*1.3, b*1.3])

    leaf = leafmask(size, c)
    dr = ImageDraw.Draw(leaf)
    dr.line((size-1,0,0,size-1),width=2,fill=vein)

    return leaf
    

def fuiri(size, c=COLOR1):
    r,g,b = to_rgb(c)
    vein = to_rgb([r*1.3, g*1.3, b*1.3])

    bright = int(0.2126*r + 0.7152*g + 0.0722*b)
    diff = 72 / bright
    r,g,b = 0xed, 0xe1, 0xa8  # FUCHI
    fuchi = to_rgb([r*diff, g*diff, b*diff])

    base = Image.new('RGBA', (size, size), (0,0,0,0))
    leafimg = leafmask(size, c)
    shrink = int(size*0.9)
    leafshrink = leafimg.resize((shrink,shrink),resample=Image.BICUBIC)
    dr = ImageDraw.Draw(leafshrink)
    dr.line((shrink-1,0,0,shrink-1),width=2,fill=vein)

    fu_color = Image.new('RGBA', (size, size), (*fuchi,255))
    base.paste(fu_color, (0,0), leafimg)
    
    dy = (size-shrink)//3
    dx = size-shrink-dy
    base.paste(leafshrink, (dx,dy), leafshrink)
    base = base.resize((size, size), resample=Image.LANCZOS)
    
    return base

# ==========
# 葉っぱ配置用
# ==========

# 笹の葉
@regis
def sasa(size, c=COLOR1, slant=5, child=0.9, fu=False):
    slant = prevset('s', 'slant', slant)
    child = prevset('s', 'child', child, 0.1, 1.0)
    
    if fu:
        c = rated_jitter(RGBColor(c), 40)
        leaf_s = fuiri(size, c)
    else:
        leaf_s = leaf(size, c)

    center = leaf_s.rotate(45, resample=Image.NEAREST, expand=True)

    left = leaf_s.rotate(slant, resample=Image.BILINEAR, expand=True)
    childz = int(size*child)
    left = left.resize((childz,childz), resample=Image.NEAREST)
    right = ImageOps.mirror(left)

    lx, ly = left.size
    px, py = topmost_nonzero_alpha(left)  # 描画があり、yが最小
    px = lx - px

    nx, ny = center.size
    l = max(nx, ny)
    if lx > l//2:
        l = lx*2

    base = Image.new('RGBA',(l,l),(0,0,0,0))
    base.paste(left, (l//2-lx+px, 0), left)
    base.paste(right, (l//2-px, 0), right)
    base.paste(center, ((l-nx)//2, 0), center)    

    base = base.resize((size, size), resample=Image.LANCZOS)
    return base

# 笹の葉 斑入り
@regis
def sasa2(size, c=COLOR1, slant=5, child=0.9):
    slant = prevset('s', 'slant', slant)
    child = prevset('s', 'child', child, 0.1, 1.0)
    
    return sasa(size, c, slant, child, fu=True)


# 蔦の葉
@regis
def ivy(size, c=COLOR1):
    leaf_s = leafmask(size)

    archi = leaf_s.rotate(45, resample=Image.NEAREST, expand=True)
    cx, cy = archi.size
    center = archi.resize((int(cx*1.5),cy), resample=Image.NEAREST)
    cx, cy = center.size

    cw = cx//2
    left = []
    for i, (r, s) in enumerate([(-60,0.75), (-30,0.85)]):
        timg = archi.rotate(r, resample=Image.NEAREST, expand=True)
        tx, ty = timg.size
        timg = timg.resize((int(tx*s), int(ty*s)), resample=Image.NEAREST)
        timg = timg.crop(timg.getbbox())
        tx, ty = timg.size
        px, py = topmost_nonzero_alpha(timg)
        left.append([timg, (px, py)])
        if cw < (tx-px):
            cw = tx-px

    base = Image.new('RGBA', (cw*2, cy), (0,0,0,0))
    dr = ImageDraw.Draw(base)

    for tim in left:
        tx,ty = tim[0].size
        px,py = tim[1]
        dx = cw-tx+(tx-px)
        dy = -py
        base.paste(tim[0],(dx,0),tim[0])
    rim = ImageOps.mirror(base)
    base.paste(rim,(0,0),rim)
    base.paste(center,((cw*2-cx)//2,0),center)
    dx = left[1][0].size[0] // 4
    dr.ellipse((cw-dx,-dx//3,cw+dx,dx//3),fill=(0,0,0,0))

    base = base.crop(base.getbbox())
    base = base.resize((size,size),resample=Image.LANCZOS)
    return base


# つつじっぽい
@regis
def azarea(size, c=COLOR1, division=6, number=5, density=1.6):
    n = int(prevset('s', 'division', division, 3, 20))
    number = int(prevset('s', 'number', number, 1, division))
    d = prevset('s', 'density', density, 0.5, 3.0)

    leaf_s = leafmask(size)

    img = Image.new('RGBA',(size*4,size*4),(0,0,0,0))
    img.paste(leaf_s, (int(size/d),int(size+size/d)),leaf_s)
    
    base = Image.new('RGBA',(size*4,size*4),(0,0,0,0))
    angle = 360 / n
    
    for x in range(number):
        r = img.rotate(angle*x, resample=Image.NEAREST, expand=False)
        base.paste(r,(0,0),r)

    base = base.crop(base.getbbox())
    base = base.resize((size,size),resample=Image.LANCZOS)
    return base
    

# ===========
# 葉っぱ描画支援
# ===========
def topmost_nonzero_alpha(img: Image.Image):
    arr = np.array(img)  # (H, W, 4) の RGBA 配列
    alpha = arr[..., 3]  # αチャンネルだけ取り出す

    ys, xs = np.where(alpha != 0)
    if len(ys) == 0:
        return None  # 全部透明

    # 最も y が小さい点のインデックス
    idx = np.argmin(ys)
    return int(xs[idx]), int(ys[idx])


def dlt(delta):
    return random.randint(-delta,delta)


# ==========
# 葉っぱ配置グリッド
# ==========
@regip
def pileup(W, H, *, offset=0.2):
    offset = prevset('p', 'offset', offset, 0.0, 1.0)
    grid = np.zeros((H, W), dtype=bool)

    leastw = int(W * offset)
    C = H / (W - leastw + 1e-6)**2

    for y in range(H):
        # covering では y=H→0 で描くので、反転値を使う
        y2 = H - y
        startx = int(np.sqrt(y2 / C))

        # startx から右側は「カバー領域」
        grid[y, startx:] = True

    return grid


@regip
def hangdown(W, H, *, xp=0.86, offset=0.13, alpha=80):
    xp = prevset('p', 'xp', xp, 0.0, 1.0)
    offset = prevset('p', 'offset', offset, 0.0, 1.0)
    alpha = prevset('p', 'alpha', alpha, 1, W)
    
    p=1.5
    xp = int(W * xp)

    xs = np.arange(W)
    dx = xs - xp

    # f(x) = exp(-( |dx/alpha|^p ))
    fx = np.exp(-np.abs(dx / alpha)**p)
    fx = offset + (1 - offset) * fx  # 0〜1
    heights = fx * H  # shape: (W,)

    # y座標（縦方向）
    ys = np.arange(H)[:, None]  # shape: (H,1)
    # grid[y,x] = y < heights[x]
    grid = ys < heights  # shape: (H,W), dtype=bool

    return grid


# ==========
# 葉っぱで覆う
# ==========
def covering(p: Param, T=5):
    """
    J: 葉っぱの色ゆらぎ
    lsize: 葉っぱサイズ
    D: カバー領域のステップ距離
    S: 葉っぱ個々の傾き量ゆらぎ
    T: 葉っぱ個々の縦横位置ゆらぎ
    RGB: lmaskをRGBで利用する場合True
    """
    ow,oh = p.width, p.height
    lsize = p.pwidth
    step = lsize//2
    color = p.color1
    J = p.color_jitter
    S = p.sub_jitter
    D = p.pheight / 100

    mask_name = ivy_preserv['mask']
    grid_name = ivy_preserv['grid']
  
    W,H = ow+step*4, oh+step*4
    img = Image.new('RGBA', (W,H), (0,0,0,0))

    lmask = SFN[mask_name](lsize*2, color.ctoi())
    
    if mask_name in ['sasa2']:  # colored masks
        RGB = True
        mask = lmask
    else:
        RGB = False
        mask = lmask.convert('L').point(lambda v: 255 if v > 0 else 0)

    mask = mask.crop(mask.getbbox())
    mask = mask.resize((lsize,lsize), resample=Image.BILINEAR)
    grid = PFN[grid_name](W, H)

    for y in range(H-1,0,-int(step*D)):
        line = Image.new('RGBA',(W,step*3),(0,0,0,0))
        
        for x in range(0, W-1, int(step*D)):
            if grid[y,x] == False:
                continue

            emask = mask.rotate(dlt(S), resample=Image.NEAREST, expand=True)
            if RGB:
                line.paste(emask,(x+dlt(T), dlt(T)),emask)
            else:
                c = rated_jitter(color, J).ctoi()
                colr = gradation(*emask.size, c)

                line.paste(colr,(x+dlt(T), dlt(T)),emask)

        img.paste(line, (step//2,y-step//2), line)
    return img.crop((step,step,ow+step,oh+step))


# ==========
# 単位葉っぱグラデーション
# ==========
def gradation(w, h, color, darken=0.5):
    y, x = np.ogrid[:h, :w]
    x_norm = x / (w - 1)
    y_norm = 1 - (y / (h - 1))
    coef = (x_norm + y_norm) / 2

    # 開始色と終了色
    start = np.array(color, dtype=np.float32)
    endc = list(int(b*darken) for b in color)
    end = np.array(endc, dtype=np.float32)

    # 補間
    rgb = (start + (end - start) * coef[...,None]).astype(np.uint8)
    #rgb = np.repeat(rgb, w, axis=1)
    alpha = np.full(rgb.shape[:2] + (1,), 255, dtype=np.uint8)
    rgba = np.dstack([rgb, alpha])

    return Image.fromarray(rgba, mode='RGBA')


# ==========
# レンガ塀
# ==========
def brick(W, H, bcolor, mcolor, brick, proportion=2, mortar=0.05):
    # レンガと目地のサイズ
    brick_w = brick   # レンガの幅
    brick_h = brick//proportion  # レンガの高さ
    mortar = max(int(brick*mortar), 2)  # モルタル幅

    mcolr = to_rgb(mcolor)  # 目地色(mcolor)
    bcolr = to_rgb(bcolor)  # レンガはbcolor

    # ベースは目地色
    img = np.full((H, W, 3), list(mcolr), dtype=np.uint8)

    # レンガ色aa503c
    brick_color = np.array(list(bcolr), dtype=np.uint8)

    # グリッド
    ys = np.arange(H).reshape(-1, 1)
    xs = np.arange(W).reshape(1, -1)

    # どのレンガ行か
    row_idx = ys // brick_h

    # 偶数行・奇数行でx方向のオフセットを変える（半分ずらす）
    offset = (row_idx % 2) * (brick_w // 2)

    # 各ピクセルの「レンガ内での座標」
    x_in_brick = (xs + offset) % brick_w
    y_in_brick = ys % brick_h

    # 目地部分かどうか
    is_mortar = (x_in_brick < mortar) | (y_in_brick < mortar)

    # 目地以外をレンガ色に塗る
    img[~is_mortar] = brick_color

    return Image.fromarray(img, mode='RGB')


# ==========
# generate
# ==========
def generate(p: Param):
    if ivy_preserv['shapes'] is None:
        ivy_preserv['shapes'] = list(SFN.keys())
        ivy_preserv['grids'] = list(PFN.keys())
        arglists = {}
        for k in ivy_preserv['shapes']+ivy_preserv['grids']:
            arglists[k] = DF[k].copy()
        ivy_preserv['arglists'] = arglists

    if ivy_preserv['mask'] is None:
        ivy_preserv['mask'] = ivy_preserv['shapes'][0]

    if ivy_preserv['grid'] is None:
        ivy_preserv['grid'] = ivy_preserv['grids'][0]

    W, H = p.width, p.height
    
    if p.h_img is not None:
        bg = p.bg().convert('RGBA')
    else:
        bcolor = p.color2
        mcolor = MCOLOR
        bsize = p.pdepth
        bg = brick(W, H, bcolor, mcolor, bsize)
    
    fg = covering(p)
    bg.paste(fg,(0,0),fg)

    return bg

# ==========
# TEST
# ==========
if __name__ == '__main__':
    p = Param()
    p = default_param(p)

    p.width = WIDTH
    p.height = HEIGHT

    img = generate(p)
    img.show()
