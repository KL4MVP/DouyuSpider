import requests
from bs4 import BeautifulSoup
import pickle
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import pymysql
from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
import selenium.webdriver.support.ui as ui
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

# 判断元素是否可见
def is_visible(locator, timeout=5):
    try:
        ui.WebDriverWait(driver,timeout,1).until(EC.visibility_of_element_located((By.XPATH, locator)))
        return True
    except TimeoutException:
        return False

# 获取cookie以登录
def getCookies():
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"')
    # chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
    driver = webdriver.Chrome(chrome_options=chrome_options)
    url = 'https://www.douyu.com/g_LOL'
    driver.get(url)
    time.sleep(3)
    driver.find_element_by_xpath("//*[@id='js-header']/div/div/div[3]/div[7]/div/div/a/span").click()
    time.sleep(1)
    driver.switch_to.frame("login-passport-frame")
    driver.find_element_by_xpath("//*[@id='loginbox']/div[2]/div[2]/div[3]/div/span[2]").click()
    driver.find_element_by_xpath("//*[@id='loginbox']/div[3]/div[2]/div[2]/div[2]/a[1]").click()
    time.sleep(5)
    handles = driver.window_handles
    for handle in handles:
        if handle!=driver.current_window_handle:
            driver.switch_to.window(handle)
            break
    time.sleep(5)
    driver.switch_to.frame('ptlogin_iframe')
    driver.find_element_by_xpath('//*[@id="img_out_1144268670"]').click()
    time.sleep(2)
    cookies1 = driver.get_cookies()
    print(cookies1)
    pickle.dump(cookies1,open("cookies.pkl","wb"))
    print('Cookie已存入文件中')
    driver.close()

# 将cookies添加到driver中
def addCookies(driver):
    cookies = pickle.load(open("cookies.pkl", "rb"))
    for cookie in cookies:
        cookie_dict = {
            "domain": ".douyu.com",  # 火狐浏览器不用填写，谷歌要需要
            'name': cookie.get('name'),
            'value': cookie.get('value'),
            "expires": "",
            'path': '/',
            'httpOnly': False,
            'HostOnly': False,
            'Secure': False}
        driver.add_cookie(cookie_dict)
    time.sleep(1)

# 获取所有直播间链接
def get_room_urls(room_urls):
    url = 'https://www.douyu.com/g_LOL'
    wb_data = requests.get(url).text
    soup = BeautifulSoup(wb_data, 'lxml')
    room_nums = soup.find_all("a", class_="DyListCover-wrap")
    # print(host_url)
    # room_urls = []
    for room_num in room_nums:
        room_url = "https://www.douyu.com" + room_num.get('href')
        room_urls.append(room_url)
    print("获取直播间链接成功!")

# 创建数据库表
def create_table(pw):
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    sql1 = '''
        create table vip(
        number int(3),
        vip_number int(3),
        nickname varchar(50),
        sex varchar(10),
        vip_level varchar(20),
        icon_link varchar(255),
        vip_type varchar(10),
        summary varchar(255),
        focus varchar(10),
        fans varchar(10)
        )
        '''
    cursor.execute(sql1)
    db.close()
    print("创建数据库表vip成功!")

# 将贵族用户的昵称，类别写入数据库
def write_to_DB1(pw,r,datas1):
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    j = 1
    for data in datas1:
        nickname = data['vip_name']
        vip_type = data['vip_type']
        sql_insert = '''insert into vip(number,vip_number,nickname,vip_type)
                values('%d','%d','%s','%s')
                ''' % (r, j, nickname, vip_type)
        cursor.execute(sql_insert)
        db.commit()
        j += 1
    db.close()
    print("贵族用户的昵称，类别导入数据库成功!")

 # 将贵族用户的等级，头像，网页链接写入数据库
def write_to_DB2(pw,r,datas2):
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    j = 1
    for data in datas2:
        # print(data)
        vip_level = data['vip_level']
        icon_link = data['vip_icon']
        sql_update = '''UPDATE vip SET vip_level='%s',icon_link='%s' WHERE number='%d' and vip_number='%d';
                #     ''' % (vip_level, icon_link, r, j)
        cursor.execute(sql_update)
        db.commit()
        j += 1
    db.close()
    print("贵族用户的等级，头像，网页链接导入数据库成功")

# 将贵族用户的性别，简介，关注用户数，粉丝数写入数据库
def write_to_DB3(pw,r,datas3):
    db = pymysql.connect('localhost', 'root', pw, 'douyu')
    cursor = db.cursor()
    c = 1
    for data in datas3:
        sex = data['sex']
        summary = data['brief']
        focus = data['follow']
        fans = data['fans']
        sql_update = '''UPDATE vip SET sex='%s',summary='%s',focus='%s',fans='%s' WHERE number='%d' and vip_number='%d';
                       #     ''' % (sex, summary, focus, fans, r, c)
        cursor.execute(sql_update)
        db.commit()
        c += 1
    db.close()
    print("贵族用户的性别，简介，关注用户数，粉丝数导入数据库成功")

# 获取vip数据并存储到数据库中
def get_vid_data(pw,driver,room_urls):
    r = 1
    for room_url in room_urls:
        driver.get(room_url)
        addCookies(driver)

        driver.refresh()
        datas1 = []
        datas2 = []
        datas3 = []
        time.sleep(0.5)
        # 如果有大图，下滑
        if is_visible("//*[@id='bc2']/div"):
            driver.execute_script("document.documentElement.scrollTop=700")
        if is_visible("//*[@id='js-background-holder']"):
            driver.execute_script("document.documentElement.scrollTop=700")
        js = "var q=document.documentElement.scrollLeft=" + str(500)  # 谷歌 和 火狐
        driver.execute_script(js)
        # 如果能看见贵族列表，点击
        if is_visible("//*[@id='js-player-asideMain']/div/div[1]/div[3]/div/div/div/div[1]/ul/li[2]/div"):
            driver.find_element_by_xpath('//*[@id="js-player-asideMain"]/div/div[1]/div[3]/div/div/div/div[1]/ul/li[2]/div').click()
        time.sleep(0.5)
        if r == 1:
            if is_visible("//*[@id='js-player-asideMain']/div[1]/div[2]/div/div[1]/div[9]/div/div[1]/span"):
                driver.find_element_by_xpath("//*[@id='js-player-asideMain']/div[1]/div[2]/div/div[1]/div[9]/div/div[1]/span").click()
        wb_data = driver.page_source
        soup = BeautifulSoup(wb_data,'lxml')
        vip_datas = soup.find_all('li',class_='NobleRankList-item')

        for vip_data in vip_datas:
            if len(vip_data.contents)==3:
                data = {
                    'vip_name':vip_data.contents[2].text,
                    'vip_type':vip_data.contents[0].get('alt')
                }
                print(data)
                datas1.append(data)
            elif len(vip_data.contents)==2:
                data = {
                    'vip_name': vip_data.contents[1].text,
                    'vip_type': vip_data.contents[0].get('alt')
                }
                print(data)
                datas1.append(data)
        print("直播间%d的贵族用户数为：" % (r) + str(len(datas1)))

        # 将贵族用户的昵称，类别写入数据库
        write_to_DB1(pw,r,datas1)


        for i in range(1,len(datas1)+1):
            try:
                vip_url = ''
                vip_icon = ''
                vip_level = ''
                print("正在爬取直播间%d第%d个贵族用户"%(r,i))
                element = driver.find_element_by_xpath("//*[@id='js-player-asideMain']/div/div[1]/div[3]/div/div/div/div[2]/div[2]/div/div[2]/div[1]/ul/li[{}]/span".format(i))
                element.click()
                if (i + 4) <= len(datas1):
                    target = driver.find_element_by_xpath(
                        "//*[@id='js-player-asideMain']/div/div[1]/div[3]/div/div/div/div[2]/div[2]/div/div[2]/div[1]/ul/li[{}]/span".format(
                            i + 4))
                time.sleep(1)
                # if is_visible("//*[@id='js-player-asideMain']/div/div[3]/div/div/div[1]/div"):
                #     time.sleep(0.5)
                vip = driver.execute_script('return document.getElementsByClassName("NobleCard")[0].innerHTML')
                soup = BeautifulSoup(vip,'lxml')
                vip_url = soup.find("a",class_="NobleCard-name").get('href')
                vip_icon = soup.find("img",class_="NobleCard-icon").get('src')
                vip_level = soup.find("span").get('title')
                data = {
                    'vip_level':vip_level,
                    'vip_icon':vip_icon.replace("//",''),
                    'vip_url':vip_url.replace("//",'https://')
                }
                datas2.append(data)
                driver.find_element_by_xpath(
                    "//*[@id='js-player-asideMain']/div/div[3]/div/div/div[1]/div/div[1]").click()
                time.sleep(0.5)
                # if i%2==0:
                ActionChains(driver).drag_and_drop(target, element).perform()
            except Exception:
                data = {
                    'vip_level': '',
                    'vip_icon': '',
                    'vip_url': ''
                }
                datas2.append(data)


        # 将贵族用户的等级，头像，网页链接写入数据库
        write_to_DB2(pw,r,datas2)



        for data in datas2:
            if data['vip_url']=='':
                continue
            else:
                url = data['vip_url']
            driver.get(url)
            # time.sleep(1)
            sex = ''
            brief=''
            follow=''
            fans=''
            try:
                if is_visible("//*[@id='fixedScroll']/div[1]/div[2]/div[2]"):
                    time.sleep(1)
                    wb_data = driver.page_source
                    soup = BeautifulSoup(wb_data,'lxml')
                    sex = soup.find("div",class_="index-sex-2uS5N").text
                    # print(sex)
                    brief = soup.find("p",class_="index-descContent-1Tw6P").text
                    follow = soup.find_all("span",class_="index-HeaderCount-hQ86V")[0].text
                    fans = soup.find_all("span",class_="index-HeaderCount-hQ86V")[1].text
                    dic = {
                        'sex':sex,
                        'brief':brief,
                        'follow':follow,
                        'fans':fans
                    }
                    datas3.append(dic)
            except Exception:
                dic ={
                    'sex' : '该用户已被屏蔽',
                    'brief' : '该用户已被屏蔽',
                    'follow' : '该用户已被屏蔽',
                    'fans' : '该用户已被屏蔽'
                }
                datas3.append(dic)
            print(sex,brief,follow,fans)
        print("爬取数据成功！")

        # 将贵族用户的性别，简介，关注用户数，粉丝数写入数据库
        write_to_DB3(pw,r,datas3)

        r+=1





if __name__=="__main__":
    # 获取Cookies来登录
    # getCookies()

    # 获取直播间链接
    room_urls = []
    get_room_urls(room_urls)

    pw = input("请输入密码以登录数据库：")
    # 创建数据库表
    create_table(pw)

    # 打开浏览器
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    driver = webdriver.Chrome(chrome_options=chrome_options)

    # 获取贵族用户信息并写进数据库
    get_vid_data(pw,driver,room_urls)






