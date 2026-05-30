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
FLOWER = '#F7C7F2'

ROT = 15

LEAFSIZE = 43
LEAFDIST = 130
BRICKSIZE = 71
BRICKPROP = 2
FLOWER_P = 0

LEAF_DFL = 100

ivy_preserv = {'shapes': None,
               'flowers': None,
               'grids': None,
               'shape': 'ivy',
               'flower': 'horn',
               'grid': 'hangdown',
               'brick': True,
               'set': 'ivy',
               }

RECOMMEND = [['all', None, None],
             # index, shape, [flowers],
             ['ivy', ['ivy'], None],
             ['sasa', ['sasa', 'sasavarie'], None],
             ['tsutsuji', ['azarea'], ['pointedpetal', 'roundpetal']],
             ['asagao', ['asagao'], ['horn']],
             ['kanamemochi', ['holly'], ['leaves', 'roundpetal']],
             ['dokudami', ['fishmint'], ['cordata']],
             ['kinshibai', ['branch'], ['roundpetal']],
             ]

# =========================
# 形状登録デコレータ
# =========================
SFN = {}  # 関数名: shapes
FFN = {}  # 関数名: flowers
PFN = {}  # 関数名: planting patterns
DF = {}  # パラメータ名及びデフォルト値
COLORED = []  # 色付きshape

def reg(kind):
    def decorator(func):
        """
        関数の引数名を抽出して FN 辞書に登録するデコレータ
        """
        # inspectで引数名の一覧を取得（selfなどは除外される）
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if kind == 's':
            FN = SFN
            skip = 2  # 無視する引数の数
        elif kind == 'f':
            FN = FFN
            skip = 2
        elif kind == 'g':
            FN = PFN
            skip = 2
        else:
            return func

        FN[func.__name__] = func

        params = params[skip:]
        defaults = {}
        for p in params:
            if p.default is not inspect._empty and type(p.default) != bool:
                defaults[p.name] = p.default
            if p.name == 'RGB' and p.default is True:
                COLORED.append(func.__name__)
        DF[func.__name__] = defaults
        return func

    return decorator

# ==========
# wallpaper 基本
# ==========
# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'ツタの葉   間隔=10x',
                       {'color1':'葉っぱ', 'color2':'壁',
                        'color3':'花',
                        'color_jitter':'色ゆらぎ',
                        'sub_jitter':'揺れ角',
                        'sub_jitter2':'花',
                        'pwidth':'粒度', 'pheight':'間隔',
                        'pdepth':'煉瓦サイズ'})
    return module_name

# おすすめパラメータ
def default_param(p: Param):
    p.color1 = RGBColor(COLOR1)
    p.color2 = RGBColor(BGCOLOR)
    p.color3 = RGBColor(FLOWER)
    p.color_jitter = COLOR_JITTER
    p.sub_jitter = ROT
    p.sub_jitter2 = FLOWER_P
    p.pwidth = LEAFSIZE
    p.pheight = LEAFDIST
    p.pdepth = BRICKSIZE
    return p

# 詳細設定
def sg_modline(func, ftype, enf):
    # ☑func    param[  ] ...
    # type(param) == bool の場合は無視
    """cur = [ivy_preserv['shape'],
           ivy_preserv['flower'],
           ivy_preserv['grid']
           ]
    """
    line = [sg.Radio('', key=f'-{ftype}_{func}-', group_id=ftype,
                     default=True if func == enf else False),
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
            isint = True
        elif type(v) == float:
            line.append(sg.Text(f'{par}[f]'))
            isint = False
        else:
            continue

        if par in ivy_preserv['arglists'][func].keys():
            v = ivy_preserv['arglists'][func][par]
            if isint:
                v = int(v)
           
        line.append(sg.Input(f'{v}', key=f'-{func}_{par}-',width=5))

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

def recommend_items(name):
    if name.lower() == 'all':
        shapes = ivy_preserv['shapes'].copy()
        flowers = ivy_preserv['flowers'].copy()
        return shapes, flowers
    
    for rec, shapes, flowers in RECOMMEND:
        if rec == name:
            return shapes, flowers

    return None, None


def set_layout(name):
    recommend_names = [r[0] for r in RECOMMEND]
    if name in recommend_names:
        shapes, flowers = recommend_items(name)
    else:
        shapes, flowers = None, None

    dfl_sha = ivy_preserv['shape']
    if shapes is not None:
        dfl = dfl_sha if dfl_sha in shapes else shapes[0]
        slo = make_cat_layout(shapes, 'sfn', dfl)
    else:
        slo = make_cat_layout(ivy_preserv['shapes'], 'sfn', dfl_sha)
        
    dfl_flo = ivy_preserv['flower']
    if flowers is not None:
        dfl = dfl_flo if dfl_flo in flowers else flowers[0]
        flo = make_cat_layout(flowers, 'ffn', dfl)
    else:
        flo = make_cat_layout(ivy_preserv['flowers'], 'ffn', dfl_flo)

    return slo, flo


def make_cat_layout(funcs, cat, enf):
    """cat in ['sfn', 'ffn', 'gfn'], enf==enabled"""
    lo = []
    for fn in funcs:
        line = sg_modline(fn, cat, enf)
        if line:
            lo.append(line)
    return lo


def desc(p: Param):
    rec = ivy_preserv['set']
    slo, flo = set_layout(rec)
    glo = make_cat_layout(ivy_preserv['grids'], 'gfn', ivy_preserv['grid'])
    recommend_names = [r[0] for r in RECOMMEND]

    while True:
        retv = desc_(p, slo, flo, glo, rec)
        if isinstance(retv, str):
            if retv in recommend_names:
                rec = retv
                slo, flo = set_layout(retv)
            continue
        else:
            return retv
    return None    


def desc_(p: Param, slo, flo, glo, rec):
     
    recommend_names = [r[0] for r in RECOMMEND]
    
    lo = [[sg.Frame('Shapes', layout=slo, relief='ridge', expand_x=True)],
          [sg.Frame('Flowers', layout=flo, relief='ridge', expand_x=True)],
          [sg.Frame('Grids', layout=glo, relief='ridge', expand_x=True)],
          [sg.Checkbox('Brick', default=ivy_preserv['brick'], key='-brick-'),
           sg.Text('Shape set', width=20, text_align='right'),
           sg.Combo(recommend_names, default_value=rec,
                       readonly=True, key='-recommend-',
                       enable_events=True),
           sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Apply', key='-ok-', background_color='#ddffdd'),
           ],
          ]
         
    current = [['sfn', 'shape', ivy_preserv['shape']],
               ['ffn', 'flower', ivy_preserv['flower']],
               ['gfn', 'grid', ivy_preserv['grid']]
               ]

    wn = sg.Window('mod_ivy config', layout=lo, grab_anywhere=True)

    while True:
        ev, va = wn.read()

        if ev == '-can-' or ev == sg.WINDOW_CLOSED:
            change = False
            break
        if ev == '-ok-':
            change = True
            break
        if ev == '-recommend-':
            change=False
            break

    wn.close()
   
    if change:
        for x in va.keys():
            if not '_' in x:
                continue
            fn, pn = split_guikey(x)
            if fn in (ivy_preserv['shapes']
                      +ivy_preserv['flowers']
                      +ivy_preserv['grids']):
                if pn in ivy_preserv['arglists'][fn]:
                    ivy_preserv['arglists'][fn][pn] = float(va[x])
        #print(va)
        for ent,lbl,cur in current:
            fn, pr = split_guikey(firstitem(va[ent]))
            ivy_preserv[lbl] = pr if pr is not None else cur

        ivy_preserv['brick'] = va['-brick-'] == True
        ivy_preserv['set'] = rec
           
        #print(ivy_preserv)
        return generate(p)
    elif ev == '-recommend-':
        return va['-recommend-']
    else:
        return


# =========================
# 保存パラメータがあれば返す
# =========================
def prevset(flag, name, value, lo=None, hi=None):
    if flag == 's':
        func = ivy_preserv['shape']
    elif flag == 'f':
        func = ivy_preserv['flower']
    elif flag == 'g':
        func = ivy_preserv['grid']
    else:
        return 0 if lo is None else lo
       
    argdict = ivy_preserv['arglists'].get(func,{})
    retv = argdict.get(name, value)

    if lo is not None:
        retv = max(lo, retv)
    if hi is not None:
        retv = min(retv, hi)

    t = DF[func].get(name, None)
    if isinstance(t, int):
        retv = int(retv)

    argdict[name] = retv
   
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

    """r,g,b = to_rgb(c)
    vein = to_rgb([r*1.3, g*1.3, b*1.3])
    dr = ImageDraw.Draw(img)
    dr.line((size-1,0,0,size-1),width=2,fill=vein)

    return img"""
   

def leaf(size, c=COLOR1):
    r,g,b = to_rgb(c)
    vein = to_rgb([r*1.3, g*1.3, b*1.3])

    leaf = leafmask(size, c)
    dr = ImageDraw.Draw(leaf)
    dr.line((size-1,0,0,size-1),width=2,fill=vein)

    return leaf
   

def fuiri(size, c=COLOR1, srate=0.8):
    r,g,b = to_rgb(c)
    vein = to_rgb([r*1.3, g*1.3, b*1.3])

    bright = int(0.2126*r + 0.7152*g + 0.0722*b)
    diff = 72 / bright
    r,g,b = 0xed, 0xe1, 0xa8  # FUCHI
    fuchi = to_rgb([r*diff, g*diff, b*diff])

    base = Image.new('RGBA', (size, size), (0,0,0,0))
    leafimg = leafmask(size, c)
    shrink = int(size*srate)
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
@reg('s')
def sasa(size, c=COLOR1, slant=5, child=90, RGB=False):
    slant = prevset('s', 'slant', slant)
    child = prevset('s', 'child', child, 1, 100)/100.0
   
    if RGB:
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
@reg('s')
def sasavarie(size, c=COLOR1, slant=5, child=90, RGB=True):
    slant = prevset('s', 'slant', slant)
    child = prevset('s', 'child', child, 1, 100)
   
    return sasa(size, c, slant, child, RGB=True)


# 蔦の葉
@reg('s')
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
@reg('s')
def azarea(size, c=COLOR1, div=6, number=5, density=1.6):
    n = prevset('s', 'div', div, 3, 20)
    number = prevset('s', 'number', number, 1, div)
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
   

# モチノキ クロオガネモチ、カナメモチ
@reg('s')
def holly(size, c=COLOR1, cluster=3):
    cluster = prevset('s', 'cluster', cluster, 1, 5)

    leaf = leafmask(size)
    shk = size//int((cluster+2)/3+1)
    leaf = leaf.rotate(45, expand=True)
    leaf = leaf.resize((shk,shk),resample=Image.NEAREST)
    left = leaf.rotate(-30, resample=Image.BICUBIC, expand=True)
    left = left.crop(left.getbbox())
    right = ImageOps.mirror(left)
    lx,ly = left.size
       
    base = Image.new('RGBA',(size,size*2),(0,0,0,0))
    xc = size // 2
    #dr = ImageDraw.Draw(base)
   
    for x in range(cluster):
        r = right if x%2 else left
        posx = xc if (x%2) else xc-lx
        posy = int((x / cluster) * (size / 2))
        base.paste(r,(posx,posy),r)
        #dr.rectangle((posx,posy,posx+lx,posy+ly),outline='#3333ff',width=2)

    base = base.crop(base.getbbox())
    r = size/base.width
    base = base.resize((size, int(base.height*r)), resample=Image.LANCZOS)
   
    return base
   
# 朝顔
@reg('s')
def asagao(size, c=COLOR1, cluster=2):
    cluster = prevset('s', 'cluster', cluster, 1, 10)
   
    leaf_s = leafmask(size)
    leaf_s = leaf_s.rotate(45,resample=Image.NEAREST,expand=True)
    sx,sy = leaf_s.size

    leaf_s = leaf_s.resize((int(leaf_s.width*0.75),leaf_s.height),
                           resample=Image.NEAREST)
    sx,sy = leaf_s.size
    cut = sy/3

    subleaf = leaf_s.resize((int(sx//1.8),int(sy//2.3)), resample=Image.NEAREST)
    subleaf = subleaf.rotate(-55,resample=Image.NEAREST,expand=True)
    subleaf = subleaf.crop(subleaf.getbbox())
    ssx,ssy = subleaf.size

    base = Image.new('RGBA',(sx*3,sy*2),(0,0,0,0))
    bx,by = base.size

    dx = int(bx/2-ssx*0.9)
    dy = int(ssy/2)
    base.paste(subleaf, (dx,dy), subleaf)
    right = ImageOps.mirror(subleaf)
    rx = int(bx/2-ssx*0.1)
    base.paste(right, (rx,dy), right)
    base.paste(leaf_s,((bx-sx)//2,0),leaf_s)
   
    dr = ImageDraw.Draw(base)
    dr.rectangle((0,0,bx,dy), fill=(255,0,0,0))
    dr.ellipse((int(bx*0.46),0,int(bx*0.54),int(dy*1.3)),fill=(0,0,0,0))

    base = base.crop(base.getbbox())
    base = base.rotate(-35, resample=Image.BICUBIC, expand=True)

    #base.show()
    bx,by = base.size
    b2 = [base.copy(), ImageOps.mirror(base)]

    clus = Image.new('RGBA', (int(bx*2)+1,int(by*(cluster+1))+1), (0,0,0,0))
    dr = ImageDraw.Draw(clus)
    for i in range(cluster):
        dx = int(bx * (i%2) / 2)
        dy = int(by * i / 2)
       
        clus.paste(b2[i%2],(dx,dy),b2[i%2])

    clus = clus.crop(clus.getbbox())
    r = size/max(clus.width, clus.height)
    clus = clus.resize((int(clus.width*r),int(clus.height*r)),
                       resample=Image.LANCZOS)

    return clus


@reg('s')
def fishmint(size, c=COLOR1):
    """どくだみ"""
    S = int(size * 1.1)
    color = to_rgb(c)
    
    y, x = np.mgrid[0:S, 0:S]

    x = (x - S/2) / (S/2)
    y = (y - S/2) / (S/2)

    circle1 = (x + 0.35)**2 + (y + 0.2)**2 < 0.45**2
    circle2 = (x - 0.35)**2 + (y + 0.2)**2 < 0.45**2

    triangle = (y > -0.1) & (np.abs(x) < (1.2 - y) * 0.5)

    mask = (circle1 | circle2 | triangle).astype(np.float32)
    
    rgb = (mask[...,None] * color).astype(np.uint8)
    alpha = (mask * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]), 'RGBA')


@reg('s')
def branch(size, c=COLOR1, length=3, step=15, phase=0.0):
    length = prevset('s', 'length', length, 1, 10)
    step = int(prevset('s', 'step', step, 1, 100)/100 * size)
    phase = prevset('s', 'phase', phase, 0.0, 1.0)
    color = to_rgb(c)
    
    lf = leaf(size//4)
    lx = lf.width
    bl = (length+1)*step+lx
    base = Image.new('RGBA',(bl,bl),(0,0,0,0))

    for i in range(length):
        p = step*i+lx
        base.paste(lf, (p, p-lx), lf)
        p2 = int(step*(i+phase)+lx)
        base.paste(lf, (p2-lx, p2), lf)
        
    el = lf.rotate(85, resample=Image.NEAREST, expand=False)
    base.paste(el,(0,0),el)
    bx = base.width
    dr = ImageDraw.Draw(base)
    dr.line((*el.size, p2, p2), width=1, fill=color)
    base_n = base.rotate(dlt(8)+37, resample=Image.BICUBIC, expand=True)
    base_n = base_n.resize((int(bx*0.8),int(bx*0.8)),resample=Image.NEAREST)
    nx = base_n.width

    base.paste(base_n,((bx-nx)//2,(bx-nx)//2),base_n)
    base = base.crop(base.getbbox())

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


# ===========
# 花マスク(色付き)
# ===========
@reg('f')
def horn(size, c=FLOWER):
    bcol =  rated_jitter(RGBColor(c),10)

    blossom = Image.new('RGBA',(size, size),(0,0,0,0))
    dr = ImageDraw.Draw(blossom)
    dr.polygon((size//5, size//4, size//2,size, size*4//5, size//4),
               fill=bcol.ctoi())

    flair = Image.new('L',(size, size//2),0)
    dr = ImageDraw.Draw(flair)
    dr.ellipse((0,0,size-1,size//2), fill=255)

    bcol2 =  brightness(bcol, f=1.6)
    msk = rad_grad(size,size//2, bcol2, bcol, center=(size//2,size//2),
                   rmed=0.2, power2=0.6)
    blossom.paste(msk,(0,0),flair)

    blossom = blossom.rotate(180+dlt(60), resample=Image.BILINEAR, expand=True)
    blossom = blossom.crop(blossom.getbbox())
    r = size/max(blossom.width, blossom.height)
    blossom = blossom.resize((int(blossom.width*r),int(blossom.height*r)),
                             resample=Image.LANCZOS)

    return blossom

@reg('f')
def roundpetal(size, c=FLOWER, petals=5, gradation=100, floret=10):
    size = int(size*0.7)
    bcol =  rated_jitter(RGBColor(c),10).ctoi()
    gradation = int(prevset('f', 'gradation', gradation))/100.0
    n = int(prevset('f', 'petals', petals, 3, 6))
    floret = prevset('f', 'floret', floret, 25, 50)
   
    mask = Image.new('L',(size, size), 0)
    
    petal = Image.new('L',(size, size), 0)
    dr = ImageDraw.Draw(petal)
    psize = int(size/2.5)
    dr.ellipse(((size-psize)//2,0,(size-psize)//2+psize, psize),
               fill=255)

    angle = 360 // n
    for n in range(n):
        p = petal.rotate(n*angle, expand=False)
        mask.paste(p,(0,0),p)

    W,H = mask.size
    if gradation != 0:
        brigt = brightness(RGBColor(bcol),f=gradation)
    else:
        brigt = bcol
    if gradation < 0:
        rgb = rad_grad(W, H, bcol, brigt, rmed=0.7, power2=2.0)
    else:
        rgb = rad_grad(W, H, brigt, bcol)

    base = Image.new('RGBA', (W,H), (0,0,0,0))
    base.paste(rgb, (0,0), mask)
    
    return drawfloret(base, floret)


def drawfloret(img, floret):
    sr = int(img.width*floret/100)

    fimg = Image.new('L',(sr,sr), 0)
    dr = ImageDraw.Draw(fimg)
    dr.ellipse((0,0,sr,sr), fill=255)

    scol = rated_jitter(RGBColor(240, 240, 64),20)
    dark = brightness(scol, s=1.6)
    rgb = rad_grad(sr, sr, dark, scol, rmed=0.8)

    w, h = img.size
    img.paste(rgb,((w-sr)//2,(h-sr)//2,(w+sr)//2,(h+sr)//2), fimg)

    return img
   

@reg('f')
def daisy(size, c=FLOWER, petals=14, gradation=100, floret=20):
    size = int(size*0.9)
    bcol =  rated_jitter(RGBColor(c),10).ctoi()
    n = int(prevset('f', 'petals', petals, lo=3))
    gradation = int(prevset('f', 'gradation', gradation))/100.0
    floret = int(prevset('f', 'floret', floret, 10, 50))
   
    r = np.pi*size/(3.4*n)  # 花弁先端の円弧半径 (2πr/n)/2 = 2*π*size/2/n/2
    xc = size // 2
    x0,y0 = xc,xc
    x1, y1 = int(xc - r), int(r)
    x2, y2 = int(xc + r), y1

    pt = Image.new('L',(size,size),0)
    dr = ImageDraw.Draw(pt)
    dr.pieslice((x1,0,x2,r*2),start=180,end=0,fill=255)
    dr.polygon((x0,y0,x1,y1,x2,y2),fill=255)

    mask = Image.new('L',(size,size),0)
    for i in range(n):
        q = pt.rotate(i*360/n, expand=False)
        mask.paste(q,(0,0),q)

    W,H = mask.size
    if gradation != 0:
        brigt = brightness(RGBColor(bcol),f=gradation)
    else:
        brigt = bcol
    if gradation < 0:
        rgb = rad_grad(W, H, bcol, brigt, rmed=0.3, power2=2.0)
    else:
        rgb = rad_grad(W, H, brigt, bcol)

    base = Image.new('RGBA', (W,H), (0,0,0,0))
    base.paste(rgb, (0,0), mask)

    return drawfloret(base, floret)    


@reg('f')
def cordata(size, c=FLOWER, spike=65):
    """ドクダミ spike:穂状花序のsizeとの比率"""
    spike = int(prevset('f', 'spike', spike, 10)/100.0 * size)
    base = Image.new('RGBA',(size,size),(0,0,0,0))

    # bract(苞)
    bract = daisy(size, c=c, petals=4, gradation=1, floret=10)
    bract = bract.crop(bract.getbbox())
    bw,bh = bract.size
    bc = size-bw//2
    base.paste(bract, (size-bw,size-bh,size,size), bract)

    # spike(穂状花序)
    dr = ImageDraw.Draw(base)
    scol = rated_jitter(RGBColor('#e8e820'),20).ctoi()
    sr = spike//2  # 花序弧半径(≒花序長さ)
    sx = bc-sr
    #sy = bc
    sw = int(size*0.11)//2  # 花序太さ
    dr.arc((sx-sr+sw,bc-sr,sx+sr+sw,bc+sr), start=-60, end=0,
           fill=scol, width=sw*2)
    dr.circle((sx+sr,bc), sw, fill=scol)
    dr.circle((int(sx+sr*0.6),int(bc-sr*0.866+sw)),  # cos(60), sin(60)を調整
              sw, fill=scol)

    return base


@reg('f')
def pointedpetal(size, c=FLOWER, petals=5, weight=1.7, stimen=2):
    bcol =  rated_jitter(RGBColor(c),10).ctoi()
    n = prevset('f', 'petals', petals, lo=3)
    weight = prevset('f', 'weight', weight, 1E-6, 2.0)
    stimen = prevset('f', 'stimen', stimen, 2, 5)
   
    # マスク作成
    cx = size//2
    R = size * 0.45
    r = R * (np.cos(2*np.pi/n) / np.cos(np.pi/n)) * weight
   
    outer = np.linspace(0, 2*np.pi, n, endpoint=False)
    inner = outer + np.pi / n

    angles = np.empty(2*n)
    angles[0::2] = outer
    angles[1::2] = inner
    radii  = np.array([R, r] * n)
    xs = cx + radii * np.cos(angles)
    ys = cx + radii * np.sin(angles)

    P = np.stack([xs, ys], axis=1)
    A = P
    B = np.roll(P, -1, axis=0)

    X, Y = np.meshgrid(np.arange(size), np.arange(size))
    X = X[..., None]  # (H,W,1)
    Y = Y[..., None]
   
    # XOR で内外判定
    cond1 = ((A[:,1] > Y) != (B[:,1] > Y))  # 条件1 辺がYを跨ぐか(偶奇ルール)
    xints = (B[:,0] - A[:,0]) * \
            (Y - A[:,1]) / (B[:,1] - A[:,1] + 1e-12) + A[:,0]  # 交点
    cond2 = X < xints  # 条件2 交点が左側にあるか
    mask = np.logical_xor.reduce(cond1 & cond2, axis=2)

    mask = Image.fromarray(mask.astype(np.uint8)*255, 'L')
    W,H = mask.size
    dark = brightness(RGBColor(bcol),f=0.6)
    rgb = rad_grad(W, H, dark, bcol, rmed=0.4)

    base = Image.new('RGBA', (W,H), (0,0,0,0))
    base.paste(rgb, (0,0), mask)

    st = Image.new('RGBA',base.size,(0,0,0,0))
    drw = ImageDraw.Draw(st)
    cx = base.width//2
    l = int(cx * 0.40)
    darker = brightness(RGBColor(bcol),f=0.3).ctoi()
    drw.arc((cx-l,cx,cx+l,cx+2*l), start=200, end=270,
           fill=darker, width=2)
    for i in range(stimen):
        ss = st.rotate((i-stimen//2)*10)
        base.paste(ss,(i*2,i*2),ss)
   
    return base

# 葉(色違い)
@reg('f')
def leaves(size, c=FLOWER, cluster=3):
    cluster = prevset('s', 'cluster', cluster, 1, 3)
    bcol =  rated_jitter(RGBColor(c),10).ctoi()

    leaf = leafmask(size)
    leaf = leaf.convert('L').point(lambda v: 255 if v > 0 else 0)
    shk = size//int((cluster+2)/3+1)
    leaf = leaf.rotate(45, expand=True)
    leaf = leaf.resize((shk,shk),resample=Image.NEAREST)
    leaf = leaf.crop(leaf.getbbox())
   
    base = Image.new('L',(size,size),0)
    xc = size//2
   
    for i in range(cluster):
        # 0 = 0, 1 = -30 , 2=+30  0,-1,1
        angle = -(i%2)*60 + 30 if i>0 else 0
        lt = leaf.rotate(angle, resample=Image.BICUBIC, expand=True)
        lt = lt.crop(lt.getbbox())
        dx = lt.width * (i%2) if i>0 else lt.width//2
        dy = (cluster-i-1)*lt.height//8
        base.paste(lt,(xc-dx,dy),lt)

    base = base.crop(base.getbbox())
    h = int(base.height*size/base.width)
    base = base.resize((size, h), resample=Image.LANCZOS)

    colr = gradation(size, h, bcol)
    img = Image.new('RGBA',(size, h),(0,0,0,0))
    img.paste(colr, (0,0), base)

    return img
   

# ==========
# 葉っぱ配置グリッド
# ==========
@reg('g')
def pileup(W, H, *, cover=40, offset=0):
    cover = prevset('g', 'cover', cover, 0, 100)/100.0
    offset = prevset('g', 'offset', offset, 0, 100)/100.0
    grid = np.zeros((H, W), dtype=bool)

    leastw = int(W * cover)
    B = int(H * offset)
    h = H - B
    if h == 0:
        return np.ones((H, W), dtype=bool)

    C = h / (W - leastw + 1e-6)**2
    ys = np.arange(h)[:, None]
    y2 = h - np.arange(h)
    startx = np.sqrt(y2 / C).astype(int)
    xs = np.arange(W)[None, :]
    grid[:h, :] = xs >= startx[:, None]

    # 下側を wobble 付きで塗る
    jit=int(H*0.1)
    wobbles = wobble(W, jitter=jit).astype(int)
    boundaries = np.clip(h - jit + wobbles, 0, H)
    grid |= np.arange(H)[:, None] >= boundaries[None, :]
   
    return grid


@reg('g')
def hangdown(W, H, *, xp=88, offset=63, alpha=110, reach=1.25):
    xp = prevset('g', 'xp', xp, 0, 100)/100.0
    offset = prevset('g', 'offset', offset, 0, 100)/100.0
    alpha = prevset('g', 'alpha', alpha, 1, W)
    reach = prevset('g', 'reach', reach, lo=1E-2)

    p = 1.5
    xp = int(W * xp)

    xs = np.arange(W)
    dx = xs - xp

    # f(x) = exp(-( |dx/alpha|^p ))
    fx = np.exp(-np.abs(dx / alpha)**p) * reach
    fx = offset + (1 - offset) * fx  # 0〜1
    heights = fx * H  # shape: (W,)

    wobbles = wobble(W, jitter=50)

    # y座標（縦方向）
    ys = np.arange(H)[:, None]  # shape: (H,1)
    # grid[y,x] = y < heights[x]
    grid = ys < (heights+wobbles)  # shape: (H,W), dtype=bool

    return grid


@reg('g')
def arch(W, H, *, xp=82, radius=30, width=40):
    """xp: 中心位置、radius: 上部の短径、width: ゲート幅＝長径"""
    xp = prevset('g', 'xp', xp, 0, 100)/100.0
    radius = prevset('g', 'radius', radius, 0, 100)/100.0
    width = prevset('g', 'width', width, 1, W)/100.0

    # 中心 x 座標
    xc = int(W * xp)
    sr = int(H * radius)
    lr = int(W * width)//2

    # 全体 True
    grid = np.ones((H, W), dtype=bool)

    # 座標
    xs = np.arange(W)[None, :]      # shape (1, W)
    ys = np.arange(H)[:, None]      # shape (H, 1)

    # 半楕円の中心 y（上に配置したいので b を上に取る）
    yc = sr

    # --- 半楕円領域 ---
    # ((x-xc)/a)^2 + ((y-yc)/b)^2 <= 1 かつ y <= yc
    ellipse = ((xs - xc) / lr)**2 + ((ys - yc) / sr)**2 <= 1
    ellipse &= (ys <= yc)

    # --- 下の長方形領域 ---
    rect = (ys > yc) & ((xc- lr) < xs) & (xs < (xc+ lr))

    # False を埋める
    grid[ellipse | rect] = False

    return grid


@reg('g')
def wobblyrect(W, H, *, leftp=30, rightp=100, topp=20, bottomp=100, jitter=100):
    min_thickness=1
    left = int(prevset('g', 'leftp', leftp, lo=-100, hi=100)/100.0 * W)
    top = int(prevset('g', 'topp', topp, lo=-100, hi=100)/100.0 * H)
    right = int(prevset('g', 'rightp', rightp, lo=-100, hi=100)/100.0 * W)
    bottom = int(prevset('g', 'bottomp', bottomp, lo=-100, hi=100)/100.0 * H)
    jitter = prevset('g', 'jitter', jitter, lo=0)

    left = max(W + left, 0)     if left < 0   else min(left, W-1)
    top = max(H + top, 0)       if top < 0    else min(top, H-1)
    right = max(W + right, 0)   if right < 0  else min(right, W-1)
    bottom = max(H + bottom, 0) if bottom < 0 else min(bottom, H-1)
    # 基準矩形が逆転しないように整える
    left, right = sorted((left, right))
    top, bottom = sorted((top, bottom))

    #jitter = min(jitter, lx, ly, W - 1 - rx, H - 1 - ry)
    #jitter = max(jitter, 0)
   
    xs = np.arange(W)[None, :]   # shape (1, W)
    ys = np.arange(H)[:, None]   # shape (H, 1)

    top_w = wobble(W, jitter=jitter)
    bot_w = wobble(W, jitter=jitter)
    top_x = np.clip(np.rint(top + top_w - jitter / 2).astype(int), 0, H - 1)
    bottom_x = np.clip(np.rint(bottom + bot_w - jitter / 2).astype(int), 0, H - 1)

    left_w = wobble(H, jitter=jitter)
    right_w = wobble(H, jitter=jitter)
    left_y = np.clip(np.rint(left + left_w - jitter / 2).astype(int), 0, W - 1)
    right_y = np.clip(np.rint(right + right_w - jitter / 2).astype(int), 0, W - 1)

    # 逆転防止
    bottom_x = np.maximum(bottom_x, top_x + min_thickness)
    right_y = np.maximum(right_y, left_y + min_thickness)

    bottom_x = np.clip(bottom_x, 0, H - 1)
    right_y = np.clip(right_y, 0, W - 1)

    # 内部判定
    inside = (
        (ys >= top_x[None, :]) & (ys <= bottom_x[None, :]) &
        (xs >= left_y[:, None]) & (xs <= right_y[:, None])
    )

    return inside


def wobble(W, jitter=20):
    c = 9
    noise = np.random.randn(W)
    noise = np.convolve(noise, np.ones(c)/c, mode='same')
    wob = ((noise - noise.min()) / (noise.max() - noise.min()+ 1e-6) * jitter)
   
    return wob    



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
    flower = p.color3
    J = p.color_jitter
    S = p.sub_jitter
    D = p.pheight / 100
    flw = min(p.sub_jitter2,100)

    mask_name = ivy_preserv['shape']
    flower_name = ivy_preserv['flower']
    grid_name = ivy_preserv['grid']
 
    W,H = ow+step*4, oh+step*4
    img = Image.new('RGBA', (W,H), (0,0,0,0))

    lmask = SFN[mask_name](lsize*2, color.ctoi())
    fmask = FFN[flower_name](lsize, flower.ctoi())
   
    if mask_name in COLORED:  # colored masks
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

            if random.randint(0,100) < flw:
                emask = fmask.rotate(dlt(S), resample=Image.BICUBIC,
                                     expand=True)
                line.paste(emask,(x+dlt(T), dlt(T)),emask)
            else:
                emask = mask.rotate(dlt(S), resample=Image.NEAREST,
                                    expand=True)
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


def rad_grad(w, h, color1, color2, center=None,
             inner=0.0, outer=1.0, power=1.0, rmed=0.5, power2=None):
    color1 = to_rgb(color1)
    color2 = to_rgb(color2)
    if power2 is None:
        power2 = power
   
    if center is None:
        center = (w//2, h//2)
    cx,cy = center
   
    xs = np.arange(w)[None,:]
    ys = np.arange(h)[:,None]
    dx,dy = xs-cx, ys-cy
    dist = np.sqrt(dx*dx+dy*dy)
    maxd = np.sqrt((max(cx, w-cx))**2 + (max(cy, h-cy))**2)

    x = np.clip(dist/maxd, 0, 1)
    r2 = np.clip(rmed, 1e-6, 1-1e-6)
    t = np.empty_like(x)

    mask = x < r2
    t[mask] = ((x[mask]/r2)**power) * r2
    t[~mask] = r2 + (((x[~mask]-r2)/(1-r2))**power2) * (1-r2)

    g = inner + (outer - inner) * t
    g = g[..., None]

    c1 = np.array(color1, dtype=np.float32)
    c2 = np.array(color2, dtype=np.float32)
    rgb = (c1 * (1 - g) + c2 * g).astype(np.uint8)

    return Image.fromarray(rgb, 'RGB')

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
        ivy_preserv['flowers'] = list(FFN.keys())
        ivy_preserv['grids'] = list(PFN.keys())
        arglists = {}
        for k in (ivy_preserv['shapes']
                  +ivy_preserv['flowers']
                  +ivy_preserv['grids']):
            arglists[k] = DF[k].copy()
        ivy_preserv['arglists'] = arglists

    if ivy_preserv['shape'] is None:
        ivy_preserv['shape'] = ivy_preserv['shapes'][0]

    if ivy_preserv['grid'] is None:
        ivy_preserv['grid'] = ivy_preserv['grids'][0]

    W, H = p.width, p.height
   
    if p.h_img is not None:
        bg = p.bg().convert('RGBA')
    elif ivy_preserv['brick']:
        bcolor = p.color2
        mcolor = MCOLOR
        bsize = p.pdepth
        bg = brick(W, H, bcolor, mcolor, bsize)
    else:
        bcolor = rgb_random_jitter(p.color2, p.color_jitter)
        bg = Image.new('RGBA',(W,H),bcolor.ctoi())
   
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
