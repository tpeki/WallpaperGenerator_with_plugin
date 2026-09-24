from wall_common import *
import re
import copy
import glob
import os
import os.path as pa
import TkEasyGUI as sg
import filedialog as fdi
import numpy as np
from PIL import Image, ImageDraw, UnidentifiedImageError

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

MAX_SIZE = (128,128)

INT_LABEL = '--internal--'
INTERNAL_SET = {
    'rhkd':[
        (16,16),
        [0x18,'#A9792C'], [0xfcb,'#A9792C'],
        [0x1ffc,'#A9792C'], [0x3ff8,'#A9792C'],
        [[0x79fc,0x600],['#A9792C','#FBE488']],
        [[0x783c,0x7c0],['#A9792C','#FBE488']],
        [[0x601c,0x1760],['#A9792C','#FBE488']],
        [[0x1760,0x18],['#FBE488','#A9792C']],
        [[0x2220,0x1dc0,0x18],['#049EF0','#FBE488','#A9792C']],
        [[0x1dc0,0x220,0x18],['#049EF0','#FBE488','#A9792C']],
        [[0xa03d,0x1fc0],['#A9792C','#FBE488']],
        [[0xf00f,0xdc0,0x200],['#A9792C','#FBE488','#ED0E57']],
        [[0x6006,0x780],['#A9792C','#FBE488']],
        [[0x480,0x300],['#8BF7ED','#FBE488']],
        [[0x16c0,0x920],['#FFFFFF','#8BF7ED']],
        [[0x2940,0x16b0],['#8BF7ED','#FFFFFF']],
        ],
    'afu':[
        (16,16),
        [0x780,'#F3EF2A'], [0xc00,'#F3EF2A'], [0x6f0,'#F3EF2A'],
        [0x1ff8,'#F3EF2A'], [0x1ffc,'#F3EF2A'],
        [[0x1dfc,0x200],['#F3EF2A','#FDF1C0']],
        [[0x87c,0x780],['#F3EF2A','#FDF1C0']],
        [[0x6c0,0x100,0x3c],['#FDF1C0','#4B5108','#F3EF2A']],
        [[0xf40,0x80,0x3e],['#FDF1C0','#13A7BC','#F3EF2A']],
        [[0x1bc0,0x400,0x3c],['#FDF1C0','#FBC4C2','#F3EF2A']],
        [[0x1bc0,0x400,0x3d],['#FDF1C0','#FBC4C2','#F3EF2A']],
        [[0x6fc0,0x3e],['#FDF1C0','#F3EF2A']],
        [[0x6180,0x7e],['#FDF1C0','#F3EF2A']],
        [[0x6000,0x740,0x80,0x3c],['#FDF1C0','#7AF527','#4EB808','#F3EF2A']],
        [[0x6ff0,0xe],['#7AF527','#F3EF2A']],
        [[0x77f0,0x800,0xd],['#7AF527','#4EB808','#F3EF2A']],
        ],
    'azssn':[
        (16,16),
        [[0x1800,0x600],['#240CE2','#210BD0']],
        [[0x6e0,0x100],['#7161F6','#3A23F3']],
        [[0x1978,0x680],['#7161F6','#3A23F3']],
        [[0x101c,0xaa0,0x440,0x100],
         ['#7161F6','#3A23F3','#1D0AB9','#FDF1C0']],
        [[0x381c,0x7e0],['#7161F6','#FDF1C0']],
        [[0x381e,0x7e0],['#7161F6','#FDF1C0']],
        [[0x301e,0xba0],['#7161F6','#FDF1C0']],
        [[0x300e,0xbb0],['#7161F6','#FDF1C0']],
        [[0x3004,0xff0,0xa],['#4263F6','#FDF1C0','#7161F6']],
        [[0x1004,0xfd0,0x20,8],['#4263F6','#FDF1C0','#FCCFC7','#7161F6']],
        [[0x1000,0xce0,0x300,0x10,0xc],
         ['#4263F6','#FDF1C0','#F791EA','#7161F6','#0B34EC']],
        [[0x180c,0x7c0,0x30],['#0B34EC','#FDF1C0','#0928B4']],
        [[0x180e,0x670,0x180],['#0B34EC','#0928B4','#FDF1C0']],
        [[0x180e,0x430,0x2c0,0x100],
         ['#0B34EC','#0928B4','#8F29AF','#FDF1C0']],
        [[0x1006,0x818,0x7e0],['#0B34EC','#FDF1C0','#8F29AF']],
        [[0x100c,0xff0,2],['#FDF1C0','#8F29AF','#0B34EC']],
        ],
    }        


# 共有データクラス(preserv)定義
class SpriteSet:
    def __init__(self):
        self.name=''
        self.desc=''
        self.sprites = {}
        self.enabled = []
        self.anglefix = None
       
    def load_internal(self):
        self.sprites = copy.deepcopy(INTERNAL_SET)
        self.name = INT_LABEL
        self.desc = 'Internal Set'
        self.enabled = list(INTERNAL_SET.keys())

    def set_pattern(self, name, patterndic, desc=''):
        self.sprites = patterndic
        self.name = name
        self.desc = desc if desc is not None else ''
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


# -----
# スプライト編集
# -----
DIGIT_RE = re.compile(r'\d+')

# -----
# スプライト形式ファイル読込
# -----
def sprfile_list(directory, zfile):
    """スプライトデータファイルの取得"""
    patn = directory+pa.sep+'*.spr'
    files = [fn.replace('.spr','') \
             for fn in fdi.glob_filelistz(patn, add_zip=zfile)]
    files.append(INT_LABEL)
    return files


def str_to_tuple(s: str):
    """カンマ区切りで2要素以上、数値か#で始まる色文字列
        ただし、1要素目が空文字列の場合2要素目はコマンド文字列
        1要素目,2要素目がlistもしくはtupleの場合もあり"""
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


def load_spr(file:str, directory, zfile):
    """テキストファイルからSPR形式のデータを読み込んでスプライトデータに"""
    file = fdi.sanitize_filename(file, ext='.spr')
    path, base = pa.split(file)
    pdic = {}

    # print(f'path {path}  // base {base}')
    source = fdi.read_filez(file, add_zip=zfile)
    if source is None and path == '':
        source = fdi.read_filez(directory+pa.sep+file, add_zip=zfile)
        if source is None:
            return [], ''
        
    spr_name = None
    spr_desc = None
    ptn = []
    w,h = None, None

    for line in source:
        if len(line) == 0 or line[0] == '#':  # 空行、コメント行は飛ばす
            if spr_desc is None and len(line) > 2:
                spr_desc = line[1:].strip()
            continue
       
        if line[0] == '[':  # [スプライト名] 行
            if spr_name is not None:
                if len(ptn) > 0:  # 読込済みのパターンを保存,新規スプライト初期化
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

        data = str_to_tuple(line)
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

    return pdic, spr_desc


def save_spr(file:str, pdic):
    """スプライトの保存"""
    file = fdi.sanitize_filename(file, force_ext='.spr')
    set_name = pa.splitext(pa.basename(file))[0]

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
    return set_name


# -----
# スプライト形式保存
# -----
def dtos(data):
    """内部データを数値文字列CSVに変換"""
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
    """圧縮マクロの埋め込み"""
    n = len(buf)

    dp = [float('inf')] * (n+1)
    choice = [None] * (n+1)

    dp[n] = 0

    def cost_line(x):
        return len(x)

    def cost_rep(k):
        return len(f',rep{k-1}')

    def cost_turn():
        return len(f',turnover{k-1}')

    for i in range(n-1, -1, -1):

        # --- 1. 単行 ---
        c = cost_line(buf[i]) + dp[i+1]
        if c < dp[i]:
            dp[i] = c
            choice[i] = ('line', 1)

        # --- 2. rep ---
        j = i+1
        while j < n and buf[j] == buf[i]:
            k = j - i + 1
            c = cost_line(buf[i]) + cost_rep(k) + dp[i+k]
            if c < dp[i]:
                dp[i] = c
                choice[i] = ('rep', k)
            j += 1

        # --- 3. turnover ---
        for k in range(1, (n-i)//2 + 1):
            head = buf[i:i+k]
            tail = buf[i+k:i+2*k]

            if head == tail[::-1]:
                c = sum(cost_line(x) for x in head) + cost_turn() + dp[i+2*k]
                if c < dp[i]:
                    dp[i] = c
                    choice[i] = ('turn', k)

    # --- 再構築 ---
    out = []
    i = 0

    while i < n:
        typ, k = choice[i]

        if typ == 'line':
            out.append(buf[i])
            i += 1

        elif typ == 'rep':
            out.append(buf[i])
            out.append(f',rep{k-1}')
            i += k

        elif typ == 'turn':
            out.extend(buf[i:i+k])
            if i == 1:
                out.append(',turnover')
            else:
                out.append(f',turnover{k}')
            i += 2*k

    return out


# -----
# ビットマップで保存(dump)
# -----
def dump_sprites(outdir, sprites: SpriteSet):
    outdir = fdi.sanitize_dirname(outdir)
    if not pa.isdir(outdir):
        if not pa.exists(outdir):
            os.mkdir(outdir)
        else:
            print('Already exists file "{outdir}", not dir!')
            return

    enable_list = sprites.enabled
    extract_list = [k for k in enable_list if k in sprites.list()]
    for item in extract_list:
        pat = sprite_pattern(item, sprites)
        img = sprite_image(pat)
        
        file = fdi.sanitize_filename(item+'.png')
        img.save(outdir+pa.sep+file)
        
    return


# -----
# ビットマップから読込
# -----
# ライン当たり色数の制限
def reduce_cpr(img, colors_per_row):
    """ビットマップを行当たりN色に減色"""
    if img.mode != 'RGB':
        img = img.convert('RGB')
    # w,h = img.size

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
                                       method=Image.FASTOCTREE).convert('RGB')

        # 3. 減色後のデータをNumPy配列として元の配列へ書き戻す
        img_array[y:y+1, :, :] = np.array(row_reduced)

    # 最終結果を画像として保存
    result_img = Image.fromarray(img_array)
    result_img = result_img.quantize(16).convert('RGB')  # 全色数を制限
    return result_img


def conv_spr(img, transparent_color):
    """ビットマップをスプライト文字列に変換
        透過色は #rrggbb形式で指定"""
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


def read_and_conv(file, trans):
    if file is not None and file != '':
        file=fdi.sanitize_filename(file)
    try:
        img = Image.open(file)
    except UnidentifiedImageError:
        return None
    w,h = [min(MAX_SIZE[_],img.size[_]) for _ in (0,1)]  # サイズ制限
    img = img.resize((w,h),resample=Image.NEAREST)
    img = img.convert('RGB')
    pattern = conv_spr(img, trans)
    pat = []
    for itm in pattern:
        dat = str_to_tuple(itm)
        pat.append(dat)

    return pat


# -----
# スプライトパターン操作
# -----
def and_pat(orig, pat, n):
    """多値パターン文字列に畳み込み"""
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


def sprite_pattern(name: str, sprites: SpriteSet):
    if name not in sprites.sprites:
        return []
    
    spr=[]

    data = sprites.get(name)
    w,h = data[0]
    w,h = int(w),int(h)
    body = data[1:]
    
    for r in body:        
        va,ca = r
        
        if va is None or va == '':  # コマンド行
            if not isinstance(ca, str):
                continue
            cmd = ca.lower()
            
            if 'turnover' in cmd:
                r = DIGIT_RE.search(cmd)
                if r:
                    q = min(int(r.group()), len(spr))
                else:
                    q = len(spr)
                
                block = spr[-q:]
                #block = [copy.deepcopy(x) for x in reversed(block)]
                block = [x for x in reversed(block)]
                spr.extend(block)

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
            if not isinstance(ca, list):
                ca = [ca,]
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


def get_sprite_by_name(name: str, sprites: SpriteSet):
    if name not in sprites.list():
        return Image.new('RGB',(8,8),0)
    pat = sprite_pattern(name, sprites)
    return sprite_image(pat)

# -----
# スプライトビットマップ生成
# -----
def draw_oneline(dr, pat, colors, y):
    """1行分の処理"""
    if isinstance(colors, str):
        colors = [colors]
    for x in range(len(pat)):
        if pat[x] != '0':
            c = colors[(int(pat[x],16)-1) % len(colors)]
            dr.point((x,y),fill=c)
    return


def sprite_image(pat: list):
    """スプライト内部データをビットマップに変換"""
    img = Image.new('RGBA', (len(pat[0][0]),len(pat)), 0)
    dr = ImageDraw.Draw(img)

    y = 0
    for line in pat:
        pat, colors = line
        draw_oneline(dr, pat, colors, y)
        y += 1
    return img

# 追加画面パレット
def palette_extract(img, max_colors=16):
    """画像から使用色(上位16色まで)を抽出"""
    pals = img.getcolors()
    if pals is None:
        return []
    pal_sorted = sorted(pals, key=lambda x: x[0], reverse=True)
    return [rgb for count, rgb in pal_sorted[:max_colors]]


def palette_draw(palette, trans=None):
    """パレット画像生成"""
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
PREVIEW_SIZE=(272,240)

def xy_keep_aspect(img):
    w, h = img.size
    scale = min(PREVIEW_SIZE[0] / w, PREVIEW_SIZE[1] / h)
    return int(w * scale), int(h * scale)


def update_preview(wn, img, cpr, trans):
    rimg = reduce_cpr(img, cpr)
    x,y = xy_keep_aspect(img)
    rimg = rimg.resize((x,y), resample=Image.NEAREST)
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


def create_spr(spriteset, directory):
    colormenu = [[sg.Text('SPRITE SET '),
                sg.Text(spriteset.name,
                        size=(20,1),key='-setname-')],
               [sg.Text('ID'),
                sg.Input('', size=(12,1), key='-name-')],
               [sg.Text('Color/Row '),
                sg.Input('8', size=(2,1), key='-cpr-')],
               [sg.Text('Transparent '),
                sg.Text('#000000', size=(8,1), key='-tcol-')],
               [sg.Image(size=(164,44), key='-tcpal-', enable_events=True)],
               ]

    column_lo = [[sg.Frame('', layout=colormenu, relief='groove',
                    vertical_alignment='top')],
                 [sg.Text(expand_y=True)],
                 [sg.Text('File:'),
                  sg.Text('',size=(0,1), key='-fname-')],
                 [sg.Button('Read File', key='-import-',
                            background_color='#ffffdd'),
                  sg.Button('Reduce Color', key='-redc-'),
                 ]]
           
    lo = [[sg.Image(size=PREVIEW_SIZE,key='-prvw-'),
           sg.Column(layout=column_lo, expand_y=True)],
          [sg.Button('BulkRead', key='-blk-', background_color='#ddffff'),
           sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Register', key='-ok-', background_color='#ddffdd'),
           ]]

    img = None
    cpr = 8
    trans = (0,0,0)
    pcols = []
   
    wn = sg.Window('Import bitmap', layout=lo,)

    while True:
        ev,va = wn.read()

        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            spriteset = None
            break
        elif ev == '-ok-':
            nname = wn['-name-'].get()
            if nname !='' and \
               nname not in spriteset.list():
                pcol = palette_extract(img)
                trans = to_rgb(wn['-tcol-'].get())
                if trans not in pcol:
                    palette_draw(pcol, trans=None)
                    continue
                pattern = conv_spr(img, rgb_string(trans))
                # print(nname,' Pattern:', pattern[3])
                pat = []
                for itm in pattern:
                    dat = str_to_tuple(itm)
                    pat.append(dat)

                spriteset.sprites[nname] = pat
                spriteset.enabled.append(nname)
                # print(f"'{nname}': {pat}")
            break
        elif ev == '-redc-':
            ncpr = safeint(wn['-cpr-'].get())
            if ncpr != cpr and (0 < ncpr <= 16):
                cpr = ncpr
                rimg, pcols = update_preview(wn, img, cpr, trans)
                check_transparent(wn, pcols, trans)
            continue                
        elif ev == '-blk-':
            wn.hide()
            result = bulk_import(directory)
            wn.un_hide()
            if result:
                pdic, setname, foldername = result
                spriteset.set_pattern(setname, pdic, desc=foldername)
                break
        elif ev == '-import-':
            ftypes = '*.png;*.jpg;*.gif;*.ico'
            fname = fdi.get_openfile('', filetypes=[('Bitmap',ftypes),
                                                    ('any', '.*')],
                                     init_dir=directory)
            fdi.flush_ev(wn)
            if fname is not None and fname != '':
                img = Image.open(fdi.sanitize_filename(fname))
                w,h = [min(MAX_SIZE[_],img.size[_]) for _ in (0,1)]  # ザイズ制限
                img = img.resize((w,h), resample=Image.NEAREST)
                img = img.quantize(colors=16).convert('RGB')
                wn['-fname-'].update(pa.splitext(pa.split(fname)[1])[0])
                cpr = safeint(wn['-cpr-'].get())
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
    return spriteset


def bulk_import(directory):
    """一括スプライト取込み"""
    lo = [[sg.Text('Import folder:'),
           sg.Input(key='-folder-', size=(0,1)),
           sg.FolderBrowse(key='-fsel-', target_key='-folder-',
                           default_path=directory)],
          [sg.Text('Transparent Color:'),
           sg.Input('#000000', key='-trns-', size=(10,1)),
           sg.Text(expand_x=True),
           sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
           sg.Button('Register', key='-ok-', background_color='#ddffdd'),
           ],
          ]
    wn = sg.Window('Bulk read', layout=lo)

    while True:
        ev, va = wn.read()
        if ev == sg.WINDOW_CLOSED or ev == '-can-':
            wn.close()
            return None
        elif ev == '-ok-':
            foldername = va['-folder-']
            trans = va['-trns-']
            if pa.isdir(foldername):
                break
        
        print(ev, va)

    wn.close()

    setname = pa.basename(foldername)
    fnames = glob.glob(foldername+pa.sep+'*.*')

    print( f'folder={foldername}\ntrans={trans}')
    pdic = {}
    for file in fnames:
        nname = pa.splitext(pa.split(file)[1])[0]
        p = read_and_conv(file, trans)
        if p is not None:
            print(nname, end=' ')
            pdic[nname] = p
            
    if len(pdic) >= 1:
        print(f'\n{setname} includes {len(pdic)} pattern(s)')
        return pdic, setname, foldername
    else:
        return None


# -----
# 汎用サポート関数
# -----
# 文字列 -> 数値変換 (16進考慮)
def safeint(s, default=0):
    try:
        val = int(s)
    except ValueError:
        if isinstance(s, str):
            val = int(s,0)
        else:
            val = default
    return val

if __name__ == '__main__':
    print('sprite create submodule')
