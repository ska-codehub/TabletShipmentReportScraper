# main file for the scraping
# @author: Sk Khurshid Alam

import os
import sys
import shutil
import signal
import psutil
from contextlib import suppress
import configparser
import argparse
from pathlib import Path
from getpass import getpass
import time
import random
import pickle
import pandas as pd
import base64
from selenium import webdriver
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pyautogui
import traceback


TRUTHY = [
    'TRUE', 'True', 'true', 'T', 't', True,
    '1', 1,
    'ON', 'On', 'on',
    'YES', 'Yes', 'yes', 'Y', 'y'
]


FALSY = [
    'FALSE', 'False', 'false', 'F', 'f', False,
    '0', 0,
    'OFF', 'Off', 'off',
    'NO', 'No', 'no', 'N', 'n'
]

BASE_DIR = Path("./")
CONFIGURATION_FILE = BASE_DIR / 'settings.config'
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = BASE_DIR / "archive"
CHROME_DIR = BASE_DIR / "chrome"
VPN_EXTN_DIR = CHROME_DIR / "veepn"
VPN_TURN_ON_IMGS_DIR = VPN_EXTN_DIR / "images" / "upto-turn-on"
USER_DATA_DIR = CHROME_DIR / "user-data"
CREDS_PATH = BASE_DIR / ".creds.pkl"

DATA_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)
CHROME_DIR.mkdir(exist_ok=True)
USER_DATA_DIR.mkdir(exist_ok=True)

config = configparser.RawConfigParser()
config.read(CONFIGURATION_FILE)
SETTINGS = dict(config.items('settings'))

PROJECT_NAME = SETTINGS.get('project_name').strip()
PROJECT_DESCRIPTION = SETTINGS.get('project_description').strip()
VERSION = SETTINGS.get('version').strip()
SITE_DOMAIN = SETTINGS.get('site_domain').strip()
LOGIN_URL = SETTINGS.get('login_url').strip()
LOGIN_TITLE = SETTINGS.get('login_title').strip()
LOGIN_REDIRECT_TITLE = SETTINGS.get('login_redirect_title').strip()
LOGIN_SESSION_EXPIRED_TITLE = SETTINGS.get('login_session_expired_title').strip()
SITE_URL = SETTINGS.get('site_url').strip()
SITE_TITLE = SETTINGS.get('site_title').strip()

HEALTH_CHECK_URL = SETTINGS.get('health_check_url').strip()
HEALTH_CHECK_TITLE = SETTINGS.get('health_check_title').strip()

USERNAME = None
PASSWORD = None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.5735.90",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36", 
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
]


def confirmation_input(ask_str, ask_type):
    if ask_type not in ['Y/n', 'y/N', 'N/y', 'n/Y']:
        ask_type = 'Y/n'
    ask_str = f"{ask_str} [{ask_type}]: "
    while True:
        ask_value = input(ask_str).lower()
        if not ask_value in [''] + TRUTHY + FALSY:
            print("Please provide a valid confirmation!")
            continue
        if ask_type == 'Y/n':
            return ask_value in [''] + TRUTHY
        elif ask_type == 'y/N':
            return ask_value in TRUTHY
        elif ask_type == 'N/y':
            return ask_value in TRUTHY
        elif ask_type == 'n/Y':
            return ask_value in [''] + TRUTHY


def creds_export():
    if USERNAME is not None and PASSWORD is not None:
        username_byte = USERNAME.encode("UTF-8")
        password_byte = PASSWORD.encode("UTF-8")
        for _ in range(0, 10):
            username_byte = base64.b85encode(username_byte)
            password_byte = base64.b85encode(password_byte)
        with open(CREDS_PATH, "wb") as f:
            pickle.dump({"username" : username_byte, "password" : password_byte}, f)
    
def creds_import():
    if CREDS_PATH.exists():
        with open(CREDS_PATH, "rb") as f:
            obj = pickle.load(f)
            username_byte = obj.get("username")
            password_byte = obj.get("password")
        for _ in range(0, 10):
            username_byte = base64.b85decode(username_byte)
            password_byte = base64.b85decode(password_byte)
        global USERNAME, PASSWORD
        USERNAME = username_byte.decode("UTF-8")
        PASSWORD = password_byte.decode("UTF-8")

class TabletScraper:
    def __init__(self, invisible=False, vpn_off=False) -> None:
        self.invisible = invisible
        self.vpn_off = vpn_off
        self.user_agent = USER_AGENTS[random.randrange(0, len(USER_AGENTS)-1)]
        self.page_load_timeout = 60
        self.not_ok = 0
        self.retry = 0
        self.max_retries = 3

    def is_head_ready(self):
        try:
            WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, "head")))
            return self.browser.find_element(By.TAG_NAME, "head") is not None 
        except Exception as e:
            print("TabletScraper.is_head_ready Error: ", e, traceback.format_exc())
            return False
    
    def is_dom_ready(self):
        try:
            time.sleep(0.5)
            WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))                
            try:
                self.browser.execute_script(f'window.scrollTo(0, {random.randrange(100, 1000)})')
            except:
                pass
            return self.browser.find_element(By.TAG_NAME, "body") is not None
        except Exception as e:
            print("TabletScraper.is_dom_ready Error: ", e, traceback.format_exc())
            return False        

    def is_title_valid(self, title=""):
        try:
            return self.browser.title==title or self.browser.title.strip()==title.strip()
        except Exception as e:
            print("WhatsAppScraper.is_title_valid Error: ", e, traceback.format_exc())
            return False
        
    def is_page_ready(self, title):
        ready = False
        for _ in range(0, 3):
            try:
                time.sleep(1)
                ready = self.is_head_ready() and self.is_dom_ready() and self.is_title_valid(title)
                if ready:
                    break
            except:
                ready = False
        return ready


    def get_page(self, url, title=None):
        try:
            self.browser.get(url)
            return self.is_page_ready(title)
        except TimeoutException as e:
            print("TabletScraper.get_page Error1: ", e, traceback.format_exc())
            if self.retry<=self.max_retries:
                self.retry += 1
                # self.config_browser()
                return self.get_page(url, title)
            return False
        except Exception as e:
            print("TabletScraper.get_page Error2: ", e, traceback.format_exc())
            return False

    def test_browser_ok(self):
        print("Testing browser")
        if self.get_page(HEALTH_CHECK_URL, HEALTH_CHECK_TITLE):
            self.not_ok = 0
            print("OK")
            return True
        else:
            self.not_ok += 1
            print("NOT OK")
            return False

    
    def kill_browser_process(self):     
        try:
            if hasattr(self, "browser") and self.browser is not None:
                print("Killing browser instances and process")
                try:
                    pid = int(self.browser.service.process.id)
                except:
                    pid = None
                try:
                    self.browser.service.process.send_signal(signal.SIGTERM)
                except:
                    pass
                try:
                    self.browser.close()
                except:
                    pass
                try:
                    self.browser.quit()
                except:
                    pass
                try:
                    if pid is not None:
                        os.kill(pid, signal.SIGTERM)
                except:
                    pass
            try:
                for process in psutil.process_iter():
                    try:
                        if process.name() == "chrome.exe" \
                            and "--test-type=webdriver" in process.cmdline():
                            with suppress(psutil.NoSuchProcess):
                                try:
                                    os.kill(process.pid, signal.SIGTERM)
                                except:
                                    pass
                    except:
                        pass
            except:
                pass
        except:
            pass
        
        if hasattr(self, "browser"):
            if self.browser is None or not hasattr(self.browser, "service") or self.browser.service:
                print("Browser closed and webdriver process killed!")
                self.browser = None
            else:
                print("Browser and Webdriver process NOT killed !!!!")


    def turn_on_vpn(self):
        print("######### WARNING: PLEASE DO NOT MOVE YOUR MOUSE! #########")
        ok = True
        screenWidth, screenHeight = pyautogui.size()
        try:
            pyautogui.moveTo(screenWidth/2, screenHeight/2)
            time.sleep(0.5)
            for i in range(0, 3):
                try:
                    extn = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"Extension{i}.png").absolute()), grayscale=False)
                    pyautogui.click(x=extn[0], y=extn[1], clicks=1, interval=0.0, button="left")
                    break
                except Exception as e:
                    if i==2:
                        raise e
        except Exception as e:
            print("TabletScraper.config_browser Error1: ", e, traceback.format_exc())
            ok = False

        try:
            if ok:
                pyautogui.moveTo(screenWidth/2, screenHeight/2)
                time.sleep(1)
                for i in range(0, 3):
                    try:
                        free_vpn = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"FreeVPN{i}.png").absolute()), grayscale=False)
                        pyautogui.click(x=free_vpn[0], y=free_vpn[1], clicks=1, interval=0.0, button="left") 
                        break
                    except Exception as e:
                        if i==2:
                            raise e
        except Exception as e:
            print("TabletScraper.config_browser Error2: ", e, traceback.format_exc())
            ok = False

        try:
            if ok:
                pyautogui.moveTo(screenWidth/2, screenHeight/2)
                time.sleep(1)
                for i in range(0, 3):
                    try:
                        continue_btn = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"Continue{i}.png").absolute()), grayscale=False)
                        pyautogui.click(x=continue_btn[0], y=continue_btn[1], clicks=1, interval=0.0, button="left")
                        break
                    except Exception as e:
                        if i==2:
                            raise e
        except Exception as e:
            print("TabletScraper.config_browser Error3: ", e, traceback.format_exc())
            ok = False

        try:
            if ok:
                pyautogui.moveTo(screenWidth/2, screenHeight/2)
                time.sleep(1)
                for i in range(0, 3):
                    try:
                        start = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"Start{i}.png").absolute()), grayscale=False)
                        pyautogui.click(x=start[0], y=start[1], clicks=1, interval=0.0, button="left")
                        break 
                    except Exception as e:
                        if i==2:
                            raise e
        except Exception as e:
            print("TabletScraper.config_browser Error4: ", e, traceback.format_exc())
            ok = False

        try:
            pyautogui.moveTo(screenWidth/2, screenHeight/2)
            time.sleep(1)
            for i in range(0, 3):
                try:
                    no_thanks = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"NoThanks{i}.png").absolute()), grayscale=False)
                    pyautogui.click(x=no_thanks[0], y=no_thanks[1], clicks=1, interval=0.0, button="left") 
                    break
                except Exception as e:
                    if i==2:
                        raise e
        except:
           pass

        try:
            pyautogui.moveTo(screenWidth/2, screenHeight/2)
            time.sleep(1)
            for i in range(0, 3):
                try:
                    turn_on = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"TurnOn{i}.png").absolute()), grayscale=False)
                    pyautogui.click(x=turn_on[0], y=turn_on[1], clicks=1, interval=0.0, button="left") 
                    break
                except Exception as e:
                    if i==2:
                        raise e        
        except Exception as e:
            print("TabletScraper.config_browser Error6: ", e, traceback.format_exc())
            ok = False

        try:
            pyautogui.moveTo(screenWidth/2, screenHeight/2)
            time.sleep(5)
            for i in range(0, 3):
                try:
                    turned_on = pyautogui.locateCenterOnScreen(str((VPN_TURN_ON_IMGS_DIR / f"TurnedOn{i}.png").absolute()), grayscale=False)
                    ok = True
                    break
                except Exception as e:
                    if i==2:
                        raise e        
        except Exception as e:
            print("TabletScraper.config_browser Error7: ", e, traceback.format_exc())
            ok = False

        pyautogui.moveTo(screenWidth/2, screenHeight/2)

        if ok:
            print("VPN is Turned ON")
        else:
            print("Advice: Couldn't turn on the VPN. Please do it manually!")


    def config_browser(self, *args, **kwargs):
        print("Configuring browser...")
        chrome_driver_path = CHROME_DIR / 'chromedriver.exe'
        self.kill_browser_process()
        options = Options()
        options.page_load_strategy = "none"
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-gpu-blacklist")
        options.add_argument("--use-gl")
        options.add_argument("--allow-insecure-localhost")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--ignore-ssl-errors=yes")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--block-insecure-private-network-requests=false")
        options.add_argument(f"--unsafely-treat-insecure-origin-as-secure={SITE_DOMAIN}")
        options.add_argument("--safebrowsing-disable-download-protection")
        options.add_argument("--disable-gpu")
        if self.invisible:
            print("Configuring browser with invisible mode!")
            options.add_argument("--headless")
        else:
            print("Configuring browser with visible mode!")
        if not self.vpn_off and VPN_EXTN_DIR.exists():
            options.add_argument(f"--load-extension={VPN_EXTN_DIR.absolute()}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"user-agent={self.user_agent}")
        options.add_argument("--kiosk-printing")
        options.add_argument("--disable-blink-features")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-notifications")
        options.add_argument(f"user-data-dir={USER_DATA_DIR.absolute()}")
        options.set_capability("acceptInsecureCerts", True)
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        prefs = {
            "profile.default_content_setting_values.notifications" : 2,
            "safebrowsing_for_trusted_sources_enabled" : False,
            "safebrowsing.enabled" : False,
            "profile.exit_type" : "Normal"
        }
        options.add_experimental_option("prefs", prefs)
        os.environ["webdriver.chrome.driver"] = str(chrome_driver_path.absolute())
        service = Service(executable_path=chrome_driver_path, service_args=["--verbose"])
        self.browser = webdriver.Chrome(service=service, options=options)
        self.browser.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.browser.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent":self.user_agent})
        self.browser.set_page_load_timeout(self.page_load_timeout)
        self.browser.maximize_window()
        print("browserVersion: ", self.browser.capabilities["browserVersion"])
        print("chromedriverVersion: ", self.browser.capabilities["chrome"]["chromedriverVersion"].split(" ")[0])
        if not self.test_browser_ok():
            self.retry += 1
            if self.retry<=self.max_retries:
                self.config_browser()
            else:
                raise Exception("Failed to configure browser.")
        else:
            self.retry = 0
        
        if not self.vpn_off and VPN_TURN_ON_IMGS_DIR.exists():
            while len(self.browser.window_handles)<=1:
                time.sleep(1)
            self.browser.switch_to.window(self.browser.window_handles[1])
            time.sleep(0.5)
            self.browser.execute_script("alert('PLEASE DO NOT MOVE YOUR MOUSE AND DO NOT PRESS ANY KEY!');")
            time.sleep(0.5)
            self.turn_on_vpn()

        closed = False
        for _ in range(0, 3):
            try:
                time.sleep(1)
                self.browser.switch_to.window(self.browser.window_handles[1])
                self.browser.execute_script("window.close();")
                closed = True
                break
            except:
                closed = False
        if not closed:
            print("##### WARNING: Please close this tab manually --> 'Thank you for installing VeePN' #####")
        try:
            self.browser.switch_to.window(self.browser.window_handles[0])
        except Exception as e:
            print("TabletScraper.config_browser Error4: ", e, traceback.format_exc())
        
    def get_clickable_element(self, by_tuple):
        el = None
        error = ""
        sep = ""
        try:
            el = WebDriverWait(self.browser, 10).until(EC.presence_of_element_located(by_tuple))
        except Exception as e:
            error += f"Error1: {e}"
            sep = "\n"
        try:
            el1 = WebDriverWait(self.browser, 10).until(EC.element_to_be_clickable(by_tuple))
            if el1 is not None:
                el = el1
        except Exception as e:
            error += f"{sep}Error2: {e}"
        if len(error)>0:
            error = f"TabletScraper.get_clickable_element {error}"
            print(e)
        return el


    def ask_credentials(self):
        creds_import()
        global USERNAME, PASSWORD
        if USERNAME is None or PASSWORD is None:
            ask_username = True
            again = ""
            while True:
                if ask_username:
                    username = input(f"Please type the username{again}: ")
                    if len(username)==0:
                        print("Username can't be empty!")
                        continue
                    USERNAME = username
                password = getpass(f"Please type the password{again}: ")
                if len(password)==0:
                    print("Password can't be empty!")
                    ask_username = False
                    continue
                confirm_password = getpass(f"Please re-type the password{again}: ")
                if password!=confirm_password:
                    print("Password doesn't match!")
                    again = " again"
                    ask_username = False
                    continue
                PASSWORD = password
                ask_username = True
                again = ""
                if confirmation_input("Please confirm by", "y/N")==True:break
            creds_export()
        else:
            if confirmation_input("Reuse the username & password", "Y/n")==False:
                if CREDS_PATH.exists():
                    CREDS_PATH.unlink(missing_ok=True)
                USERNAME = None
                PASSWORD = None
                return self.ask_credentials()

    def cleanup_session_login(self):
        if self.is_title_valid(None) or self.is_title_valid("") or self.is_page_ready(LOGIN_SESSION_EXPIRED_TITLE):
            body_el = self.browser.find_element(By.TAG_NAME, "body")
            body_el.send_keys(Keys.ESC)
            print("Re-configuring and Re-loging...")
            if USER_DATA_DIR.exists():
                self.kill_browser_process()
                shutil.rmtree(USER_DATA_DIR)
                USER_DATA_DIR.mkdir(exist_ok=True)
            self.config_browser()
            return self.login()
        return False
    
    def login(self):
        if self.get_page(LOGIN_URL, LOGIN_TITLE):
            username_el = self.browser.find_element(By.ID, "username")
            password_el = self.browser.find_element(By.NAME, "password")
            otp_el = self.browser.find_element(By.NAME, "otp")
            btn_signin_el = self.get_clickable_element((By.ID, "btn_signin"))
            if btn_signin_el is not None:
                self.ask_credentials()
                username_el.send_keys(USERNAME)
                password_el.send_keys(PASSWORD)
                javascript = '''return generateOTP(document.querySelector("#username"), document.querySelector("[name='password']"));'''
                self.browser.execute_script(javascript)
                while True:
                    otp = input("Please type the OTP: ")
                    if len(otp)==0:
                        print("OTP can't be empty!")
                        continue
                    if confirmation_input("Please confirm by", "y/N")==True:break
                otp_el.send_keys(otp)
                btn_signin_el.click()
                time.sleep(4)
                print(f"Waiting for login redirect title {LOGIN_REDIRECT_TITLE}!")
                if not self.is_page_ready(LOGIN_REDIRECT_TITLE):
                    if not self.cleanup_session_login():
                        print("Couldn't login!!! Re-loging...")
                        return self.login()
                return True
        print()
        print("Browser Title: ", self.browser.title)
        print()
        return self.cleanup_session_login() or self.is_page_ready(LOGIN_REDIRECT_TITLE) or self.is_page_ready(SITE_TITLE)

    def get_franchise_list_codelist(self, page_source):
        soup = BeautifulSoup(page_source, "html.parser")
        franchise_list = [" ".join([x.strip() for x in fl.text.strip(" ").split()]) for fl in soup.find("select", {"class": "franchise_list"}).find_all("option")][1:]
        franchise_code_list = [" ".join([x.strip() for x in fl.attrs.get("value").strip(" ").split()]) for fl in soup.find("select", {"class": "franchise_list"}).find_all("option")][1:]
        return (franchise_list, franchise_code_list)

    def parse_and_save(self, page_source, franchise, page, save=True):
        has_next_button = False
        try:
            soup = BeautifulSoup(page_source, "html.parser")
            has_next_button = soup.find("button", {"class": "btnNextShipped"}) is not None
            if not save:
                return has_next_button
            customer_names = [cn.text.strip() for cn in soup.find_all("td", {"class": "customer_name"})]
            customer_mobiles = [cm.text.strip() for cm in soup.find_all("td", {"class": "customer_mobile"})]
            full_addresses = [fa.text.strip() for fa in soup.find_all("td", {"class": "fullAddress"})]
            address_pins = [ap.text.strip() for ap in soup.find_all("td", {"class": "address_pin"})]
            billing_amounts = [ap.text.strip() for ap in soup.find_all("td", {"class": "billing_amount"})]
            if len(customer_names)>0:
                filepath = DATA_DIR / f"{franchise}.xlsx" 
                if filepath.exists():
                    original_df = pd.read_excel(str(filepath.absolute()), sheet_name=None)
                    sheets = list(original_df.keys())
                else:
                    original_df = pd.DataFrame()
                    sheets = []
                
                df = pd.DataFrame({
                                "Customer Name": customer_names, 
                                "Customer Mobile": customer_mobiles, 
                                "Shipping Address": full_addresses, 
                                "Pincode": address_pins,
                                "Total Billing Amount" : billing_amounts
                            })
                sheet_name = f"Page {page}"
                while True:
                    try:
                        with pd.ExcelWriter(path=str(filepath.absolute()), engine="openpyxl") as writer:
                            for sheet in sheets:
                                original_df[sheet].to_excel(excel_writer=writer, sheet_name=sheet, index=False)
                            df.to_excel(excel_writer=writer, sheet_name=sheet_name, index=False)
                        print(f"{len(customer_names)} customers have been saved in sheet '{sheet_name}' at '{filepath}'")
                        break
                    except Exception as e:
                        print("TabletScraper.parse_and_save Error1: ", e, traceback.format_exc())
                        if confirmation_input("Try again?", "y/N")==False:
                            print("Data not saved. Procceeding to next!")
                            break                    
            else:
                print(f"Page {page} has no customer data.")
        except Exception as e:
            print("TabletScraper.parse_and_save Error2: ", e, traceback.format_exc())
        return has_next_button

    def start_scraping(self, offset_franchise_code=None):
        try:
            max_retries = 3
            retry = 0
            while True:
                try:
                    self.config_browser()
                    break
                except Exception as e:
                    print("TabletScraper.start_scraping Error: ", e, traceback.format_exc())
                    retry += 1
                if retry>max_retries:
                    raise Exception("Browser can't be configured at this moment!")
            if confirmation_input("Start?", "Y/n")==False:return
            if self.login():
                url = f"{SITE_URL}/1"
                print(f"Waiting for title: {SITE_TITLE} @ {url}")
                if not self.get_page(url, SITE_TITLE):
                    print("Page not found. Restarting")
                    self.start_scraping(offset_franchise_code=offset_franchise_code)
                WebDriverWait(self.browser, 20).until(EC.presence_of_element_located((By.TAG_NAME, "title")))
                page_source = self.browser.page_source
                franchise_list, franchise_code_list = self.get_franchise_list_codelist(page_source)
                if offset_franchise_code is not None and offset_franchise_code in franchise_code_list:
                    skip_index = franchise_code_list.index(offset_franchise_code)
                    franchise_code_list = franchise_code_list[skip_index:]
                    franchise_list = franchise_list[skip_index:]
                    
                existing_franchise_list =  [f.split(".")[0] for f in os.listdir(ARCHIVE_DIR)]
                considerable_list = [f.split(".")[0] for f in os.listdir(DATA_DIR)]
                for i, franchise_code in enumerate(franchise_code_list):
                    try:
                        franchise = franchise_list[i]
                        franchise = franchise.replace("/", "")
                        if franchise in existing_franchise_list:
                            print(f"Franchise {franchise} already exists in {str(ARCHIVE_DIR.absolute())}\nSkip processing franchise {franchise}")
                            continue
                        page = 1
                        save = True
                        if franchise in considerable_list:
                            print(f"Franchise {franchise} already exists in {str(DATA_DIR.absolute())}, but checking if it's properly completed!")
                            if (DATA_DIR / f"{franchise}.xlsx").exists():
                                df = pd.read_excel(DATA_DIR / f"{franchise}.xlsx", sheet_name=None)
                                sheets = list(df.keys())
                                if len(sheets)>0:
                                    page = int(sheets[-1].replace("Page", "").strip())
                                    save = False
                        while True:
                            wait_time = random.randrange(1, 2)
                            print(f"Processing franchise: {franchise}, page: {page} will get started after {wait_time} secs")
                            time.sleep(wait_time)
                            try:
                                url = f"{SITE_URL}/{franchise_code}?page_size=20&page={page}"
                                if self.get_page(url, SITE_TITLE):
                                    page_source = self.browser.page_source
                                    has_next_button = self.parse_and_save(page_source, franchise, page, save=save)
                                    if not has_next_button:
                                        break
                                    page += 1
                                    save = True
                                else:
                                    print(f"Couldn't get page for {franchise}")
                                    if confirmation_input(f"Retry with re-configuring and re-login...", "N/y")==True:
                                        return self.start_scraping(offset_franchise_code=franchise_code_list[i-2])
                                    elif confirmation_input(f"Retry with only re-login...", "N/y")==True:
                                        self.login()
                                    else:
                                        print("Trying to get the page again...")
                            except Exception as e:
                                print("TabletScraper.start_scraper Error: ", e, traceback.format_exc())
                                print(f"Skipping {url}")
                                break
                        src_filepath = DATA_DIR / f"{franchise}.xlsx"
                        dst_filepath = ARCHIVE_DIR / f"{franchise}.xlsx"
                        if src_filepath.exists():
                            shutil.move(src_filepath.absolute() , dst_filepath.absolute())
                            print(f"{franchise}.xlsx is successfully moved to {ARCHIVE_DIR.absolute()}")
                        print("####################################################################")
                        print()
                    except Exception as e:
                        print("TabletScraper.start_scraping Error1: ", e, traceback.format_exc())
                if len(franchise_code_list)>0:
                    print("######################## COMPLETED ########################")
        except Exception as e:
            print("TabletScraper.start_scraping Error2: ", e, traceback.format_exc())
        self.kill_browser_process()
            
                    


if __name__ == "__main__":
    argv = sys.argv
    parser = argparse.ArgumentParser(prog=PROJECT_NAME, description=PROJECT_DESCRIPTION)
    parser.version = VERSION
    parser.add_argument("-v", "--version", action="version", version=parser.version)
    parser.add_argument(
        "-c",
        "--ofc",
        dest="OFFSET_FRANCISE_CODE",
        default=None,
        required=False,
        help="Run script with Offset Francise Code, default: None"
    )
    parser.add_argument(
        "-inviz",
        "--invisible",
        dest="INVISIBLE",
        action='store_true',
        default=False,
        required=False,
        help="Run script with visible mode, default: visible"
    )

    parser.add_argument(
        "-vpn_off",
        "--vpn_off",
        dest="VPN_OFF",
        action='store_true',
        default=False,
        required=False,
        help="Run script with VPN, default: ON"
    )

    args = parser.parse_args(argv[1:])
    print(parser.description)
    OFFSET_FRANCISE_CODE = args.OFFSET_FRANCISE_CODE
    print("Offset Francise Code: ", OFFSET_FRANCISE_CODE)
    INVISIBLE = args.INVISIBLE
    print("INVISIBLE: ", INVISIBLE)
    VPN_OFF = args.VPN_OFF
    print("VPN_OFF: ", VPN_OFF)
    tablet_scraper = TabletScraper(invisible=INVISIBLE, vpn_off=VPN_OFF)
    tablet_scraper.start_scraping(offset_franchise_code=OFFSET_FRANCISE_CODE)
