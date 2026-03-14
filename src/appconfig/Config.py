import json
import os

def getServerConfig():
  with open('../config/server.json', 'r') as server:
    jsonServerData = json.load(server)
    return jsonServerData

def getSystemConfig():
  with open('../config/system.json', 'r') as system:
    jsonSystemData = json.load(system)
    return jsonSystemData

def getBrokerAppConfig(broker_name=None):
  """Load broker config. broker_name 'icicidirect' uses brokerapp_icici.json, else brokerapp.json (zerodha)."""
  if broker_name == 'icicidirect':
    config_path = '../config/brokerapp_icici.json'
  else:
    config_path = '../config/brokerapp.json'
  with open(config_path, 'r') as brokerapp:
    jsonUserData = json.load(brokerapp)
    return jsonUserData

def getHolidays():
  with open('../config/holidays.json', 'r') as holidays:
    holidaysData = json.load(holidays)
    return holidaysData

def getTimestampsData():
  serverConfig = getServerConfig()
  timestampsFilePath = os.path.join(serverConfig['deployDir'], 'timestamps.json')
  if os.path.exists(timestampsFilePath) == False:
    return {}
  timestampsFile = open(timestampsFilePath, 'r')
  timestamps = json.loads(timestampsFile.read())
  return timestamps

def saveTimestampsData(timestamps = {}):
  serverConfig = getServerConfig()
  timestampsFilePath = os.path.join(serverConfig['deployDir'], 'timestamps.json')
  with open(timestampsFilePath, 'w') as timestampsFile:
    json.dump(timestamps, timestampsFile, indent=2)
  print("saved timestamps data to file " + timestampsFilePath)
