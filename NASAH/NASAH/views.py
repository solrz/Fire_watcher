from django.http import JsonResponse
import requests
from math import *

sess = requests.Session()

resp = sess.get("https://forecast.forest.gov.tw/Forecast/Fire/GetMyMap?target=%E9%81%BF%E9%9B%A3%E6%89%80&_=1540046479798")
cont = resp.json()
users = dict()

class LatLonToTWD97(object):
    """This object provide method for converting lat/lon coordinate to TWD97
    coordinate

    the formula reference to
    http://www.uwgb.edu/dutchs/UsefulData/UTMFormulas.htm (there is lots of typo)
    http://www.offshorediver.com/software/utm/Converting UTM to Latitude and Longitude.doc

    Parameters reference to
    http://rskl.geog.ntu.edu.tw/team/gis/doc/ArcGIS/WGS84%20and%20TM2.htm
    http://blog.minstrel.idv.tw/2004/06/taiwan-datum-parameter.html
    """

    def __init__(self,
        a = 6378137.0,
        b = 6356752.314245,
        long0 = radians(121),
        k0 = 0.9999,
        dx = 250000,
    ):
        # Equatorial radius
        self.a = a
        # Polar radius
        self.b = b
        # central meridian of zone
        self.long0 = long0
        # scale along long0
        self.k0 = k0
        # delta x in meter
        self.dx = dx

    def convert(self, lat, lon):
        """Convert lat lon to twd97

        """
        a = self.a
        b = self.b
        long0 = self.long0
        k0 = self.k0
        dx = self.dx

        e = (1-b**2/a**2)**0.5
        e2 = e**2/(1-e**2)
        n = (a-b)/(a+b)
        nu = a/(1-(e**2)*(sin(lat)**2))**0.5
        p = lon-long0

        A = a*(1 - n + (5/4.0)*(n**2 - n**3) + (81/64.0)*(n**4  - n**5))
        B = (3*a*n/2.0)*(1 - n + (7/8.0)*(n**2 - n**3) + (55/64.0)*(n**4 - n**5))
        C = (15*a*(n**2)/16.0)*(1 - n + (3/4.0)*(n**2 - n**3))
        D = (35*a*(n**3)/48.0)*(1 - n + (11/16.0)*(n**2 - n**3))
        E = (315*a*(n**4)/51.0)*(1 - n)

        S = A*lat - B*sin(2*lat) + C*sin(4*lat) - D*sin(6*lat) + E*sin(8*lat)

        K1 = S*k0
        K2 = k0*nu*sin(2*lat)/4.0
        K3 = (k0*nu*sin(lat)*(cos(lat)**3)/24.0) * (5 - tan(lat)**2 + 9*e2*(cos(lat)**2) + 4*(e2**2)*(cos(lat)**4))

        y = K1 + K2*(p**2) + K3*(p**4)

        K4 = k0*nu*cos(lat)
        K5 = (k0*nu*(cos(lat)**3)/6.0) * (1 - tan(lat)**2 + e2*(cos(lat)**2))
        
        x = K4*p + K5*(p**3) + dx
        return x, y

lonlat_to_twd97 = LatLonToTWD97()

def twd97_to_latlon(x,y):    
    a = 6378137.0
    b = 6356752.314245
    lng0 = 121 * pi / 180
    k0 = 0.9999
    dx = 250000

    dy = 0
    e = pow((1 - pow(b, 2) / pow(a, 2)), 0.5)
    x -= dx
    y -= dy
    M = y / k0
    mu = M / (a * (1.0 - pow(e, 2) / 4.0 - 3 * pow(e, 4) / 64.0 - 5 * pow(e, 6) / 256.0))
    e1 = (1.0 - pow((1.0 - pow(e, 2)), 0.5)) / (1.0 + pow((1.0 - pow(e, 2)), 0.5))
    J1 = (3 * e1 / 2 - 27 * pow(e1, 3) / 32.0)
    J2 = (21 * pow(e1, 2) / 16 - 55 * pow(e1, 4) / 32.0)
    J3 = (151 * pow(e1, 3) / 96.0)
    J4 = (1097 * pow(e1, 4) / 512.0)
    fp = mu + J1 * sin(2 * mu) + J2 * sin(4 * mu) + J3 * sin(6 * mu) + J4 * sin(8 * mu)
    e2 = pow((e * a / b), 2)
    C1 = pow(e2 * cos(fp), 2)
    T1 = pow(tan(fp), 2)
    R1 = a * (1 - pow(e, 2)) / pow((1 - pow(e, 2) * pow(sin(fp), 2)), (3.0 / 2.0))
    N1 = a / pow((1 - pow(e, 2) * pow(sin(fp), 2)), 0.5)

    D = x / (N1 * k0)
    Q1 = N1 * tan(fp) / R1
    Q2 = (pow(D, 2) / 2.0)
    Q3 = (5 + 3 * T1 + 10 * C1 - 4 * pow(C1, 2) - 9 * e2) * pow(D, 4) / 24.0
    Q4 = (61 + 90 * T1 + 298 * C1 + 45 * pow(T1, 2) - 3 * pow(C1, 2) - 252 * e2) * pow(D, 6) / 720.0
    lat = fp - Q1 * (Q2 - Q3 + Q4)
    Q5 = D
    Q6 = (1 + 2 * T1 + C1) * pow(D, 3) / 6
    Q7 = (5 - 2 * C1 + 28 * T1 - 3 * pow(C1, 2) + 8 * e2 + 24 * pow(T1, 2)) * pow(D, 5) / 120.0
    lng = lng0 + (Q5 - Q6 + Q7) / cos(fp)
    lat = (lat * 180) / pi
    lng = (lng * 180) / pi

    return lat,lng

def get_danger():
    inquire_date = [2018,10,20]

    resp = sess.get("https://forecast.forest.gov.tw/Forecast/UploadFiles/Forest/ForestDanger/Data-{}{:02d}{:02d}.txt".format(*inquire_date))
    # print(resp.text)
    cont = resp.text.replace('\r','')
    lines = cont.split('\n')

    left_border  = 0
    right_border = 150
    pixels = []
    for l in lines:
        last_endpoint = left_border
        pixels.append([])
        for section in l.split(';'):
            if len(section) == 0:
                continue
            # print(section)
            start_from = int(section.split(':')[0])
            data_set = section.split(':')[1].split(',')
            # print(start_from,last_endpoint)
            # print(data_set)
            if last_endpoint < start_from:
                pixels[-1].extend(['*']* (start_from-last_endpoint))
            pixels[-1].extend( list(map(lambda x: int(sqrt(x)),list(map(int, data_set)))) )

            last_endpoint = start_from + len(data_set)
        if len(pixels[-1]) > last_endpoint:
            pixels[-1].extend(['*'] * (right_border-last_endpoint))
        else:
            pixels[-1] = pixels[-1][:right_border]

    '''
    for lp in pixels:
        list(map(lambda x:print(x,end=' '),lp))
        print('')
    '''
    return pixels

def inquire_danger(pixels,lon,lat):
    x,y = lonlat_to_twd97.convert(float(lat),float(lon))
    convX,convY = int((x - 149958 + 1000) / 1000), int((2767245 - y + 1500) / 1000)
    try:
        danger = pixels[convY][convX]
    except:
        danger = '*'
    return danger
        

def save_location(request):
    #try:
        id = request.GET['id']
        lon =  request.GET['lon']
        lat =  request.GET['lat']
        users[ id ] = {
            'longitude' : lon,
            'latitude'  : lat
        }
        print('\n[!]New User: {}@( {}, {} )\n'.format(id,lon,lat))
        pixels = get_danger()
        return JsonResponse({'status':'success','danger':inquire_danger(pixels,lon,lat)})
    #except:
        return JsonResponse({'status':'failed'})
    
def get_shelters(request):
    sess = requests.Session()
    resp = sess.get("https://forecast.forest.gov.tw/Forecast/Fire/GetMyMap?target=%E9%81%BF%E9%9B%A3%E6%89%80&_=1540046479798")
    cont = resp.json()
    
    least_dist = 99999999999
    nearest_shelter = None
    
    id = request.GET['id']
    user_location = (users[id]['longitude'],users[id]['latitude'])
    pixels = get_danger()
    print(len(pixels),len(pixels[0]))
    
    for shelter in cont:
        # convert x,y into lon,lan
        shelter['lat'],shelter['lon'] = twd97_to_latlon(shelter['x'],shelter['y'])
        x,y = shelter['x'],shelter['y']
        convX,convY = int((x - 149958 + 1000) / 1000), int((2767245 - y + 1500) / 1000)
        shelter['cx'],shelter['cy'] = convX,convY
        
        try:
            shelter['danger'] = pixels[convY][convX]
        except:
            shelter['danger'] = '*'
        
        # find nearest shelter
        shelter['dist'] = sqrt((float(user_location[0])-float(shelter['lon'])) ** 2 + (float(user_location[1])-float(shelter['lat'])) ** 2)
        
        if least_dist > shelter['dist']:
            least_dist = shelter['dist']
            nearest_shelter = shelter
            
    return JsonResponse(nearest_shelter)

