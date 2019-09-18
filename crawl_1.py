import requests
from bs4 import BeautifulSoup
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import pymysql
from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
import selenium.webdriver.support.ui as ui
from selenium.common.exceptions import TimeoutException
import json


# 确认元素是否可见
def is_visible(locator, timeout=5):
    try:
        ui.WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.CLASS_NAME, locator)))
        return True
    except TimeoutException:
        return False

# 下载图片
def DownloadImage(str,url):
    path = '/Users/keliang/Downloads/LOL'
    isExist = os.path.exists(path)
    if not isExist:
        os.mkdir(path)
    else:
        print("文件夹已存在")
    # 爬取图片
    pic = requests.get(url)
    string = path + '/' + str
    fp = open(string, 'wb')
    fp.write(pic.content)
    fp.close()

# 下拉缓存截图并获取网页代码
def drag_down_to_get_HTML(driver,url):
    driver.get(url)
    time.sleep(5)
    print("正在抓取图片", end='')
    # 下拉使所有直播间截图可见
    i = 1
    while True:
        print(".", end='')
        js = "var q=document.documentElement.scrollTop=" + str(700 * i)  # 谷歌 和 火狐
        i = i + 1
        driver.execute_script(js)
        time.sleep(0.5)
        if (i > 12):
            print("图片抓取完成！")
            break
    return driver.page_source

# 获取图片链接
def get_pic_urls(data):
    soup1 = BeautifulSoup(data,'lxml')
    pic_urls = soup1.find_all("div",class_="LazyLoad is-visible DyImg DyListCover-pic")
    tails = []
    urls = []
    j = 1
    for pic_url in pic_urls:
        url = pic_url.contents[0].get('src')
        if url.find('.png') > 0:
            tails.append(".png")
            pic_url = url.replace('/webpdy1','')
        if url.find('.jpg') > 0:
            tails.append(".jpg")
            pic_url = url.replace('?x-oss-process=image/format,webp', '')
        urls.append(pic_url)
        j+=1
    return urls

# 将直播间标题，主播昵称，热度，直播间截图，直播间链接写入数据库
def write_to_DB1(pw,room_datas):
    # 写入数据库
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    sql1 = '''
        create table basic(
        number int(3) primary key,
        name varchar(50),
        title varchar(100),
        hot varchar(10),
        image_link varchar(255),
        room_num varchar(20),
        room_url varchar(255)
        )
        '''
    cursor.execute(sql1)
    print("创建数据库basic成功！")
    for room_data in room_datas:
        number = room_data['number']
        name = room_data['name']
        title = room_data['title']
        hot = room_data['hot']
        image_link = room_data['image_link']
        room_num = room_data['room_num']
        room_url = room_data['room_url']
        sql_insert = '''insert into basic(number,name,title,hot,image_link,room_num,room_url)
            values('%d','%s','%s','%s','%s','%s','%s')
            '''%(number,name,title,hot,image_link,room_num,room_url)
        cursor.execute(sql_insert)
        db.commit()
    db.close()
    print("直播间标题，主播昵称，热度，直播间截图，直播间链接导入数据库成功！")

#将主播的人数转化为整数型
def trans_string(str1):
    number = 0
    if str1.__contains__("万"):
        str2 = str1[-2::-1]
        number = float(str2[::-1]) * 10000
    else:
        number = int(str1)
    return number

#计算影响因子
def caculate_rate(hot, online):
    result = 0.0
    if online == 0:
        return result
    else:
        result = hot / online
    return result


# 将标签，房间号等数据整合到room_datas字典中并打印出来
def add_to_data(rooms,hots,hosts,room_nums,tags):
    room_urls = []
    room_datas = []
    # print(len(rooms),len(hots),len(pic_urls),len(hosts),len(room_nums),len(tags))
    k = 1
    for room,hot,pic_url,host,room_num,tag in zip(rooms,hots,pic_urls,hosts,room_nums,tags):
        data = {
            'number':k,
            'name':host.text,
            'title':room.text,
            'hot':hot.text,
            'tag':tag.contents[2].text,
            'image_link':pic_url,
            'room_num':room_num.get('href'),
            'room_url':"https://www.douyu.com"+room_num.get('href')
        }
        room_datas.append(data)
        web_url = data['room_url']
        room_urls.append(web_url)
        print(data)
        k += 1
    return room_datas,room_urls

# 爬取每个直播间的主播头像，主播等级，直播间最新排名，关注者人数
def crawl_single_room(driver,room_urls,room_datas):
    datas=[]
    q=1
    for url,room_data in zip(room_urls,room_datas):
        print("正在爬取直播间{}".format(q))
        # 直接从api获取在线人数和粉丝数
        single_url = "https://www.douyu.com/swf_api/h5room"+room_data['room_num']
        html = requests.get(single_url).text
        json_a = json.loads(html)
        result = 0
        try:
            online_number = str(json_a['data']['online'])
            followers = str(json_a['data']['fans'])
            hot = trans_string(room_data['hot'])
            result = caculate_rate(hot, float(online_number))
        except:
            print('爬取直播间人数失败')
            online_number = ''
            followers = ''
        driver.get(url)
        # 下拉屏幕，防止出现大图获取不到数据
        driver.execute_script("document.documentElement.scrollTop=450")
        if is_visible("//*[@id='js-player-title']/div/div[3]/div[3]/div[1]/div[1]",5):
            time.sleep(0.8)
        data = driver.page_source
        soup1 = BeautifulSoup(data, 'lxml')
        icon_url = soup1.find("div", class_="Title-anchorPicBack").contents[0].contents[1].get('src')
        level = soup1.find("a", class_="AnchorLevelTip-levelIcon").text
        host_url = soup1.find("a", class_="Title-anchorName").get('href').replace('//','https://')
        driver.get(host_url)
        # 爬取直播间排名
        time.sleep(2)
        try:
            host_data = driver.page_source
            soup2 = BeautifulSoup(host_data, 'lxml')
            rank = soup2.find("span", class_="titleBg-rankColorN-hCQPm").text
        except Exception:
            rank = ''
        data = {
            'icon_url':icon_url,
            'level':level,
            'rank':rank,
            'followers':followers,
            'online_number':online_number,
            'result':result
        }
        print(data)
        datas.append(data)
        q += 1
    driver.close()
    return datas

# 将每个直播间的主播头像，主播等级，直播间最新排名，关注者人数添加到数据库中
def write_to_DB2(pw,datas):
    # 写入数据库
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    sql1 = '''
        ALTER TABLE basic
        add icon_url varchar(255),
        add level varchar(20),
        add ranking varchar(20),
        add followers varchar(20),
        add online_number varchar(20),
        add influence FLOAT(10);
        '''
    cursor.execute(sql1)
    q = 1
    for data in datas:
        icon_url = data['icon_url']
        level = data['level']
        rank = data['rank']
        followers = data['followers']
        online_number = data['online_number']
        influence = data['result']
        sql_update = '''UPDATE basic SET icon_url='%s',level='%s',ranking='%s',followers='%s',online_number='%s',influence='%f' WHERE number='%d';
        '''%(icon_url,level,rank,followers,online_number,influence,q)
        cursor.execute(sql_update)
        db.commit()
        q+=1
    db.close()
    print("主播头像，主播等级，直播间最新排名，关注者人数导入数据库成功！")




if __name__ == "__main__":
    # 爬取的主页面
    url = 'https://www.douyu.com/g_LOL'
    # 设置浏览器不可见
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(chrome_options=chrome_options)
    data = drag_down_to_get_HTML(driver,url)

    # 获取截图
    pic_urls = get_pic_urls(data)
    # 解析网页
    soup = BeautifulSoup(data,'lxml')
    # 获取直播间
    rooms = soup.find_all("h3",class_="DyListCover-intro")
    # 获取直播间热度
    hots = soup.find_all("span",class_="DyListCover-hot")
    # 获取主播信息
    hosts = soup.find_all("h2",class_="DyListCover-user")
    # 获取房间号
    room_nums = soup.find_all("a",class_="DyListCover-wrap")
    # 获取主播标签
    tags = soup.find_all("div",class_="DyListCover-content")

    # 整合得到直播间相关信息和每个直播间的链接
    room_datas,room_urls = add_to_data(rooms,hots,hosts,room_nums,tags)

    pw = input("请输入密码以登录数据库：")
    # 将一部分信息写入数据库
    write_to_DB1(pw,room_datas)


    # 爬取每个直播间的主播头像，主播等级，直播间最新排名，关注者人数
    datas = crawl_single_room(driver,room_urls,room_datas)

    # 将每个直播间的主播头像，主播等级，直播间最新排名，关注者人数等信息写入数据库
    write_to_DB2(pw,datas)




