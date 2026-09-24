from wall_common import *
import numpy as np
from PIL import Image, ImageDraw
import TkEasyGUI as sg

# --- Global 変数の設定 ---
ITERATION = 6
LINE_WIDTH = 8
#LINE_COLOR = (240, 170, 120)
#BG_COLOR = (90, 100, 120)
JITTER = 40
ANGLE = 12

curves_preserv = {'type': 'sierpinski',
                  'crop': 'box'}

# 座標生成関数登録用デコレータ
FN = {}
def regi(func):
    FN[func.__name__] = func
    return func


# ==========================================================================
# モジュール共通処理
# ==========================================================================
def intro(modlist: Modules, module_name):
    """module基本情報"""
    modlist.add_module(
        module_name,
        '再帰曲線',
        {
            'color1': '線色',
            'color2': '地色',
            'color_jitter': '色ゆらぎ',
            'pwidth': '次数',
            'pheight': '線幅',
            'pdepth': '回転角',
        }
    )
    return module_name


def default_param(p: Param):
    """おすすめパラメータ"""
    r, g, b = tuple(map(int, np.random.randint(0, 256, 3)))

    p.color1 = RGBColor(r,g,b)
    p.color2 = RGBColor(255-r,255-g,255-b)
    p.color_jitter = JITTER

    p.pwidth = ITERATION
    p.pheight = LINE_WIDTH
    p.pdepth = ANGLE

    return p


# ==========================================================================
# シェルピンスキー曲線
# ==========================================================================
@regi
def sierpinski(iteration: int, step_length: float = 10.0) -> np.ndarray:
    """ シェルピンスキ曲線の頂点座標リストを生成
    (PILの座標系 [右: +X, 下: +Y] に完全対応)
    
    :param iteration: 次数 (1以上の整数)
    :param step_length: 各ステップの移動距離
    :return: (N, 2) の float64 型 NumPy 配列
    """
    if iteration < 1:
        #raise ValueError("iteration は 1 以上の整数を指定してください。")
        return None
    elif iteration > 9:
        iteration = 9

    diag = step_length / np.sqrt(2)

    # 8つの移動ベクトル (0:→, 1:↘, 2:↓, 3:↙, 4:←, 5:↖, 6:↑, 7:↗)
    # PIL等の画面座標系 (右:+X, 下:+Y) にあわせた正確なベクトル定義
    dir_vecs = np.array([
        [ step_length,          0.0],  # 0: 右 (→)
        [        diag,         diag],  # 1: 右下 (↘)
        [         0.0,  step_length],  # 2: 下 (↓)
        [       -diag,         diag],  # 3: 左下 (↙)
        [-step_length,          0.0],  # 4: 左 (←)
        [       -diag,        -diag],  # 5: 左上 (↖)
        [         0.0, -step_length],  # 6: 上 (↑)
        [        diag,        -diag]   # 7: 右上 (↗)
    ], dtype=np.float64)

    # L-system 規則による方向インデックスの生成
    def expand_A(d):
        if d == 0: return []
        return (expand_A(d-1) + [1] + expand_B(d-1) + [0] +
                expand_D(d-1) + [7] + expand_A(d-1))

    def expand_B(d):
        if d == 0: return []
        return (expand_B(d-1) + [3] + expand_C(d-1) + [2] +
                expand_A(d-1) + [1] + expand_B(d-1))

    def expand_C(d):
        if d == 0: return []
        return (expand_C(d-1) + [5] + expand_D(d-1) + [4] +
                expand_B(d-1) + [3] + expand_C(d-1))

    def expand_D(d):
        if d == 0: return []
        return (expand_D(d-1) + [7] + expand_A(d-1) + [6] +
                expand_C(d-1) + [5] + expand_D(d-1))

    # 全体を結ぶ外周ループ
    moves = (
        expand_A(iteration) + [1] +
        expand_B(iteration) + [3] +
        expand_C(iteration) + [5] +
        expand_D(iteration) + [7]
    )

    # NumPyの累積和 (cumsum) で全頂点座標を一括計算
    move_indices = np.array(moves, dtype=np.int32)
    step_vectors = dir_vecs[move_indices]

    # 原点 (0, 0) からスタートして順に移動結果を蓄積
    points = np.zeros((len(step_vectors) + 1, 2), dtype=np.float64)
    np.cumsum(step_vectors, axis=0, out=points[1:])
    # 最後の点から最初の原点(0,0)へ接続する点を追加
    points = np.vstack([points, points[0]])
    
    return points


# ==========================================================================
# ヒルベルト曲線 (Hilbert Curve)
# ==========================================================================
@regi
def hilbert(iteration: int, step_length: float = 10.0) -> np.ndarray:
    """ ヒルベルト曲線の座標列を生成します。 """
    
    if iteration < 1:
        #raise ValueError("iteration は 1 以上の整数を指定してください。")
        return None
    elif iteration > 9:
        iteration = 9

    # L-system 規則
    # A -> - B F + A F A + F B -
    # B -> + A F - B F B - F A +
    # F: 前進, +: 右回転(90°), -: 左回転(-90°)
    def expand_A(d):
        if d == 0: return []
        return ['-'] + expand_B(d-1) + ['F', '+'] + expand_A(d-1) + ['F'] + expand_A(d-1) + ['+', 'F'] + expand_B(d-1) + ['-']

    def expand_B(d):
        if d == 0: return []
        return ['+'] + expand_A(d-1) + ['F', '-'] + expand_B(d-1) + ['F'] + expand_B(d-1) + ['-', 'F'] + expand_A(d-1) + ['+']

    commands = expand_A(iteration)

    # 方向定義 (0:右, 1:下, 2:左, 3:上) - PIL座標系
    dirs = np.array([
        [step_length, 0.0],
        [0.0, step_length],
        [-step_length, 0.0],
        [0.0, -step_length]
    ], dtype=np.float64)

    curr_dir = 0  # 最初は右向き
    move_vectors = []

    for cmd in commands:
        if cmd == 'F':
            move_vectors.append(dirs[curr_dir])
        elif cmd == '+':
            curr_dir = (curr_dir + 1) % 4
        elif cmd == '-':
            curr_dir = (curr_dir - 1) % 4

    step_vectors = np.array(move_vectors, dtype=np.float64)
    
    points = np.zeros((len(step_vectors) + 1, 2), dtype=np.float64)
    np.cumsum(step_vectors, axis=0, out=points[1:])

    return points


# ==========================================================================
# ペアノ曲線 (Peano Curve)
# ==========================================================================
@regi
def peano(iteration: int, step_length: float = 10.0) -> np.ndarray:
    """ ペアノ（Peano）曲線の座標列を生成します。 """
    if iteration < 1:
        #raise ValueError("iteration は 1 以上の整数を指定してください。")
        return None
    elif iteration > 5:
        iteration = 5

    # ペアノ曲線のL-systemルール定義
    # F: 前進, +: 右90度回転, -: 左90度回転
    
    # X: XFYF X+F+ YFXF Y-F- XFYF X
    def expand_X(d):
        if d == 0: return []
        return (
            expand_X(d-1) + ['F'] + expand_Y(d-1) + ['F'] +
            expand_X(d-1) + ['+'] + ['F'] + ['+'] +
            expand_Y(d-1) + ['F'] + expand_X(d-1) + ['F'] +
            expand_Y(d-1) + ['-'] + ['F'] + ['-'] +
            expand_X(d-1) + ['F'] + expand_Y(d-1) + ['F'] +
            expand_X(d-1)
        )

    # Y: YFXF Y-F- XFYF X+F+ YFXF Y
    def expand_Y(d):
        if d == 0: return []
        return (
            expand_Y(d-1) + ['F'] + expand_X(d-1) + ['F'] +
            expand_Y(d-1) + ['-'] + ['F'] + ['-'] +
            expand_X(d-1) + ['F'] + expand_Y(d-1) + ['F'] +
            expand_X(d-1) + ['+'] + ['F'] + ['+'] +
            expand_Y(d-1) + ['F'] + expand_X(d-1) + ['F'] +
            expand_Y(d-1)
        )

    # コマンド列の展開
    commands = expand_X(iteration)

    # 方向定義 (0:右, 1:下, 2:左, 3:上) - PIL座標系
    dirs = np.array([
        [step_length, 0.0],
        [0.0, step_length],
        [-step_length, 0.0],
        [0.0, -step_length]
    ], dtype=np.float64)

    curr_dir = 0  # 最初は右向き
    move_vectors = []

    # コマンドを移動ベクトル列に変換
    for cmd in commands:
        if cmd == 'F':
            move_vectors.append(dirs[curr_dir])
        elif cmd == '+':
            curr_dir = (curr_dir + 1) % 4
        elif cmd == '-':
            curr_dir = (curr_dir - 1) % 4

    step_vectors = np.array(move_vectors, dtype=np.float64)

    # NumPy の 累積和(cumsum) で座標配列を一括生成
    points = np.zeros((len(step_vectors) + 1, 2), dtype=np.float64)
    np.cumsum(step_vectors, axis=0, out=points[1:])

    return points


# ==========================================================================
# ゴスパー曲線
# ==========================================================================
@regi
def gosper(iteration: int, step_length: float = 10.0) -> np.ndarray:
    """
    ゴスパー（Gosper）曲線の座標列を生成します。
    (PILの座標系 [右: +X, 下: +Y] に対応)
    
    :param iteration: 次数 (1以上の整数)
    :param step_length: 各ステップの移動距離
    :return: (N, 2) の float64 型 NumPy 配列
    """
    if iteration < 1:
        raise ValueError("iteration は 1 以上である必要があります。")

    # L-system 展開ルール
    def expand_A(d):
        if d == 0: return ['A']
        return (
            expand_A(d-1) + ['+'] + expand_B(d-1) + ['+', '+'] + expand_B(d-1) +
            ['-'] + expand_A(d-1) + ['-', '-'] + expand_A(d-1) + expand_A(d-1) +
            ['-'] + expand_B(d-1) + ['+']
        )

    def expand_B(d):
        if d == 0: return ['B']
        return (
            ['-'] + expand_A(d-1) + ['+'] + expand_B(d-1) + expand_B(d-1) +
            ['+', '+'] + expand_B(d-1) + ['+'] + expand_A(d-1) +
            ['-', '-'] + expand_A(d-1) + ['-'] + expand_B(d-1)
        )

    # コマンド列の展開 (公理: A)
    commands = expand_A(iteration)

    # 60度ごとの6方向ベクトルをあらかじめ計算 (PIL座標系: +Yが下)
    angles_rad = np.radians(np.arange(0, 360, 60))
    # 0: 0°, 1: 60°(右下), 2: 120°(左下), 3: 180°(左), 4: 240°(左上), 5: 300°(右上)
    dirs = np.stack([
        step_length * np.cos(angles_rad),
        step_length * np.sin(angles_rad)
    ], axis=1)

    curr_dir = 0  # 初期方向: 0度 (右向き)
    move_vectors = []

    # コマンド列を解析して移動ベクトルに変換
    for cmd in commands:
        if cmd in ('A', 'B'):
            move_vectors.append(dirs[curr_dir])
        elif cmd == '+':
            # 左折 (PIL座標系では反時計回り -> インデックスを減らす)
            curr_dir = (curr_dir - 1) % 6
        elif cmd == '-':
            # 右折 (PIL座標系では時計回り -> インデックスを増やす)
            curr_dir = (curr_dir + 1) % 6

    step_vectors = np.array(move_vectors, dtype=np.float64)

    # 原点 (0, 0) からスタートして累積和 (cumsum) で全頂点座標を一括計算
    points = np.zeros((len(step_vectors) + 1, 2), dtype=np.float64)
    np.cumsum(step_vectors, axis=0, out=points[1:])

    return points


# ==========================================================================
# 座標列の回転・拡縮
# ==========================================================================
def calculate_inscribed_radius(pts_centered: np.ndarray,
                               num_sectors: int = 360) -> float:
    """
    セクタ内で最も外側にある「境界点」を抽出し、
    境界点群の中で最も中心に近い距離（真の内接円半径）を算出する
    """
    # 角度（-π ～ +π）と距離を計算
    angles = np.arctan2(pts_centered[:, 1], pts_centered[:, 0])
    distances = np.hypot(pts_centered[:, 0], pts_centered[:, 1])

    # セクター分割し、各角度方向での「最も遠い点（＝境界点）」を抽出
    sector_indices = np.digitize(angles,
                                 np.linspace(-np.pi, np.pi, num_sectors))
    boundary_distances = []
    for s in range(1, num_sectors + 1):
        mask = (sector_indices == s)
        if np.any(mask):
            boundary_distances.append(distances[mask].max())

    # 境界点群の中で、最も中心に近い距離 ＝ 最大内接円の半径 R_min
    if boundary_distances:
        return float(np.min(boundary_distances))
    else:
        return float(distances.max())

def rotate_and_scale_points(
    points: np.ndarray, 
    angle_deg: float, 
    target_w: int, 
    target_h: int, 
    cover_mode: str = 'circle'
) -> np.ndarray:
    """
    矩形・非矩形問わず、回転後に画面(target_w, target_h)へ余白を出さずに収める
    汎用回転・スケール関数。
    
    :param points: (N, 2) の座標配列
    :param angle_deg: 回転角度（度数法）
    :param target_w: 描画先の幅
    :param target_h: 描画先の高さ
    :param cover_mode: 
        'circle': 内接円ベース（ゴスパー曲線など非矩形領域向け）
        'box': 従来の矩形ベース（正方形充填曲線向け）
    """
    if points.size == 0:
        return points

    # 重心を原点 (0,0) に移動
    center = points.mean(axis=0)
    pts_centered = points - center
    cover_mode = curves_preserv['crop']

    if cover_mode == 'circle':
        # 内接円ベースのスケール計算
        # 画面の四隅（対角線）を完全に覆うために必要な半径
        r_target = np.hypot(target_w, target_h) / 2.0
        
        # 重心から内接円への距離
        r_min = calculate_inscribed_radius(pts_centered, num_sectors=60)
        
        # 倍率算出
        scale = r_target / max(r_min, 1e-6)
        # print(f'Inscribed_circle_crop scale = {scale}')

    else:
        # 矩形ベース（正方形領域向け）
        min_xy = pts_centered.min(axis=0)
        max_xy = pts_centered.max(axis=0)
        orig_w, orig_h = max_xy - min_xy

        rad = np.radians(angle_deg)
        cos_a = abs(np.cos(rad))
        sin_a = abs(np.sin(rad))

        needed_w = target_w * cos_a + target_h * sin_a
        needed_h = target_w * sin_a + target_h * cos_a

        scale = max(needed_w / orig_w, needed_h / orig_h)

    # スケーリング、回転(PILの Y軸下向き座標系)
    pts_scaled = pts_centered * min(scale, 12.0)  # 倍率が極端に大きければ制限
    rad = np.radians(angle_deg)
    R = np.array([
        [np.cos(rad), -np.sin(rad)],
        [np.sin(rad),  np.cos(rad)]
    ], dtype=np.float64)

    return pts_scaled @ R.T  # Rの転置行列を乗算


# ==========================================================================
# 座標列の描画
# ==========================================================================
def draw_curve(points: np.ndarray, line_width, pen_color, padding=0):
    """
    NumPy配列の座標を受け取り、RGBAのPIL Imageに描画します。
    
    :param points: shape (N, 2) の NumPy 配列
    :param line_width: 線の太さ（ピクセル）
    :param pen_color: ペンの色 RGBA タプル
    :param bg_color: 背景色 RGBA タプル
    :param padding: 画像外周のマージン（ピクセル）
    :return: PIL Image オブジェクト
    """
    bg_color = (0, 0, 0, 0)
    
    if points.size == 0 or points.ndim != 2 or points.shape[1] != 2:
        img = Image.new('RGBA', (800,600), bg_color)
        dr = ImageDraw.Draw(img)
        dr.text((0,0),'points must be Numpy array in shape (N,2)',
                fill='white')
        return img


    # NumPyのベクトル演算でバウンディングボックスの計算
    min_xy = points.min(axis=0)
    max_xy = points.max(axis=0)

    bbox_size = max_xy - min_xy
    width = int(np.ceil(bbox_size[0])) + padding * 2
    height = int(np.ceil(bbox_size[1])) + padding * 2

    # 原点を移動してパディングを追加（NumPyで一括計算）
    transformed_points = points - min_xy + padding

    # RGBA画像の作成
    image = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(image)

    # PIL.ImageDraw.line に渡すため、(N, 2) 配列を (N, 2) のリスト構造、
    # または [x1, y1, x2, y2, ...] のフラットなタプル群にキャスト
    flat_points = transformed_points.reshape(-1).tolist()

    # 線を描画 (joint="round" で角を丸める)
    draw.line(flat_points, fill=pen_color, width=line_width, joint="curve")

    return image


# ==========================================================================
# 詳細設定
# ==========================================================================
def prev(name,dflt):
    ret = curves_preserv[name]
    if ret is None:
        if isinstance(dflt, (list, tuple)):
            ret = dflt[0]
        else:
            ret = dflt
    return ret

def smodified(name, val):
    if curves_preserv[name] == val:
        return False
    else:
        curves_preserv[name] = val
        return True

def pmodified(p, name, val, lo=None):
    val = stoi(val)
    if getattr(p, name) == val:
        return False
    else:
        if lo is not None:
            val = max(val, lo)
        setattr(p, name, val)
        return True

def desc(p):
    items = list(FN.keys())
    crop_methods = ['circle', 'box']

    idim = p.pwidth
    lwidth = p.pheight
    angl = p.pdepth
    
    key = prev('type', items)
    crop = prev('crop', crop_methods)

    lo =[[sg.Text('Select type'),
          sg.Combo(items, readonly=True, default_value=key,
                   size=(12,1), key='-item-')
          ],
         [sg.Text('Crop Method'),
          sg.Combo(crop_methods, readonly=True, default_value=crop,
                   size=(5,1), key='-crop-'),
          ],
         [sg.Text('Non square curve like gosper, choose crop circle',
                  pad=1, text_color='#333388')],
         [sg.Text('Iteration'), sg.Input(f'{idim}', key='-ite-', width=3),
          sg.Text(' LineWidth'), sg.Input(f'{lwidth}', key='-lwd-', width=3),
          sg.Text(' Angle'), sg.Input(f'{angl}', key='-agl-', width=4),
          ],
         [sg.Text(expand_x=True),
          sg.Button('Cancel', key='-can-', background_color='#ffdddd'),
          sg.Button('Select', key='-ok-', background_color='#ddffdd'),
          ],
         [sg.Text('* If deep iteration and thick line outputs flat image,',
                  pad=1, text_color='#333388')],
         [sg.Text('then try less iteration-depth or thin width.',
                  pad=1, text_color='#333388')
          ]]
    wn = sg.Window('Curves', layout=lo)
    mod = False

    while True:
        ev, va = wn.read()

        if ev in ('-can-', sg.WINDOW_CLOSED):
            break
        elif ev == '-ok-':
            mod = True
            break
        
    wn.close()

    if mod:
        mod = smodified('type', va['-item-'])
        mod |= smodified('crop', va['-crop-'])
        mod |= pmodified(p, 'pwidth', va['-ite-'], lo=1)
        mod |= pmodified(p, 'pheight', va['-lwd-'], lo=1)
        mod |= pmodified(p, 'pdepth', va['-agl-'])

        if mod:
             return generate(p)
    return


# ==========================================================================
# generate
# ==========================================================================
def generate(p: Param):

    width = p.width
    height = p.height

    line_color = p.color1.ctoi()
    bg_color = p.color2.ctoi()

    iteration = max(p.pwidth, 1)
    line_width = max(p.pheight, 1)
    angle = p.pdepth
    jitter = p.color_jitter

    ct = curves_preserv['type']
    if ct in FN.keys():
        #print(f'{ct} iteration={iteration}')
        pts = FN[ct](iteration, step_length=25.0)
    else:
        ct = next(iter(FN))
        #print(f'Fallback({ct}) iteration={iteration}')
        pts = FN[ct](iteration, step_length=25.0)
        curves_preserv['type'] = ct

    if pts is not None:
        pts = rotate_and_scale_points(pts, angle, width, height)
        image = draw_curve(pts, line_width, tuple([*line_color,255][:4]))
        iw, ih = image.size

        ox = (iw - width) // 2
        oy = (ih - height) // 2

        image = image.crop((ox, oy, ox + width, oy + height))
    else:
        image = Image.new("RGBA", (width, height), (0,0,0,0))

    if p.h_img is None:
        bg_start = rgb_random_jitter(bg_color, jitter)
        bg_end = rgb_random_jitter(bg_color, jitter)

        bg = diagonal_gradient_rgb(width, height, bg_start, bg_end)
    else:
        bg = p.bg(width, height)

    bg = bg.convert('RGBA')
    bg.alpha_composite(image)

    return bg


# ==========================================================================
# Test
# ==========================================================================

if __name__ == '__main__':

    p = Param()
    p = default_param(p)

    p.width = 1920
    p.height = 1080

    image = generate(p)
    image.show()
