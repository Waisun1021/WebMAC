import codecs
import csv
import subprocess

def trans_to_pict(variable):
    # data_dict = eval(variable)
    data_dict = variable

    # 格式化内容
    formatted_content = ""
    for key, values in data_dict.items():
        quoted_values = []
        for v in values:
            # 对含空格/逗号的值添加双引号
            if any(char in v for char in ' ,\t'):
                quoted_values.append(f'"{v}"')  # 添加双引号包裹
            else:
                quoted_values.append(v)
        formatted_content += f"{key}: {', '.join(quoted_values)}\n"

    # 保存到文件
    # file_name = "output.pict"
    # with open(file_name, "w", encoding="ansi") as file:
    #     file.write(formatted_content)
    file_name = "./data/output.pict"
    with codecs.open(file_name, "w", encoding="utf-8") as file:
        file.write(formatted_content)

    # 使用 subprocess 调用 pict 命令
    try:
        # 执行 pict 命令并重定向输出到 output.csv
        result = subprocess.run(
            ["./model/pict", file_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )

        # 将输出保存到 output.csv 文件
        csv_file_path = "./data/output.csv"
        # 使用 csv.reader 解析 TSV（制表符分隔）
        tsv_data = csv.reader(result.stdout.strip().splitlines(), delimiter='\t')
        with open(csv_file_path, "w", encoding="utf-8", newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerows(tsv_data)
        # csv_file_path = "../data/output.csv"
        # with open(csv_file_path, "w", encoding="utf-8", newline='') as csv_file:
        #     csv_writer = csv.writer(csv_file, delimiter=',')
        #     # 将 result.stdout 的内容解析为 CSV 格式
        #     for line in result.stdout.strip().split('\n'):
        #         row = line.split('\t')  # 假设每列之间用制表符分隔
        #         csv_writer.writerow(row)

        print("已成功生成 output.csv 文件")
    except FileNotFoundError:
        print("错误：pict 工具未找到，请确保已安装并添加到系统路径中。")
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == '__main__':
    data = """{
    "name": ["", "Jamie"*11, "     ", "Ja@m!e#", "Jamie😊"],
    "birthDate": ["20230512", "2023-13-12", "2023-00-12", "2023-02-31", "2500-05-12", "2026-05-12", "    "]
}"""
    trans_to_pict(data)