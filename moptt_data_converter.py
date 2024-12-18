"""
MOPTT 資料轉換工具
用於將 JSON 格式的爬蟲資料轉換為 CSV 格式
"""

import json
import pandas as pd
from datetime import datetime
import os
import glob


def convert_json_to_csv(json_file_path, output_csv_path=None):
    """
    將 JSON 檔案轉換為 CSV 格式
    
    Args:
        json_file_path (str): JSON 檔案的路徑
        output_csv_path (str, optional): 輸出 CSV 檔案的路徑。如果未指定，將使用與 JSON 相同的檔名
    
    Returns:
        str: 輸出的 CSV 檔案路徑
    """
    # 檢查檔案是否存在
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"找不到檔案：{json_file_path}")

    # 讀取 JSON 檔案
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 將資料轉換為 DataFrame
    df = pd.DataFrame(data)
    
    # 如果沒有指定輸出路徑，則使用預設格式
    if output_csv_path is None:
        output_csv_path = json_file_path.replace('.json', '.csv')
    
    # 將 DataFrame 儲存為 CSV
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print(f'CSV 檔案已儲存至: {output_csv_path}')
    return output_csv_path


def convert_all_json_files(directory='.', pattern='moptt_*.json'):
    """
    轉換指定目錄下所有符合模式的 JSON 檔案
    
    Args:
        directory (str): 要搜尋的目錄路徑，預設為當前目錄
        pattern (str): 檔案名稱模式，預設為 'moptt_*.json'
    
    Returns:
        list: 轉換後的 CSV 檔案路徑列表
    """
    # 取得所有符合模式的 JSON 檔案
    json_files = glob.glob(os.path.join(directory, pattern))
    converted_files = []
    
    if not json_files:
        print("找不到任何符合條件的 JSON 檔案")
        return converted_files
    
    for json_file in json_files:
        try:
            csv_file = convert_json_to_csv(json_file)
            converted_files.append(csv_file)
            print(f"成功轉換：{json_file}")
        except Exception as e:
            print(f"轉換 {json_file} 時發生錯誤: {str(e)}")
    
    return converted_files


if __name__ == "__main__":
    # 轉換當前目錄下所有 MOPTT JSON 檔案
    converted_files = convert_all_json_files()
    
    if converted_files:
        print("\n成功轉換的檔案：")
        for file in converted_files:
            print(f"- {file}")
    else:
        print("\n沒有成功轉換的檔案")
