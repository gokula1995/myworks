# Auto Recovery Monitor Script

There are two lambda functions. One will start monitoring the ec2 instance whenever status check fails and other will get triggered based on the this lambda function status, means if instance is unable to recover automatically then this lambda function stops the instance forcefully and starts it.

Before creating the serverless stack, create new configuration like config.dev.yml and make changes according to it then run the below command.

```
sls deploy --stage dev --region us-east-1
```

Once the stack gets created, attach "<STATUS_CHECK_FAILED_SNS_TOPIC>" sns topic to ec2 instance which will trigger the lambda function.

# Sample Ec2 Status check failed Payload data in JSON Format
```sh
"{
  "AlarmName":"awsec2-<INSTANCE_ID>-High-Status-Check-Failed-Instance-",
  "AlarmDescription":"Reboot the instance if the instance status check failed",
  "AWSAccountId":"<ACCOUNT_ID>",
  "NewStateValue":"ALARM",
  "NewStateReason":"Threshold Crossed: 3 datapoints [1.0 (13/02/20 03:56:00), 1.0 (13/02/20 03:55:00), 1.0 (13/02/20 03:54:00)] were greater than or equal to the threshold (1.0).",
  "StateChangeTime":"2020-02-13T03:57:37.968+0000",
  "Region":"US East (N. Virginia)",
  "OldStateValue":"OK",
  "Trigger":{
    "MetricName":"StatusCheckFailed_Instance",
    "Namespace":"AWS/EC2",
    "StatisticType":"Statistic",
    "Statistic":"MAXIMUM",
    "Unit":null,
    "Dimensions":[
      {
        "value":"<INSTANCE_ID>",
        "name":"InstanceId"
        }
      ],
      "Period":60,
      "EvaluationPeriods":3,
      "ComparisonOperator":"GreaterThanOrEqualToThreshold",
      "Threshold":1.0,
      "TreatMissingData":"",
      "EvaluateLowSampleCountPercentile":""
      }
    }",
  "Timestamp" : "2020-02-13T03:57:38.045Z",
  "SignatureVersion" : "1",
  "Signature" : "",
  "SigningCertURL" : "",
  "UnsubscribeURL" : ""
}
```
