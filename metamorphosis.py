import logging
import csv
import json
import os
from io import StringIO



from model.utils import get_response_from_llm
from model.pict import trans_to_pict
from datetime import datetime

# """

#
# """

def get_template(scenario_template):
    system = """You are a language expert and know how to translate the content in 'Then' into antonyms.
    
The input is a scenario template.
The output is the scenario template in which the content in 'Then' has been transformed into an antonym.

Notes:
You can only change the semantics in 'Then'!
You can only output scenario templates without any annotations."""

    prompt = f"The following is a scenario template: {scenario_template}"

    message = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

    response = get_response_from_llm("gpt-4.1-mini", messages=message)

    return response
def read_csv_to_string(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    except FileNotFoundError:
        print(f"Error: File {file_path} was not found.")
        return None

    except Exception as e:
        print(f"An error occurred when reading the file: {e}")
        return None

def replace_var_to_template(file_path, true_template, false_template, dict_valid):
    try:
        # 解析 valid_reply 为字典
        valid_data = dict_valid

        # 读取 CSV 文件
        with open(file_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            true_cases = []  # 存储有效测试用例
            false_cases = []  # 存储无效测试用例
            test_cases = []  # 存储所有测试用例（按原始顺序）

            # 获取所有字段名
            fieldnames = reader.fieldnames

            for row in reader:
                all_valid = True

                # 检查每个字段是否在 valid_reply 中
                for field in fieldnames:
                    value = row.get(field, "").strip()

                    # 如果字段存在于 valid_reply
                    if field in valid_data:
                        if value not in valid_data[field]:
                            all_valid = False
                            break

                # 根据检查结果选择模板
                if all_valid:
                    formatted = true_template.format(**row)
                    true_cases.append(formatted)
                    test_cases.append(formatted)
                else:
                    formatted = false_template.format(**row)
                    false_cases.append(formatted)
                    test_cases.append(formatted)

            # 分别打印有效和无效测试用例
            if true_cases:
                print("\n===== VALID=====\n")
                for test_case in true_cases:
                    print(test_case)
                    print("-" * 40)

            if false_cases:
                print("\n===== INVALID=====\n")
                for test_case in false_cases:
                    print(test_case)
                    print("-" * 40)

            # 打印统计信息
            print("\n===== STATISTICS =====\n")
            print(f"Generated {len(true_cases)} valid test cases")
            print(f"Generated {len(false_cases)} invalid test cases")
            print(f"Total {len(test_cases)} test cases")
            print("=" * 40)

            return test_cases

    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def metamorphosis_var_prompt(str1, str2, str3):
    prompt = f"""test scenario: 
{str1}

variable list in scenario: {str2}

equivalence classes for variable: 
{str3}
"""
    return prompt

def metamorphosis_var(scenario, variable, equivalence_class):

    system = """You are an expert in metamorphic testing and can mutate meaningful variable based on equivalence classes.

Notes: 
petclinic. The inputs are test scenario, variable list in scenario and equivalence classes.
2. Specific variables cannot use the ".repeat()" method or " * number"!
3. Specific variables cannot be described in an abstract manner.
4. If there are any empty variables, use " ".

The output is the mutated variable and is presented in the form of a list (Don't add any comments!).
{
    "Variable Name": [Specific variables (str), ...],
    "Variable Name": [Specific variables (str), ...]
    ...
}"""

    time_system = """You need to determine whether there are any variables related to time among the variables provided by the user (such as date of birth, production date, etc.
Is_Time: If there is a variable related to time, return \"1\"; if not, return \"0\".
Output format as follows:
Is_Time:"""
    time_prompt = f"The following are all the variables: {variable}"

    time_message = [{"role": "system", "content": time_system}, {"role": "user", "content": time_prompt}]

    istime = get_response_from_llm("gpt-4.1-mini", messages=time_message)

    if "1" in istime:
        now = datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")

        prompt = metamorphosis_var_prompt(scenario, variable, equivalence_class)

        message = [{"role": "system", "content": system}, {"role": "user", "content": prompt + "Current time:" + formatted_time}]

        # Call the OpenAI API to obtain the response of the model
        var = get_response_from_llm("gpt-4.1-mini", messages=message)
    elif "0" in istime:
        prompt = metamorphosis_var_prompt(scenario, variable, equivalence_class)


        message = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]

        # Call the OpenAI API to obtain the response of the model
        var = get_response_from_llm("gpt-4.1-mini", messages=message)

    return var

def extract_equivalence_classes(feature, variable_list, knowledge_base_path=None):
    if knowledge_base_path is None:
        knowledge_base_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "knowledgebase",
            "knowledge_petclinic.json"
        )    
        """
    """
    # Read the knowledge base file
    try:
        # 检查文件路径有效性
        if not os.path.exists(knowledge_base_path):
            raise FileNotFoundError(f" {knowledge_base_path}")

        # 检查文件可读性
        if not os.access(knowledge_base_path, os.R_OK):
            raise PermissionError(f" {knowledge_base_path}")

        # 显式管理文件描述符
        with open(knowledge_base_path, "r", encoding="utf-8") as file:
            file_content = file.read()  # 先读取内容
            knowledge_base = json.loads(file_content)  # 再解析JSON

    except (FileNotFoundError, PermissionError, json.JSONDecodeError) as e:
        logging.error(f" {e}")
        # 返回空或默认值
        return [], []

    candidate_knowledge_base = knowledge_base[feature]

    # Initialize the result list
    valid_result = []
    invalid_result = []

    # Traverse each variable
    for variable in variable_list:
        # Find the corresponding variable information
        variable_info = next((item for item in candidate_knowledge_base if item["Variable"] == variable), None)
        if variable_info:
            # Extract valid or invalid equivalence classes
            # equivalence_classes = []
            valid_equivalence_classes = []
            invalid_equivalence_classes = []
            for partition in variable_info["Equivalence partitioning"]:
                if "Valid equivalence class" in partition:
                    valid_equivalence_classes.extend(partition["Valid equivalence class"])
                else:
                    invalid_equivalence_classes.extend(partition["Invalid equivalence class"])
            # Add to the result list
            if valid_equivalence_classes:
                valid_result.append({variable: valid_equivalence_classes})
            if invalid_equivalence_classes:
                invalid_result.append({variable: invalid_equivalence_classes})

    return valid_result, invalid_result


def remove_common_elements(dict_a, dict_b):
    """
    """
    result = {}

    # 遍历dict_b的所有键
    for key in dict_b:
        # 确保键在dict_a中存在
        if key in dict_a:
            # 转换为集合提高查找效率
            set_a = set(dict_a[key])
            # 保留dict_b中不在dict_a的元素
            result[key] = [item for item in dict_b[key] if item not in set_a]
        else:
            # 如果键在dict_a中不存在，保留所有元素
            result[key] = dict_b[key]

    return result

def run_metamorphosis(input_data: dict):
    feature = input_data["Feature"]
    scenario = input_data["Scenario"]
    variable_list = input_data["Variable_List"]
    is_effective = input_data["Is_Effective"]
    # webpage_information = input_data["Webpage_Information"]
    scenario_template = input_data["Scenario_Template"]

    # Retrieve the equivalence classes from the database
    valid_equivalence_classes, invalid_equivalence_classes = extract_equivalence_classes(feature, variable_list)    # return {variable name: equivalence classes list}

    # Input parameters based on metamorphosis such as equivalence classes
    valid_reply = metamorphosis_var(scenario, variable_list, valid_equivalence_classes)
    print(f"\nAssistant:\n {valid_reply}")
    invalid_reply = metamorphosis_var(scenario, variable_list, invalid_equivalence_classes)
    print(f"\nAssistant:\n {invalid_reply}")

    # 解析字符串为字典
    dict_valid = eval(valid_reply)
    dict_invalid = eval(invalid_reply)
    # dict_valid = valid_reply
    # dict_invalid = invalid_reply

    dict_invalid = remove_common_elements(dict_valid, dict_invalid)

    # 合并有效和无效变量
    merged_dict = {}
    for key in set(dict_valid.keys()) | set(dict_invalid.keys()):
        merged_dict[key] = dict_valid.get(key, []) + dict_invalid.get(key, [])

    trans_to_pict(merged_dict)

    # Call the function to read the content of the file
    file_path = "./data/output.csv"
    var = read_csv_to_string(file_path)

    if var:
        print("Test case combination：")
        print(var)

    if is_effective:
        true_template = scenario_template
        false_template = get_template(scenario_template)
    else:
        false_template = scenario_template
        true_template = get_template(scenario_template)

    test_cases = replace_var_to_template(file_path, true_template, false_template, dict_valid)

    return test_cases


if __name__ == '__main__':
    input_data = {
    "Feature": "Register account",
    "Scenario": "Given this is the current URL: \"http://localhost:8080/register\"\nWhen I entered the Username \"abc\", the Password \"123456@Mm\", Phone Number \"1234567890\", Initial Balance \"10\", and then clicked \"Register\"\nThen register successfully",
    "Variable_List": ["username", "password", "phoneNumber", "balance"],
    "Is_Effective": True,
    "Scenario_Template": "Given this is the current URL: \"http://localhost:8080/register\"\nWhen I entered the Username \"{username}\", the Password \"{password}\", Phone Number \"{phoneNumber}\", Initial Balance \"{balance}\", and then clicked \"Register\"\nThen register successfully",
    "Webpage_Information": "This is a registration page for creating a new account on the TRACW platform. The main functions of the page include:\n- Input fields for Username, Password, Phone Number, and Initial Balance.\n- A password strength meter that provides feedback on the strength of the entered password.\n- A form submission button labeled \"Register\".\n- A link to the login page for users who already have an account."
}

    run_metamorphosis(input_data=input_data)