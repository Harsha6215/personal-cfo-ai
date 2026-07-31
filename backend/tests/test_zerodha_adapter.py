"""
Tests for the Zerodha Holdings CSV adapter.
"""

from backend.services.import_engine.adapters.zerodha import ZerodhaHoldingsAdapter

SAMPLE_CSV = '''"Instrument","Qty.","Avg. cost","LTP","Invested","Cur. val","P&L","Net chg.","Day chg.",""
"EICHERMOT",2,7847.5,7833.5,15695,15667,-28,-0.18,-1,""
"GOLDBEES",150,97.04,117.11,14556.25,17566.5,3010.25,20.68,-0.22,""
"GROWW",65,100,194.4,6500,12636,6136,94.4,1.04,""
"GVT&D",5,3105.36,4323.3,15526.8,21616.5,6089.7,39.22,2.88,""
"HINDCOPPER",10,518.7,491.85,5187,4918.5,-268.5,-5.18,2.34,""
"LUPIN",5,2446,2415,12230,12075,-155,-1.27,-0.26,""
"MEDIASSIST",50,433.06,358,21653,17900,-3753,-17.33,0.15,""
"OSWALPUMPS",24,614,329.15,14736,7899.6,-6836.4,-46.39,-1.45,""
"SILVERBEES",100,154.69,206.51,15469.46,20651,5181.54,33.5,-0.06,""
'''


class TestZerodhaDetection:
    def test_detects_zerodha_holdings(self):
        adapter = ZerodhaHoldingsAdapter()
        assert adapter.detect(SAMPLE_CSV) is True

    def test_detects_by_filename(self):
        adapter = ZerodhaHoldingsAdapter()
        assert adapter.detect("some,random,content", "holdings (1).csv") is True

    def test_does_not_detect_random_csv(self):
        adapter = ZerodhaHoldingsAdapter()
        assert adapter.detect("name,age,city\nJohn,30,NYC") is False


class TestZerodhaValidation:
    def test_validates_correct_file(self):
        adapter = ZerodhaHoldingsAdapter()
        result = adapter.validate(SAMPLE_CSV)
        assert result.is_valid is True
        assert result.row_count == 9

    def test_rejects_empty_file(self):
        adapter = ZerodhaHoldingsAdapter()
        result = adapter.validate("Instrument,Qty.\n")
        assert result.is_valid is False


class TestZerodhaParsing:
    def test_parses_all_rows(self):
        adapter = ZerodhaHoldingsAdapter()
        transactions = adapter.parse(SAMPLE_CSV)
        assert len(transactions) == 9

    def test_first_row_values(self):
        adapter = ZerodhaHoldingsAdapter()
        transactions = adapter.parse(SAMPLE_CSV)
        eicher = transactions[0]
        assert eicher.ticker == "EICHERMOT"
        assert eicher.quantity == 2
        assert eicher.price == 7847.5
        assert eicher.event_type == "BUY"
        assert eicher.source == "zerodha"

    def test_goldbees_row(self):
        adapter = ZerodhaHoldingsAdapter()
        transactions = adapter.parse(SAMPLE_CSV)
        goldbees = transactions[1]
        assert goldbees.ticker == "GOLDBEES"
        assert goldbees.quantity == 150
        assert goldbees.price == 97.04
        assert goldbees.amount == 14556.25

    def test_all_tickers_parsed(self):
        adapter = ZerodhaHoldingsAdapter()
        transactions = adapter.parse(SAMPLE_CSV)
        tickers = [t.ticker for t in transactions]
        assert "EICHERMOT" in tickers
        assert "GOLDBEES" in tickers
        assert "GROWW" in tickers
        assert "GVT&D" in tickers
        assert "HINDCOPPER" in tickers
        assert "LUPIN" in tickers
        assert "MEDIASSIST" in tickers
        assert "OSWALPUMPS" in tickers
        assert "SILVERBEES" in tickers

    def test_no_errors(self):
        adapter = ZerodhaHoldingsAdapter()
        transactions = adapter.parse(SAMPLE_CSV)
        errors = [t for t in transactions if t.error]
        assert len(errors) == 0
