import pyupbit

access = "1WOAdsCcUZzXTxxbazQkljLh56yTMhSUwjsagMFv"         
secret = "GfiGD36aC6xhcg9PNHPrxhlAlAPx7VSDRJajo9Va"
upbit = pyupbit.Upbit(access, secret)

print(upbit.get_balance("KRW-XRP"))     # KRW-XRP 조회
print(upbit.get_balance("KRW"))         # 보유 현금 조회