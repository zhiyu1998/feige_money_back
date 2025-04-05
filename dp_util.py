import re
import time
from datetime import datetime
from DrissionPage import Chromium, ChromiumOptions
from DrissionPage.items import NoneElement, ChromiumElement
from loguru import logger

from config import SWITCH_STATUS
from utils import compare_dates, contains_html_tags, is_date_prefix


def get_tab():
    """
        获取 Nil 的浏览器标签对象
    """
    path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    co = ChromiumOptions().set_paths(
        browser_path=path,
        local_port=9111,
        user_data_path=r'C:\Users\Administrator\AppData\Local\Microsoft\Edge\User Data'
    )

    tab = Chromium(addr_or_opts=co).latest_tab
    return tab


def inspire_status_and_switch(tab):
    """
        抖店函数：查看当前用户的状态，如果是离线就切换成小休/在线状态
        :param tab: 浏览器标签对象
    """
    # 判断是否是离线
    offline_sign = tab.ele('xpath=//*[@id="rootContainer"]/div/div[1]/div[1]/div[1]/div[1]/div/div/div/div')
    tab.wait.ele_displayed(offline_sign)
    time.sleep(2)
    logger.info(f'当前状态为：<{offline_sign.text}>')
    if "离线" == offline_sign.text:
        offline_sign.click()
        # 切换到在线
        switch_online = None
        if SWITCH_STATUS == 0:
            switch_online = tab.ele('xpath=//*[@id="rootContainer"]/div/div[1]/div[1]/div[1]/div[1]/div/div[2]/div[3]')
        elif SWITCH_STATUS == 1:
            switch_online = tab.ele('xpath=//*[@id="rootContainer"]/div/div[1]/div[1]/div[1]/div[1]/div/div[2]/div[4]')
        tab.wait.ele_displayed(switch_online)
        switch_online.click()
        logger.info(f"已切换至 <{SWITCH_STATUS == 0 and '在线' or '小休'} 状态>，开始上班")


def search_order_and_input(tab, excel_order_num):
    """
        搜索订单然后输入
        :param tab: 浏览器标签对象
        :param excel_order_num: 需要输入的订单号
    """
    order_num = tab.ele('xpath=//*[@id="rootContainer"]/div/div[1]/div[1]/div[2]/div/input')
    tab.wait.ele_displayed(order_num)
    order_num.click()
    order_num.input(excel_order_num)


def is_user_order_exist(tab):
    """
        检查订单是否存在
        :param tab: 浏览器标签对象
    """
    # 获取用户名称并点击
    user_info = tab.ele('xpath=//*[@id="chantListScrollArea"]/div[2]', timeout=5)
    if not user_info:
        tab.ele('xpath=//*[@id="rootContainer"]/div/div[1]/div[1]/div[2]/div/img[2]').click()
        return False
    user_info = tab.ele('xpath=//*[@id="chantListScrollArea"]/div[2]')
    time.sleep(0.5)
    tab.wait.ele_displayed(user_info)
    logger.info(f'正在处理订单号: {user_info.text}')
    user_info.click()
    return True


def get_client_name(tab):
    """
        获取客户姓名
        :param tab: 浏览器标签对象
    """
    return tab.ele('xpath=//*[@id="workspace-chat"]/div[3]/div[1]/div[1]/span/div').text


def extract_date(s):
    # 定义正则表达式模式
    pattern = r'(\d{1,2}月\d{1,2}日)'

    # 使用re.findall查找所有匹配的日期
    dates = re.findall(pattern, s)

    # 返回找到的日期列表
    return dates


def get_all_history_by_date(tab, is_filter_customer, GET_DATE):
    """
        获取日期前的所有的历史记录
        :param tab: 浏览器标签对象
        :is_filter_customer 是否过滤客户
        :param GET_DATE: 越过这个时期就停止
    """
    try:
        # 当前聊天框的全部历史记录
        chat_histroy = tab.ele('xpath://*[@id="workspace-chat"]/div[3]/div[3]/div/div[2]')
        while chat_histroy.child().text != '已经到顶啦':
            tab.scroll.to_see(chat_histroy.child())
            logger.info("开始滑动")
            chat_histroy = tab.ele('xpath=//*[@id="workspace-chat"]/div[3]/div[3]/div/div[2]')
            # 如果达到了某个日期超过了GET_DATE，那么就停止
            start_date = chat_histroy.child().text[:6]
            # 如果是昨天就重置下日期
            if start_date.startswith("昨天"):
                start_date = str(datetime.now().month) + "月" + str(datetime.now().day) + "日"
            logger.info(start_date)
            if is_date_prefix(start_date) and compare_dates(extract_date(start_date)[0], GET_DATE, "<"):
                logger.info(f'当前日期：{start_date}，超过{GET_DATE}')
                break
            time.sleep(3)
        logger.info("获取聊天记录完成")
        chat_history = chat_histroy.children()
        if is_filter_customer:
            return [chat_one for chat_one in chat_history if chat_one.ele('tag:div@style:row-reverse', timeout=2)]
        return chat_history
    except Exception as e:
        logger.error(f"出现错误: {e}")
        logger.info("正在刷新页面...")
        tab.refresh()  # 刷新页面
        time.sleep(5)  # 给页面刷新一定时间
        # 可以选择再次递归调用该方法，或者重新处理
        return get_all_history_by_date(tab, is_filter_customer, GET_DATE)


def print_chat_history(chat_all_histroy):
    """
        调试时打印聊天记录
    """
    for chat in chat_all_histroy:
        logger.info(chat.text)


def backtrack_find_customer(chat_one, top_chat=None):
    """
        从当前聊天记录中回溯找出客服
        :param chat_one: 当前聊天记录
        :top_chat: 限定日期内最早的聊天，防止回溯过头
    """
    cur_customer = ""
    # 找到图片，开始回溯找客服
    tmp_chat_one = chat_one
    # logger.info(chat_one)
    while cur_customer == '':
        # 向上寻找
        tmp_chat_one = tmp_chat_one.prev(timeout=1)
        # 如果到顶就结束
        if not tmp_chat_one or tmp_chat_one.text == '已经到顶啦':
            break

        if tmp_chat_one.child(timeout=1) and tmp_chat_one.child().child(
                timeout=2) and tmp_chat_one.child().child().child(timeout=2):
            tmp_chat_text = tmp_chat_one.child().child().child()
            if tmp_chat_text and tmp_chat_text.next(timeout=1) and tmp_chat_text.next().child(timeout=1):
                tmp_chat_text = tmp_chat_text.next().child().child().inner_html
            else:
                continue
        else:
            continue
        # logger.info(f'================{tmp_chat_text}')
        if not isinstance(tmp_chat_text, NoneElement) and tmp_chat_text != '' and not isinstance(tmp_chat_text,
                                                                                                 ChromiumElement) and not contains_html_tags(
                tmp_chat_text):
            cur_customer = tmp_chat_text
            logger.info(f"捕捉到客服名字：{tmp_chat_text}")
            return cur_customer

        # 【这个逻辑只能放到最后】最后一条也检测完成，如果当前聊天等于最顶端的聊天，那么就结束
        if top_chat is not None and tmp_chat_one == top_chat:
            break
    return cur_customer
