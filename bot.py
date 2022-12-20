import os
import time
import logging
import sys
import requests
import json
import chromedriver_autoinstaller

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options

chromedriver_autoinstaller.install()
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=chrome_options)

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_user_balance():
    user_balance = driver.find_element("id", "header_wallet_balance")
    user_balance_edit = (''.join(c for c in user_balance.text if c.isdigit()))
    return user_balance_edit

def count_itens_by_collection(collection):
    count = 0
    
    log_file_path = "purchased_itens.log"
    if not os.path.isfile(log_file_path):
        return 0
    
    log_file = open(log_file_path, "r")
    log_file_lines = log_file.readlines()
    for line in log_file_lines:
        split_result = line.split("<>")
        date_str = str(split_result[0].strip())
        collection_name = str(split_result[1].strip().replace("Collection: ", ""))
        item_name = str(split_result[1].strip().replace("Item: ", ""))
        item_float = float(split_result[2].strip().replace("Float: ", ""))
        item_price = float(split_result[3].strip().replace("Price: ", ""))
        if (collection_name == collection["name"]):
            count += 1
            
    return count

def buy_log(current_collection, item_name, item_float, item_price):
    log_file_path = "purchased_itens.log"
    if not os.path.isfile(log_file_path):
        open(log_file_path, "w")
    
    log_message = "<> Collection: {} <> Item: {} <> Float: {} <> Price: {} <>".format(current_collection["name"], item_name, item_float, item_price)
    
    logger = logging.getLogger('BUYLOGGER')
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file_path, mode='a')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%d/%m/%Y %I:%M:%S%p')
    file_handler.setFormatter(formatter)
    logger.handlers.clear()
    if not logger.handlers:
        logger.addHandler(file_handler)
    logger.info(log_message)

def buy_skin(buy_button):
    # Buy now button
    driver.execute_script("arguments[0].click();", buy_button)
    # Execute order
    try:
        check_box = driver.find_element("id", "market_buynow_dialog_accept_ssa")
        driver.execute_script("arguments[0].click();", check_box)

        buy_button = driver.find_element("id", "market_buynow_dialog_purchase")
        driver.execute_script("arguments[0].click();", buy_button)

        close_button = driver.find_element("id", "market_buynow_dialog_close")
        driver.execute_script("arguments[0].click();", close_button)

        time.sleep(5)
    except NoSuchElementException:
        print("Erro ao comprar essa skin, pulando para a proxima.")

def find_next_page():
    try:
        print("Carregando proxima pagina...")
        next_page = driver.find_element('xpath', '//span[@id="searchResults_btn_next" and @class="pagebtn"]')
        driver.execute_script("arguments[0].click();", next_page)
        time.sleep(speed)
        return True
    except NoSuchElementException:
        print("Pagina nao encontrada, indo para a proxima skin...")
        return False


def load_purchase_buttons():
    try:
        inspect_button = driver.find_elements("class name", "market_actionmenu_button")
        buy_buttons = driver.find_elements("class name", "item_market_action_button")
        prices_box = driver.find_elements('xpath', '//span[@class="market_listing_price market_listing_price_with_fee"]')
        return inspect_button, buy_buttons, prices_box
    except NoSuchElementException:
        print("Erro ao carregar pagina de compra, tentando novamente...")
        return

def check_whole_page(current_collection):
    last_item_log_message = ''
    max_price_reached = False
    while True:
        try:
            buttons, buy_now, prices = load_purchase_buttons()
        except NoSuchElementException:
            continue

        try:
            price_text_num = []
            for price in prices:
                price_text_num.append(int(''.join(c for c in price.text if c.isdigit())) / 100)
        except (StaleElementReferenceException, ValueError):
            break

        for idx, btn in enumerate(buttons):
            # Check if max price is reached
            if not check_max_price(idx, price_text_num, current_collection['maxPrice']):
                max_price_reached = True
                break

            # Save JSON information
            try:
                item_name, item_float, item_pattern, whole_json = save_json_response(btn)
            except (NoSuchElementException, StaleElementReferenceException):
                print("Erro ao obter dados da api de float, verificando proxima skin...")
                continue

            # Check user balance
            try:
                user_bal_num = float(check_user_balance()) / 100
            except ValueError:
                print("Erro ao obter saldo da steam, voce precisa fazer login.")
                driver.quit()
                sys.exit()

            # Check if user have enough money for skin
            if user_bal_num < price_text_num[idx]:
                print("Saldo insuficiente, verificando proxima skin...")
                continue

            # Check if float and pattern match with user input
            if check_item_parameters(item_float, whole_json, current_collection['maxFloat']) is False:
                continue

            # Buy skin & save log
            buy_skin(buy_now[idx])
            buy_log(current_collection, item_name, item_float, price_text_num[idx])
            print("Itens comprados nessa colecao: " + count_itens_by_collection(current_collection))

        # Search for next page
        if not find_next_page() or max_price_reached:
            break

def save_json_response(button):
    driver.execute_script("arguments[0].click();", button)
    popup = driver.find_element("css selector", "#market_action_popup_itemactions > a")
    href = popup.get_attribute('href')

    response = requests.get('https://api.csgofloat.com/?url=' + href)
    response.raise_for_status()
    json_response = response.json()
    json_response_name = str(json_response["iteminfo"]["full_item_name"])
    json_response_float = float(json_response["iteminfo"]["floatvalue"])
    json_response_pattern = int(json_response["iteminfo"]["paintseed"])
    return json_response_name, json_response_float, json_response_pattern, json_response

def check_item_parameters(item_float, whole, maxFloat):
    if item_float > float(maxFloat):
        return False
    return True

def check_max_price(order, price, maxPrice):
    if float(maxPrice) >= float(price[order]):
        return True
    return False

# Login page load
driver.get("https://steamcommunity.com/login/home/?goto=market%2Flistings%2F730")
print("Efetue login na steam.")
input("Aperte enter para continuar:")
speed = 15
cls()

# Reading URLs
collections = {}
try:
    with open('collections.json', 'r', encoding="utf-8") as read_file:
        collections = json.load(read_file)
except FileNotFoundError:
    print("Crie o arquivo collections.json e insira os objetos com as chaves: name(string), urls(<string>[]), maxFloat(float), maxValue(float)")
    driver.quit()
    sys.exit()

# Search loop
count = 0
while True:
    for collection in collections['collections']:
        if collection['enabled']:
            count = 0
            cls()
            for url in collection['urls']:
                count += 1
                print("Carregando {}a URL da colecao {}...".format(count, collection['name']))
                driver.get(url)
                check_whole_page(collection)
