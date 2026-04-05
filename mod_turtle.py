from PIL import Image, ImageDraw, ImageFont
import random
import TkEasyGUI as sg
from wall_common import *
from filedialog import *
import os.path as pa

# --- 定数設定 ---
PEN_COLOR = (0x40, 0xff, 0xff)  # ペン色
BG_COLOR = (0x88, 0x88, 0x88)  # 背景色
PEN_WIDTH = 40  # ペン幅
PEN_STEP = 10
BACK_JITTER = 50  # 背景色の最大変化幅
CMDFONTS = 'BIZ UDゴシック'

DATA_DIR = 'samples'
ZIPFILE = 'turtle.zip'

DEBUG_PR = [
#    'x',
#    'y',
#    'dir',
#    'pen',
#    'color',
#    'width',
#    'step',
    'sp',
    'stack',
    'lsp',
    'lstack'
    ]

#CMD = '200,100J2R10FR5F255,255,0C200,400J2H10FR5F'
CMD = '65z130,210j3{frfr2}flflf2l4f'\
      'ulfrfd2l4frfr2frfr4frfr2frf'\
      'u2h6fn3fdfrfr2frfr2frfr2flflf2l4f'\
      'u2h2fn3fdrfr2frfr2frfr2frfr4frfr2frf'\
      '200,670j52p255,127,64c2h"Hope your year is "'\
      '250,800j"filled with many "248,64,64c"happy "255,127,64c"moments!"'\
      '1600,950j5p4z255,255,88c2h4f4r2f2l6fu2l4fdn6f2r2frfrfrfr2f'\
      'u3l3fl2fdn6fu4r3fd3l3fu4r3fd2l3f'

tur_preserve = {'cmd': ''}

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, '年賀(似非タートル)',
                       {'color1':'ペン色','color2':'背景基本色',
                        'color_jitter':'背景色変化',
                        'pwidth':'ペン幅', 'pheight':'ステップ幅'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc(*PEN_COLOR)
    p.color2.itoc(*BG_COLOR)
    p.color_jitter = BACK_JITTER
    p.pwidth = PEN_WIDTH
    p.pheight = PEN_STEP
    tur_preserve['cmd'] = CMD

    return p


def view_desc(p: Param):
    posx = p.wwidth
    posy = p.wheight + p.wposy

    layout=[[sg.Multiline(tur_preserve['cmd'], readonly=True,
                          text_color='#000000', background_color='#f0eea0',
                          text_align='left', size=(60,10), expand_x=True)],
            [sg.Text('',expand_x=True), sg.Button('Close',key='-d_close-'),
             sg.Text('',expand_x=True)]]
    sdialog = sg.Window('Command String', layout=layout,
                        location=(posx,posy), padding_x=0, padding_y=0,
                        grab_anywhere=True)

    while True:
        ev,va = sdialog.read()
        if ev == '-d_close-':
            break
    sdialog.close()

    return None

def edit_layout():
    test_pane = [sg.Image(key='-t_test-', size=(640,360),
                          background_color='#444444')
                 ]
    command_pane = [sg.Multiline(key='-t_cmds-', size=(80,10),
                                 text_color='black', background_color='#f0eea0',
                                 text_align='left', font=(CMDFONTS,12),
                                 expand_x=True, expand_y=True)
                    ]
    buttons = [sg.Text('File'),
               sg.Input('', text_align='right', key='-t_file-',expand_x=True),
               sg.Text('', size=(2,1)),
               sg.Button('Clear', key='-t_clr-', background_color='#ddddff'),
               sg.Button('Test', key='-t_tst-'),
               sg.Text(' ', size=(2,1)),
               sg.Button('Load', key='-t_ld-'),
               sg.Button('Save', key='-t_sv-'),
               sg.Text(' ', size=(2,1)),
               sg.Button('Cancel', key='-t_can-', background_color='#ffdddd'),
               sg.Button('Apply', key='-t_ok-', background_color='#ddffdd'),
               ]

    return [test_pane, command_pane, buttons]


def desc(p: Param):
    layout = edit_layout()

    wn = sg.Window('Turtle Draw', layout=layout, grab_anywhere=True,
                   resizable=True) #, modal=True
    
    cmds = tur_preserve['cmd']
    wn['-t_cmds-'].update(text=cmds)
    
    t_img = generate(p, command = cmds)
    wn['-t_test-'].update(data=t_img)

    while True:
        ev, va = wn.read()
        if ev == sg.WINDOW_CLOSED or ev == '-t_can-':
            t_img = None
            break
        elif ev == '-t_clr-':
            cmds = f'{p.width//2},{p.height//2}jh'  # 初期コマンド
            wn['-t_cmds-'].update(text=cmds)
            t_img = Image.new('RGB', (p.width, p.height), color='#444444')
            wn['-t_test-'].update(data=t_img)
        elif ev == '-t_tst-':
            cmds = wn['-t_cmds-'].get_text()
            #if '\n' in cmds:
            #    cmds = ''.join(cmds.splitlines())
            # print(f'CMDS: {cmds}')
            t_img = generate(p, command=cmds)
            wn['-t_test-'].update(data=t_img)
        elif ev == '-t_ok-':
            cmds = wn['-t_cmds-'].get_text()
            #if '\n' in cmds:
            #    cmds = ''.join(cmds.splitlines())
            t_img = generate(p, command=cmds)
            wn['-t_test-'].update(data=t_img)
            tur_preserve['cmd'] = cmds
            break
        elif ev == '-t_ld-':
            fname = wn['-t_file-'].get_text()
            cmds, fname = load_tur(fname)
            frush_ev(wn)
            # print(f'FILE: {fname} / CMDS: {cmds}')
            if fname == '':  # =cancelled
                continue
            wn['-t_cmds-'].update(text=''.join(cmds))
            wn['-t_file-'].update(text=fname)
            t_img = generate(p, command=cmds)
            wn['-t_test-'].update(data=t_img)
        elif ev == '-t_sv-':
            fname = wn['-t_file-'].get_text()
            cmds = wn['-t_cmds-'].get_text()
            fname = save_tur(fname, cmds)
            frush_ev(wn)
            if fname == '':  # =cancelled
                continue
            wn['-t_file-'].update(text=fname)
        
    wn.close()
    return t_img

def load_tur(fname):
    fname = get_openfile(sanitize_filename(fname),
                         filetypes=[('Turtle command','*.tur'),],
                         init_dir=DATA_DIR)
    # print(f'File {fname}')
    if fname == '':
        return '', ''
    cmds = ''  # 仮 cmdsに\n入っててもよい
    #with open(fname, mode='r', encoding='shift-jis') as f:
    #    print(f'read {fname}')
    #    cmds = f.read()
    cmds = read_filez(fname, add_zip=ZIPFILE)
    cmds = [s+'\n' for s in cmds]
    return cmds, fname

def save_tur(fname, cmds):
    fname = get_savefile(fname,
                         filetypes=[('Turtle command','*.tur'),],
                         init_dir=DATA_DIR)
    if fname == '':
        return ''
    fname = sanitize_filename(fname, force_ext='.tur')
    with open(fname, mode='w', encoding='shift-jis') as f:
        f.write(cmds)
    return fname

'''
TURTLEコマンド
F    スタック先頭をpopし、数値だけn歩前進 スタックに値が無ければ1歩
L/R  スタック先頭をpopし、その回数CCW/CWに回頭 ただし1単位=45度、スタックに値が無ければ1とみなす
U/D  ペンアップ／ダウン
C    スタック先頭からb,g,rをpopしてペン色を(r,g,b)に変更
P    スタック先頭をpopし、ペン太さ(ピクセル)を変更
J    スタック先頭からx,yをpopし、絶対座標(x,y)に移動
N    タートルの方向を北(方向0)に変更(初期値)
H    スタック先頭をpopし、タートルの方向をその向きにする(0..7)
]    スタック先頭の値を複製してスタックに積む
[    スタック先頭の値を捨てる
X    スタック先頭の2値を入れ替える
,    直前の数値をスタック先頭に積む(数値の後に文字が来たらスタックに積むので実は何もしない)
W    現在の座標をスタック先頭にx,yの順で積む
Z    スタック先頭をpopし、移動単位をnピクセルにする
S    スタック先頭をレジスタ番号とし、次値をレジスタ#nにコピー(値はスタックに残る)
Q    レジスタ#nの値をスタックに積む
?    スタック先頭の値を数値として描画する(popしない)
+/-/*///^ スタック先頭の2値を用いて四則演算・べき乗
~    スタック先頭をpopし、符号反転して積む
".." クォート間の文字をカーソル位置に挿入
{    スタック先頭をpopし、繰り返し数として対応する}まで繰り返し(ネスト可)
}    ループ終端
!    スタック先頭をpopし、0なら一番浅いループを抜ける
&    デバッグ出力をコンソールに行う
#    行末までコメントとして読み飛ばす
'''

DIR = [(0,-1), (1,-1), (1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1)]
REGISTER_SIZE = 10
STACK_SIZE = 32
LSTACK_SIZE = 32
MAX_PEN_WIDTH = 200
Opcode = ['+', '-', '*', '/', '^']  # 二項演算子
Unary = ['~']  # 単項演算子

class Turtle:
    def __init__(self, dir=0, pen_down=True, size=PEN_WIDTH, step=PEN_STEP,
                 color=RGBColor(PEN_COLOR), x=0, y=0):
        self.dir = dir
        self.pen = pen_down
        self.width = size
        self.color = color
        self.step = step
        self.x = x
        self.y = y
        
        self.lastx = x
        self.lasty = y
        self.register = [0]*REGISTER_SIZE
        self.stack = [0] * STACK_SIZE
        self.sp = -1
        self.lstack = [0] * LSTACK_SIZE
        self.lsp = -1

    def pop_stack(self, default=0):
        if self.sp < 0:
            return default
        val = self.stack[self.sp]
        self.sp -= 1
        return val

    def push_stack(self,n):
        if self.sp < STACK_SIZE - 1:
            self.sp += 1
            self.stack[self.sp] = n

    def pop_lstack(self):
        if self.lsp < 0:
            return (0,None,None)
        val = self.lstack[self.lsp]
        self.lsp -= 1
        return val  # (count, start, end)

    def read_lstack(self):
        if self.lsp < 0:
            return (0,None,None)
        val = self.lstack[self.lsp]
        return val  # (count, start, end)

    def push_lstack(self, count, start, end):
        if self.lsp < LSTACK_SIZE - 1:
            self.lsp += 1
            self.lstack[self.lsp] = (count, start, end)

    def show_stack(self, n):
        val = {}
        val['x'] = self.x
        val['y'] = self.y
        val['dir'] = self.dir
        val['pen'] = self.pen
        val['color'] = self.color.ctox()
        val['width'] = self.width
        val['step'] =  self.step
        val['register'] = self.register
        val['sp'] = self.sp
        s = []
        num = min(STACK_SIZE, max(n, 0))
        for i in range(num):
            if (self.sp-i) >= 0:
                s.append(self.stack[self.sp - i])

        val['stack'] = s
        val['lsp'] = self.lsp
        l = []
        num = min(LSTACK_SIZE, max(n, 0))
        for i in range(num):
            if (self.lsp-i) >= 0:
                l.append(self.lstack[self.lsp-i])
        val['lstack'] = l
        
        return val
            
        
    def forward(self, draw):
        p = self.pop_stack(1)  # スタックが空なら1
        distance = self.step*p
        self.lastx = self.x
        self.lasty = self.y
        self.x = self.x + DIR[self.dir][0]*distance
        self.y = self.y + DIR[self.dir][1]*distance
        # print(f'Turtle.Forward: ({self.lastx},{self.lasty}) to Dir={self.dir}/{DIR[self.dir]}, Stack={p}, Step={self.step}, Distance={distance}')
        # print(f'   Pendown={self.pen}, New coord = ({self.x},{self.y})')
        if self.pen:
            r = self.width // 2
            c = tuple(list(self.color.ctoi())+[255])
            draw.line((self.lastx,self.lasty, self.x,self.y),
                      width=self.width, fill=c)
            draw.circle((self.lastx, self.lasty), r,  fill=c)
            draw.circle((self.x, self.y), r,  fill=c)
            
    
    def right(self):
        p = self.pop_stack(1)  # スタックが空なら1
        self.dir = (self.dir + p) % 8
        # print(f'Turtle.Right: result={self.dir}')

    def left(self):
        p = self.pop_stack(1)  # スタックが空なら1    
        self.dir = (self.dir - p) % 8
        # print(f'Turtle.Left: result={self.dir}')
        
    def north(self):
        self.dir = 0

    def head(self):
        p = self.pop_stack()    
        self.dir = p % 8

    def set_color(self):
        b = self.pop_stack()
        g = self.pop_stack()
        r = self.pop_stack()
        self.color = RGBColor(r,g,b)

    def pen_up(self):
        self.pen = False

    def pen_down(self):
        self.pen = True

    def pen_width(self):
        p = self.pop_stack(10)  # スタックが空なら10
        if p < MAX_PEN_WIDTH:
            self.width = p

    def jump(self):
        y = self.pop_stack()
        x = self.pop_stack()
        self.last_x = self.x
        self.last_y = self.y
        self.x = x
        self.y = y

    def where(self):
        x = self.x
        y = self.y
        self.push_stack(x)
        self.push_stack(y)

    def dup(self):
        x = self.pop_stack()
        self.push_stack(x)
        self.push_stack(x)

    def drop(self):
        self.pop_stack()

    def exchange(self):
        x = self.pop_stack()
        y = self.pop_stack()
        self.push_stack(x)
        self.push_stack(y)

    def zoom(self):
        x = self.pop_stack()
        self.step = x

    def store(self):
        n = self.pop_stack()
        x = self.pop_stack()  # スタックに元の値は残さない
        if 0 <= n < REGISTER_SIZE:
            self.register[n] = x
        # print(f'Turtle.Store[{n}]: pop {x} into register')

    def restore(self):
        n = self.pop_stack()
        if 0 <= n < REGISTER_SIZE:
            self.push_stack(self.register[n])
        # print(f'Turtle.Retore[{n}]: push {self.register[n]}')

    def calc(self, opcode):
        y = self.pop_stack()
        x = self.pop_stack()
        if opcode == '+':
            self.push_stack(x+y)
        elif opcode == '-':
            self.push_stack(x-y)
        elif opcode == '*':
            self.push_stack(x*y)
        elif opcode == '/':
            self.push_stack(x//y)
        elif opcode == '^':
            if -(2**31)< x**y and x**y < 2**31:
                self.push_stack(x**y)
        else:
             self.push_stack(y)  # do nothing
             self.push_stack(x)

    def unary(self, opcode):
        x = self.pop_stack()
        if opcode == '~':
            self.push_stack(-x)
        else:
            self.push_stack(x)

    def put_text(self, draw, s):
        p = min(64, max(int(self.width*2.4),10))
        font = ImageFont.truetype('meiryob.ttc',p)
        c = tuple(list(self.color.ctoi())+[255])
        draw.text((self.x, self.y), s, c, font=font)
        bbox = draw.textbbox((self.x, self.y), s, font=font)
        self.last_x = self.x
        self.last_y = self.y
        self.x = int(bbox[2])
        self.y = self.y  # 高さは変えない
        # print(f'Turtle.put_text: {s}, bbox=({bbox})')

    def loop_start(self, script, pos):
        loop_counter = self.pop_stack()
        loop_start = pos+1
        lc = 0
        cptr = pos+1
        while cptr < len(script):
            if script[cptr] == '{':
                lc += 1
                # print('Found InnerLoop')
            elif script[cptr] == '}':
                lc -= 1
                if lc < 0:
                    loop_end = cptr
                    # print('Found LoopEND')
                    break
                else:
                    # print('Found InnerLoopEND')
                    pass
            cptr += 1
        if lc >= 0:
            loop_end = len(script) - 1

        self.push_lstack(loop_counter, loop_start, loop_end)
        # print(f'LoopStart {self.show_stack(3)}')

    def loop_end(self, pos):
        c,s,e = self.pop_lstack()
        # print(f'LoopEnd1 {self.show_stack(3)}')
        if e is None:
            print(f'Turtle.loop: Illegal loop end')
            return pos+1
            
        if e == pos:
            c -= 1
            if c <= 0:
                return pos + 1
            else:
                # print(f'LoopEnd2 {self.show_stack(3)}')
                self.push_lstack(c, s, e)
                return s
        print(f'Turtle.loop: Illegal loop clause @ {pos}; {s}-{e}, count={c}')
        return pos+1

    def brk(self, pos):
        f = self.pop_stack()
        c,s,e = self.read_lstack()
        if e is None:
            print(f'Turtle.loop: Illegal break code')
            return pos+1
        if f != 0: # 0以外なら続行
            return pos+1
        else:
            c,s,e = self.pop_lstack()
            return e+1

    def print_stacktop(self, draw):
        t = self.pop_stack()
        self.push_stack(t)
        self.put_text(draw, str(t))
        
    def trace(self):
        val = self.show_stack(3)
        buf = ''

        for x in DEBUG_PR:
            buf += x+': '+str(val[x])+'  '
        print(f'Dump: {buf}')


# コマンドディスパッチテーブル
Commands = {
    'U': Turtle.pen_up,
    'D': Turtle.pen_down,
    'R': Turtle.right,
    'L': Turtle.left,
    'N': Turtle.north,
    'H': Turtle.head,
    'C': Turtle.set_color,
    'P': Turtle.pen_width,
    'J': Turtle.jump,
    'W': Turtle.where,
    ']': Turtle.dup,
    '[': Turtle.drop,
    'X': Turtle.exchange,
    'Z': Turtle.zoom,
    'S': Turtle.store,
    'Q': Turtle.restore,
    '&': Turtle.trace
    }


def turtle_draw(draw, turtle, cmds, verbose=True): #False):
    '''turtle_draw(draw: ImageDraw, turtle: Turtle, cmds: str)'''
    if isinstance(cmds, list):
        cmds =  '\n'.join(cmds)
    if verbose:
        print(f'Command = {cmds}')
    ptr = 0
    while ptr < len(cmds):
        cur = ptr
        # print(f'{ptr}:{cmds[ptr]} ')
        if '0' <= cmds[cur] <= '9':  # 連続数字は数値としてスタックに積む
            while True:
                cur += 1
                if cur >= len(cmds) or not ('0' <= cmds[cur] <= '9'):
                    break
            n = int(cmds[ptr:cur])
            turtle.push_stack(n)
            if verbose:
                print( f'{ptr}: push {n}')
            ptr = cur
        elif cmds[cur] == '"':  # テキスト出力
            while True:
                cur += 1
                if cur >= len(cmds) or cmds[cur] == '"':
                    break
            s = cmds[ptr+1:cur]
            turtle.put_text(draw,s)
            if verbose:
                print( f'{ptr}: Command print("{s}")', turtle.show_stack(3))
            ptr = cur+1
        elif cmds[cur] == '#':  # コメント
            while True:
                cur += 1
                # print(cmds[cur], ord(cmds[cur]))
                if cur >= len(cmds):
                    break
                if ord(cmds[cur]) < 0x20:
                    break
            ptr = cur
        elif cmds[cur].upper() == 'F':  # Fコマンドだけdrawを渡すので別
            if verbose:
                print( f'{ptr}: Command "F"', turtle.show_stack(3))
            turtle.forward(draw)
            ptr += 1
        elif cmds[cur] == '?':
            if verbose:
                print( f'{ptr}: Command "?"', turtle.show_stack(3))
            turtle.print_stacktop(draw)
            ptr += 1
        elif cmds[cur] in Opcode:  # 二項演算子
            if verbose:
                print( f'{ptr}: Calc "{cmds[cur]}"', turtle.show_stack(3))
            turtle.calc(cmds[cur])
            ptr += 1
        elif cmds[cur] in Unary:  # 単項演算子
            if verbose:
                print( f'{ptr}: Unary "{cmds[cur]}"', turtle.show_stack(3))
            turtle.unary(cmds[cur])
            ptr += 1
        elif cmds[cur] == '{':
            if verbose:
                print( f'{ptr}: loopstart "{cmds[cur]}"', turtle.show_stack(3))
            turtle.loop_start(cmds, cur)
            ptr += 1
        elif cmds[cur] == '}':
            if verbose:
                print( f'{ptr}: loopend "{cmds[cur]}"', turtle.show_stack(3))
            ptr = turtle.loop_end(cur)
        elif cmds[cur] == '!':
            if verbose:
                print( f'{ptr}: break "{cmds[cur]}"', turtle.show_stack(3))
            ptr = turtle.brk(cur)
        else:  # その他のコマンドはディスパッチテーブルで
            if verbose:
                print( f'{ptr}: Command "{cmds[cur]}"', turtle.show_stack(3))
            try:
                Commands[cmds[cur].upper()](turtle)
            except KeyError:
                pass
            ptr += 1
            
    # interpreter end


def generate(p: Param, command=''):
    """
    指定されたパラメータに基づいて、turtleで画像生成する
    """
    width = p.width
    height = p.height
    pen_color = p.color1
    bg_color = p.color2
    jitter = clip8(p.color_jitter)
    pen_size = min(max(p.pwidth,1),200)
    pen_step = min(max(p.pheight,1),100)
    start_x = p.width // 2
    start_y = p.height // 2
    intrctv = p.pdepth == 0
    if command == '':
        # print('command = Null str')
        cmd = tur_preserve['cmd']
    else:
        # print(f'given command: {command}')
        cmd = command
    if isinstance(cmd, list):
        cmd = ''.join(cmd)
    
    turtle = Turtle(size=pen_size, step=pen_step, color=pen_color,
                    x=start_x, y=start_y)

    # 描画イメージの生成
    image = Image.new('RGBA',(width, height),(0,0,0,0))
    draw = ImageDraw.Draw(image)
        
    turtle_draw(draw, turtle, cmd, verbose=False)
    # print(cmd)

    if p.h_img is None:
        bg_start = rgb_random_jitter(bg_color, jitter)
        bg_end   = rgb_random_jitter(bg_color, jitter)
        bg = diagonal_gradient_rgb(width, height, bg_start, bg_end)
    else:
        bg = p.bg(width, height)

    bg = bg.convert('RGBA')
    bg.alpha_composite(image)

    return bg
    

if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    

    print(f'\n==========\nParameters = {p}\n==========\n')
    
    image = generate(p)
    image.show()

