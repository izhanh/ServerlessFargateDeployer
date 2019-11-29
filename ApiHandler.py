import sys
import json
import traceback
import PythonFunctions
import FargateFunctions
from pprint import pprint

# CORE API

def createApi(event, context):

    response = { "statusCode": 400 }
    configFile = PythonFunctions.readYamlfile('defaultConfig.yml')
    # If the event contains 'queryStringParameters' means it's being called from the API and parse it
    if "queryStringParameters" in event.keys():
        message = "Functions is being called from an API Call, parsing it...\n"
        if event['queryStringParameters']:
            message = "API call contains Query Parameters...\n"
            event = event['queryStringParameters']
        else:
            event = {}
            message = "API call does NOT contains Query Parameters...\n"
    else:
        message = "Functions is NOT being called from an API Call, not parsing\n"

    # Check that all the mandatory parameters are in
    if "api_environment" not in event.keys() or "lambda_key" not in event.keys():
        message = message + "\nWrong use of parameters. Mandatory:"
        message = message + "\n\tLambda API Key { 'lambda_key' : [ ALPHANUMERIC ] }"
        message = message + "\n\tAPI Environment { 'api_environment' : [ STRING ] }"
        message = message + "\n\nOptional:"
        message = message + "\n\tExecution Mode { 'mode' : [ LOCAL | LAMBDA ] }. If none is provided, 'lambda' is assumed"
        message = message + "\n\tAmount of Tasks { 'tasks_amount' : [ INTEGER ] }. If none is provided, '2' is defined by default"
        message = message + "\n\nParameters received:\n\n"
        message = message + PythonFunctions.turnDictToPrettyStr(event)
        
        response['body'] = message
        print(message)
        return response
    # Check that the lambda API Key is correct
    if event['lambda_key'] not in configFile['credentials']['api_key']:
        message = message + "\nUnauthorised"
        message = message + "\n\tLambda API Key is wrong"
        response['body'] = message
        print(message)
        return response

    # Optional Params
    if "mode" not in event.keys(): event['mode'] = "lambda"
    if "tasks_amount" in event.keys(): configFile[event['api_environment']]['task']['amount'] = event['tasks_amount']

    # Final configuration file
    PythonFunctions.printTitleInfo("AWS CREDS", configFile['aws'])
    PythonFunctions.printTitleInfo("API DEFAULT CONFIG", configFile[event['api_environment']])

    # Call the creation function and analyze the result
    creationResult = FargateFunctions.createApi(configFile, event['api_environment'], event['mode'])
    if creationResult['success']:
        response['statusCode'] = 200
        response['body'] = message + "API Environment [{}] created successfully".format(event['api_environment'])
    else:
        response['body'] = message + "API Environment [{}] Failed to be created. Reason: {}".format(event['api_environment'], creationResult['error'])

    print("\n" + str(response))
    return response

def deleteApi(event, context):

    response = { "statusCode": 400 }
    configFile = PythonFunctions.readYamlfile('defaultConfig.yml')
    # If the event contains 'queryStringParameters' means it's being called from the API and parse it
    if "queryStringParameters" in event.keys():
        message = "Functions is being called from an API Call, parsing it...\n"
        if event['queryStringParameters']:
            message = "API call contains Query Parameters...\n"
            event = event['queryStringParameters']
        else:
            event = {}
            message = "API call does NOT contains Query Parameters...\n"
    else:
        message = "Functions is NOT being called from an API Call, not parsing\n"

    # Check that all the mandatory parameters are in
    if "api_environment" not in event.keys() or "lambda_key" not in event.keys():
        message = message + "\nWrong use of parameters. Mandatory:"
        message = message + "\n\tLambda API Key { 'lambda_key' : [ ALPHANUMERIC ] }"
        message = message + "\n\tAPI Environment { 'api_environment' : [ STRING ] }"
        message = message + "\n\nOptional:"
        message = message + "\n\tExecution Mode { 'mode' : [ LOCAL | LAMBDA ] }. If none is provided, 'lambda' is assumed"
        message = message + "\n\nParameters received:\n\n"
        message = message + PythonFunctions.turnDictToPrettyStr(event)

        response['body'] = message
        print(message)
        return response
    # Check that the lambda API Key is correct
    if event['lambda_key'] not in configFile['credentials']['api_key']:
        message = message + "\nUnauthorised"
        message = message + "\n\tLambda API Key is wrong"
        response['body'] = message
        print(message)
        return response

    # Optional Params
    if "mode" not in event.keys(): event['mode'] = "lambda"

    # Final configuration file
    PythonFunctions.printTitleInfo("AWS CREDS", configFile['aws'])
    PythonFunctions.printTitleInfo("API DEFAULT CONFIG", configFile['shop'])

    # Call the deletion function and analyze the result
    deletionResult = FargateFunctions.deleteApi(configFile, event['api_environment'], event['mode'])
    if deletionResult['success']:
        response['statusCode'] = 200
        response['body'] = "API Environment [{}] deleted successfully".format(event['api_environment'])
    else:
        response['body'] = "API Environment [{}] Failed to be deleted. Reason: {}".format(event['api_environment'], deletionResult['error'])

    print("\n" + str(response))
    return response

# Local Function runner
if __name__ == '__main__':
    if len(sys.argv) < 2: 
        print("Please introduce what operation to perform [CREATE/DELETE] and the api_environment [STRING] (optional)\n")
    if len(sys.argv) > 3:
        print("Too many arguments. Please introduce what operation to perform [CREATE/DELETE/UPDATE] and the api_environment [STRING] (optional)\n")
    else:
        if len(sys.argv) == 2:
            api_environment = "api_prod"
            print("\nUsing default Env api_environment [{}]\n".format(api_environment))
        if len(sys.argv) == 3:
            api_environment = sys.argv[2]
            print("\nUsing specified Env api_environment [{}]\n".format(api_environment))
        elif "create" in sys.argv[1].lower():
            createApi({ "lambda_key": "YYYYYYYYYYYYYYYYYYYYYYYYYY", "api_environment": api_environment }, "")
        elif "delete" in sys.argv[1].lower():
            deleteApi({ "lambda_key": "YYYYYYYYYYYYYYYYYYYYYYYYYY", "api_environment": api_environment }, "")
        else:
            print("Could not recognize operation type. Please use [CREATE/DELETE]\n")