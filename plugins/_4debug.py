# モジュールデバッグ用モジュール
# 親ディレクトリを import対象(sys.path) に追加する
#
# 使い方例:
# if __name__ == '__main__':
#     import _4debug
# from wall_common import *

import sys
from pathlib import Path

# 今のスクリプトの親ディレクトリを取得
parent = Path(__file__).resolve().parent.parent

# sys.path に追加
sys.path.append(str(parent))
# 親ディレクトリにあるモジュールを import 可に

