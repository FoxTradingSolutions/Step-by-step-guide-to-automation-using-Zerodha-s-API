# importing necessary modules
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import datetime
from kiteconnect import KiteTicker
from kiteconnect import KiteConnect
import pandas as pd
import time
from furl import furl

# zerodha credentials
api_key = '4krp3g3rsr3uobbu'
api_secret = '5khd9l21rccwz0ejwamaf3xikqxoa3vz'
username = 'NQ9241'
password = 'jeyaraj345'
pin = '938092'

# fuction to wait for elements on page load for selenium
def getCssElement( driver , cssSelector ):
    return WebDriverWait( driver, 100 ).until( EC.presence_of_element_located( ( By.CSS_SELECTOR, cssSelector ) ) )

#function to login to zerodha using selenium
def autologin():
    kite = KiteConnect(api_key=api_key)
    service = webdriver.chrome.service.Service('./chromedriver')
    service.start()
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options = options.to_capabilities()
    driver = webdriver.Remote(service.service_url, options)
    driver.get(kite.login_url())
    
    passwordField = getCssElement( driver , "input[placeholder=Password]" )
    passwordField.send_keys( password )
    
    userNameField = getCssElement( driver , "input[placeholder='User ID']" )
    userNameField.send_keys( username )
    
    loginButton = getCssElement( driver , "button[type=submit]" )
    loginButton.click()
    
    WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.CLASS_NAME, 'twofa-value')))
    pinField = driver.find_element_by_class_name('twofa-value').find_element_by_xpath(".//input[1]")
    pinField.send_keys( pin )
    
    loginButton = getCssElement( driver , "button[type=submit]" )
    loginButton.click()
    
    while True:
        try:
            request_token=furl(driver.current_url).args['request_token'].strip()
            break
        except:
            time.sleep(1)
    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token, api_secret=api_secret)
    with open('access_token.txt', 'w') as file:
        file.write(data["access_token"])
    driver.quit()

autologin()

# retriving access token from saved file
access_token_zerodha = open("access_token.txt",'r').read()

# Tokens to subscribe
# (RELIANCE and ACC here)
TOKENS = [738561, 5633]

# #creating kite connect object
kite = KiteConnect(api_key=api_key)
# # setting access token ti kite connect object
kite.set_access_token(access_token_zerodha)

# time at which code starts
STARTTIME = datetime.datetime.now()
#time at which code ends
ENDTIME = STARTTIME + datetime.timedelta(seconds=10)#datetime.datetime.now().replace(hour=14,minute=7,second=0)
print(ENDTIME)
# database to store last traded price
DATABASE = {token:{'timestamp':[],'ltp':[]} for token in TOKENS}

#waits till start time
while datetime.datetime.now()<STARTTIME:
    pass

#kite ticker object to recieve data from zerodha
kws = KiteTicker(api_key, access_token_zerodha)

#function to run when data is coming from zerodha
def on_ticks(ws, ticks):
    global DATABASE
    # recored timestamp and ltp valaue for each tick
    for x in ticks:
        DATABASE[x['instrument_token']]['timestamp'].append(datetime.datetime.now())
        DATABASE[x['instrument_token']]['ltp'].append(x['last_price'])
    #if current time is grater than ENDTIME the stop the code
    if(datetime.datetime.now()>ENDTIME):
        for x in TOKENS:
        	# create empty dataframe
            data = pd.DataFrame(columns=['timestamp','ltp'])
            # populate the datframe
            data['timestamp'] = DATABASE[x]['timestamp']
            data['ltp'] = DATABASE[x]['ltp']
            data = data.set_index('timestamp')
            # save dataframe, ex : "5633_2020-07-23.csv"
            data.to_csv(f"{x}_{str(datetime.datetime.now().date())}.csv")
        ws.stop()

#function to run when connection is established to zerodha
def on_connect(ws, response):
    # Callback on successful connect.
    ws.subscribe(TOKENS)

#funcion to run on connection close
def on_close(ws, code, reason):
    # On connection close try to reconnect
    pass

# Assign the callbacks.
kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close

# Infinite loop on the main thread. Nothing after this will run.
# You have to use the pre-defined callbacks to manage subscriptions.
kws.connect()
