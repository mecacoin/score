from iconservice import *

class mecacoin(IconScoreBase):
    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'
    _DECIMALS = 'decimals'
    _TOKEN_RELEASE_BALANCE_TABLE = 'token_release_percent_table'
    _TOKEN_RELEASE_TIME_TABLE = 'token_release_time_table'
    _PRIVATE_INVESTOR_TABLE = 'private_investor_table'
    
    _CASINO_GAME_RESULT_TALBE = 'casino_game_result_table'
    _MECACASINO_GAME_MASTER_ADDRESS = 'mecacasino_gamemaster_owner_address'
     
    _BONUS_INDEX = 12

    @eventlog(indexed=3)
    def Transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):
        pass 

    @eventlog(indexed=3)
    def ReleasedTokenLog(self, _targetAddr: Address, _time : int, _index: int,  _value: int):
        pass 

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
        self._decimals = VarDB(self._DECIMALS, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)
        
        self._token_release_balance_table = DictDB(self._TOKEN_RELEASE_BALANCE_TABLE, db, value_type=int, depth=2)
        self._token_release_time_table = DictDB(self._TOKEN_RELEASE_TIME_TABLE, db, value_type=int, depth=2)
        self._private_investors_table = DictDB(self._PRIVATE_INVESTOR_TABLE, db, value_type=int)
        
        self._casino_game_result_table = DictDB(self._CASINO_GAME_RESULT_TALBE, db, value_type=str)
        self._gamemasterOwner = VarDB(self._MECACASINO_GAME_MASTER_ADDRESS, db, value_type=str)
        
    def on_install(self) -> None:
        super().on_install()
        
        total_supply = 5000000000
        _decimals = 0

        self._total_supply.set(total_supply)
        self._decimals.set(_decimals)
        self._balances[self.msg.sender] = total_supply
        
    def on_update(self) -> None:
        super().on_update()
        
    @external(readonly=True)
    def name(self) -> str:
        return "MECA Coin"

    @external(readonly=True)
    def tokenOwner(self) -> Address:
        return self.owner
        
    @external(readonly=True)
    def symbol(self) -> str:
        return "MCA"

    @external(readonly=True)
    def decimals(self) -> int:
        return self._decimals.get()

    @external(readonly=True)
    def totalSupply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balanceOf(self, _owner: Address) -> int:
        return self._balances[_owner]

    @external
    def transfer(self, _to: Address, _value: int, _data: bytes = None):
        if _data is None:
            _data = b'None'

        if self.msg.sender == _to :
            revert("The recevier and sender must be different.")
            
        self._transfer(self.msg.sender, _to, _value, _data)

    def _transfer(self, _from: Address, _to: Address, _value: int, _data: bytes):
        # Checks the sending value and balance.
        if _value < 0:
            revert("Transferring value cannot be less than zero")
        if self._balances[_from] < _value:
            revert("Out of balance")

        if self._private_investors_table[_from] == 1 and _from != self.owner:
            if self._getWithdrawableAmount_PrivateSale(_from) < _value:
                revert("Out of balance - Private Sale")

            d = int(self.now() / 1000000.0)
            s_index = -1
            for _index in range(0,12):
                if self._token_release_time_table[_from][_index] > 0 and self._token_release_time_table[_from][_index] < d :
                    s_index = _index
            if s_index >= 0 and s_index <= 11 :
                self._token_release_balance_table[_from][s_index] -= _value
                self.ReleasedTokenLog(_from, self._token_release_time_table[_from][s_index], s_index, _value)
            else :
                revert("Invalid balance index")

        logTime = str(int(self.now() / 1000000.0))
                
        # If the sender is token holder, will be set token lock.
        if _from == self.owner :
            _data = b'From Token Holder'

        # Update balance.
        self._balances[_from] = self._balances[_from] - _value
        self._balances[_to] = self._balances[_to] + _value

        self.Transfer(_from, _to,  _value, _data)

    def _getWithdrawableAmount_PrivateSale(self, _to: Address) -> int:     
        t = 0
        b = 0
        d = int(self.now() / 1000000.0)
        for _index in range(0,12):
            if self._token_release_time_table[_to][_index] > 0 and self._token_release_time_table[_to][_index] < d :
                t = t + self._token_release_balance_table[_to][_index]

        if self._token_release_time_table[_to][self._BONUS_INDEX] > 0 and self._token_release_time_table[_to][self._BONUS_INDEX] < d : 
            b = self._token_release_balance_table[_to][self._BONUS_INDEX]

        if (t+b) > self._balances[_to] :
            return self._balances[_to]

        return (t+b)
  
    def setDefaultLock(self, _to: Address, _flag : int ) -> None : 
        self._private_investors_table[_to] = _flag
        d = int(self.now() / 1000000.0)
 
        for month in range(0,13) :
            self.updateLock_PrivateSale(_to, month, d, 0 ) 

    @external(readonly=True)
    def getWithdrawableAmount_PrivateSale(self) -> int:        
        return self._getWithdrawableAmount_PrivateSale(self.msg.sender)

    @external(readonly=True)
    def getLockupTable_PrivateSale(self, _to: Address) -> str:
        if self.msg.sender != self.owner :
            return "Denied"
            
        r = "["
        for _index in range(0,13):
            r = r + "{\"key\":" + str(_index) + ","
            r = r + " \"value\": " + str(self._token_release_time_table[_to][_index]) + "}"
            
            if _index < 12 :
                r =  r + "," 

        r = r + "]"

        return r
                 
    @external(readonly=True)
    def getBalanceTable_PrivateSale(self, _to: Address) -> str: 
        if self.msg.sender != self.owner :
            return "Denied"
        
        r = "["
        for _index in range(0,13):
            r =  r + "{\"key\":" + str(_index) + ","
            r =  r + " \"value\": " + str(self._token_release_balance_table[_to][_index]) + "}"

            if _index < 12 :
                r = r + ","

        r = r + "]"
        return r

    @external
    def setLockup_PrivateSale(self, _to: Address, total_amount_mca: int , invest_type: str) -> str:  
        if self.msg.sender != self.owner :
            return "Denied"

        token_release_time_table = [
        [1546304400, 1547514000], # 2019-01-01  2019-01-15
        [1548982800, 1550192400], # 2019-02-01  2019-02-15
        [1551402000, 1552611600], # 2019-03-01  2019-03-15
        [1554080400, 1555290000], # 2019-04-01  2019-04-15
        [1556672400, 1557882000], # 2019-05-01  2019-05-15
        [1559350800, 1560560400], # 2019-06-01  2019-06-15
        [1561942800, 1563152400], # 2019-07-01  2019-07-15
        [1564621200, 1565830800], # 2019-08-01  2019-08-15
        [1567299600, 1568509200], # 2019-09-01  2019-09-15
        [1569891600, 1571101200], # 2019-10-01  2019-10-15
        [1572570000, 1573779600], # 2019-11-01  2019-11-15
        [1575162000, 1576371600], # 2019-12-01  2019-12-15
        [1577840400, 1579050000], # 2020-01-01  2020-01-15
        [1580518800, 1581728400], # 2020-02-01  2020-02-15
        [1583024400, 1584234000], # 2020-03-01  2020-03-15
        [1585702800, 1586912400], # 2020-04-01  2020-04-15
        [1588294800, 1589504400], # 2020-05-01  2020-05-15
        [1590973200, 1592182800]  # 2020-06-01  2020-06-15
        ]
        
        token_allocation_ratio = [
            ["PS_TYPE_A_50",10,10,10,10,10,10,10,10,10,10,0,0,50],
            ["PS_TYPE_A_35",20, 0,30, 0,50, 0, 0, 0, 0, 0,0,0,35],
            ["PS_TYPE_B_40",10,10,10,10,10,10,10,10,10,10,0,0,40],
            ["PS_TYPE_B_25",20, 0,30, 0,50, 0, 0, 0, 0, 0,0,0,25],
        ]
        _f = -1
        _s =  1
        for i in range(0,4) :
            if token_allocation_ratio[i][0] == invest_type :
                _f = i
                if i == 0 or i == 2 :
                    _s = 0
                
        if _f >= 0 :
            self._private_investors_table[_to] = 1
            array_index = 0
            for month in range(0,14) :
                self._token_release_time_table[_to][month] = 0
                self._token_release_balance_table[_to][month] = 0

                if month >= 1 and token_allocation_ratio[_f][month] > 0 :
                    if (month-1) >= self._BONUS_INDEX :
                        self._token_release_time_table[_to][self._BONUS_INDEX] = token_release_time_table[month-1][_s]
                        self._token_release_balance_table[_to][self._BONUS_INDEX] = int(total_amount_mca * (token_allocation_ratio[_f][month] * 0.01))
                    else :
                        self._token_release_time_table[_to][array_index] = token_release_time_table[month-1][_s]
                        self._token_release_balance_table[_to][array_index] = int(total_amount_mca * (token_allocation_ratio[_f][month] * 0.01))
                        array_index = array_index + 1
        
        return ""

    @external
    def updateLock_PrivateSale(self, _to: Address, _index: int, _time: int, _balance: int) -> None:
        if self.msg.sender == self.owner :
            d = int(self.now() / 1000000.0)
            if d < _time :
                if _index >= 0 and _index <= 11 :
                    self._token_release_time_table[_to][_index] = _time
                    self._token_release_balance_table[_to][_index] = _balance
                if _index >= self._BONUS_INDEX :
                    self._token_release_time_table[_to][self._BONUS_INDEX] = _time
                    self._token_release_balance_table[_to][self._BONUS_INDEX] = _balance 

    @external
    def setMECACasinoOwnerAddress(self,  _newOwnerAddress : str) -> str: 
        if self.msg.sender != self.owner :
            return "Denied"
        
        self._gamemasterOwner.set(_newOwnerAddress)
        
        return ""

    @external(readonly=True)
    def getMECACasinoOwnerAddress(self) -> Address:
        return self._gamemasterOwner.get()
               
    @external
    def pushGameResultToBlock(self,  _hash : str) -> str:
        if (self.msg.sender != self._gamemasterOwner.get()) and (self.msg.sender != self.owner):
            return "Denied"
            
        self._casino_game_result_table[_hash] = _hash
        
        return ""

    @external(readonly=True)
    def getGameResultFromBlock(self, _hash : str) -> str:
        r  = "["
        r += self._casino_game_result_table[_hash]
        r += "]"
        
        return r
                     
    @external
    def removePrivateInvestor(self, _to : Address) -> None:
        if self.msg.sender != self.owner :
            revert("Denied")

        self._private_investors_table[_to] = 0
        
    @external(readonly=True)
    def isPrivateInvestor(self, _to : Address) -> int :
        return self._private_investors_table[_to]

    @external(readonly=True)
    def getBlockchainTime(self) -> int :
        d = int(self.now() / 1000000.0)
        return d