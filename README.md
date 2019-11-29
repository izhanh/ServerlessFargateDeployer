# SERVERLESS FARGATE DEPLOYER

Framework to deploy and manage Fargate containers in AWS using Lambda Functions and Serverless Fwk


## Prequisites

To deploy this you need:

- Python 3.5+
- Node & npm 8.0+
- Serverless Framework 1.5.1+
- Having an actual AWS account with ECS+Lambda privileges

## Recommended

- AWS Cli
- Virtualenv for Python3


## Usage

- Install all the Python dependencies (preferrably inside of a Virtualenv) using `pip install -r requirements.txt`
- Replace the AWS access key and secret values with your own AWS account
- Run `sls deploy`
