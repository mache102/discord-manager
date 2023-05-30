import argparse
import configparser
import json
import logging
import os 
import ruamel.yaml
import time


from datetime import datetime, timezone
from api_depot import Canopy
from utils import add_one, format_timedelta

API_VERSION = 10
CONFIG_PATH = 'config.yaml'
RESULT_OPT_PATH = 'result_options.ini'

"""
python3 main.py -act start -d
python3 main.py -act end
"""

def parse_option():
    parser = argparse.ArgumentParser()

    parser.add_argument('-act', '--action', type=str, help="Action to perform")
    parser.add_argument('-d', '--debug', action='store_true', help="Show debug messages")
    parser.add_argument('-result', '--app_result', type=str, default='none-default',
                        help="Application result (for end_app & send_result)")

    opt = parser.parse_args()
    return opt

def load_config(yaml_obj):
    with open(CONFIG_PATH, 'r') as file:
        config = yaml_obj.load(file)

    return config

def create_log(debug):

    logging.basicConfig(filename='app_manager.log', level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    console = logging.StreamHandler()

    if debug:
        console.setLevel(logging.DEBUG)
    else: 
        console.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    return logging 
    
class Actions:
    def __init__(self, debug):
        self.debug = debug
        self.logging = create_log(self.debug)

        # General configs
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True

        self.config = load_config(self.yaml)
        self.logging.debug('[SUCCESS] Loaded general configurations')

        # App results
        self.result_opt = configparser.ConfigParser()
        self.result_opt.read(RESULT_OPT_PATH)
        self.logging.debug('[SUCCESS] Loaded application results')

        # Discord API
        headers = {
            "Authorization": self.config['OPERATOR_TOKEN'],
            "Content-Type": "application/json"
        }
        self.cano = Canopy(api_version=API_VERSION, headers=headers)
        self.logging.debug('[SUCCESS] Initialized Discord API')

        # Other 
        self.get_applicant_id()
        self.logging.debug('[SUCCESS] Retrieved applicant ID')

    def get_applicant_id(self):
        channel_id = self.config['APPLICATION_LINK'].split('/')[-2]
        message_id = self.config['APPLICATION_LINK'].split('/')[-1]
        search_cutoff = add_one(message_id)

        params = {
            'before': search_cutoff
        }
        res = self.cano.get_messages(channel_id, count=1, params=params)
        messages = res.json()
        app_message = messages[0]
        assert app_message['id'] == message_id

        self.config['APPLICANT_ID'] = app_message['author']['id']
        self.config['APPLICANT_NAME'] = str(self.config['APPLICANT_NAME'])
        return None
    
    def start_app(self):
        """
        # Start App
        # Description: Start an application.

        1. [S] Create thread
        2. [S] Delete thread creation message
        3. [S] Send interview initiator
        4. [S] Send reference link
        5. [M] Unlock members' channel
        6. [M] Purge members' channel
        7. [M] Send app vote initiator
        8. [M] Add accept/deny reactions
        9. [M] Pin message
        10. [M] Delete pin notification

        """
        applicant_ch, member_ch = \
            self.config['APPLICANT_CHANNEL'], self.config['MEMBER_CHANNEL']
        self.logging.info('Start application process')
        
        # 1. Create thread
        res = self.cano.create_thread(applicant_ch, self.config['APPLICANT_NAME'])
        thread_data = res.json()
        app_thread_id = thread_data['id']
        time.sleep(1)
        self.logging.info('[SUCCESS] 1. Create thread')

        # 2. Delete creation message
        res = self.cano.get_messages(applicant_ch) 
        messages = res.json()

        for message in messages:
            if (message['content'] == str(self.config['APPLICANT_NAME'])) \
                and (message['author']['id'] == self.config['OPERATOR_ID']):
                self.cano.delete_message(applicant_ch, message['id'])
                break
        self.logging.info('[SUCCESS] 2. Delete creation message')

        # 3. Send interview initiator
        message_content = self.config['THREAD_M1'].replace('[APPLICANT_ID]', self.config['APPLICANT_ID']).replace('[PING_ROLE]', self.config['PING_ROLE'])
        self.cano.send_message(app_thread_id, message_content, is_thread=True)
        self.logging.info('[SUCCESS] 3. Send interview initiator')

        # 4. Send reference link
        message_content = self.config['THREAD_M2'].replace('[APPLICATION_LINK]', self.config['APPLICATION_LINK'])
        self.cano.send_message(app_thread_id, message_content, is_thread=True)
        self.logging.info('[SUCCESS] 4. Send reference link')

        # 5. Unlock members' channel
        self.cano.send_message(member_ch, '1unlock')
        time.sleep(1)
        self.logging.info('[SUCCESS] 5. Unlock members\' channel')

        # 6. Purge members' channel
        self.cano.purge_channel(member_ch)
        self.logging.info('[SUCCESS] 6. Purge members\' channel')

        # 7. Send app vote initiator
        message_content = self.config['MEMBER_M1'] \
            .replace('[PING_ROLE]', self.config['PING_ROLE']) \
            .replace('[APPLICATION_LINK]', self.config['APPLICATION_LINK']) \
            .replace('[GUILD]', self.config['GUILD']) \
            .replace('[THREAD_ID]', app_thread_id) \
            .replace(' ', '\n')
        res = self.cano.send_message(member_ch, message_content)
        message_data = res.json()
        vote_message_id = message_data['id']
        self.logging.info('[SUCCESS] 7. Send app vote initiator')

        # 8. Add accept/deny reactions
        self.cano.add_reaction(member_ch, vote_message_id, self.config['ACCEPT_EMOJI'])
        self.cano.add_reaction(member_ch, vote_message_id, self.config['DENY_EMOJI'])
        self.logging.info('[SUCCESS] 8. Add accept/deny reactions')

        # 9. Pin message
        self.cano.pin_message(member_ch, vote_message_id)
        time.sleep(1)
        self.logging.info('[SUCCESS] 9. Pin message')

        # 10. Delete pin notification
        res = self.cano.get_messages(member_ch) 
        messages = res.json()

        for message in messages:
            if message['type'] == 6:
                self.cano.delete_message(member_ch, message['id'])
                break
        self.logging.info('[SUCCESS] 10. Delete pin notification')

        self.logging.info('Successfully started application process')
        self.config['APP_THREAD_ID'] = app_thread_id
        self.config['VOTE_MESSAGE_ID'] = vote_message_id

        with open(CONFIG_PATH, 'w') as file:
            self.yaml.dump(self.config, file)
        return None

    def end_app(self, app_result):
        """
        # End App
        # Description: End the previously initiated application.

        1. Lock members' channel
        2. Purge members' channel with bot command
        3. Retrieve & pack application metadata 
        4. Retrieve & pack application thread message history
        5. Manual iteration purge for exceptional messages
        6. Lock & archive thread 
        7. Informing of channel locking & send public metadata
        8. Inform application result

        """
        member_ch = self.config['MEMBER_CHANNEL']
        app_meta = {}
        
        self.logging.info('Start application closing process')

        # 1. Lock members' channel
        self.cano.send_message(member_ch, '1lock')
        time.sleep(1)
        self.logging.info('[SUCCESS] 1. Lock members\' channel')

        # 2. Purge members' channel with bot command 
        res = self.cano.get_messages(member_ch)

        while len(res.json()) > 10:
            self.cano.send_message(member_ch, '2purge 1000')
            time.sleep(1)
            res = self.cano.get_messages(member_ch)
        self.logging.info('[SUCCESS] 2.1. Command-based mass purge for discussion messages')

        # 3. Retrieve & pack application metadata
        res = self.cano.get_messages(member_ch)
        messages = res.json()
        vote_message = messages[-1]

        # applicant info
        app_meta['applicant_name'] = self.config['APPLICANT_NAME']
        app_meta['applicant_id'] = self.config['APPLICANT_ID']

        # time elapsed
        iso_stamp1 = vote_message['timestamp']
        dt_obj = datetime.fromisoformat(iso_stamp1)
        app_meta['start_date'] = str(dt_obj.date())

        dt_stamp1 = datetime.fromisoformat(iso_stamp1)
        dt_stamp1 = dt_stamp1.replace(tzinfo=timezone.utc)
        dt_stamp2 = datetime.now(timezone.utc)
        app_meta['time_elapsed'] = format_timedelta(dt_stamp2 - dt_stamp1)

        # votes
        res = self.cano.get_reaction_info(member_ch, self.config['VOTE_MESSAGE_ID'], self.config['ACCEPT_EMOJI'])
        app_meta['accept_votes'] = len(res.json())
        res = self.cano.get_reaction_info(member_ch, self.config['VOTE_MESSAGE_ID'], self.config['DENY_EMOJI'])
        app_meta['deny_votes'] = len(res.json())

        # result
        app_meta['app_result'] = app_result
        decision, mtype = app_result.split('-')
        app_meta['result_message'] = self.result_opt[decision][mtype]

        # misc
        app_meta['application_link'] = self.config['APPLICATION_LINK']
        app_meta['operator_id'] = self.config['OPERATOR_ID']

        # app_meta_string = json.dumps(app_meta, indent=4)
        # app_meta_bytesio = io.BytesIO(app_meta_string.encode())
        app_meta_name = '{}_{}_{}.json'\
                        .format(self.config['FILE_PREFIX'], app_meta["start_date"], app_meta["applicant_id"])
        with open(os.path.join(self.config['META_PATH'], app_meta_name), 'w') as file:
            json.dump(app_meta, file, indent=4)

        self.logging.info('[SUCCESS] 3. Retrieve & pack application metadata')

        # 4. Retrieve & pack application thread message history

        self.logging.info('[SUCCESS] 4. Retrieve & pack application thread message history')

        # 5. Manual iteration purge for exceptional messages
        
        for message in messages:
            self.cano.delete_message(member_ch, message['id'])
        self.logging.info('[SUCCESS] 5. Manual iteration purge for exceptional messages')

        # 6. Lock & archive thread 
        message_content = self.config['THREAD_MLOCK']
        self.cano.send_message(self.config['APP_THREAD_ID'], message_content, is_thread=True)
        self.cano.update_thread(self.config['APP_THREAD_ID'], updates={'locked': True, 'archived': True})
        self.logging.info('[SUCCESS] 6. Lock & archive thread')

        # 7. Inform of channel locking & send public metadata
        lock_message = self.config['MEMBER_MLOCK'] \
                           .replace('[APPLICANT_NAME]', str(app_meta['applicant_name'])) \
                           .replace('[ACCEPT_VOTES]', str(app_meta['accept_votes'])) \
                           .replace('[DENY_VOTES]', str(app_meta['deny_votes'])) \
                           .replace('[APP_RESULT]', app_meta['app_result'])
        self.cano.send_message(member_ch, message_content=lock_message)
        self.cano.send_message(member_ch, message_content=self.config['MEMBER_MMETA'], files=[(app_meta_name, os.path.join(self.config['META_PATH'], app_meta_name))])

        self.logging.info('[SUCCESS] 7. Inform of channel locking & send public metadata')

        # 8. Inform application result
        self.send_result(app_result)
        self.logging.info('[SUCCESS] 8. Inform application result')

        self.logging.info('Successfully closed application')
        return None

    def send_result(self, app_result):
        """
        # Send result
        # Description: Send an application result to the applicant.

        1. Send application result message
        2. Delete result creation message

        """
        applicant_ch = self.config['APPLICANT_CHANNEL']
        app_result = app_result.split('-')
        format = {
            'accept': '#9fec97 Accepted',
            'deny': '#da8e8e Denied',
            'reject': '#da8e8e Rejected'
        }
        self.logging.info('Start result process')

        # 1. Send application result message

        decision, mtype = app_result
        message_header = '2embed {}|<@{}> [{}]'\
                         .format(format[decision], self.config["APPLICANT_ID"], str(self.config["APPLICANT_NAME"]))
        app_response = self.result_opt[decision][mtype]

        message_content = f'{message_header} {app_response}'
        self.cano.send_message(applicant_ch, message_content)
        time.sleep(1)
        self.logging.info('[SUCCESS] 1. Send application result message')

        # 2. Delete result creation message 
        res = self.cano.get_messages(applicant_ch)
        messages = res.json()

        for message in messages:
            if message['author']['id'] == self.config['OPERATOR_ID']:
                self.cano.delete_message(applicant_ch, message['id'])
                break
        self.logging.info('[SUCCESS] 2. Delete result creation message')
        
        self.logging.info('Successfully sent result')
        return None

def main(opt):

    act = Actions(opt.debug)

    if opt.action == 'start':
        act.start_app()

    elif opt.action == 'end':
        act.end_app(opt.app_result)
    
    elif opt.action == 'result_only':
        act.send_result(opt.app_result)
    
    else:
        raise AttributeError('Invalid action')
    
if __name__ == "__main__":
    opt = parse_option()
    main(opt)
