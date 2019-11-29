#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import ast
import json
import spur
import time
import yaml
import boto3
import datetime
import platform
import requests
import multiprocessing
from pprint import pprint
from termcolor import colored
from datetime import date, timedelta

# LOCAL OS PARAMS

currentFolder = os.path.dirname(os.path.abspath(__file__))
opSys = "windows" if "windows" in platform.platform().lower() else "linux"
pathSep = "\\" if opSys == "windows" else "/"

# SYTEM FUNCTIONS

def executeOsCommand(command):
    return os.popen(command).read()

def performSSHCommand(sshHost, sshPort, user, passw, command):
    shell = spur.SshShell(hostname = sshHost, port = sshPort, username = user, password = passw, missing_host_key = spur.ssh.MissingHostKey.accept)
    return shell.run(command).output

# AWS FUNCTIONS

def getAWSClient(awsTool, awsCreds):
    return boto3.client(awsTool,
        region_name = awsCreds['region_name'],
        aws_access_key_id = awsCreds['aws_access_key_id'],
        aws_secret_access_key = awsCreds['aws_secret_access_key'])

def parseAWSEventTrigger(triggerData, yamlFile):
    parsedEvent = {}

    if "s3" in triggerData['Records'][0].keys():
        print("Parsing an S3 Event")
        parsedEvent['lambda_key'] = readYamlfile(yamlFile)['credentials']['api_key']
        parsedEvent['ecommerce_id'] = triggerData['Records'][0]['s3']['object']['key'].split("/")[0]
    if "codecommit" in triggerData['Records'][0].keys():
        print("Parsing a CodeCommit Event")
        jsonDict = json.loads(triggerData['Records'][0]['customData'])
        parsedEvent['lambda_key'] = jsonDict['lambda_key']
        parsedEvent['ecommerce_id'] = jsonDict['ecommerce_id']

    return parsedEvent

# ARRAYS FUNCTIONS

def removeListFromOtherList(initialList, listToRemove):
    for element in listToRemove:
        if element in initialList: initialList.remove(element)

    return initialList

# STRING FUNCTIONS

def bytesToString(bytesText):
    return bytesText.decode("utf-8")

def parseKeyValueFromString(text, key):
    for line in text.split("\n"):
        if key in line: return line.replace(key + "=", "").replace("\n", "").strip()

def getColoredText(text, color):
    return colored(text, color)

def printTitle(title):
    print("\n==============================================================================================================")
    print(title + "\n==============================================================================================================")

def printSubTitle(subtitle):
    print("--------------------------------------------------------------------------------------------------------------")
    pprint(subtitle)
    print("--------------------------------------------------------------------------------------------------------------")

def printTitleInfo(title, info):
    printTitle(title)
    pprint(info)

def replaceAllNumericChars(ogStr, replacement):
    finalStr = ogStr
    for char in ogStr:
        if char.isnumeric(): finalStr = finalStr.replace(char, replacement)

    return finalStr.strip()

def replaceAllNonNumericChars(ogStr, replacement):
    finalStr = ogStr
    for char in ogStr:
        if not char.isnumeric(): finalStr = finalStr.replace(char, replacement)

    return finalStr.strip()

def removeStringsFromList(ogList, strToRemove):
    finaList = []
    for element in ogList:
        if element is not strToRemove: finaList.append(element)

    return finaList

def removeEmptyElementsFromList(ogList):
    finaList = []
    for element in ogList:
        if len(element) > 0: finaList.append(element)

    return finaList

# JSON/YAML/DICT FUNCTIONS

def byteEncondeDict(dictToEnconde):
    return bytes(json.dumps(dictToEnconde), encoding = 'utf8')

def replaceJSONBoolsAsDict(strDict):
    return ast.literal_eval(str(strDict).replace(": \"True\"", ": True").replace(": \"False\"", ": False"))

def replaceAllInDict(dicto, valueToReplace, finalVal):
    return ast.literal_eval(str(dicto).replace(valueToReplace, finalVal))

def replaceAllInJsonDict(jsonDict, valueToReplace, finalVal):
    return json.loads(str(jsonDict) \
        .replace(valueToReplace, finalVal) \
        .replace("\"", "") \
        .replace(": True", ": \"True\"") \
        .replace(": False", ": \"False\"") \
        .replace("'", "\""))

def turnDictToPrettyStr(dictStr):
    if len(str(dictStr)) < 3: return "{\n\tNone\n}"
    return json.dumps(dictStr, indent = 4, sort_keys = True)

def printDictPretty(dictStr):
    print(dictStr)

# TIMESTAMP FUNCTIONS

def sleepSecs(secs):
    time.sleep(secs)

def getTomorrowDate():
    yd = date.today() + timedelta(1)
    return yd.strftime("%d_%m")

def getTimestampAsString(timestamp):
    return timestamp.strftime("%H:%M")

def getDatestampAsString(timestamp):
    return timestamp.strftime("%d-%m")

def getTimedeltaInHours(hoursDelta):
    return datetime.datetime.now() + timedelta(hours = hoursDelta)

def getYesterdayDate():
    yd = date.today() - timedelta(1)
    return yd.strftime("%d_%m")

def getCurrentDate():
    dt = datetime.datetime.now()
    return dt.strftime("%d_%m")

def getCurrentTime():
    return datetime.datetime.now()

def getCurrentTimeAsMilis():
    return time.time()

def getElapsedTime(iniTime):
    return getCurrentTimeAsMilis() - iniTime

def checkElapsedTime(iniTime, maxTime):
    return getElapsedTime(iniTime) < maxTime

def getCurrentTimeAsStr():
    return getTimestampAsString(getCurrentTime())

def getHour():
    dt = datetime.datetime.now()
    return dt.strftime("%H")

def getMinute():
    dt = datetime.datetime.now()
    return dt.strftime("%M")

def formatTime(timeStr):
    if timeStr[0] == "0":
        return timeStr[1:]
    else:
        return timeStr

# MANAGE FILES FUNCTIONS

def parseKeyValueFromFile(filePath, key):
    parseKeyValueFromString(readStringfile(filePath), key)

def createFolder(path):
    os.mkdir(path)

def checkFolderExist(path):
    return os.path.isdir(path)

def doesFileExist(path):
    return os.path.isfile(path)

def writeToFile(path, text):
    with open(path, 'w') as file:
        print(text, file)

def writeJsonFile(path, jsonDict):
    with open(path, 'w') as outfile:
        json.dump(jsonDict, outfile)

def readStringfile(path):
    return open(path).read()

def readJsonfile(path):
    return json.loads(readStringfile(path))

def readYamlfile(path):
    return yaml.safe_load(readStringfile(path))

# HTTP CALLS FUNCTIONS

def pingHost(host):
    response = os.system('ping -c 1 ' + host)
    if response == 0:
        print("Host [{}] is up".format(host))
    else:
        print("Host [{}] is down".format(host))

def getRequestAsJson(url):
    payload = ""
    headers = { "cache-control": "no-cache" }
    response = requests.get(url, data = payload, headers = headers).text
    
    if "IP banned" in response or "restrict access" in response or "Checking your browser" in response:
        response = getResponseFromLambda("HttpCaller", url, "eu-west-1")
        if "IP banned" in response or "restrict access" in response or "Checking your browser" in response:
            response = getResponseFromLambda("HttpCaller", url, "eu-west-2")
        return eval(response)["body"]

    return json.loads(response)

def getResponseFromLambda(lambdaFunction, url, region):
    payload = { "url": url }

    bynaryPayload = json.dumps(payload)
    client = boto3.client('lambda', region_name = region)
    response = client.invoke(
        FunctionName = lambdaFunction,
        InvocationType = 'RequestResponse',
        Payload = bynaryPayload)

    binaryResponse = response['Payload'].read()
    strResponse = binaryResponse.decode('ascii').replace("\"", "'").replace("\\", "").replace("''", "")

    # return eval(strResponse)
    return strResponse

def getResponseFromLambdaAsDict(lambdaFunction, url, region):
    response = getResponseFromLambda(lambdaFunction, url, region)
    jsonData = json.dumps(response)

    return jsonData

# MULTIPROCESSING FUNCTIONS

def executePythonFunctionWithOutput(function, arguments, output):
    output.put(function(arguments))

def executeMultiprocessingFunctions(multiFunction, arguments, waitFinish):
    repetitions = len(arguments)
    print("\nExecuting Concurrently:\n\tFunction => [{}]\n\tArguments => {}\n\tRepetitions => [{}]\n\tWait for Finish => [{}]\n" \
        .format(str(multiFunction).split(" ")[1], arguments, repetitions, waitFinish))

    # Output values
    output = multiprocessing.Queue()
    # Setup a list of processes that we want to run
    processes = [multiprocessing.Process(target = executePythonFunctionWithOutput, \
        args = (multiFunction, arguments[x], output)) for x in range(repetitions)]

    # Run processes
    for p in processes: p.start()

    if waitFinish:
        # Exit the completed processes
        for p in processes: p.join()

        # Get process results from the output queue
        return [output.get() for p in processes]
