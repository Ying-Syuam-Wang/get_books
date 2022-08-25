import json
import time

import requests
from selenium.webdriver.common.by import By

from funcs import get_book_set_info, get_books_with_index


def add_to_downloaded_set(book_id,
                          book_set_url_base,
                          download_book_list_id,
                          book_list_owner_cookies):
    # add to downloaded book set
    print(f"{book_set_url_base}/{download_book_list_id}/add-book/{book_id}")
    add_to_download_book_set_resp = requests.get(
        f"{book_set_url_base}/{download_book_list_id}/add-book/{book_id}",
        headers={"cookie": book_list_owner_cookies})
    return add_to_download_book_set_resp.status_code == 200


def remove_from_waiting_download_set(readlist_id, readlist_book_id, book_set_url_base, book_list_owner_cookies):
    # remove from the book set
    remove_from_download_book_set_resp = requests.get(
        f"{book_set_url_base}/{readlist_id}/remove-book/{readlist_book_id}",
        headers={"cookie": book_list_owner_cookies})
    return remove_from_download_book_set_resp.status_code == 200


def ran_out_download_limit(driver):
    try:
        driver.find_element(By.XPATH, "//*[contains(text(), '每日限额已用完')]")
        return True
    except:
        return False


def webdriver_download(driver,
                       daily_limit,
                       book_detail_url_base,
                       books_set_url,
                       download_books_info_file_full_name,
                       start_page_index,
                       file_download_dir,
                       book_set_url_base,
                       download_book_list_id,
                       book_list_owner_cookies):
    books_info = get_book_set_info(books_set_url)
    total_pages_num = books_info["total_pages"]
    total_items_num = books_info["total_items"]

    print(f"total_pages_num: {total_pages_num}, total_items_num: {total_items_num}")

    download_books_dict = {}
    # 'w' – open a file for writing.If the file doesn’t exist, the open() function creates a new file.Otherwise, it’ll overwrite the contents of the existing file.
    with open(download_books_info_file_full_name, 'w') as f:
        try:
            download_books_dict = json.load(f)
        except Exception as e:
            print(f"Read download_books_info_file_full_name failed, with {e}. Might be an empty file.")
            pass
    new_download_file_dict = {}

    print("Starting get all book though api....")

    for i in range(start_page_index, total_pages_num):
        print(f"Getting books , index: {i}")
        books_page_info = get_books_with_index(books_set_url, i)
        for idb, b in enumerate(books_page_info["books"]):
            if daily_limit == 0:
                raise Exception("daily_limit is up")

            title = b["book"]["title"]
            year = b["book"]["year"]
            extension = b["book"]["extension"]
            file_name = f"{title}({year}).{extension}"
            # check is the book already downloaded
            if file_name in download_books_dict:
                print(f"{file_name} already exist. will not download again")
                continue
            # download the books from this page
            file_download_position = f"{file_download_dir}/{file_name}"
            book_id = b["book"]["id"]
            book_hash = b["book"]["hash"]

            print(
                f"{i}.{idb}. {file_name} book detail url: {book_detail_url_base}/{book_id}/{book_hash}, download position: {file_download_position}")

            driver.get(f"{book_detail_url_base}/{book_id}/{book_hash}")
            time.sleep(5)
            try:
                driver.find_element(By.XPATH,
                                    "/html/body/table/tbody/tr[2]/td/div/div/div/div[2]/div[2]/div[1]/div[1]/div/a").click()
                time.sleep(20)

                if ran_out_download_limit(driver):
                    raise Exception("Ran out of download limit")
            except Exception as e:
                if "Ran out of download limit" in e.args:
                    raise Exception("Ran out of download limit")
                print(f"error: {e}")
                continue

            daily_limit -= 1
            # update the downloaded json
            new_download_file_dict[file_name] = b

            book_id = b["book"]["id"]
            is_add_to_download_success = add_to_downloaded_set(book_id,
                                                               file_name,
                                                               book_set_url_base,
                                                               download_book_list_id,
                                                               book_list_owner_cookies)

            if is_add_to_download_success:
                readlist_id = b["readlist_id"]
                readlist_book_id = b["id"]
                remove_from_waiting_download_set(readlist_id, readlist_book_id, book_set_url_base,
                                                 book_list_owner_cookies)

        print(f"Done getting for page index:{i}, new_download_file_dict count: {len(new_download_file_dict)}")

        # setting ensure_ascii and encoding for chinese
    new_download_file_string = json.dumps(new_download_file_dict, ensure_ascii=False)
    with open(download_books_info_file_full_name, 'w', encoding="utf8") as outfile:
        outfile.write(new_download_file_string)


def login(driver, account, pwd, login_url):
    try:
        driver.get(login_url)
        time.sleep(3)
        driver.find_element(By.XPATH,
                            "/html/body/table/tbody/tr[2]/td/div/div/div/div/div[1]/form/div[1]/input").send_keys(
            account)
        driver.find_element(By.XPATH,
                            "/html/body/table/tbody/tr[2]/td/div/div/div/div/div[1]/form/div[2]/input").send_keys(pwd)
        driver.find_element(By.XPATH, "/html/body/table/tbody/tr[2]/td/div/div/div/div/div[1]/form/button").click()
        time.sleep(20)
        return True
    except Exception as e:
        print(f"error: {e}")
        return False
