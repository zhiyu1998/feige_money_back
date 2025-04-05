import threading
import time

from DataRecorder import Recorder
from dp_util import backtrack_find_customer, get_all_history_by_date, get_client_name, get_tab, \
    inspire_status_and_switch, is_user_order_exist, print_chat_history, search_order_and_input
from logger_config import logger
from utils import calibration_chat_history, read_csv, read_excel
from config import GET_DATE, EXCEL_PATH, MODE, TEST_CSV_PATH, LAST_INTERRUPT_ORDER

if MODE == "test":
    remaining_data = [str(*item) for item in read_csv(rf"./{TEST_CSV_PATH}").values]
    r = Recorder("test_customer_services_back_money.csv", cache_size=10)
else:
    remaining_data = [str(*item) for item in read_excel(rf"./{EXCEL_PATH}").values]
    r = Recorder("customer_services_back_money.csv", cache_size=10)
# 自动备份
r.set.auto_backup(interval=10, path='backup')

if LAST_INTERRUPT_ORDER != '' and MODE != "test":
    logger.info(f"从上一次中断点继续执行，上次中断订单是 {LAST_INTERRUPT_ORDER}")
    start_index = remaining_data.index(LAST_INTERRUPT_ORDER)
    remaining_data = remaining_data[start_index:] if start_index else remaining_data

# input(remaining_data)

tab = get_tab()
tab.get("https://im.jinritemai.com/pc_seller_v2/main/workspace")

# 切换小休
inspire_status_and_switch(tab)

for excel_order_num in remaining_data:
    # 点击订单号
    search_order_and_input(tab, excel_order_num)
    # 判断是否存在用户，存在就点击进入，不存在就跳过
    if not is_user_order_exist(tab):
        continue

    # 获取客户昵称
    time.sleep(2)
    client_name = get_client_name(tab)
    # 获取历史消息
    chat_all_histroy = get_all_history_by_date(tab, False, GET_DATE)

    logger.info(f"正在校准聊天记录日期")
    # 校准历史消息日期，校准GET_DATE到当天
    chat_all_histroy = calibration_chat_history(chat_all_histroy, GET_DATE)
    logger.info(f"已校准聊天记录日期为 {GET_DATE}")

    # if MODE == "test":
    #     print_chat_history(chat_all_histroy)
    #     break

    # 如果在某天没有聊天记录，就跳过
    if len(chat_all_histroy) == 0:
        logger.info(f"当前客户：{client_name}在 {GET_DATE} 没有聊天记录")
        r.add_data({ "订单号": excel_order_num, "日期": GET_DATE, "客服": "无", "退款": "¥0.00" })
        r.record()
        continue

    # 保存客服的名字，防止重复
    customer_set = set()
    customer_set_lock = threading.Lock()


    def process_chat(chat_one):
        if "收到用户打款，请及时收款" in chat_one.text:
            logger.info(chat_one.text)
            # 初始化
            money = '¥0.00'
            # 找到钱是多少
            for item in chat_one.text.split("\n"):
                if item.startswith("¥"):
                    money = item
                    break
            # 回溯找客服
            customer = backtrack_find_customer(chat_one, chat_all_histroy[0])
            with customer_set_lock:
                customer_set.add(customer)
                logger.info(f'客服：{customer}，成功要到打款 {money}')
                r.add_data({ "订单号": excel_order_num, "日期": GET_DATE, "客服": customer, "退款": money })


    threads = []
    for chat_one in chat_all_histroy:
        t = threading.Thread(target=process_chat, args=(chat_one,))
        threads.append(t)
        t.start()

    # 等待所有线程完成
    for t in threads:
        t.join()

    if len(customer_set) == 0:
        # 不存在客服
        customer = backtrack_find_customer(chat_all_histroy[-1], chat_all_histroy[0])
        r.add_data({ "订单号": excel_order_num, "日期": GET_DATE, "客服": '无' if not customer else customer,
                     "退款": "¥0.00" })
    r.record()