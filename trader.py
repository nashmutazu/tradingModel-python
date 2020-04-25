'''
    Trading Model 
    @version 1.01
    @author Nyasha Mutazu nashmutazu@gmail.com
    @copyright 2020 | Free to use
    @terms and condition -- Please read before proceeding
'''
import requests
import os
import json
import difflib 
from bs4 import BeautifulSoup
import decimal
import pandas as pd

import plotly.graph_objs as go
from plotly.offline import plot

# From secrets 
import secrets

companies = json.load(open('./companies-symbols/companies.json'))

class TradingModel:
    def __init__(self):
        self.stock_name = '' 
        self.buy_signals = []
        self.headers = {
            'APCA-API-KEY-ID': secrets.ALPACA_API_KEY,
            'APCA-API-SECRET-KEY': secrets.ALPACA_SECRET_KEY
        }
        self.df = pd.read_csv(f'./data/Data-for-{self.stock_name}.csv')

    def snp500(self):

        '''
        Pulling all the top 500 companies in the S&P 500 

        '''
        c = requests.get('https://www.slickcharts.com/sp500').content
        page = BeautifulSoup(c, 'html.parser')
        page.prettify()

        table = page.findAll('tr')[1:]

        contained_data = open('./companies-symbols/companies.json', 'w+')
        contained_data.write('{\n')

        for i in table:
            company = i.find_all('td')[1].text
            symbol = i.find_all('td')[2].text
            if i == table[-1]:
                contained_data.write(f"\"{company.lower()}\": \"{symbol}\"\n")
            else:
                contained_data.write(f"\"{company.lower()}\": \"{symbol}\",\n")

        contained_data.write('}\n')
        contained_data.close()

    def createFolder(self, path_insert=False):
        directory = './data/'
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            print ('Error: Creating directory. ' +  directory)

    def check_path(self):
        stock_path = f'./data/{self.stock_name}.csv'

        if os.path.exists(stock_path):
            pass
        elif not os.path.exists('./data/'):
            createFolder()
        
        return stock_path

    def floatToString(self, f: float):
        ctx = decimal.Context()
        ctx.prec = 12
        d1 = ctx.create_decimal(repr(f))
        return format(d1, 'f')

    def add_stock_details(self):
        response = requests.get(secrets.url.format(self.stock_name, secrets.API_KEY))

        if response.status_code == 200 and 'Error Message' not in response.json().keys():

            dictionary = response.json()['Time Series (Daily)']

            data = []

            col_names = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']

            for i, j in dictionary.items():
                data.append((i, float(j['1. open']), float(j['2. high']), float(j['3. low']), float(j['4. close']), float(j['5. volume'])))
                
            df = pd.DataFrame(data, columns=col_names)

            #  Creating the rolling mean and standard deviation 
            rolling_mean = df['Close'].ewm(span=2, adjust=False).mean()
            rolling_std = df['Close'].ewm(span=2, adjust=False).std()

            # Creating Fast and Slow moving average 
            df['Fast SMA'] = df['Close'].ewm(span=1, adjust=False).mean()
            df['Slow SMA'] = df['Close'].ewm(span=3, adjust=False).mean()

            # Creating Low Bollinger Band
            df['LBB'] = rolling_mean - (2 * rolling_std)

            df.to_csv(f'./data/Data-for-{self.stock_name}.csv')

        else: 
            print(f"Error creating Data for {self.stock_name} ")

    def find_request(self):
        while True:
            try: 
                user_input = str(input('Search for a business: ')).lower()
            except:
                print(f'Sorry, I cannot fetch {user_input} right now')
            else:
                pass

            value = difflib.get_close_matches(user_input, companies.keys())

            if value:
                newValueAnswer = str(input(f'Do you mean {value[0]}? yes(y) or no(n): ')).lower()
                value = value[0]

                if newValueAnswer[0] == 'y' and value:
                    if value in companies:
                        self.stock_name = companies[value]
                        break

            
            print('Care to try again? ')

    def plot_data(self):
        df = pd.read_csv(f'./data/Data-for-{self.stock_name}.csv')

        # Plot candlestick chart
        candle = go.Candlestick(
            x = df['Time'],
            open = df['Open'],
            close = df['Close'],
            high = df['High'],
            low = df['Low'],
            name = 'Candlesticks'
        )

        # Plotting MA's
        ssma = go.Scatter(
            x = df['Time'],
            y = df['Slow SMA'],
            name = 'Slow SMA',
            # Green
            line = dict(color='rgba(0, 255, 0, .8)'),
            line_shape="spline"
        )

        # Plotting MA's
        fsma = go.Scatter(
            x = df['Time'],
            y = df['Fast SMA'],
            name = 'Fast SMA',
            # Blue
            line = dict(color='rgba(0, 0, 255, .8)'),
            line_shape="spline"
        )

        lowb = go.Scatter(
            x = df['Time'],
            y = df['LBB'],
            name = 'Lower Bollinger Band',
            # Red
            line = dict(color='rgba(255, 0, 0, 0.8)'),
            line_shape="spline"
        )

        # Plotting moving averages 
        data = [candle, ssma, fsma, lowb]

        # Displaying Buy signals 
        if len(self.buy_signals) > 0:
            buys = go.Scatter(
                    x = [item[0] for item in self.buy_signals],
                    y = [item[1] for item in self.buy_signals],
                    name = "Buy Signals",
                    mode = "markers",
                )

            sells = go.Scatter(
                    x = [item[0] for item in self.buy_signals],
                    y = [item[1]*1.05 for item in self.buy_signals],
                    name = "Sell Signals",
                    mode = "markers",
                    )
            
            data = [candle, ssma, fsma, lowb, buys, sells]

        layout = go.Layout(title = f'Data for {self.stock_name}')
        fig = go.Figure(data = data, layout = layout)

        plot(fig, filename=f'Stock_data_for-{self.stock_name}.html')

    def maStrategy(self, i:int):
        df = self.df 
        buy_price = 0.98 * df['Slow SMA'][i]

        if buy_price >= df['Close'][i]:
            self.buy_signals.append((df['Time'][i], df['Close'][i], df['Close'][i] * 1.045))
            return True
        
        return False

    def bollStrategy(self, i:int):
        df = self.df 
        buy_price = 0.98 * df['LBB'][i]
        
        if buy_price >= df['Close'][i]:
            self.buy_signals.append((df['Time'][i], df['Close'][i], df['Close'][i] * 1.045))
            return True
        
        return False

    def strategy(self):
        try:
            df = self.df

            for i in range(len(df['Close'])):
                if self.maStrategy(i):
                    print(f" MA Strategy match at {df['Close'][i]} on date {df['Time'][i]}")
                
                if self.bollStrategy(i):
                    print(f" BOLL Strategy match at {df['Close'][i]} on date {df['Time'][i]}")


        except Exception as e: 
            print(e)
        else:
            pass

    def buyOrder(self, symbol: str, qty: float, take_profit: float, stop_loss: float, test:bool = True): 
        params = {
            'symbol': symbol,
            'qty': self.floatToString(qty),
            'side': 'buy',
            'take_profit': self.floatToString(take_profit),
            'stop_loss': self.floatToString(stop_loss),
            'time_in_force': 'gtc',
            'type': 'market',
        }

        if test:
            try: 
                response = requests.post(secrets.endpoint + '/v2/orders/', params = params, headers = self.headers)
            except Exception as e:
                print(f'Expection occured when placing order {secrets.endpoint}')
                print(e)
            else:
                pass
    
    def cancelOrder(self, _id: str, test:bool =True):
        params = {
            'order_id': _id
        }

        try: 
            response = requests.delete(secrets.endpoint + '/v2/orders/', params = params, headers = self.headers)
        except Exception as e:
            print(f'Expection occured when placing order {secrets.endpoint}')
            print(e)
        if response.status_code == 404:
            print('Order Not Found')
        elif response.status_code == 422: 
            print('The order status is not cancelable')

    def getAllOrders(self): 
        response = requests.delete(secrets.endpoint + '/v2/orders', headers = self.headers)


if __name__ == "__main__":

    stock = TradingModel()

    stock.find_request()

    stock.add_stock_details()

    stock.strategy()

    stock.plot_data()

    '''

        Create algorithm to proceed consistently getting buy, sell, cancel and get all orders
        
    '''
