import plotly.express as px
import urllib.request,urllib.parse,urllib.error
import json
import requests
from urllib.request import urlopen,quote

# https://plotly.com/python/mapbox-county-choropleth/  plotly官方文档
def show(lat, lng):
    df = px.data.election()
    geojson = px.data.election_geojson()

    fig = px.choropleth_mapbox(df, geojson=geojson, color="Bergeron",
                            locations="district", featureidkey="properties.district",
                            center={"lat": lat, "lon": lng},
                            mapbox_style="open-street-map", zoom=8.5)
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    fig.show()

# http://lbsyun.baidu.com/apiconsole/key#/home   百度控制台拿ak
def getMap(text):
    address=text
    ak='i9rWgv2oeCpGyAi2z3DpxsFrzkR2SPXx'
    url='http://api.map.baidu.com/geocoding/v3/?address='
    output = 'json'
    add = quote(address)
    url2 = url+add+'&output='+output+"&ak="+ak
    req = urlopen(url2)
    res  = req.read().decode()

    temp = json.loads(res)
    lng = temp['result']['location']['lng']  # 获取经度
    lat = temp['result']['location']['lat']  # 获取纬度
    show(lat, lng)
    