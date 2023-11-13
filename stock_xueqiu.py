#coding=utf-8
#先引入后面可能用到的library
import time
import requests
import pandas as pd
import browser_cookie3
from StockTT import *
import operator
from threading import Thread
from multiprocessing import Process
import pysnowball as ball
from dingtalkchatbot.chatbot import DingtalkChatbot
from datetime import datetime
import schedule
import sys

class StockXueQiuRequest:
    def __init__(self):
        self.dateTimp = str(int(time.time()*1000)) 
        self.allstocks=[]
        self.markStocks=[]  #标记已经突破的只提醒一次
        cj = browser_cookie3.load()
        cookie = "xq_is_login=1;"
        for item in cj:
            if item.name == "xq_a_token" :
                cookie = cookie + 'xq_a_token=' + item.value + ';'
                ball.set_token(item.value)
                
         # cookie = cookie + 'xq_a_token=' + "fc05d0366e61e3aaac0d305139e4723619016e99" + ';'
        self.header = {
            'cookie':cookie,
            'User-Agent': 'Xueqiu iPhone 13.6.5'
        }
    
    #获取所有股票，市值在20亿到1000亿之间
    def getAllStocks(self):
        stocks = []
        page = 1
        while True:
            stock_list = self.getPageStocks(page)
            if not stock_list:
                break
            stocks += stock_list
            page += 1
        print("初步股票数据个数 %s" %(len(stocks)))

        threads = []  
        print("*************   start   ***************")
        size_array_stosks =self.list_split(stocks, 200)
        for index,small_codes_array in enumerate(size_array_stosks):
            print("开启线程校验stock %s"%(index))
            thre = Thread(target=self.stock_daily_check_array, args=([small_codes_array]))   # 创建一个线程
            threads.append(thre)
            thre.start()  # 运行线程
            
        for t in threads:
            t.join()
        print("*************   end   ***************")
        print("最终股票数据个数 %s" %(len(self.allstocks)))

        return stocks
        
    def stock_daily_check_array(self,temp_stocks):
        stocks=[]
        for index, symbol in  enumerate(temp_stocks):
            [price_120,is_m5_up_m60]=self.requestXueQiuDaily(symbol)

            if (is_m5_up_m60 == False):
                continue
            else:
                stocks.append({symbol:price_120})
        print("****** 线程执行完毕 符合个数%s"%(len(stocks)))
        self.allstocks.extend(stocks)

    def getPageStocks(self,pageSize):
        url="https://xueqiu.com/service/screener/screen?category=CNorder_by=symbol&order=desc&size=200&only_count=0&fmc=1000000000_100000000000&page="+str(pageSize)
        r = requests.get(url,headers=self.header)
        
        response = r.json()
        code=response['error_code']
        if code != 0:
            print("获取股票异常")
            return None
        data=response['data']
        if not len(data) > 0:
            return None
        #股票个数
        stock_count=data['count']
        stock_list=data['list']
        stocks=[]
        for item in stock_list:
            symbol=item['symbol']
            if (symbol.startswith("BJ") or item['current'] >= 200):
                #排除BJ和 股价大于200的
                continue
            
            if ("688" in symbol):
                #排除688
                continue
            
            if ("SZ20" in symbol):
                #排除688
                continue
            
            if ("st" in symbol  or "ST" in symbol ):
                #排除st
                continue
            stocks.append(symbol)

        print("第 %s 页股票个数 %s" %(pageSize,len(stocks)))
        return stocks



    def requestXueQiuDaily(self,ts_code,type="day"):
        if ts_code == None:
            return False

        count = "-365"
        if "week" in type:
            count = "-60"
  
        
        url="https://stock.xueqiu.com/v5/stock/chart/kline.json?period="+type+"&type=before&count="+count+"&symbol="+ts_code+"&begin="+self.dateTimp
        
        r = requests.get(url,headers=self.header)
        response = r.json()
        code=response['error_code']
        if code != 0:
            return [0,False]
        stock_daily=response['data']
        if len(list(stock_daily.keys()))<=0: #上市小于1年
            return [0,False]
        
        lines=stock_daily["item"]
        # end if
        if len(lines)<=200: #上市小于1年
            return [0,False]
     
        column = stock_daily['column']
        df=pd.DataFrame(lines,columns=column)
        df=df.drop(['volume_post','amount_post'],axis=1)
        # 涨跌金额
        df.rename(columns={'timestamp':'trade_date','volume':'changjiaoliang','chg':'zhangdiefu','turnoverrate':'huanshou'},inplace=True)
        df['trade_date'] = df['trade_date'].apply(lambda x: datetime.fromtimestamp(int(x)/1000).strftime("%Y%m%d") )
        df=df.sort_values("trade_date", ascending=False)[0:120]
        
        stocks_close=df.close.values[0:120]; 
        stocks_close = sorted(stocks_close, reverse=True) #120日中最高价
        
        MA60=RD(MA(stocks_close,60) ,D=2)
        MA5=RD(MA(stocks_close,5) ,D=2)
        
        is_m5_up_m60=all(operator.gt(MA5[0:1],MA60[0:1]))#之上连续是否M5在M60之上
        return [stocks_close[0],is_m5_up_m60]



    def list_split(self,array, n):
        return [array[i:i + n] for i in range(0, len(array), n)]
    
    
    
    def jiankong(self):
        stocks = self.allstocks
        # scheduler = schedule.Scheduler()
        # scheduler.every(1).minutes.do(job(self))
        print("监控所有股票代码 个数%s"%(len(stocks)))
        dowhile = True
        while True:
            # scheduler.run_pending()
            current = datetime.now()
            if (current.hour >= 15):
                dowhile = False
                sys.exit(0)
            self.job()
            time.sleep(60)
            
                        
    
    def job(self):
        print("开始时间 %s"%(datetime.now().strftime('%Y.%m.%d %H:%M:%S')))
        size_array_stosks =self.list_split(self.allstocks, 200)
        threads=[]
        for index,small_codes_array in enumerate(size_array_stosks):
            print("开启新高校验 %s"%(index))
            thre = Thread(target=self.jobSLite, args=([small_codes_array]))   # 创建一个线程
            threads.append(thre)
            thre.start()  # 运行线程
            
        for t in threads:
            t.join()
        print("结束时间 %s"%(datetime.now().strftime('%Y.%m.%d %H:%M:%S')))


    def jobSLite(self,stocks):
        for index,info in enumerate(stocks):
            for ts_code,price_120 in info.items():
                if (not ts_code in self.markStocks):
                    self.requestCurrentPrice(ts_code,price_120)               
                    
                    
    def requestCurrentPrice(self,ts_code,price_120):
        response=ball.quotec(ts_code)
        code=response['error_code']
        if code != 0:
            return 
        data=response['data']
        if len(data)!=1: 
            return 
        
        info = data[0]
        if (len(info.keys()) <=0):
            return
        
        current = info["current"]
        if (current>=price_120):
            print("当前股票突破120新高")
            self.dingtalk_robot(ts_code)
            self.markStocks.append(ts_code)

    
    def dingtalk_robot(self,ts_code):
        webhook = 'https://oapi.dingtalk.com/robot/send?access_token=d05f3d9ae31963dd0f6d2dcd9b103bf70886611419607f9127daacc176012bec'
        secrets = 'SEC1b7f4a01121185daf824f007361bfe03f95f8c12e08964dd2b7b44c6077cef1d'
        dogBOSS = DingtalkChatbot(webhook, secrets)
        red_msg = '<font color="#dd0000">监听突破:120日新高</font>'
        now_time = datetime.now().strftime('%Y.%m.%d %H:%M:%S')
        url = 'https://xueqiu.com/S/'+ts_code
        dogBOSS.send_markdown(
            title=f'小杨Stock监控',
            text=f'### **监听股票新高**\n'
                f'**股票代码:{ts_code}**\n\n'
                f'**{red_msg}**\n\n'
                f'**发送时间:**  {now_time}\n\n'
                f'**相关网址:**[点击跳转]({url}) \n',
            is_at_all=False)
        
        
        
        

    
    # #股票基础信息
    # def requestXueQiuBaseInfo(self,ts_code):
    #     if ts_code == None:
    #         return {}
    #     ts_code_arr = ts_code.split(".", 1)
    #     ts_code_symbol=ts_code_arr[1]+ts_code_arr[0]
        
    #     url="https://stock.xueqiu.com/v5/stock/quote.json?symbol="+ts_code_symbol+"&extend=detail"
    #     r = requests.get(url,headers=self.header)
    #     response = r.json()
    #     code=response['error_code']
    #     if code != 0:
    #         print("获取基础信息异常")
    #         return []
    #     stock_data=response['data']
    #     if len(list(stock_data.keys()))<=0:
    #         print("获取基础信息异常")
    #         return []
            
    #     quote = stock_data['quote']
    #     # 总市值
    #     total_mv= quote['market_capital']/100000000
    #     # 流通市值
    #     circ_mv= quote['float_market_capital']/100000000

    #     limit_up = quote['limit_up']#涨停价
    #     limit_down = quote['limit_down']#跌停价

    #     current = quote['current']
    #     status = quote['status']
    #     name = quote['name']

    #     limit_status = 0 #是否涨停
    #     if limit_up!=None and current>=limit_up:
    #         limit_status=1
            
    #     if limit_down!=None and current <=limit_down:
    #         limit_status=-1 
        
          
    #     trade_time = quote['time']
    #     d = datetime.datetime.fromtimestamp(trade_time/1000)
    #     a = d.strftime("%Y-%m-%d")
    #     return {"total_mv":total_mv,"circ_mv":circ_mv,"limit_status":limit_status,"trade_date":a,"status":status,"name":name}
       
    

    # #股票板块信息
    # def requestBankuaiDaily(self,ts_code):
        
    #     hy_dic={"hy":"","hy2":"","hy3":""}

    #     if ts_code == None:
    #         return hy_dic
    #     ts_code_arr = ts_code.split(".", 1)
    #     ts_code_symbol=ts_code_arr[0]
        
    #     headers={
    #         'cookie':'v=A5HXHYWXl6LoBfu37zzS0SP-pJcr_gVwr3KphHMmjdh3Gr7Mu04VQD_CuVgA; escapename=Mr_Yangwd; ticket=10e15e469f4f3a1970c65d5116e7e10f; u_name=Mr_Yangwd; user=MDpNcl9ZYW5nd2Q6Ok5vbmU6NTAwOjQ5MTkxNDIyNzo3LDExMTExMTExMTExLDQwOzQ0LDExLDQwOzYsMSw0MDs1LDEsNDA7MSwxMDEsNDA7MiwxLDQwOzMsMSw0MDs1LDEsNDA7OCwwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMSw0MDsxMDIsMSw0MDoyNTo6OjQ4MTkxNDIyNzoxNjQ0MzM2ODM3Ojo6MTU1MzczOTU0MDo0MDIzNjM6MDoxOTM4YzAwOTg5MGY2OTJkMjA3ZTgyM2U1ZmZmMDFkNGI6OjA%3D; user_status=0; userid=481914227',
    #         'User-Agent': 'EQHexinFee/10.90.90 (iPhone; iOS 15.3; Scale/3.00)'
    #     };
    #     url="http://basic.10jqka.com.cn/mapp/"+ts_code_symbol+"/company_base_info.json"
    #     r = requests.get(url,headers=headers)
    #     response = r.json()
    #     code=response['status_code']
    #     if code != 0:
    #         print("获取板块异常")
    #         return hy_dic
    #     stock_info=response['data']
    #     if len(list(stock_info.keys()))<=0:
    #         return hy_dic
          
    #     hy_info = stock_info['industry']
    #     if len(list(hy_info.keys()))<=0:
    #         return hy_dic
        
    #     if "hy" in list(hy_info.keys()):
    #         hy_dic['hy'] = hy_info['hy']
    #     if "hy2" in list(hy_info.keys()):
    #         hy_dic['hy2'] = hy_info['hy2']
    #     if "hy3" in list(hy_info.keys()):
    #         hy_dic['hy3'] = ""
    
    #     return hy_dic
    
    
    # @classmethod
    # def requestTongHuaShunBK(self,bk_code):
    #     headers = {
    #         'User-Agent': '%E5%90%8C%E8%8A%B1%E9%A1%BA/7 CFNetwork/1331.0.7 Darwin/21.4.0',
    #         'Accept': '*/*'            
    #     }
    #     URL = "http://zx.10jqka.com.cn/indval/getstocks?blockcode="+bk_code
    #     # print(URL)
    #     r = requests.get(URL,headers=headers)
    #     response = r.json()
    #     code=response['errorcode']
    #     if code != 0:
    #         print(response)
    #         return
        
    #     result=response['result']
    #     if not len(result.keys())>0:
    #         print(response)
    #         return
        
    #     count=result['count']
    #     data=result['data']
    #     allStock=[]
    #     for item in data:
    #         stockcode = item['stockcode']
    #         allStock.append(stockcode)
    #     return allStock
    
    
