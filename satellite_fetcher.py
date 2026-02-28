#!/usr/bin/env python3
import argparse
import requests
import pystac_client
import planetary_computer
import rasterio
from rasterio.vrt import WarpedVRT  # 部分ダウンロード用
from datetime import datetime
from geopy.geocoders import Nominatim
from tqdm import tqdm

def get_coords_from_address(address):
    """住所文字列から緯度経度を取得する"""
    geolocator = Nominatim(user_agent="home_server_satellite_bot")
    location = geolocator.geocode(address)
    if location:
        return [location.longitude, location.latitude]
    else:
        raise ValueError(f"住所 '{address}' の座標が見つかりませんでした。")

def download_file(url, save_path):
    """通常のファイルをダウンロードする（プレビュー用）"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        
        with open(save_path, 'wb') as f, tqdm(
            desc=save_path,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                bar.update(size)
        print("完了")
    except Exception as e:
        print(f"ダウンロードエラー: {e}")

def download_subset(href, save_path, bbox):
    """
    巨大なGeoTIFFから、指定したBBoxの範囲だけを切り抜いて保存する
    （HTTP Range Requestsを使用）
    """
    # Rasterioが内部でGDALのエラーを出さないように環境変数を一時セットする場合もありますが、
    # 基本的にはSTACで署名されたURLであればそのまま読めます。
    
    print(f"部分ダウンロード開始: {save_path} ...")
    try:
        with rasterio.open(href) as src:
            # Sentinel-2はUTM投影ですが、緯度経度(EPSG:4326)で切り抜くためにWarpedVRTを使います
            with WarpedVRT(src, crs="EPSG:4326") as vrt:
                # 指定したbbox(西, 南, 東, 北)に対応する読み込み枠(Window)を計算
                window = vrt.window(*bbox)
                
                # データを読み込む
                data = vrt.read(window=window)
                
                # 切り抜いた範囲に合わせてメタデータ(transform, width, height)を更新
                transform = vrt.window_transform(window)
                profile = vrt.profile.copy()
                profile.update({
                    'driver': 'GTiff',
                    'height': window.height,
                    'width': window.width,
                    'transform': transform,
                    # countやdtypeはvrt.profileから自動で引き継がれるため指定不要
                })
                
                # 保存
                with rasterio.open(save_path, 'w', **profile) as dst:
                    dst.write(data)
                    
        print(f"完了（切り抜き成功）: {save_path}")

    except Exception as e:
        print(f"部分ダウンロードエラー: {e}")
        print("※URLの有効期限切れや、GDAL/Rasterioのバージョン相性の可能性があります。")

def main():
    parser = argparse.ArgumentParser(description="Sentinel-2衛星画像からNDVI/NDWIなどを取得・計算するツール")
    
    # 必須オプション（住所 or 座標）
    location_group = parser.add_mutually_exclusive_group(required=True)
    location_group.add_argument("-a", "--address", type=str, help="住所や施設名（例: '東京ドーム', '北海道庁'）")
    location_group.add_argument("-p", "--point", type=float, nargs=2, metavar=('LON', 'LAT'), help="経度と緯度（例: 139.76 35.68）")
    
    # 取得モード
    parser.add_argument("-i", "--index", type=str, choices=['preview', 'ndvi', 'ndwi', 'all'], default='preview', 
                        help="取得する画像の種類")
    
    # 検索設定
    parser.add_argument("--coord-only", action="store_true", help="座標のみ表示")
    parser.add_argument("-c", "--cloud-cover", type=float, default=10.0, help="許容する最大雲量（%%）")
    parser.add_argument("-s", "--start-date", type=str, default="2023-01-01", help="検索開始日 YYYY-MM-DD")
    parser.add_argument("-e", "--end-date", type=str, default=None, help="検索終了日 YYYY-MM-DD")
    # ピンポイント取得のため、デフォルト範囲を小さく(約1km四方)設定
    parser.add_argument("-b", "--bbox-size", type=float, default=0.01, help="検索範囲のサイズ（度単位）")
    
    parser.add_argument("--save", action="store_true", help="画像を保存する")
    parser.add_argument("-o", "--output", type=str, help="保存ファイル名のベース")

    args = parser.parse_args()

    # 1. 座標決定
    if args.address:
        print(f"住所 '{args.address}' の座標を検索中...")
        lon, lat = get_coords_from_address(args.address)
    else:
        lon, lat = args.point
    
    print(f"Target: {lon}, {lat}")
    if args.coord_only: return

    # 2. STAC検索
    end_date = args.end_date if args.end_date else datetime.now().strftime('%Y-%m-%d')
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )
    
    # 検索用BBox（少し広めに取る）
    search_bbox = [lon - args.bbox_size, lat - args.bbox_size, lon + args.bbox_size, lat + args.bbox_size]
    
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=search_bbox,
        datetime=f"{args.start_date}/{end_date}",
        query={"eo:cloud_cover": {"lt": args.cloud_cover}},
        sortby=[{"field": "properties.datetime", "direction": "desc"}]
    )
    
    items = list(search.items())
    if not items:
        print("画像が見つかりませんでした。条件を緩和してください。")
        return
        
    best_item = items[0]
    date_str = best_item.datetime.strftime('%Y-%m-%d')
    print(f"データ発見: {date_str} (雲量: {best_item.properties['eo:cloud_cover']}%)")

    base_name = args.output if args.output else f"sentinel2_{date_str}"

    # 3. ダウンロード処理
    if args.index in ['preview', 'all']:
        url = best_item.assets["rendered_preview"].href
        print(f"[Preview] {url}")
        if args.save:
            download_file(url, f"{base_name}_preview.jpg")
        
    if args.index in ['ndvi', 'ndwi', 'all']:
        if not args.save:
            print("※解析用データのURL取得は --save オプションが必要です")
        else:
            # 必要なバンドをリストアップ
            bands = []
            if args.index in ['ndvi', 'all']: bands.extend(['B04', 'B08'])
            if args.index in ['ndwi', 'all']: bands.extend(['B03', 'B11'])
            
            bands = list(set(bands)) # 重複除去
            
            for band in bands:
                href = best_item.assets[band].href
                print(f"[{band}] 部分ダウンロード中...")
                download_subset(href, f"{base_name}_{band}.tif", search_bbox)

if __name__ == "__main__":
    main()
