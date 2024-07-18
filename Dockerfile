FROM python:3

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY AXLAPI*.wsdl ./
COPY AXLSoap.xsd ./
COPY .env ./

ENTRYPOINT [ "python", "main.py" ]