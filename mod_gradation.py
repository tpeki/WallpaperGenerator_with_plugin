import numpy as np
from PIL import Image
from wall_common import *

START_COLOR = (0x11, 0x11, 0x66)
END_COLOR = (0x11, 0x60, 0x00)
MID_COLOR = (0x66, 0x44, 0x33)
MODE = 3
ANGLE = 45
MIDDLE_POINT = 60


def intro(modlist: Modules, module_name):
    '''module基本情報'''
    modlist.add_module(module_name,
                       '染め分け/単純グラデーション 色数3色まで',
                       {'color1':'始色', 'color2':'終色', 'color3':'中間色',
                        'color_jitter':'色数(1-3)',
                        'pwidth':'角度', 'pheight':'中間位置%'})
    return module_name


def default_param(p: Param):
    '''おすすめパラメータ'''
    p.color1.itoc(*START_COLOR)
    p.color2.itoc(*END_COLOR)
    p.color3.itoc(*MID_COLOR)
    p.color_jitter = MODE
    p.pwidth = ANGLE
    p.pheight = MIDDLE_POINT
    return p


def generate(p: Param):
    """指定した角度で2～3色のグラデーション画像を生成する。"""

    width, height = p.width, p.height
    color1 = p.color1.ctoi()
    color2 = p.color2.ctoi()
    color3 = p.color3.ctoi()
    mode = p.color_jitter  # 利用色数 1はベタ塗り、3は中間色を入れて補間
    angle_rad = np.deg2rad(p.pwidth)  # degee(整数)を指定
    mid = min(max(p.pheight, 0), 100)  # 中間色位置(相対位置を%で指定)

    if mode <= 1:
        return Image.new('RGB', (width, height), color1)
    elif mode > 2:
        return tricolor(width, height, color1, color2, color3, mid, angle_rad)
   
    # 座標グリッドを作成 (y, x)
    y, x = np.ogrid[:height, :width]
    
    # 指定された角度方向への投影距離を計算
    # 角度に応じて座標の重みを決定する
    # cos(theta) * x + sin(theta) * y
    projection = x * np.cos(angle_rad) + y * np.sin(angle_rad)
    
    # 投影値を 0.0 ～ 1.0 の範囲に正規化
    p_min, p_max = projection.min(), projection.max()
    norm_projection = (projection - p_min) / (p_max - p_min)
    
    # 各チャンネル(R, G, B)ごとに補間計算
    # (height, width, 3) の配列を作成
    result = np.zeros((height, width, 3), dtype=np.uint8)
    for i in range(3):
        # 線形補間: color1 + (color2 - color1) * ratio
        result[..., i] = color1[i] + (color2[i] - color1[i]) * norm_projection
        
    return Image.fromarray(result, 'RGB')


def tricolor(width: int, height: int,
             color1, color2, color3, mid: int, angle_rad: float):
    """
    3色を指定した比率で経由するグラデーションを生成する。
    :param mid: color3が配置される位置(%)
    """
    y, x = np.ogrid[:height, :width]
    
    # 投影距離の計算
    projection = x * np.cos(angle_rad) + y * np.sin(angle_rad)
    
    # 0.0 ～ 1.0 に正規化
    p_min, p_max = projection.min(), projection.max()
    norm_projection = (projection - p_min) / (p_max - p_min)
    
    # 各チャンネルの計算
    result = np.zeros((height, width, 3), dtype=np.uint8)
    
    # 補間ポイントの定義
    # xp: 投影比率 [0.0, midポイント, 1.0]
    xp = [0.0, mid / 100.0, 1.0]
    
    for i in range(3):
        # 各色のi番目の成分を取り出し、補間に使う
        # fp: 対応するRGB値 [color1[i], color3[i], color2[i]]
        fp = [color1[i], color3[i], color2[i]]
        
        # np.interpで一括補間（これが非常に高速です）
        result[..., i] = np.interp(norm_projection, xp, fp)
        
    return Image.fromarray(result, 'RGB')


if __name__ == '__main__':
    p = Param()
    p.width = 1920
    p.height = 1080
    p = default_param(p)
    img = generate(p)
    img.show()
