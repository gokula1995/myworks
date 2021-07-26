import os
import boto3
import json

region=os.environ['REGION']

client_sns = boto3.client('sns', region_name=region)

def trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject):
    response = client_sns.publish(
        TargetArn=topic_arn,
        Message=json.dumps({
            "default": json.dumps(current_instance_status_details)
        }),
        Subject=mail_subject,
        MessageStructure='json'
        )
    return response
