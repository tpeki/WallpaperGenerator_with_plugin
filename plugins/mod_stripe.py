from PIL import Image, ImageDraw
import random
from wall_common import *

# --- 定数設定 ---
BASE_R, BASE_G, BASE_B = 239, 168, 62  # 基本色
STRIPE_WIDTH = 17  # タイルの幅
TILE_HEIGHT = 140  # タイルの高さ
DIFF_STRIPE = 48  # ストライプ毎の色の最大変化幅
DIFF_TILE = 27  # タイル毎の色の最大変化幅

# module基本情報
def intro(modlist: Modules, module_name):
    modlist.add_module(module_name, 'ストライプ(タイル)',
                       {'color1':'基本色', 'color_jitter':'基本色変化',
                        'sub_jitter':'タイル色変化',
                        'pwidth':'列幅', 'pheight':'タイル長'})
    return module_name


# おすすめパラメータ
def default_param(p: Param):
    p.color1.itoc( BASE_R, BASE_G, BASE_B)
    p.pwidth = STRIPE_WIDTH
    p.pheight = TILE_HEIGHT
    p.color_jitter = DIFF_STRIPE
    p.sub_jitter = DIFF_TILE
    return p

# 画像生成
def generate(p: Param):
    """
    指定されたパラメータに基づいて、列ごとにY座標がランダムにずれたタイル状の画像を生成します。
    """
    width = p.width
    height = p.height
    stripe_width = min(max(p.pwidth,1),width)
    stripe_height = min(max(p.pheight,1),height)
    
    base_r, base_g, base_b = p.color1.ctoi()
    eps = p.color_jitter
    zeta = p.sub_jitter
    
    orig_height = height
    height = height + stripe_height
    
    image = Image.new("RGB", (width, height),
                      color=(base_r, base_g, base_b))
    draw = ImageDraw.Draw(image)

    last_y_offset = 0
    granurality = min(5, stripe_height/10)
    y_rand_max = int(stripe_height/granurality)

    # 各列の処理
    for x in range(0, width, stripe_width):
        # 列ごとにランダムなYオフセットを決定
        # タイル高さの範囲内でランダムにずらす
        while True:
            column_y_offset = random.randint(0, y_rand_max) * granurality
            if column_y_offset != last_y_offset:
                break
        last_y_offset = column_y_offset
        
        # この列全体で使用する基本色からの変化量を決定
        # 列全体で色が統一されるように調整
        color_offset_r = random.randint(-eps, eps)
        color_offset_g = random.randint(-eps, eps)
        color_offset_b = random.randint(-eps, eps)

        # この列のタイルを描画
        # オフセットを考慮してY座標を計算
        start_y = column_y_offset - stripe_height * (column_y_offset // stripe_height)
        
        while start_y < height:
            # 各タイル固有の色を生成（基本色＋列オフセット＋微調整）
            tile_color_r = max(0, min(255, base_r + color_offset_r +
                                      random.randint(-zeta, zeta)))
            tile_color_g = max(0, min(255, base_g + color_offset_g +
                                      random.randint(-zeta, zeta)))
            tile_color_b = max(0, min(255, base_b + color_offset_b +
                                      random.randint(-zeta, zeta)))

            end_y = start_y + stripe_height
            
            # 画像の境界内で描画領域をクリップ
            draw_start_y = max(0, start_y)
            draw_end_y = min(height, end_y)
            draw_end_x = min(width, x + stripe_width)

            if draw_end_y > draw_start_y and draw_end_x > x:
                 draw.rectangle([x, draw_start_y, draw_end_x, draw_end_y], fill=(tile_color_r, tile_color_g, tile_color_b))
            
            start_y += stripe_height # 次のタイルへ
        
    image = image.crop((0, stripe_height, width, height))
    return image


if __name__ == '__main__':
    p = Param()
    p = default_param(p)
    p.width = 1920
    p.height = 1080
    image = generate(p)
    image.show()
