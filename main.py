import asyncio
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import yaml

from funcs import get_books_with_index, get_book_set_info
from webdriver_download import webdriver_download, login, ran_out_download_limit, add_to_downloaded_set, \
    remove_from_waiting_download_set
import json
from os import walk


async def get_file_download_info(book_set_url_base, download_files, exclude_downloaded_file_names,
                                 lib_book_set_ids):
    books = []
    tasks = []
    for lib_book_set_id in lib_book_set_ids:
        url = f"{book_set_url_base}/{lib_book_set_id}/get-books"
        # get info
        print(f"{url}/{0}")
        book_set_info = get_book_set_info(url)
        print(
            f"book set id: {lib_book_set_id}, url: {url}, info: {book_set_info}, starting getting all books info in this page")

        for index in range(0, book_set_info["total_pages"], 1):
            tasks.append(get_books_with_index(url, index))
    print(f"Starting get books infos , len: {len(tasks)}")
    results = await asyncio.gather(*tasks)
    for book_info in results:
        books.extend(book_info["books"])
    print(f"waiting_for_download_files: {len(books)}")
    print(f"books {len(books)}")
    waiting_for_download_files = {}
    waiting_for_download_files_only_name = set([])
    downloaded_files_only_name = set([])
    for b in books:
        downloaded = False
        for download_book in download_files:
            title = b["book"]["title"]
            if title in download_book:
                # print(f"{title} in {download_book}")
                downloaded = True
                break
        if not downloaded:
            for exclude_downloaded_file_name in exclude_downloaded_file_names:
                title = b["book"]["title"]
                if exclude_downloaded_file_name in title:
                    # print(f"{exclude_downloaded_file_name} in {title}, be excluded")
                    downloaded = True
                    break
        if not downloaded:
            waiting_for_download_files[b["book"]["title"]] = b
            waiting_for_download_files_only_name.add(b["book"]["title"])
        else:
            downloaded_files_only_name.add(b["book"]["title"])
    print(f"downloaded_files_only_name: {len(downloaded_files_only_name)}")
    print(f"waiting_for_download_files: {len(waiting_for_download_files)}")
    print(f"all books {len(books)}")
    return downloaded_files_only_name, waiting_for_download_files, waiting_for_download_files_only_name


def get_file_names(ebooks_path, exclude_downloaded_dirs):
    download_files = []
    for (dir_path, dir_names, file_names) in walk(ebooks_path):
        is_exclude_dir = False
        for exclude_dir in exclude_downloaded_dirs:
            if exclude_dir in dir_path:
                is_exclude_dir = True
                break
        if is_exclude_dir:
            continue
        download_files.extend(file_names)
        print(f"Total file amt: {len(download_files)}. In {dir_path}, file amt: {len(file_names)}. ")
    return download_files


async def main():
    try:
        with open("./settings.yml", 'r') as stream:
            data_loaded = yaml.safe_load(stream)
    except:
        print("Read settings.yml failed!, exit")
        exit(0)

    logout_url = data_loaded["logout_url"]
    accounts = data_loaded["accounts"]
    if accounts == None:
        accounts = []

    downloaded_dirs = data_loaded["downloaded_dirs"]
    exclude_downloaded_file_names = data_loaded["exclude_downloaded_file_names"]
    exclude_downloaded_dirs = data_loaded["exclude_downloaded_dirs"]

    book_list_owner_cookies = data_loaded["book_list_owner_cookies"]

    file_download_dir = data_loaded["file_download_dir"]
    download_book_list_id = data_loaded["download_book_list_id"]
    book_set_url_base = data_loaded["book_set_url_base"]
    book_detail_url_base = data_loaded["book_detail_url_base"]
    logout_success_redirect_url = data_loaded["logout_success_redirect_url"]

    waiting_for_download_files_file_name = data_loaded["waiting_for_download_files_file_name"]
    waiting_for_download_files_only_name_file_name = data_loaded["waiting_for_download_files_only_name_file_name"]
    downloaded_files_only_name_file_name = data_loaded["downloaded_files_only_name_file_name"]
    account_waiting_time = data_loaded["account_waiting_time"]

    lib_book_set_ids = data_loaded["lib_book_set_ids"]

    print("Starting to get books information......")
    download_files = await get_download_files(downloaded_dirs, exclude_downloaded_dirs)

    downloaded_files_only_name, waiting_for_download_files, waiting_for_download_files_only_name = await get_file_download_info(
        book_set_url_base, download_files, exclude_downloaded_file_names, lib_book_set_ids)

    print("Starting to use webdriver..........")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    new_download_files = []

    for account in accounts:
        print(f"{account[0]} login")
        login_success = login(driver, account[0], account[1], logout_url)

        if not login_success:
            continue
        for new_download_file in new_download_files:
            waiting_for_download_files.pop(new_download_file)
            # TODO remove
            print(f"pop download file: {new_download_file}, len(rest): {len(new_download_file)}")
        print(f"{account[0]} login success")
        for waiting_for_download_file in waiting_for_download_files.values():
            try:
                book_id = waiting_for_download_file["book"]["id"]
                book_hash = waiting_for_download_file["book"]["hash"]

                driver.get(f"{book_detail_url_base}/{book_id}/{book_hash}")

                time.sleep(5)
                try:
                    download_btn_path = "/html/body/table/tbody/tr[2]/td/div/div/div/div[2]/div[2]/div[1]/div[1]/div/a"
                    driver.find_element(By.XPATH, download_btn_path).click()
                    time.sleep(20)

                    if ran_out_download_limit(driver):
                        break
                except Exception as e:
                    print(f"error: {e}")
                    continue

                add_to_downloaded_set_success = add_to_downloaded_set(book_id,
                                                                      book_set_url_base,
                                                                      download_book_list_id,
                                                                      book_list_owner_cookies)

                new_download_files.append(waiting_for_download_file["book"]["title"])

                book_title = waiting_for_download_file["book"]["title"]
                if add_to_downloaded_set_success:
                    print(f"Success add {book_title} to downloaded book set")
                else:
                    print(f"Add {book_title} to download books failed!!!!")

                readlist_id = waiting_for_download_file["readlist_id"]
                readlist_book_id = waiting_for_download_file["id"]
                remove_from_waiting_download_set_success = remove_from_waiting_download_set(readlist_id,
                                                                                            readlist_book_id,
                                                                                            book_set_url_base,
                                                                                            book_list_owner_cookies)

                if remove_from_waiting_download_set_success:
                    print(f"Success remove {book_title} from waiting download book set")
                else:
                    print(f"Failed to remove {book_title} from waiting download book set")

            except Exception as e:
                print(f"{account[0]} download failed, err: {e}")

        driver.get(logout_url)
        time.sleep(10)
        if driver.current_url != logout_success_redirect_url:
            print(f"{account[0]} logout failed, current_url: {driver.current_url}")
            break

        # for download file waiting
        time.sleep(account_waiting_time)
        print(f"{account[0]} logout success")

    print("driver.quit()")
    driver.quit()

    print("Starting to get books information......")
    download_files = await get_download_files(downloaded_dirs, exclude_downloaded_dirs)

    downloaded_files_only_name, waiting_for_download_files, waiting_for_download_files_only_name = await get_file_download_info(
        book_set_url_base, download_files, exclude_downloaded_file_names, lib_book_set_ids)
    print("Starting write download info files......")
    f_path = f"{file_download_dir}/{waiting_for_download_files_file_name}.json"
    with open(f_path, 'w') as f:
        json.dump(waiting_for_download_files, f, ensure_ascii=False)
    print(f"Write {f_path} complete")

    f_path = f"{file_download_dir}/{waiting_for_download_files_only_name_file_name}.txt"
    waiting_for_download_files_only_name_set = set(waiting_for_download_files_only_name)
    downloaded_files_only_name_set = set(downloaded_files_only_name)

    with open(f_path, 'w', encoding='utf-8') as f:
        f.write("[\n")
        for line in waiting_for_download_files_only_name_set:
            f.write(f"{line},\n")
        f.write("]")
    print(f"Write {f_path} complete")

    f_path = f"{file_download_dir}/{downloaded_files_only_name_file_name}.txt"
    with open(f_path, 'w', encoding='utf-8') as f:
        f.write("[\n")
        for line in downloaded_files_only_name_set:
            f.write(f"{line},\n")
        f.write("]")
    print(f"Write {f_path} complete")


async def get_download_files(downloaded_dirs, exclude_downloaded_dirs):
    download_files = []
    for downloaded_dir in downloaded_dirs:
        download_files.extend(get_file_names(downloaded_dir, exclude_downloaded_dirs))
    return download_files


if __name__ == '__main__':
    asyncio.run(main())

    exit(0)
