'''
https://tinkoff.github.io/investAPI/head-users/
'''



from tinkoff.invest import Client
from tinkoff.invest.exceptions import RequestError
import mydata


with Client(mydata.TOKEN) as client:
    try:
        result = client.users.get_accounts()
        print(result)
        
    except RequestError as e:
        print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
    
    
