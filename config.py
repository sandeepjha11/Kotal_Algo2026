import pytz
from datetime import datetime
TIME_ZONE = pytz.timezone('Asia/Kolkata')
TZ_INFO = datetime.now(TIME_ZONE).tzinfo
ENTRY_ORDERTAG = 'SAN_ALGO'
EXIT_ORDERTAG = 'SAN_ALGO'


EXCHANGE = 'nse_fo'
RUN_PROCESS = True
NEO_OBJ =None
TOKEN_MAP = {}
EXPIRY_DATE= None
SPOT_TOKEN = None

#KOTAK Credentials


consumer_key= ""
CS= ""
Mob = ""
Pwd  = ""
MPIN= ""
totp=""
ucc=""



QTY = 1
SL_LIMIT = 1
EXPIRY_OFFSET = 0
SL = 5 # in  percentage
ORDER_TYPE = 'MIS' #NRML
SYMBOL = 'NIFTY'
EXIT_TIME = (15,30,0)     
ENTRY_TIME = (9,25,0)

