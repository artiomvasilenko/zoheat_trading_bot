from tinkoff.invest import Client

import mydata






with Client(mydata.TOKEN) as client:
    result = client.users.get_accounts()
    print(result)
    