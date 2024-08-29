import requests
import h5py,h5pyd
import traceback
from keycloak import KeycloakOpenID
import time 

def get_kcclient (keycloak_server_url,keycloak_client_id,keycloak_realm_name,client_secret_key):
    return KeycloakOpenID(
        server_url=keycloak_server_url,
        client_id=keycloak_client_id,
        realm_name=keycloak_realm_name,
        client_secret_key="secret")


class TokenService():
    def __init__(self,kcclient,token=None):
        self.kcclient = kcclient
        self.token=None

    def well_known(self):
        return self.kcclient.well_known()


    def get_token(self,username,password):
        self.token = self.kcclient.token(username,password)
        return self.token

    def refresh_token(self):
        self.token = self.kcclient.refresh_token(self.token['refresh_token'])

    #def token(self):
    #    return self.token

    def api_key(self):
        return self.token['access_token']

    def userinfo(self):
        return self.kcclient.userinfo(self.token['access_token'])

    def logout(self):
        self.kcclient.logout(self.token["refresh_token"])
        self.token = None

    def getHeaders(self):
        headers = {}
        headers["Accept"] = "application/json"
        _token = self.token['access_token']
        if _token != None:
            headers["Authorization"] = "Bearer {}".format(_token)
        return headers

    def token_time_left(self):
        if not self.token:
            return True

        # Decode the access token to get its expiration time
        decoded_token = self.kcclient.decode_token(self.token['access_token'])
        expiration_time = decoded_token['exp']
        current_time = time.time()

        return expiration_time - current_time

class QueryService():
    def __init__(self,tokenservice):
        self.tokenservice = tokenservice

    def get(self,url,params):
        return requests.get(url, params,headers=self.tokenservice.getHeaders())

    def post(self,url,data,files):
        return requests.post(url, data = data, files = files,headers=self.tokenservice.getHeaders())

    def api_key(self):
        return self.tokenservice.api_key()

    def login(self,username,password):
        self.tokenservice.get_token(username,password)

    def logout(self):
        self.tokenservice.logout()
