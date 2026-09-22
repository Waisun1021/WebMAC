import codecs
import csv
import os
import subprocess


def trans_to_pict(variable):
    """
    將變數及測試值寫入 PICT 模型檔，
    呼叫 pict.exe 產生組合，最後轉成 CSV。
    """

    data_dict = variable

    # WebMAC 專案根目錄
    project_root = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    # 建立 PICT 模型內容
    formatted_content = ""

    for key, values in data_dict.items():
        quoted_values = []

        for value in values:
            value = str(value)

            # 含有空格、逗號或 Tab 時，以雙引號包住
            if any(char in value for char in " ,\t"):
                quoted_values.append(f'"{value}"')
            else:
                quoted_values.append(value)

        formatted_content += (
            f"{key}: {', '.join(quoted_values)}\n"
        )

    # 寫入 data/output.pict
    pict_input_path = os.path.join(
        project_root,
        "data",
        "output.pict"
    )

    with codecs.open(
        pict_input_path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(formatted_content)

    # 使用相對路徑呼叫 PICT，避免中文絕對路徑問題
    pict_exe_relative = os.path.join(
        "model",
        "pict.exe"
    )

    pict_input_relative = os.path.join(
        "data",
        "output.pict"
    )

    result = subprocess.run(
        [
            pict_exe_relative,
            pict_input_relative
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    # 檢查 PICT 是否執行失敗
    if result.returncode != 0:
        raise RuntimeError(
            f"PICT 執行失敗，結束代碼："
            f"{result.returncode}\n"
            f"錯誤訊息：{result.stderr}\n"
            f"一般輸出：{result.stdout}"
        )

    # 防止沒有資料卻顯示成功
    if not result.stdout.strip():
        raise RuntimeError(
            "PICT 沒有產生任何測試組合。\n"
            f"輸入檔案：{pict_input_relative}\n"
            f"錯誤訊息：{result.stderr}"
        )

    # 將 PICT 的 Tab 分隔結果轉成 CSV
    csv_file_path = os.path.join(
        project_root,
        "data",
        "output.csv"
    )

    tsv_data = csv.reader(
        result.stdout.strip().splitlines(),
        delimiter="\t"
    )

    rows = list(tsv_data)

    with open(
        csv_file_path,
        "w",
        encoding="utf-8",
        newline=""
    ) as csv_file:
        writer = csv.writer(csv_file)
        writer.writerows(rows)

    # 第一列是欄位名稱，所以減 1
    combination_count = max(len(rows) - 1, 0)

    print(
        f"已成功生成 output.csv，"
        f"共 {combination_count} 筆組合"
    )

    return csv_file_path


if __name__ == "__main__":
    # 只在直接執行 pict.py 時使用的簡單測試
    test_data = {
        "firstName": ["John", "Jane"],
        "lastName": ["Smith", "Johnson"],
        "city": ["New York", "Taipei"]
    }

    trans_to_pict(test_data)