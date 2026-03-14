import logging

from appconfig.Config import getBrokerAppConfig
from models.BrokerAppDetails import BrokerAppDetails
from loginmgmt.ZerodhaLogin import ZerodhaLogin
from loginmgmt.ICICIDirectLogin import ICICIDirectLogin

class Controller:
  brokerLogin = None # static variable
  brokerName = None # static variable

  def handleBrokerLogin(args, broker_name=None):
    brokerAppConfig = getBrokerAppConfig(broker_name)

    brokerAppDetails = BrokerAppDetails(brokerAppConfig['broker'])
    brokerAppDetails.setClientID(brokerAppConfig['clientID'])
    brokerAppDetails.setAppKey(brokerAppConfig['appKey'])
    brokerAppDetails.setAppSecret(brokerAppConfig['appSecret'])

    logging.info('handleBrokerLogin appKey %s', brokerAppDetails.appKey)
    Controller.brokerName = brokerAppDetails.broker
    if Controller.brokerName == 'zerodha':
      Controller.brokerLogin = ZerodhaLogin(brokerAppDetails)
    # Other brokers - not implemented
    #elif Controller.brokerName == 'fyers':
      #Controller.brokerLogin = FyersLogin(brokerAppDetails)
    elif Controller.brokerName == 'icicidirect':
      Controller.brokerLogin = ICICIDirectLogin(brokerAppDetails)

    redirectUrl = Controller.brokerLogin.login(args)
    return redirectUrl

  def getBrokerLogin():
    return Controller.brokerLogin

  def getBrokerName():
    return Controller.brokerName
