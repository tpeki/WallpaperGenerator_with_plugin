if __name__ == '__main__':
    import _4debug

from wall_common import *
import os.path as pa
import copy
import TkEasyGUI as sg
import filedialog as fdi
import numpy as np
from PIL import Image, ImageFilter, ImageChops, ImageOps
from plugins import sub_sprites as sps

# --- 定数設定 ---
WIDTH = 1920
HEIGHT = 1080
BGCOLOR1 = (0xc6, 0xc6, 0xc6) # 背景基本色
BGCOLOR2 = (0xa6, 0xa6, 0xd6) # 背景基本色2
OLCOLOR = (0, 0, 0x11)   # spriteアウトライン色初期値
FGJITTER = 30  # テープ色ゆらぎ Palette +/- FGJitter, 
BGJITTER = 50  # 背景色ゆらぎ  Gradation(BG1 +/- BGJitter,BG2 +/- BGJitter)
# 単位面積 = テープ幅×(利用spr幅+spr間隔)+利用spr数
ZOOM = 4  # multiplier テープ幅倍率 
SPACING = 4  # spr間隔(pix)
ANGLE = 0  # 全体角度 degree
# sprite配置しない場合は無視

# --- 内部定数設定 ---
MARGIN = 5  # スプライトの両側に設ける余白：テープ幅=sprite最大高＋border(pix)
FLIP = 0  # sprite配置時、反転spriteを続けて配置する bit1:up/down bit2:left/right

DATA_DIR = 'samples'
ZIPFILE = 'sprites.zip'
SPSEXT = '.spr'
PALETTE_SIZE = 10
TAPZIP = 'tylorean.zip'
TAPEXT = '.tap'
TY_THUMB = (300,60)

if __name__ == '__main__':
    PRFX = '../'
else:
    PRFX = ''

Palette = [(0x99, 0xdd, 0xdd), (0xec, 0xec, 0xec), (0xdd, 0x99, 0xdd),
           (0x99, 0xdd, 0x99), (0xee, 0xee, 0x99), (0xdd, 0x99, 0x99),
           (0x99, 0x99, 0xdd), (0xee, 0xbb, 0x99), (0xbb, 0x99, 0xee),
           (0x44, 0x44, 0x44)  
           ]

# -----
# Tape pattern (initial)
# -----
INT_TAPESET = '*internal*'
INT_PATTERNS = {
    'simple': [[(0,3), (1,2), (0,10), (1,2), (0,3)]
               ],  # 20px
    'flat': [[(2,18)],
             ],
    'wavy': [[(0,18)],
             [(0,17),(10,1)],
             [(0,15),(10,3)],
             [(0,16),(10,2)],
             [(0,18)],
             [(10,1),(0,17)],
             [(10,2),(0,16)],
             [(10,2),(0,16)],
             [(10,1),(0,17)],
             [(10,1),(0,17)],
             ],  # 18px
    'cross': [[(0,2), (1,2), (0,1), (1,2), (2,1), (1,1), (2,1), (1,2),
               (0,1), (1,2), (0,2)],
              [(0,2), (1,3), (0,1), (1,2), (2,1), (1,2), (0,1), (1,3), (0,2)],
              [(0,2), (1,1), (2,1), (1,2), (0,1), (1,3), (0,1), (1,2),
               (2,1), (1,1), (0,2)],
              [(0,2), (2,1), (1,1), (2,1), (1,2), (0,1), (1,1), (0,1),
               (1,2), (2,1), (1,1), (2,1), (0,2)],
              [(0,1), (2,1), (1,3), (2,1), (1,2), (0,1), (1,2), (2,1),
               (1,3), (2,1), (0,1)],
              [(0,2), (2,1), (1,1), (2,1), (1,2), (0,1), (1,1), (0,1),
               (1,2), (2,1), (1,1), (2,1), (0,2)],
              [(0,2), (1,1), (2,1), (1,2), (0,1), (1,3), (0,1), (1,2),
               (2,1), (1,1), (0,2)],
              [(0,2), (1,3), (0,1), (1,2), (2,1), (1,2), (0,1), (1,3), (0,2)],
              [(0,2), (1,2), (0,1), (1,2), (2,1), (1,1), (2,1), (1,2),
               (0,1), (1,2), (0,2)],
              [(0,2), (1,1), (0,1), (1,2), (2,1), (1,3), (2,1), (1,2),
               (0,1), (1,1), (0,2)],
              ],  # 17px
    'zigzag': [[(0,3), (1,2), (5,3), (1,2), (0,3), (1,2)],
               [(1,1), (0,3), (1,2), (5,3), (1,2), (0,3), (1,1)],
               [(1,2), (0,3), (1,2), (5,3), (1,2), (0,3)],
               [(1,1), (0,3), (1,2), (5,3), (1,2), (0,3), (1,1)],
               ],  # 15px
    'bubble': [[(0,2),(9,1),(5,5),(9,3),(4,4),(9,1),(0,2)],
               [(0,2),(9,2),(5,3),(9,3),(4,6),(0,2)],
               [(0,2),(9,7),(4,8),(0,1)],
               [(0,2),(9,7),(4,8),(0,1)],
               [(0,2),(9,6),(6,3),(4,6),(0,1)],
               [(0,2),(9,4),(6,7),(4,4),(0,1)],
               [(0,2),(9,3),(6,9),(4,2),(0,2)],
               [(0,2),(9,2),(6,11),(9,1),(0,2)],
               [(0,2),(9,2),(6,11),(9,1),(0,2)],
               [(0,2),(9,1),(6,13),(0,2)],
               [(0,2),(9,1),(6,13),(0,2)],
               [(0,2),(9,1),(6,13),(0,2)],
               [(0,2),(9,2),(6,11),(9,1),(0,2)],
               [(0,2),(9,2),(6,11),(9,1),(0,2)],
               [(0,2),(9,2),(5,3),(6,6),(3,2),(9,1),(0,2)],
               [(0,2),(9,1),(5,5),(6,4),(3,4),(0,2)],
               [(0,2),(5,7),(6,2),(9,1),(3,4),(0,2)],
               [(0,1),(5,9),(9,3),(3,2),(9,1),(0,2)],
               [(0,1),(5,9),(9,6),(0,2)],
               [(0,1),(5,9),(9,6),(0,2)],
               [(0,2),(5,7),(9,7),(0,2)],
               ],  # 18px
    'rainbow': [[(9,2), (5,2), (9,1), (7,2), (9,1), (4,2), (9,1),(3,2),
                 (9,1), (6,2), (9,2)]
                ],  # 18px
    }

# -----
# sprite pattern (initial)
# -----
INT_SETNAME = '*Sunflower*'
INT_SPRITES = {
    'pat1': [
        [0x10, 0x10],
        [0x180, '#FF0808'],
        [0x6186, '#FF0808'],
        [0x6006, '#FF0808'],
        [0x1188, '#FF0808'],
        [0xff0, '#FF0808'],
        [0xc30, '#FF0808'],
        [0x990, '#FF0808'],
        [0xdbdb, '#FF0808'],
        [None, 'turnover'],
        ],
    'pat2': [
        [0x10, 0x10],
        [0, '#000000'],
        [0x80, '#FFF208'],
        [0x258c, '#FFF208'],
        [0x3598, '#FFF208'],
        [0x1bd0, '#FFF208'],
        [[0x42c, 0x180], ['#FFF208', '#A40C00']],
        [[0x810, 0x3c0], ['#FFF208', '#A40C00']],
        [[0x781c, 0x7e0], ['#FFF208', '#A40C00']],
        [[0x381e, 0x7e0], ['#FFF208', '#A40C00']],
        [[0x810, 0x3c0], ['#FFF208', '#A40C00']],
        [[0x3420, 0x180], ['#FFF208', '#A40C00']],
        [0xbd8, '#FFF208'],
        [0x19ac, '#FFF208'],
        [0x31a4, '#FFF208'],
        [0x100, '#FFF208'],
        [0, '#000000'],
        ],
    'flower_r': [
        [0x10, 0x10],
        [0xee0, '#FA3E4C'],
        [0x1ff0, '#FA3E4C'],
        [None, 'rep2'],
        [0xffe, '#FA3E4C'],
        [[0x7e7f,0x180], ['#FA3E4C','#FBF99A']],
        [[0xf81f,0x7e0], ['#FA3E4C','#FBF99A']],
        [None, 'rep1'],
        [[0x7c7e,0x380], ['#FA3E4C','#FBF99A']],
        [[0xf81c,0x7e0], ['#FA3E4C','#FBF99A']],
        [[0x791e,0x6e0], ['#FA3E4C','#FBF99A']],
        [0x1fff, '#FA3E4C'],
        [0x3fff, '#FA3E4C'],
        [0x3ffe, '#FA3E4C'],
        [0x3e7c, '#FA3E4C'],
        [0xc38, '#FA3E4C'],
        ],
    'flower_y': [
        [0x10, 0x10],
        [0xee0, '#F4E769'],
        [0x1ff0, '#F4E769'],
        [None, 'rep2'],
        [0xffe, '#F4E769'],
        [[0x7e7f,0x180], ['#F4E769','#92111B']],
        [[0xf81f,0x7e0], ['#F4E769','#92111B']],
        [None, 'rep1'],
        [[0x7c7e,0x380], ['#F4E769','#92111B']],
        [[0xf81c,0x7e0], ['#F4E769','#92111B']],
        [[0x791e,0x6e0], ['#F4E769','#92111B']],
        [0x1fff, '#F4E769'],
        [0x3fff, '#F4E769'],
        [0x3ffe, '#F4E769'],
        [0x3e7c, '#F4E769'],
        [0xc38, '#F4E769'],
        ],
    'leaf': [
        [0x08, 0x10],
        [0xc6, '#3f8a20'],
        [0xee, '#3f8a20'],
        [0x6c, '#3f8a20'],
        [0x38, '#3f8a20'],
        [0x10, '#3f8a20'],
        [0xd6, '#3f8a20'],
        [0xee, '#3f8a20'],
        [0x7c, '#3f8a20'],
        [0x38, '#3f8a20'],
        [0x10, '#3f8a20'],
        [0xd6, '#3f8a20'],
        [0xee, '#3f8a20'],
        [0x7c, '#3f8a20'],
        [0x38, '#3f8a20'],
        [0x10, '#3f8a20'],
        [0x10, '#3f8a20'],
        ],
    }


tyrolean_preserv = {'palette': Palette.copy(),
                    'basic': {'bg1': BGCOLOR1, 'bg2': BGCOLOR2,
                              'outline': OLCOLOR,
                              'fjitter': FGJITTER, 'bjitter': BGJITTER,
                              'zoom': ZOOM, 'spacing': SPACING,
                              'angle': ANGLE, 'margin': MARGIN,
                              'flip': FLIP, 'twopt': Image.NEAREST, # Image.LANCZOS
                              },
                    'sps': None,
                    'tap': None,
                    'tape_name': None,
                    'tplist': [],
                    }


class Tapes:
    def __init__(self):
        self.patterns = {}
        self.name = ''
        self.desc = ''
        self.internal_set = copy.deepcopy(INT_PATTERNS)
        self.internal_name = INT_TAPESET

    def set_internal(self, name=None, pattern_dic=None):
        if pattern_dic is None:
            pattern_dic = INT_PATTERNS
        self.internal_set = copy.deepcopy(pattern_dic)

        if name is None:
            name = INT_TAPESET
        self.internal_name = name

        return len(self.internal_set)

    def load_internal(self):
        self.patterns = self.internal_set.copy()
        self.name = self.internal_name
        self.desc = 'Internal set'

    def list(self):
        return list(self.patterns.keys())

    def get(self, label):
        if label in self.list():
            return self.patterns[label]
        else:
            return None

    def size(self, label):
        return check_pat_size(self.patterns[label])

    def image(self, label, length=None):
        if not label in self.patterns:
            return None
        if length is None:
            length,h = self.size(label)
        
        pattern = self.patterns[label]
        palette = tyrolean_preserv['palette']  # default palette
        return tape_image(pattern, palette, int(length))

    def set_patterns(self, set_name, pattern_dic):
        if pattern_dic is None:
            return None
        self.patterns = copy.deepcopy(pattern_dic)

        if set_name is None:
            set_name = next(iter(self.patterns.key()))
        self.internal_name = set_name
        return self.patterns


    def merge_patterns(self, appendic):
        """パターンセット(辞書)をマージ(既存は書き換えない)
        return: マージ後のパターンセット"""
        for k, v in appendic.items():
            if k not in self.patterns:
                self.patterns[k] = copy.deepcopy(v)
        return self.patterns

    def add_pattern(self, label, pattern):
        self.patterns[label] = copy.deepcopy(pattern)
        return self.patterns[label]

    def pat_to_text(self, label):
        """1パターン分のテキスト
        返り値： 以下のフォーマットで返却。ラベルが存在しなければNone
        
        [label]<br>
        カラム数<br>
        パレット,ドット数,パレット,ドット数,...<br>  ×カラム数
        """
        if not label in self.patterns:
            return None
        
        pattern = self.patterns[label]
        lines = [f'[{label}]',f'{len(pattern)}']
        for column in pattern:
            buf = []
            for pix in column:
                if isinstance(pix, tuple|list):
                    buf.append(f'{int(pix[0])},{int(pix[1])}')
            lines.append(','.join(buf))

        return lines

    def patterns_to_text(self):
        """パターンセットを文字列にする"""
        buf = [f'#TapeSet:{self.set_name}',]
        for pat in self.patterns:
            ptxt = self.pat_to_text(pat)
            if ptxt is not None:
                buf.extend(ptxt)
        return buf

    def text_to_pat(self, buf):
        """[パターン名]行から続くパターンテキストを読み込んで辞書レコードに変換
        戻り値は 変換結果辞書(1エントリ), 取り込んだ行数"""
        ptr = 0
        if buf[ptr][0] != '[':
            return None, 0
        label = buf[ptr][1:].split(']')[0]
        ptr += 1
        length = int(buf[ptr])
        ptr += 1
        pat_data = []
        for line in range(length):
            array = buf[ptr+line].split(',')
            lbuf = []
            for n in range(len(array)//2):
                p = safe_int(array[n*2])
                l = safe_int(array[n*2+1])
                if l > 0:
                    lbuf.append((p,l))
            pat_data.append(lbuf)
        return {label: pat_data}, ptr+length
 

    def text_to_patterns(self, buf):
        """テキストからパターンを読み込んでテープセットに登録。
            戻り値はset名とパターンセット(辞書) エラー時は None,None"""
        ptr = 0
        while buf[ptr][0] != '[':  # パターン名行までスキップ
            if buf[ptr].startswith('#TapeSet:'):
                set_name = buf[ptr][9:].split(' ')[0]
            ptr += 1
            if ptr > len(buf):
                return None, None
        pattern_set = {}
        while True:
            if ptr >= len(buf):
                break
            #print(buf[ptr:])
            pat, nxptr = self.text_to_pat(buf[ptr:])
            if ptr+nxptr > len(buf):
                break
            if isinstance(pat, dict):
                pattern_set.update(pat)
            ptr += nxptr
            while  ptr < len(buf):
                if buf[ptr][0] == '[':
                    break
                ptr += 1

        if len(pattern_set) == 0:
            return None, None
        self.name = set_name
        self.patterns = pattern_set
        
        return set_name, pattern_set

    def load_file(self, file_name, directory=None, add_zip=None):
        pats, desc = load_tape_patterns(file_name, directory, add_zip)
        if len(pats) == 0 or not isinstance(pats, dict):
            self.__init__(self)
        else:
            self.name = pa.splitext(pa.basename(file_name))[0]
            self.patterns = pats
            self.desc = desc

        return len(self.patterns)  # num of loaded patterns

    def save_file(self, file_name=None, directory=None):
        if file_name is None:
            if self.name is None:
                return 0
            file_name = self.name + TAPEXT
            
        r = save_tape_patterns(self.patterns, file_name, directory, self.desc)
        return r  # num of saved patterns


class Tylorean:
    def __init__(self, pattern, palette=None):
        if palette is None:
            palette = Palette
        self.pattern = copy.deepcopy(pattern)  # 2次元配列なので引数はlocalに
        self.palette = copy.deepcopy(palette)
        self.sprites = []
        self.spr_h = 0
        tw = 0
        for col in self.pattern:
            cw = sum([y for x,y in col])
            tw = max(tw, cw)
        self.p_height = tw  # パターンの最大幅
        self.p_width = len(self.pattern)  # テープの最小繰り返し幅
        self.image = None  # image()で後から生成
        

    def put_sprite(self, sprite_image, shrink=False):
        w,h = sprite_image.size
        if self.spr_h < h and shrink:
            spr_w = int(w * (self.spr_h / h))
            sprite_image = sprite_image.resize((spr_w, self.spr_h),
                                               resample=Image.LANCZOS)
        self.sprites.append(sprite_image)
        
        return len(self.sprites)-1

    def sprite_height(self, limit=0):
        """limit=0:最大sprite高 n:制限高"""
        if len(self.sprites) == 0:
            return 0
        if limit == 0:
            return max([x.height for x in self.sprites])
        else:
            self.spr_h = limit
            return limit


    def weave(self, height, length):
        """height=0: sprite_height based, n:limitted_height
            length: > 0"""
        margin = tyrolean_preserv['basic']['margin']
        spacing = tyrolean_preserv['basic']['spacing']
        twopt = tyrolean_preserv['basic']['twopt']

        if len(self.sprites) == 0:  # spriteなし
            if height != 0:
                th = check_pat_size(self.pattern) + margin*2
                sr = height / th
                tape_img = tape_image(self.pattern, self.palette,
                                      int(length/sr))
                
                tape_img = tape_img.resize((length, th), twopt)
            else:
                tape_img = tape_image(self.pattern, self.palette, length)
            return tape_img

        
        print(margin, spacing)

        lheight = self.spr_h
        if lheight == 0:
            lheight = self.sprite_height(0)

        if height > 0:
            lheight = height
        
        spr_img = []
        swidth = 0
        for x in self.sprites:
            if x.height > lheight:
                w = int(x.width * (lheight/x.height))
                x.resize((w, lheight), resample=Image.LANCZOS)
            swidth += x.width
            spr_img.append(x)

        swidth += len(self.sprites)*spacing
        tape_height = lheight + margin*2
        simage = Image.new('RGBA', (swidth, tape_height), (0,0,0,0))

        pos = 0
        for x in self.sprites:
            y = (tape_height - x.height)//2
            simage.paste(x, (pos, y), x)
            pos += x.width + spacing
        
        flip = tyrolean_preserv['basic']['flip']
        flip_img = ImageOps.flip(simage) if flip & 1 else simage
        flip_img = ImageOps.mirror(flip_img) if flip & 2 else flip_img

        
        _, th = check_pat_size(self.pattern)
        sr = tape_height / th

        tape_img = tape_image(self.pattern, self.palette, int(length/sr))
        tape_img = tape_img.resize((length, tape_height), twopt)
        #tape_img.show()

        print((length, tape_height))
        
        pos = 0
        while True:
            if pos > length:
                break

            tape_img.paste(simage, (pos, 0), simage)
            pos += swidth
            if flip != 0:
                tape_img.paste(flip_img, (pos, 0), flip_img)
                pos += swidth
            
        self.image = tape_img
        return tape_img


def safe_int(s):
    try:
        r = int(s)
    except ValueError:
        r = 0
    return r

def load_tape_patterns(file_name, directory=None, add_zip=None):
    file_name = fdi.sanitize_filename(file_name, ext=TAPEXT)
    path, base = pa.split(file_name)
    if directory is None or directory == '':
        directory = DATA_DIR

    source = fdi.read_filez(file_name, add_zip=add_zip)
    if source is None and path == '':
        source = fdi.read_filez(directory+pa.sep+file, add_zip=zfile)
        if source is None:
            return {}, ''

    set_name = pa.splitext(base)[0]  # 使わないか
    desc = None
    pdic = {}
    ptn = []
    ptn_name = None

    for line in source:
        if len(line) == 0 or line[0] == '#':  # 空行、コメント行は飛ばす
            if desc is None and line[0] == '#':
                desc = re.sub(r'^#\s*', '', line.strip())
                # 最初のコメント行をdescとして保存(#と空白,"SET_NAME ="は除外)
            continue
        if line[0] == '[':
            if ptn_name is not None:
                if len(ptn) > 0:  # 前の定義があった
                    pdic[ptn_name] = ptn
                    ptn = []
                    ptn_name = None
            m = re.match(r'^\[(.*?)\]', line)
            if m:
                ptn_name = m.group(1)
            continue
                
        if ptn_name is None:
            continue
        data = str_to_tapecolumn(line)
        if data is None:
            continue
        ptn.append(data)

    if ptn_name is not None:
        if len(ptn) > 0:  # 前の定義があった
            pdic[ptn_name] = ptn

    return pdic, desc        
    
aznum = re.compile(r'^([A-Za-z]+)(\d+)')

def str_to_tapecolumn(line):
    array = line.split(',')
    if len(array) == 0:
        return None
    print(line,'\n', array)
    array = [aznum.match(s).groups() for s in array]
    data = []
    for pal, length in array:
        pal = ord(pal.upper()[0]) - ord('A')
        length = safe_int(length)
        if length > 0:
            data.append((pal, length))
    return data
        
def save_tape_patterns(patterns, file_name, directory=None, desc=None):
    file_name = fdi.sanitize_filename(file_name, ext=TAPEXT)
    set_name = pa.splitext(pa.basename(file_name))[0]
    if desc is None or desc == '':
        desc = set_name

    with open(file_name, mode='w', encoding='sjis') as f:
        f.write(f'# {desc}\n')
        
        for item in patterns:
            f.write(f'[{item}]\n')
            buffer = []
            for line in patterns[item]:
                buffer.append(tapecolumn_to_str(line))
            f.write('\n'.join(buffer)+'\n')
    print(f'{file_name} : wrote {len(patterns.keys())} records')
    return set_name

def tapecolumn_to_str(line):
    buf = []
    oa = ord('a')
    for d in line:
        p, l = d
        buf.append(f'{chr(oa+p)}{l:d}')
    return ','.join(buf)
    

def tapfile_list(directory, zfile):
    """テープセットファイルの取得"""
    patn = directory+pa.sep+'*'+TAPEXT
    files = [fn.replace(TAPEXT,'') \
             for fn in fdi.glob_filelistz(patn, add_zip=zfile)]
    # files.append(INT_SETNAME)  # internalは呼び出し元で追加する
    return files


# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'チロリアンテープ',
                       {'color1':'背景色1', 'color2':'背景色2',
                        'color3':'縁取り色',
                        'color_jitter':'前景揺らぎ', 'sub_jitter':'背景揺らぎ',
                        'pwidth':'ズーム率', 'pheight':'キャラ間隔',
                        'pdepth':'角度'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*BGCOLOR1)
    p.color2.itoc(*BGCOLOR2)
    p.color3.itoc(*OLCOLOR)
    p.color_jitter = FGJITTER
    p.sub_jitter = BGJITTER
    p.pwidth = ZOOM
    p.pheight = SPACING
    p.pdepth = ANGLE
    return p


def set_preserv(p):
    bdic = tylorean_preserv['basic']
    bdic['bg1'] = p.color1.ctoi()
    bdic['bg2'] = p.color2.ctoi()
    bdic['outline'] = p.color3.ctoi()
    bdic['fjitter'] = p.color_jitter
    bdic['bjitter'] = p.sub_jitter
    bdic['zoom'] = p.pwidth
    bdic['spacing'] = p.pheight
    bdic['angle'] = p.pdepth


# 基本スプライトの設定
def set_intspr(): # -> sps.SpriteSet
    s = sps.SpriteSet()
    # s.set_internal()  # defaultset in sps
    s.set_internal(INT_SETNAME, INT_SPRITES)  # 内部定義を設定
    s.load_internal()  # 内部定義をload

    return s

def set_inttap():
    t = Tapes()
    t.load_internal()  # Tapesは内部定義を初期化時に取込済
    return t


# テープパターンの基本サイズを取得
def check_pat_size(pattern):
    """patternの周期長、テープ幅を取得 -> (W, H)"""
    h = []
    #try:
    for x in pattern:
        linemax = sum([j for i,j in x])
        h.append(linemax)
        #print(linemax, x)
        
    return len(pattern), max(h)
    #except ValueError:
     #   return None


def tape_image(pattern: list, palette: list, length: int) -> Image.Image:
    """
    指定されたパターン名と長さ(幅)に基づいてテープ画像を生成する
    
    :param pattern: パターンデータ
    :param palette: パレットデータ
    :param length: 描画するテープの長さ（画像の横幅 px）
    :return: PIL.Image オブジェクト (RGBモード)
    """
    num_cols, tape_height = check_pat_size(pattern)
    
    # パターン1ユニット分(高さ × 列数)の配列を作成
    unit_matrix = np.zeros((tape_height, num_cols, 3), dtype=np.uint8)
    unit_alpha = np.full((tape_height, num_cols),255, dtype=np.uint8)
    
    for x, col in enumerate(pattern):
        y = 0
        for pal_idx, count in col:
            if pal_idx == 10:
                unit_alpha[y:y+count,x] = 0
            else:
                color = palette[pal_idx]
                unit_matrix[y:y+count, x] = color
            y += count
        if y < tape_height:
            unit_alpha[y:tape_height, x] = 0
            
    # 横方向にリピートして指定の length にスライス
    repeats = (length // num_cols) + 1
    full_matrix = np.tile(unit_matrix, (1, repeats, 1))[:, :length, :]
    alpha = np.tile(unit_alpha, (1, repeats))[:, :length]

    #h,w,_ = full_matrix.shape
    #rgba = np.dstack([full_matrix, np.full((h, w), 255, np.uint8)])
    rgba = np.dstack([full_matrix, alpha])
   
    return Image.fromarray(rgba,'RGBA')


# -----
# テープ要素を組み合わせる
# -----
def collect_parts(number):
    """number: 0..9 テープ番号
       テープ要素の組み合わせ編集ダイアログ"""
    tt = len(tyrolean_preserv['tplist'])
    dsps = tyrolean_preserv['sps'].name
    tapset = tyrolean_preserv['tap']
    taps = tapset.name
    tapname = tyrolean_preserv['tape_name']

    if number < tt:
        cur_ty = tyrolean_preserv['tplist'][number]
    elif number == tt:
        if tapname is None:
            tapname = next(iter(tapset.list()))
        pat = tapset.get(tapname)
        cur_ty = Tylorean(pat, Palette)
        tyrolean_preserv['tplist'].append(cur_ty)
    else:
        return None
        
    print('--- tyrolean created ---')
    spslist = sps.sprfile_list(PRFX+DATA_DIR, ZIPFILE)  # PRFX+は後で削除
    taplist = tapfile_list(PRFX+DATA_DIR, TAPZIP)       # PRFX+は後で削除
    spsel = [sg.Text('Sprite set:', width=10),
             sg.Combo(values=spslist, key='-spsl-', readonly=True),
             sg.Combo(values=[], key='-sprl-', readonly=True),
             sg.Button('Add', key='-spadd-', background_color='#ddddff'),
             ]
    tpsel = [sg.Text('Tape set:', width=10),
             sg.Combo(values=taplist, key='-tpsl-', readonly=True),
             sg.Combo(values=[], key='-tapl-', readonly=True),
             sg.Button('Select', key='-tapch-', background_color='#ffbbdd'),
             ]

    tyimg = tapethumb(cur_ty)
    preview = sg.Image(data=tyimg, key='-preview-', size=TY_THUMB,
                       resize_type=sg.utils.ImageResizeType.FIT_WIDTH)
    
    






    


def tapethumb(ty: Tylorean):
    w0,h0 = TY_THUMB

    if ty.image is None:
        tyimg = ty.weave(0, w0)
    else:
        tyimg = ty.image

    w,h = tyimg.size
    if h > h0:
        tyimg = tyimg.thumbnail((int(w*h0/h), h0))  # 幅広なら縮小
        h = h0
    if tyimg.width > w0:
        w = w0

    if w < tyimg.width or h < tyimg.height:
        tyimg = tyimg.crop((w,h))
    #tyimg = tyimg.resize((w*2,h*2), resample=Image.LANCZOS)
    
    return tyimg
    











#-----------------------------------------------------------------------
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
    bim = Image.new('RGB',image.size, rgb_string(border))
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

# ------------------------------------------------------------------------
import time
def chk(tape_name=None, fringe=3, gap=3, spr_set=None, spr_name=None):
    """動作チェック： 完成版では削除"""
    tapes = tyrolean_preserv['tap']
    if not isinstance(tapes, Tapes):
        tapes = Tapes()
        tapes.load_internal()

    if tape_name is None:
        tape_name = tyrolean_preserv['tape_name']
    if tape_name not in tapes.list():
        tape_name = next(iter(tapes.list()))

    if spr_set is None:
        s = tyrolean_preserv['sps']
    else:
        s = sps.SpriteSet()
        s.load_file(spr_set, '..\\samples', ZIPFILE)
        print(s.list())
    if spr_name is None:
        spr_name = s.list()

    ty = Tylorean(tapes.get(tape_name), Palette)

    border = tyrolean_preserv['basic']['outline']
    for spr in spr_name:
        simg = s.image_with_border(spr, border_color=border)
        ty.put_sprite(simg)

    
    ty.weave(0,1920).show()
        

if __name__ == '__main__':
    s = set_intspr()
    tyrolean_preserv['sps'] = s
    t = set_inttap()
    tyrolean_preserv['tap'] = t

    p = Param()
    p = default_param(p)
    
    p.width = WIDTH
    p.height = HEIGHT
   
    #img = generate(p)
    #img.show()

    chk('zigzag', 2)
