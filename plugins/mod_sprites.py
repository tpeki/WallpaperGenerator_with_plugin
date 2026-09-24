import random
import math
import copy
import os.path as pa
import TkEasyGUI as sg
import filedialog as fdi
import numpy as np
from PIL import Image, ImageFilter, ImageChops, ImageOps
from wall_common import *
from plugins import sub_sprites as sps

# --- 定数設定 ---
PATTERN_SIZE = 4
DELTA = 50
BGCOLOR1 = (1,1,0x99)
BGCOLOR2 = (1,1,1)
OLCOLOR = (0,0,0)
TINT = 100
BRIGHT = 100
OUTLINE = 0
STAR = 8

# --- 内部定数設定 ---
WIDTH = 1920
HEIGHT = 1080
DATA_DIR = 'samples'
ZIPFILE = 'sprites.zip'
DENSITY = 10
AA=2

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'スプライトまみれ',
                       {'color1':'背景色', 'color2':'背景色2',
                        'color3':'輪郭色',
                        'color_jitter':'彩度(%)', 'sub_jitter':'明度(%)',
                        'sub_jitter2':'星(0:OFF)',
                        'pwidth':'パターン拡大率', 'pheight':'間隔',
                        'pdepth':'輪郭幅(0:なし)'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BGCOLOR1)
    p.color2.itoc(*BGCOLOR2)
    p.color3.itoc(*OLCOLOR)
    p.color_jitter = TINT
    p.sub_jitter = BRIGHT
    p.sub_jitter2 = STAR
    p.pwidth = PATTERN_SIZE
    p.pheight = DELTA
    p.pdepth = OUTLINE
    return p

#スプライトデータの管理は sps.* (sub_sprites.py) に分離
sprite_preserv = {'data': sps.SpriteSet(),
                  'anglefix': None}

# -----
# 表示スプライトの選択
# -----
def checkboxes_by_set(spset: sps.SpriteSet):
    item_list = spset.list()
    list_h = max(5, math.ceil(len(item_list)/4))
    list_w = int((len(item_list)+list_h-1)/list_h)
    checks = []
    for x in item_list:
        ck = False
        if x in spset.enabled:
            ck = True
        item_check = sg.Checkbox(x, default=ck, group_id='item',
                                 key=f'-{x}_ck-')
        img = sps.get_sprite_by_name(x, spset)
        dx,dy = img.size
        item_img = sg.Image(data=img, key=f'-{x}_img-', size=(dx+1,dy+1))        

        checks.append([item_check, item_img])

    chk_lo = []
    for x in range(list_w):
        column = []
        for y in range(list_h):
            if len(item_list) <= (y+x*list_h):
                break
            tgt = checks[y+x*list_h]
            column.append([tgt[0], tgt[1]])

        chk_lo.append(sg.Column(layout=column, vertical_alignment='top',
                                expand_x=True, expand_y=True))
    return [chk_lo]
   

def select_items():
    if len(sprite_preserv['data'].sprites) < 1:
        return []
   
    checkboxes = checkboxes_by_set(sprite_preserv['data'])
    list_name = sprite_preserv['data'].name

    lo = [[sg.Frame(list_name, key='-frm-',
                    layout=checkboxes, relief='groove',
                    expand_x=True, expand_y=True)],
          [sg.Button('Select all', key='-all-'),
           sg.Button('Clear all', key='-clr-'),
           sg.Text(' ', expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Done', key='-ok-', background_color='#ddffdd'),
           ]]
    wn = sg.Window('Select disply items', layout=lo)
   
    while True:
        ev,va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            wn.close()
            break
        elif ev == '-ok-':
            sprite_preserv['data'].enabled = []
            for x in va['item']:
                sprite_preserv['data'].enabled.append(x[1:-4])
            wn.close()
            break
        elif ev == '-all-':
            for x in sprite_preserv['data'].sprites:
                wn[f'-{x}_ck-'].update(value=True)
        elif ev == '-clr-':
            for x in sprite_preserv['data'].sprites:
                wn[f'-{x}_ck-'].update(value=False)

        # print(ev,va)

    #print(f'checkbox end {va["item"]}')
    return va['item']
   

# -----
# デモ画像生成/表示
def sprite_preview():
    org_dic = sprite_preserv['data'].sprites
    enable_list = sprite_preserv['data'].enabled
    if len(enable_list) == 0:
        enable_list = sprite_preserv['data'].list()
        sprite_preserv['data'].enabled = enable_list

    extract_list = [k for k in enable_list if k in org_dic]
    if len(extract_list) == 0:
        return Image.new('RGB', (16,16), (0x44, 0x44, 0x44)), 1
    num = len(extract_list)
    max_h = 0
    max_w = 0
    images = {}
    for item in extract_list:
        pat = sps.sprite_pattern(item, sprite_preserv['data'])
        # print(item,'\n',pat)  #### check
        images[item] = sps.sprite_image(pat)
        tw,th = images[item].size
        if max_w < tw:
            max_w = tw
        if max_h < th:
            max_h = th

    ww = min(math.isqrt(num),30)
    if ww*ww < num:
        ww += 1
    hh = int(num/ww) if num % ww == 0 else int(num/ww) + 1
    maxwh = max(ww*(max_w+1),hh*(max_h+1))
    magnify = int(min(max(1, 640/maxwh),4))
   
    # print(f'num {num}: W{ww} x H{hh}')
    base = Image.new('RGB', (ww*(max_w+1)*magnify,hh*(max_h+1)*magnify),
                     (0x44, 0x44, 0x44))
    for i, (k, v) in enumerate(images.items()):
        im = v.resize(size=(v.width*magnify,v.height*magnify), resample=0)
        base.paste(im, (int(i%ww)*(max_w+1)*magnify,
                        int(i//ww)*(max_h+1)*magnify), im)
   
    return base, magnify


# -----
# スプライトセット設定
# -----
def desc(p: Param):
    """ 利用スプライトセットの選択、追加など
        (プラグイン時の設定画面)"""
    global sprite_preserv
    sprite_backup = copy.deepcopy(sprite_preserv['data'])

    files = sps.sprfile_list(DATA_DIR, ZIPFILE)
    preview_image, mag = sprite_preview()
    anglsw = sprite_preserv['anglefix'] is not None
    angle = sprite_preserv['anglefix'] if anglsw else 0
        

    lo = [[sg.Combo(files, key='-set-', readonly=True),
           sg.Button('Load',key='-fread-', background_color='#ddddff'),
           sg.Text('', expand_x=True),
           sg.Text('Angle Fix'),
           sg.Checkbox('', default=anglsw, key='-anglsw-'),
           sg.Input(str(angle), key='-angle-', size=(3,1)),
           sg.Text('', expand_x=True),
           sg.Text(f'Mag = x{mag}',key='-mag-')],
          [sg.Text(sprite_preserv['data'].desc, key='-sdesc-')],
          [sg.Image(data=preview_image, key='-prvw-',
                    size=preview_image.size)],
          [sg.Button('Pick Items', key='-sel-'),
           sg.Button('Import', key='-ins-', background_color='#ffffdd'),
           sg.Button('Purge', key='-del-', background_color='#ffdddd'),
           sg.Text('', expand_x=True),
           sg.Button('Dump', key='-dmp-', background_color='#ddddff'),
           sg.Button('Save', key='-sav-', background_color='#ddddff'),
           sg.Text('', expand_x=True),
           sg.Button('Cancel', size=(5,1), key='-can-',
                     background_color='#ffdddd'),
           sg.Button('Done', size=(5,1), key='-ok-',
                     background_color='#ddffdd'),
           ]]
    wn = sg.Window(sprite_preserv['data'].name, layout=lo,
                   element_justification='right')
    modf = False
    
    while True:
        ev,va = wn.read()
        
        if ev in (sg.WINDOW_CLOSED, '-can-'):
            modf = False
            break
        elif ev == '-ok-':
            if len(sprite_preserv['data'].sprites) > 0:
                break
            continue
        elif ev == '-fread-':
            fname = wn['-set-'].get()
            if fname == '':
                continue
            elif sps.INT_LABEL == fname:
                sprite_preserv['data'].load_internal()
            else:
                pdic, sdesc = sps.load_spr(fname, DATA_DIR, ZIPFILE)
                if len(pdic) == 0:
                    sprite_preserv['data'].load_internal()
                else:
                    sprite_preserv['data'].set_pattern(fname, pdic, desc=sdesc)
            wn['-sdesc-'].update(sprite_preserv['data'].desc)
            files = sps.sprfile_list(DATA_DIR, ZIPFILE)
            wn['-set-'].update(values=files)
            wn.refresh()
        elif ev == '-ins-':
            wn.hide()
            orgspr = copy.deepcopy(sprite_preserv['data'])
            result= sps.create_spr(sprite_preserv['data'], DATA_DIR)
            if result:
                sprite_preserv['data'] = result
            else:
                sprite_preserv['data'] = orgspr
            wn.un_hide()
        elif ev == '-del-':
            sprdata = sprite_preserv['data'].sprites
            if len(sprdata) == 0:
                continue
            last_key = next(reversed(sprdata))
            ans = fdi.yn_dialog('Purge Item', f'Delete {last_key}?', 'Sure')

            if ans:
                if len(sprdata) > 0:
                    sprite_preserv['data'].sprites.popitem()
                    sprite_preserv['data'].enabled.remove(last_key)
        elif ev == '-dmp-':
            outdir = DATA_DIR+pa.sep+sprite_preserv['data'].name
            ans = fdi.yn_dialog('Dump Item', f'Dump image to {outdir}', 'Dump')
            fdi.flush_ev(wn)
            if ans:
                sps.dump_sprites(outdir, sprite_preserv['data'])
        elif ev == '-sav-':
            if len(sprite_preserv['data'].sprites) == 0:
                continue
            fname = sprite_preserv['data'].name
            if fname == sps.INT_LABEL or fname == '':
                fname = 'temp'
            file = fdi.get_savefile(fname+'.spr',
                                    [('Sprite', '.spr'),],
                                    init_dir=DATA_DIR)
            fdi.flush_ev(wn)
            if file is not None and file != '':
                pdic = {}
                for key in sprite_preserv['data'].enabled:
                    if key in sprite_preserv['data'].sprites:
                        pdic[key] = sprite_preserv['data'].sprites[key]
                if len(pdic) == 0:
                    print(f'No pattern to save.')
                    continue

                set_name = sps.save_spr(file, pdic)
                if set_name:
                    sprite_preserv['data'].name = set_name
        elif ev == '-sel-':
            wn.hide()
            select_items()
            # print('Enabled: ',sprite_preserv['data'].enabled)
            wn.un_hide()
            fdi.flush_ev(wn)
        elif ev == '-anglsw-':
            anglsw = va['-anglsw-']

        modf = True
        img, mag = sprite_preview()
        wn['-prvw-'].update(data=img, size=img.size)
        wn['-mag-'].update(f'x{mag}')
        wn.refresh()

    sprite_preserv['anglefix'] = int(va['-angle-']) % 360 if anglsw else None
    wn.close()
    
    # if sprite_backup.name != sprite_preserv['data'].name:
    if modf:
        return generate(p)
    return


# -----
# モジュール動作
# -----
def outlined(image, width, border='#000000'):
    """輪郭強調"""
    width = min(max(width, 0), 10)
    if width == 0:
        return image
    contour = image.filter(ImageFilter.CONTOUR)
    bim = Image.new('RGB',image.size, border)
    if width ==1:
        mask = ImageOps.invert(contour.convert('L'))
    else:
        thick = contour
        for count in range(width-1):
            for dx,dy in [(1,0),(0,1)]:
                  shifted = ImageChops.offset(thick, dx, dy)
                  thick = ImageChops.darker(thick, shifted)
        mask = ImageOps.invert(thick.convert('L'))

    image.paste(bim, (0,0), mask)
    return image


def starfield(w, h, pixel, star_density=2, seed=None):
    """Galagaっぽい星背景"""
    rng = np.random.default_rng(seed)

    # 低解像度星マップ
    sw = w // pixel
    sh = h // pixel
    density = star_density / 10000

    stars = np.zeros((sh, sw, 4), dtype=np.uint8)

    mask = rng.random((sh, sw)) < density

    palette = np.array([0, 71, 151, 222], dtype=np.uint8)
    # galaga背景の星の色から

    r = rng.choice(palette, (sh, sw))
    g = rng.choice(palette, (sh, sw))
    b = rng.choice(palette, (sh, sw))

    black = (r == 0) & (g == 0) & (b == 0)

    while np.any(black):
        r[black] = rng.choice(palette, black.sum())
        g[black] = rng.choice(palette, black.sum())
        b[black] = rng.choice(palette, black.sum())
        black = (r == 0) & (g == 0) & (b == 0)

    stars[...,0] = r
    stars[...,1] = g
    stars[...,2] = b
    stars[...,3] = mask.astype(np.uint8) * 255

    # pwidth倍拡大
    stars = stars.repeat(pixel, axis=0).repeat(pixel, axis=1)

    return Image.fromarray(stars, "RGBA")


def generate(p: Param):

    ow, oh = p.width, p.height
    pat_size = p.pwidth
    delta = p.pheight
    density = DENSITY
    outline = p.pdepth
    tint = p.color_jitter
    bright = p.sub_jitter
    stars = p.sub_jitter2

    w = int(ow + p.pwidth*1.3 + delta*3)
    h = int(oh + p.pwidth*1.3 + delta*3)

    if sprite_preserv['data'].name == '':
        sprite_preserv['data'].load_internal()

    sprset = sprite_preserv['data']
    sprites = sprset.sprites
    activespr = sprset.enabled

    base = Image.new('RGBA',(w,h),0)

    # -----------------------------
    # sort large first
    # -----------------------------

    activespr_sorted = sorted(
        activespr,
        key=lambda s: max(sprset.size(s)),
        reverse=True
    )

    # -----------------------------
    # occupancy map (1/4)
    # -----------------------------

    scale = 4
    occ_w = w//scale
    occ_h = h//scale

    occ = np.zeros((occ_h,occ_w),dtype=bool)

    # -----------------------------
    # circle collision
    # -----------------------------

    def check_circle(cx,cy,r):

        cx = int(cx/scale)
        cy = int(cy/scale)
        r = int(r/scale)
        
        x0=max(cx-r,0)
        x1=min(cx+r+1,occ_w)

        y0=max(cy-r,0)
        y1=min(cy+r+1,occ_h)

        r2=r*r

        for y in range(y0,y1):
            dy=y-cy
            for x in range(x0,x1):
                dx=x-cx
                if dx*dx+dy*dy<=r2:
                    if occ[y,x]:
                        return True

        return False


    def draw_circle(cx,cy,r):

        cx = int(cx/scale)
        cy = int(cy/scale)
        r = int(r/scale)

        x0=max(cx-r,0)
        x1=min(cx+r+1,occ_w)

        y0=max(cy-r,0)
        y1=min(cy+r+1,occ_h)

        r2=r*r

        for y in range(y0,y1):
            dy=y-cy
            for x in range(x0,x1):
                dx=x-cx
                if dx*dx+dy*dy<=r2:
                    occ[y,x]=True


    # -----------------------------
    # average radius (density)
    # -----------------------------

    radii=[]

    for s in activespr_sorted:

        sw, sh = sprset.size(s)

        size = max(sw,sh)*pat_size
        r = size/2+delta

        radii.append(r)

    avg_r = sum(radii)/len(radii)
    avg_area = math.pi*avg_r*avg_r

    target_num = int((ow*oh)*density/avg_area)

    # -----------------------------
    # placement storage
    # -----------------------------

    placed = []
    placed_radius = []

    fail = 0
    fail_limit = target_num*3

    # -----------------------------
    # Blue Noise placement
    # -----------------------------

    while fail < fail_limit:

        ps = random.choice(activespr_sorted)

        sw,sh = sprset.size(ps)

        size = max(sw,sh)*pat_size
        r = size/2+delta

        # candidate count grows with density
        candidates = 8+len(placed)//20

        best = None
        best_score = -1e9

        for _ in range(candidates):

            px = random.uniform(r,w-r)
            py = random.uniform(r,h-r)

            if check_circle(px,py,r):
                continue

            if not placed:

                score=1e9

            else:

                score = min(math.hypot(px-x,py-y)-(r+pr)
                            for (x,y),pr in zip(placed,placed_radius))

            if score > best_score:

                best_score = score
                best = (px,py)

        if best is None:
            fail+=1
            continue

        fail=0

        px,py=best

        draw_circle(px,py,r)

        placed.append((px,py))
        placed_radius.append(r)

        if sprite_preserv['anglefix'] is None:
            theta = random.random()*360
        else:
            theta = sprite_preserv['anglefix']
            
        pat = sps.sprite_pattern(ps, sprite_preserv['data'])
        ssiz = (int(sw*pat_size), int(sh*pat_size))
        simg = sps.sprite_image(pat).resize(ssiz, resample=Image.NEAREST)

        p1 = simg.rotate(theta, expand=True, resample=Image.NEAREST)


        p1size = (int(px-p1.width/2), int(py-p1.height/2))
        base.paste(p1, p1size, p1)

    # -----------------------------
    # crop
    # -----------------------------

    ofsx=int((w-ow)/2)
    ofsy=int((h-oh)/2)

    base=base.crop((ofsx,ofsy,ow+ofsx,oh+ofsy))

    if outline > 0:
        base = outlined(base, outline, p.color3.ctox())

    base=sat_attenate(base,tint)
    base=bri_attenate(base,bright)

    if p.h_img is None:
        img = diagonal_gradient_rgb(ow,oh,p.color1,p.color2)
    else:
        img = p.bg(ow, oh)
    
    if stars > 0:
        star_img = starfield(ow, oh, pat_size, stars)
        img.paste(star_img,(0,0),star_img)

    img.paste(base,(0,0),base)

    return img

if __name__ == '__main__':
    if sprite_preserv['data'].name == '':
        sprite_preserv['data'].load_internal()
 
    p = Param()
    p = default_param(p)
    
    p.width = WIDTH
    p.height = HEIGHT
   
    img = generate(p)
    img.show()

