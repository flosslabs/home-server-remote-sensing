# 🛰️ おうちサーバーでリモートセンシング (Home Server Remote Sensing)

自宅のサーバー（PC）からAPI経由で人工衛星データにアクセスし、特定の場所の地球観測データ（NDVI/MNDWI）を自動取得・解析・可視化するためのPythonツールキットです。

本リポジトリは、Zennでの連載記事 **「おうちサーバーでリモートセンシング」** の公式ソースコードです。

📚 **Zenn 連載記事一覧**
- [第1回：OSSで始める「個人宇宙開発」の全体構想](https://zenn.dev/flosslabs/articles/home-server-remote-sensing-01)
- [第2回：宇宙から「自分の家」を自動監視するPythonツールを作る](https://zenn.dev/flosslabs/articles/home-server-satellite-02-stac)
- [第3回：Pythonで真っ黒な衛星データを「現像」し、地球の緑と水を可視化する](https://zenn.dev/flosslabs/articles/home-server-satellite-03)

---

## ✨ Features (主な機能)

1. **`satellite_fetcher.py` (データ取得ツール)**
   - Microsoft Planetary ComputerのSTAC APIを利用し、Sentinel-2衛星の最新データを検索します。
   - **住所文字列（例: "東京ドーム"）から自動で緯度経度を解決**します。
   - クラウドネイティブなアプローチ（HTTP Range Requests）により、巨大なGeoTIFFファイル全体ではなく、**指定範囲（BBox）だけを爆速で切り抜いてダウンロード**します。

2. **`satellite_analyzer.py` (データ解析・可視化ツール)**
   - ダウンロードした16bitのRawデータ（真っ黒な画像）をNumPyで高速処理します。
   - **NDVI（正規化植生指数：植物の元気度）** や **MNDWI（修正正規化水指数：水域の抽出）** を計算し、鮮やかなヒートマップ画像（PNG）として出力します。
   - ゼロ除算（ZeroDivisionError）の安全な回避処理を実装済みです。

---

## 🚀 Installation (セットアップ手順)

Python 3.8 以上の環境を推奨します。仮想環境（venv 等）での実行をおすすめします。

```bash
# リポジトリをクローン
git clone https://github.com/あなたのユーザー名/home-server-remote-sensing.git
cd home-server-remote-sensing

# 必要なライブラリのインストール
pip install -r requirements.txt
```

*(※ `requirements.txt` には以下が含まれていることを想定しています: `pystac-client`, `planetary-computer`, `rasterio`, `matplotlib`, `geopy`, `requests`, `tqdm`, `numpy`, `pillow`)*

---

## 📖 Usage (使い方)

### Step 1: 衛星データの検索とダウンロード

`satellite_fetcher.py` を使って、観測したい地点のデータを取得します。

```bash
# 例：実家の住所周辺の「植物の元気度（NDVI）」計算用データを、雲量5%以下で取得する
python3 satellite_fetcher.py -a "実家の住所や施設名" -c 5.0 -i ndvi --save -o my_hometown

# 例：緯度経度を直接指定して、プレビュー画像を保存する
python3 satellite_fetcher.py -p 139.767 35.681 -i preview --save -o tokyo_station
```

> **Note:** `-i ndvi` を指定して保存すると、カレントディレクトリに `my_hometown_B04.tif` (赤波長) と `my_hometown_B08.tif` (近赤外線) の16bit解析用データが保存されます。

**オプション一覧:**
- `-h, --help`: ヘルプと全オプションの表示
- `-a, --address`: 住所や施設名による検索
- `-p, --point`: 経度と緯度による検索
- `-c, --cloud-cover`: 許容する最大雲量（デフォルト: 10%）
- `-i, --index`: 取得する種類 (`preview`, `ndvi`, `ndwi`, `all`)
- `--save`: ファイルをローカルにダウンロードする
- `-o, --output`: 保存するファイル名のベース（接頭辞）

---

### Step 2: データの解析と可視化

Step 1でダウンロードした解析用データ（`.tif`）を使い、`satellite_analyzer.py` でヒートマップ画像を生成します。

```bash
# Step 1で指定したベース名（-o で指定した名前）を引数に渡します
python3 satellite_analyzer.py my_hometown
```

**出力結果:**
処理が成功すると、同じディレクトリに以下の画像ファイルが生成されます。
- `my_hometown_NDVI_result.png` (NDVIのヒートマップ)
- `my_hometown_MNDWI_result.png` (MNDWIのヒートマップ ※B03とB11が存在する場合)

---

## 🖼️ Sample Output (出力サンプル)

| 元のデータ (16bit Raw) | 解析後: NDVI (植物の元気度) |
| :---: | :---: |
| 真っ黒で人間の目には見えない | 緑が濃いほど植物が健康であることを示す |
| *(※ここにプレビュー画像やTIFのスクショなどを置くと良いです)* | *(※ここに生成されたNDVIのPNG画像を置くと良いです)* |

---

## ⚠️ Disclaimer (免責事項)

- 本ツールはSentinel-2のオープンデータを利用しています。APIの仕様変更やアクセス制限等により、予告なく動作しなくなる可能性があります。
- データのダウンロードや処理によって発生した通信費やマシントラブルについて、筆者は一切の責任を負いません。
- 本リポジトリのコードは、Zenn連載の学習用・個人開発用を目的として簡略化されています。

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
