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
        self.output_file = open(output_file, 'w')

    def __enter__(self):
        sys.stdout = self.output_file
        return self

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


if __name__ == "__main__":
    log_dir = "/run_log/GPT4"
    timestamp = __import__('datetime').datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    timestamp_dir = os.path.join(log_dir, timestamp)
    os.makedirs(timestamp_dir, exist_ok=True)

    clarify_log = os.path.join(timestamp_dir, "clarify.txt")
    metamorphosis_log = os.path.join(timestamp_dir, "metamorphosis.txt")
    test_log = os.path.join(timestamp_dir, "test.txt")
    csv_file = os.path.join(timestamp_dir, "test_results.csv")

    # 澄清阶段
    example_input: str = """Given this is the current URL: "http://localhost:8080/owners/new"
        When I add a person with first name "John" and last name "Smith" as a new pet owner
        Then "John Smith" is an owner"""
    start_url: str = "http://localhost:8080/owners/new"

    with OutputRedirector(clarify_log):
        clarify: Clarify = Clarify()
        result = clarify.run(example_input, start_url)
        information = extract_json_from_string(result.history)

    # 蜕变阶段
    with OutputRedirector(metamorphosis_log):
        test_cases = run_metamorphosis(input_data=information)

    # 测试阶段
    with OutputRedirector(test_log):
        test: Test = Test()
        with open(csv_file, 'w', newline='') as csvfile:
            fieldnames = ['test_case', 'test_result']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for test_case in test_cases:
                test_result = test.run(test_case, start_url)
                writer.writerow({'test_case': test_case, 'test_result': test_result})

    print(f"The outputs of each stage have been saved respectively to the corresponding files under the {timestamp_dir} directory.")
