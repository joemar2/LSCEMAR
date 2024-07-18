# LSC Expiration Monitoring and Automatic Renewal (EMAR)

Locally Significant Certificate (LSC) <ins>E</ins>xpiration <ins>M</ins>onitoring and <ins>A</ins>utomatic <ins>R</ins>enewal for Cisco Unified Communications Manager (CUCM) using the AXL API.

This script should be used with a scheduler to run periodically (daily for example).  Phones may restart after an LSC update.

It is recommended to also setup certificate monitoring on CUCM by following [Certificate Monitoring Task Flow](https://www.cisco.com/c/en/us/td/docs/voice_ip_comm/cucm/security/12_5_1/cucm_b_security-guide-1251/cucm_b_security-guide-1251_chapter_011111.html#task_86DB33CC77B85F10FCE6DB83881D8938) as a backup to be notified if certificates are not renewed for some reason.
## Installation

#### Rename **.env_example** to **.env** and edit the values.

Assuming a working python environment run the following to install dependencies.
```bash
pip install -r requirements.txt
```

Run the application with the following (.env will be read for all parameters)
```bash
python main.py
```

### -- OR --

#### Rename **.env_example** to **.env** and edit the values.

Create the docker image using the provided Dockerfile.
```bash
docker build --no-cache -t joemar2/lsc_emar .
```

Start the docker container:
```bash
docker run --rm -it --name lsc_emar joemar2/lsc_emar 
```


## Contribution
LSC Expiration Monitoring and Automatic Renewal (EMAR) is a community developed project. Code contributions are welcome.
Copyright (c) 2024 Cisco and/or its affiliates.