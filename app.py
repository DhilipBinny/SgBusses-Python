from flask import Flask, request, jsonify
import requests
import pandas as pd
from scipy import spatial
import json
from flask_cors import CORS
# import cv2
import numpy as np
from datetime import datetime 
import os

headers = {'AccountKey': os.getenv("AccountKey"),  #QpVNIQH4RNC01YkvDIrG8Q==
           'accept': 'application/json'}

dfs = []
for i in range(0, 5500, 500):
    print(i)
    url = "http://datamall2.mytransport.sg/ltaodataservice/BusStops"
    url_ = (url+f'?$skip={i}')
    resp = requests.get(url_, headers=headers)
    df = pd.DataFrame(resp.json()['value'])
    dfs.append(df)
df_full = pd.concat(dfs)

type_of_loads = {
    "SEA": "Seats Available",
    "SDA": "Standing Available",
    "LSD":"Limited Standing"
    }
    
app = Flask(__name__)
CORS(app)

@app.route("/")
def hello():
    return "Hello World!"

@app.route("/processimage", methods=["POST"])
def processimage():
    # if request.get_data():
        # image = np.asarray(bytearray(request.get_data()), dtype="uint8")
        # image = cv2.imdecode(image, cv2.IMREAD_COLOR)
        # cv2.imshow("window 1", image) 
        # cv2.waitKey(0)
    response = jsonify({"result":"ok","busstopcode": 18121})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route("/bstops")
def getbusstops_call():
    lon = request.args.get('lon', 103.7891453 )
    lat = request.args.get('lat', 1.2982791999999999)
    top_busstops = getbusstops(float(lon), float(lat))
    response = jsonify(top_busstops)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route("/buses")
def getbuses_call():
    bstopcode = request.args.get('bstpcode', 17159 )
    bus_list = getBusses(bstopcode)
    response = jsonify(bus_list)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route("/timing")
def gettiming_call():
    bs_code = request.args.get('bstpcode', 17159 )
    b_code = request.args.get('bscode', 166)
    listtemp = get_timing(bs_code, b_code)
    response = jsonify(listtemp)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

def getbusstops(lon, lat):
    df_full_ = df_full
    pt = [lat, lon]
    A_ = df_full_[["BusStopCode", "Description"]].values
    A = df_full_[['Latitude', 'Longitude']].values
    kdtree = spatial.KDTree(A)
    distance, index = kdtree.query(pt, 20)
    top_busstops = A_[index].tolist()
    return top_busstops

def getresult(bus_stop):
    path = f'http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2?BusStopCode={bus_stop}'
    resp = requests.get(path, headers=headers)
    if resp.ok and len(resp.json().get("Services")) > 0:
        print("valid bus stop code ...")
        return True, resp.json()
    else:
        print("No bus available / or invalid bus stop code")
        return False, ''

def getBusses(bus_stop):
    status, result = getresult(bus_stop)
    bus_list = []
    if status:
        if result["Services"]:
            for item in result["Services"]:
                bus_list.append(item["ServiceNo"])
    return bus_list

def get_timing(bs_code, b_code):
    url = f'http://datamall2.mytransport.sg/ltaodataservice/BusArrivalv2?BusStopCode={bs_code}&ServiceNo={b_code}'
    resp = requests.get(url, headers=headers)
    res = resp.json()
    item = res["Services"][0]
    listtemp = []
    for key, value in item.items():
        if isinstance(value, dict):
            _item = item[key]
            if _item.get("EstimatedArrival", False):
                _x = {} 
                _x["EstimatedArrival"] = message_based_on_time_difference(_item["EstimatedArrival"])
                _x["Load"] = type_of_loads.get(_item["Load"],"")
                _x["type_img"], _x["Type"] = func_2(_item["Type"])
                listtemp.append( _x )
    return listtemp

def func_2(load):
    if load == "SD":
        return "https://d1nhio0ox7pgb.cloudfront.net/_img/v_collection_png/512x512/shadow/bus.png", "Single Deck"
    elif load == "DD":
        return "https://i2.wp.com/www.associationoftartanarmyclubs.com/wp-content/uploads/2016/08/tour-bus-images-7bb97906free-vector.png?fit=600%2C380&w=640", "Double Deck"
    elif load == "BD":
        return "https://static.turbosquid.com/Preview/001201/728/2R/citaro-g-euro-vi-model_0.jpg", "Bendy"


def message_based_on_time_difference(time):
    time_utc = datetime.fromisoformat(time)
    minutes , seconds = divmod((time_utc - datetime.now(time_utc.tzinfo)).total_seconds(), 60)
    print(minutes,",", seconds)
    if minutes <= 1:
        return ("Arriving Now")
    else:
        return (f"{int(minutes)} min")

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0',port=os.getenv("PORT"))
