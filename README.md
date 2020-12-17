Zenmoney tools
==============

Auxilliary tools to improve [Zenmoney](https://zenmoney.ru/)

Requirements
------------

* Python 3
* [Matplotlib](https://matplotlib.org), [pandas](https://pandas.pydata.org/)

Installation
------------

```bash
python3 -m venv .env  # or replace .env with appropriate name
. .env/bin/activate
pip install -r requirements
```

Usage examples
--------------

### Plot income chart

```bash
./graph-income-source.py --time Y zen_2020-10-10_dumpof_transactions_from_alltime.csv
```


Author
------

Alexander Sapozhnikov
http://shoorick.ru
<shoorick@cpan.org>
