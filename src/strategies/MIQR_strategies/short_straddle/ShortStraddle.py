from typing import List, Dict, Any, Union
from strategy import BaseStrategy
from data_module.bardata import BarData
import time

class NiftyODTEShortGamma(BaseStrategy):
    def __init__(self, bar_duration: int, strategy_config: Dict):
        super().__init__(bar_duration)
        self.symbol = strategy_config["symbol"]
        self.exg = strategy_config.get("exg", "NSE")
        self.maxpos = strategy_config["maxpos"]
        
        # Configurable parameters
        self.entry_time = strategy_config.get("entry_time", "092000")  # 9:20 AM
        self.exit_time = strategy_config.get("exit_time", "152000")    # 3:20 PM
        self.sl_percentage = strategy_config.get("sl_percentage", 0.20)  # 20% stop-loss
        self.buffer_percentage = strategy_config.get("buffer_percentage", 0.10)  # 10% buffer
        self.retry_duration = strategy_config.get("retry_duration", 30)  # 30 seconds retry window
        self.retry_interval = strategy_config.get("retry_interval", 2)   # Retry every 2 seconds
        
        # State variables
        self.entered = False
        self.positions = {
            "short_call": {"contract": None, "entry_price": None, "sl_price": None, "is_open": False},
            "short_put": {"contract": None, "entry_price": None, "sl_price": None, "is_open": False},
            "long_call": {"contract": None, "entry_price": None, "is_open": False},
            "long_put": {"contract": None, "entry_price": None, "is_open": False}
        }
        self.order_place_time = {}
        self.sl_triggered = {"call": False, "put": False}
        self.sl_trigger_time = {"call": None, "put": None}
        self.lot_size = None

    def updateBarAlpha(self, bar: List[BarData]):
        """Main method called on each bar update."""
        current_time = bar[0].stime
        
        if current_time == self.entry_time and not self.entered:
            self.enter_positions(bar)
        
        elif current_time >= self.exit_time and self.entered:
            self.exit_all_positions(bar)
        
        elif self.entered:
            self.monitor_sl(bar)
            self.handle_order_rejections(bar)

    def enter_positions(self, bar: List[BarData]):
        """Enter short straddle with long wings."""
        today = bar[0].date
        index_price = self.get_index_price(bar)
        if index_price is None:
            return

        atm_strike, long_call_strike, long_put_strike = self.select_strikes(bar, index_price)
        if not all([atm_strike, long_call_strike, long_put_strike]):
            return

        self.lot_size = bar[0].lot_size
        self.new_position_size = self.maxpos

        # Short ATM call and put with stop-limit orders
        short_call_contract = self.get_contract(bar, today, "C", atm_strike)
        short_put_contract = self.get_contract(bar, today, "P", atm_strike)
        self.place_short_entry_order(short_call_contract, -self.new_position_size, bar)
        self.place_short_entry_order(short_put_contract, -self.new_position_size, bar)

        # Long OTM call and put with limit orders
        long_call_contract = self.get_contract(bar, today, "C", long_call_strike)
        long_put_contract = self.get_contract(bar, today, "P", long_put_strike)
        self.place_long_order(long_call_contract, self.new_position_size, bar)
        self.place_long_order(long_put_contract, self.new_position_size, bar)

        self.entered = True

    def place_short_entry_order(self, contract: str, target_pos: int, bar: List[BarData]):
        """Place a short entry order with stop-limit and 10% buffer."""
        bar_data = next(b for b in bar if b.contract == contract)
        trigger_price = bar_data.ltp
        limit_price = trigger_price * (1 + self.buffer_percentage)  # 10% above trigger
        
        # Set target position
        self._updateTargetPosition(contract, target_pos)
        
        # Use _setTradeParams for trigger price and stop-limit execution type
        self._setTradeParams(contract, trigger_price, exec_type=4)  # Assuming 4 is stop-limit
        
        # Use overWriteMiscDict to set limit price and quantity
        misc_dict = {
            'limit_price': limit_price,
            'quantity': abs(target_pos)
        }
        self.overWriteMiscDict(contract, misc_dict)
        
        self.order_place_time[contract] = time.time()
        self.positions["short_call" if "C" in contract else "short_put"] = {
            "contract": contract,
            "entry_price": trigger_price,
            "sl_price": trigger_price * (1 + self.sl_percentage),
            "is_open": True
        }

    def place_long_order(self, contract: str, target_pos: int, bar: List[BarData]):
        """Place a long order with a limit order."""
        bar_data = next(b for b in bar if b.contract == contract)
        limit_price = bar_data.ltp
        
        # Set target position
        self._updateTargetPosition(contract, target_pos)
        
        # Use _setTradeParams for limit order
        self._setTradeParams(contract, limit_price, exec_type=2)  # Assuming 2 is limit order
        
        self.order_place_time[contract] = time.time()
        self.positions["long_call" if "C" in contract else "long_put"] = {
            "contract": contract,
            "entry_price": limit_price,
            "is_open": True
        }

    def monitor_sl(self, bar: List[BarData]):
        """Monitor stop-loss for short positions."""
        for leg in ["short_call", "short_put"]:
            if self.positions[leg]["is_open"]:
                contract = self.positions[leg]["contract"]
                bar_data = next(b for b in bar if b.contract == contract)
                if bar_data.ltp >= self.positions[leg]["sl_price"]:
                    self.trigger_sl(leg, bar_data)

    def trigger_sl(self, leg: str, bar_data: BarData):
        """Trigger stop-loss exit for a leg with stop-limit order."""
        contract = self.positions[leg]["contract"]
        trigger_price = self.positions[leg]["sl_price"]
        limit_price = trigger_price * (1 - self.buffer_percentage)  # 10% below trigger for buyback
        
        # Set target position to 0 (exit)
        self._updateTargetPosition(contract, 0)
        
        # Use _setTradeParams for trigger price and stop-limit execution type
        self._setTradeParams(contract, trigger_price, exec_type=4)  # Stop-limit order
        
        # Use overWriteMiscDict to set limit price and quantity
        misc_dict = {
            'limit_price': limit_price,
            'quantity': self.new_position_size
        }
        self.overWriteMiscDict(contract, misc_dict)
        
        self.sl_triggered[leg] = True
        self.sl_trigger_time[leg] = time.time()
        self.positions[leg]["is_open"] = False

    def handle_order_rejections(self, bar: List[BarData]):
        """Retry rejected orders within a time window."""
        current_time = time.time()
        for contract in list(self.order_place_time.keys()):
            elapsed = current_time - self.order_place_time[contract]
            if elapsed < self.retry_duration:
                if int(elapsed) % self.retry_interval < 1:
                    self.retry_order(contract, bar)
            elif elapsed >= self.retry_duration:
                self.logger.error(f"Order for {contract} failed after {self.retry_duration} seconds")
                self.exit_all_positions(bar)
                del self.order_place_time[contract]

    def retry_order(self, contract: str, bar: List[BarData]):
        """Retry a failed order."""
        if "short" in contract:
            self.place_short_entry_order(contract, -self.new_position_size, bar)
        else:
            self.place_long_order(contract, self.new_position_size, bar)

    def exit_all_positions(self, bar: List[BarData]):
        """Exit all open positions with limit orders."""
        for leg in self.positions:
            if self.positions[leg]["is_open"]:
                contract = self.positions[leg]["contract"]
                bar_data = next(b for b in bar if b.contract == contract)
                limit_price = bar_data.ltp * (1 - self.buffer_percentage if "short" in leg else 1)
                
                # Set target position to 0
                self._updateTargetPosition(contract, 0)
                
                # Use _setTradeParams for limit order
                self._setTradeParams(contract, limit_price, exec_type=2)  # Limit order
                
                self.positions[leg]["is_open"] = False
        self.entered = False

    # Helper Methods
    def get_index_price(self, bar: List[BarData]) -> Union[float, None]:
        """Get the current index price."""
        try:
            index_bar = next(b for b in bar if b.contract == f"{self.exg}_{self.symbol}")
            return index_bar.ltp
        except StopIteration:
            self.logger.error("Index bar not found")
            return None

    def select_strikes(self, bar: List[BarData], index_price: float) -> tuple:
        """Select ATM and OTM strikes."""
        today = bar[0].date
        calls = [b for b in bar if b.expiry_date == today and b.contract.split("_")[3] == "C"]
        if not calls:
            self.logger.error("No call options found for today")
            return None, None, None

        call_strikes = sorted([int(b.contract.split("_")[-1]) for b in calls])
        atm_strike = min(call_strikes, key=lambda x: abs(x - index_price))
        atm_index = call_strikes.index(atm_strike)
        long_call_strike = call_strikes[min(atm_index + 10, len(call_strikes) - 1)]
        long_put_strike = call_strikes[max(atm_index - 10, 0)]
        return atm_strike, long_call_strike, long_put_strike

    def get_contract(self, bar: List[BarData], today: str, option_type: str, strike: int) -> str:
        """Get the contract string for a given strike and type."""
        return next(b.contract for b in bar if b.expiry_date == today and b.contract.endswith(f"_{option_type}_{strike}"))

    # State Management
    def getCurrentState(self) -> Dict[str, Any]:
        """Return the current state for persistence."""
        current_state = super().getCurrentState()
        current_state.update({
            "positions": self.positions,
            "entered": self.entered,
            "sl_triggered": self.sl_triggered,
            "sl_trigger_time": self.sl_trigger_time,
            "order_place_time": self.order_place_time
        })
        return current_state

    def setLastState(self, state: Dict[str, Any]):
        """Restore the last saved state."""
        super().setLastState(state)
        self.positions = state["positions"]
        self.entered = state["entered"]
        self.sl_triggered = state["sl_triggered"]
        self.sl_trigger_time = state["sl_trigger_time"]
        self.order_place_time = state["order_place_time"]