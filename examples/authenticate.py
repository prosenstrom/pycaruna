import sys
import os

sys.path.append('../pycaruna')
from pycaruna import Authenticator, customer_ids_from_user

if __name__ == '__main__':
    username = os.getenv('CARUNA_USERNAME')
    password = os.getenv('CARUNA_PASSWORD')

    if username is None or password is None:
        raise Exception('CARUNA_USERNAME and CARUNA_PASSWORD must be defined')

    # Authenticate using your e-mail and password. This will ultimately return an object containing a token (used for
    # Caruna Plus API interaction) and a user object which among other things contain your customer IDs (needed when
    # interacting with the Caruna Plus API). See resources/login_result.json for an example of the JSON structure.
    #
    # The token is valid for 60 minutes (as of this writing), so it should be enough to authenticate once and then
    # reuse the token for all further requests you may want to make.
    authenticator = Authenticator(username, password)
    login_result = authenticator.login()

    # print(json.dumps(login_result))
    print(login_result['token'])
    customer_ids = customer_ids_from_user(login_result.get('user'))
    if not customer_ids:
        raise Exception('No customer numbers on this account')
    print(customer_ids[0])
