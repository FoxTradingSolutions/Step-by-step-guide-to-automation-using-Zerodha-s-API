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

# class for single instrument data
class pocket:
    def __init__(self,instrumentToken):
        self.instrumentToken    = instrumentToken
        self.ltp                = []
        self.open               = []
        self.high               = []
        self.low                = []
        self.close              = []
        self.timeStamp          = []
        self.newData            = 0
    
    # Function to convert ltp data to ohlc
    def ohlc(self):
        if(self.ltp):
            self.timeStamp.append(datetime.datetime.now())
            self.open.append(self.ltp[0])
            self.high.append(max(self.ltp))
            self.low.append(min(self.ltp))
            self.close.append(self.ltp[-1])
            self.ltp = []
    
    # Function to set ltp value
    def setLtp(self,ltp):
        self.ltp.append(ltp)
    
    # Function to get candles dataframe
    def getOhlc(self):
        data = pd.DataFrame(
            data={
                'timeStamp' : self.timeStamp,
                'Open'      : self.open,
                'High'      : self.high,
                'Low'       : self.low,
                'Close'     : self.close,
            },
            columns=['timeStamp','Open','High','Low','Close']
        )
        data = data.set_index('timeStamp')
        return data

# class to store all pocket data
class database:
    def __init__(self,tokens,startTime,delay):
        self.pockets    = {}
        self.startTime  = startTime
        self.delay      = delay
        self.execution  = startTime + delay
        for token in tokens:
            self.pockets[token] = pocket(token)
    
    # Function to get pocket object by token number
    def getPocket(self,token):
        return self.pockets[token]
    
    # Setting ltp value based on token
    def setVal(self,token,ltp):
        self.getPocket(token).setLtp(ltp)
    
    # Function to check of candle time is executed
    def checkCandle(self):
        if(datetime.datetime.now()>self.execution):
            self.execution += self.delay
            for token in self.pockets:
                self.pockets[token].ohlc()
                # Set the new candle to be available
                self.pockets[token].newData = 1
    
    # Function to get candles dataframe of token
    def getOhlc(self,token):
        return self.getPocket(token).getOhlc()
    
    # Function to print dataframe of token pocket
    # if new candle is formed
    def newCandle(self,token):
        if(self.getPocket(token).newData):
            self.getPocket(token).newData = 0
            print('\n',token)
            print(self.getOhlc(token))


# zerodha credentials
api_key = "your api_key"
api_secret = "your api_secret"
username = "your username"
password = "your password"
pin = "your pin"

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
ENDTIME = datetime.datetime.now().replace(hour=15,minute=30,second=0)
#duration of a candle
DELAY = datetime.timedelta(hours=0,minutes=1,seconds=0)

# Initiating Database
DATABASE = database(TOKENS,STARTTIME,DELAY)

#waits till start time
while datetime.datetime.now()<STARTTIME:
    pass

#kite ticker object to recieve data from zerodha
kws = KiteTicker(api_key, access_token_zerodha)

#function to run when data is coming from zerodha
def on_ticks(ws, ticks):
    global DATABASE
    #creating new cnadles based on execution time
    #recording current data to database for all tickers
    DATABASE.checkCandle()
    for x in ticks:
        DATABASE.setVal(x['instrument_token'],x['last_price'])
        DATABASE.newCandle(x['instrument_token'])
        # Stratergy to buy after 3 continious increasing 
        # highs and sell after 3 continious decreasing lows
        if len(DATABASE.getOhlc(x['instrument_token']))>3:
            tempDb = DATABASE.getOhlc(x['instrument_token'])
            if(tempDb.iloc[-1]['High']>tempDb.iloc[-2]['High'] and tempDb.iloc[-2]['High']>tempDb.iloc[-3]['High']):
                order_id = kite.place_order(tradingsymbol=x['instrument_token'],
                                exchange=kite.EXCHANGE_NSE,
                                transaction_type=kite.TRANSACTION_TYPE_BUY,
                                quantity=1,
                                order_type=kite.ORDER_TYPE_MARKET,
                                product=kite.PRODUCT_NRML)
                print(oid)
            elif(tempDb.iloc[-1]['Low']<tempDb.iloc[-2]['Low'] and tempDb.iloc[-2]['Low']>tempDb.iloc[-3]['Low']):
                order_id = kite.place_order(tradingsymbol=x['instrument_token'],
                                exchange=kite.EXCHANGE_NSE,
                                transaction_type=kite.TRANSACTION_TYPE_SELL,
                                quantity=1,
                                order_type=kite.ORDER_TYPE_MARKET,
                                product=kite.PRODUCT_NRML)
                print(oid)

    #if current time is grater than ENDTIME the stop the code
    if(datetime.datetime.now()>ENDTIME):
        print("Market is closed now...")
        ws.stop()

#function to run when connection is established to zerodha
def on_connect(ws, response):
    # Callback on successful connect.
    ws.subscribe(TOKENS)

#funcion to run on connection close
def on_close(ws, code, reason):
    # On connection close stop the main loop
    # Reconnection will not happen after executing `ws.stop()`
    print(code)
    print(reason)
    ws.stop()

# Assign the callbacks.
kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close

# Infinite loop on the main thread. Nothing after this will run.
# You have to use the pre-defined callbacks to manage subscriptions.
kws.connect()
