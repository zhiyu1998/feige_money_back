import re
import pandas as pd
from datetime import datetime, timedelta

from functools import lru_cache
from logger_config import logger


@lru_cache(maxsize=None)
def read_excel(excel_path, usecols="B") -> pd.DataFrame:
    """
    读取Excel文件中指定的列数据
    :param excel_path: Excel文件路径
    :param usecols: 要读取的列（默认读取第A列）
    :return: 包含指定列数据的DataFrame
    """
    df = pd.read_excel(excel_path, usecols=usecols, dtype=str)
    return df


@lru_cache(maxsize=None)
def read_csv(excel_path) -> pd.DataFrame:
    """
    读取CSV文件中的所有数据
    :param excel_path: CSV文件路径
    :return: 包含所有数据的DataFrame
    """
    df = pd.read_csv(excel_path, dtype=str)
    return df


# 定义一个函数来解析中文日期字符串
# 定义一个函数来解析和比较中文日期字符串
def compare_dates(date_str1, date_str2, compare_symbol="<="):
    # 获取当前年份
    current_year = datetime.now().year

    # 定义一个函数来解析日期字符串
    def parse_date(date_str):
        # 检查日期字符串是否包含年份
        if '年' in date_str:
            year, month_day = date_str.split('年')
            month, day = month_day.split('月')
            day = day.replace('日', '')
            return int(year), int(month), int(day)
        elif '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3:
                year, month, day = parts
                return int(year), int(month), int(day)
            elif len(parts) == 2:
                month, day = parts
                return current_year, int(month), int(day)
        else:
            month, day = date_str.split('月')
            day = day.replace('日', '')
            return current_year, int(month), int(day)

    # 解析日期字符串
    year1, month1, day1 = parse_date(date_str1)
    year2, month2, day2 = parse_date(date_str2)

    # 创建datetime对象
    date1 = datetime(year=year1, month=month1, day=day1)
    date2 = datetime(year=year2, month=month2, day=day2)

    # 使用eval动态执行比较操作
    return eval(f"date1 {compare_symbol} date2")


def is_date_prefix(s):
    # 判断字符串是否以日期格式开头
    date_prefixes = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月", "昨天"]
    for prefix in date_prefixes:
        if s.startswith(prefix):
            return True
    return False


def extract_date(s):
    # 定义正则表达式模式
    pattern = r'(\d{1,2}月\d{1,2}日)'

    # 使用re.findall查找所有匹配的日期
    dates = re.findall(pattern, s)

    # 返回找到的日期列表
    return dates


def get_customer_service(input_str):
    # 使用正则表达式提取“xxx”
    match = re.search(r'客服(\w+)接入', input_str)

    if match:
        # 提取到的“xxx”
        extracted_name = match.group(1)
        return extracted_name
    else:
        return "未知客服"


def extract_date_from_line(line):
    """
    从一行文本中提取日期和时间。
    """
    date_pattern = re.compile(r'((\d{1,2}月\d{1,2}日|昨天))(\s+\d{1,2}:\d{2}:\d{2})?')
    match = date_pattern.search(line)
    if match:
        date_str = match.group(1)
        time_str = match.group(3) or ''
        return date_str.strip(), time_str.strip()
    return None, None


def parse_chat_item(item):
    """
    解析单条聊天记录，提取消息、日期和时间。
    """
    parts = item.split('\n')
    message = parts[0]
    date_str = ''
    time_str = ''
    for part in parts[1:]:
        ds, ts = extract_date_from_line(part)
        if ds:
            date_str = ds
            time_str = ts
            break
    return message, date_str, time_str


def date_str_to_datetime(date_str):
    """
    将日期字符串转换为 datetime 对象。
    """
    current_year = datetime.now().year
    if date_str.startswith('昨天'):
        date_obj = datetime.now() - timedelta(days=1)
        return date_obj
    else:
        if '月' in date_str and '日' in date_str:
            month_day = date_str.split('月')
            if len(month_day) == 2:
                month = int(month_day[0])
                day = int(month_day[1].replace('日', ''))
                return datetime(year=current_year, month=month, day=day)
    return None


def calibration_chat_history(chat_all_histroy, target_date_str):
    """
        校准聊天记录，将聊天记录的历史定位到目标日期
        e.g. 比如11月1日，如果有聊天记录就定位到这天返回
    :param chat_all_histroy: 聊天记录列表
    :param target_date_str: 目标日期字符串
    """
    chat_histroy = []
    for chat_msg in chat_all_histroy:
        chat_histroy.append(chat_msg.text)
    # 目标日期
    target_date = date_str_to_datetime(target_date_str)
    # 初始化变量
    start_index = None
    end_index = None
    current_date = None

    for idx, item in enumerate(chat_histroy):
        if not item.strip():
            continue  # 跳过空行

        # 检查是否是日期行
        date_str, _ = extract_date_from_line(item)
        if date_str:
            current_date_obj = date_str_to_datetime(date_str)
            if current_date_obj:
                if current_date_obj.date() == target_date.date():
                    if start_index is None:
                        # 找到目标日期的起始索引
                        start_index = idx
                    current_date = current_date_obj
                else:
                    if start_index is not None and end_index is None:
                        # 找到下一个日期，记录结束索引
                        end_index = idx
                        break  # 已经找到目标区间，可以退出循环
            else:
                # 日期解析失败，跳过
                continue

    # 如果在最后都没有遇到下一个日期，且已经有start_index，则将end_index设为列表末尾
    if start_index is not None and end_index is None:
        end_index = len(chat_histroy)

    # 根据情况处理 chat_histroy
    if start_index is not None and end_index is not None:
        # 截取目标日期的消息区间
        return chat_all_histroy[start_index:end_index]
    else:
        # 不存在目标日期的消息，置为空列表
        return []


def contains_html_tags(text):
    # 定义正则表达式模式
    pattern = re.compile(r'<[^>]+>')

    # 使用正则表达式查找匹配项
    match = pattern.search(text)

    # 如果找到匹配项，返回 True，否则返回 False
    return bool(match)