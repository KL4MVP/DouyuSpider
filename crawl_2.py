import requests
from bs4 import BeautifulSoup
import pymysql
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
import selenium.webdriver.support.ui as ui
from selenium.common.exceptions import TimeoutException

def create_table(pw):
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    sql1 = '''
        create table comments(
        number int(3),
        user_number int(3),
        nickname varchar(50),
        level varchar(20),
        contents varchar(255)
        )
        '''
    cursor.execute(sql1)
    db.close()
    print("创建数据库表成功!")

def get_room_urls(url):
    wb_data = requests.get(url).text
    soup = BeautifulSoup(wb_data, 'lxml')
    room_nums = soup.find_all("a", class_="DyListCover-wrap")
    room_urls = []
    for room_num in room_nums:
        room_url = "https://www.douyu.com" + room_num.get('href')
        room_urls.append(room_url)
    print("获取直播间链接成功!")
    return room_urls

def is_visible(locator, timeout=5):
    try:
        ui.WebDriverWait(driver,timeout,1).until(EC.visibility_of_element_located((By.XPATH, locator)))
        return True
    except TimeoutException:
        return False

def write_to_DB(pw,k,comments_data):
    # pw = input("请输入密码以登录数据库：")
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    j = 1
    for data in comments_data:
        nickname = data['nickname']
        level = data['level']
        contents = data['contents']
        sql_insert = '''insert into comments(number,user_number,nickname,level,contents)
                       values('%d','%d','%s','%s','%s')
                       ''' % (k, j, nickname, level, contents)
        cursor.execute(sql_insert)
        db.commit()
        j += 1
    db.close()
    print("导入数据库成功!")


def get_comment(pw,driver,urls):
    comments_data = []
    k=1
    for url in urls:
        print("正在爬取直播间{}".format(k))
        driver.get(url)
        time.sleep(2)
        if is_visible("//*[@id='js-player-title']/div/div[3]/div[3]/a[1]/h2"):
            if is_visible("//*[@id='bc2']/div"):
                driver.execute_script("document.documentElement.scrollTop=750")
            driver.execute_script("document.documentElement.scrollLeft=300")
            comments = driver.execute_script('return document.getElementsByClassName("Barrage-listItem").length;')
            # 屏蔽特效
            # if k==1:
            #     if is_visible("//*[@id='js-player-asideMain']/div/div[2]/div/div[2]/div[1]/div/div[5]"):
            #         driver.find_element_by_xpath("//*[@id='js-player-asideMain']/div/div[2]/div/div[2]/div[1]/div/div[5]").click()
            #         # time.sleep(0.5)
            #     if is_visible("//*[@id='js-player-asideMain']/div[1]/div[2]/div/div[1]/div[10]/div/div[1]/span"):
            #         driver.find_element_by_xpath("//*[@id='js-player-asideMain']/div[1]/div[2]/div/div[1]/div[10]/div/div[1]/span").click()
            while True:
                if comments >90:
                    time.sleep(1)
                    for j in range(0,comments):
                        single_comment_data = driver.execute_script('return document.getElementsByClassName("Barrage-listItem")[{}].innerHTML;'.format(j))
                        soup2 = BeautifulSoup(single_comment_data,'lxml')
                        span = soup2.find_all("span")
                        if len(span)==3:
                            user_level = span[0].get("title")
                            print(str(user_level).strip().replace("用户", "用户{}".format(j)))
                            user_nickname = span[1].text
                            print(user_nickname.strip(),end='')
                            user_comment = span[2].text
                            print(user_comment.strip())
                            if user_level==None:
                                pass
                            else:
                                data = {
                                    'nickname':user_nickname.strip(),
                                    'level':str(user_level).strip(),
                                    'contents':user_comment.strip()
                                }
                                comments_data.append(data)
                        elif len(span)==4:
                            user_level = span[0].get("title")
                            print(str(user_level).strip().replace("用户", "用户{}".format(j)))
                            user_nickname = span[2].text
                            print(user_nickname.strip(),end='')
                            user_comment = span[3].text
                            print(user_comment.strip())
                            if user_level==None:
                                pass
                            else:
                                data = {
                                    'nickname': user_nickname.strip(),
                                    'level': str(user_level).strip(),
                                    'contents': user_comment.strip()
                                }
                                comments_data.append(data)
                        else:
                            pass
                    break
                else:
                    time.sleep(1)
                    comments = driver.execute_script('return document.getElementsByClassName("Barrage-listItem").length;')
                    print("爬取到的评论数："+str(comments))
            write_to_DB(pw,k,comments_data)
        k+=1
        if k>10:
            input('wait')



if __name__ == "__main__":
    # 爬取的主链接
    url = 'https://www.douyu.com/g_LOL'
    # 获取每个直播间的链接
    room_urls = get_room_urls(url)
    # 设置浏览器为不可见
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(chrome_options=chrome_options)
    pw = input("请输入密码以登录数据库：")
    # 创建数据库表
    create_table(pw)
    # 获取评论
    get_comment(pw,driver,room_urls)
