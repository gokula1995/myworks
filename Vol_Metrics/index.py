import os
import json
import requests
import subprocess
import sys
import csv
from ses_email import send_mail
import concurrent.futures
import time
from threading import Timer


environment=os.environ.get('ENVIRONMENT')
r=requests.get('<URL to get the list of hosts>'+environment)
get_playout_list=r.json()

command_output_lists=[]
host_name_list=[]
account_name_list=[]
feed_name_list=[]
command_list=[]
for item in get_playout_list[environment]:
    sub_domain=item['account']
    headend_host=item['headend']

    host_name_list.append(sub_domain+'_'+headend_host)
    account_name_list.append(item['account'])
    feed_name_list.append(item['feed'])

    command_list.append("df -hP /mnt | awk '{print $2}' |tail -1|sed 's/%$//g' ; \
        df -hP /mnt | awk '{print $3}' |tail -1|sed 's/%$//g' ; \
        df -hP /mnt | awk '{print $4}' |tail -1|sed 's/%$//g' ; \
        df -hP /mnt | awk '{print $5}' |tail -1|sed 's/%$%//g' ; \
        curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | grep -oP '(?<=\"accountId\" : \")[^\"]*(?=\")' ; \
        curl http://169.254.169.254/latest/meta-data/instance-id; echo""; \
        curl -s http://169.254.169.254/latest/dynamic/instance-identity/document| grep region | awk -F \\\" '{print $4}'")

def ssh_exec_command(account_name, feed_name, host_name, command):

    try:
        kill = lambda process: process.kill()
        disk_size_output = subprocess.Popen(["ssh", host_name, command],
                                shell=False,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE
                            )
        my_timer = Timer(20, kill, [disk_size_output])
        my_timer.start()
        result = disk_size_output.stdout.readlines()
        result.insert(0, account_name)
        result.insert(1, feed_name)
        result.insert(2,host_name)
        if result == []:
            error = disk_size_output.stderr.readlines()
            print >>sys.stderr, "ERROR: %s" % error
        else:
            print(result)
            result_dict={
                "Account": str(result[0]),
                "Feed": str(result[1]),
                "PlayerName": str(result[2]),
                "TotalDiskSize": str(result[3].strip("\n")), 
                "Used": str(result[4].strip("\n")),
                "Available": str(result[5].strip("\n")),
                "Used%": str(result[6].strip("\n"))
            }
            try:
                AWSAccountID = {"AWSAccountID":str(result[7].strip("\n"))}
            except: 
                AWSAccountID={"AWSAccountID":"Not Available"}
            result_dict.update(AWSAccountID)
            try:
                InstanceID = {"InstanceID":str(result[8].strip("\n"))}
            except: 
                InstanceID={"InstanceID":"Not Available"}
            result_dict.update(InstanceID)
            try:
                Region = {"Region":str(result[9].strip("\n"))}
            except: 
                Region={"Region":"Not Available"}
            result_dict.update(Region)
            return result_dict
    except Exception as e:
        # logging.error(traceback.format_exc())
        print(e)
        result_dict={

                "Account": str(result[0]),
                "Feed": str(result[1]),
                "PlayerName": str(result[2]),
                "TotalDiskSize": "Not Available", 
                "Used": "Not Available",
                "Available": "Not Available",
                "Used%": "Not Available",
                "AWSAccountID": "Not Available",
                "InstanceID": "Not Available",
                "Region": "Not Available"
        }
        return result_dict
    
with concurrent.futures.ThreadPoolExecutor(5) as executor:
    results = executor.map(ssh_exec_command, account_name_list, feed_name_list, host_name_list, command_list)
    output_list=list(results)
    output_list_sorted = sorted(output_list, key = lambda i: i['Used%'], reverse=True) 
    print(output_list_sorted)

    fields = ['AWSAccountID', 'InstanceID', 'Region', 'Account', 'Feed', 'PlayerName', 'TotalDiskSize', 'Used', 'Available', 'Used%']
    file_name = "players_volume_report.csv"
    
    with open(file_name, 'w') as csvfile:

        # creating a csv dict writer object    
        writer = csv.DictWriter(csvfile, fieldnames=fields)

        # writing fields( field names)
        writer.writeheader()

        writer.writerows(output_list_sorted)

    msgsubject = "Players Volume Daily Report"
    msgtxt="Hi Team,\n Please find the below attachment for the today's player volume stats report"
    send_mail(msgsubject, msgtxt, file_name)