# AWS Group and Users in Identity Store
Query and export AWS Group and its users to CSV using bash script

## Pre-requisite
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html)

## Usage
- Make sure script is executable
```
chmod +x aws-identitystore-groups-users.sh
```
- Create `.env` file
```
AWS_PROFILE=dev
IDENTITY_STORE_ID=abcd1234-efgh-5678
OUTPUT_FILE=myreport.csv
```

- Run
```
./identitystore-groups-users.sh
```