import argparse
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def calculate_index(band1_path, band2_path, index_name):
    """
    2つのバンド画像を使って正規化指数 (B1 - B2) / (B1 + B2) を計算する関数
    """
    print(f"[{index_name}] 計算開始: {band1_path} & {band2_path}")
    
    # 1. データの読み込み
    with rasterio.open(band1_path) as src1:
        # 計算時のオーバーフローを防ぐため float32 に変換
        b1 = src1.read(1).astype('float32')
        meta = src1.meta # メタデータを保存用に取得
        
    with rasterio.open(band2_path) as src2:
        b2 = src2.read(1).astype('float32')

    # 2. 安全な割り算（ゼロ除算の回避）
    # 分母を計算 (A + B)
    denominator = (b1 + b2)
    
    # NumPyの np.errstate を使って、一時的にゼロ除算の警告を無視する
    with np.errstate(divide='ignore', invalid='ignore'):
        # 分母が0の場所は 0.0 に置き換え、それ以外は計算する
        index_map = np.where(denominator == 0., 0., (b1 - b2) / denominator)
    
    print(f"[{index_name}] 計算完了 (Min: {np.nanmin(index_map):.2f}, Max: {np.nanmax(index_map):.2f})")
    return index_map, meta

def save_heatmap(data, output_path, cmap, title):
    """計算結果をカラーマップ（PNG画像）として保存する"""
    plt.figure(figsize=(10, 10))
    # ヒートマップ表示 (値の範囲を-1〜1に固定することで、日時の違う画像とも比較可能にします)
    plt.imshow(data, cmap=cmap, vmin=-1.0, vmax=1.0)
    plt.colorbar(label='Index Value')
    plt.title(title)
    plt.axis('off') # 軸を消す
    
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    print(f"画像保存完了: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="衛星データのバンド画像からNDVI/MNDWIを計算・可視化するツール")
    parser.add_argument("base_name", type=str, help="入力ファイルのベース名（例: my_hometown_ndvi）")
    args = parser.parse_args()

    base = args.base_name

    # --- 1. NDVI (植生指数) の計算 ---
    # 必要なファイル: _B08.tif (NIR), _B04.tif (Red)
    b08_path = f"{base}_B08.tif"
    b04_path = f"{base}_B04.tif"

    if Path(b08_path).exists() and Path(b04_path).exists():
        ndvi, _ = calculate_index(b08_path, b04_path, "NDVI")
        # 植物は「緑」で表現したいので 'RdYlGn' (赤→黄→緑) を使用
        save_heatmap(ndvi, f"{base}_NDVI_result.png", 'RdYlGn', f"NDVI Analysis: {base}")
    else:
        print(f"スキップ: NDVI計算用のファイル({b08_path}, {b04_path})が見つかりません。")

    # --- 2. MNDWI (水指数) の計算 ---
    # 必要なファイル: _B03.tif (Green), _B11.tif (SWIR)
    b03_path = f"{base}_B03.tif"
    b11_path = f"{base}_B11.tif"
    
    if Path(b03_path).exists() and Path(b11_path).exists():
        # MNDWI = (Green - SWIR) / (Green + SWIR)
        mndwi, _ = calculate_index(b03_path, b11_path, "MNDWI")
        # 水は「青」で表現したいので 'PuBu' (白→青) を使用
        save_heatmap(mndwi, f"{base}_MNDWI_result.png", 'PuBu', f"MNDWI Analysis: {base}")
    else:
        print(f"スキップ: MNDWI計算用のファイル({b03_path}, {b11_path})が見つかりません。")

if __name__ == "__main__":
    main()
