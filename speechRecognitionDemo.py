import websocket
import requests
import datetime
import hashlib
import base64
import hmac
import json
import os, sys
import re
from urllib.parse import urlencode
import logging
import time
import ssl
import wave
from wsgiref.handlers import format_date_time
from datetime import datetime
from time import mktime
from pyaudio import PyAudio,paInt16
from get_audio import get_audio # 导入录音.py文件
from get_weather import getWeather
from get_map import getMap

input_filename = "input.wav"               # 麦克风采集的语音输入
input_filepath = "./"              # 输入文件的path
in_path = input_filepath + input_filename

type = sys.getfilesystemencoding()

path_pwd = os.path.split(os.path.realpath(__file__))[0]
os.chdir(path_pwd)

try:
    import thread
except ImportError:
    import _thread as thread

logging.basicConfig()

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识

framerate = 8000
NUM_SAMPLES = 2000
channels = 1
sampwidth = 2
TIME = 2

global wsParam

text = ""

class Ws_Param(object):
    # 初始化
    def __init__(self, host):
        self.Host = host
        self.HttpProto = "HTTP/1.1"
        self.HttpMethod = "GET"
        self.RequestUri = "/v2/iat"
        self.APPID = "5fbe44ac" # 在控制台-我的应用-语音听写（流式版）获取APPID
        self.Algorithm = "hmac-sha256"
        self.url = "wss://" + self.Host + self.RequestUri

        # 采集音频 录音
        get_audio("./input.wav")

        # 设置测试音频文件，流式听写一次最多支持60s，超过60s会引起超时等错误。
        self.AudioFile = r"./input.wav"

        self.CommonArgs = {"app_id": self.APPID}
        self.BusinessArgs = {"domain":"iat", "language": "zh_cn","accent":"mandarin"}

    # https://console.xfyun.cn/services/iat
    def create_url(self):
        url = 'wss://iat-api.xfyun.cn/v2/iat'
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))
        APIKey = '' # 在控制台-我的应用-语音听写（流式版）获取APIKey
        APISecret = '' # 在控制台-我的应用-语音听写（流式版）获取APISecret

        signature_origin = "host: " + "iat-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/iat " + "HTTP/1.1"
        signature_sha = hmac.new(APISecret.encode('utf-8'), signature_origin.encode('utf-8'),
                                 digestmod=hashlib.sha256).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        v = {
            "authorization": authorization,
            "date": date,
            "host": "iat-api.xfyun.cn"
        }
        url = url + '?' + urlencode(v)
        return url

# 收到websocket消息的处理
def on_message(ws, message):
    msg = json.loads(message) # 将json对象转换为python对象 json格式转换为字典格式
    try:
        code = msg["code"]
        sid = msg["sid"]

        if code != 0:
            errMsg = msg["message"]
            print("sid:%s call error:%s code is:%s\n" % (sid, errMsg, code))
        else:
            result = msg["data"]["result"]["ws"]
            '''
            data_result = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=4, separators=(',', ': ')) 
            print("sid:%s call success!" % (sid))
            '''
            global text
            for i in result:
                for w in i["cw"]:
                    text += w["w"]
            '''
            print("result is:%s\n" % (data_result))
            '''
    except Exception as e:
        print("receive msg,but parse exception:", e)

# 收到websocket错误的处理
def on_error(ws, error):
    print("### error:", error)

# 收到websocket关闭的处理
def on_close(ws):
    print("### closed ###")

# 收到websocket连接建立的处理
def on_open(ws):
    def run(*args):
        frameSize = 1280  # 每一帧的音频大小
        intervel = 0.04  # 发送音频间隔(单位:s)
        status = STATUS_FIRST_FRAME  # 音频的状态信息，标识音频是第一帧，还是中间帧、最后一帧
        with open(wsParam.AudioFile, "rb") as fp:
            while True:
                buf = fp.read(frameSize)

                # 文件结束
                if not buf:
                    status = STATUS_LAST_FRAME
                # 第一帧处理
                # 发送第一帧音频，带business 参数
                # appid 必须带上，只需第一帧发送
                if status == STATUS_FIRST_FRAME:

                    d = {"common": wsParam.CommonArgs,
                         "business": wsParam.BusinessArgs,
                         "data": {"status": 0, "format": "audio/L16;rate=16000",
                                   "audio": str(base64.b64encode(buf),'utf-8'),
                                  "encoding": "raw"}}
                    d = json.dumps(d)
                    ws.send(d)
                    status = STATUS_CONTINUE_FRAME
                # 中间帧处理
                elif status == STATUS_CONTINUE_FRAME:
                    d = {"data": {"status": 1, "format": "audio/L16;rate=16000",
                                   "audio": str(base64.b64encode(buf),'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                # 最后一帧处理
                elif status == STATUS_LAST_FRAME:
                    d = {"data": {"status": 2, "format": "audio/L16;rate=16000",
                                  "audio": str(base64.b64encode(buf),'utf-8'),
                                  "encoding": "raw"}}
                    ws.send(json.dumps(d))
                    time.sleep(1)
                    break
                # 模拟音频采样间隔
                time.sleep(intervel)
        ws.close()

    thread.start_new_thread(run, ())

# 提取关键字
def check(text):
    dataEvent = ["天气", "地图"]
    dataCity = ['北京', '上海', '广州', '深圳', '成都', '重庆', '杭州', '武汉', '西安', '天津','苏州','南京' ,
    '郑州','长沙','东莞','沈阳','青岛','合肥','佛山' ,'无锡','佛山','合肥','大连','福州','厦门','哈尔滨' ,
    '济南' ,'温州','南宁','长春','泉州' ,'石家庄','贵阳','南昌' ,'金华' ,'常州' ,'南通','嘉兴' ,'太原' ,'徐州' ,
    '惠州' ,'珠海' ,'中山' ,'台州' ,'烟台' ,'兰州' ,'绍兴' ,'海口' ,'扬州' ,'汕头','揭阳' ,'江门' ,'湛江' ,'潮州' ,
    '肇庆' ,'清远' ,'梅州' ,'湖州' ,'舟山' ,'丽水' ,'盐城' ,'泰州' ,'淮安' ,'连云港' ,'宿迁' ,'潍坊' ,'临沂' ,
    '济宁' ,'淄博' ,'威海' ,'泰安' ,'保定' ,'唐山' ,'廊坊' ,'邯郸' ,'沧州','秦皇岛' ,'洛阳' ,'商丘','南阳' ,
    '新乡' ,'乌鲁木齐' ,'漳州' ,'莆田' ,'宁德' ,'龙岩' ,'三明' ,'南平' ,'九江' ,'赣州' ,'上饶' ,'呼和浩特' ,
    '包头' ,'芜湖' ,'蚌埠' ,'阜阳' ,'马鞍山' ,'滁州' ,'安庆' ,'桂林' ,'柳州' ,'银川' ,'三亚' ,'遵义' ,'绵阳' ,
    '南充' ,'宜昌' ,'襄阳' ,'荆州' ,'黄冈' ,'咸阳' ,'衡阳' ,'株洲' ,'岳阳' ,'郴州' ,'大庆' ,'鞍山' ,'吉林' ,
    '韶关' ,'常德' ,'六安' ,'汕尾' ,'西宁' ,'茂名' ,'驻马店' ,'邢台' ,'宜春' ,'大理' ,'丽江' ,'延边朝鲜族自治州' ,
    '衢州' ,'黔东南苗族侗族自治州' ,'景德镇' ,'开封' ,'红河哈尼族彝族自治州' ,'北海' ,'黄冈' ,'东营' ,'怀化' ,'阳江' ,
    '菏泽' ,'黔南布依族苗族自治州' ,'宿州' ,'日照' ,'黄石' ,'周口' ,'晋中' ,'许昌' ,'拉萨' ,'锦州' ,'佳木斯' ,'淮南' ,
    '抚州' ,'营口' ,'曲靖' ,'齐齐哈尔' ,'牡丹江' ,'河源' ,'德阳' ,'邵阳' ,'孝感' ,'焦作' ,'益阳' ,'张家口' ,'运城' ,
    '大同' ,'德州' ,'玉林' ,'榆林' ,'平顶山' ,'盘锦' ,'渭南' ,'安阳' ,'铜仁' ,'宣城' ,'永州' ,'黄山' ,'西双版纳傣族自治州' ,
    '十堰' ,'宜宾' ,'丹东' ,'乐山' ,'吉安' ,'宝鸡' ,'鄂尔多斯' ,'铜陵' ,'娄底' ,'六盘水' ,'承德','保山' ,'毕节' ,
    '泸州' ,'恩施土家族苗族自治州' ,'安顺' ,'枣庄' ,'聊城' ,'百色' ,'临汾' ,'梧州' ,'亳州' ,'德宏傣族景颇族自治州' ,
    '鹰潭' ,'滨州' ,'绥化' ,'眉山' ,'赤峰' ,'咸宁' ,'防城港' ,'玉溪' ,'呼伦贝尔' ,'普洱' ,'葫芦岛' ,'楚雄彝族自治州' ,
    '衡水' ,'抚顺' ,'钦州' ,'四平' ,'汉中' ,'黔西南布依族苗族自治州' ,'内江' ,'湘西土家族苗族自治州' ,'漯河' ,'新余' ,
    '延安' ,'长治' ,'文山壮族苗族自治州' ,'云浮' ,'贵港' ,'昭通' ,'河池' ,'达州' ,'宣城' ,'濮阳' ,'通化' ,'松原' ,
    '通辽' ,'广元' ,'鄂州' ,'凉山彝族自治州' ,'张家界' ,'荆门' ,'来宾' ,'忻州' ,'克拉玛依' ,'遂宁' ,'朝阳' ,'崇左' ,
    '辽阳' ,'广安' ,'萍乡' ,'阜新' ,'吕梁' ,'池州' ,'贺州' ,'本溪' ,'铁岭' ,'自贡' ,'锡林郭勒盟' ,'白城' ,'白山' ,
    '雅安' ,'酒泉' ,'天水' ,'晋城' ,'巴彦淖尔' ,'随州' ,'兴安盟' ,'临沧' ,'鸡西' ,'迪庆藏族自治州' ,'攀枝花' ,
    '鹤壁' ,'黑河' ,'双鸭山' ,'三门峡' ,'安康' ,'乌兰察布' ,'庆阳' ,'伊犁哈萨克自治州' ,'儋州' ,'哈密' ,'海西蒙古族藏族自治州' ,
    '甘孜藏族自治州' ,'伊春' ,'陇南' ,'乌海' ,'林芝' ,'怒江傈僳族自治州' ,'朔州' ,'阳泉' ,'嘉峪关' ,'鹤岗' ,'张掖' ,
    '辽源' ,'吴忠' ,'昌吉回族自治州' ,'大兴安岭地区' ,'巴音郭楞蒙古自治州' ,'阿坝藏族羌族自治州' ,'日喀则' ,'阿拉善盟' ,
    '巴中' ,'平凉' ,'阿克苏地区' ,'定西' ,'商洛' ,'金昌' ,'七台河' ,'石嘴山' ,'白银' ,'铜川' ,'武威' ,'吐鲁番' ,'固原' ,
    '山南' ,'临夏回族自治州' ,'海东','喀什地区','甘南藏族自治州','昌都','中卫','资阳','阿勒泰地区','塔城地区',
    '博尔塔拉蒙古自治州','海南藏族自治州','克孜勒苏柯尔克孜自治州','阿里地区','和田地区','玉树藏族自治州',
    '那曲','黄南藏族自治州','海北藏族自治州','果洛藏族自治州','三沙']

    city = ''
    event = 0
    for i in range(len(dataCity)):
        if dataCity[i] in text:
            city = dataCity[i]
            break
    for i in range(len(dataEvent)):
        if dataEvent[i] in text:
            event = i + 1
            break
    return event, city
    

if __name__ == "__main__":  
    deadCircle = 1
    while deadCircle == 1:
        text = ""
        aa = input("是否开始录音?   （y/n）")
        if aa == "y" :
            wsParam = Ws_Param("iat-api.xfyun.cnn") #流式听写 域名
            websocket.enableTrace(False)
            wsUrl = wsParam.create_url()
            ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            print("\n识别文本："+text+"\n\n")
            event, city = check(text)
            if event == 1:
                getWeather(city)
            if event == 2:
                getMap(city)
        elif aa == "n":
            print("结束！\n")
            break
        else:
            print("语音录入失败，请重新开始\n")