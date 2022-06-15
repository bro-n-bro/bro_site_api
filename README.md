# API for bronbro landing page

## Usage

requirements:

- pip3
- python3.8 or higher

1. Install `requirements.txt`

```bash
pip3 install -r requirements.txt
```

2. Setup a cron job for `python3 get_data.py` with 1 or more hour frequent
3. Setup an service for API with `python3 api.py` command

## What's going on? 

The `get_data.py` script collects data form networks in `config.py` file and saves it in `data.json` as usual as you've set up your cron job. The `api.py` only servs data from the `data.json`.