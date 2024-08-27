from tinkoff.invest import Client
from tinkoff.invest.exceptions import RequestError
import mydata


with Client(mydata.TOKEN) as client:
    try:
        result = client.orders.get_orders(account_id=mydata.ACCOUNT_ID)
        
        print(result.orders)
        
    except RequestError as e:
        print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
    
    

    
    