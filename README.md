# wallpaper.pyw

#   壁紙用のシンプルなイメージを生成する

V2.3.7  2026/09/20 paletteのファイル出力に対応。モジュールによって色数が違うが、多いのを少ない方で読むのは問題なし。

## 概要
複雑なことは(あまり)しません。
Wallpaper用の画像を生成します。

## 必要ライブラリ
Pythonのライブラリとして、標準ライブラリ以外に以下のものを利用します。pipなどでライブラリをインストールして利用してください。 作成時点の各バージョンを()で追記してあります
- pillow  (12.0.0)
- TkEasyGUI  (1.0.40)
- numpy (2.2.6)
- fonttools  (4.63.0) ※ efx_imposeモジュール使用時のみ

## 利用方法(exe)

buildしたバイナリファイルをdistに置いておきます。

利用する際は、 WallpaperGenerator.exe のディレクトリに plugins と samples をディレクトリ丸ごとコピーしてください。

buildに関する手順は、**work/pyinstallerでexe化する.md** を参照のこと。

## 利用方法(pythonスクリプト)

一式を同じディレクトリに配置し、pythonにパスが通っている環境で wallpaper.pyw スクリプトを起動してください。

最低限必要なファイルは、以下の3つ ＋ 任意のモジュール1つ ＋ samplesフォルダです。

| ファイル名     | 説明                                                    |
| -------------- | ------------------------------------------------------- |
| wallpaper.pyw  | ジェネレータ本体                                        |
| wall_common.py | 共通ライブラリ関数                                      |
| filedialog.py  | ファイルダイアログ関連関数                              |
| winwall.py     | Windows環境依存関数                                     |
| mod_*.py       | wallpaper generator用モジュール (最低1モジュールは必要) |
| sample/        | タータン設定、スプライトデータなどを配置するフォルダ    |

上記ライブラリが入っていれば、モジュール(mod_*.py)が読み込まれた後、GUIが表示されます。

- メニュー 
 - File → 表示されている画像のSave、プログラムの終了
 -  modules → moduleの切替え (切替えるとパラメータは初期値に戻ります)
- 画像下のパラメータを適宜変更してください。
- 右下のRedoボタンを押すと、基本色から乱数で振ったタイルパターンを再作成します。
- 右下のSaveボタンを押すと、表示されているパターンをPNGで保存します。
- Quitボタンは、何もせずに終了します。

なお、画像ファイルの幅・高さはFHDサイズ(1920x1080)でスクリプトに埋め込んでいるので、ほかのサイズをデフォルトにしたい場合はスクリプトを直接修正してください。メイン画面右上の入力ボックスの数値で生成画像のサイズを変えられます。変更後はRedoボタンなどで反映してください。

一部のモジュールは、サンプル画像をクリックすると追加設定画面を呼び出します。おおむね、applyで設定反映、cancelで追加設定の変更をキャンセルします。

メニューから hold を行うことで、現在表示している画像を背景画像として保存できます。他のモジュールを呼ぶ際に背景に設定されます。

Windows環境で実行した場合、「SetWP」ボタンがメイン画面に表示されます。このボタンを押下することで、壁紙に現在プレビューに表示されている画像を設定します。tiledチェックボックスをONにすると、タイリング表示するので、その場合は画像サイズを小さくしてください。

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
## パターンモジュール

 　　※ 壁紙パターンをmod_*.py で追加できます

- argyle: アーガイル柄
- bauhaus: バウハウスっぽいタイル
- bias: 斜め帯
- chevron: ギザギザボーダー
- curves: 平面充填曲線各種 (hilbert, peanoはこちらに集約)
- dune: 砂丘？
- easter: イースター風 たまご 時々 ひよこ
- emoji: 絵文字(0:敷石 1:螺旋) 
- flowerworks スピログラフをランダム/グリッド配置で
- footprint: 足跡 (直線か時計回りのみ対応)
- gangi: 階段状ストライブ
- garland: 垂れ幕  もしくは連提灯通り  間隔を両方マイナスにするとポルカドット
- gladation: 1～3色グラデーション 1色(ベタ塗)を含む5パターン
- grass: 芝生シミュレータ
- hexmap: グラデ六角タイル  color1=whiteの場合6色タイルに
- hexmaze: 森の六角迷路
- ivy: ツタ もしくは 植え込み
- kaleidoscope: 万華鏡 くるくる回すだけでも楽しいかもしれない
- memphis: メンフィス風グラフィック
- packingbubble: グラデーション泡充填
- penrose: ペンローズタイル
- photo: イメージファイルを読み込み FIT/回転
- polkadot 水玉模様的な繰り返しパターン
- scallop: ホタテ貝(緋扇貝かもしれない)
- sprites: スプライトまみれ ＋スプライトセットエディタ
- stripe: 縦ストライプ・モダン柄
- tartan: タータン風チェック＋柄エディタ
- tiles: 正方形タイル 多色タイル、回転、3Dパースなど対応
- turtle: タートルコマンド描画 (プレビュークリックでコマンドエディタ起動)
- waves: 青海波文様

  

## efx(効果)モジュール

　　※ 追加効果を efx_*.py で追加できます。
- 共通機能
  - メニューバーから AE_x を選択して、効果設定調整、OK押下でメイン画面に反映されます。

  - 貼り付けるパターンとして、単色ベタ塗り、表示中のイメージ(fg)、holdで保存している背景(bg)、および任意の画像ファイルを利用できます。

- shade: フォアグラウンド画像を型抜きして、影付きでバックグラウンドに貼り付け
  - bgに任意の画像ファイルも指定可能
  - マスクパターンの詳細パラメータは設定画面で確認してください

- impose: フォアグラウンド画像の上に、カレンダーや任意の文字列を貼り付け
  - カレンダーは1～3カ月、6,9,12カ月が利用可能。日本の祝日対応済
  - 任意文字列、固定文字列は配置場所に合わせて左右字詰めを自動調整

- lines: フォアグラウンド画像の上に、平行ストライプ、放射ストライプを描画
  - 任意の位置に1か所、円/楕円の非描画領域を配置可能 (excludeにカンマ区切りで ra,rb と書くことで楕円を指定) 
  - pitch/freqを変更することでストライプ周期を、dutyを変更することでストライプの描画比をそれぞれ調整可能


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

![stripe](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/stripe+impose.png)![HexMaze](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/hexmaze.png) ![Penrose](https://github.com/tpeki/Stripe-Wallpaper-Generator/blob/main/samples/penrose.png)

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
