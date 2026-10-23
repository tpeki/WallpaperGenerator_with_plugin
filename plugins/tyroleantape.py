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
INTERVAL = 0  # テープ間隔
ANGLE = 0  # 全体角度 degree
# sprite配置しない場合は無視

# --- 内部定数設定 ---
BGANGLE = 0
SPACING = 4  # spr間隔(pix)
MARGIN = 5  # スプライトの両側に設ける余白：テープ幅=sprite最大高＋border(pix)
FLIP = 0  # sprite配置時、反転spriteを続けて配置する bit1:up/down bit2:left/right

DATA_DIR = 'samples'
ZIPFILE = 'sprites.zip'
SPSEXT = '.spr'
PALETTE_SIZE = 10
TAPZIP = 'Tyrolean.zip'
TAPEXT = '.tap'
TY_THUMB = (300,60)
TEXTURE_WEIGHTS = [[0,0,0,0],  # 断面,サテン,織目,ムラ(長手方向)
                   [0.5, 0.2, 0.3, 1],
                   [0.6, 0.7, 0.5, 1]
                   ]

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
    'simple': [[(0,3), (1,3), (0,12), (1,3), (0,3)]
               ],  # 24px
    'flat': [[(2,20)],
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
    'rainbow': [[(9,3), (5,3), (9,2), (7,3), (9,2), (4,3), (9,2),(3,3),
                 (9,2), (6,3), (9,3)]
                ],  # 29px
    'tiger': [[(4,16)],[(4,14),(9,2)],[(4,12),(9,4)],[(4,10),(9,6)],
              [(4,8),(9,8)],[(4,6),(9,10)],[(4,4),(9,12)],[(4,2),(9,14)],
              [(9,16)],[(9,14),(4,2)],[(9,12),(4,4)],[(9,10),(4,6)],
              [(9,8),(4,8)],[(9,6),(4,10)],[(9,4),(4,12)],[(9,2),(4,14)],
              ],  # 16px
    'tiger2': [[(4,16)],[(4,15),(9,1)],[(4,14),(9,2)],[(4,13),(9,3)],
               [(4,12),(9,4)],[(4,11),(9,5)],[(4,10),(9,6)],[(4,9),(9,7)],
               [(4,8),(9,8)],[(4,7),(9,9)],[(4,6),(9,10)],[(4,5),(9,11)],
               [(4,4),(9,12)],[(4,3),(9,13)],[(4,2),(9,14)],[(4,1),(9,15)],
               [(9,16)],[(9,15),(4,1)],[(9,14),(4,2)],[(9,13),(4,3)],
               [(9,12),(4,4)],[(9,11),(4,5)],[(9,10),(4,6)],[(9,9),(4,7)],
               [(9,8),(4,8)],[(9,7),(4,9)],[(9,6),(4,10)],[(9,5),(4,11)],
               [(9,4),(4,12)],[(9,3),(4,13)],[(9,2),(4,14)],[(9,1),(4,15)],
               ],  # 16px
    }

# -----
# sprite pattern (initial)
# -----
INT_SETNAME = '*Sunflower*'
INT_SPRITES = {
    'sun': [
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
    'sunflower': [
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
                              'zoom': ZOOM, 'interval': INTERVAL,
                              'angle': ANGLE, 'bgangle': BGANGLE,
                              'spacing': SPACING, 'margin': MARGIN,
                              'flip': FLIP, 'twopt': Image.NEAREST, # Image.LANCZOS
                              },
                    'sps': None,
                    'tap': None,
                    'tape_name': None,
                    'tplist': [],
                    }


# -----
# テープセット
# -----
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

# -----
# テープ構成
# -----
class Tyrolean:
    def __init__(self, pattern, palette=None):
        if palette is None:
            palette = Palette
        self.pattern = copy.deepcopy(pattern)  # 2次元配列なので引数はlocalに
        self.palette = copy.deepcopy(palette)
        self.sprites = []  # sprite名のリスト[(sl, sr), ... ]
        self.sprdic = {}  # spritesの登場スプライトパターン '{sl}&{sr}': [[sprtext]]
        self.imglist = []
        self.spr_h = 0
        self.height = 0
        self.outline = tyrolean_preserv['basic']['outline']
        self.margin = tyrolean_preserv['basic']['margin']
        self.spacing = tyrolean_preserv['basic']['spacing']
        self.flip = tyrolean_preserv['basic']['flip']
        self.twopt = tyrolean_preserv['basic']['twopt']
        self.texture = 1
        
        tw = 0
        for col in self.pattern:
            cw = sum([y for x,y in col])
            tw = max(tw, cw)
        self.p_height = tw  # パターンの最大幅
        self.p_width = len(self.pattern)  # テープの最小繰り返し幅
        # self.image = None  # image()で後から生成
        
    def sprite_height(self, limit=0):
        """limit=0:最大sprite高 n:制限高"""
        if len(self.sprites) == 0:
            return 0
        if limit == 0:
            self.imglist = self.render_sprites()
            maxheight = max([x.height for x in self.imglist])
            return maxheight
        else:
            self.spr_h = limit
            return limit

    def pattern_size(self):
        return check_pat_size(self.pattern)
    
    def weave(self, length, height=None):
        """height=0:sprite_height based, n:limitted_height, None:default
            length: > 0"""
        #margin = self.margin
        #spacing = self.spacing
        #twopt = self.twopt
        if height is None:
            height = self.height

        if len(self.imglist) == 0:  # spriteなし
            if height != 0:
                th = check_pat_size(self.pattern) + self.margin*2
                sr = height / th
                tape_img = tape_image(self.pattern, self.palette,
                                      int(length/sr))
                
                tape_img = tape_img.resize((length, th), twopt)
            else:
                tape_img = tape_image(self.pattern, self.palette, length)
            return tape_img

        lheight = self.spr_h
        if lheight == 0:
            lheight = self.sprite_height(0)
        if height > self.margin*2:
            lheight = height - self.margin*2

        spr_img = []
        swidth = 0
        for x in self.imglist:
            w = int(x.width * (lheight/x.height))
            x = x.resize((w, lheight), resample=Image.LANCZOS)
            swidth += w
            spr_img.append(x)

        swidth += len(self.imglist)*self.spacing
        tape_height = lheight + self.margin*2
        simage = Image.new('RGBA', (swidth, tape_height), (0,0,0,0))

        pos = 0
        for x in spr_img:
            y = (tape_height - x.height)//2
            simage.paste(x, (pos, y), x)
            pos += x.width + self.spacing
        
        fimage = ImageOps.flip(simage) if self.flip & 1 else simage  # 縦
        fimage = ImageOps.mirror(fimage) if self.flip & 2 else fimage  # 横

        
        _, th = check_pat_size(self.pattern)
        sr = tape_height / th

        tape_img = tape_image(self.pattern, self.palette, int(length/sr))
        tape_img = tape_img.resize((length, tape_height), self.twopt)
        #print((length, tape_height))
        
        pos = 0
        while True:
            if pos > length:
                break

            tape_img.paste(simage, (pos, 0), simage)
            pos += swidth
            if self.flip != 0:
                tape_img.paste(fimage, (pos, 0), fimage)
                pos += swidth

        if 0 < self.texture < 3:
            tape_img = add_texture(tape_img, TEXTURE_WEIGHTS[self.texture])
        self.image = tape_img
        return tape_img

    def render_sprites(self):
        ss = sps.SpriteSet()
        ss.merge_pdic(self.sprdic)
        
        ol = self.outline
        otf = ol is not None
        #print(self.sprites)
        
        if otf:
            imglist = [ss.image_with_border(ssname(sl,sr), ol)\
                       for sl,sr in self.sprites]
        else:
            imglist = [ss.image(ssname(sl,sr)) for sl,sr in self.sprites]

        self.imglist = imglist
        return imglist

    def merge_sprdic(self, setname, sdic):
        for x in sdic:
            self.sprdic[ssname(setname,x)] = sdic[x]
        return len(sdic)


def safe_int(s):
    try:
        r = int(s)
    except ValueError:
        r = 0
    return r

def ssname(s1,s2):
    def rplemp(s):
        if not isinstance(s, str):
            return ''
        return s.replace('&','%26')
    
    return rplemp(s1)+'&'+rplemp(s2)

def load_tape_patterns(file_name, directory=None, add_zip=None):
    file_name = fdi.sanitize_filename(PRFX+file_name, ext=TAPEXT)
    path, base = pa.split(file_name)
    if directory is None or directory == '':
        directory = DATA_DIR

    source = fdi.read_filez(file_name, add_zip=add_zip)
    if source is None and path == '':
        source = fdi.read_filez(directory+pa.sep+file_name, add_zip=add_zip)
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
    file_name = fdi.sanitize_filename(PRFX+file_name, ext=TAPEXT)
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
    patn = PRFX+directory+pa.sep+'*'+TAPEXT
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
                        'pwidth':'ズーム率', 'pheight':'テープ間隔',
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
    p.pheight = INTERVAL
    p.pdepth = ANGLE
    return p


def set_preserv(p):
    bdic = tyrolean_preserv['basic']
    bdic['bg1'] = p.color1.ctoi()
    bdic['bg2'] = p.color2.ctoi()
    bdic['outline'] = p.color3.ctoi()
    bdic['fjitter'] = p.color_jitter
    bdic['bjitter'] = p.sub_jitter
    bdic['zoom'] = p.pwidth
    bdic['interval'] = p.pheight
    bdic['angle'] = p.pdepth

def revert_p(p):
    bdic = tyrolean_preserv['basic']
    p.color1 = RGBColor(bdic['bg1'])
    p.color2 = RGBColor(bdic['bg2'])
    p.color3 = RGBColor(bdic['outline'])
    p.color_jitter = bdic['fjitter'] 
    p.sub_jitter = bdic['bjitter']
    p.pwidth = bdic['zoom'] 
    p.pheight = bdic['interval'] 
    p.pdepth = bdic['angle']



    
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
    for x in pattern:
        linemax = sum([j for i,j in x])
        h.append(linemax)
        
    return len(pattern), max(h)


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
    bdr = tyrolean_preserv['basic']['margin']

    tpcache = {}
    tapset = set_inttap()
    tpcache[INT_TAPESET] = tapset
    spcache = {}
    spset = set_intspr()
    spcache[INT_SETNAME] = spset
    collected = sps.SpriteSet()
    spr_arrange = []

    if number < tt:
        cur_ty = tyrolean_preserv['tplist'][number]
        spr_arrange = cur_ty.sprites.copy()
        collected.sprites = cur_ty.sprdic.copy()
        sprth, imglist = sprthumb(cur_ty, spr_arrange, collected)
        cur_ty.imglist = imglist
    elif number == tt:
        if tapname is None:
            tapname = next(iter(tapset.list()))
        pat = tapset.get(tapname)
        cur_ty = Tyrolean(pat, Palette)
        tyrolean_preserv['tplist'].append(cur_ty)
        sprth = Image.new('RGB',(500,60), '#d8d8d8')
    else:
        return None
        
    print('--- tyrolean created ---')
    tyimg = tapethumb(cur_ty)
    tex = cur_ty.texture
    top = [sg.Text(f'Tape No. {number}'),
           sg.Text(expand_x=True),
           sg.Image(data=tyimg, key='-preview-', size=TY_THUMB,
                    resize_type=sg.utils.ImageResizeType.FIT_WIDTH),
           sg.Text('Texture'),
           sg.Slider(value_range=(0,2), default_value=tex, resolution=1,
                     orientation='v', size=(1,5), disable_number_display=True,
                     enable_changed_events=True, key='-ftex-'),
           ]
    
    taplist = tapfile_list(PRFX+DATA_DIR, TAPZIP)       # PRFX+は後で削除
    taplist.append(INT_TAPESET)
    patlist = list(INT_PATTERNS.keys())
    tpsel = [sg.Text('Tape set:', width=10),
             sg.Combo(values=taplist, key='-tpsl-', readonly=True,
                      width=10, default_value=INT_TAPESET,
                      enable_events=True),
             sg.Combo(values=patlist, key='-tapl-', readonly=True,
                      width=16, default_value=''),
             sg.Button('Select', key='-tsel-', background_color='#ffbbdd'),
             ]

    palette = cur_ty.palette
    pals = palparts(palette)
    pals.extend([sg.Text(expand_x=True),
                 sg.Button('P-Load', key='-pld-', background_color='#ddddff'),
                 sg.Button('P-Save', key='-psv-', background_color='#ddddff'),
                 ])
    
    spslist = sps.sprfile_list(PRFX+DATA_DIR, ZIPFILE)  # PRFX+は後で削除
    spslist.append(INT_SETNAME)
    sprlist = list(INT_SPRITES.keys())
    spsel = [sg.Text('Sprite set:', width=10),
             sg.Combo(values=spslist, key='-spsl-', readonly=True,
                      width=10, default_value=INT_SETNAME,
                      enable_events=True),
             sg.Combo(values=sprlist, key='-sprl-', readonly=True,
                      width=16, default_value=''),
             sg.Button('Add', key='-spadd-', width=5,
                       background_color='#ddddaa'),
             sg.Button('Remove', key='-sprmv-', width=5,
                       background_color='#eeddaa'),
             ]

    ssprvw = [sg.Image(data=sprth, size=(500,60), key='-ssprvw-',
                       background_color='#d8d8d8')]

    margin = cur_ty.margin
    spacing = cur_ty.spacing
    cparam = [sg.Text('Margin', width=7),
              sg.Input(width=4, key='-cbdr-', default_text=margin,
                       background_color='#ffffdd'),
              sg.Text('Spacing', width=7),
              sg.Input(width=4, key='-cspc-', default_text=spacing,
                       background_color='#ffffdd'),
              ]
    
    _,th = cur_ty.pattern_size()
    sh = cur_ty.sprite_height()
    fheight = cur_ty.height
    heights = [sg.Text('Height', width=7),
               sg.Input(width=4, key='-fheight-', default_text=fheight,
                        background_color='#ffffdd'),
               sg.Text(f' Tape {th}', key='-theights-'),
               sg.Text(f'/Sprite {sh}', key='-sheights-'),
               ]
    
    if cur_ty.outline is None:
        otf = False
        outline = tyrolean_preserv['basic']['outline']
    else:
        otf = True
        outline = cur_ty.outline
    fgc, bgc = bg_and_font(outline)
    coutl = [sg.Checkbox('Outline', default=otf, width=8, key='-foutl-'),
             sg.Button(bgc[1:], text_color=fgc, background_color=bgc,
                       key='-coutl-')]

    flip = cur_ty.flip
    twopt = cur_ty.twopt
    blur = twopt != Image.NEAREST  # NEAREST or LANCZOS
    flags = [sg.Checkbox('Flip', default=(flip & 1),
                         width=6, key='-fflip-'),
             sg.Checkbox('Mirror', default=(flip & 2),
                         width=6, key='-fmirr-'),
             sg.Checkbox('Blur', default=blur,
                         width=6, key='-fsmpl-'),
             ]

    buttons = [sg.Button('SetLoad', key='-tyld-', background_color='#ddddff'),
               sg.Button('SetSave', key='-tysv-', background_color='#ddddff'),
               sg.Text(expand_x=True),
               sg.Button('Test', key='-tst-', width=6,
                         background_color='#ddeeff'),
               sg.Button('Cancel', key='-can-', width=6,
                         background_color='#ffdddd'),
               sg.Button('Done', key='-ok-', width=6,
                         background_color='#ddffdd'),
               ]

    layout = [top,
              tpsel,
              pals,
              spsel,
              ssprvw,
              [sg.Column([cparam, heights],
                         expand_x=True, expand_y=True),
               sg.Text(' '),
               sg.Column([coutl,flags], expand_x=True),
               #sg.Text(' '),
               #sg.Column([flags], expand_x=True),
               ],
              buttons]

    dup = copy.deepcopy(cur_ty)  # キャンセル用
    wn = sg.Window(f'Tape No.{number}', layout)

    while True:
        ev,va = wn.read()

        if ev in ('-can-', sg.WINDOW_CLOSED):
            ev = '-can-'
            break
        elif ev == '-ok-':
            break
        elif ev.startswith('-pal'):
            n = int(ev[4])
            cl = sg.popup_color(ev,rgb_string(cur_ty.palette[n]),
                                format='tuple')
            fdi.flush_ev(wn)
            if cl is None:
                continue
            cur_ty.palette[n] = cl
            fgc, bgc = bg_and_font(cl)
            wn[ev].update(background_color=bgc)
        elif ev == '-psv-':
            # save functions doesn't need refresh preview
            continue
        elif ev == '-tysv-':
            # save functions doesn't need refresh preview
            continue
        elif ev == '-tpsl-':
            v = wn[ev].get()
            if v in tpcache:
                tps = tpcache[v]
            else:
                tps = Tapes()
                tps.load_file(v, PRFX+DATA_DIR, TAPZIP)
                tpcache[v] = tps

            patlist = tps.list()
            wn['-tapl-'].update(values=patlist, value='')
            continue
        elif ev == '-spsl-':
            v = wn[ev].get()
            print(v, spcache)
            if v in spcache:
                spset = spcache[v]
            else:
                spset = sps.SpriteSet()
                spset.load_file(v, PRFX+DATA_DIR, ZIPFILE)
                spcache[v] = spset
            sprlist = spset.list()
            wn['-sprl-'].update(values=sprlist, value='')
            continue
        elif ev == '-tsel-':
            tpsname = wn['-tpsl-'].get()
            tapname = wn['-tapl-'].get()
            if not tapname in tpcache[tpsname].list():
                continue
            cur_ty.pattern = tpcache[tpsname].get(tapname)
            _,h = cur_ty.pattern_size()
            wn['-theights-'].update(f' Tape {h}')
        elif ev in ('-spadd-', '-sprmv-'):
            if ev == '-sprmv-':
                if len(spr_arrange) == 0:
                    continue
                spr_arrange.pop()
            else:
                spset = wn['-spsl-'].get()
                sprname = wn['-sprl-'].get()
                if not sprname in spcache[spset].list():
                    continue
                spr_arrange.append([spset,sprname])
                collected.update_sprite(ssname(spset,sprname),
                                        spcache[spset].get(sprname))
            sh = cur_ty.sprite_height()
            wn['-sheights-'].update(f'/Sprite {sh}')
        elif ev == '-coutl-':
            cl = sg.popup_color(ev,rgb_string(cur_ty.outline),
                                format='tuple')
            if cl is None:
                continue
            cur_ty.outline = cl if cur_ty.outline is not None else None
            fgc, bgc = bg_and_font(cl)
            wn[ev].update(text=bgc[1:], background_color=bgc, text_color=fgc)
            outline = cl
        elif ev == '-foutl-':
            otf = wn[ev].get()
            if otf:
                cur_ty.outline = outline
            else:
                cur_ty.outline = None
        elif ev in ('-fflip-', '-fmirr-'):
            ffl = 1 if wn['-fflip-'].get() else 0
            fmi = 2 if wn['-fmirr-'].get() else 0
            cur_ty.flip = ffl | fmi
        elif ev == '-fsmpl-':
            cur_ty.twopt = Image.LANCZOS if wn['-fsmpl-'].get() \
                           else Image.NEAREST
        elif ev == '-tst-':
            fh = safe_int(wn['-fheight-'].get())
            if fh > 0:
                cur_ty.height = fh
            spc = safe_int(wn['-cspc-'].get())
            if spc > 0:
                cur_ty.spacing = spc
            mgn = safe_int(wn['-cbdr-'].get())
            if mgn > 0:
                cur_ty.margin = mgn
        elif ev == '-ftex-':
            v = safe_int(wn[ev].get())
            cur_ty.texture = v

        cur_ty.sprites = spr_arrange
        cur_ty.sprdic = collected.sprites
        sprth, imglist = sprthumb(cur_ty, spr_arrange, collected)
        cur_ty.imglist = imglist
        wn['-ssprvw-'].update(data=sprth)

        tyimg = tapethumb(cur_ty)
        wn['-preview-'].update(data=tyimg)
        print(ev)

    wn.close()
    if ev == '-can-':
        cur_ty = dup
        return None

    return cur_ty

    
def palparts(palette):
    pals = [sg.Text('Palette', width=7),
            sg.Text(' 0', width=2, text_align='right'),
            ]

    if len(palette) < 10:
        palette.extend([[(0,0,0)]*10])
        palette = palette[:10]
    for n,c in enumerate(palette):
        cstr = rgb_string(c)
        pals.append(sg.Button(' ', width=1, background_color=cstr,
                              key=f'-pal{n}-'))
    pals.append(sg.Text('9', width=1, text_align='left'))
    return pals
        

def tapethumb(ty: Tyrolean):
    w0,h0 = TY_THUMB

    tyimg = ty.weave(w0, 0)
    
    w,h = tyimg.size
    if h > h0:
        tyimg.thumbnail((int(w*h0/h), h0))  # 幅広なら縮小
        h = h0
    if tyimg.width > w0:
        w = w0

    if w < tyimg.width or h < tyimg.height:
        tyimg = tyimg.crop((w,h))

    if 0 < ty.texture < 3:
        tyimg = add_texture(tyimg, TEXTURE_WEIGHTS[ty.texture])
    return tyimg

    
def sprthumb(ty: Tyrolean, sprites_list, ss: sps.SpriteSet):
    w0,h0 = 500,60
    bg = '#d8d8d8'
    
    sp = ty.spacing
    ol = ty.outline
    otf = ol is not None
    if otf:
        fgc, bgc = bg_and_font(ol)
        if fgc == '#000000':
            bg = '#383838'
        
    if len(sprites_list) == 0:
        return Image.new('RGB', (500,60), bg), []
    
    maxheight = max([ss.size(x)[1] for x in ss.list()])
    sph = maxheight if ty.height == 0 else ty.height - ty.margin*2

    if otf:
        imlist = [ss.image_with_border(ssname(sl,sr), ol) \
                  for sl,sr in sprites_list]
    else:
        imlist = [ss.image(ssname(sl,sr)) for sl,sr in sprites_list]
    
    ww = 0
    for x in imlist:
        if not isinstance(x, Image.Image):
            continue
        w,h = x.size
        w = int(w*60/h)
        ww += w+sp

    base = Image.new('RGB', (ww, 60), bg)

    
    ww = 0
    for x in imlist:
        if not isinstance(x, Image.Image):
            continue
        w,h = x.size
        w = int(w*60/h)
        im = x.resize((w,60), resample=Image.NEAREST)
        base.paste(im, (ww,0), im)
        ww += w+sp

    return base, imlist


def add_texture(image, weights=None):
    """weight = [crossing, satin-hilight, fabric, longitude]
    """
    arr = np.asarray(image).astype(np.float32)
    h, w = arr.shape[:2]

    tex = ribbon_texture(w, h, weights)

    arr[..., :3] *= tex[..., None]
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def ribbon_texture(width: int, height: int, weights: (list|None)=None
                   )-> np.ndarray:
    """リボン用テクスチャ生成 -> ndarray (height, width) 0～1.5程度の乗算係数
    """
    if not isinstance(weights, list):
        weights = [0.5, 0.3, 0.2, 1.0]
    weights.extend([0,]*4)
    wc, wh, wf, wl = weights[:4]
     
    # 正規化座標
    u = np.linspace(0.0, 1.0, width, dtype=np.float32)
    v = np.linspace(-1.0, 1.0, height, dtype=np.float32)
    U, V = np.meshgrid(u, v)

    # 断面陰影
    cross = (
        0.95
        + 0.05 * np.cos(V * np.pi / 2)
    )
    # サテン光沢
    highlight = (
        1.0
        + 0.25 * np.exp(
            -((V - 0.08*np.sin(U*4*np.pi))/0.12)**2)
    )
    # 織り目
    fabric = (
        1.0
        + 0.015 * np.sin(U * 600 * np.pi)
        + 0.008 * np.sin(U * 1200 * np.pi)
    )
    # 長手方向のムラ
    longitudinal = (
        0.97
        + 0.03 * np.sin(U * 8 * np.pi)
    )

    tex = tex = np.ones((height, width), dtype=np.float32)

    tex *= 1 + (cross - 1) * wc
    tex *= 1 + (highlight - 1) * wh
    tex *= 1 + (fabric - 1) * wf
    tex *= 1 + (longitudinal - 1) * wl
    return tex.astype(np.float32)


def desc(p):
    placer = ['Parallel', 'Random']
    bg_grad = ['Vertical', 'Horizontal', 'Diagonal']
    dup_b = copy.deepcopy(tyrolean_preserv['basic'])
    dup_t = copy.deepcopy(tyrolean_preserv['tplist'])
    set_preserv(p)
    bdic = tyrolean_preserv['basic']

    left = []
    right = []
    for x in range(5):
        left.append([sg.Text(f'{x}'),
                     sg.Image(key=f'-tap{x}-', background_color='#d8d8d8',
                              size=TY_THUMB, resize_type='fit_width',
                              enable_events=True),
                     ])
        right.append([sg.Text(f'{x+5}'),
                     sg.Image(key=f'-tap{x+5}-', background_color='#d8d8d8',
                              size=TY_THUMB, resize_type='fit_width',
                              enable_events=True),
                     ])
    tapes = [sg.Frame('Tape Set', layout=[[sg.Column(layout=left),
                                           sg.Column(layout=right)]])]
    
    layouting = [sg.Combo(placer, default_value=next(iter(placer)),
                          width=10, key='-plcr-', readonly=True),
                 sg.Text('  Zoom'),
                 sg.Input(f'{bdic["zoom"]}', key='-zm-', width=4,
                          background_color='#ffffdd'),
                 sg.Text('Interval'),
                 sg.Input(f'{bdic["interval"]}', key='-itvl-', width=4,
                          background_color='#ffffdd'),
                 sg.Text('Rotate'),
                 sg.Input(f'{bdic["angle"]}', key='-angl-', width=4,
                          background_color='#ffffdd'),
                 sg.Text(' Front Jit.'),
                 sg.Input(f'{bdic["fjitter"]}', key='-fjit-', width=4,
                          background_color='#ffffdd'),
                 ]

    fgc1, bgc1 = bg_and_font(bdic['bg1'])
    fgc2, bgc2 = bg_and_font(bdic['bg2'])
    bginfo = [sg.Combo(bg_grad, default_value=next(iter(bg_grad)),
                       width=10, key='-grad-', readonly=True),
              sg.Text(' C1'), sg.Button(bgc1[1:], key='-bg1-', text_color=fgc1,
                                       background_color=bgc1),
              sg.Text('C2'), sg.Button(bgc2[1:], key='-bg2-', text_color=fgc2,
                                       background_color=bgc2),
              sg.Text(' BG Angle'),
              sg.Input(f'{bdic["bgangle"]}', key='-incl-', width=4,
                          background_color='#ffffdd'),
              sg.Text(' BG Jit.'),
              sg.Input(f'{bdic["bjitter"]}', key='-bjit-', width=4,
                       background_color='#ffffdd'),
              ]

    buttons = [sg.Text(expand_x=True),
               sg.Button('Cancel', key='-can-', width=6,
                         background_color='#ffdddd'),
               sg.Button('Done', key='-ok-', width=6,
                         background_color='#ddffdd'),
               ]
    layout = [tapes,
              layouting,
              bginfo,
              buttons]

    wn = sg.Window('Tyroleantape conf.', layout=layout)

    for i, x in enumerate(tyrolean_preserv['tplist']):
        wn[f'-tap{i}-'].update(data=tapethumb(x))

    while True:
        ev, va = wn.read()

        if ev in ('-can-', sg.WINDOW_CLOSED):
            ev = '-can-'
            break
        elif ev.startswith('-tap') and va['event_type'] == 'mousedown':
            n = safe_int(ev[4])
            print(n)
            tyr = collect_parts(n)
            tplist = tyrolean_preserv['tplist']
            if tyr is not None:
                if n < len(tplist):
                    tplist[n] = tyr
                    print('old one')
                else:
                    tplist.append(tyr)
                    print('new one')
                wn[ev].update(data=tapethumb(tyr))
            else:
                print('tyr is None')
            fdi.flush_ev(wn)
        elif ev.startswith('-bg'):
            label = ev[1:4]
            cl = sg.popup_color(ev,rgb_string(bdic[label]),
                                format='tuple')
            if cl is None:
                continue
            fgc, bgc = bg_and_font(cl)
            wn[ev].update(bgc[1:], text_color=fgc, background_color=bgc)
            bdic[label] = cl
            setattr(p, 'color'+label[-1], RGBColor(cl))
            fdi.flush_ev(wn)
            

                


    wn.close()
    if ev == '-can-':
        tyrolean_preserv['basic'] = dup_b
        tyrolean_preserv['tplist'] = dup_t
        revert_p(p)
        return None
    
    
    

# -----
# モジュール動作
# -----
def generate(p: Param):


    return

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
    spr_set = s.name

    ty = Tyrolean(tapes.get(tape_name), Palette)
    ty.merge_sprdic(spr_set, s.sprites)

    border = tyrolean_preserv['basic']['outline']
    ty.outline = border
    ty.spacing = gap
    ty.margin = fringe

    for spr in spr_name:
        ty.sprites.append((spr_set,spr))

    ty.render_sprites()

    ty.weave(1920, 0).show()
        

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
