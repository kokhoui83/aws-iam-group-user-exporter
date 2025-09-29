# AWS Group and Users in Identity Store
Query and export AWS Group and its users to CSV using python script

## Pre-requisite
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)
- Python 3.12.x

## Setup
- Create virtual environment
```
# venv
python -m venv .venv

# pipenv
pipenv --python 3.12
```

- Activate virtual envinronment
```
# venv
source .venv/bin/activate

# pipenv
pipenv shell
```


- Install dependencies
```
# requirements.txt
pip install -r requirements.txt

# pipenv
pipenv install
```

## Usage
- Create `.env` file
```
AWS_PROFILE=dev
IDENTITY_STORE_ID=abcd1234-efgh-5678
OUTPUT_FILE=myreport.csv
```

- Run
```
python main.py
```