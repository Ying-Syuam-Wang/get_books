import json
import urllib.request
import requests


def api_download(books_set_url,
                 download_books_info_file_full_name,
                 file_download_dir,
                 redirect_url_base,
                 cookies,
                 book_set_url_base,
                 download_book_list_id,
                 book_list_owner_cookies,
                 start_page_index=0, daily_limit=9999):
    books_info = get_book_set_info(books_set_url)
    total_pages_num = books_info["total_pages"]
    total_items_num = books_info["total_items"]

    print(f"total_pages_num: {total_pages_num}, total_items_num: {total_items_num}")

    download_books_dict = {}
    # # 'w' – open a file for writing.If the file doesn’t exist, the open() function creates a new file.Otherwise, it’ll overwrite the contents of the existing file.
    with open(download_books_info_file_full_name, 'w') as f:
        try:
            download_books_dict = json.load(f)
        except Exception as e:
            print(f"Read download_books_info_file_full_name failed, with {e}. Might be an empty file.")
            pass
    new_download_file_dict = {}

    print("Starting get all book though api....")
    for i in range(start_page_index, total_pages_num):
        if daily_limit == 0:
            exit("daily_limit is up")
        print(f"Getting books , index: {i}")
        books_page_info = get_books_with_index(books_set_url, i)
        for idb, b in enumerate(books_page_info["books"]):
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
            dl = b["book"]["dl"]
            print(
                f"{i}.{idb}. {file_name} download url: {redirect_url_base}{dl}, download position: {file_download_position}")

            try:
                download_file(f"{redirect_url_base}{dl}", cookies, file_download_position)
                daily_limit -= 1
                # update the downloaded json
                new_download_file_dict[file_name] = b

                # add to downloaded book set
                book_id = b["book"]["id"]
                print(f"{book_set_url_base}/{download_book_list_id}/add-book/{book_id}")
                add_to_download_book_set_resp = requests.get(
                    f"{book_set_url_base}/{download_book_list_id}/add-book/{book_id}",
                    headers={"cookie": book_list_owner_cookies})
                if add_to_download_book_set_resp.status_code == 200:
                    print("Success add to downloaded book set")
                    # remove from the book set
                    readlist_id = b["readlist_id"]
                    id = b["id"]
                    remove_from_download_book_set_resp = requests.get(
                        f"{book_set_url_base}/{readlist_id}/remove-book/{id}",
                        headers={"cookie": book_list_owner_cookies})
                    if remove_from_download_book_set_resp.status_code == 200:
                        print("Success remove books from waiting download book set")
                    else:
                        print("Failed to remove books from waiting download book set")
                else:
                    print(f"Add {file_name} to download books failed!!!!")
            except Exception as e:
                print(f"download {file_name} failed!!!, e: {e}")
        print(f"Done getting for page index:{i}, new_download_file_dict count: {len(new_download_file_dict)}")

    # setting ensure_ascii and encoding for chinese
    new_download_file_string = json.dumps(new_download_file_dict, ensure_ascii=False)
    with open(download_books_info_file_full_name, 'w', encoding="utf8") as outfile:
        outfile.write(new_download_file_string)
    exit(0)


def book_list_to_name_map(lst):
    res_dct = {}
    for i in range(0, len(lst), 1):
        title = lst[i]["book"]["title"]
        year = lst[i]["book"]["year"]
        res_dct[f"{title}_year_{year}"] = lst[i]
    return res_dct


async def get_books_with_index(books_set_url, page_index):
    book_set_url_with_index = f"{books_set_url}/{page_index}"
    get_books_resp = requests.get(book_set_url_with_index)
    books_info = get_books_resp.json()
    if books_info["success"] != 1:
        print('get books failed, success code: %c'.format(books_info))

    return books_info


def get_book_set_info(books_set_url):
    book_set_url_with_index = f"{books_set_url}/0"
    get_books_resp = requests.get(book_set_url_with_index)
    books_info = get_books_resp.json()
    if books_info["success"] != 1:
        print('get books not success, success code: %c'.format(books_info))
        # TODO throw an error
        exit(0)

    total_pages_num = books_info["pagination"]["total_pages"]
    total_items_num = books_info["pagination"]["total_items"]
    return {"total_pages": total_pages_num, "total_items": total_items_num}


def download_file(redirect_url, cookies, file_download_position):
    # get the init url
    response = requests.get(
        redirect_url,
        allow_redirects=False,
        headers={"cookie": cookies}
    )
    # get source url
    url = response.headers['Location']
    print(f"download from {redirect_url}, download url: {url}")
    # download file
    if "wrongHash" in url:
        raise Exception("redirect url has wrongHash")
    urllib.request.urlretrieve(response.headers['Location'], file_download_position)
    with urllib.request.urlopen(url) as f:
        f.read()
    print('download finished')
