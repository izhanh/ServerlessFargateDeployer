import sys
import json
import traceback
import PythonFunctions
import FargateFunctions

# FRONT SHOPS

# This function updates ALL or ONE shop(s)
def updateShop(event, context):

    response = { "statusCode": 400 }
    configFile = PythonFunctions.readYamlfile('defaultConfig.yml')
    # If the event contains 'queryStringParameters' means it's being called from the API and parse it
    if "queryStringParameters" in event.keys():
        message = "Function is being called from an API Call, parsing it...\n"
        if event['queryStringParameters']:
            message = message + "\nAPI call contains Query Parameters...\n"
            event = event['queryStringParameters']
        else:
            event = {}
            message = "\nAPI call does NOT contains Query Parameters...\n"
    else:
        message = "Function is NOT being called from an API Call, not parsing\n"

    # If the event contains 'Records' means it's being called from an S3 update
    if "Records" in event.keys():
        message = message + "\nFunction is being called from an AWS Event trigger, parsing it...\n"
        unparsedEvent = event

        # Parse the AWS Event message
        try:
            event = PythonFunctions.parseAWSEventTrigger(event, 'defaultConfig.yml')
        except:
            message = message + "\nAWS Event call is wrong/wrongly parsed"
            message = message + "\n\nAWS Event received:\n\n"
            message = message + PythonFunctions.turnDictToPrettyStr(unparsedEvent)
            response['body'] = message
            print(message)
            return response
    else:
        message = message + "\nFunction is NOT being called from an AWS Event trigger, not parsing\n"

    # Check that all the mandatory parameters are in
    if "ecommerce_id" not in event.keys() or "lambda_key" not in event.keys() or "force_update" not in event.keys():
        message = message + "\nWrong use of parameters. Mandatory:"
        message = message + "\n\tLambda API Key { 'lambda_key' : [ ALPHANUMERIC ] }"
        message = message + "\n\tEcommerce-ID { 'ecommerce_id' : [ INTEGER ] or [ALL] to update every Shop }"
        message = message + "\n\tForce Update { 'force_update' : [ BOOLEAN ] }"
        message = message + "\n\nOptional:"
        message = message + "\n\tExecution Mode { 'mode' : [ LOCAL | LAMBDA ] }. If none is provided, 'lambda' is assumed"
        message = message + "\n\tVersion of the shop { 'ecommerce_version' : [ STRING ] }. If none is provided, 'master' is defined by default"
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

    # Mandatory params
    PythonFunctions.printTitle("REPLACING CONFIG FILE VALUE [{}] WITH [{}]" \
        .format(configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id']))
    configFile = PythonFunctions.replaceAllInDict(configFile, configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id'])

    # Optional Params
    if "mode" not in event.keys(): event['mode'] = "lambda"
    if "ecommerce_version" in event.keys(): configFile['shop']['properties']['ecommerce_version'] = event['ecommerce_version']

    # Final configuration file
    PythonFunctions.printTitleInfo("AWS CREDS", configFile['aws'])
    PythonFunctions.printTitleInfo("SHOP DEFAULT CONFIG", configFile['shop'])

    # Call the deletion function and analyze the result
    deletionResult = FargateFunctions.updateShops(configFile, event['force_update'], event['mode'])
    if deletionResult['success']:
        response['statusCode'] = 200
        if "all" in event['ecommerce_id']:
            response['body'] = "All Shops instances updated successfully".format(event['ecommerce_id'])
        else:
            response['body'] = "Shop with Ecommerce-ID [{}] updated successfully".format(event['ecommerce_id'])
    else:
        if "all" in event['ecommerce_id']:
            response['body'] = "All Shop Insances failed to be updated. Reason: {}".format(deletionResult['error'])
        else:
            response['body'] = "Shop with Ecommerce-ID [{}] update failed. Reason: {}".format(event['ecommerce_id'], deletionResult['error'])

    print("\n" + str(response))
    return response

def createShop(event, context):

    response = { "statusCode": 400 }
    configFile = PythonFunctions.readYamlfile('defaultConfig.yml')
    # If the event contains 'queryStringParameters' means it's being called from the API and parse it
    if "queryStringParameters" in event.keys():
        message = "Function is being called from an API Call, parsing it...\n"
        if event['queryStringParameters']:
            message = message + "\nAPI call contains Query Parameters...\n"
            event = event['queryStringParameters']
        else:
            event = {}
            message = message + "\nAPI call does NOT contains Query Parameters...\n"
    else:
        message = "Function is NOT being called from an API Call, not parsing\n"

    # Check that all the mandatory parameters are in
    if "ecommerce_id" not in event.keys() or "lambda_key" not in event.keys():
        message = message + "\nWrong use of parameters. Mandatory:"
        message = message + "\n\tLambda API Key { 'lambda_key' : [ ALPHANUMERIC ] }"
        message = message + "\n\tEcommerce-ID { 'ecommerce_id' : [ INTEGER ] }"
        message = message + "\n\nOptional:"
        message = message + "\n\tExecution Mode { 'mode' : [ LOCAL | LAMBDA ] }. If none is provided, 'lambda' is assumed"
        message = message + "\n\tAmount of Tasks { 'tasks_amount' : [ INTEGER ] }. If none is provided, '2' is defined by default"
        message = message + "\n\tCPU of the Tasks { 'tasks_cpu' : [ INTEGER ] }. If none is provided, '256' is defined by default"
        message = message + "\n\tMemory of the Tasks { 'tasks_memory' : [ INTEGER ] }. If none is provided, '512' is defined by default"
        message = message + "\n\tVersion of the sdk { 'sdk_version' : [ STRING ] }. If none is provided, 'master' is defined by default"
        message = message + "\n\tVersion of the fwk { 'fwk_version' : [ STRING ] }. If none is provided, 'master' is defined by default"
        message = message + "\n\tVersion of the shop { 'ecommerce_version' : [ STRING ] }. If none is provided, 'master' is defined by default"
        message = message + "\n\tPHAR Autoupdater active { 'shop_autoupdate' : [ BOOLEAN ] }. If none is provided, 'false' is defined by default\n"
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

    # Mandatory params (the URL is generated thru the Ecommerce-ID)
    configFile['shop']['properties']['url'] = event['ecommerce_id'] + ".site.logicommerce.cloud"
    PythonFunctions.printTitle("REPLACING CONFIG FILE VALUE [{}] WITH [{}]" \
        .format(configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id']))
    configFile = PythonFunctions.replaceAllInDict(configFile, configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id'])

    # Optional Params
    if "mode" not in event.keys(): event['mode'] = "lambda"
    if "tasks_cpu" in event.keys(): configFile['shop']['task']['cpu'] = event['tasks_cpu']
    if "tasks_memory" in event.keys(): configFile['shop']['task']['memory'] = event['tasks_memory']
    if "tasks_amount" in event.keys(): configFile['shop']['task']['amount'] = event['tasks_amount']
    if "sdk_version" in event.keys(): configFile['shop']['properties']['sdk_version'] = event['sdk_version']
    if "fwk_version" in event.keys(): configFile['shop']['properties']['fwk_version'] = event['fwk_version']
    if "shop_autoupdate" in event.keys(): configFile['shop']['properties']['shop_autoupdate'] = event['shop_autoupdate']
    if "ecommerce_version" in event.keys(): configFile['shop']['properties']['ecommerce_version'] = event['ecommerce_version']

    # Final configuration file
    PythonFunctions.printTitleInfo("AWS CREDS", configFile['aws'])
    PythonFunctions.printTitleInfo("SHOP DEFAULT CONFIG", configFile['shop'])

    # Call the creation function and analyze the result
    creationResult = FargateFunctions.createShop(configFile, event['mode'])
    if creationResult['success']:
        response['statusCode'] = 200
        response['body'] = "Shop with Ecommerce-ID [{}] created successfully".format(event['ecommerce_id'])
    else:
        response['body'] = "Shop with Ecommerce-ID [{}] Failed to be created. Reason: {}".format(event['ecommerce_id'], creationResult['error'])

    print("\n" + str(response))
    return response

def deleteShop(event, context):

    response = { "statusCode": 400 }
    configFile = PythonFunctions.readYamlfile('defaultConfig.yml')
    # If the event contains 'queryStringParameters' means it's being called from the API and parse it
    if "queryStringParameters" in event.keys():
        message = "Function is being called from an API Call, parsing it...\n"
        if event['queryStringParameters']:
            message = message + "\nAPI call contains Query Parameters...\n"
            event = event['queryStringParameters']
        else:
            event = {}
            message = message + "\nAPI call does NOT contains Query Parameters...\n"
    else:
        message = "Function is NOT being called from an API Call, not parsing\n"

    # Check that all the mandatory parameters are in
    if "ecommerce_id" not in event.keys() or "lambda_key" not in event.keys():
        message = message + "\nWrong use of parameters. Mandatory:"
        message = message + "\n\tLambda API Key { 'lambda_key' : [ ALPHANUMERIC ] }"
        message = message + "\n\tEcommerce-ID { 'ecommerce_id' : [ INTEGER ] }"
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

    # Mandatory params
    configFile['shop']['properties']['url'] = event['ecommerce_id'] + ".site.logicommerce.cloud"
    PythonFunctions.printTitle("REPLACING CONFIG FILE VALUE [{}] WITH [{}]" \
        .format(configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id']))
    configFile = PythonFunctions.replaceAllInDict(configFile, configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id'])

    # Optional Params
    if "mode" not in event.keys(): event['mode'] = "lambda"

    # Final configuration file
    PythonFunctions.printTitleInfo("AWS CREDS", configFile['aws'])
    PythonFunctions.printTitleInfo("SHOP DEFAULT CONFIG", configFile['shop'])

    # Call the deletion function and analyze the result
    deletionResult = FargateFunctions.deleteShop(configFile, event['mode'])
    if deletionResult['success']:
        response['statusCode'] = 200
        response['body'] = "Shop with Ecommerce-ID [{}] deleted successfully".format(event['ecommerce_id'])
    else:
        response['body'] = "Shop with Ecommerce-ID [{}] Failed to be deleted. Reason: {}".format(event['ecommerce_id'], deletionResult['error'])

    print("\n" + str(response))
    return response

def compileS3Phar(event, context):

    response = { "statusCode": 400 }
    configFile = PythonFunctions.readYamlfile('defaultConfig.yml')
    # If the event contains 'queryStringParameters' means it's being called from the API and parse it
    if "queryStringParameters" in event.keys():
        message = "Function is being called from an API Call, parsing it...\n"
        if event['queryStringParameters']:
            message = message + "\nAPI call contains Query Parameters...\n"
            event = event['queryStringParameters']
        else:
            event = {}
            message = message + "\nAPI call does NOT contains Query Parameters...\n"
    else:
        message = "Function is NOT being called from an API Call, not parsing\n"

    # If the event contains 'Records' means it's being called from an S3 update
    if "Records" in event.keys():
        message = message + "\nFunction is being called from an AWS Event trigger, parsing it...\n"
        unparsedEvent = event

        # Parse the AWS Event message
        try:
            event = PythonFunctions.parseAWSEventTrigger(event, 'defaultConfig.yml')
        except Exception as err:
            message = message + "\nAWS Event call is wrong/wrongly parsed. Error:\n\n" + traceback.format_exc()
            message = message + "\n\nAWS Event received:\n\n"
            message = message + PythonFunctions.turnDictToPrettyStr(unparsedEvent)
            response['body'] = message
            print(message)
            return response
    else:
        message = message + "\nFunction is NOT being called from an AWS Event trigger, not parsing\n"

    # Check that all the mandatory parameters are in
    if "ecommerce_id" not in event.keys() or "lambda_key" not in event.keys():
        message = message + "\nWrong use of parameters. Mandatory:"
        message = message + "\n\tLambda API Key { 'lambda_key' : [ ALPHANUMERIC ] }"
        message = message + "\n\tEcommerce-ID { 'ecommerce_id' : [ INTEGER ] }\n"
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

    # Mandatory Params
    PythonFunctions.printTitle("REPLACING CONFIG FILE VALUE [{}] WITH [{}]" \
        .format(configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id']))
    configFile = PythonFunctions.replaceAllInDict(configFile, configFile['shop']['properties']['ecommerce_id'], event['ecommerce_id'])

    # Optional Params
    if "mode" not in event.keys(): event['mode'] = "lambda"

    # Final configuration file
    PythonFunctions.printTitleInfo("AWS CREDS", configFile['aws'])
    PythonFunctions.printTitleInfo("SHOP DEFAULT CONFIG", configFile['shop'])

    # Call the creation function and analyze the result
    creationResult = FargateFunctions.compileS3Phar(configFile, event['mode'])
    if creationResult['success']:
        response['statusCode'] = 200
        response['body'] = "Shop with Ecommerce-ID [{}] compiled and uploaded a brand new S3 Phar file successfully".format(event['ecommerce_id'])
    else:
        response['body'] = "Shop with Ecommerce-ID [{}] Phar file could not be compiled and/or uploaded to S3. Reason: {}". \
            format(event['ecommerce_id'], creationResult['error'])

    print("\n" + str(response))
    return response

# Local Function runner
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Please introduce what operation to perform [CREATE/DELETE/UPDATE/REPO] and the ecommerce_id [INTEGER] (optional)\n")
    if len(sys.argv) > 3:
        print("Too many arguments. Please introduce what operation to perform [CREATE/DELETE/UPDATE] and the ecommerce_id [INTEGER] (optional)\n")
    else:
        if len(sys.argv) == 2:
            ecommerce_id = "9"
            print("\nUsing default Shop ecommerce_id [{}]\n".format(ecommerce_id))
        if len(sys.argv) == 3:
            ecommerce_id = sys.argv[2]
            print("\nUsing specified Shop ecommerce_id [{}]\n".format(ecommerce_id))
        if "create" in sys.argv[1].lower():
            createShop({ "lambda_key": "YYYYYYYYYYYYYYYYYYYYYYYYYY", "ecommerce_id": ecommerce_id }, "")
        elif "delete" in sys.argv[1].lower():
            deleteShop({ "lambda_key": "YYYYYYYYYYYYYYYYYYYYYYYYYY", "ecommerce_id": ecommerce_id }, "")
        elif "compile" in sys.argv[1].lower():
            compileS3Phar({ "lambda_key": "YYYYYYYYYYYYYYYYYYYYYYYYYY", "ecommerce_id": ecommerce_id }, "")
        elif "update" in sys.argv[1].lower():
            updateShop({ "lambda_key": "YYYYYYYYYYYYYYYYYYYYYYYYYY", "ecommerce_id": ecommerce_id, "force_update": True }, "")
        else:
            print("Could not recognize operation type. Please use [CREATE/DELETE/UPDATE/REPO]\n")
