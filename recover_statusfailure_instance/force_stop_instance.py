import json
import boto3
import time
import datetime
import os
import logging
from trigger_sns import trigger_sns_topic

recovery_success_sns_notify_topic_name=os.environ['SNS_FORCESTOP_SUCCESS_TOPIC']
recovery_failure_sns_notify_topic_name=os.environ['SNS_FORCESTOP_FAILURE_TOPIC']
region=os.environ['REGION']
pending_in_minutes=3


def lambda_handler(event, context):
    message = event['Records'][0]['Sns']['Message']
    json_msg_obj=json.loads(message) 
    instance_id=json_msg_obj['InstanceId'] 
    instance_status=json_msg_obj['Status'] 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.debug("main.lambda_handler : Incoming event is \n {}".format(event))

    logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state".format(instance_id, instance_status))

    client_sns = boto3.client('sns', region_name=region)
    client=boto3.client('ec2')
    stop_instance_response=client.stop_instances(
        InstanceIds=[instance_id]
        )
    ec2_waiter=client.get_waiter('instance_stopped')

    ec2_waiter.wait(
        InstanceIds=[instance_id]
    )
    response=client.describe_instances(
        InstanceIds=[instance_id]
        )
    while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'running' :
        logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))
        time.sleep(2)
        response=client.describe_instances(
           InstanceIds=[instance_id]
            )

    logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

    if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':

        start_instance_response=client.start_instances(
            InstanceIds=[instance_id]
            )

        time.sleep(2)
        endTime = datetime.datetime.now() + datetime.timedelta(minutes=pending_in_minutes)

        response=client.describe_instances(
            InstanceIds=[instance_id]
            )
        logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

        while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'pending':

            time.sleep(1)
            response=client.describe_instances(
                InstanceIds=[instance_id]
                )
            logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state". \
                format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))


            if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'running':
                time.sleep(3)
                logger.info("main.lambda_handler : Instance \"{}\" is in \"{}\" state".format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

                current_instance_status_details={
                    "InstanceId": instance_id, 
                    "Status": response['Reservations'][0]['Instances'][0]['State']['Name'],
                    "Message": "Instance is operating normally." 
                    }

                topic_response=client_sns.create_topic(
                    Name=recovery_success_sns_notify_topic_name
                    )

                topic_arn=topic_response['TopicArn']
                mail_subject='Successfully restarted, Instance '+str(instance_id)+' is operating normally now.'
                trigger_sns_response=trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject)
                logging.info(trigger_sns_response)
                break

            elif datetime.datetime.now() >= endTime:
                logger.info("main.lambda_handler : Instance \"{}\" is still in \"{}\"  \
                    state, it might have launch issue please launch it manually" \
                    .format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

                current_instance_status_details={
                    "InstanceId": instance_id, 
                    "Status": response['Reservations'][0]['Instances'][0]['State']['Name'],
                    "Message": "Unable to start instance, Please do necessary action manually" 
                    
                }

                topic_response=client_sns.create_topic(
                    Name=recovery_failure_sns_notify_topic_name
                    )                        
                topic_arn=topic_response['TopicArn']
                mail_subject='Unable to start the instance ' \
                        +str(instance_id)+', Instance is on ' \
                        +str(response['Reservations'][0]['Instances'][0]['State']['Name']) \
                        +'state only since long time'
                trigger_sns_response=trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject)
                logging.info(trigger_sns_response)
                break

            while response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopping':
                time.sleep(1)
                response=client.describe_instances(
                    InstanceIds=[instance_id]
                    )
                if response['Reservations'][0]['Instances'][0]['State']['Name'] == 'stopped':
                    logger.info("main.lambda_handler : Instance \"{}\" went to \"{}\" state" \
                        .format(instance_id, response['Reservations'][0]['Instances'][0]['State']['Name']))

                    current_instance_status_details={"InstanceId": instance_id, \
                        "Status": response['Reservations'][0]['Instances'][0]['State']['Name'], \
                        "Message": "Instance went to stopped state, Instance is having issues to start. Please do necessary action to function normally" }
                    topic_response=client_sns.create_topic(
                        Name=recovery_failure_sns_notify_topic_name
                        )
                    topic_arn=topic_response['TopicArn']
                    mail_subject='Instance '+str(instance_id)+ \
                            'went to'+str(response['Reservations'][0]['Instances'][0]['State']['Name'])+ \
                            ' state again, Having issues to launch'
                    trigger_sns_response=trigger_sns_topic(topic_arn,current_instance_status_details,mail_subject)
                    logging.info(trigger_sns_response)
                    break