import boto3
import requests
from datetime import datetime, timedelta
from requests.auth import HTTPDigestAuth
import logging
import json

# Create a custom logger
logger = logging.getLogger(__name__)

# Set the level of logger to DEBUG. This will capture all DEBUG & above level logs
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    public_ip = get_public_ip()

    update_atlas_whitelist(public_ip)

def get_public_ip():
    # Create a new session with Boto3
    session = boto3.Session()

    # Initialize the ECS client
    ecs = session.client('ecs')

    # Initialize the EC2 client
    ec2 = session.client('ec2')

    # Retrieve the running task ARNs for a particular service
    list_tasks_response = ecs.list_tasks(cluster="bsg-makeup-be", serviceName="bsg-makeup-be-lb-service")
    task_arns = list_tasks_response['taskArns']

    # Get public IP of the first running task
    for task_arn in task_arns:
        # Obtain information regarding the task
        describe_tasks_response = ecs.describe_tasks(cluster="bsg-makeup-be", tasks=[task_arn])

        # Obtain the network interface id from the task details
        eni_id = None
        for detail in describe_tasks_response['tasks'][0]['attachments'][0]['details']:
            if detail['name'] == 'networkInterfaceId':
                eni_id = detail['value']

        # Query the network interface for its public IP
        if eni_id is not None:
            network_interface = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])

            return network_interface["NetworkInterfaces"][0]["Association"]["PublicIp"]


def update_atlas_whitelist(ip: str):
    logger.debug('Inside update_atlas_whitelist function')

    # Define your private_key, public_key and project_id
    private_key = ''
    public_key = ''
    project_id = ''

    # Construct the
    base_url = "https://cloud.mongodb.com/api/atlas/v2/groups"
    url = f"{base_url}/{project_id}/accessList"

    # Get the current datetime in the required format
    now = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
    comment = f"EC2 {now}"

    # Construct the payload
    payload = [{"ipAddress": ip, "comment": comment}]
    payload = json.dumps(payload)

    # Construct the headers
    headers = {
        'Content-Type': "application/json",
        'Accept': "application/vnd.atlas.2023-01-01+json",
    }

    response = requests.post(url, data=payload, auth=HTTPDigestAuth(public_key, private_key), headers=headers)

    logger.debug(f'MongoDB Atlas API response: {response.text}')

    if response.status_code != 201:
        raise Exception("Failed to update MongoDB Atlas whitelist.")
