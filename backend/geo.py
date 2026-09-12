from math import radians,sin,cos,asin,sqrt

CAMERAS=[
 ('C01','Barakhamba Road','Barakhamba Road · Connaught Place',28.6308,77.2241,'South-east','online'),
 ('C02','Mandi House','Sikandra Road · Mandi House',28.6259,77.2344,'East','online'),
 ('C03','ITO junction','Indraprastha Marg · ITO',28.6286,77.2414,'East','online'),
 ('C04','Akshardham approach','Noida Link Road · Akshardham',28.6177,77.2774,'North-east','online'),
 ('C05','India Gate','C-Hexagon · India Gate',28.6115,77.2346,'North','online'),
 ('C06','Pragati Maidan','Bhairon Marg · Pragati Maidan',28.6151,77.2499,'North-east','online'),
 ('C07','Rajiv Chowk','Outer Circle · Connaught Place',28.6355,77.2194,'East','online'),
 ('C08','Yamuna Bank','Vikas Marg · Yamuna Bank',28.6333,77.2663,'East','degraded'),
 ('C09','Laxmi Nagar','Vikas Marg · Laxmi Nagar',28.6365,77.2773,'East','online'),
 ('C10','Preet Vihar','Vikas Marg · Preet Vihar',28.6419,77.2953,'East','online'),
 ('C11','Tilak Bridge','Tilak Marg · Tilak Bridge',28.6235,77.2400,'North','online'),
 ('C12','Indraprastha','Ring Road · Indraprastha',28.6205,77.2548,'North','offline'),
]
CORRIDORS=[{'from':'C01','to':'C02','km':1.5,'baseline_seconds':240}, {'from':'C02','to':'C03','km':1.2,'baseline_seconds':180}, {'from':'C03','to':'C04','km':5.3,'baseline_seconds':480}, {'from':'C08','to':'C09','km':1.5,'baseline_seconds':180}, {'from':'C09','to':'C10','km':2.0,'baseline_seconds':240}]
def distance_km(a,b):
    lat1,lon1,lat2,lon2=map(radians,[a.lat,a.lon,b.lat,b.lon])
    return 6371*2*asin(sqrt(sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2))
