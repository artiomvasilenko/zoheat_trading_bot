'''
https://tinkoff.github.io/investAPI/head-operations/
'''

from tinkoff.invest import Client
from tinkoff.invest.exceptions import RequestError
from find_instrument import find_instrument
import mydata


with Client(mydata.TOKEN) as client:
    try:
        moneys = client.operations.get_positions(account_id=mydata.ACCOUNT_ID).money
        for money in moneys:
            print(money.units, 'RUB') if money.currency == 'rub' else None
            
        shares = client.operations.get_positions(account_id=mydata.ACCOUNT_ID).securities
        for share in shares:
            instr = find_instrument(share.instrument_uid)
            None if instr == None else print(instr.name, share.balance)
        
    except RequestError as e:
        print(e.details, mydata.errors[e.details]) if e.details in mydata.errors else print(e.details, e.metadata.message)
    
    
