import requests
from bs4 import BeautifulSoup
import db
import uuid
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36"}


def load_html(url):
    time.sleep(1)
    print("loading page: " + url)
    html = requests.get(
        url, headers=headers)
    return BeautifulSoup(html.text, "html.parser"), url


def get_thread_urls(soup):
    links = []
    for link in soup.find_all("a", attrs={"href": re.compile("/keskustelu/(\d+)/")}):
        href = link.get("href")
        try:
            href = re.sub(r"\?changed=(\d+)", "", href)
            href = re.sub(r"\?page=(\d+)", "", href)
        except:
            print("nothing to see...")
        links.append("https://www.vauva.fi" + href)
    # remove duplicatest from links
    links = list(set(links))
    return links


def get_last_page_number(soup):
    li = soup.find(name="li", attrs={"class": re.compile("pager-last")})
    if li:
        number = li.find("span").string
        return number
    else:
        return 0


def goto_next_page(soup):
    href = None
    link_div = soup.find("li", attrs={"class": "pager-next"})
    if link_div:
        href = "https://vauva.fi" + link_div.next.attrs['href']
    return href


def format_data(data):
    data = data.replace("\n", "").replace("\r", "")
    data = data.replace("Vierailija kirjoitti:", "")
    return data


def parse_comment(soup, url):
    comments = []
    comment_reply = dict()
    topic_header = soup.find("h1")

    if topic_header is None:
        return comments

    comment = topic_header.string
    comment_wrapper = soup.find(name="div", attrs={"class": "sanoma-comment"})

    if comment_wrapper is None:
        return comments

    comment_div = comment_wrapper.find(
        name="div", attrs={"class": "field-item", "property": "content:encoded"})
    comment_id = int(re.findall('\d+', url)[0])
    if comment_div and comment_div.contents and len(comment_div.contents) > 0:
        content = comment_div.contents[0]
        if content and content.string is not None:
            reply = " " + content.string
            comment_reply = {"comment_id": comment_id, "parent_id": None,
                             "comment": comment, "reply": reply}

    comments.append(comment_reply)

    comments_wrapper = soup.find(
        "div", attrs={"class": "comments-list-wrapper"})

    if comments_wrapper is None:
        return comments

    comment_ids = comments_wrapper.find_all(
        "a", attrs={"id": re.compile("comment-(\d+)")})

    i = 0
    articles = comments_wrapper.find_all("article", attrs={"class": "comment"})

    for article in articles:
        reply_text = ""
        comment_text = ""
        middle = article.find(
            "div", attrs={"class": "middle clearfix"})
        field_item = middle.find(
            "div", attrs={"class": "field-item"})

        reply_found = False
        comment_found = False
        for field_item_element in reversed(field_item.contents):
            if field_item_element.name == "p" and reply_found == False and format_data(field_item_element.text) != "":
                reply_text += format_data(field_item_element.text)
                reply_found = True
            elif field_item_element.name == "p" and reply_found == True and format_data(field_item_element.text) != "":
                comment_text += format_data(field_item_element.text)
                comment_found = True
            elif reply_found and comment_found:
                break
        ci = str(comment_ids[i])
        reply_id = int(re.findall('\d+', ci)[0])
        if comment_text == "":
            comment_text = comment
        reply = {"comment_id": reply_id, "parent_id": comment_id, "comment": comment_text, "reply":
                 reply_text}

        comments.append(reply)
        i += 1

    return comments


def find_page(page):
    return db.find_page(page)


def save_page(page):
    db.insert_page(page)


conv_topics = ["aihe_vapaa", "vauvakuume", "raskaus_ja_synnytys", "vauvat_ja_taaperot", "kasvatus", "perhe_ja_arki", "lapsettomuus_ja_adoptio", "erota_vai_ei_kysy_asiantuntijat_vastaavat",
               "kysy_terveydenhoitajalta", "kysy_seksuaaliterapeutilta", "keskustelu_unesta_ja_jaksamisesta", "keskutelu_nettikiusaamisesta", "seksi", "nimet"]

db.create_tables()
topic_index = 0
links = []
try:
    for topic_page_index in range(0, 5):
        for topic_index in range(len(conv_topics)):
            page_url_param = ""
            if topic_page_index > 0:
                page_url_param = "?page=" + str(topic_page_index)

            soup, url = load_html(
                "https://www.vauva.fi/keskustelu/alue/" + conv_topics[topic_index] + page_url_param)
            links += get_thread_urls(soup)

        print("crawling with {} comment links".format(len(links)))

        for link in links:
            if find_page(link):
                # print("allready crawled {}".format(link))
                continue
            save_page(link)
            page, url = load_html(link)
            comments = parse_comment(page, url)
            if len(comments) > 0:
                db.insert_comments(comments)
            href = goto_next_page(page)
            while href:
                if not find_page(href):
                    save_page(href)
                    comment_page, url = load_html(href)
                    comments = parse_comment(comment_page, url)
                    if len(comments) > 0:
                        db.insert_comments(comments)
                    href = goto_next_page(comment_page)
                else:
                    break
except KeyboardInterrupt:
    pass
finally:
    print("Closing crawler.. last commits..")
    db.close()
