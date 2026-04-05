# wallpaper.pyw		壁紙用のシンプルなイメージを生成する
V2.2.0  2026/03/16 efxの事は棚上げ中

## 概要
複雑なことは(あまり)しません。
Wallpaper用の画像を生成します。

## 必要ライブラリ
Pythonのライブラリとして、以下のものを利用します。pipなどでライブラリをインストールして利用してください。 作成時点の各バージョンを()で追記してあります
- pillow  (12.0.0)
- TkEasyGUI  (1.0.40)
- numpy (2.2.6)

## 利用方法
一式を同じディレクトリに配置し、pythonにパスが通っている環境で wallpaper.pyw スクリプトを起動してください。
上記ライブラリが入っていれば、モジュール(mod_*.py)が読み込まれた後、GUIが表示されます。

- メニュー 
 - File → 表示されている画像のSave、プログラムの終了
 -  modules → moduleの切替え (切替えるとパラメータは初期値に戻ります)
- 画像下のパラメータを適宜変更してください。
- 右下のRedoボタンを押すと、基本色から乱数で振ったタイルパターンを再作成します。
- 右下のSaveボタンを押すと、表示されているパターンをPNGで保存します。
- Quitボタンは、何もせずに終了します。

なお、画像ファイルの幅・高さはFHDサイズ(1920x1080)でスクリプトに埋め込んでいるので、ほかのサイズにしたい場合はスクリプトを直接修正してください。

一部のモジュールは、サンプル画像をクリックすると追加設定画面を呼び出します。おおむね、applyで設定反映、cancelで追加設定の変更をキャンセルします。

## コマンドラインパラメータ
```
usage: wallpaper.pyw [-h] [- plugin_dir PLUGI _DIR] [--list_mod les] [--module 
                    [--height HEIGHT] [--color1 COLOR1] [--color2 COLOR2] [--color3 COLOR3] [--jitter1 JITTER1]
                    [--jitter2 JITTER2] [--jitter3 JITTER3] [--pheight PHEIGHT] [--pwidth PWIDTH] [--pdepth PDEPTH]
                    [files ...]

--width w  --height h : 生成画像サイズを指定
--plugin_dir dirname : プラグインの読み込みディレクトリを指定します。デフォルトは実行スクリプトのあるディレクトリです
--list_modules : 組み込まれるモジュール名の一覧を表示します。 でも.pywなので--helpも--list_modulesも表示されません。悲しみ。

 (以下はバッチ実行時のみ有効なコマンドラインパラメータ)
--moduke modulename ： 指定したモジュールを読み込み、バッチ実行します。ファイル指定があればファイル出力、なければ既定のイメージビューアで表示
--color1 #rrggbb : 基本色color1 (同様にcolor2, color3もあり) を指定します。
--jitter1 n : 基本色変化幅jitter1 (同様にjitter2、jitter3) を指定します。
--pwidth n  --pheight n  --pdepth n : パターンの大きさ/再帰次数など、形状変化パラメータを指定します。
※ ただし、モジュールによってどのパラメータをどういう使い方にしているかが異なるため、GUI版でパラメータを変えた際の違いを確認してください。
```
## モジュール

 　　壁紙パターンをmod_*.py で追加できます

- bias: 斜め帯
- chevron: ギザギザボーダー
- dune: 砂丘？
- emoji: 絵文字(0:敷石 1:螺旋)   (プレビュークリックで拡張設定)
- flowerworks スピログラフをランダム/グリッド配置で
- footprint: 足跡 (直線か時計回りのみ対応) 
- gangi: 階段
- garland: 垂れ幕  もしくは連提灯通り  間隔を両方マイナスにするとポルカドット
- gladation: 染め分け/角度指定グラデーション 色数3だと中間色設定あり 色数1はベタ塗り
- hexmap: グラデ六角タイル  color1=whiteの場合6色タイルに
- hexmaze: 森の六角迷路
- hilbert: ヒルベルト曲線
- memphis: メンフィス風
- packingbubble: グラデーション泡
- peano: ペアノ曲線
- penrose: ペンローズタイル
- scallop: ホタテ貝
- sprites: スプライトまみれ  (プレビュークリックでスプライトセットエディタ起動)
- stripe: 縦ストライプ・モダン
- tartan: タータン風チェック (プレビュークリックで柄エディタを起動)
- tiles: 正方形タイル (mode: 0=3色ミックス, 1=2色市松, 2=パース)
- turtle: タートルコマンド描画 (プレビュークリックでコマンドエディタ起動)
- waves: 青海波

## 効果モジュール

　　実装方法を検討中； efx_*.py

- shade: 型抜きして影付きで貼り付け

## Turtle Graphics

- タートルグラフィクスっぽいスタックベースのスクリプトを用意しました。
- 基本は数値を積む、コマンドで消費して結果を積む、という動きになります。

| コマンド      | 内容                                                         |
| ------------- | ------------------------------------------------------------ |
| F             | スタック先頭をPOPし、数値だけ前進                            |
| L/R           | スタック先頭をPOPし、その数だけCW/CCWに45°方向転換           |
| N             | タートルの方向を北(0°)に設定                                 |
| H             | スタック先頭をPOPし、その数値の向きにタートルの方向を設定(0..7) |
| U/D           | ペンを上げる/下げる (ペンダウンで移動すると足跡を描画する)   |
| C             | スタック先頭から3つpop(b,g,r)してペン色を(r,g,b)に設定       |
| P             | スタック先頭をPOPし、ペン幅を設定                            |
| J             | スタック先頭から2値(y,x)をPOPし、タートル座標を設定          |
| , (カンマ)    | 数値をスタック先頭に積む                                     |
| Z             | スタック先頭をPOPし、1歩の長さをそのピクセル数にする         |
| X             | スタック先頭の2値を入れ替える                                |
| ]             | スタック先頭の値を複製して積む                               |
| [             | スタック先頭の値を捨てる                                     |
| S             | スタック先頭の値をレジスタ番号として、次の値をレジスタ#nに格納 (数値はpopしない) |
| Q             | スタック先頭の値をレジスタ番号として、レジスタ#nの値を積む   |
| ?             | スタック先頭の値を数値として描画(popしない)                  |
| +\|-\|*\|/\|^ | スタック先頭の2値(y,x)をpopして、2項演算の結果を積む         |
| ~ (チルダ)    | スタック先頭の値を符号反転する                               |
| {             | スタック先頭をPOPし、繰り返し回数として{}間を繰り返す        |
| }             | {に対するループエンドを示す。ネスト可                        |
| !             | スタック先頭をPOPし、0だったら直近のループを抜ける           |
| "文字列"      | ダブルクォートで括られた範囲を文字列として描画               |
| #             | 行末までコメントとして読み飛ばす                           |
| &             | デバッグプリントでスタックなどをコンソールに出力             |

## 謝辞
作成にあたり、Google Geminiに生成部分のコーディングなど大幅に支援いただきました。
Microsoftさん、Windowsスポットライトのあまりの鬱陶しさにこんなツールを作るモチベーションが湧きました。
KujiraHandさん、使いやすくて柔軟なTkEasyGUIをありがとう。これがなければGUI化は考えませんでした。


### サンプル

samplesの下に各モジュールを使ったサンプル画像を置きました。デフォルトパラメータをいじって保存したものなので、参考まで。

![stripe](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/stripe.png)![HexMaze](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/hexmaze.png) ![Penrose](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/penrose.png)

画像サンプルとともに、tartanのサンプルセットも置いてあります。セットパターンファイル(*.ttn)は、mod_tartan のセットパターンエディタで読み込んでください。

![tartan samples](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/tartan.png)



## モジュール仕様

### 各モジュールファイルで作成必要なAPI関数

- def **intro**(*modlist: Modules, module_name: str*)

  - return **module_name**

  - モジュール基本情報の設定; この関数内で modlist.add_module() を行って基本情報をモジュール側で登録する

  - modlist.add_module( module_name: str, module_descliption: str, parameter_list: list[str] )

    - moduile_name; モジュール名('mod_'をbasenameから削除したもの),  eg. 'stripe'

    - module_descliption; モジュールの概略(1行), eg. 'ストライプタイル'

    - parameter_list; 利用するパラメータkeyのリスト, eg. ['color1', 'color_jitter', 'pwidth', 'pheight']

- def **default_param**(*p: Param*)
  - return **p**
  - p (Param型)のattributeにモジュールで必要なパラメータの参考値を設定して返す
  - モジュール選択時にプレビューで表示する画像はこのパラメータでgenerateしたもの
- def **generate**(*p: Param*)
  - return **image**
  - pで指定したパラメータでPIL Imageを生成して返す
  - imageのモードは 'RGB' または 'RGBA' とする

- def **desc**(*p: Param*)

  - return **image | None**

  - モジュール詳細情報表示/固有パラメータ設定

  - descの実装はoptionalであり、無くてもよい。
       サンプル画像をクリックした際に関数が存在すれば呼び出されるので、詳細情報/モジュール固有の追加パラメータ設定を提供する場合に利用可能

  - 設定変更の結果で生成画像に影響が出るような場合、descからimage型を返すとメイン画面のサンプル画像を更新する

  - 固有パラメータを不揮発にしたい場合は、モジュール側のglobalに ***モジュール名*_preserv{}** として不揮発辞書を作成して保存すること。辞書に登録する内容は任意

    

### wallpaper.pywでのモジュールの呼び出し方

- modlist**.modules** 
  - 導入したモジュール名のリスト
- modlist**.mod_gui[** *module-name* **]**
  - モジュールで利用するGUI項目、利用するもののみ
- modlist.<u>mods[ *module-name* ]</u>**.default_param(p)**
  - おすすめ初期パラメータを取得する(p: Param型)
- image = modlist.<u>mods[ *module-name* ]</u>**.generate(p)**
  - 該当モジュールで画像を生成
- image = modlist.<u>mods[ *module-name* ]</u>**.desc(p)**
  - 固有オプションの設定画面を呼び出す。該当モジュールで画像を生成して返した場合はサンプル表示を更新
  - 戻り値がNoneの場合は何もしない
