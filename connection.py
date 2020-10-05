"""
This script creates various object to connect with different components of Trade API"
"""
import configparser as ConfigParser
import alpaca_trade_api as tradeapi


class Client:
    """
    A class to establish the connection with the brokers API.
    """

    def __init__(self):
        """
        Establish the API connection
        """
        configParser = ConfigParser.RawConfigParser()
        configFile = 'config.cfg'
        configParser.read(configFile)
        self.api_key = configParser.get('alpaca', 'api_key')
        self.api_secret = configParser.get('alpaca', 'api_secret')
        self.base_url = configParser.get('alpaca', 'base_url')

    def connect(self):
        return tradeapi.StreamConn(str(self.api_key), str(
            self.api_secret), str(self.base_url))

    def api(self):
        return tradeapi.REST(str(self.api_key), str(
            self.api_secret), str(self.base_url), api_version='v2')
