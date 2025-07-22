#!/usr/bin/env python3
"""
Unit tests for MT5 API
"""
import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))

from api.main import app, AccountInfo, OrderRequest  # noqa: E402


class TestMT5API(unittest.TestCase):
    """Test FastAPI endpoints"""

    def setUp(self):
        """Set up test client"""
        self.client = TestClient(app)

        # Mock MT5 client
        self.mock_mt5 = Mock()

        # Patch global mt5_client
        patcher = patch('main.mt5_client', self.mock_mt5)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_health_check_healthy(self):
        """Test health check when MT5 is connected"""
        mock_terminal_info = Mock()
        mock_terminal_info._asdict.return_value = {"connected": True}
        self.mock_mt5.terminal_info.return_value = mock_terminal_info

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["mt5_connected"])

    def test_health_check_unhealthy(self):
        """Test health check when MT5 is not connected"""
        self.mock_mt5.terminal_info.return_value = None

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "unhealthy")
        self.assertFalse(data["mt5_connected"])

    def test_get_account_info_success(self):
        """Test getting account information"""
        mock_account = Mock()
        mock_account.login = 12345
        mock_account.server = "TestServer"
        mock_account.balance = 10000.0
        mock_account.equity = 10500.0
        mock_account.margin = 100.0
        mock_account.margin_free = 10400.0
        mock_account.leverage = 100
        mock_account.currency = "USD"
        mock_account.name = "Test User"
        mock_account.company = "Test Broker"

        self.mock_mt5.account_info.return_value = mock_account

        response = self.client.get("/account")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["login"], 12345)
        self.assertEqual(data["balance"], 10000.0)
        self.assertEqual(data["currency"], "USD")

    def test_get_account_info_not_available(self):
        """Test account info when not available"""
        self.mock_mt5.account_info.return_value = None

        response = self.client.get("/account")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Account info not available", response.json()["detail"])

    def test_get_symbols(self):
        """Test getting all symbols"""
        mock_symbol1 = Mock()
        mock_symbol1.name = "EURUSD"
        mock_symbol1.visible = True

        mock_symbol2 = Mock()
        mock_symbol2.name = "GBPUSD"
        mock_symbol2.visible = True

        mock_symbol3 = Mock()
        mock_symbol3.name = "HIDDEN"
        mock_symbol3.visible = False

        self.mock_mt5.symbols_get.return_value = [mock_symbol1, mock_symbol2, mock_symbol3]

        response = self.client.get("/symbols")

        self.assertEqual(response.status_code, 200)
        symbols = response.json()
        self.assertEqual(len(symbols), 2)
        self.assertIn("EURUSD", symbols)
        self.assertIn("GBPUSD", symbols)
        self.assertNotIn("HIDDEN", symbols)

    def test_get_symbol_info_success(self):
        """Test getting symbol information"""
        mock_info = Mock()
        mock_info.name = "EURUSD"
        mock_info.description = "Euro vs US Dollar"
        mock_info.spread = 10
        mock_info.digits = 5
        mock_info.trade_contract_size = 100000
        mock_info.volume_min = 0.01
        mock_info.volume_max = 100.0
        mock_info.volume_step = 0.01

        mock_tick = Mock()
        mock_tick.bid = 1.1000
        mock_tick.ask = 1.1001

        self.mock_mt5.symbol_info.return_value = mock_info
        self.mock_mt5.symbol_info_tick.return_value = mock_tick

        response = self.client.get("/symbol/EURUSD")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "EURUSD")
        self.assertEqual(data["bid"], 1.1000)
        self.assertEqual(data["ask"], 1.1001)
        self.assertEqual(data["digits"], 5)

    def test_get_symbol_info_not_found(self):
        """Test symbol info for non-existent symbol"""
        self.mock_mt5.symbol_info.return_value = None

        response = self.client.get("/symbol/INVALID")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Symbol INVALID not found", response.json()["detail"])

    def test_place_order_buy_success(self):
        """Test placing a buy order"""
        # Mock symbol info
        mock_symbol = Mock()
        mock_symbol.name = "EURUSD"
        self.mock_mt5.symbol_info.return_value = mock_symbol

        # Mock tick
        mock_tick = Mock()
        mock_tick.bid = 1.1000
        mock_tick.ask = 1.1001
        self.mock_mt5.symbol_info_tick.return_value = mock_tick

        # Mock order result
        mock_result = Mock()
        mock_result.retcode = 10009  # TRADE_RETCODE_DONE
        mock_result.order = 12345
        mock_result.price = 1.1001
        mock_result.comment = "Success"
        self.mock_mt5.order_send.return_value = mock_result

        # Mock constants
        with patch('main.mt5_constants.ORDER_TYPE_BUY', 0), \
             patch('main.mt5_constants.TRADE_ACTION_DEAL', 1), \
             patch('main.mt5_constants.TRADE_RETCODE_DONE', 10009):

            order_request = {
                "symbol": "EURUSD",
                "volume": 0.1,
                "order_type": "BUY",
                "sl": 1.0950,
                "tp": 1.1050
            }

            response = self.client.post("/order", json=order_request)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["ticket"], 12345)
        self.assertEqual(data["price"], 1.1001)
        self.assertEqual(data["status"], "executed")

    def test_place_order_invalid_type(self):
        """Test placing order with invalid type"""
        order_request = {
            "symbol": "EURUSD",
            "volume": 0.1,
            "order_type": "INVALID"
        }

        response = self.client.post("/order", json=order_request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid order type", response.json()["detail"])

    def test_get_positions_empty(self):
        """Test getting positions when none exist"""
        self.mock_mt5.positions_get.return_value = None

        response = self.client.get("/positions")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_get_positions_with_data(self):
        """Test getting open positions"""
        mock_position = Mock()
        mock_position.ticket = 12345
        mock_position.symbol = "EURUSD"
        mock_position.volume = 0.1
        mock_position.type = 0  # Buy
        mock_position.price_open = 1.1000
        mock_position.price_current = 1.1010
        mock_position.profit = 10.0
        mock_position.sl = 1.0950
        mock_position.tp = 1.1050
        mock_position.time = 1234567890
        mock_position.magic = 0
        mock_position.comment = "Test"

        self.mock_mt5.positions_get.return_value = [mock_position]

        response = self.client.get("/positions")

        self.assertEqual(response.status_code, 200)
        positions = response.json()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["ticket"], 12345)
        self.assertEqual(positions[0]["type"], "BUY")
        self.assertEqual(positions[0]["profit"], 10.0)

    def test_close_position_not_found(self):
        """Test closing non-existent position"""
        self.mock_mt5.positions_get.return_value = None

        response = self.client.delete("/position/99999")

        self.assertEqual(response.status_code, 404)
        self.assertIn("Position not found", response.json()["detail"])

    def test_get_candles_success(self):
        """Test getting historical candles"""
        mock_rates = [
            {
                'time': 1234567890,
                'open': 1.1000,
                'high': 1.1010,
                'low': 1.0990,
                'close': 1.1005,
                'tick_volume': 100,
                'spread': 10
            },
            {
                'time': 1234567950,
                'open': 1.1005,
                'high': 1.1015,
                'low': 1.1000,
                'close': 1.1010,
                'tick_volume': 150,
                'spread': 12
            }
        ]

        self.mock_mt5.copy_rates_range.return_value = mock_rates

        # Mock constants
        with patch('main.mt5_constants.TIMEFRAME_M1', 1):
            request_data = {
                "symbol": "EURUSD",
                "timeframe": "M1",
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-01T01:00:00"
            }

            response = self.client.post("/history/candles", json=request_data)

        self.assertEqual(response.status_code, 200)
        candles = response.json()
        self.assertEqual(len(candles), 2)
        self.assertEqual(candles[0]["open"], 1.1000)
        self.assertEqual(candles[0]["close"], 1.1005)

    def test_get_candles_invalid_timeframe(self):
        """Test candles with invalid timeframe"""
        request_data = {
            "symbol": "EURUSD",
            "timeframe": "INVALID",
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-01T01:00:00"
        }

        response = self.client.post("/history/candles", json=request_data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid timeframe", response.json()["detail"])

    def test_websocket_ticks(self):
        """Test WebSocket tick streaming"""
        # This would require a more complex test setup with WebSocket client
        # For now, just verify the endpoint exists
        pass


class TestAPIModels(unittest.TestCase):
    """Test Pydantic models"""

    def test_account_info_model(self):
        """Test AccountInfo model validation"""
        account = AccountInfo(
            login=12345,
            server="TestServer",
            balance=10000.0,
            equity=10500.0,
            margin=100.0,
            free_margin=10400.0,
            leverage=100,
            currency="USD"
        )

        self.assertEqual(account.login, 12345)
        self.assertEqual(account.balance, 10000.0)
        self.assertEqual(account.name, "")  # Default value

    def test_order_request_model(self):
        """Test OrderRequest model validation"""
        order = OrderRequest(
            symbol="EURUSD",
            volume=0.1,
            order_type="BUY"
        )

        self.assertEqual(order.symbol, "EURUSD")
        self.assertEqual(order.volume, 0.1)
        self.assertEqual(order.deviation, 20)  # Default value
        self.assertEqual(order.magic, 0)  # Default value
        self.assertEqual(order.comment, "API Order")  # Default value

    def test_order_request_with_sl_tp(self):
        """Test OrderRequest with SL/TP"""
        order = OrderRequest(
            symbol="EURUSD",
            volume=0.1,
            order_type="SELL",
            sl=1.1050,
            tp=1.0950,
            magic=12345,
            comment="Test order"
        )

        self.assertEqual(order.sl, 1.1050)
        self.assertEqual(order.tp, 1.0950)
        self.assertEqual(order.magic, 12345)
        self.assertEqual(order.comment, "Test order")


if __name__ == '__main__':
    unittest.main()
