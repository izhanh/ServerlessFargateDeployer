import json
import time
import boto3
import traceback
import PythonFunctions

# CONSTANTS

config = {}
sshCredentials = {}
s3Client = boto3.client('s3')
ecsClient = boto3.client('ecs')
elbClient = boto3.client('elbv2')
cbClient = boto3.client('codebuild')
ccClient = boto3.client('codecommit')
lambdaClient = boto3.client('lambda')

# API MAIN FUNCTIONS

def createApi(configFile, apiEnvironment, mode):
	# Define the Config file and the AWS Credentials
	defineGlobalConfig(configFile[apiEnvironment])
	# Set the AWS creds if running locally
	if mode in "local": defineGlobalAWSClients(configFile['aws'])

	try:
		# Delete all the Rules related to the TG
		deleteRelatedRules()
		# Create the TG
		createTargetGroup()
		# Assign the TG to the ALB
		assignTgToAlb()
		# Create the Service
		createService()

		# Return 'True' if everything was successful
		return {"success": True, "error": None}

	except Exception as err:
		# Manage the possible exceptions and return 'False'
		excTrace = traceback.format_exc()
		if "idempotent" in excTrace: excTrace = "Service [{}] already exists!".format(config['service']['name'])
		if "Draining" in excTrace: excTrace = "Service [{}] is still being deleted".format(config['service']['name'])
		if "target group with the same name" in excTrace: excTrace = "Target Group [{}] already exists!".format(config['target_group']['name'])
		printTitleInfo("API ENVIONMENT [{}] COULD NOT BE CREATED. REASON:".format(apiEnvironment), excTrace)

		return { "success": False, "error": excTrace }

def deleteApi(configFile, apiEnvironment, mode):
	# Define the Config file and the AWS Credentials
	defineGlobalConfig(configFile[apiEnvironment])
	# Set the AWS creds if running locally
	if mode in "local": defineGlobalAWSClients(configFile['aws'])

	try:
		# Delete all the Rules related to the TG
		deleteRelatedRules()
		# Once the rules are gone, we can delete now the TG itself
		deleteTargetGroup()
		# Time to delete the Service
		deleteService()

		return {"success": True, "error": None}

	except Exception as err:
		# Manage the possible exceptions and return 'False'
		excTrace = traceback.format_exc()
		if "Service" in excTrace and "not found" in excTrace: excTrace = "Service [{}] was already deleted".format(config['service']['name'])
		if "Draining" in excTrace: excTrace = "Service [{}] is still being deleted".format(config['service']['name'])
		if "currently in use" in excTrace:
			excTrace = "Target Group [{}] cannot be deleted because is currently in use by other rule".format(config['target_group']['name'])
		printTitleInfo("API [{}] COULD NOT BE DELETED. REASON:".format(apiEnvironment), excTrace)

		return { "success": False, "error": excTrace }

# SHOP MAIN FUNCTIONS

def updateShops(configFile, forceUpdate, mode):
	# Define the Config file and the AWS Credentials
	defineGlobalConfig(configFile['shop'])
	# Define the SSH Credentials
	defineSSHCredentials(configFile['credentials'])
	# Set the AWS creds if running locally
	if mode in "local": defineGlobalAWSClients(configFile['aws'])

	try:
		# Update the Phars in the Fargate containers
		updateShopPhars(forceUpdate)

		# Return 'True' if everything was successful
		return { "success": True, "error": None }

	except Exception as err:
		# Manage the possible exceptions and return 'False'
		excTrace = traceback.format_exc()
		if "cannot be empty" in excTrace: excTrace = "Tasks must exist to be updated! Task [{}] does not exist!".format(config['task']['family'])

		if "all" in config['properties']['ecommerce_id']:
			printTitleInfo("ALL SHOPS [{}] INSTANCES COULD NOT BE UPDATED. REASON:".format(config['properties']['ecommerce_id']), excTrace)
		else:
			printTitleInfo("SHOP INSTANCES OF THE ECOMMERCE-ID [{}] COULD NOT BE UPDATED. REASON:".format(config['properties']['ecommerce_id']), excTrace)
		return { "success": False, "error": excTrace }

def createShop(configFile, mode):
	# Define the Config file and the AWS Credentials
	defineGlobalConfig(configFile['shop'])
	# Define the SSH Credentials
	defineSSHCredentials(configFile['credentials'])
	# Set the AWS creds if running locally
	if mode in "local": defineGlobalAWSClients(configFile['aws'])

	# If the value in [ecommerce_id], we create an array of shops to deploy and execute as many lambdas as necessary
	if "," in config['properties']['ecommerce_id']:
		shopsToDeploy = config['properties']['ecommerce_id'].split(",")
		printTitleInfo("CREATING ALL THE SHOPS IN THE LIST", shopsToDeploy)

		failedShops = []
		for shop in shopsToDeploy:
			lambdaPayload = {
    			"mode": mode,
				"ecommerce_id": shop,
    			"tasks_cpu": config['task']['cpu'],
    			"tasks_memory": config['task']['memory'],
    			"tasks_amount": config['task']['amount'],
    			"lambda_key": config['lambda']['api_key'],
    			"sdk_version": config['properties']['sdk_version'],
    			"fwk_version": config['properties']['fwk_version'],
    			"shop_autoupdate": config['properties']['shop_autoupdate'],
    			"ecommerce_version": config['properties']['ecommerce_version']
			}

			updateResponse = lambdaClient.invoke(FunctionName = config['lambda']['create_shop_function'], InvocationType = 'Event',
				Payload = PythonFunctions.byteEncondeDict(lambdaPayload))

			if "200" in str(updateResponse) or "202" in str(updateResponse):
				printSubTitle("Lambda [{}] successfully invoked for creating shop [{}]".format(config['lambda']['create_shop_function'], shop))
			else:
				failedShops = []
				printSubTitle("Lambda [{}] failed to invoke for creating shop [{}]".format(config['lambda']['create_shop_function'], shop))

		if len(failedShops) > 0:
			returnDict = { "success": False,
				"error": "Could not create all listed shops with function [{}]. Failed Shops:\n{}" \
					.format(config['lambda']['create_shop_function'], failedShops) }

			return returnDict

	# If not, we create the specified Shop in ['ecommerce_id']	
	else:
		try:
			# Create CodeCommit repo if it doesn't exist already
			createCodeCommitRepo()
			# If there is no Bucket folder for the shop, create it
			createS3Folder()
			# Delete all the Rules related to the TG
			deleteRelatedRules()
			# Get the base shop definition and replace placeholders, then upload the new TD
			uploadNewTaskDefinition()
			# Create the TG
			createTargetGroup()
			# Assign the TG to the ALB
			assignTgToAlb()
			# Create the Service
			createService()

		except Exception as err:
			# Manage the possible exceptions and return 'False'
			excTrace = traceback.format_exc()
			if "idempotent" in excTrace: excTrace = "Service [{}] already exists!".format(config['service']['name'])
			if "Draining" in excTrace: excTrace = "Service [{}] is still being deleted".format(config['service']['name'])

			printTitleInfo("SHOP [{}] COULD NOT BE CREATED. REASON:".format(config['properties']['ecommerce_id']), excTrace)
			return { "success": False, "error": excTrace }

	# Return 'True' if everything was successful
	return { "success": True, "error": None }

def deleteShop(configFile, mode):
	# Define the Config file and the AWS Credentials
	defineGlobalConfig(configFile['shop'])
	# Set the AWS creds if running locally
	if mode in "local": defineGlobalAWSClients(configFile['aws'])

	# If the value in [ecommerce_id] is 'ALL' or an array, we delete a list of shops and execute as many lambdas as necessary async
	if "," in config['properties']['ecommerce_id'] or "all" in config['properties']['ecommerce_id'] or "ALL" in config['properties']['ecommerce_id']:
		if "," in config['properties']['ecommerce_id']:
			shopsToDeploy = config['properties']['ecommerce_id'].split(",")
		else:
			shopsToDeploy = PythonFunctions.removeListFromOtherList(listAllServices(), config['multiple_operations']['shops_to_save'])

		printTitleInfo("DELETING ALL THE SHOPS IN THE LIST", shopsToDeploy)
		# Excluding the Shops in the reserved list
		if "all" in config['properties']['ecommerce_id'] or "ALL" in config['properties']['ecommerce_id']:
			printSubTitle("Saving reserved Shops: {}".format(config['multiple_operations']['shops_to_save']))

		failedShops = []
		for shop in shopsToDeploy:
			lambdaPayload = { "mode": mode,	"ecommerce_id": shop, "lambda_key": config['lambda']['api_key']	}

			updateResponse = lambdaClient.invoke(FunctionName = config['lambda']['delete_shop_function'], InvocationType = 'Event',
				Payload = PythonFunctions.byteEncondeDict(lambdaPayload))

			if "200" in str(updateResponse) or "202" in str(updateResponse):
				printSubTitle("Lambda [{}] successfully invoked for creating shop [{}]".format(config['lambda']['delete_shop_function'], shop))
			else:
				failedShops = []
				printSubTitle("Lambda [{}] failed to invoke for creating shop [{}]".format(config['lambda']['delete_shop_function'], shop))

		if len(failedShops) > 0:
			returnDict = { "success": False,
				"error": "Could not delete all listed shops with function [{}]. Failed Shops:\n{}" \
					.format(config['lambda']['delete_shop_function'], failedShops) }

			return returnDict

	# If not, we delete the specified Shop in ['ecommerce_id']	
	else:
		try:
			# Delete the CodeCommit repo
			deleteCodeCommitRepo()
			# Delete the S3 Folders of the Shop
			deleteS3Folder()
			# Delete all the Rules related to the TG
			deleteRelatedRules()
			# Once the rules are gone, we can delete now the TG itself
			deleteTargetGroup()
			# Time to delete the Service
			deleteService()
			# Finally delete the Task Definition
			clearShopPreviousTaskDefinitions()

		except Exception as err:
			# Manage the possible exceptions and return 'False'
			excTrace = traceback.format_exc()
			if "Draining" in excTrace: excTrace = "Service [{}] is still being deleted".format(config['service']['name'])
			if "currently in use" in excTrace:
				excTrace = "Target Group [{}] cannot be deleted because is currently in use by other rule".format(config['target_group']['name'])
			printTitleInfo("SHOP [{}] COULD NOT BE DELETED. REASON:".format(config['properties']['ecommerce_id']), excTrace)

			return { "success": False, "error": excTrace }

	# Return 'True' if everything was successful
	return { "success": True, "error": None }

def compileS3Phar(configFile, mode):
	# Define the Config file and the AWS Credentials
	defineGlobalConfig(configFile['shop'])
	# Define the Credentials
	defineSSHCredentials(configFile['credentials'])
	# Set the AWS creds if running locally
	if mode in "local": defineGlobalAWSClients(configFile['aws'])

	try:
		# Create Repo from the Base Repo
		executePharCompilerBuilder()

		return {"success": True, "error": None}

	except Exception as err:
		# Manage the possible exceptions and return 'False'
		excTrace = traceback.format_exc()
		if "already exists" in excTrace:
			excTrace = "CodeCommit Repository [{}] already exists!".format(config['properties']['ecommerce_id'])
		printTitleInfo("SHOP [{}] COULD NOT BE DELETED. REASON:".format(config['properties']['ecommerce_id']), excTrace)

		return { "success": False, "error": excTrace }

# GLOBAL VARS DEFINITIONS

def printTitle(title):
	PythonFunctions.printTitle(title)

def printSubTitle(subTitle):
	PythonFunctions.printSubTitle(subTitle)

def printTitleInfo(title, info):
	PythonFunctions.printTitleInfo(title, info)

def defineGlobalConfig(configFile):
	global config
	config = configFile

def defineSSHCredentials(configCreds):
	global sshCredentials
	sshCredentials = configCreds

def defineGlobalAWSClients(awsCreds):
	global ccClient
	global cbClient
	global s3Client
	global ecsClient
	global elbClient
	global lambdaClient

	s3Client = PythonFunctions.getAWSClient('s3', awsCreds)
	ecsClient = PythonFunctions.getAWSClient('ecs', awsCreds)
	elbClient = PythonFunctions.getAWSClient('elbv2', awsCreds)
	cbClient = PythonFunctions.getAWSClient('codebuild', awsCreds)
	ccClient = PythonFunctions.getAWSClient('codecommit', awsCreds)
	lambdaClient = PythonFunctions.getAWSClient('lambda', awsCreds)

	printTitle("GENERATED AWS CLIENTS WITH LOCAL CREDENTIALS")

# CODEBUILD FUNCTIONS

def executePharCompilerBuilder():
	# Create the Repo empty
	printTitle("EXECUTING CODEBUILD BUILDER FOR COMPILING THE SHOP [{}] PHAR FILE".format(config['properties']['ecommerce_id']))

	# Fill the empty Repo with the Base Shop
	buildRunResponse = cbClient.start_build(projectName = config['codebuild']['compile_phar_builder'], environmentVariablesOverride = [
		{ 'name': 'ECOMMERCE_ID', 'value': config['properties']['ecommerce_id'], 'type': 'PLAINTEXT' }])['build']

	printTitleInfo("PHAR COMPILER BUILDER EXECUTED SUCCESSFULLY FOR SHOP [{}]".format(config['properties']['ecommerce_id']), buildRunResponse)

# CODECOMMIT FUNCTIONS

def createCodeCommitRepo():
	# Check if the Repository already exists
	printTitle("CREATING CODECOMMIT REPO FOR THE SHOP [{}] IF IT DOESN'T EXIST ALREADY".format(config['properties']['ecommerce_id']))

	ccRepos = []
	ccResponse = ccClient.list_repositories()['repositories']
	for ccRepo in ccResponse: ccRepos.append(ccRepo['repositoryName'])
	printTitleInfo("LIST OF CODECOMMIT REPOS IN THE REGION [{}]".format(config['properties']['aws_region']), ccRepos)
	if config['properties']['ecommerce_id'] in ccRepos:
		printSubTitle("Shop E-commerce [{}] has a CodeCommit Repo already".format(config['properties']['ecommerce_id']))
		return

	# If the Repo does not exist, invoke a Lambda function that creates it and clones the data from the default repo 'base-shop-php'
	printSubTitle("Shop E-commerce [{}] has NOT a CodeCommit Repo, creating it asynchronously...".format(config['properties']['ecommerce_id']))
	createAndCopyRepoFromBase()

def deleteCodeCommitRepo():
	# Delete the CodeCommit Repo
	printTitle("DELETING CODECOMMIT REPO FOR THE SHOP [{}]".format(config['properties']['ecommerce_id']))

	# Delete the repository trigger (this is done 'putting' an empty list of trigger)
	printTitle("REMOVING CODECOMMIT TRIGGER FOR LAMBDA [{}]".format(config['lambda']['compile_phar_function']))
	try:
		triggerResponse = ccClient.put_repository_triggers(repositoryName = config['properties']['ecommerce_id'], triggers=[])
		printTitleInfo("CODECOMMIT TRIGGER FOR LAMBDA [{}] REMOVED SUCCESSFULLY".format(config['lambda']['compile_phar_function']), triggerResponse)
	except:
		printTitle("CODECOMMIT TRIGGER FOR LAMBDA [{}] DOES NOT EXIST".format(config['lambda']['compile_phar_function']))

	try:
		ccClient.delete_repository(repositoryName = config['properties']['ecommerce_id'])
	except:
		printSubTitle("Shop [{}] CodeCommit Repo doesn't exist or was already deleted".format(config['properties']['ecommerce_id']))

	# Remove the Lambda Permission generated with this Repo
	printTitle("REMOVING CODECOMMIT PERMISSION FOR LAMBDA [{}]".format(config['lambda']['compile_phar_function']))

	try:
		permissionResponse = lambdaClient.remove_permission(FunctionName = config['lambda']['compile_phar_function'], \
			StatementId = config['properties']['ecommerce_id'])
		printTitleInfo("CODECOMMIT PERMISSION FOR LAMBDA [{}] REMOVED SUCCESSFULLY".format(config['lambda']['compile_phar_function']), \
			permissionResponse)
	except:
		printTitle("CODECOMMIT PERMISSION FOR LAMBDA [{}] DOES NOT EXIST".format(config['lambda']['compile_phar_function']))

def createAndCopyRepoFromBase():
	# Create the Repo empty
	printTitle("CREATING CODECOMMIT REPO FOR THE SHOP [{}]".format(config['properties']['ecommerce_id']))
	creationReponse = ccClient.create_repository(repositoryName = config['properties']['ecommerce_id'],
	    repositoryDescription = "CodeCommit repo for the eCommerce Shop [{}]".format(config['properties']['ecommerce_id']))['repositoryMetadata']

	printTitleInfo("CODECOMMIT REPO CREATED SUCCESSFULLY FOR SHOP [{}]".format(config['properties']['ecommerce_id']), creationReponse)

	# Setting the Trigger to execute the Phar Compiler anytime the CodeCommit repo is altered
	printTitle("CREATING CODECOMMIT REPO [{}] TRIGGER FOR FUNCTION [{}]". \
		format(config['properties']['ecommerce_id'], config['lambda']['compile_phar_function']))

	triggerName = "{}_{}_repository_trigger".format(config['properties']['ecommerce_id'], config['properties']['ecommerce_version'])
	for lambdaFunction in lambdaClient.list_functions()['Functions']:
		if config['lambda']['compile_phar_function'] in lambdaFunction['FunctionName']: lambdaPharCompilerArn = lambdaFunction['FunctionArn']
	if lambdaPharCompilerArn is None: raise Exception("COULD NOT FIND ANY LAMBDA FUNCTION WITH NAME [{}]". \
		format(config['lambda']['compile_phar_function']))
	payload = json.dumps({ "lambda_key": config['lambda']['api_key'], "ecommerce_id": config['properties']['ecommerce_id'] })
	repositoryArn = ccClient.get_repository(repositoryName = config['properties']['ecommerce_id'])['repositoryMetadata']['Arn']
	sourceAccount = repositoryArn.replace("arn:aws:codecommit:" + config['properties']['aws_region'] + ":", ""). \
		replace(":" + config['properties']['ecommerce_id'], "")

	codeCommitProperties = "AWS Account: [{}]".format(sourceAccount)
	codeCommitProperties = codeCommitProperties + "\nTrigger Name: [{}]".format(triggerName)
	codeCommitProperties = codeCommitProperties + "\nData Payload: [{}]".format(payload)
	codeCommitProperties = codeCommitProperties + "\nRepository Events to trigger: [all]"
	codeCommitProperties = codeCommitProperties + "\nRepository ARN: [{}]".format(repositoryArn)
	codeCommitProperties = codeCommitProperties + "\nBranches to trigger: [{}]".format(config['properties']['ecommerce_version'])
	codeCommitProperties = codeCommitProperties + "\nPhar Compiler Lambda ARN: [{}]".format(lambdaPharCompilerArn)
	codeCommitProperties = codeCommitProperties + "\nPhar Compiler Lambda Function: [{}]".format(config['lambda']['compile_phar_function'])
	printSubTitle(codeCommitProperties)

	# Set the Lambda Permissions so the CodeCommit trigger can actually invoke the Lambda
	permissionsResponse = lambdaClient.add_permission(FunctionName = config['lambda']['compile_phar_function'],
	    StatementId = config['properties']['ecommerce_id'],
	    Action = 'lambda:InvokeFunction',
    	Principal = 'codecommit.amazonaws.com',
	    SourceArn = repositoryArn,
	    SourceAccount = sourceAccount)

	# Create the trigger
	triggerResponse = ccClient.put_repository_triggers(repositoryName = config['properties']['ecommerce_id'],
	    triggers=[{'name': triggerName, 'destinationArn': lambdaPharCompilerArn, 'customData': payload,
	    	'branches': [config['properties']['ecommerce_version']], 'events': ['all']}])

	printTitleInfo("CODECOMMIT TRIGGER CREATED SUCCESSFULLY FOR REPO [{}]".format(config['properties']['ecommerce_id']), triggerResponse)

	# Fill the empty Repo with the Base Shop using a CodeBuild builder
	buildRunResponse = cbClient.start_build(projectName = config['codebuild']['create_repo_builder'], environmentVariablesOverride = [
		{ 'name': 'ECOMMERCE_ID', 'value': config['properties']['ecommerce_id'], 'type': 'PLAINTEXT' }])['build']

	printTitleInfo("CODECOMMIT REPO FILLED SUCCESSFULLY FOR SHOP [{}]".format(config['properties']['ecommerce_id']), buildRunResponse)

# S3 FOLDER FUNCTIONS

def createS3Folder():
	# Listing all the S3 buckets
	s3Buckets = []
	for s3Bucket in s3Client.list_buckets()['Buckets']: s3Buckets.append(s3Bucket['Name'])
	printTitleInfo("ALL THE S3 BUCKETS IN THE REGION [{}]".format(config['properties']['aws_region']), s3Buckets)

	# Create the S3 bucket for the shops if it doesn't exist
	if config['s3']['shops_bucket'] not in s3Buckets:
		printTitle("SHOP BUCKET [{}] DOES NOT EXIST IN THE REGION [{}], CREATING IT" \
			.format(config['s3']['shops_bucket'], config['properties']['aws_region']))

		s3Response = s3Client.create_bucket(ACL = 'authenticated-read',
		    Bucket = config['properties']['aws_region'],
		    CreateBucketConfiguration = { 'LocationConstraint': config['properties']['aws_region'] })

		printTitleInfo("SHOPS S3 BUCKET [{}] SUCCESSFULLY CREATED IN REGION [{}]" \
			.format(config['properties']['aws_region']), s3Response)
	else:
		printSubTitle("Bucket for Shops [{}] in S3 already existed in region [{}]" \
			.format(config['s3']['shops_bucket'], config['properties']['aws_region']))

	# Listing all the folders in the S3 folder in order to copy it or not
	printTitle("CREATING S3 BUCKET FOLDER FOR THE NEW SHOP [{}] IN THE BUCKET [{}]" \
		.format(config['properties']['ecommerce_id'], config['s3']['shops_bucket']))

	bucketFolders = []
	try:
		bucketFoldersDicts = s3Client.list_objects(Bucket = config['s3']['shops_bucket'], Delimiter = '/')['CommonPrefixes']
		for bucketFolderDict in bucketFoldersDicts: bucketFolders.append(bucketFolderDict['Prefix'].replace("/", ""))
	except:
		pass

	printTitleInfo("EXISTING S3 SHOP FOLDERS IN BUCKET [{}]".format(config['s3']['shops_bucket']), bucketFolders)
	if config['properties']['ecommerce_id'] in bucketFolders:
		printSubTitle("Shop E-commerce [{}] has a PHARs folder already".format(config['properties']['ecommerce_id']))
		return

	# If the Folder does not exist, create it
	printSubTitle("Shop E-commerce [{}] doesn't have a PHARs folder, creating it from Base Shop folder [{}]" \
		.format(config['properties']['ecommerce_id'], config['s3']['base_shop_bucket']))

	# Copying the Base Shop folder (last version of the PHAR only) into the new S3 folder
	copy_source_master = { 'Bucket': config['s3']['base_shop_bucket'], 'Key': "master/index_latest.phar" }
	copy_source_integration = { 'Bucket': config['s3']['base_shop_bucket'], 'Key': "integration/index_latest.phar" }
	s3Client.copy(copy_source_master, config['s3']['shops_bucket'], config['properties']['ecommerce_id'] + "/master/index_latest.phar")
	s3Client.copy(copy_source_integration, config['s3']['shops_bucket'], config['properties']['ecommerce_id'] + "/integration/index_latest.phar")

def deleteS3Folder():
	# Listing all the folders in the S3 folder in order to copy it or not
	printTitle("DELETING S3 FOLDER OF THE SHOP [{}] IN THE BUCKET [{}]" \
		.format(config['properties']['ecommerce_id'], config['s3']['shops_bucket']))

	# Delete all the files in the S3 Folder of the E-commerceID
	try:
		filesToDelete = []
		allShopFiles = s3Client.list_objects(Bucket = config['s3']['shops_bucket'], Prefix = config['properties']['ecommerce_id'] + '/')['Contents']
		for file in allShopFiles: filesToDelete.append({ "Key": file['Key'] })
		s3Client.delete_objects(Bucket = config['s3']['shops_bucket'], Delete = { 'Objects': filesToDelete,'Quiet': False })
		printSubTitle("Shop [{}] Bucket folder successfully deleted".format(config['properties']['ecommerce_id']))
	except:
		printSubTitle("Shop [{}] Bucket folder doesn't exist or was already deleted".format(config['properties']['ecommerce_id']))

	bucketFolders = []
	try:
		bucketFoldersDicts = s3Client.list_objects(Bucket = config['s3']['shops_bucket'], Delimiter = '/')['CommonPrefixes']
		for bucketFolderDict in bucketFoldersDicts: bucketFolders.append(bucketFolderDict['Prefix'].replace("/", ""))
	except:
		pass

	printTitleInfo("REMAINING S3 SHOP FOLDERS IN BUCKET [{}]".format(config['s3']['shops_bucket']), bucketFolders)

# BALANCER FUNCTIONS

def findBalancerArn():
	# Search for a load balancer that matches the Balancer Name
	balancerArn = None
	for balancerInfo in elbClient.describe_load_balancers()['LoadBalancers']:
		if balancerInfo['LoadBalancerName'] in config['load_balancer']['name']:
			balancerArn = balancerInfo['LoadBalancerArn']
			printTitleInfo("FOUND LOAD BALANCER MATCHING NAME [" + config['load_balancer']['name'] + "]", balancerInfo)
			break

	# Raise exception if we find no match
	if balancerArn is None: raise Exception("COULD NOT FIND ANY ALB WITH NAME [{}]".format(config['load_balancer']['name']))
	return balancerArn

def findListenerArn(balancerArn):
	# Search for the Listener of the ALB that matches the intended port
	listenerArn = None
	for listenerInfo in elbClient.describe_listeners(LoadBalancerArn = balancerArn)['Listeners']:
		if listenerInfo['Port'] is config['load_balancer']['port']:
			listenerArn = listenerInfo['ListenerArn']
			printTitleInfo("FOUND LOAD BALANCER LISTENER MATCHING PORT [{}]".format(config['load_balancer']['port']), listenerInfo)
			break

	# Raise exception if we find none
	if listenerArn is None: raise Exception("COULD NOT FINT ANY LISTENER WITH PORT [{}]".format(config['load_balancer']['port']))
	return listenerArn

# RULE FUNCTIONS

def deleteRelatedRules():
	# Get the Listener ARN
	listenerArn = findListenerArn(findBalancerArn())
	printTitle("DELETING ALL RULES RELATED TO TG [{}] AND URL [{}]".format(config['target_group']['name'], config['properties']['url']))

	# Delete the rules that contain the Target Group as a destination
	for rule in describeAlbRules(listenerArn):
		# Check if the rule contains the TG
		if config['target_group']['name'] in str(rule) and config['properties']['url'] in str(rule):
			printSubTitle("Deleting rule [{}]".format(rule['RuleArn']))
			elbClient.delete_rule(RuleArn = rule['RuleArn'])

def findLowestFreePriorityRule(listenerArn):
	# Create a list with all the values of the priority rules
	priorityRules = []
	for rule in describeAlbRules(listenerArn):
		if rule['Priority'] not in "default": priorityRules.append(int(rule['Priority']))

	# Find the lowest still-free priority rule and assign it
	for prioRule in range(1, len(priorityRules) + 2):
		if prioRule not in priorityRules: return prioRule

def describeAlbRules(listenerArn):
	return elbClient.describe_rules(ListenerArn = listenerArn)['Rules']

def createRule(listenerArn, hostUrl, tgArn, rulePriority):
	createRuleResponse = elbClient.create_rule(ListenerArn = listenerArn,
		Conditions = [{
			"Field": "host-header",
			"Values": ["*{}*".format(hostUrl)]
		}],
		Actions = [{
			"Type": "forward",
			"TargetGroupArn": tgArn
		}],
		Priority = rulePriority)

	printTitleInfo("RULE CREATED SUCCESFULLY", createRuleResponse)

# SERVICE FUNCTIONS

def deleteService():
	try:
		deleteServiceResponse = ecsClient.delete_service(cluster = config['service']['cluster_name'],
			service = config['service']['name'], force = True)
		printTitle("SERVICE [{}] SUCCESFULLY DELETED".format(config['service']['name']))
	except:
		printTitle("SERVICE [{}] DOESN'T EXIST OR WAS ALREADY DELETED".format(config['service']['name']))

def createService():
	# Search for the TG Arn
	tgArn = elbClient.describe_target_groups(Names = [config['target_group']['name']])['TargetGroups'][0]['TargetGroupArn']

	createServiceResponse = ecsClient.create_service(cluster = config['service']['cluster_name'],
		serviceName = config['service']['name'],
		desiredCount = config['task']['amount'],
		taskDefinition = config['task']['family'],
		launchType = config['task']['launch_type'],
		loadBalancers = [{'targetGroupArn': tgArn, 'containerName': config['container']['name'], 'containerPort': config['container']['port']}],
		networkConfiguration = {"awsvpcConfiguration": {'subnets': config['service']['subnets'],
			"assignPublicIp": config['task']['public_ip'],
			"securityGroups": config['service']['security_group']}})['service']

	printTitleInfo("SERVICE [{}] CREATED SUCCESSFULLY".format(config['service']['name']), createServiceResponse)

def listAllServices():
	servicesList = []
	for service in ecsClient.list_services(cluster = config['service']['cluster_name'])['serviceArns']:
		servicesList.append(service.split("-")[len(service.split("-")) - 1])
	return servicesList

# TARGET GROUP FUNCTIONS

def deleteTargetGroup():
	# Delete the target group that has the name in the config file
	try:
		tgArn = elbClient.describe_target_groups(Names = [config['target_group']['name']])['TargetGroups'][0]['TargetGroupArn']
		deleteTgResponse = elbClient.delete_target_group(TargetGroupArn = tgArn)
		printTitle("TARGET GROUP [{}] SUCCESSFULLY DELETED".format(config['target_group']['name']))
	except Exception as err:
		excTrace = traceback.format_exc()
		# If the deletion failed because there aren't any TG with the name already, completely fine
		if "not found" in excTrace:
			printTitle("TARGET GROUP [{}] WAS ALREADY DELETED".format(config['target_group']['name']))
			return

		raise Exception("TARGET GROUP [{}] COULD NOT BE DELETED. REASON: {}".format(config['target_group']['name'], excTrace))

def createTargetGroup():
	printTitle("CREATING TARGET GROUP [" + config['target_group']['name'] + "]")

	createTgResponse = elbClient.create_target_group(Name = config['target_group']['name'],
	    Port = config['target_group']['port'],
	    VpcId = config['load_balancer']['vpc_id'],
	    Matcher = config['healthcheck']['matcher'],
	    Protocol = config['target_group']['protocol'],
	    HealthCheckPath = config['healthcheck']['path'],
	    HealthCheckPort = config['healthcheck']['port'],
	    TargetType = config['target_group']['target_type'],
	    HealthCheckProtocol = config['healthcheck']['protocol'],
	    HealthCheckTimeoutSeconds = config['healthcheck']['timeout'],
	    HealthCheckIntervalSeconds = config['healthcheck']['interval'],
	    HealthyThresholdCount = config['healthcheck']['healthy_threshold'],
	    UnhealthyThresholdCount = config['healthcheck']['unhealthy_threshold'])['TargetGroups'][0]

	# Wait for the TG created a max of 20s
	printSubTitle("Waiting for the TG [{}] to be available [Timeout = 20s]".format(config['target_group']['name']))
	iniTime = PythonFunctions.getCurrentTimeAsMilis()
	while PythonFunctions.checkElapsedTime(iniTime, 20):
		time.sleep(1)
		registeredTgs = elbClient.describe_target_groups()['TargetGroups']
		for registeredTg in registeredTgs:
			if config['target_group']['name'] in registeredTg['TargetGroupName']:
				printTitleInfo("TARGET GROUP [" + config['target_group']['name'] + "] CREATED SUCCESSFULLY", createTgResponse)
				time.sleep(1)
				return True

	# If the TG wasn't found after 20s we raise an exception
	raise Exception("Error: Could not find the created TG [{}] after 20s waiting".format(config['target_group']['name']))

def assignTgToAlb():
	# Search for the TG Arn
	tgArn = elbClient.describe_target_groups(Names = [config['target_group']['name']])['TargetGroups'][0]['TargetGroupArn']
	
	printTitle("ASSIGNING CREATED TG [" + config['target_group']['name'] + "] TO ALB: [" + config['load_balancer']['name'] + "]")

	# Find the Balancer and the Listener ARNs
	balancerArn = findBalancerArn()
	listenerArn = findListenerArn(balancerArn)

	# Create a Rule for the Target Group
	printTitle("CREATING A RULE INTO THE ALB [" + config['load_balancer']['name'] + "]")
	printSubTitle("Target Group ARN: [{}] Load Balancer ARN: [{}] Listener ARN: [{}]".format(tgArn, balancerArn, listenerArn))

	# Find the lowest free priority rule to assign
	lowestFreePriorityRule = findLowestFreePriorityRule(listenerArn)
	if lowestFreePriorityRule is None: raise Exception("COULD NOT FIND ANY HIGHEST RULE IN ALB [{}]".format(config['load_balancer']['name']))
	printTitle("FOUND HIGHEST FREE RULE PRIORITY [{}]".format(lowestFreePriorityRule))

	# Create the rule in the assigned priority
	createRule(listenerArn, config['properties']['url'], tgArn, lowestFreePriorityRule)

# SHOP FUNCTIONS

def updateShopPhars(forceUpdate):
	# Filter some of the shops or get them all
	if "all" in config['properties']['ecommerce_id'] or "ALL" in config['properties']['ecommerce_id']:
		# List all the taks in the Cluster
		tasksListResponse = ecsClient.list_tasks(cluster = config['service']['cluster_name'],
		    desiredStatus = 'RUNNING',
		    launchType = config['task']['launch_type'])['taskArns']
		printTitleInfo("LIST ALL TASKS IN THE CLUSTER [{}]".format(config['service']['cluster_name']), tasksListResponse)
	else:
		# List the taks in the Cluster that match the Task Definition
		tasksListResponse = ecsClient.list_tasks(cluster = config['service']['cluster_name'],
		    family = config['task']['family'],
		    desiredStatus = 'RUNNING')['taskArns']
		printTitleInfo("LIST OF TASKS IN THE CLUSTER [{}] WITH TD [{}]".format(config['service']['cluster_name'], \
			config['task']['family']), tasksListResponse)

	# Retrieve the IPs of every Fargate container
	tasksDescriptionsResponse = ecsClient.describe_tasks(cluster = config['service']['cluster_name'], tasks = tasksListResponse)['tasks']

	shopsToUpdate = []
	for taskDescription in tasksDescriptionsResponse:
		for container in taskDescription['containers']:
			for networkInterface in container['networkInterfaces']:
				ip = networkInterface['privateIpv4Address']
		shopsToUpdate.append({ "ecommerce_id": taskDescription['group'].replace("service:svc-", ""), "ip": ip, "force": forceUpdate })

	printTitleInfo("TASKS DESCRIPTIONS", shopsToUpdate)

	# Update the PHARs in every IP
	if "all" in config['properties']['ecommerce_id'] or "ALL" in config['properties']['ecommerce_id']:
		printTitle("UPDATING EVERY INSTANCE OF ALL SHOPS")

		updatedShops = []
		for shop in shopsToUpdate:
			# In case there are multiple instances of the same shop don't send the signal duplicated
			if shop['ecommerce_id'] in updatedShops: continue
			updatedShops.append(shop['ecommerce_id'])

			lambdaPayload = {
				"ecommerce_version": "all",
				"force_update": forceUpdate,
				"ecommerce_id": shop['ecommerce_id'],
				"lambda_key": config['lambda']['api_key']
			}

			updateResponse = lambdaClient.invoke(FunctionName = config['lambda']['update_shop_function'], InvocationType = 'Event',
				Payload = PythonFunctions.byteEncondeDict(lambdaPayload))

			if "200" in str(updateResponse) or "202" in str(updateResponse):
				printSubTitle("Lambda [{}] successfully invoked for updating shop [{}]".format(config['lambda']['update_shop_function'], shop['ecommerce_id']))
			else:
				printSubTitle("Lambda [{}] failed to invoke for updating shop [{}]".format(config['lambda']['update_shop_function'], shop['ecommerce_id']))

		return
	else:
		printTitle("UPDATING EVERY INSTANCE OF SHOP [{}]".format(config['properties']['ecommerce_id']))

	printSubTitle("Force mode: [{}]".format(forceUpdate))
	for shop in shopsToUpdate: updateShop(shop)

	# Multiprocessing DOES NOT work in Lambda
	#PythonFunctions.executeMultiprocessingFunctions(updateShop, shopsToUpdate, True)

def updateShop(shop):
	# If the auto-update in the shop is configured as 'false' the autoupdate won't be performed
	shopProperties = PythonFunctions.bytesToString(PythonFunctions.performSSHCommand(shop['ip'], sshCredentials['ssh_port'], \
		sshCredentials['ssh_user'], sshCredentials['ssh_pass'], ["cat", "/local/www/shop.properties"]))

	# Parse the AUTO_UPDATE value
	autoUpdate = PythonFunctions.parseKeyValueFromString(shopProperties, "AUTO_UPDATE")
	# Parse the ECOMMERCE_VERSION value
	ecommerce_version = PythonFunctions.parseKeyValueFromString(shopProperties, "ECOMMERCE_VERSION")

	# If the config version is "all", we update regardless of the version
	if config['properties']['ecommerce_version'] in "ALL" or config['properties']['ecommerce_version'] in "all":
		printSubTitle("Ecommerce version is set to [ALL], updating shop regardless of version")
	else:
		# If the version doesn't match, do not update
		if config['properties']['ecommerce_version'] not in ecommerce_version:
			printSubTitle("Shop: [{}] at [{}] version doesn't match the ECOMMERCE_VERSION [{}] vs [{}], not updating". \
				format(shop['ecommerce_id'], shop['ip'], ecommerce_version, config['properties']['ecommerce_version']))
			return
		else:
			printSubTitle("Shop: [{}] at [{}] version matches the ECOMMERCE_VERSION [{}], updating...". \
				format(shop['ecommerce_id'], shop['ip'], config['properties']['ecommerce_version']))
	
	# If 'Force == True' we force the update. If it's 'False', we check if the Shop has the AUTO-UPDATE option ON
	if "False" in str(shop['force']) or "false" in str(shop['force']):
		# If the auto-update in the shop is configured as 'false' the autoupdate won't be performed
		if "false" in autoUpdate:
			printSubTitle("Shop: [{}] at [{}] has the AUTO-UPDATE option DISABLED, not updating".format(shop['ecommerce_id'], shop['ip']))
			return
		else:
			printSubTitle("Shop: [{}] at [{}] has the AUTO-UPDATE option ENABLED, updating...".format(shop['ecommerce_id'], shop['ip']))
	else:
		printSubTitle("Force Update option is ENABLED, updating the Shop regardless")

	# Check the update file
	updateFileLines = PythonFunctions.bytesToString(PythonFunctions.performSSHCommand(shop['ip'], sshCredentials['ssh_port'], \
		sshCredentials['ssh_user'], sshCredentials['ssh_pass'], ["wc", "-l", "/local/www/shopUpdate.log"]))

	try:
		# Perform the update
		printSubTitle("Updating Shop: [{}] at [{}]".format(shop['ecommerce_id'], shop['ip']))
		PythonFunctions.performSSHCommand(shop['ip'], sshCredentials['ssh_port'], \
			sshCredentials['ssh_user'], sshCredentials['ssh_pass'], ["bash", "/local/downloadPhars.sh"])

		afterUpdateLines = PythonFunctions.bytesToString(PythonFunctions.performSSHCommand(shop['ip'], sshCredentials['ssh_port'], \
			sshCredentials['ssh_user'], sshCredentials['ssh_pass'], ["wc", "-l", "/local/www/shopUpdate.log"]))

		# Check if the update has been really performed
		if updateFileLines not in afterUpdateLines:
			printSubTitle("Shop: [{}] at [{}] update succeeded =)".format(shop['ecommerce_id'], shop['ip']))
		else:
			printSubTitle("Shop: [{}] at [{}] update failed =(. Reason: Should wasn't updated".format(shop['ecommerce_id'], shop['ip']))
	except Exception as err:
		printSubTitle("Shop: [{}] at [{}] update failed =(. Reason:\n{}".format(shop['ecommerce_id'], shop['ip'], traceback.format_exc()))

def clearShopPreviousTaskDefinitions():
	try:
		# List all regions arn
		tdList = ecsClient.list_task_definitions(familyPrefix = config['task']['family'])['taskDefinitionArns']
		printTitleInfo("EXISTING TD IN FAMILY [" + config['task']['family'] + "]", tdList)

		if len(tdList) < 1:
			print("\nThere are no previous revisions, returning...\n")
			return

		# Deregister previous task definition
		for clientArn in tdList: ecsClient.deregister_task_definition(taskDefinition = clientArn)

		printTitle("PREVIOUS TD REVISIONS SUCCESSFULY DEREGISTERED")

	except Exception as err:
		print("Could not delete previous revisions, reason: " + str(err))

def uploadNewTaskDefinition():
	# Get the base task definition and replace the placeholders
	newTaskDefinition = replacePlaceholders(getBaseShopTaskDefinition())

	# Clear previous revisions of the Task Definition
	clearShopPreviousTaskDefinitions()

	# Create the new task definition
	containerDefinitions = newTaskDefinition['containerDefinitions']
	printTitleInfo("NEW TASK DEFINITION", newTaskDefinition)
	printTitleInfo("REPLACED CONTAINER DEFINITION", containerDefinitions)

	printTitleInfo("TASK CONFIG", config['task'])

	ecsClient.register_task_definition(family = config['task']['family'],
	    cpu = config['task']['cpu'],
	    memory = config['task']['memory'],
	    containerDefinitions = containerDefinitions,
	    networkMode = newTaskDefinition['networkMode'],
	    executionRoleArn = newTaskDefinition['executionRoleArn'])

	printTitle("TASK DEFINITION [{}] SUCCESSFULY REGISTERED".format(config['task']['family']))

def replacePlaceholders(taskDifinition):
	# Replace the placeholders in the file
	replacedDict = PythonFunctions.replaceAllInDict(taskDifinition, config['task']['ecommerce_id_placeholder'], config['properties']['ecommerce_id'])
	replacedDict = PythonFunctions.replaceAllInDict(replacedDict, config['task']['sdk_version_placeholder'], config['properties']['sdk_version'])
	replacedDict = PythonFunctions.replaceAllInDict(replacedDict, config['task']['fwk_version_placeholder'], config['properties']['fwk_version'])
	replacedDict = PythonFunctions.replaceAllInDict(replacedDict, config['task']['ecommerce_version_placeholder'], config['properties']['ecommerce_version'])
	replacedDict = PythonFunctions.replaceAllInDict(replacedDict, config['task']['image_version_placeholder'], config['properties']['image_version'])
	replacedDict = PythonFunctions.replaceAllInDict(replacedDict, config['task']['shop_autoupdate_placeholder'], config['properties']['shop_autoupdate'])

	return replacedDict

def getBaseShopTaskDefinition():
	taskDefinition = ecsClient.describe_task_definition(taskDefinition = config['task']['base_task_family'])['taskDefinition']
	printTitleInfo("BASE TASK DEFINITION", taskDefinition)
	return taskDefinition
