#coding=utf-8
#先引入后面可能用到的library
from stock_xueqiu import StockXueQiuRequest

if __name__ == '__main__':
    xueqiu_cloinet = StockXueQiuRequest()
    xueqiu_cloinet.getAllStocks();
    xueqiu_cloinet.jiankong();
    
    # xueqiu_cloinet.dingtalk_robot("SZ300606");

    
    
    # xueqiu_cloinet.requestXueQiuDaily("SZ301160")