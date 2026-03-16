import re
import numpy as np
from PIL import Image, ImageDraw
import random
import math
import copy
import glob
import os
import os.path as pa
import TkEasyGUI as sg
from filedialog import *
from wall_common import *

# --- 定数設定 ---
PATTERN_SIZE = 4
DENSITY = 10
DELTA = 50
BGCOLOR1 = (1,1,0x99)
BGCOLOR2 = (1,1,1)
TINT = 100
STAR = 8

# --- 内部定数設定 ---
WIDTH = 1920
HEIGHT = 1080
MAX_SIZE = (64,64)
DATA_DIR = 'samples'
AA=2

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'スプライトまみれ',
                       {'color1':'背景色', 'color2':'背景色2',
                        'color_jitter':'彩度', 'sub_jitter2':'星(0:OFF)',
                        'pwidth':'パターン拡大率', 'pheight':'間隔',
                        'pdepth':'密度(微調整)'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BGCOLOR1)
    p.color2.itoc(*BGCOLOR2)
    p.color_jitter = TINT
    p.sub_jitter2 = STAR
    p.pwidth = PATTERN_SIZE
    p.pheight = DELTA
    p.pdepth = DENSITY
    return p


#スプライトデータ形式(SJIS)：
#ファイルのベース名をセット名として扱う
#内蔵データの場合は'--internal--'をセット名とする
#複数のスプライト定義を1ファイルに格納して良い
#  
#----- スプライト定義
#"["<パターン名>"]"\n
#<width>, <height>\n
#<bit pattern1>[, <bit pattern2> ...],<color1>[, <color2> ...]\n
#   <<bit pattern繰り返し>>
#
#colorは #rrggbb の文字列で指定する
#bit patternとcolorは同数であること
#bit pattern無しでcolorにコマンドを記載可能
#コマンド：
#,turnover  そこまでのビットパターンを逆順で繰り返す
#  eg. 0x18,#ff0000\n0x24,#ff00ff\n,turnover ==
#        0x18,#ff0000\n0x24,#ff00ff\n0x24,#ff00ff\n0x18,#ff0000\n
#,rep<n>  直前のパターンをn行繰り返す
#  eg. 0xc6,#ff0000\n,rep2\n == 0xc6,#ff0000\n0xc6,#ff0000\n0xc6,#ff0000\n
#
# 行頭に#がある行、空行は読み飛ばし


INT_LABEL = '--internal--'
INTERNAL_SET = {
    'pacman':[
        (16,16),
        [0, '#000000'],
        [0x07c0, '#ffff00'],
        [0x1fc0, '#ffff00'],
        [0x3f80, '#ffff00'],
        [0x3f00, '#ffff00'],
        [0x7e00, '#ffff00'],
        [0x7c00, '#ffff00'],
        [[0x7800, 0x0006],['#ffff00', '#ffb8ae']],
        [[0x7c00, 0x0006],['#ffff00', '#ffb8ae']],
        [0x7e00, '#ffff00'],
        [0x3f00, '#ffff00'],
        [0x3f80, '#ffff00'],
        [0x1fc0, '#ffff00'],
        [0x07c0, '#ffff00'],
        [0, '#000000'],
        [0, '#000000'],
        ],
    'akabee':[
        (16,16),
        [0, '#000000'],
        [0x03c0, '#ff0000'],
        [0x0ff0, '#ff0000'],
        [0x1ff8, '#ff0000'],
        [[0x39e4, 0x0618],['#ff0000', '#ffffff']],
        [[0x30c0, 0x0f3c],['#ff0000', '#ffffff']],
        [[0x30c0, 0x0c30, 0x030c],['#ff0000', '#ffffff', '#2121ff']],
        [[0x70c2, 0x0c30, 0x030c],['#ff0000', '#ffffff', '#2121ff']],
        [[0x79e6, 0x0618],['#ff0000', '#ffffff']],
        [0x7ffe, '#ff0000'],
        [None, 'rep3'],
        [0x7bde, '#ff0000'],
        [0x318c, '#ff0000'],
        [0, '#000000'],
        ],
    'cherry':[
        (16,16),
        [0, '#000000'],
        [0, '#000000'],
        [0x000c, '#de9751'],
        [0x003c, '#de9751'],
        [0x00d0, '#de9751'],
        [0x0110, '#de9751'],
        [[0x1c00, 0x0220], ['#ff0000', '#de9751']],
        [[0x3b00, 0x0440], ['#ff0000', '#de9751']],
        [[0x3eb0, 0x0040], ['#ff0000', '#de9751']],
        [[0x2db8, 0x1000, 0x0040], ['#ff0000', '#ffffff', '#de9751']],
        [[0x35f8, 0x0800], ['#ff0000', '#ffffff']],
        [[0x1d78, 0x0080], ['#ff0000', '#ffffff']],
        [[0x01b8, 0x0040], ['#ff0000', '#ffffff']],
        [0x00f0, '#ff0000'],
        [0, '#000000'],
        [0, '#000000'],
        ],
    }        

# 共有データクラス(preserv)定義
class SpriteSet:
    def __init__(self):
        self.name=''
        self.sprites = {}
        self.enabled = []
       
    def load_internal(self):
        self.sprites = copy.deepcopy(INTERNAL_SET)
        self.name = INT_LABEL
        self.enabled = list(INTERNAL_SET.keys())

    def set_pattern(self, name, patterndic):
        self.sprites = patterndic
        self.name = name
        self.enabled = list(patterndic.keys())

    def list(self):
        return list(self.sprites.keys())
   
    def get(self, label):
        if label in self.list():
            return self.sprites[label]
        else:
            return None

    def size(self, label):
        if label in self.list():
            return self.sprites[label][0]
        else:
            return (0,0)

sprite_preserv = SpriteSet()

# -----
# 汎用サポート関数
# -----
DIGIT_RE = re.compile(r'\d+')

# ファイル名サニタイズ
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

def sanitize_filename(name):
    name = name.strip()
    path, basename = pa.split(name)
    base, ext = pa.splitext(basename)

    base = re.sub(r'[\\/:*?"<>|]', '', base)
    if base.upper() in RESERVED_NAMES:
        base = f"{base}_"

    return path+pa.sep+base+ext

def sanitize_dirname(name):
    drv, path = pa.splitdrive(name)
    p = path.split('\\')
    path = '\\'.join([x+'_' if x.upper() in RESERVED_NAMES else x for x in p])

    return drv+path


# 文字列 -> 数値変換 (16進考慮)
def to_int(s):
    try:
        val = int(s)
    except ValueError:
        if isinstance(s, str):
            val = int(s,0)
        else:
            val = 0
    return val

# -----
# スプライト形式ファイル読込
# -----
# 文字列の内容をtupleに
def strtotuple(s: str):
    '''","区切りで2要素以上、数値か"#"で始まる色文字列
        ただし、1要素目が空文字列の場合2要素目はコマンド文字列
        1要素目,2要素目がlistもしくはtupleの場合もあり'''
    s = s.replace('[','').replace(']','')
    dat = [_.strip() for _ in s.split(',')]
    if len(dat) < 2:
        return None

    if dat[0] is None or dat[0] == '':  # extract command: 'turnover' or 'repeat'
        return (None,dat[1].lower())

    # print('------ s', s[:min(len(s),80)], 'dat[:4]  ',dat[:4])

    intp = []
    strp = []
    for itm in dat:
        itm = itm.replace("'",'').replace('"','')
        try:
            v = int(itm, 0)
            intp.append(v)
        except ValueError:
            if len(itm) > 0 and itm[0] == '#':
                strp.append(itm)

    if len(strp) == 0 and len(intp) == 2:
        return (intp[0], intp[1])

    num = min(len(intp), len(strp))
    if num == 1:
        retv = (intp[0], strp[0])
    elif num == 0:
        if len(strp) > 0:
            retv = (0,strp[0])
        else:
            print(f'Error: num=0 / intp {intp}, strp {strp}')
            raise ValueError('Encode string to tuple')
    else:
        retv = (intp[:num], strp[:num])

    return retv

def load_spr(file:str):
    '''テキストファイルからSPR形式のデータを読み込んでスプライトデータに'''
    file = sanitize_filename(file)
    pdic = {}
    if not pa.exists(file):
        dirname, basename = pa.split(file)
        base, ext = pa.splitext(basename)
        if pa.exists(dirname+base+'.spr'):
            file = dirname+base+'.spr'
        elif pa.exists(DATA_DIR+pa.sep+base+'.spr'):
            file = DATA_DIR+pa.sep+base+'.spr'
        else:
            return pdic

    with open(file, mode='r', encoding='sjis') as f:
        source = f.read().splitlines()
    # print(f'FILE = {file}')

    spr_name = None
    ptn = []
    w,h = None, None
   
    for line in source:
        if len(line) == 0 or line[0] == '#':  # 空行、コメント行は飛ばす
            continue
       
        if line[0] == '[':  # 最初は [スプライト名]
            if spr_name is not None:
                if len(ptn) > 0:
                    pdic[spr_name] = ptn
                    ptn = []
                    w,h = None, None
                    spr_name = None
            if len(line) > 1:
                spr_name = line[1:].split(']')[0]
                # print(f'OBJECT:{spr_name}')
        if spr_name is None:
            continue  # 名前が無ければ登録データにならない

        #### 1行変換部分はbitmap->sprite と共用できないか

        data = strtotuple(line)
        if data is None:
            continue

        if len(ptn) == 0:  # 先頭データであれば 幅、高さ
            try:
                w, h = int(data[0]),int(data[1])
                ptn.append((w,h))
                continue
            except ValueError:
                w, h = 16, 16
                ptn.append((w,h))
                continue
        if data[0] is None or data[0] == '':  # extract command: 'turnover' or 'repeat'
            ptn.append((None, data[1].lower()))
            continue
       
        ptn.append(data)

    if len(ptn) > 1 and spr_name is not None:
        pdic[spr_name] = ptn

    return pdic    


# -----
# スプライト形式保存
# -----
def dtos(data):
    if data is None:
        return ''
    elif isinstance(data, (tuple,list)):
        d = []
        for x in data:
          d.append(dtos(x))  
        return ','.join(d)
    elif isinstance(data, str):
        return data
    elif data < 10:
        return f'{data:d}'
    else:
        return f'0x{data:x}'

def compress(buf):
    if len(buf) < 2:
        return buf

    out = [buf[0]]
    last = buf[0]
    rep = 0
    for line in buf[1:]:
        if line == last:
            rep += 1
        else:
            if rep > 0:
                out.append(f',rep{rep}')
                rep = 0
            out.append(line)
            last = line

    if rep > 0:
        out.append(f',rep{rep}')

    return out
   
   
def save_spr(file:str):
    file = sanitize_filename(file)
    file = pa.splitext(file)[0]+'.spr'
    set_name = pa.splitext(pa.split(file)[1])[0]
    sprite_preserv.name = set_name
    pdic = {}
    for key in sprite_preserv.enabled:
        if key in sprite_preserv.sprites:
            pdic[key] = sprite_preserv.sprites[key]
    if len(pdic) == 0:
        print(f'No pattern to save.')
        return

    with open(file, mode='w', encoding='sjis') as f:
        f.write(f'# SET_NAME = {set_name}\n')
        for item in pdic:
            f.write(f'[{item}]\n')
            buffer = []
            for line in pdic[item]:
                buffer.append(dtos(line))
            buffer = compress(buffer)
            f.write('\n'.join(buffer)+'\n')
    print(f'{file} : wrote {len(pdic.keys())} records')
    return


# -----
# ビットマップで保存(dump)
# -----
def dump_sprites(outdir):
    outdir = sanitize_dirname(outdir)
    if not pa.isdir(outdir):
        if not pa.exists(outdir):
            os.mkdir(outdir)
        else:
            print('Already exists file "{outdir}", not dir!')
            return

    enable_list = sprite_preserv.enabled
    extract_list = [k for k in enable_list if k in sprite_preserv.list()]
    for item in extract_list:
        pat = sprite_pattern(item)
        img = sprite_image(pat)
        
        file = sanitize_filename(item+'.png')
        img.save(outdir+pa.sep+file)
        
    return


# -----
# ビットマップから読込
# -----
# ライン当たり色数の制限
def reduce_cpr(img, colors_per_row, method=1):
    '''ビットマップを行当たりN色に減色'''
    if img.mode != 'RGB':
        img = img.convert('RGB')

    w,h = img.size
    #img = img.convert('P', palette=Image.ADAPTIVE,
    #                  colors=colors_per_row*h).convert('RGB')

    # 画像を読み込んでRGBのNumPy配列にする
    img_array = np.array(img)
   
    height, width, _ = img_array.shape

    # 各行に対して処理
    for y in range(height):
        # 1. NumPyのスライスで1行取り出し、一旦PIL画像に戻す
        row_data = img_array[y:y+1, :, :]
        row_img = Image.fromarray(row_data)

        # 2. 減色処理 (この部分はPILの高速なC実装を利用)
        # method=2 (Fast Octree) などを使うとさらに高速
        row_reduced = row_img.quantize(colors=colors_per_row,
                                       method=2).convert('RGB')

        # 3. 減色後のデータをNumPy配列として元の配列へ書き戻す
        img_array[y:y+1, :, :] = np.array(row_reduced)

    # 最終結果を画像として保存
    result_img = Image.fromarray(img_array)
    result_img = result_img.quantize(16).convert('RGB')  # 全色数を制限
    return result_img


def conv_spr(img, transparent_color):
    '''ビットマップをスプライト文字列に変換
        透過色は #rrggbb形式で指定'''
    transparent_color = transparent_color.upper()

    w, h = img.size
    text = [f'{w},{h}']

    img_array = np.array(img.convert('RGB'))
    ccnt = []

    for y in range(h):
        row = img_array[y]

        cd = []
        idx = []
        # --- palette index生成 ---
        for r, g, b in row:
            ctext = f'#{r:02X}{g:02X}{b:02X}'
            if ctext not in cd:
                if len(cd) > 15:
                    ctext = transparent_color
                else:
                    cd.append(ctext)
                if ctext not in ccnt:
                    ccnt.append(ctext)
            idx.append(cd.index(ctext))
        idx = np.array(idx)

        # --- bit pattern ---
        pd = []
        for c in range(len(cd)):
            if cd[c] == transparent_color:
                continue

            mask = (idx == c)

            q = 0
            for b in mask:
                q = (q << 1) | int(b)

            pd.append(f'0x{q:X}')

        # --- 出力 ---
        if len(pd) == 0:
            text.append(f'0,{transparent_color}')
        elif len(pd) == 1:
            if transparent_color in cd:
                cd.remove(transparent_color)
            text.append(f'{pd[0]},{cd[0]}')
        else:
            if transparent_color in cd:
                cd.remove(transparent_color)
            text.append(f'{pd},{cd}')

    return text


# 追加画面パレット
def palette_extract(img, max_colors=16):
    '''画像から使用色(上位16色まで)を抽出'''
    pals = img.getcolors()
    if pals is None:
        return []
    pal_sorted = sorted(pals, key=lambda x: x[0], reverse=True)
    return [rgb for count, rgb in pal_sorted[:max_colors]]


def palette_draw(palette, trans=None):
    '''パレット画像生成'''
    pimg = Image.new('RGB',(164, 44))  # (8*20+4, 2*20+4)
    pd = ImageDraw.Draw(pimg)

    if isinstance(trans, int) and trans < len(palette):
        trans = palette[trans]

    for i,col in enumerate(palette):
        x = (i%8)*20+4
        y = (i//8)*20+4
        pd.rectangle((x, y, x+16, y+16), fill=col)

        ol = (255,0,0) if trans == col else (0,0,0)
        pd.rectangle((x-2, y-2, x+18, y+18), outline=ol, width=2)

    return pimg

def palette_img(img, trans=None):
    palette = palette_extract(img)
    pimg = palette_draw(palette, trans)

    return pimg, palette
    

# プレビュー画面生成
def update_preview(wn, img, cpr, trans):
    rimg = reduce_cpr(img, cpr)
    wn['-prvw-'].update(data=rimg)
    
    palette = palette_extract(rimg)
    pimg = palette_draw(palette, trans=trans)
    wn['-tcpal-'].update(data=pimg)
    
    return rimg, palette

def check_transparent(wn, palette, trans):
    if trans not in palette:
        tc = len(palette)-1
        # print(f'-> Transparent={palette[tc]}')
        pimg = palette_draw(palette, tc)
        wn['-tcpal-'].update(data=pimg)
        wn['-tcol-'].update(rgb_string(palette[tc]))
        return False
    return True

def create_spr():
    global sprite_preserv
    sidebar = [[sg.Text('SPRITE SET '),
                sg.Text(sprite_preserv.name,
                        size=(20,1),key='-setname-')],
               [sg.Text('ID'),
                sg.Input('', size=(12,1), key='-name-')],
               [sg.Text('Color/Row '),
                sg.Input('8', size=(2,1), key='-cpr-')],
               [sg.Text('Transparent '),
                sg.Text('#000000', size=(8,1), key='-tcol-')],
               [sg.Image(size=(164,44), key='-tcpal-', enable_events=True)],
               ]

    lo = [[sg.Image(size=(272,240),key='-prvw-'),
           sg.Frame('', layout=sidebar, relief='groove',
                    vertical_alignment='top')],
          [sg.Text('',size=(20,1), key='-fname-'),
           sg.Button('Read File', key='-import-'),
           sg.Button('Reduce Color', key='-redc-'),
           sg.Text('',expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Register', key='-ok-', background_color='#ddffdd'),
           ]]

    img = None
    cpr = 8
    trans = (0,0,0)
    pcols = []
    orgspr = copy.deepcopy(sprite_preserv.sprites)
   
    wn = sg.Window('Import bitmap', layout=lo,)

    while True:
        ev,va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            sprite_preserv.sprites = copy.deepcopy(orgspr)
            break
        elif ev == '-ok-':
            nname = wn['-name-'].get()
            if nname !='' and \
               nname not in sprite_preserv.list():
                pattern = conv_spr(img, rgb_string(trans))
                # print(nname,' Pattern:', pattern[3])
                pat = []
                for itm in pattern:
                    dat = strtotuple(itm)
                    pat.append(dat)

                sprite_preserv.sprites[nname] = pat
                sprite_preserv.enabled.append(nname)
                # print(f"'{nname}': {pat}")
            break
        elif ev == '-redc-':
            ncpr = to_int(wn['-cpr-'].get())
            if ncpr != cpr and (0 < ncpr <= 16):
                cpr = ncpr
                rimg, pcols = update_preview(wn, img, cpr, trans)
                check_transparent(wn, pcols, trans)
            continue                
        elif ev == '-import-':
            fname = get_openfile('', filetypes=[('Bitmap','.png;.jpg;.bmp;.gif;.ico'),
                                           ('any', '.*')])
            if fname is not None and fname != '':
                img = Image.open(fname)
                w,h = [min(64,_) for _ in img.size]  # 最大64ドット四方に制限
                img = img.resize((w,h))  # crop((0,0,w,h)) resizeかcropか
                img = img.quantize(colors=16).convert('RGB')
                wn['-fname-'].update(pa.splitext(pa.split(fname)[1])[0])
                cpr = to_int(wn['-cpr-'].get())
                trans = to_rgb(wn['-tcol-'].get())
                rimg, pcols = update_preview(wn, img, cpr, trans)
                check_transparent(wn, pcols, trans)
                name = pa.splitext(pa.split(fname)[1])[0]
                wn['-name-'].update(name)
   
            continue
        elif ev == '-tcpal-' and va['event_type'] == 'mousedown':
            x, y = [int((t-4)/20) for t in get_pos(str(va['event']))]
            # print(f'Pal pos= ({x},{y})')
            if 0<=x<=7 and 0<=y<=1:
                pno = y*8+x
                if pno < len(pcols):
                    trans = pcols[pno]
                    wn['-tcol-'].update(rgb_string(trans))
                    pimg = palette_draw(pcols, pno)
                    wn['-tcpal-'].update(data=pimg)
                   
        #print(ev,va)

    wn.close()
    return


# -----
# スプライトパターン操作
# -----
def and_pat(orig, pat, n):
    '''多値パターン文字列に畳み込み'''
    c = f'{n:X}'[-1:]
    if len(orig) < len(pat):
        orig = orig.ljust(len(pat),'0')[:len(pat)]
    elif len(orig) > len(pat):
        pat = pat.ljust(len(orig),'0')[:len(orig)]

    ol = list(orig)
    for i in range(len(pat)):
        if pat[i] != '0':
            ol[i] = c
    return ''.join(ol)

def sprite_pattern(name:str):
    if name not in sprite_preserv.sprites:
        return []
    
    spr=[]

    data = sprite_preserv.get(name)
    w,h = data[0]
    body = data[1:]
    
    for r in body:        
        va,ca = r
        
        if va is None or va == '':  # コマンド行
            if not isinstance(ca, str):
                continue
            cmd = ca.lower()
            
            if 'turnover' in cmd:
                q = len(spr)
                for i in range(q):
                    #print(q,i, spr)
                    spr.append(spr[q-i-1])
                break

            if 'rep' in cmd:
                if not spr:
                    continue

                r = DIGIT_RE.search(cmd)
                rep = int(r.group()) if r else 1
                rep = min(rep, h-len(spr))
                last = spr[-1]

                spr.extend([last]*rep)
            continue
        
        else:  # パターン行
            if isinstance(va, (tuple,list)):
                if len(ca) < len(va):
                    ca.extend( ['#000000']*(len(va) - len(ca)))
                    
                vl = '0'*w
                cl = []
                
                for i,(v,c) in enumerate(zip(va,ca),1):
                    st = f'{v:b}'[-w:].zfill(w)
                    vl = and_pat(vl, st, i)
                    cl.append(c)
                spr.append((vl,cl))
            else:
                spr.append((f'{va:b}'.zfill(w), ca))
           
    if len(spr) < h:  # サイズに満たない場合透明行でfillする
        dummy = ('0'*w, '#000000')
        spr.extend([dummy]*(h-len(spr)))

    return spr[:h]

# -----
# スプライトビットマップ生成
# -----
def draw_oneline(dr, p, colors, y):
    '''1行分の処理'''
    if isinstance(colors, str):
        colors = [colors]
    for x in range(len(p)):
        if p[x] != '0':
            c = colors[(int(p[x],16)-1) % len(colors)]
            dr.point((x,y),fill=c)
    return


def sprite_image(pat: list):
    '''スプライト内部データをビットマップに変換'''
    img = Image.new('RGBA', (len(pat[0][0]),len(pat)), 0)
    dr = ImageDraw.Draw(img)

    y = 0
    for line in pat:
        pat, colors = line
        draw_oneline(dr, pat, colors, y)
        y += 1
    return img


# -----
# 表示スプライトの選択
# -----
def get_sprite_by_name(name:str):
    if name not in sprite_preserv.list():
        return Image.new('RGB',(8,8),0)
    pat = sprite_pattern(name)
    return sprite_image(pat)

def checkboxes_by_set(spset: SpriteSet):
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
        img = get_sprite_by_name(x)
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
    if len(sprite_preserv.sprites) < 1:
        return []
   
    checkboxes = checkboxes_by_set(sprite_preserv)
    list_name = sprite_preserv.name

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
            sprite_preserv.enabled = []
            for x in va['item']:
                sprite_preserv.enabled.append(x[1:-4])
            wn.close()
            break
        elif ev == '-all-':
            for x in sprite_preserv.sprites:
                wn[f'-{x}_ck-'].update(value=True)
        elif ev == '-clr-':
            for x in sprite_preserv.sprites:
                wn[f'-{x}_ck-'].update(value=False)

        # print(ev,va)

    #print(f'checkbox end {va["item"]}')
    return va['item']
   

# -----
# デモ画像生成/表示
def sprite_preview():
    org_dic = sprite_preserv.sprites
    enable_list = sprite_preserv.enabled
    if len(enable_list) == 0:
        enable_list = sprite_preserv.list()
        sprite_preserv.enabled = enable_list

    extract_list = [k for k in enable_list if k in org_dic]
    if len(extract_list) == 0:
        return Image.new('RGB', (16,16), (0x44, 0x44, 0x44)), 1
    num = len(extract_list)
    max_h = 0
    max_w = 0
    images = {}
    for item in extract_list:
        pat = sprite_pattern(item)
        # print(item,'\n',pat)  #### check
        images[item] = sprite_image(pat)
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
def sprfile_list(directory=DATA_DIR):
    '''スプライトデータファイルの取得'''
    files = [pa.splitext(pa.split(fn)[1])[0] \
             for fn in glob.glob(directory+pa.sep+'*.spr')]
    files.append(INT_LABEL)
    return files


def desc(p: Param):
    ''' 利用スプライトセットの選択、追加など
        (プラグイン時の設定画面)'''
    global sprite_preserv
    sprite_backup = copy.deepcopy(sprite_preserv)

    files = sprfile_list()
    preview_image, mag = sprite_preview()

    lo = [[sg.Combo(files, key='-set-', readonly=True),
           sg.Button('Load',key='-fread-', background_color='#ddddff'),
           sg.Text('', expand_x=True),
           sg.Text(f'x{mag}',key='-mag-')],
          [sg.Image(data=preview_image, key='-prvw-',
                    size=preview_image.size)],
          [sg.Button('Pick Items', key='-sel-'),
           sg.Button('Import', key='-ins-', background_color='#ffffdd'),
           sg.Button('Purge', key='-del-', background_color='#ffdddd'),
           sg.Text('', expand_x=True),
           sg.Button('Dump', key='-dmp-', background_color='#ddddff'),
           sg.Button('Save', key='-sav-', background_color='#ddddff'),
           sg.Text('', expand_x=True),
           sg.Button('Done', size=(4,1), key='-ok-',
                     background_color='#ddffdd')
           ]]
    wn = sg.Window(sprite_preserv.name, layout=lo,
                   element_justification='right')
    while True:
        ev,va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-ok-':
            break
        elif ev == '-fread-':
            fname = wn['-set-'].get()
            if INT_LABEL == fname:
                sprite_preserv.load_internal()
            else:
                pdic = load_spr(fname)
                if len(pdic) == 0:
                    sprite_preserv.load_internal()
                else:
                    sprite_preserv.set_pattern(fname, pdic)
            files = sprfile_list()
            wn['-set-'].update(values=files)
            wn.refresh()
        elif ev == '-ins-':
            wn.hide()
            create_spr()
            wn.un_hide()
        elif ev == '-del-':
            last_key = next(reversed(sprite_preserv.sprites))
            ans = sg.ask_ok_cancel(f'Delete {last_key}?', title='Purge Item')
            if ans:
                sprite_preserv.sprites.popitem()
                sprite_preserv.enabled.remove(last_key)
        elif ev == '-dmp-':
            outdir = sprite_preserv.name
            ans = sg.ask_ok_cancel(f'Dump selected images to {outdir}/*.png',
                                   title='Dump Sprites')
            if ans:
                dump_sprites(outdir)
        elif ev == '-sav-':
            file = get_savefile(sprite_preserv.name+'.spr',
                                [('Sprite', '.spr'),])
            if file is not None and file != '':
                save_spr(file)
        elif ev == '-sel-':
            wn.hide()
            select_items()
            # print('Enabled: ',sprite_preserv.enabled)
            wn.un_hide()

        img, mag = sprite_preview()
        wn['-prvw-'].update(data=img, size=img.size)
        wn['-mag-'].update(f'x{mag}')
        wn.refresh()

    wn.close()

    if sprite_backup.name != sprite_preserv.name:
        return generate(p)
    return


def simple_frontend():
    '''仮フロントエンド'''
    global sprite_preserv
    sprite_backup = copy.deepcopy(sprite_preserv)

    files = sprfile_list()

    lo = [[sg.Listbox(files, default_value=INT_LABEL,select_mode='single',
                      key='-list-')],
          [sg.Text('',expand_x=True),
           sg.Button('View', key='-prvw-'),
           sg.Text('',expand_x=True),
           sg.Button('Done', key='-ok-'),
           sg.Button('Cancel', key='-can-')]]
    wn = sg.Window('sprite', layout = lo )

    while True:
        ev, va = wn.read()
        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            # print('Cancelled')
            sprite_preserv = copy.deepcopy(sprite_backup)
            break
        elif ev == '-ok-':
            if sprite_preserv.name != '':
                break
        elif ev == '-prvw-':
            wn.hide()
            if INT_LABEL == va['-list-'][0]:
                sprite_preserv.load_internal()
            else:
                pdic = load_spr(va['-list-'][0])
                if len(pdic) == 0:
                    sprite_preserv.load_internal()
                else:
                    sprite_preserv.set_pattern(va['-list-'][0], pdic)
            desc()
            wn.un_hide()
            files = sprfile_list()
            wn['-list-'].update(values=files)

       
        # print(ev, va)
    wn.close()

    print(f"SETNAME: {sprite_preserv.name}")
    print(f"INCLUDES: {sprite_preserv.list()}")
    print(f" - TOTAL {len(sprite_preserv.sprites)} SPRITES")


# -----
# モジュール動作
# -----
def starfield(w, h, pixel, star_density=2, seed=None):

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
    density = p.pdepth / 100
    tint = p.color_jitter
    stars = p.sub_jitter2

    w = int(ow + p.pwidth*1.3 + delta*3)
    h = int(oh + p.pwidth*1.3 + delta*3)

    if sprite_preserv is None or sprite_preserv.name == '':
        sprite_preserv.load_internal()

    sprites = sprite_preserv.sprites
    activespr = sprite_preserv.enabled

    base = Image.new('RGBA',(w,h),0)

    # -----------------------------
    # sort large first
    # -----------------------------

    activespr_sorted = sorted(
        activespr,
        key=lambda s: max(sprite_preserv.size(s)),
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

        sw,sh=sprite_preserv.size(s)

        size=max(sw,sh)*pat_size
        r=size/2+delta

        radii.append(r)

    avg_r=sum(radii)/len(radii)
    avg_area=math.pi*avg_r*avg_r

    target_num=int((ow*oh)*density/avg_area)

    # -----------------------------
    # placement storage
    # -----------------------------

    placed=[]
    placed_radius=[]

    fail=0
    fail_limit=target_num*3

    # -----------------------------
    # Blue Noise placement
    # -----------------------------

    while fail<fail_limit:

        ps=random.choice(activespr_sorted)

        sw,sh=sprite_preserv.size(ps)

        size=max(sw,sh)*pat_size
        r=size/2+delta

        # candidate count grows with density
        candidates=8+len(placed)//20

        best=None
        best_score=-1e9

        for _ in range(candidates):

            px=random.uniform(r,w-r)
            py=random.uniform(r,h-r)

            if check_circle(px,py,r):
                continue

            if not placed:

                score=1e9

            else:

                score=min(
                    math.hypot(px-x,py-y)-(r+pr)
                    for (x,y),pr in zip(placed,placed_radius)
                )

            if score>best_score:

                best_score=score
                best=(px,py)

        if best is None:

            fail+=1
            continue

        fail=0

        px,py=best

        draw_circle(px,py,r)

        placed.append((px,py))
        placed_radius.append(r)

        theta=random.random()*360

        pat=sprite_pattern(ps)
        simg=sprite_image(pat)

        simg=simg.resize(
            (int(sw*pat_size),int(sh*pat_size)),
            resample=Image.BICUBIC
        )

        p1=simg.rotate(theta,expand=True)

        p1w,p1h=p1.size

        p1x=int(px-p1w/2)
        p1y=int(py-p1h/2)

        base.paste(p1,(p1x,p1y),p1)

    # -----------------------------
    # crop
    # -----------------------------

    ofsx=int((w-ow)/2)
    ofsy=int((h-oh)/2)

    base=base.crop((ofsx,ofsy,ow+ofsx,oh+ofsy))

    base=sat_attenate(base,tint)

    img=diagonal_gradient_rgb(ow,oh,p.color1,p.color2)
    
    if stars > 0:
        star_img = starfield(ow, oh, pat_size, stars)
        img.paste(star_img,(0,0),star_img)

    img.paste(base,(0,0),base)

    return img

if __name__ == '__main__':
    if sprite_preserv is None or sprite_preserv.name == '':
        sprite_preserv.load_internal()
 
    p = Param()
    p = default_param(p)
    
    p.width = WIDTH
    p.height = HEIGHT
   
    img = generate(p)
    img.show()

