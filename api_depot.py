import json
import requests 

class Endpoint:

    def __init__(self, api_version):
        self.base_url = f'https://discord.com/api/v{api_version}/'

    # Guild

    def guild(self, guild_id):
        return self.base_url + f'guilds/{guild_id}'

    def guild_channels(self, guild_id):
        return self.base_url + f'guilds/{guild_id}/channels'
    
    def guild_message_search(self, guild_id, message_limit=25):
        return self.base_url + f'guilds/{guild_id}/messages/search?limit={message_limit}'

    # Channel

    def message(self, channel_id, message_id):
        return self.base_url + f'channels/{channel_id}/messages/{message_id}'

    def message_reactions(self, channel_id, message_id):
        return self.base_url + f'channels/{channel_id}/messages/{message_id}/reactions/'
    
    def pins(self, channel_id, message_id):
        return self.base_url + f'channels/{channel_id}/pins/{message_id}'
    
    def new_reaction(self, channel_id, message_id, reaction):
        return self.base_url + f'channels/{channel_id}/messages/{message_id}/reactions/{reaction}/%40me'
    
    def reaction_info(self, channel_id, message_id, reaction):
        return self.base_url + f'channels/{channel_id}/messages/{message_id}/reactions/{reaction}'

    def destination_messages(self, channel_id, message_limit=0):
        if message_limit == 0:
            return self.base_url + f'channels/{channel_id}/messages'
        else: 
            return self.base_url + f'channels/{channel_id}/messages?limit={message_limit}'

    def threads(self, channel_id):
        return self.base_url + f'channels/{channel_id}/threads'

    def thread_contents(self, thread_id):
        return self.base_url + f'channels/{thread_id}/messages'

    def thread_info(self, thread_id):
        return self.base_url + f'channels/{thread_id}'

    # User

    def user(self, user_id):
        return self.base_url + f'users/{user_id}'
    
    def user_profile(self, user_id):
        return self.base_url + f'users/{user_id}/profile'

  

class Canopy:
    def __init__(self, api_version, headers):
        self.depot = Endpoint(api_version=api_version)
        self.headers = headers

        # A special version of headers for attaching files in a message
        self.sendf_headers = {'Authorization': self.headers['Authorization']}

    def check_status(self, res):
        assert (res.status_code >= 200 and res.status_code <= 299), \
               f"Status Code: {res.status_code}, JSON: {res.json()}"


    def get_messages(self, channel_id, count=100, params=None):
        res = requests.get(self.depot.destination_messages(channel_id, message_limit=count), 
                                      headers=self.headers, 
                                      params=params)
        self.check_status(res)
        return res
    
    def send_message(self, destination_id, message_content=None, files=None, is_thread=False):
        endpoint = self.depot.thread_contents if is_thread else self.depot.destination_messages

        message_json = {
            "content": message_content
        }

        message_files = {}
        if files is not None:
            for ix, path in enumerate(files):
                if isinstance(path, tuple):
                    if len(path) > 2:
                        if path[2] == 'bytesio':
                            message_files[f'file{ix + 1}'] = (path[0], path[1])
                        else:
                            raise AttributeError('Invalid specified file type.')
                    else:
                        message_files[f'file{ix + 1}'] = (path[0], open(path[1], 'rb'))
                else:
                    message_files[f'file{ix + 1}'] = open(path, 'rb')

            res = requests.post(endpoint(destination_id),
                                headers=self.sendf_headers,
                                data=message_json,
                                files=message_files)
        else:
            res = requests.post(endpoint(destination_id),
                                headers=self.headers,
                                data=json.dumps(message_json))
        
        self.check_status(res)
        return res

    def delete_message(self, channel_id, message_id):
        res = requests.delete(self.depot.message(channel_id, message_id), 
                        headers=self.headers)
        
        try: 
            # Unknown message, probably attempted to delete a nonexistent message
            if res.json().get('code') == 10008: 
                return res 
        except json.decoder.JSONDecodeError:
            pass 

        self.check_status(res)
        return res

    def add_reaction(self, channel_id, message_id, reaction):
        res = requests.put(self.depot.new_reaction(channel_id, message_id, reaction), 
                           headers=self.headers)
        self.check_status(res)
        return res

    def get_reaction_info(self, channel_id, message_id, reaction):
        res = requests.get(self.depot.reaction_info(channel_id, message_id, reaction), 
                           headers=self.headers)
        self.check_status(res)
        return res

    def pin_message(self, channel_id, message_id):
        res = requests.put(self.depot.pins(channel_id, message_id), headers=self.headers)
        self.check_status(res)
        return res

    def create_thread(self, channel_id, thread_name):
        thread_json = {
            "name": thread_name,
            "type": 11
        }

        res = requests.post(self.depot.threads(channel_id), 
                      headers=self.headers, 
                      data=json.dumps(thread_json))
        self.check_status(res)
        return res
    
    def update_thread(self, thread_id, updates):

        res = requests.patch(self.depot.thread_info(thread_id), headers=self.headers, json=updates)
        self.check_status(res)
        return res   

    def purge_channel(self, channel_id):
        res = requests.get(self.depot.destination_messages(channel_id, message_limit=100), headers=self.headers)
        self.check_status(res)

        messages = res.json()
        for message in messages:
            self.delete_message(channel_id, message['id'])

        return res