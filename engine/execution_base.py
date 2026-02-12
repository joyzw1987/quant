from abc import ABC, abstractmethod


class ExecutionBase(ABC):
    @abstractmethod
    def send_order(self, symbol, signal, price, size, atr=None, risk=None, contract_multiplier=None, bar_time=None):
        raise NotImplementedError

    @abstractmethod
    def check_exit(self, price, risk=None, bar_time=None):
        raise NotImplementedError

    @abstractmethod
    def force_close(self, price, bar_time=None):
        raise NotImplementedError

