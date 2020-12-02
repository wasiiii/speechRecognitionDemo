import requests
def getWeather(text):
    url = 'http://www.tianqiapi.com/api?version=v6&appid=41872873&appsecret=a6VMqtFS&city='+text
    rep = requests.get(url)
    rep.encoding = 'utf-8'
    print('城市：%s'%rep.json()['city'])
    print('天气：%s'%rep.json()['wea'])
    print('风向：%s'%rep.json()['win'])
    print('温度：%s'%rep.json()['tem']+'°C')
    print('风力：%s'%rep.json()['win_speed'])
    print('湿度：%s'%rep.json()['humidity'])
    print('空气质量：%s'%rep.json()['air_level'])
    print('\n')