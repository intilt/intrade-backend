
class BarData:
    def __init__(self):
        self.barnum: int = 0
        self.date: str = ''
        self.stime: str = ''
        self.etime: str = ''
        self.contract: str = ''
        self.expiry_date: str = ''
        self.lot_size: int = 1
        self.dte: float = float('nan')
        self.open: float = 0.0
        self.high: float = 0.0
        self.low: float = 0.0
        self.close: float = 0.0
        self.ltp: int = 0.0
        self.volume: int = 0
        self.count: int = 0
        self.vwap: float = 0
        self.total_vwap: float = 0
        self.cp_fut: float = 0
        self.atm1: float = 0
        self.atm2: float = 0
        self.iv1: float = 0
        self.delta: float = 0
        self.gamma: float = 0
        self.total_oi: int = 0
        self.index: float = 0
        self.tq: int = 1
        return