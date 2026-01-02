

import logging 
import sys 
from  datetime import datetime
td = datetime.today().date()
logging.basicConfig(filename=f"KOTAK_NEO_{td}.log", format='%(asctime)s - %(levelname)s - %(message)s') 
  
  
logger=logging.getLogger() 
logger.setLevel(logging.INFO) 

stdout_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stdout_handler)
