import json
import requests
import urllib3
from os import system
from datetime import datetime
from collections import OrderedDict
from encrypt import *
from collections import namedtuple

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def extract(a):
    """
    a - exact filename of the data to be extracted
    """
    with open(a,'r') as i:
        return(i.read())

def nxapi_cli(node, cmd, username, password, mode):
    '''
    a - filtered device detail in netmiko format
    b - filtered device detail with hostname
    c - filtered device command line
    d - file format of the log file
    '''
    timestamp = datetime.now().strftime("%d%b%Y")
    header = {'content-type':'application/json'}
    success = 0
    failed = 0
    failed_nodes = {}
    for i in node:
        url = 'https://' + i[0] + '/ins'
        try:
            wr_file = open( 'logs/' + i[1] + '_' + i[0] + '_' + timestamp + '.' + mode, 'w' )
            for j in cmd:
                if j[0] == mode:
                    payload = {
                        "ins_api":{
                        "version": "1.0",
                        "type": "cli_show_ascii",
                        "chunk": "0",
                        "sid": "1",
                        "input": j[1],
                        "output_format": "json"
                        }
                    }
                    response = requests.post(url, verify=False, timeout=10, data=json.dumps(payload), headers=header, auth=(username,password)).json()
                    output = response['ins_api']['outputs']['output']['body']
                    wr_file.write( j[1] + '\n' + output + '\n')
                    print (i[1] + ' ' + j[1] + ' - COMPLETED')
                    #print(response['ins_api']['outputs']['output']['body'])
                else:
                    pass
            wr_file.close()
            success += 1
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as z:
            wr_file = open( 'logs/' + i[1] + '_' + i[0] + '_' + timestamp + '.' + mode, 'w' )
            wr_file.write(str(z))
            wr_file.close()
            failed_nodes[failed] = i[1]
            failed += 1
    return (success, failed, failed_nodes)

if __name__ == '__main__':
    start_time = datetime.now()
    print('\n**************** S T A R T  O F  T H E  S C R I P T ****************\n')
    #Extract login credentials
    username = decrypt_message(extract('login_credentials.txt').split(',')[0].encode())
    password = decrypt_message(extract('login_credentials.txt').split(',')[1].encode())
    
    #temporary storage of the raw data of cli commands
    nxos_cmd_raw = extract('nxos_command_list.txt')
    #temporary storage of the raw data of the nodes database
    nxos_node_raw = extract('nxos_device_list.txt')
    
    #nxos parsed command lines
    nxos_cmd_list = [ i.split(',') for i in nxos_cmd_raw.splitlines() ]
    #nxos parsed node list
    nxos_node_list = [ i.split(' ') for i in nxos_node_raw.splitlines() ]
    
    #Zip the config files and move to archive folder
    system('zip -R $(echo cfg_backup_$(date +%d%b%Y)) logs/*.cfg && mv *.zip logs/archive/')
    #Zip the logs files and move to archive folder
    system('zip -R $(echo log_backup_$(date +%d%b%Y)) logs/*.log && mv *.zip logs/archive/')
    #Deletes all config and log files
    system('rm logs/*.cfg && rm logs/*.log')
    
    #nxapi call to device for config backup
    (cfg_success,cfg_failed, cfg_failed_nodes) = nxapi_cli(nxos_node_list, nxos_cmd_list, username, password, 'cfg')
    #nxapi call to device for config backup
    (log_success,log_failed, log_failed_nodes) = nxapi_cli(nxos_node_list, nxos_cmd_list, username, password, 'log')
    
    #Upload the config files to jump server thru linux bash scp
    system('scp -i ~/.ssh/id_rsa logs/*.cfg 192.168.190.24:/home/shared/')
    #Upload the log files to jump server thru linux bash scp
    system('scp -i ~/.ssh/id_rsa logs/*.log 192.168.190.24:/home/shared/')
    end_time = datetime.now()
    total_time = (end_time - start_time).seconds
    print('\n**************** E N D  O F  T H E  S C R I P T ****************\n')
    print('Successful Login : (' + str(cfg_success) + '/' + str(len(nxos_node_list)) + ') config backup')
    print('Successful Login : (' + str(log_success) + '/' + str(len(nxos_node_list)) + ') logs backup')
    print('Failed Login : (' + str(cfg_failed) + '/' + str(len(nxos_node_list)) + ') config backup')
    for i in range(len(cfg_failed_nodes)):
        print(cfg_failed_nodes[i])
    print('Failed Login : (' + str(log_failed) + '/' + str(len(nxos_node_list)) + ') logs backup')
    for i in range(len(log_failed_nodes)):
        print(cfg_failed_nodes[i])
    print('Start time : ' + start_time.strftime("%d %b %Y - %H:%M:%S"))
    print('End time : ' + end_time.strftime("%d %b %Y - %H:%M:%S"))
    print('Total time : ' + str(total_time//60) + ' minute/s and ' + str(total_time%60) + ' second/s')