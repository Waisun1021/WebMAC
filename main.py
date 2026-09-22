import sys
import os
import re
import json
import csv

from clarify import Clarify
from test import Test
from metamorphosis import run_metamorphosis

class OutputRedirector:
    def __init__(self, output_file):
        self.original_stdout = sys.stdout
        self.output_file = open(output_file, "w", encoding="utf-8")

    def __enter__(self):
        sys.stdout = self
        return self

    def write(self, text):
        self.original_stdout.write(text)
        self.output_file.write(text)

    def flush(self):
        self.original_stdout.flush()
        self.output_file.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        self.output_file.close()

def extract_json_from_string(s):
    pattern = r'\{.*\}'
    match = re.search(pattern, s, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print("The extracted string cannot be parsed into valid JSON.")
    return None
def extract_json_from_history(history):
    for message in reversed(history):
        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = str(message)

        data = extract_json_from_string(content)
        if data is not None:
            return data

    return None

if __name__ == "__main__":
    log_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "run_log",
    "GPT4"
    )
    timestamp = __import__('datetime').datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    timestamp_dir = os.path.join(log_dir, timestamp)
    os.makedirs(timestamp_dir, exist_ok=True)

    clarify_log = os.path.join(timestamp_dir, "clarify.txt")
    metamorphosis_log = os.path.join(timestamp_dir, "metamorphosis.txt")
    test_log = os.path.join(timestamp_dir, "test.txt")
    csv_file = os.path.join(timestamp_dir, "test_results.csv")

    # 澄清阶段
    example_input: str = """Feature: Add owner
        Given this is the current URL: "http://localhost:8080/owners/new"
        When I add a person with first name "John" and last name "Smith" as a new pet owner
        Then "John Smith" is an owner"""
    start_url: str = "http://localhost:8080/owners/new"

    with OutputRedirector(clarify_log):
        clarify: Clarify = Clarify()
        result = clarify.run(example_input, start_url)

        if result is None:
                raise RuntimeError(
                    "Clarify 階段失敗，請檢查 PetClinic 是否已啟動，以及 localhost:8080 是否可連線。"
                )

        information = extract_json_from_history(result.history)

        if information is None:
                raise RuntimeError(
                    "無法從 Clarify 對話記錄取得 JSON，請查看 clarify.txt。"
                )

    # 蜕变阶段
    with OutputRedirector(metamorphosis_log):
        test_cases = run_metamorphosis(input_data=information)
        test_cases = test_cases[:1]

    # 测试阶段
    with OutputRedirector(test_log):
        test: Test = Test()

    # 使用 utf-8-sig，讓 Windows Excel 開啟時不容易出現中文亂碼
    with open(
        csv_file,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csvfile:

        fieldnames = [
            "test_case",
            "test_result",
            "test_summary",
            "duration_seconds",
            "tokens",
            "interactions",
            "generated_scripts",
            "code_errors"
        ]

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for test_case in test_cases:
            test_result = test.run(
                test_case,
                start_url
            )

            # 防止測試執行失敗而回傳 None
            if test_result is None:
                writer.writerow({
                    "test_case": test_case,
                    "test_result": "ERROR",
                    "test_summary": "Test.run() returned None",
                    "duration_seconds": "",
                    "tokens": "",
                    "interactions": "",
                    "generated_scripts": "",
                    "code_errors": ""
                })

                # 立即將內容寫入硬碟
                csvfile.flush()
                continue

            # 找出最後一則 Analyst 訊息
            analyst_output = ""

            for message in reversed(test_result.history):
                if (
                    isinstance(message, dict)
                    and message.get("name") == "Analyst"
                ):
                    analyst_output = message.get(
                        "content",
                        ""
                    )
                    break

            # 根據專案定義轉成容易理解的結果
            if "IsPass: petclinic" in analyst_output:
                status = "PASS"
            elif "IsPass: 0" in analyst_output:
                status = "FAIL"
            else:
                status = "UNKNOWN"

            # 移除原始 IsPass 標記，只保留測試摘要
            clean_summary = analyst_output.replace(
                "IsPass: petclinic",
                ""
            ).replace(
                "IsPass: 0",
                ""
            ).strip()

            writer.writerow({
                "test_case": test_case,
                "test_result": status,
                "test_summary": clean_summary,
                "duration_seconds": round(
                    test_result.duration,
                    2
                ),
                "tokens": test_result.nr_tokens,
                "interactions": test_result.interactions,
                "generated_scripts": (
                    test_result.nr_generated_scripts
                ),
                "code_errors": (
                    test_result.nr_code_errors
                )
            })

            # 每完成一筆就立即寫入，避免中途停止後全部遺失
            csvfile.flush()

    print(f"The outputs of each stage have been saved respectively to the corresponding files under the {timestamp_dir} directory.")
