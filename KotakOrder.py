import pandas as pd
import uuid
from time import sleep,time
from logger import  logger
import config
class KotakAPI:
    
    def __init__(self, neoObj):
            self.neoObj = neoObj

  
    """
    {'stat': 'Ok',
 'nOrdNo': '230722000001531',
 'tid': 'server3_29087',
 'stCode': 200}
order_type  = 'MKT' /'CNC' / 
 transaction_type = 'B' /'S'
    """


    def placeOrder(self,tsym:str,transaction_type:str,quantity:int,order_type ='MKT',limitPrice = 0,trigger_price = 0,productType= config.ORDER_TYPE ):
        try:
            ordeRes = self.neoObj.place_order(exchange_segment=config.EXCHANGE, product=productType, price=str(self.truncate(limitPrice)), order_type=order_type, 
                quantity=str(quantity), validity='DAY', trading_symbol=tsym,
                transaction_type=transaction_type, amo="NO", disclosed_quantity="0", market_protection="0", pf="N",
                trigger_price=str(self.truncate(trigger_price)), tag=config.ENTRY_ORDERTAG + str(uuid.uuid4())  )
            
            logger.info(f'Order submitted for {tsym} {transaction_type} {quantity} {order_type} {limitPrice} {trigger_price} {productType} Response: {ordeRes}')

            if 'nOrdNo' in ordeRes:
                return ordeRes['nOrdNo']
        except :
            logger.exception(f'Error in order Placement')


    def truncate(self,price):
        if price is None or  price == 0 :
            return 0
        price = round(price / 0.05) * 0.05  # tick size 0.05
        n = 2
        s = '%.12f' % price
        i, p, d = s.partition('.')
        return float('.'.join([i, (d+'0'*n)[:n]]))

    def getOrderbook(self):
        for i in range(4):
            try:
                orderRes =  self.neoObj.order_report()
                if orderRes :
                    return orderRes
            except  :
                logger.exception(f'Error in orderbook')
            sleep(i)

    def getPosition(self):
        for i in range(4):
            try:
                positionRes =  self.neoObj.positions()
                if positionRes :
                    return positionRes
            except  :
                logger.exception(f'Error in positionBook')
            sleep(i)

    
    def cancelOrderbyid(self,order_id):
        try:
            cancelRes = self.neoObj.cancel_order(order_id = order_id)
            logger.info(f'Cancellation response {order_id} {cancelRes}')
        except  :
            logger.exception(f'Error in cancel order {order_id}  ')


    def cancelAllOrder(self,ordertag = None):
        try:
            orderRes =  self.neoObj.order_report()
            logger.info(f'Cancel All order  {orderRes}')
            for order in orderRes['data']:
                orderid = order['nOrdNo']
                if order['ordSt'] in ['rejected', 'cancelled','complete']:
                    logger.info(f'{orderid} not open for cancel')
                    continue
                
                if (ordertag is None  or order['GuiOrdId'] == ordertag) : 
                    self.cancelOrderbyid(orderid)
        except :
            logger.exception(f'Error in cancel ALL order ')

    def isAllOrderTrigger(self,orderlist):
        try:
            orderBook = self.getOrderbook()
            orderdf = pd.DataFrame(orderBook['data'])
            orderdf = orderdf[orderdf.nOrdNo.isin(orderlist)]
            if len(orderdf[orderdf['ordSt'] =='complete']) ==  len(orderlist)  : 
                logger.info(f'All Order Traded : {orderdf.to_json(orient ="records")}')
                return True ,orderdf
        except :
            logger.exception(f'Error in getting entry Price')
        
        return False ,orderdf

    def exitAllPosition(self):
        config.RUN_PROCESS = False
        self.cancelAllOrder()
        positionRes = self.getPosition()
        logger.info(f'Close Position {positionRes}')
        if 'data' in  positionRes :
            for pos in positionRes['data']:
                try:
                    buyQty = int(pos['flBuyQty'])
                    sellQty = int(pos['flSellQty'])
                    if buyQty != sellQty:
                        qty = abs(buyQty - sellQty)
                        transaction_type ='S' if buyQty > sellQty  else 'B'
                        logger.info(f"Open Position {transaction_type} {pos['trdSym']} {qty}")
                        self.placeOrder(pos['trdSym'],transaction_type,qty,order_type ='MKT',productType= pos['prod'] )
                except :
                    logger.exception(f'Error in closing {pos}')
 

